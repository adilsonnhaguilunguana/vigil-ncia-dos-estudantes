"""
Serviço de Zona de Detecção.
Gere a linha virtual para detectar entrada e saída de pessoas.
"""

import logging
from app.services.utils import obter_configuracao

logger = logging.getLogger(__name__)


class ZonaDeteccao:
    """
    Classe responsável pela detecção de cruzamento da linha virtual.

    A linha virtual é configurável pelo utilizador via interface web
    e as coordenadas são guardadas na tabela configuracoes.

    Funcionamento:
    1. O sistema de reconhecimento rastreia a posição de cada pessoa
    2. A cada frame, verifica se a pessoa cruzou a linha
    3. Determina a direcção do cruzamento (entrada ou saída)
    """

    def __init__(self):
        """Inicializa a zona de detecção com as coordenadas da BD."""
        self._carregar_configuracoes()

    def _carregar_configuracoes(self):
        """Carrega as coordenadas e configurações da linha virtual da BD."""
        self.x1 = int(obter_configuracao('linha_x1', '0'))
        self.y1 = int(obter_configuracao('linha_y1', '300'))
        self.x2 = int(obter_configuracao('linha_x2', '1280'))
        self.y2 = int(obter_configuracao('linha_y2', '300'))
        self.ativa = obter_configuracao('linha_ativa', 'true') == 'true'
        self.direcao_entrada = obter_configuracao('direcao_entrada', 'cima_para_baixo')

        logger.debug(
            f'Linha virtual: ({self.x1},{self.y1}) → ({self.x2},{self.y2}) '
            f'| Ativa: {self.ativa} | Entrada: {self.direcao_entrada}'
        )

    def atualizar_configuracoes(self):
        """Recarrega as configurações da BD (chamado periodicamente)."""
        self._carregar_configuracoes()

    def verificar_cruzamento(self, x_anterior: int, y_anterior: int,
                             x_atual: int, y_atual: int) -> dict:
        """
        Verifica se uma pessoa cruzou a linha virtual entre dois frames.

        Args:
            x_anterior: Coordenada X no frame anterior
            y_anterior: Coordenada Y no frame anterior
            x_atual: Coordenada X no frame atual
            y_atual: Coordenada Y no frame atual

        Returns:
            Dicionário com o resultado:
            {
                'cruzou': True/False,
                'direcao': 'cima_para_baixo' / 'baixo_para_cima' / ...,
                'tipo': 'entrada' / 'saida',
                'ponto_cruzamento': (x, y) ou None
            }
        """
        resultado = {
            'cruzou': False,
            'direcao': None,
            'tipo': None,
            'ponto_cruzamento': None,
        }

        # Se a linha estiver desativada, não detecta nada
        if not self.ativa:
            return resultado

        # Verificar se o segmento de movimento cruza a linha virtual
        cruzou, ponto = self._segmentos_cruzam(
            x_anterior, y_anterior, x_atual, y_atual,
            self.x1, self.y1, self.x2, self.y2
        )

        if not cruzou:
            return resultado

        # Determinar a direcção do movimento
        direcao = self._determinar_direcao(x_anterior, y_anterior, x_atual, y_atual)

        # Determinar se é entrada ou saída
        tipo = 'entrada' if direcao == self.direcao_entrada else 'saida'

        resultado['cruzou'] = True
        resultado['direcao'] = direcao
        resultado['tipo'] = tipo
        resultado['ponto_cruzamento'] = ponto

        logger.info(f'🚶 Cruzamento detectado: {tipo.upper()} ({direcao})')

        return resultado

    def _determinar_direcao(self, x_anterior: int, y_anterior: int,
                            x_atual: int, y_atual: int) -> str:
        """
        Determina a direcção do movimento com base na posição anterior e atual.

        Args:
            x_anterior, y_anterior: Posição no frame anterior
            x_atual, y_atual: Posição no frame atual

        Returns:
            Uma das direcções:
            - 'cima_para_baixo' (y aumentou)
            - 'baixo_para_cima' (y diminuiu)
            - 'esquerda_para_direita' (x aumentou)
            - 'direita_para_esquerda' (x diminuiu)
        """
        dx = x_atual - x_anterior
        dy = y_atual - y_anterior

        # Determinar a direcção dominante
        if abs(dy) >= abs(dx):
            # Movimento vertical dominante
            if dy > 0:
                return 'cima_para_baixo'
            else:
                return 'baixo_para_cima'
        else:
            # Movimento horizontal dominante
            if dx > 0:
                return 'esquerda_para_direita'
            else:
                return 'direita_para_esquerda'

    def _segmentos_cruzam(self, x1: int, y1: int, x2: int, y2: int,
                          x3: int, y3: int, x4: int, y4: int) -> tuple:
        """
        Verifica se dois segmentos de reta se cruzam.
        Usa o algoritmo de orientação (cross product).

        Segmento A: (x1,y1) → (x2,y2)  - movimento da pessoa
        Segmento B: (x3,y3) → (x4,y4)  - linha virtual

        Args:
            x1, y1: Início do segmento A
            x2, y2: Fim do segmento A
            x3, y3: Início do segmento B
            x4, y4: Fim do segmento B

        Returns:
            Tuplo (cruzou: bool, ponto_cruzamento: tuple ou None)
        """
        # Calcular orientações
        o1 = self._orientacao(x1, y1, x2, y2, x3, y3)
        o2 = self._orientacao(x1, y1, x2, y2, x4, y4)
        o3 = self._orientacao(x3, y3, x4, y4, x1, y1)
        o4 = self._orientacao(x3, y3, x4, y4, x2, y2)

        # Caso geral: segmentos cruzam-se
        if o1 != o2 and o3 != o4:
            # Calcular ponto de intersecção
            ponto = self._calcular_intersecao(x1, y1, x2, y2, x3, y3, x4, y4)
            return True, ponto

        # Casos especiais: pontos colineares
        if o1 == 0 and self._ponto_no_segmento(x1, y1, x2, y2, x3, y3):
            return True, (x3, y3)
        if o2 == 0 and self._ponto_no_segmento(x1, y1, x2, y2, x4, y4):
            return True, (x4, y4)
        if o3 == 0 and self._ponto_no_segmento(x3, y3, x4, y4, x1, y1):
            return True, (x1, y1)
        if o4 == 0 and self._ponto_no_segmento(x3, y3, x4, y4, x2, y2):
            return True, (x2, y2)

        return False, None

    def _orientacao(self, ax: int, ay: int, bx: int, by: int,
                    cx: int, cy: int) -> int:
        """
        Calcula a orientação de três pontos.
        Usa o produto vetorial para determinar se os pontos estão
        no sentido horário, anti-horário ou são colineares.

        Args:
            ax, ay: Ponto A
            bx, by: Ponto B
            cx, cy: Ponto C

        Returns:
            0 → colineares
            1 → sentido horário
            2 → sentido anti-horário
        """
        val = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)

        if val == 0:
            return 0  # colineares
        return 1 if val > 0 else 2  # horário ou anti-horário

    def _ponto_no_segmento(self, ax: int, ay: int, bx: int, by: int,
                           cx: int, cy: int) -> bool:
        """
        Verifica se o ponto C está contido no segmento AB.
        Assume que A, B e C são colineares.

        Args:
            ax, ay: Ponto A (início do segmento)
            bx, by: Ponto B (fim do segmento)
            cx, cy: Ponto C (ponto a verificar)

        Returns:
            True se C está no segmento AB
        """
        return (
            min(ax, bx) <= cx <= max(ax, bx) and
            min(ay, by) <= cy <= max(ay, by)
        )

    def _calcular_intersecao(self, x1: int, y1: int, x2: int, y2: int,
                             x3: int, y3: int, x4: int, y4: int) -> tuple:
        """
        Calcula o ponto de intersecção entre dois segmentos.
        Usa a fórmula paramétrica da reta.

        Args:
            x1, y1, x2, y2: Segmento A
            x3, y3, x4, y4: Segmento B

        Returns:
            Tuplo (x, y) do ponto de intersecção
        """
        try:
            # Denominador da fórmula
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

            if den == 0:
                # Segmentos paralelos - retornar ponto médio da sobreposição
                return ((x1 + x2) // 2, (y1 + y2) // 2)

            # Parâmetros t e u
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den

            # Ponto de intersecção
            px = x1 + t * (x2 - x1)
            py = y1 + t * (y2 - y1)

            return (int(px), int(py))

        except ZeroDivisionError:
            return ((x1 + x2) // 2, (y1 + y2) // 2)

    def desenhar_linha(self, frame, cor=(0, 255, 255), espessura=3):
        """
        Desenha a linha virtual no frame (para visualização).

        Args:
            frame: Frame OpenCV (numpy array)
            cor: Cor da linha em BGR (padrão: amarelo)
            espessura: Espessura da linha em pixels

        Returns:
            Frame com a linha desenhada
        """
        import cv2

        # Linha principal
        cv2.line(frame, (self.x1, self.y1), (self.x2, self.y2), cor, espessura)

        # Pequenos círculos nas pontas (para arrastar)
        cv2.circle(frame, (self.x1, self.y1), 8, cor, -1)
        cv2.circle(frame, (self.x2, self.y2), 8, cor, -1)

        # Rótulo "ENTRADA" e "SAÍDA" nos lados
        altura, largura = frame.shape[:2]
        centro_x = (self.x1 + self.x2) // 2
        centro_y = (self.y1 + self.y2) // 2

        # Determinar qual lado é entrada
        if self.direcao_entrada == 'cima_para_baixo':
            cv2.putText(frame, 'ENTRADA', (centro_x - 40, centro_y - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, 'SAIDA', (centro_x - 30, centro_y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        elif self.direcao_entrada == 'baixo_para_cima':
            cv2.putText(frame, 'SAIDA', (centro_x - 30, centro_y - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, 'ENTRADA', (centro_x - 40, centro_y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Status da linha
        status = 'ATIVA' if self.ativa else 'DESATIVADA'
        cor_status = (0, 255, 0) if self.ativa else (0, 0, 255)
        cv2.putText(frame, f'Linha: {status}', (10, altura - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_status, 1)

        return frame

    def desenhar_cruzamento(self, frame, ponto: tuple, tipo: str):
        """
        Desenha indicador visual de cruzamento no frame.

        Args:
            frame: Frame OpenCV
            ponto: Coordenadas do ponto de cruzamento (x, y)
            tipo: 'entrada' ou 'saida'

        Returns:
            Frame com indicador desenhado
        """
        import cv2

        if ponto is None:
            return frame

        x, y = ponto

        # Cor baseada no tipo
        cor = (0, 255, 0) if tipo == 'entrada' else (0, 0, 255)
        texto = 'ENTRADA' if tipo == 'entrada' else 'SAIDA'

        # Círculo pulsante no ponto de cruzamento
        cv2.circle(frame, (x, y), 15, cor, 3)
        cv2.circle(frame, (x, y), 5, cor, -1)

        # Texto acima do ponto
        cv2.putText(frame, texto, (x - 30, y - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)

        return frame

    def esta_ativa(self) -> bool:
        """Verifica se a linha virtual está ativa."""
        return self.ativa

    def obter_configuracao_atual(self) -> dict:
        """
        Retorna a configuração atual da linha virtual.

        Returns:
            Dicionário com coordenadas e estado
        """
        return {
            'x1': self.x1,
            'y1': self.y1,
            'x2': self.x2,
            'y2': self.y2,
            'ativa': self.ativa,
            'direcao_entrada': self.direcao_entrada,
            'opcoes_direcao': [
                {'valor': 'cima_para_baixo', 'descricao': 'Cima → Baixo (padrão)'},
                {'valor': 'baixo_para_cima', 'descricao': 'Baixo → Cima'},
                {'valor': 'esquerda_para_direita', 'descricao': 'Esquerda → Direita'},
                {'valor': 'direita_para_esquerda', 'descricao': 'Direita → Esquerda'},
            ],
        }

    def rastrear_pessoa(self, frame, bbox: tuple, id_pessoa: int = 0) -> dict:
        """
        Rastreia uma pessoa entre frames e verifica se cruzou a linha.

        Deve ser chamado a cada frame para cada pessoa detectada.
        Mantém um dicionário interno de posições anteriores.

        Args:
            frame: Frame atual (para desenho)
            bbox: Bounding box da pessoa (x, y, w, h)
            id_pessoa: Identificador único da pessoa

        Returns:
            Resultado do rastreamento com cruzamento se detectado
        """
        if not hasattr(self, '_historico_posicoes'):
            self._historico_posicoes = {}

        x, y, w, h = bbox
        # Usar o centro inferior da bounding box (pés da pessoa)
        centro_x = x + w // 2
        centro_y = y + h  # base da bounding box

        resultado = {
            'cruzou': False,
            'direcao': None,
            'tipo': None,
            'ponto': None,
        }

        # Verificar se já temos posição anterior para esta pessoa
        if id_pessoa in self._historico_posicoes:
            x_ant, y_ant = self._historico_posicoes[id_pessoa]

            # Só verifica se houve movimento significativo
            distancia = ((centro_x - x_ant) ** 2 + (centro_y - y_ant) ** 2) ** 0.5
            if distancia > 10:  # pixels mínimos para considerar movimento
                resultado = self.verificar_cruzamento(
                    x_ant, y_ant, centro_x, centro_y
                )

        # Atualizar posição histórica
        self._historico_posicoes[id_pessoa] = (centro_x, centro_y)

        # Limpar histórico antigo (mais de 5 segundos)
        # (implementação simplificada - pode ser melhorada)
        if len(self._historico_posicoes) > 50:
            self._historico_posicoes.clear()

        return resultado

    def limpar_historico(self):
        """Limpa o histórico de posições rastreadas."""
        if hasattr(self, '_historico_posicoes'):
            self._historico_posicoes.clear()