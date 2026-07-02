"""
SmartSchool Guard
Ponto de entrada da aplicação.
Inicia o servidor Flask com todas as configurações.
"""

import os
from app import create_app

# Cria a aplicação usando a factory function
app = create_app()

if __name__ == '__main__':
    # Obtém a porta do ambiente ou usa 5000 como padrão
    port = int(os.getenv('FLASK_PORT', 5000))
    
    # Modo debug: ativo por padrão no desenvolvimento
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print("=" * 55)
    print("  🏫 SmartSchool Guard")
    print("  Sistema Inteligente de Monitoramento Escolar")
    print("=" * 55)
    print(f"  🌐 Servidor: http://0.0.0.0:{port}")
    print(f"  🐛 Debug: {'ligado' if debug else 'desligado'}")
    print("=" * 55)
    print("  ⚠️  Ctrl+C para parar o servidor")
    print("=" * 55)
    print()
    
    # Inicia o servidor Flask
    app.run(
        host='0.0.0.0',    # Acessível de qualquer IP na rede local
        port=port,
        debug=debug
    )