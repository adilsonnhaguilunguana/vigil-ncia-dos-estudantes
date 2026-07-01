"""
Regista todos os blueprints (rotas) da aplicação.
Cada blueprint representa um módulo funcional do sistema.
"""


def register_all_blueprints(app):
    """
    Regista todos os blueprints na aplicação Flask.

    Args:
        app: Aplicação Flask
    """

    # Importar blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.alunos import alunos_bp
    from app.routes.registos import registos_bp
    from app.routes.alertas import alertas_bp
    from app.routes.visitantes import visitantes_bp
    from app.routes.relatorios import relatorios_bp
    from app.routes.configuracoes import configuracoes_bp
    from app.routes.zona import zona_bp
    from app.routes.camara import camara_bp

    # Registar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(registos_bp)
    app.register_blueprint(alertas_bp)
    app.register_blueprint(visitantes_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(configuracoes_bp)
    app.register_blueprint(zona_bp)
    app.register_blueprint(camara_bp)