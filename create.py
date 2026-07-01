"""
Script para criar apenas a estrutura de pastas e ficheiros vazios.
Não adiciona conteúdo — só cria os ficheiros em branco.
A pasta venv já existe e não é tocada.
"""

import os

# Nome do projeto
NOME_PROJETO = "SmartSchool_Guard"
CAMINHO_BASE = os.path.join(os.getcwd(), NOME_PROJETO)

# Pastas a criar (venv não está nesta lista porque já existe)
PASTAS = [
    "app",
    "app/routes",
    "app/services",
    "app/templates",
    "app/static",
    "app/static/css",
    "app/static/js",
    "app/static/img",
    "uploads",
    "uploads/alunos",
    "uploads/frames",
    "uploads/embeddings",
    "arduino",
    "docs",
]

# Ficheiros vazios a criar
FICHEIROS = [
    # Raiz
    ".env",
    ".gitignore",
    "requirements.txt",
    "README.md",
    "run.py",

    # App
    "app/__init__.py",
    "app/config.py",
    "app/database.py",
    "app/models.py",
    "app/seed.py",

    # Rotas
    "app/routes/__init__.py",
    "app/routes/auth.py",
    "app/routes/dashboard.py",
    "app/routes/alunos.py",
    "app/routes/registos.py",
    "app/routes/alertas.py",
    "app/routes/visitantes.py",
    "app/routes/relatorios.py",
    "app/routes/configuracoes.py",
    "app/routes/zona.py",
    "app/routes/camara.py",

    # Serviços
    "app/services/__init__.py",
    "app/services/cadastro.py",
    "app/services/reconhecimento.py",
    "app/services/zona_deteccao.py",
    "app/services/notificacoes.py",
    "app/services/esp_controlo.py",
    "app/services/utils.py",

    # Templates
    "app/templates/base.html",
    "app/templates/login.html",
    "app/templates/dashboard.html",
    "app/templates/alunos.html",
    "app/templates/cadastro.html",
    "app/templates/aluno_detalhes.html",
    "app/templates/registos.html",
    "app/templates/alertas.html",
    "app/templates/alerta_detalhes.html",
    "app/templates/visitantes.html",
    "app/templates/visitante_cadastro.html",
    "app/templates/relatorios.html",
    "app/templates/configuracoes.html",
    "app/templates/configurar_zona.html",
    "app/templates/configurar_camara.html",
    "app/templates/erro.html",

    # CSS
    "app/static/css/style.css",

    # JavaScript
    "app/static/js/main.js",
    "app/static/js/dashboard.js",
    "app/static/js/cadastro.js",
    "app/static/js/zona.js",
    "app/static/js/camara.js",
    "app/static/js/alertas.js",
    "app/static/js/relatorios.js",

    # .gitkeep para pastas vazias
    "uploads/alunos/.gitkeep",
    "uploads/frames/.gitkeep",
    "uploads/embeddings/.gitkeep",

    # Arduino
    "arduino/smartschool.ino",
    "arduino/config_wifi.example.h",
    "arduino/README.md",
]


def criar():
    print("=" * 50)
    print("  SmartSchool Guard - Criar Estrutura")
    print("=" * 50)
    print()

    # Verificar se a pasta já existe
    if os.path.exists(CAMINHO_BASE):
        print(f"⚠️  A pasta '{NOME_PROJETO}' já existe.")
        resposta = input("   Continuar mesmo assim? (s/n): ")
        if resposta.lower() != 's':
            print("   ❌ Cancelado.")
            return

    # Criar pastas
    print("📁 A criar pastas...")
    for pasta in PASTAS:
        caminho = os.path.join(CAMINHO_BASE, pasta)
        os.makedirs(caminho, exist_ok=True)
        print(f"   ✅ {pasta}")

    print()
    print("📄 A criar ficheiros vazios...")
    contador = 0
    for ficheiro in FICHEIROS:
        caminho = os.path.join(CAMINHO_BASE, ficheiro)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'w', encoding='utf-8') as f:
            pass  # ficheiro vazio
        contador += 1
        print(f"   ✅ {ficheiro}")

    print()
    print("=" * 50)
    print("  ✅ ESTRUTURA CRIADA COM SUCESSO!")
    print(f"     📁 Pastas: {len(PASTAS)}")
    print(f"     📄 Ficheiros: {contador}")
    print(f"     📍 Localização: {CAMINHO_BASE}")
    print("=" * 50)
    print()
    print("  Nota: A pasta 'venv' já existia e não foi alterada.")
    print()
    print(f"  cd {NOME_PROJETO}")
    print("  code .")
    print()


if __name__ == "__main__":
    criar()