"""
Serviço de Controlo do ESP8266.
Envia comandos HTTP para o microcontrolador que controla:
- Trava electromagnética (porta)
- LEDs (verde e vermelho)
- Buzzer (sonoro)
- Sensor DHT22 (temperatura e humidade)
"""

import requests
import logging
from app.services.utils import obter_configuracao

logger = logging.getLogger(__name__)


class ESPControlo:
    """
    Classe para comunicação com o ESP8266 via HTTP.

    O ESP8266 executa um servidor web que aceita comandos GET.
    Cada comando aciona um componente físico diferente.

    Endpoints do ESP8266:
    - /porta/abrir      → abre a trava (2 segundos)
    - /porta/fechar     → fecha a trava
    - /led/verde        → acende LED verde
    - /led/vermelho     → acende LED vermelho
    - /buzzer/ok        → beep curto (1x)
    - /buzzer/alerta    → beep longo (3x)
    - /temperatura      → retorna JSON com temp e humidade
    - /status           → retorna status geral
    """

    def __init__(self, app=None):
        """
        Inicializa o controlador ESP8266.

        Args:
            app: Instância Flask (opcional)
        """
        self.ip = None
        self.token = None
        self.timeout = 3  # segundos
        self.modo_simulacao = False

        if app:
            self._carregar_configuracoes_app(app)
        else:
            self._carregar_configuracoes_bd()

    def _carregar_configuracoes_app(self, app):
        """Carrega configurações da aplicação Flask."""
        self.ip = app.config.get('ESP_IP', '')
        self.token = app.config.get('TOKEN_ESP', '')
        self.modo_simulacao = app.config.get('MODO_SIMULACAO', False)

    def _carregar_configuracoes_bd(self):
        """Carrega configurações da base de dados."""
        self.ip = obter_configuracao('esp_ip', '')
        self.token = obter_configuracao('TOKEN_ESP', '')

    def _enviar_comando(self, endpoint: str, timeout: int = None) -> dict:
        """
        Envia um comando HTTP GET ao ESP8266.

        Args:
            endpoint: Caminho do endpoint (ex: '/porta/abrir')
            timeout: Timeout em segundos (opcional)

        Returns:
            Dicionário com resultado:
            {
                'sucesso': True/False,
                'status_code': 200,
                'resposta': '...',
                'erro': None ou mensagem
            }
        """
        resultado = {
            'sucesso': False,
            'status_code': None,
            'resposta': None,
            'erro': None,
        }

        if timeout is None:
            timeout = self.timeout

        # Modo simulação
        if self.modo_simulacao:
            logger.info(f'[SIMULAÇÃO] Comando ESP: {endpoint}')
            resultado['sucesso'] = True
            resultado['status_code'] = 200
            resultado['resposta'] = 'OK (simulado)'
            return resultado

        # Verificar IP configurado
        if not self.ip:
            logger.warning('IP do ESP8266 não configurado.')
            resultado['erro'] = 'IP do ESP8266 não configurado.'
            return resultado

        # Construir URL
        url = f'http://{self.ip}{endpoint}'

        # Headers com token (se configurado)
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            resposta = requests.get(url, headers=headers, timeout=timeout)

            resultado['status_code'] = resposta.status_code

            if resposta.status_code == 200:
                resultado['sucesso'] = True
                resultado['resposta'] = resposta.text.strip()
                logger.debug(f'Comando ESP OK: {endpoint} → {resposta.text.strip()}')
            else:
                resultado['erro'] = f'HTTP {resposta.status_code}: {resposta.text.strip()}'
                logger.warning(f'Comando ESP falhou: {endpoint} → HTTP {resposta.status_code}')

        except requests.ConnectionError:
            resultado['erro'] = 'ESP8266 offline (sem conexão)'
            logger.error(f'ESP8266 offline: {url}')

        except requests.Timeout:
            resultado['erro'] = f'Timeout ({timeout}s)'
            logger.error(f'Timeout ao contactar ESP8266: {url}')

        except Exception as e:
            resultado['erro'] = str(e)
            logger.error(f'Erro ao contactar ESP8266: {e}')

        return resultado

    # ============================================================
    # COMANDOS DA PORTA
    # ============================================================

    def abrir_porta(self) -> dict:
        """
        Abre a trava electromagnética.
        O ESP8266 mantém a porta aberta por 2 segundos.

        Returns:
            Resultado da operação
        """
        logger.info('🔓 Comando: ABRIR PORTA')
        return self._enviar_comando('/porta/abrir')

    def fechar_porta(self) -> dict:
        """
        Fecha a trava electromagnética imediatamente.

        Returns:
            Resultado da operação
        """
        logger.info('🔒 Comando: FECHAR PORTA')
        return self._enviar_comando('/porta/fechar')

    # ============================================================
    # COMANDOS DOS LEDS
    # ============================================================

    def led_verde(self) -> dict:
        """
        Acende o LED verde (acesso autorizado).

        Returns:
            Resultado da operação
        """
        logger.info('🟢 Comando: LED VERDE')
        return self._enviar_comando('/led/verde')

    def led_vermelho(self) -> dict:
        """
        Acende o LED vermelho (acesso negado/alerta).

        Returns:
            Resultado da operação
        """
        logger.info('🔴 Comando: LED VERMELHO')
        return self._enviar_comando('/led/vermelho')

    def led_desligar(self) -> dict:
        """
        Desliga todos os LEDs.

        Returns:
            Resultado da operação
        """
        logger.info('⚫ Comando: LEDS DESLIGAR')
        return self._enviar_comando('/led/desligar')

    # ============================================================
    # COMANDOS DO BUZZER
    # ============================================================

    def buzzer_ok(self) -> dict:
        """
        Emite um beep curto (1x) — acesso autorizado.

        Returns:
            Resultado da operação
        """
        logger.info('🔔 Comando: BUZZER OK')
        return self._enviar_comando('/buzzer/ok')

    def buzzer_alerta(self) -> dict:
        """
        Emite beeps longos (3x) — alerta de segurança.

        Returns:
            Resultado da operação
        """
        logger.info('🚨 Comando: BUZZER ALERTA')
        return self._enviar_comando('/buzzer/alerta')

    def buzzer_desligar(self) -> dict:
        """
        Desliga o buzzer imediatamente.

        Returns:
            Resultado da operação
        """
        logger.info('🔇 Comando: BUZZER DESLIGAR')
        return self._enviar_comando('/buzzer/desligar')

    # ============================================================
    # COMANDOS DE SENSORES
    # ============================================================

    def obter_temperatura(self) -> dict:
        """
        Obtém a temperatura e humidade do sensor DHT22.

        Returns:
            Dicionário com os dados:
            {
                'sucesso': True,
                'temperatura': 28.5,    # °C
                'humidade': 65.2,       # %
                'indice_calor': 30.1,   # sensação térmica (opcional)
            }
        """
        logger.info('🌡️ Comando: LER TEMPERATURA')

        resultado = self._enviar_comando('/temperatura', timeout=5)

        if resultado['sucesso'] and resultado['resposta']:
            try:
                import json
                dados = json.loads(resultado['resposta'])
                resultado['temperatura'] = dados.get('temperatura')
                resultado['humidade'] = dados.get('humidade')
                resultado['indice_calor'] = dados.get('indice_calor')
            except (json.JSONDecodeError, ValueError):
                resultado['temperatura'] = None
                resultado['humidade'] = None
                resultado['indice_calor'] = None

        return resultado

    def obter_status(self) -> dict:
        """
        Obtém o status geral do ESP8266.

        Returns:
            Dicionário com status:
            {
                'sucesso': True,
                'online': True,
                'porta_aberta': False,
                'led_verde': False,
                'led_vermelho': False,
                'buzzer': False,
                'temperatura': 28.5,
                'humidade': 65.2,
                'wifi_sinal': -45,     # dBm
                'uptime': 3600,        # segundos
            }
        """
        logger.info('📊 Comando: STATUS')

        resultado = self._enviar_comando('/status', timeout=5)
        resultado['online'] = resultado['sucesso']

        if resultado['sucesso'] and resultado['resposta']:
            try:
                import json
                dados = json.loads(resultado['resposta'])
                resultado.update(dados)
            except (json.JSONDecodeError, ValueError):
                pass

        return resultado

    # ============================================================
    # SEQUÊNCIAS PRÉ-DEFINIDAS
    # ============================================================

    def sequencia_autorizado(self) -> dict:
        """
        Executa a sequência completa para acesso autorizado:
        LED verde + Buzzer OK + Abrir porta.

        Returns:
            Resultado da operação
        """
        logger.info('✅ Sequência: ACESSO AUTORIZADO')

        resultados = {
            'led_verde': self.led_verde(),
            'buzzer_ok': self.buzzer_ok(),
            'abrir_porta': self.abrir_porta(),
        }

        sucesso_total = all(r['sucesso'] for r in resultados.values())

        return {
            'sucesso': sucesso_total,
            'resultados': resultados,
            'mensagem': 'Acesso autorizado!' if sucesso_total else 'Alguns comandos falharam.',
        }

    def sequencia_negado(self) -> dict:
        """
        Executa a sequência para acesso negado:
        LED vermelho + Buzzer alerta.

        Returns:
            Resultado da operação
        """
        logger.info('⛔ Sequência: ACESSO NEGADO')

        resultados = {
            'led_vermelho': self.led_vermelho(),
            'buzzer_alerta': self.buzzer_alerta(),
        }

        sucesso_total = all(r['sucesso'] for r in resultados.values())

        return {
            'sucesso': sucesso_total,
            'resultados': resultados,
            'mensagem': 'Alerta de segurança!' if sucesso_total else 'Alguns comandos falharam.',
        }

    def sequencia_emergencia(self) -> dict:
        """
        Executa a sequência de emergência:
        Abrir porta + LED vermelho piscando + Buzzer contínuo.

        Returns:
            Resultado da operação
        """
        logger.info('🚨 Sequência: EMERGÊNCIA')

        resultados = {
            'abrir_porta': self.abrir_porta(),
            'led_vermelho': self.led_vermelho(),
            'buzzer_alerta': self.buzzer_alerta(),
        }

        sucesso_total = all(r['sucesso'] for r in resultados.values())

        return {
            'sucesso': sucesso_total,
            'resultados': resultados,
            'mensagem': 'EMERGÊNCIA! Porta aberta!' if sucesso_total else 'Alguns comandos falharam.',
        }

    # ============================================================
    # TESTE DE CONEXÃO
    # ============================================================

    def testar_conexao(self) -> dict:
        """
        Testa se o ESP8266 está online e a responder.

        Returns:
            Dicionário com status da conexão
        """
        logger.info(f'🔍 Testando conexão com ESP8266 em {self.ip}')

        if self.modo_simulacao:
            return {
                'online': True,
                'ip': self.ip or 'simulado',
                'mensagem': 'Modo simulação ativo.',
            }

        if not self.ip:
            return {
                'online': False,
                'ip': None,
                'mensagem': 'IP do ESP8266 não configurado.',
            }

        resultado = self._enviar_comando('/status', timeout=3)

        return {
            'online': resultado['sucesso'],
            'ip': self.ip,
            'status_code': resultado['status_code'],
            'erro': resultado['erro'],
            'mensagem': (
                '🟢 ESP8266 online!'
                if resultado['sucesso']
                else f'🔴 ESP8266 offline: {resultado["erro"]}'
            ),
        }