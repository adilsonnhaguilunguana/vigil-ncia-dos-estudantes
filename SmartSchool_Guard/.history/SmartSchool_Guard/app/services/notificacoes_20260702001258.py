"""
Serviço de Notificações.
Envia mensagens WhatsApp/SMS aos pais via Twilio.
"""

import logging
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.services.utils import obter_configuracao, formatar_hora, formatar_data

logger = logging.getLogger(__name__)


class Notificador:
    """
    Classe responsável pelo envio de notificações via Twilio.

    Suporta:
    - WhatsApp (recomendado)
    - SMS (fallback)

    Mensagens enviadas:
    - Entrada do aluno
    - Saída do aluno
    - Alerta de segurança
    - Alerta de emergência
    """

    def __init__(self, app=None):
        """
        Inicializa o notificador.

        Args:
            app: Instância Flask (opcional, para aceder às configs)
        """
        self.account_sid = None
        self.auth_token = None
        self.numero_twilio = None
        self.cliente = None
        self.notificar_pais = True
        self.modo_simulacao = False

        if app:
            self._carregar_configuracoes_app(app)
        else:
            self._carregar_configuracoes_bd()

    def _carregar_configuracoes_app(self, app):
        """Carrega configurações da aplicação Flask."""
        self.account_sid = app.config.get('TWILIO_SID', '')
        self.auth_token = app.config.get('TWILIO_TOKEN', '')
        self.numero_twilio = app.config.get('TWILIO_NUMERO', '')
        self.modo_simulacao = app.config.get('MODO_SIMULACAO', False)

        if self.account_sid and self.auth_token:
            self.cliente = Client(self.account_sid, self.auth_token)

    def _carregar_configuracoes_bd(self):
        """Carrega configurações da base de dados."""
        self.account_sid = obter_configuracao('TWILIO_SID', '')
        self.auth_token = obter_configuracao('TWILIO_TOKEN', '')
        self.numero_twilio = obter_configuracao('TWILIO_NUMERO', '')
        self.notificar_pais = obter_configuracao('notificar_pais', 'true') == 'true'

        if self.account_sid and self.auth_token:
            try:
                self.cliente = Client(self.account_sid, self.auth_token)
            except Exception as e:
                logger.error(f'Erro ao criar cliente Twilio: {e}')
                self.cliente = None

    def _formatar_whatsapp(self, numero: str) -> str:
        """
        Formata um número de telefone para o formato WhatsApp do Twilio.

        Args:
            numero: Número de telefone (ex: +258840000000)

        Returns:
            Número formatado (ex: whatsapp:+258840000000)
        """
        # Remover espaços e caracteres especiais
        numero = numero.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Adicionar + se não tiver
        if not numero.startswith('+'):
            # Assumir código do país +258 (Moçambique)
            if numero.startswith('8'):
                numero = '+258' + numero
            else:
                numero = '+' + numero

        return f'whatsapp:{numero}'

    def _enviar_whatsapp(self, destino: str, mensagem: str) -> dict:
        """
        Envia uma mensagem WhatsApp via Twilio.

        Args:
            destino: Número de telefone do destinatário
            mensagem: Texto da mensagem

        Returns:
            Dicionário com resultado do envio
        """
        resultado = {
            'sucesso': False,
            'sid': None,
            'erro': None,
        }

        # Modo simulação: apenas log
        if self.modo_simulacao:
            logger.info(f'[SIMULAÇÃO] WhatsApp para {destino}: {mensagem}')
            resultado['sucesso'] = True
            resultado['sid'] = 'SIMULADO'
            return resultado

        # Verificar se o cliente Twilio está configurado
        if not self.cliente:
            logger.warning('Cliente Twilio não configurado.')
            resultado['erro'] = 'Cliente Twilio não configurado.'
            return resultado

        if not self.numero_twilio:
            logger.warning('Número Twilio não configurado.')
            resultado['erro'] = 'Número Twilio não configurado.'
            return resultado

        try:
            destino_formatado = self._formatar_whatsapp(destino)
            remetente = self._formatar_whatsapp(self.numero_twilio)

            message = self.cliente.messages.create(
                body=mensagem,
                from_=remetente,
                to=destino_formatado,
            )

            resultado['sucesso'] = True
            resultado['sid'] = message.sid
            logger.info(f'WhatsApp enviado para {destino}: {message.sid}')

        except TwilioRestException as e:
            logger.error(f'Erro Twilio (WhatsApp): {e.msg}')
            resultado['erro'] = str(e.msg)

        except Exception as e:
            logger.error(f'Erro ao enviar WhatsApp: {e}')
            resultado['erro'] = str(e)

        return resultado

    def _enviar_sms(self, destino: str, mensagem: str) -> dict:
        """
        Envia um SMS via Twilio (fallback se WhatsApp falhar).

        Args:
            destino: Número de telefone do destinatário
            mensagem: Texto da mensagem

        Returns:
            Dicionário com resultado do envio
        """
        resultado = {
            'sucesso': False,
            'sid': None,
            'erro': None,
        }

        if self.modo_simulacao:
            logger.info(f'[SIMULAÇÃO] SMS para {destino}: {mensagem}')
            resultado['sucesso'] = True
            resultado['sid'] = 'SIMULADO'
            return resultado

        if not self.cliente:
            resultado['erro'] = 'Cliente Twilio não configurado.'
            return resultado

        try:
            message = self.cliente.messages.create(
                body=mensagem,
                from_=self.numero_twilio,
                to=destino,
            )

            resultado['sucesso'] = True
            resultado['sid'] = message.sid
            logger.info(f'SMS enviado para {destino}: {message.sid}')

        except TwilioRestException as e:
            logger.error(f'Erro Twilio (SMS): {e.msg}')
            resultado['erro'] = str(e.msg)

        except Exception as e:
            logger.error(f'Erro ao enviar SMS: {e}')
            resultado['erro'] = str(e)

        return resultado

    def notificar_entrada(self, nome_aluno: str, telefone_pai: str,
                          hora: datetime = None) -> dict:
        """
        Notifica o pai que o aluno entrou na escola.

        Args:
            nome_aluno: Nome do aluno
            telefone_pai: Número de telefone do pai
            hora: Data/hora da entrada (opcional)

        Returns:
            Resultado do envio
        """
        if not self.notificar_pais:
            logger.info('Notificações aos pais estão desativadas.')
            return {'sucesso': False, 'erro': 'Notificações desativadas.'}

        if not telefone_pai:
            logger.warning(f'Sem telefone para notificar entrada de {nome_aluno}.')
            return {'sucesso': False, 'erro': 'Telefone não cadastrado.'}

        if hora is None:
            hora = datetime.now()

        data_formatada = formatar_data(hora)
        hora_formatada = formatar_hora(hora)

        mensagem = (
            f'🏫 *SmartSchool Guard*\n\n'
            f'👤 *{nome_aluno}* entrou na escola.\n'
            f'📅 Data: {data_formatada}\n'
            f'⏰ Hora: {hora_formatada}\n\n'
            f'✅ Entrada registada com sucesso.'
        )

        logger.info(f'Enviando notificação de ENTRADA: {nome_aluno} para {telefone_pai}')

        # Tentar WhatsApp primeiro
        resultado = self._enviar_whatsapp(telefone_pai, mensagem)

        # Fallback para SMS
        if not resultado['sucesso']:
            logger.warning(f'WhatsApp falhou, tentando SMS...')
            resultado = self._enviar_sms(telefone_pai, mensagem)

        return resultado

    def notificar_saida(self, nome_aluno: str, telefone_pai: str,
                        hora: datetime = None) -> dict:
        """
        Notifica o pai que o aluno saiu da escola.

        Args:
            nome_aluno: Nome do aluno
            telefone_pai: Número de telefone do pai
            hora: Data/hora da saída (opcional)

        Returns:
            Resultado do envio
        """
        if not self.notificar_pais:
            return {'sucesso': False, 'erro': 'Notificações desativadas.'}

        if not telefone_pai:
            return {'sucesso': False, 'erro': 'Telefone não cadastrado.'}

        if hora is None:
            hora = datetime.now()

        data_formatada = formatar_data(hora)
        hora_formatada = formatar_hora(hora)

        mensagem = (
            f'🏫 *SmartSchool Guard*\n\n'
            f'👤 *{nome_aluno}* saiu da escola.\n'
            f'📅 Data: {data_formatada}\n'
            f'⏰ Hora: {hora_formatada}\n\n'
            f'👋 Até amanhã!'
        )

        logger.info(f'Enviando notificação de SAÍDA: {nome_aluno} para {telefone_pai}')

        resultado = self._enviar_whatsapp(telefone_pai, mensagem)

        if not resultado['sucesso']:
            resultado = self._enviar_sms(telefone_pai, mensagem)

        return resultado

    def notificar_alerta(self, tipo_alerta: str, descricao: str,
                         telefones: list = None) -> dict:
        """
        Envia notificação de alerta para administradores.

        Args:
            tipo_alerta: Tipo do alerta ('desconhecido', 'emergencia')
            descricao: Descrição do alerta
            telefones: Lista de números para notificar

        Returns:
            Resultado do envio
        """
        if telefones is None:
            # Buscar telefones dos administradores na BD
            telefones = self._obter_telefones_admin()

        if not telefones:
            return {'sucesso': False, 'erro': 'Nenhum telefone para notificar.'}

        agora = datetime.now()
        data_formatada = formatar_data(agora)
        hora_formatada = formatar_hora(agora)

        emoji = '🚨' if tipo_alerta == 'emergencia' else '⚠️'

        mensagem = (
            f'{emoji} *ALERTA - SmartSchool Guard*\n\n'
            f'Tipo: *{tipo_alerta.upper()}*\n'
            f'Descrição: {descricao}\n'
            f'📅 Data: {data_formatada}\n'
            f'⏰ Hora: {hora_formatada}\n\n'
            f'🔐 Aceda ao dashboard para mais detalhes.'
        )

        resultados = []
        for telefone in telefones:
            resultado = self._enviar_whatsapp(telefone, mensagem)
            if not resultado['sucesso']:
                resultado = self._enviar_sms(telefone, mensagem)
            resultados.append(resultado)

        return {
            'sucesso': any(r['sucesso'] for r in resultados),
            'total_enviados': sum(1 for r in resultados if r['sucesso']),
            'resultados': resultados,
        }

    def notificar_emergencia(self, descricao: str) -> dict:
        """
        Envia notificação de emergência para todos os administradores.

        Args:
            descricao: Descrição da emergência

        Returns:
            Resultado do envio
        """
        return self.notificar_alerta('emergencia', descricao)

    def _obter_telefones_admin(self) -> list:
        """
        Obtém a lista de telefones dos administradores da BD.

        Returns:
            Lista de números de telefone
        """
        try:
            from app.database import db
            from app.models import Utilizador

            # Por enquanto, retorna o número configurado no .env
            # Futuramente, pode buscar da tabela utilizadores
            return []
        except Exception:
            return []

    def enviar_teste(self, telefone: str) -> dict:
        """
        Envia uma mensagem de teste para verificar a configuração.

        Args:
            telefone: Número de telefone para o teste

        Returns:
            Resultado do envio
        """
        mensagem = (
            f'✅ *SmartSchool Guard*\n\n'
            f'Teste de notificação realizado com sucesso!\n'
            f'📅 {formatar_data(datetime.now())}\n'
            f'⏰ {formatar_hora(datetime.now())}\n\n'
            f'As notificações estão configuradas corretamente. 👍'
        )

        return self._enviar_whatsapp(telefone, mensagem)

    def notificar_resumo_diario(self, telefone: str, stats: dict) -> dict:
        """
        Envia um resumo diário de movimentação.

        Args:
            telefone: Número do destinatário
            stats: Dicionário com estatísticas do dia

        Returns:
            Resultado do envio
        """
        mensagem = (
            f'📊 *Resumo Diário - SmartSchool Guard*\n\n'
            f'📅 Data: {stats.get("data", "---")}\n'
            f'{"─" * 25}\n'
            f'🚶 Entradas: {stats.get("entradas", 0)}\n'
            f'🚶 Saídas: {stats.get("saidas", 0)}\n'
            f'👥 Visitantes: {stats.get("visitantes", 0)}\n'
            f'⚠️ Alertas: {stats.get("alertas", 0)}\n'
            f'{"─" * 25}\n'
            f'🏫 Tenha um bom dia!'
        )

        return self._enviar_whatsapp(telefone, mensagem)