"""
Blueprint da Câmara IP.
Gere a configuração da câmara (telemóvel Android) via interface web.
O utilizador pode alterar o IP sem mexer no código.
"""

from flask import Blueprint, request, jsonify, session
from app.database import db
from app.models import Configuracao, HistoricoIP
from app.routes.auth import login_obrigatorio, admin_obrigatorio
from app.services.utils import (
    validar_ip,
    testar_conexao_camara,
    obter_configuracao,
    guardar_configuracao,
)

camara_bp = Blueprint('camara', __name__)


# ============================================================
# API: OBTER IP ATUAL DA CÂMARA
# ============================================================

@camara_bp.route('/api/camara')
@login_obrigatorio
def api_obter():
    """
    Retorna o IP atual da câmara e o status da conexão.
    """
    ip = obter_configuracao('ip_camara', 'Não configurado')
    online = testar_conexao_camara(ip) if ip != 'Não configurado' else False

    return jsonify({
        'ip': ip,
        'online': online,
        'status': 'online' if online else 'offline',
    })


# ============================================================
# API: TESTAR CONEXÃO COM A CÂMARA
# ============================================================

@camara_bp.route('/api/camara/testar', methods=['POST'])
@login_obrigatorio
def api_testar():
    """
    Testa se um IP de câmara está acessível.
    Usado pelo botão "Testar Ligação" na interface.

    Espera JSON: {"ip": "192.168.1.100:8080"}

    Resposta:
    {
        "ip": "192.168.1.100:8080",
        "online": true,
        "url_stream": "http://192.168.1.100:8080/video",
        "url_snapshot": "http://192.168.1.100:8080/shot.jpg",
        "tempo_resposta_ms": 245,
        "mensagem": "🟢 Câmara online!"
    }
    """
    import time
    from app.services.utils import testar_conexao_camara

    dados = request.get_json()

    if not dados or 'ip' not in dados:
        return jsonify({'erro': 'IP não fornecido'}), 400

    ip = dados['ip'].strip()

    # Validar formato do IP
    if not validar_ip(ip):
        return jsonify({
            'online': False,
            'erro': 'Formato de IP inválido.',
            'ajuda': 'Exemplo correto: 192.168.1.100:8080'
        }), 400

    # Medir tempo de resposta
    inicio = time.time()
    online = testar_conexao_camara(ip)
    tempo_resposta = int((time.time() - inicio) * 1000)  # ms

    # Construir URLs
    url_stream = f'http://{ip}/video'
    url_snapshot = f'http://{ip}/shot.jpg'

    if online:
        return jsonify({
            'ip': ip,
            'online': True,
            'url_stream': url_stream,
            'url_snapshot': url_snapshot,
            'tempo_resposta_ms': tempo_resposta,
            'mensagem': f'🟢 Câmara online! (resposta em {tempo_resposta}ms)',
        })
    else:
        return jsonify({
            'ip': ip,
            'online': False,
            'url_stream': url_stream,
            'url_snapshot': url_snapshot,
            'tempo_resposta_ms': tempo_resposta,
            'erro': 'Não foi possível ligar à câmara.',
            'dicas': [
                'Verifique se a app IP Webcam está aberta no telemóvel.',
                'Verifique se o telemóvel e o computador estão na mesma rede Wi-Fi.',
                'Confirme se o IP mostrado na app está correto.',
                'Toque em "Start Server" na app IP Webcam.',
            ],
        }), 200


# ============================================================
# API: GUARDAR IP DA CÂMARA
# ============================================================

@camara_bp.route('/api/camara/guardar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_guardar():
    """
    Guarda o IP da câmara na base de dados.
    Regista no histórico de IPs.

    Espera JSON: {"ip": "192.168.1.100:8080"}
    """
    dados = request.get_json()

    if not dados or 'ip' not in dados:
        return jsonify({'erro': 'IP não fornecido'}), 400

    ip = dados['ip'].strip()

    # Validar formato
    if not validar_ip(ip):
        return jsonify({
            'erro': 'Formato de IP inválido.',
            'exemplo': '192.168.1.100:8080'
        }), 400

    # Testar conexão primeiro
    online = testar_conexao_camara(ip)

    # Guardar na tabela configuracoes
    guardar_configuracao('ip_camara', ip)

    # Registar no histórico
    historico = HistoricoIP(
        ip=ip,
        adicionado_por=session.get('usuario_nome', 'Sistema'),
    )
    db.session.add(historico)
    db.session.commit()

    if online:
        return jsonify({
            'sucesso': True,
            'ip': ip,
            'online': True,
            'mensagem': f'✅ Câmara configurada com sucesso! IP: {ip}'
        })
    else:
        return jsonify({
            'sucesso': True,
            'ip': ip,
            'online': False,
            'mensagem': f'⚠️ IP guardado, mas a câmara não está a responder. Verifique a ligação.'
        })


# ============================================================
# API: HISTÓRICO DE IPs
# ============================================================

@camara_bp.route('/api/camara/historico')
@login_obrigatorio
def api_historico():
    """
    Retorna o histórico de IPs da câmara.
    """
    limite = request.args.get('limite', 10, type=int)

    historico = HistoricoIP.query.order_by(
        HistoricoIP.data.desc()
    ).limit(limite).all()

    return jsonify([
        {
            'id': h.id,
            'ip': h.ip,
            'adicionado_por': h.adicionado_por,
            'data': h.data.strftime('%d/%m/%Y %H:%M:%S') if h.data else None,
        }
        for h in historico
    ])


# ============================================================
# API: OBTER FRAME ATUAL (SNAPSHOT)
# ============================================================

@camara_bp.route('/api/camara/snapshot')
@login_obrigatorio
def api_snapshot():
    """
    Obtém um frame atual da câmara e retorna como imagem.
    Útil para pré-visualização na página de configuração.
    """
    import requests
    from flask import Response

    ip = obter_configuracao('ip_camara', '')

    if not ip:
        return jsonify({'erro': 'Câmara não configurada'}), 404

    url = f'http://{ip}/shot.jpg'

    try:
        resposta = requests.get(url, timeout=3)
        if resposta.status_code == 200:
            return Response(
                resposta.content,
                mimetype='image/jpeg',
                headers={'Cache-Control': 'no-cache'}
            )
        else:
            return jsonify({'erro': f'Erro na câmara: HTTP {resposta.status_code}'}), 502
    except requests.ConnectionError:
        return jsonify({'erro': 'Câmara offline'}), 502
    except requests.Timeout:
        return jsonify({'erro': 'Timeout ao ligar à câmara'}), 502


# ============================================================
# API: URL DO STREAM MJPEG
# ============================================================

@camara_bp.route('/api/camara/stream-url')
@login_obrigatorio
def api_stream_url():
    """
    Retorna a URL completa do stream MJPEG da câmara.
    Usado pelo sistema de reconhecimento.
    """
    ip = obter_configuracao('ip_camara', '')

    if not ip:
        return jsonify({'erro': 'Câmara não configurada'}), 404

    return jsonify({
        'stream_url': f'http://{ip}/video',
        'snapshot_url': f'http://{ip}/shot.jpg',
        'ip': ip,
    })


# ============================================================
# API: VERIFICAR SE A CÂMARA ESTÁ CONFIGURADA
# ============================================================

@camara_bp.route('/api/camara/configurada')
@login_obrigatorio
def api_configurada():
    """
    Verifica rapidamente se a câmara está configurada e online.
    Usado pelo dashboard para mostrar status.
    """
    ip = obter_configuracao('ip_camara', '')

    if not ip:
        return jsonify({
            'configurada': False,
            'online': False,
            'mensagem': 'Câmara não configurada. Acesse Configurações > Câmara.'
        })

    online = testar_conexao_camara(ip)

    return jsonify({
        'configurada': True,
        'ip': ip,
        'online': online,
        'mensagem': '🟢 Câmara online' if online else '🔴 Câmara offline',
    })


# ============================================================
# API: LISTA DE APPS DE CÂMARA IP COMPATÍVEIS
# ============================================================

@camara_bp.route('/api/camara/apps-compativeis')
def api_apps_compativeis():
    """
    Retorna uma lista de apps Android compatíveis.
    Útil para mostrar ajuda ao utilizador.
    """
    return jsonify({
        'apps': [
            {
                'nome': 'IP Webcam',
                'link': 'https://play.google.com/store/apps/details?id=com.pas.webcam',
                'gratis': True,
                'recomendada': True,
                'stream': '/video',
                'snapshot': '/shot.jpg',
            },
            {
                'nome': 'DroidCam',
                'link': 'https://play.google.com/store/apps/details?id=com.dev47apps.droidcam',
                'gratis': True,
                'recomendada': False,
                'stream': '/video',
                'snapshot': '/shot.jpg',
            },
            {
                'nome': 'Câmera IP',
                'link': 'https://play.google.com/store/apps/details?id=com.shenyaocn.android.webcam',
                'gratis': True,
                'recomendada': False,
                'stream': '/video',
                'snapshot': '/photo.jpg',
            },
        ],
        'instrucoes': [
            '1. Instale uma das apps acima no telemóvel Android.',
            '2. Ligue o telemóvel e o computador à mesma rede Wi-Fi.',
            '3. Abra a app e toque em "Start Server".',
            '4. Copie o IP mostrado no ecrã do telemóvel.',
            '5. Cole o IP nesta página e clique em "Testar Ligação".',
        ]
    })