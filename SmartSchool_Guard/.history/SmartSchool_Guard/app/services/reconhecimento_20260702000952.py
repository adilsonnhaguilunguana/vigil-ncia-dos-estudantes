"""
Serviço de Reconhecimento Facial.
Gere o loop principal de captura de vídeo, deteção e reconhecimento de rostos.
"""

import os
import cv2
import time
import threading
import requests
import numpy as np
from datetime import datetime
from deepface import DeepFace
from app.database import db
from app.models import Aluno, Registo, Alerta, SessaoAtiva, Configuracao
from app.services.utils import (
    obter_configuracao,
    guardar_configuracao,
    salvar_frame,
    logger,
)


class ReconhecimentoFacial:
    """
    Classe principal do sistema de reconhecimento facial.
    Executa em loop contínuo: captura frame → detecta rostos → reconhece → regista.
    """

    def __init__(self, app):
        """
        Inicializa o sistema de reconhecimento.

        Args:
            app: Instância da aplicação Flask (para contexto da BD)
        """
        self.app = app
        self.em_execucao = False
        self.thread = None

        # Configurações carregadas da BD
        self.confianca_minima = 60
        self.modelo_facial = 'VGG-Face'
        self.ip_camara = ''
        self.cooldown_segundos = 30  # evita duplicados

        # Estado interno
        self.ultimo_reconhecimento = {}  # aluno_id → timestamp
        self.frame_atual = None
        self.rostos_detectados = []

        # Pastas
        self.pasta_alunos = app.config.get('ALUNOS_FOLDER', 'uploads/alunos')
        self.pasta_frames = app.config.get('FRAMES_FOLDER', 'uploads/frames')
        self.pasta_embeddings = app.config.get('EMBEDDINGS_FOLDER', 'uploads/embeddings')

        os.makedirs(self.pasta_frames, exist_ok=True)
        os.makedirs(self.pasta_embeddings, exist_ok=True)

    def carregar_configuracoes(self):
        """Carrega as configurações atuais da base de dados."""
        with self.app.app_context():
            self.confianca_minima = int(obter_configuracao('confianca_minima', '60'))
            self.modelo_facial = obter_configuracao('modelo_facial', 'VGG-Face')
            self.ip_camara = obter_configuracao('ip_camara', '')
            self.cooldown_segundos = int(obter_configuracao('cooldown_segundos', '30'))

    def iniciar(self):
        """Inicia o loop de reconhecimento numa thread separada."""
        if self.em_execucao:
            logger.warning('Sistema de reconhecimento já está em execução.')
            return

        self.carregar_configuracoes()

        if not self.ip_camara:
            logger.error('Câmara IP não configurada. Não é possível iniciar.')
            return

        self.em_execucao = True
        self.thread = threading.Thread(target=self._loop_reconhecimento, daemon=True)
        self.thread.start()
        logger.info('🔍 Sistema de reconhecimento facial iniciado.')

    def parar(self):
        """Para o loop de reconhecimento."""
        self.em_execucao = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info('⏹️ Sistema de reconhecimento facial parado.')

    def _loop_reconhecimento(self):
        """Loop principal: captura → deteta → reconhece → age."""
        stream_url = f'http://{self.ip_camara}/video'
        cap = None

        # Tentar abrir o stream
        tentativas = 0
        while self.em_execucao and tentativas < 10:
            try:
                cap = cv2.VideoCapture(stream_url)
                if cap.isOpened():
                    logger.info(f'📹 Conectado à câmara: {stream_url}')
                    break
                tentativas += 1
                time.sleep(2)
            except Exception as e:
                logger.error(f'Erro ao conectar à câmara: {e}')
                tentativas += 1
                time.sleep(2)

        if not cap or not cap.isOpened():
            logger.error('❌ Não foi possível conectar à câmara IP.')
            self.em_execucao = False
            return

        # Carregar embeddings dos alunos (cache)
        embeddings_alunos = self._carregar_embeddings()

        frame_count = 0
        ultima_recarga_config = time.time()

        while self.em_execucao:
            try:
                # Recarregar configurações a cada 60 segundos
                if time.time() - ultima_recarga_config > 60:
                    self.carregar_configuracoes()
                    ultima_recarga_config = time.time()

                # Capturar frame
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning('Frame vazio, a reconectar...')
                    time.sleep(0.5)
                    continue

                self.frame_atual = frame.copy()
                frame_count += 1

                # Processar apenas a cada 3 frames (≈10 FPS → 3-4 reconhecimentos/seg)
                if frame_count % 3 != 0:
                    continue

                # Reduzir resolução para acelerar processamento
                frame_pequeno = cv2.resize(frame, (640, 480))

                # Detetar rostos
                rostos = self._detetar_rostos(frame_pequeno)

                if rostos:
                    self.rostos_detectados = rostos

                    for (x, y, w, h) in rostos:
                        # Extrair região do rosto
                        rosto = frame_pequeno[y:y+h, x:x+w]

                        # Tentar reconhecer
                        resultado = self._reconhecer_rosto(rosto, embeddings_alunos)

                        if resultado['identificado']:
                            self._processar_aluno_reconhecido(
                                resultado, frame_pequeno, (x, y, w, h)
                            )
                        else:
                            self._processar_desconhecido(frame_pequeno, (x, y, w, h))

                # Pequena pausa para não sobrecarregar o CPU
                time.sleep(0.05)

            except Exception as e:
                logger.error(f'Erro no loop de reconhecimento: {e}')
                time.sleep(1)

        # Libertar recursos
        if cap:
            cap.release()
        logger.info('📴 Stream da câmara fechado.')

    def _detetar_rostos(self, frame: np.ndarray) -> list:
        """
        Deteta rostos no frame usando OpenCV Haar Cascade.

        Args:
            frame: Frame a processar

        Returns:
            Lista de tuplos (x, y, largura, altura)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Classificador Haar Cascade (rápido, bom para tempo real)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        rostos = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        return rostos

    def _carregar_embeddings(self) -> dict:
        """
        Carrega os embeddings faciais dos alunos da BD.
        Se não existirem, calcula e guarda.

        Returns:
            Dicionário {aluno_id: {'embedding': array, 'nome': str, 'caminho_foto': str}}
        """
        embeddings = {}

        with self.app.app_context():
            alunos = Aluno.query.filter_by(activo=True).all()

            for aluno in alunos:
                if not aluno.foto_path:
                    continue

                caminho_foto = os.path.join(
                    os.path.dirname(self.pasta_alunos),
                    aluno.foto_path
                )

                if not os.path.exists(caminho_foto):
                    continue

                # Verificar se o embedding já foi calculado
                embedding_path = aluno.embedding_path
                if embedding_path:
                    caminho_embedding = os.path.join(
                        os.path.dirname(self.pasta_embeddings),
                        embedding_path
                    )
                    if os.path.exists(caminho_embedding):
                        try:
                            embedding = np.load(caminho_embedding)
                            embeddings[aluno.id] = {
                                'embedding': embedding,
                                'nome': aluno.nome,
                                'caminho_foto': caminho_foto,
                            }
                            continue
                        except Exception:
                            pass  # Se falhar, recalcula

                # Calcular embedding
                try:
                    embedding = DeepFace.represent(
                        img_path=caminho_foto,
                        model_name=self.modelo_facial,
                        enforce_detection=False,
                    )[0]['embedding']

                    # Guardar embedding para uso futuro
                    nome_embedding = f'{aluno.numero}_{aluno.id}.npy'
                    caminho_embedding = os.path.join(self.pasta_embeddings, nome_embedding)
                    np.save(caminho_embedding, np.array(embedding))

                    # Atualizar caminho na BD
                    aluno.embedding_path = f'embeddings/{nome_embedding}'
                    db.session.commit()

                    embeddings[aluno.id] = {
                        'embedding': np.array(embedding),
                        'nome': aluno.nome,
                        'caminho_foto': caminho_foto,
                    }

                except Exception as e:
                    logger.error(f'Erro ao calcular embedding para {aluno.nome}: {e}')

        logger.info(f'📊 {len(embeddings)} embeddings carregados.')
        return embeddings

    def _reconhecer_rosto(self, rosto: np.ndarray, embeddings_alunos: dict) -> dict:
        """
        Tenta reconhecer um rosto comparando com os embeddings conhecidos.

        Args:
            rosto: Imagem do rosto (array numpy)
            embeddings_alunos: Dicionário de embeddings dos alunos

        Returns:
            {
                'identificado': bool,
                'aluno_id': int ou None,
                'nome': str ou None,
                'confianca': float,
            }
        """
        resultado = {
            'identificado': False,
            'aluno_id': None,
            'nome': None,
            'confianca': 0.0,
        }

        if not embeddings_alunos:
            return resultado

        try:
            # Gerar embedding do rosto capturado
            embedding_capturado = DeepFace.represent(
                img_path=rosto,
                model_name=self.modelo_facial,
                enforce_detection=False,
            )[0]['embedding']
            embedding_capturado = np.array(embedding_capturado)

            # Comparar com cada aluno conhecido (distância cosseno)
            melhor_confianca = 0.0
            melhor_aluno_id = None
            melhor_nome = None

            for aluno_id, dados in embeddings_alunos.items():
                embedding_aluno = dados['embedding']

                # Calcular distância cosseno
                similaridade = self._distancia_cosseno(embedding_capturado, embedding_aluno)

                # Converter para percentagem de confiança
                confianca = (1 - similaridade) * 100

                if confianca > melhor_confianca:
                    melhor_confianca = confianca
                    melhor_aluno_id = aluno_id
                    melhor_nome = dados['nome']

            # Verificar se a confiança atinge o mínimo
            if melhor_confianca >= self.confianca_minima:
                resultado['identificado'] = True
                resultado['aluno_id'] = melhor_aluno_id
                resultado['nome'] = melhor_nome
                resultado['confianca'] = round(melhor_confianca, 1)

        except Exception as e:
            logger.error(f'Erro no reconhecimento: {e}')

        return resultado

    def _distancia_cosseno(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calcula a distância cosseno entre dois vetores.

        Args:
            a: Primeiro vetor
            b: Segundo vetor

        Returns:
            Distância cosseno (0 = idênticos, 2 = opostos)
        """
        a = a.flatten()
        b = b.flatten()
        dot = np.dot(a, b)
        norma = np.linalg.norm(a) * np.linalg.norm(b)
        if norma == 0:
            return 1.0
        return 1 - (dot / norma)

    def _processar_aluno_reconhecido(self, resultado: dict, frame: np.ndarray,
                                     bbox: tuple):
        """
        Processa um aluno reconhecido: regista entrada/saída, notifica, controla ESP.

        Args:
            resultado: Dicionário com dados do reconhecimento
            frame: Frame atual
            bbox: Coordenadas do rosto (x, y, w, h)
        """
        aluno_id = resultado['aluno_id']
        agora = datetime.now()

        # Verificar cooldown (evitar duplicados em 30s)
        ultimo = self.ultimo_reconhecimento.get(aluno_id)
        if ultimo and (agora - ultimo).total_seconds() < self.cooldown_segundos:
            return

        self.ultimo_reconhecimento[aluno_id] = agora

        with self.app.app_context():
            aluno = Aluno.query.get(aluno_id)
            if not aluno:
                return

            # Verificar se está presente ou não
            sessao_ativa = SessaoAtiva.query.filter_by(
                aluno_id=aluno_id,
                hora_saida=None
            ).first()

            if sessao_ativa:
                # Aluno estava dentro → é uma SAÍDA
                tipo = 'saida'
                direcao = 'saida'

                # Fechar sessão ativa
                sessao_ativa.hora_saida = agora
                aluno.presente = False

                logger.info(f'🚶 SAÍDA: {aluno.nome}')
            else:
                # Aluno estava fora → é uma ENTRADA
                tipo = 'entrada'
                direcao = 'entrada'

                # Criar nova sessão ativa
                nova_sessao = SessaoAtiva(
                    aluno_id=aluno_id,
                    hora_entrada=agora,
                )
                db.session.add(nova_sessao)
                aluno.presente = True

                logger.info(f'🚶 ENTRADA: {aluno.nome} ({resultado["confianca"]}%)')

            # Guardar frame do momento
            frame_path = salvar_frame(frame, self.pasta_frames, f'{aluno.numero}_{tipo}')

            # Criar registo
            registo = Registo(
                aluno_id=aluno_id,
                tipo=tipo,
                confianca=resultado['confianca'],
                direcao=direcao,
                frame_path=frame_path,
                metodo='facial',
            )
            db.session.add(registo)
            db.session.commit()

            # Enviar notificação (WhatsApp)
            self._enviar_notificacao(aluno, tipo, agora)

            # Controlar ESP8266
            self._controlar_esp(tipo, aluno.nome)

    def _processar_desconhecido(self, frame: np.ndarray, bbox: tuple):
        """
        Processa uma pessoa desconhecida: gera alerta.

        Args:
            frame: Frame atual
            bbox: Coordenadas do rosto (x, y, w, h)
        """
        agora = datetime.now()

        # Guardar frame
        frame_path = salvar_frame(frame, self.pasta_frames, 'desconhecido')

        with self.app.app_context():
            # Criar alerta
            alerta = Alerta(
                tipo='desconhecido',
                descricao='Pessoa desconhecida detectada pela câmara.',
                severidade='alerta',
                frame_path=frame_path,
            )
            db.session.add(alerta)
            db.session.commit()

            logger.warning(f'🚨 ALERTA: Pessoa desconhecida detectada!')

        # Acionar ESP8266 (LED vermelho + buzzer)
        self._controlar_esp('alerta')

    def _enviar_notificacao(self, aluno: Aluno, tipo: str, hora: datetime):
        """
        Envia notificação WhatsApp ao pai do aluno.

        Args:
            aluno: Objeto Aluno
            tipo: 'entrada' ou 'saida'
            hora: Data/hora do evento
        """
        notificar_pais = obter_configuracao('notificar_pais', 'true')
        if notificar_pais != 'true':
            return

        if not aluno.telefone_pai:
            return

        try:
            from app.services.notificacoes import Notificador
            notificador = Notificador()

            if tipo == 'entrada':
                notificador.notificar_entrada(
                    aluno.nome, aluno.telefone_pai, hora
                )
            else:
                notificador.notificar_saida(
                    aluno.nome, aluno.telefone_pai, hora
                )
        except Exception as e:
            logger.error(f'Erro ao enviar notificação: {e}')

    def _controlar_esp(self, acao: str, nome_aluno: str = None):
        """
        Envia comandos HTTP ao ESP8266.

        Args:
            acao: 'entrada', 'saida', ou 'alerta'
            nome_aluno: Nome do aluno (opcional)
        """
        try:
            from app.services.esp_controlo import ESPControlo
            esp = ESPControlo()

            if acao == 'entrada':
                esp.abrir_porta()
                esp.led_verde()
                esp.buzzer_ok()
            elif acao == 'saida':
                esp.abrir_porta()
                esp.led_verde()
                esp.buzzer_ok()
            elif acao == 'alerta':
                esp.led_vermelho()
                esp.buzzer_alerta()

        except Exception as e:
            logger.error(f'Erro ao controlar ESP8266: {e}')

    def obter_frame_atual(self):
        """Retorna o frame atual com anotações (para dashboard)."""
        if self.frame_atual is None:
            return None

        frame = self.frame_atual.copy()

        # Desenhar retângulos nos rostos
        for (x, y, w, h) in self.rostos_detectados:
            # Escala de volta para o tamanho original
            escala_x = frame.shape[1] / 640
            escala_y = frame.shape[0] / 480
            x = int(x * escala_x)
            y = int(y * escala_y)
            w = int(w * escala_x)
            h = int(h * escala_y)

            # Retângulo verde (por padrão, o reconhecimento atualiza a cor)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return frame


# ============================================================
# INSTÂNCIA GLOBAL (inicializada no app)
# ============================================================

reconhecimento = None


def init_reconhecimento(app):
    """Inicializa a instância global do reconhecimento."""
    global reconhecimento
    reconhecimento = ReconhecimentoFacial(app)
    return reconhecimento