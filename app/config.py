"""
Configurações da aplicação SmartSchool Guard.
Carrega todas as variáveis do ficheiro .env usando python-dotenv.
"""

import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()


class Config:
    """Classe base de configuração."""

    # ==========================================
    # FLASK
    # ==========================================
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave-padrao-insegura')

    # ==========================================
    # BASE DE DADOS POSTGRESQL
    # ==========================================
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'vigilancia')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # URI de conexão (formato: postgresql://user:pass@host:port/dbname)
    SQLALCHEMY_DATABASE_URI = (
        f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==========================================
    # CÂMARA IP (telemóvel Android)
    # ==========================================
    IP_CAMARA_PADRAO = os.getenv('IP_CAMARA_PADRAO', '192.168.1.100:8080')

    # ==========================================
    # ESP8266
    # ==========================================
    ESP_IP = os.getenv('ESP_IP', '192.168.1.200')
    TOKEN_ESP = os.getenv('TOKEN_ESP', '')

    # ==========================================
    # RECONHECIMENTO FACIAL
    # ==========================================
    CONFIANCA_MINIMA = int(os.getenv('CONFIANCA_MINIMA', '60'))
    QUALIDADE_MINIMA = int(os.getenv('QUALIDADE_MINIMA', '60'))
    MODELO_FACIAL = os.getenv('MODELO_FACIAL', 'VGG-Face')

    # ==========================================
    # TWILIO (notificações WhatsApp/SMS)
    # ==========================================
    TWILIO_SID = os.getenv('TWILIO_SID', '')
    TWILIO_TOKEN = os.getenv('TWILIO_TOKEN', '')
    TWILIO_NUMERO = os.getenv('TWILIO_NUMERO', '')

    # ==========================================
    # MODO SIMULAÇÃO
    # ==========================================
    MODO_SIMULACAO = os.getenv('MODO_SIMULACAO', 'false').lower() == 'true'

    # ==========================================
    # UPLOADS
    # ==========================================
    # Caminho absoluto da pasta uploads
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'uploads'
    )
    ALUNOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'alunos')
    FRAMES_FOLDER = os.path.join(UPLOAD_FOLDER, 'frames')
    EMBEDDINGS_FOLDER = os.path.join(UPLOAD_FOLDER, 'embeddings')