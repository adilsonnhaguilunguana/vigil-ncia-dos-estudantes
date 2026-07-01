"""
Script para popular a base de dados com dados iniciais.

Executar uma vez após criar a BD:
    python -m app.seed

Cria:
- Configurações padrão do sistema
- Utilizadores padrão (admin e porteiro)
"""

from app import create_app
from app.database import db
from app.models import Configuracao, Utilizador
from werkzeug.security import generate_password_hash

# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================

CONFIGURACOES_INICIAIS = {
    # Linha virtual (zona de detecção)
    'linha_x1': '0',
    'linha_y1': '300',
    'linha_x2': '1280',
    'linha_y2': '300',

    # Reconhecimento facial
    'confianca_minima': '60',
    'qualidade_minima': '60',

    # Notificações
    'alerta_som': 'true',
    'notificar_pais': 'true',

    # Câmara IP (valor inicial, depois o utilizador muda pela web)
    'ip_camara': '192.168.1.100:8080',
}

# ============================================================
# UTILIZADORES PADRÃO
# ============================================================

UTILIZADORES_INICIAIS = [
    {
        'username': 'admin',
        'password': 'admin123',
        'role': 'admin',
    },
    {
        'username': 'porteiro',
        'password': 'porteiro123',
        'role': 'porteiro',
    },
]


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def popular():
    """Popula a base de dados com dados iniciais."""

    app = create_app()

    with app.app_context():
        print("=" * 55)
        print("  🏫 SmartSchool Guard - Populando BD")
        print("=" * 55)
        print()

        # Criar tabelas (se não existirem)
        db.create_all()
        print("✅ Tabelas verificadas/criadas.")
        print()

        # Inserir configurações iniciais
        print("📝 A inserir configurações iniciais...")
        config_criadas = 0
        for chave, valor in CONFIGURACOES_INICIAIS.items():
            if not Configuracao.query.filter_by(chave=chave).first():
                db.session.add(Configuracao(chave=chave, valor=valor))
                config_criadas += 1
                print(f"   ✅ {chave} = {valor}")
            else:
                print(f"   ⏭️  {chave} já existe, ignorado")

        db.session.commit()
        print(f"   📊 {config_criadas} configurações criadas.")
        print()

        # Inserir utilizadores padrão
        print("👤 A inserir utilizadores padrão...")
        users_criados = 0
        for user_data in UTILIZADORES_INICIAIS:
            if not Utilizador.query.filter_by(username=user_data['username']).first():
                utilizador = Utilizador(
                    username=user_data['username'],
                    password_hash=generate_password_hash(user_data['password']),
                    role=user_data['role'],
                )
                db.session.add(utilizador)
                users_criados += 1
                print(f"   ✅ {user_data['username']} ({user_data['role']})")
            else:
                print(f"   ⏭️  {user_data['username']} já existe, ignorado")

        db.session.commit()
        print(f"   📊 {users_criados} utilizadores criados.")
        print()

        # Mostrar credenciais
        print("=" * 55)
        print("  🔑 CREDENCIAIS DE ACESSO")
        print("=" * 55)
        print("  👤 Admin:    admin / admin123")
        print("  👤 Porteiro: porteiro / porteiro123")
        print("=" * 55)
        print()
        print("⚠️  Altere as senhas após o primeiro acesso!")
        print("✅ Base de dados populada com sucesso!")
        print()


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == '__main__':
    popular()