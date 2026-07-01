import os

# Lista de pastas a criar
pastas = [
    "alunos",
    "frames",
    "embeddings",
    "templates",
    "static/css",
    "static/js",
    "static/img",
    "arduino",
    "docs",
]

# Lista de ficheiros a criar
ficheiros = [
    # Python
    "run.py", "config.py", "database.py", "models.py", "seed.py",
    "cadastro.py", "reconhecimento.py", "zona_deteccao.py",
    "notificacoes.py", "esp_controlo.py", "utils.py", "app.py",
    # Configuração
    ".env", ".gitignore", "requirements.txt", "README.md",
    # Templates
    "templates/base.html", "templates/login.html",
    "templates/dashboard.html", "templates/alunos.html",
    "templates/cadastro.html", "templates/aluno_detalhes.html",
    "templates/registos.html", "templates/alertas.html",
    "templates/alerta_detalhes.html", "templates/visitantes.html",
    "templates/visitante_cadastro.html", "templates/relatorios.html",
    "templates/configuracoes.html", "templates/configurar_zona.html",
    "templates/configurar_camara.html", "templates/erro.html",
    # Estáticos
    "static/css/style.css",
    "static/js/main.js", "static/js/dashboard.js",
    "static/js/cadastro.js", "static/js/zona.js",
    "static/js/camara.js", "static/js/alertas.js",
    "static/js/relatorios.js",
    # Arduino
    "arduino/smartschool.ino", "arduino/config_wifi.h",
    "arduino/README.md",
    # .gitkeep
    "alunos/.gitkeep", "frames/.gitkeep", "embeddings/.gitkeep",
]

print("📁 A criar estrutura do SmartSchool Guard...")

# Criar pastas
for pasta in pastas:
    os.makedirs(pasta, exist_ok=True)
    print(f"  📂 {pasta}/")

# Criar ficheiros vazios
for ficheiro in ficheiros:
    with open(ficheiro, 'w', encoding='utf-8') as f:
        pass  # cria ficheiro vazio
    print(f"  📄 {ficheiro}")

print("\n✅ Estrutura criada com sucesso!")
print(f"   Total: {len(pastas)} pastas, {len(ficheiros)} ficheiros")