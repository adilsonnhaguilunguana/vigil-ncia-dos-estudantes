"""
Inicialização da base de dados com SQLAlchemy.
Fornece o objeto db e funções auxiliares.
"""

from flask_sqlalchemy import SQLAlchemy

# Objeto global da base de dados
db = SQLAlchemy()


def init_db(app):
    """Inicializa a base de dados com a aplicação Flask."""
    db.init_app(app)