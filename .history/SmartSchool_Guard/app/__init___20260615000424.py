"""
Factory function da aplicação Flask.
Cria e configura a aplicação com todos os blueprints e extensões.
"""

from flask import Flask
from app.config import Config
from app.database import db, init_db


def create_app(config_class=Config) -> Flask:
    """
    Cria e configura a aplicação Flask.

    Args:
        config_class: Classe de configuração (padrão: Config)

    Returns:
        Flask: Aplicação Flask configurada
    """
    app = Flask(__name__)

    # Carregar configurações
    app.config.from_object(config_class)

    # Inicializar a base de dados
    init_db(app)

    # Registar todos os blueprints (rotas)
    from app.routes import register_all_blueprints
    register_all_blueprints(app)

    # Registar tratamento de erros
    register_error_handlers(app)

    # Criar pastas de uploads se não existirem
    create_upload_folders(app)

    # Criar tabelas na BD se não existirem
    with app.app_context():
        db.create_all()

    return app


def register_error_handlers(app: Flask):
    """Regista handlers para páginas de erro."""

    @app.errorhandler(404)
    def page_not_found(error):
        return {'erro': 'Página não encontrada', 'codigo': 404}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'erro': 'Erro interno do servidor', 'codigo': 500}, 500

    @app.errorhandler(403)
    def forbidden(error):
        return {'erro': 'Acesso proibido', 'codigo': 403}, 403


def create_upload_folders(app: Flask):
    """Cria as pastas de uploads se não existirem."""
    import os
    pastas = [
        app.config.get('UPLOAD_FOLDER', 'uploads'),
        app.config.get('ALUNOS_FOLDER', 'uploads/alunos'),
        app.config.get('FRAMES_FOLDER', 'uploads/frames'),
        app.config.get('EMBEDDINGS_FOLDER', 'uploads/embeddings'),
    ]
    for pasta in pastas:
        os.makedirs(pasta, exist_ok=True)