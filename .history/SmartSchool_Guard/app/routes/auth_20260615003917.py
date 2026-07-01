"""
Blueprint de autenticação.
Gere login, logout e proteção de rotas.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from datetime import datetime
from app.models import Utilizador
from app.database import db

auth_bp = Blueprint('auth', __name__)


# ============================================================
# ROTA: LOGIN
# ============================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login.
    GET  → mostra o formulário
    POST → processa as credenciais
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validar campos preenchidos
        if not username or not password:
            flash('⚠️ Preencha todos os campos.', 'warning')
            return render_template('login.html')

        # Procurar utilizador na BD
        utilizador = Utilizador.query.filter_by(username=username).first()

        # Verificar credenciais
        if utilizador and check_password_hash(utilizador.password_hash, password):
            if not utilizador.activo:
                flash('⛔ Conta desativada. Contacte o administrador.', 'danger')
                return render_template('login.html')

            # Criar sessão
            session['usuario_id'] = utilizador.id
            session['usuario_nome'] = utilizador.username
            session['usuario_role'] = utilizador.role

            # Atualizar último acesso
            utilizador.ultimo_acesso = datetime.now()
            db.session.commit()

            flash(f'👋 Bem-vindo, {utilizador.username}!', 'success')
            return redirect(url_for('dashboard.index'))

        else:
            flash('❌ Username ou senha incorretos.', 'danger')

    return render_template('login.html')


# ============================================================
# ROTA: LOGOUT
# ============================================================

@auth_bp.route('/logout')
def logout():
    """Termina a sessão do utilizador."""
    session.clear()
    flash('👋 Sessão terminada com sucesso.', 'info')
    return redirect(url_for('auth.login'))


# ============================================================
# DECORATOR: EXIGIR LOGIN
# ============================================================

def login_obrigatorio(f):
    """
    Decorator para proteger rotas que exigem autenticação.
    Se o utilizador não estiver logado, redireciona para /login.

    Uso:
        @auth_bp.route('/rota-protegida')
        @login_obrigatorio
        def rota_protegida():
            ...
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('🔒 Faça login para aceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# DECORATOR: EXIGIR ADMIN
# ============================================================

def admin_obrigatorio(f):
    """
    Decorator para proteger rotas que exigem role='admin'.

    Uso:
        @auth_bp.route('/rota-admin')
        @login_obrigatorio
        @admin_obrigatorio
        def rota_admin():
            ...
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('usuario_role') != 'admin':
            flash('⛔ Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)

    return decorated_function