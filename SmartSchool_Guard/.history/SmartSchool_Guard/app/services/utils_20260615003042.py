"""
Funções auxiliares e utilitários para o sistema SmartSchool Guard.

Inclui:
- Validações (IP, formato de dados)
- Manipulação de imagens (qualidade, redimensionamento)
- Formatação de data/hora
- Geração de PINs e códigos
- Leitura/escrita de configurações da BD
- Logging do sistema
"""

import os
import re
import cv2
import logging
import random
import string
from datetime import datetime
from PIL import Image
import numpy as np

# ============================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('smartschool.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# VALIDAÇÕES
# ============================================================

def validar_ip(ip: str) -> bool:
    """
    Valida se uma string é um IP:porta válido.

    Exemplos válidos:
        192.168.1.100
        192.168.1.100:8080
        10.0.0.1:5000

    Args:
        ip: String com IP e porta opcional

    Returns:
        True se for válido, False caso contrário
    """
    # Padrão: IP (0-255.0-255.0-255.0-255) + :porta opcional (0-65535)
    padrao = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?$'
    match = re.match(padrao, ip)

    if not match:
        return False

    # Validar cada octeto do IP
    octetos = match.group(1).split('.')
    for octeto in octetos:
        if int(octeto) > 255:
            return False

    # Validar porta (se existir)
    if match.group(2):
        porta = int(match.group(2).replace(':', ''))
        if porta > 65535:
            return False

    return True


def validar_telefone(telefone: str) -> bool:
    """
    Valida formato de número de telefone.
    Aceita formatos: +258XXXXXXXXX, 8XXXXXXXX, etc.

    Args:
        telefone: Número de telefone

    Returns:
        True se for válido
    """
    # Remove espaços e traços
    telefone = telefone.replace(' ', '').replace('-', '')
    padrao = r'^(\+?\d{8,15})$'
    return bool(re.match(padrao, telefone))


def validar_numero_aluno(numero: str) -> bool:
    """
    Valida o número do aluno (apenas letras e números).

    Args:
        numero: Número do aluno

    Returns:
        True se for válido
    """
    return bool(re.match(r'^[a-zA-Z0-9]{1,20}$', numero))


# ============================================================
# MANIPULAÇÃO DE IMAGENS
# ============================================================

def verificar_qualidade_foto(caminho_foto: str) -> dict:
    """
    Avalia a qualidade de uma foto para cadastro.

    Critérios:
    - Nitidez (Laplacian variance > 100)           → 25 pontos
    - Brilho (média pixel entre 80-200)             → 25 pontos
    - Rosto detectado (Haar Cascade)                → 35 pontos
    - Resolução mínima 300x300                      → 15 pontos

    Args:
        caminho_foto: Caminho do ficheiro da foto

    Returns:
        Dicionário com pontuação total e detalhes
    """
    resultado = {
        'pontuacao_total': 0,
        'nitidez': 0,
        'brilho': 0,
        'rosto_detectado': 0,
        'resolucao': 0,
        'aprovada': False,
        'dicas': []
    }

    # Carregar imagem
    img = cv2.imread(caminho_foto)
    if img is None:
        resultado['dicas'].append('❌ Não foi possível abrir a imagem.')
        return resultado

    altura, largura = img.shape[:2]

    # 1. Verificar resolução (15 pontos)
    if altura >= 300 and largura >= 300:
        resultado['resolucao'] = 15
    else:
        resultado['dicas'].append(
            f'📏 Resolução baixa ({largura}x{altura}). Mínimo: 300x300.'
        )

    # 2. Verificar nitidez - Laplacian variance (25 pontos)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var > 100:
        resultado['nitidez'] = 25
    elif laplacian_var > 50:
        resultado['nitidez'] = 15
    else:
        resultado['dicas'].append(
            '🔍 Foto desfocada. Segure o telemóvel mais firme.'
        )

    # 3. Verificar brilho (25 pontos)
    brilho_medio = np.mean(gray)
    if 80 <= brilho_medio <= 200:
        resultado['brilho'] = 25
    elif 50 <= brilho_medio <= 230:
        resultado['brilho'] = 15
    else:
        if brilho_medio < 50:
            resultado['dicas'].append(
                '💡 Foto muito escura. Procure melhor iluminação.'
            )
        else:
            resultado['dicas'].append(
                '☀️ Foto muito clara. Evite luz direta no rosto.'
            )

    # 4. Verificar rosto com Haar Cascade (35 pontos)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    rostos = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    if len(rostos) == 1:
        resultado['rosto_detectado'] = 35
    elif len(rostos) > 1:
        resultado['rosto_detectado'] = 20
        resultado['dicas'].append(
            '👥 Múltiplos rostos detectados. Apenas uma pessoa na foto.'
        )
    else:
        resultado['dicas'].append(
            '😶 Nenhum rosto detectado. Centralize o rosto na câmara.'
        )

    # Calcular pontuação total
    resultado['pontuacao_total'] = (
        resultado['nitidez'] +
        resultado['brilho'] +
        resultado['rosto_detectado'] +
        resultado['resolucao']
    )

    # Verificar se foi aprovada
    resultado['aprovada'] = resultado['pontuacao_total'] >= 60

    return resultado


def redimensionar_imagem(caminho_entrada: str, caminho_saida: str,
                         largura: int = 640, altura: int = 480):
    """
    Redimensiona uma imagem mantendo a proporção.

    Args:
        caminho_entrada: Imagem original
        caminho_saida: Imagem redimensionada
        largura: Largura máxima
        altura: Altura máxima
    """
    img = Image.open(caminho_entrada)
    img.thumbnail((largura, altura), Image.Resampling.LANCZOS)
    img.save(caminho_saida, quality=85)


def salvar_frame(frame, pasta: str, prefixo: str = 'frame') -> str:
    """
    Guarda um frame da câmara como imagem.

    Args:
        frame: Array numpy (OpenCV)
        pasta: Pasta onde guardar
        prefixo: Prefixo do nome do ficheiro

    Returns:
        Caminho do ficheiro guardado
    """
    os.makedirs(pasta, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    nome_ficheiro = f'{prefixo}_{timestamp}.jpg'
    caminho = os.path.join(pasta, nome_ficheiro)
    cv2.imwrite(caminho, frame)
    return caminho


# ============================================================
# FORMATAÇÃO DE DATA/HORA
# ============================================================

def formatar_data_hora(data: datetime) -> str:
    """Formata data e hora no formato legível."""
    if data is None:
        return '---'
    return data.strftime('%d/%m/%Y %H:%M:%S')


def formatar_data(data: datetime) -> str:
    """Formata data no formato legível."""
    if data is None:
        return '---'
    return data.strftime('%d/%m/%Y')


def formatar_hora(data: datetime) -> str:
    """Formata hora no formato legível."""
    if data is None:
        return '---'
    return data.strftime('%H:%M:%S')


def data_pt(data: datetime) -> str:
    """Formata data por extenso em português."""
    if data is None:
        return '---'

    meses = [
        'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
    ]

    dia_semana = [
        'Segunda-feira', 'Terça-feira', 'Quarta-feira',
        'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ]

    return (
        f'{dia_semana[data.weekday()]}, '
        f'{data.day} de {meses[data.month - 1]} de {data.year}'
    )


def tempo_passado(data: datetime) -> str:
    """
    Retorna o tempo passado desde uma data em formato legível.

    Exemplos: "agora mesmo", "5 minutos atrás", "2 horas atrás"
    """
    if data is None:
        return '---'

    agora = datetime.now()
    diferenca = agora - data
    segundos = diferenca.total_seconds()

    if segundos < 60:
        return 'agora mesmo'
    elif segundos < 3600:
        minutos = int(segundos / 60)
        return f'{minutos} minuto{"s" if minutos > 1 else ""} atrás'
    elif segundos < 86400:
        horas = int(segundos / 3600)
        return f'{horas} hora{"s" if horas > 1 else ""} atrás'
    else:
        dias = int(segundos / 86400)
        return f'{dias} dia{"s" if dias > 1 else ""} atrás'


# ============================================================
# GERAÇÃO DE CÓDIGOS
# ============================================================

def gerar_pin(tamanho: int = 4) -> str:
    """
    Gera um PIN numérico aleatório.

    Args:
        tamanho: Número de dígitos (padrão: 4)

    Returns:
        PIN como string
    """
    return ''.join(random.choices(string.digits, k=tamanho))


def gerar_nome_ficheiro(prefixo: str = 'arquivo', extensao: str = 'jpg') -> str:
    """
    Gera um nome de ficheiro único com timestamp.

    Args:
        prefixo: Prefixo do ficheiro
        extensao: Extensão do ficheiro

    Returns:
        Nome do ficheiro
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f'{prefixo}_{timestamp}.{extensao}'


# ============================================================
# CONFIGURAÇÕES DA BASE DE DADOS
# ============================================================

def obter_configuracao(chave: str, default=None):
    """
    Obtém uma configuração da tabela configuracoes.

    Args:
        chave: Chave da configuração
        default: Valor padrão se não existir

    Returns:
        Valor da configuração ou default
    """
    from app.database import db
    from app.models import Configuracao

    config = Configuracao.query.filter_by(chave=chave).first()
    return config.valor if config else default


def guardar_configuracao(chave: str, valor) -> bool:
    """
    Guarda ou atualiza uma configuração na tabela configuracoes.

    Args:
        chave: Chave da configuração
        valor: Valor a guardar

    Returns:
        True se guardou com sucesso
    """
    from app.database import db
    from app.models import Configuracao
    from datetime import datetime

    try:
        config = Configuracao.query.filter_by(chave=chave).first()
        if config:
            config.valor = str(valor)
            config.atualizado_em = datetime.now()
        else:
            config = Configuracao(chave=chave, valor=str(valor))
            db.session.add(config)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao guardar configuração {chave}: {e}')
        return False


# ============================================================
# FUNÇÕES DE REDE
# ============================================================

def testar_conexao_camara(ip: str, timeout: int = 3) -> bool:
    """
    Testa se a câmara IP está acessível.

    Tenta obter um frame da câmara via HTTP.

    Args:
        ip: IP:porta da câmara
        timeout: Tempo máximo de espera em segundos

    Returns:
        True se a câmara respondeu
    """
    import requests

    url = f'http://{ip}/shot.jpg'
    try:
        resposta = requests.get(url, timeout=timeout)
        return resposta.status_code == 200
    except requests.RequestException:
        return False


def testar_conexao_esp(ip: str, token: str = '', timeout: int = 3) -> dict:
    """
    Testa se o ESP8266 está acessível.

    Args:
        ip: IP do ESP8266
        token: Token de segurança
        timeout: Tempo máximo de espera

    Returns:
        Dicionário com status e dados
    """
    import requests

    url = f'http://{ip}/status'
    headers = {'Authorization': f'Bearer {token}'} if token else {}

    try:
        resposta = requests.get(url, headers=headers, timeout=timeout)
        if resposta.status_code == 200:
            return {'online': True, 'dados': resposta.json()}
        return {'online': False, 'erro': f'HTTP {resposta.status_code}'}
    except requests.ConnectionError:
        return {'online': False, 'erro': 'Sem conexão'}
    except requests.Timeout:
        return {'online': False, 'erro': 'Timeout'}
    except Exception as e:
        return {'online': False, 'erro': str(e)}