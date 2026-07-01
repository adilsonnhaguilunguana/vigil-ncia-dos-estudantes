"""
Serviço de Cadastro de Alunos.
Gere a captura de foto, verificação de qualidade e processamento de imagem.
"""

import os
import cv2
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from app.services.utils import (
    verificar_qualidade_foto,
    redimensionar_imagem,
    gerar_nome_ficheiro,
    logger,
)


class CadastroAluno:
    """
    Classe responsável pelo cadastro de alunos com verificação de qualidade.

    Critérios de qualidade da foto:
    - Nitidez (Laplacian variance > 100)           → 25 pontos
    - Brilho (média pixel entre 80-200)             → 25 pontos
    - Rosto detectado pelo Haar Cascade             → 35 pontos
    - Resolução mínima 300x300                      → 15 pontos
    - Pontuação total mínima para aprovação: 60%
    """

    def __init__(self, pasta_alunos: str, qualidade_minima: int = 60):
        """
        Inicializa o serviço de cadastro.

        Args:
            pasta_alunos: Caminho da pasta onde guardar as fotos
            qualidade_minima: Percentagem mínima para aprovar a foto
        """
        self.pasta_alunos = pasta_alunos
        self.qualidade_minima = qualidade_minima

        # Criar pasta se não existir
        os.makedirs(self.pasta_alunos, exist_ok=True)

        # Carregar classificador Haar Cascade para deteção de rostos
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def processar_foto(self, arquivo_foto, numero_aluno: str, nome_aluno: str) -> dict:
        """
        Processa a foto de um aluno: valida, verifica qualidade e guarda.

        Args:
            arquivo_foto: Ficheiro da foto (UploadedFile do Flask)
            numero_aluno: Número do aluno
            nome_aluno: Nome do aluno

        Returns:
            Dicionário com resultado do processamento:
            {
                'sucesso': True/False,
                'foto_path': 'alunos/001_joao_silva.jpg',
                'qualidade': {...},
                'mensagem': '...',
                'erros': [...]
            }
        """
        resultado = {
            'sucesso': False,
            'foto_path': None,
            'qualidade': None,
            'mensagem': '',
            'erros': [],
        }

        # Validar se o arquivo foi enviado
        if not arquivo_foto or not arquivo_foto.filename:
            resultado['erros'].append('Nenhum arquivo de foto enviado.')
            resultado['mensagem'] = 'Nenhum arquivo enviado.'
            return resultado

        # Validar extensão do arquivo
        extensoes_permitidas = {'.jpg', '.jpeg', '.png', '.bmp'}
        ext = os.path.splitext(arquivo_foto.filename)[1].lower()

        if ext not in extensoes_permitidas:
            resultado['erros'].append(
                f'Formato {ext} não permitido. Use: {", ".join(extensoes_permitidas)}'
            )
            resultado['mensagem'] = 'Formato de arquivo inválido.'
            return resultado

        # Gerar nome seguro para o ficheiro
        nome_base = f'{numero_aluno}_{nome_aluno.lower().replace(" ", "_")}'
        nome_base = secure_filename(nome_base)
        nome_ficheiro = f'{nome_base}{ext}'

        # Caminhos
        caminho_temp = os.path.join(self.pasta_alunos, f'temp_{nome_ficheiro}')
        caminho_final = os.path.join(self.pasta_alunos, nome_ficheiro)

        try:
            # Guardar arquivo temporário
            arquivo_foto.save(caminho_temp)
            logger.info(f'Foto temporária guardada: {caminho_temp}')

            # Verificar qualidade
            qualidade = verificar_qualidade_foto(caminho_temp)
            resultado['qualidade'] = qualidade

            # Verificar se a foto foi aprovada
            if not qualidade['aprovada']:
                # Remover foto temporária
                os.remove(caminho_temp)
                resultado['erros'] = qualidade['dicas']
                resultado['mensagem'] = (
                    f'Foto recusada. Qualidade: {qualidade["pontuacao_total"]}% '
                    f'(mínimo: {self.qualidade_minima}%)'
                )
                logger.warning(
                    f'Foto recusada para {nome_aluno}: {qualidade["pontuacao_total"]}%'
                )
                return resultado

            # Foto aprovada → redimensionar e guardar
            redimensionar_imagem(caminho_temp, caminho_final, largura=640, altura=480)

            # Remover temporária
            if os.path.exists(caminho_temp):
                os.remove(caminho_temp)

            # Caminho relativo para a BD
            foto_path_relativa = f'alunos/{nome_ficheiro}'

            resultado['sucesso'] = True
            resultado['foto_path'] = foto_path_relativa
            resultado['mensagem'] = (
                f'Foto aprovada! Qualidade: {qualidade["pontuacao_total"]}%'
            )
            logger.info(
                f'Foto aprovada para {nome_aluno}: {qualidade["pontuacao_total"]}%'
            )

            return resultado

        except Exception as e:
            logger.error(f'Erro ao processar foto: {e}')
            # Limpar arquivos temporários
            for caminho in [caminho_temp, caminho_final]:
                if os.path.exists(caminho):
                    os.remove(caminho)
            resultado['erros'].append(f'Erro interno: {str(e)}')
            resultado['mensagem'] = 'Erro ao processar a foto.'
            return resultado

    def capturar_foto_webcam(self, camera_id: int = 0) -> np.ndarray:
        """
        Captura uma foto da webcam para cadastro.

        Args:
            camera_id: ID da câmara (0 = webcam padrão)

        Returns:
            Frame capturado (array numpy) ou None se falhar
        """
        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            logger.error(f'Não foi possível abrir a câmara {camera_id}')
            return None

        try:
            # Aguardar a câmara aquecer
            for _ in range(30):
                ret, frame = cap.read()

            # Capturar o frame final
            ret, frame = cap.read()

            if ret and frame is not None:
                logger.info('Foto capturada da webcam com sucesso.')
                return frame
            else:
                logger.error('Falha ao capturar frame da webcam.')
                return None

        finally:
            cap.release()

    def verificar_rosto_webcam(self, frame: np.ndarray) -> dict:
        """
        Verifica se há um rosto no frame da webcam.

        Args:
            frame: Frame da webcam

        Returns:
            Dicionário com resultado da deteção
        """
        if frame is None:
            return {'rosto_detectado': False, 'total_rostos': 0, 'mensagem': 'Frame vazio.'}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostos = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(rostos) == 0:
            return {
                'rosto_detectado': False,
                'total_rostos': 0,
                'mensagem': 'Nenhum rosto detectado. Posicione-se em frente à câmara.',
            }
        elif len(rostos) == 1:
            x, y, w, h = rostos[0]
            return {
                'rosto_detectado': True,
                'total_rostos': 1,
                'posicao': {'x': int(x), 'y': int(y), 'largura': int(w), 'altura': int(h)},
                'mensagem': 'Rosto detectado! Pode capturar a foto.',
            }
        else:
            return {
                'rosto_detectado': False,
                'total_rostos': len(rostos),
                'mensagem': f'{len(rostos)} rostos detectados. Apenas uma pessoa deve estar na foto.',
            }

    def desenhar_guia_rosto(self, frame: np.ndarray) -> np.ndarray:
        """
        Desenha uma guia oval no frame para ajudar a posicionar o rosto.

        Args:
            frame: Frame da webcam

        Returns:
            Frame com a guia desenhada
        """
        if frame is None:
            return None

        altura, largura = frame.shape[:2]

        # Centro do frame
        centro_x = largura // 2
        centro_y = altura // 2

        # Tamanho do oval guia
        eixo_x = largura // 4
        eixo_y = altura // 3

        # Desenhar oval guia
        cv2.ellipse(
            frame,
            (centro_x, centro_y),
            (eixo_x, eixo_y),
            0, 0, 360,
            (0, 255, 0),  # verde
            2
        )

        # Texto de instrução
        cv2.putText(
            frame,
            'Posicione o rosto aqui',
            (centro_x - 120, centro_y - eixo_y - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        return frame

    def processar_cadastro_completo(
        self, arquivo_foto, numero_aluno: str, nome_aluno: str,
        turma: str = None, telefone_pai: str = None, nome_pai: str = None
    ) -> dict:
        """
        Processa o cadastro completo: foto + dados do aluno.

        Args:
            arquivo_foto: Foto do aluno
            numero_aluno: Número do aluno
            nome_aluno: Nome do aluno
            turma: Turma do aluno
            telefone_pai: Telefone do pai/responsável
            nome_pai: Nome do pai/responsável

        Returns:
            Dicionário com resultado completo
        """
        from app.database import db
        from app.models import Aluno

        resultado = {
            'sucesso': False,
            'aluno': None,
            'foto_resultado': None,
            'mensagem': '',
        }

        # 1. Processar foto
        foto_resultado = self.processar_foto(arquivo_foto, numero_aluno, nome_aluno)
        resultado['foto_resultado'] = foto_resultado

        if not foto_resultado['sucesso']:
            resultado['mensagem'] = foto_resultado['mensagem']
            return resultado

        # 2. Verificar se o número já existe
        if Aluno.query.filter_by(numero=numero_aluno).first():
            # Remover foto já guardada
            caminho_foto = os.path.join(self.pasta_alunos, os.path.basename(foto_resultado['foto_path']))
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)

            resultado['mensagem'] = f'O número {numero_aluno} já está cadastrado.'
            return resultado

        # 3. Criar aluno na BD
        try:
            aluno = Aluno(
                nome=nome_aluno,
                numero=numero_aluno,
                turma=turma,
                foto_path=foto_resultado['foto_path'],
                telefone_pai=telefone_pai,
                nome_pai=nome_pai,
                activo=True,
            )
            db.session.add(aluno)
            db.session.commit()

            resultado['sucesso'] = True
            resultado['aluno'] = aluno
            resultado['mensagem'] = f'Aluno {nome_aluno} cadastrado com sucesso!'
            logger.info(f'Aluno cadastrado: {numero_aluno} - {nome_aluno}')

        except Exception as e:
            db.session.rollback()
            # Remover foto guardada
            caminho_foto = os.path.join(self.pasta_alunos, os.path.basename(foto_resultado['foto_path']))
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)

            resultado['mensagem'] = f'Erro ao guardar aluno: {str(e)}'
            logger.error(f'Erro ao cadastrar aluno: {e}')

        return resultado