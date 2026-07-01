"""
Blueprint de Configurações.
Gere as configurações gerais do sistema via interface web.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from app.database import db
from app.models import Configuracao, HistoricoIP
from app.routes.auth import login_obrigatorio, admin_obrigatorio
from app.services.utils import guardar_configuracao, obter_configuracao

configuracoes_bp = Blueprint('configuracoes', __name__)


# ============================================================
# ROTA: PÁGINA DE CONFIGURAÇÕES
# ============================================================

@configuracoes_bp.route('/configuracoes')
@login_obrigatorio
@admin_obrigatorio
def index():
    """
    Página principal de configurações do sistema.
    Mostra todas as configurações organizadas por categorias.
    """
    # Buscar todas as configurações da BD
    todas = Configuracao.query.all()
    configs = {c.chave: c.valor for c in todas}

    return render_template(
        'configuracoes.html',
        configs=configs,
    )


# ============================================================
# API: OBTER TODAS AS CONFIGURAÇÕES
# ============================================================

@configuracoes_bp.route('/api/configuracoes')
@login_obrigatorio
def api_obter_todas():
    """
    Retorna todas as configurações em JSON.
    """
    todas = Configuracao.query.all()
    return jsonify([
        {
            'id': c.id,
            'chave': c.chave,
            'valor': c.valor,
            'atualizado_em': c.atualizado_em.strftime('%d/%m/%Y %H:%M:%S') if c.atualizado_em else None,
        }
        for c in todas
    ])


# ============================================================
# API: OBTER UMA CONFIGURAÇÃO ESPECÍFICA
# ============================================================

@configuracoes_bp.route('/api/configuracoes/<chave>')
@login_obrigatorio
def api_obter(chave):
    """
    Retorna uma configuração específica em JSON.
    """
    valor = obter_configuracao(chave)
    if valor is not None:
        return jsonify({'chave': chave, 'valor': valor})
    return jsonify({'erro': 'Configuração não encontrada'}), 404


# ============================================================
# API: ATUALIZAR CONFIGURAÇÕES
# ============================================================

@configuracoes_bp.route('/api/configuracoes', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_atualizar():
    """
    Atualiza uma ou mais configurações.
    Espera JSON com pares chave: valor.

    Exemplo:
    {
        "confianca_minima": "65",
        "qualidade_minima": "70",
        "alerta_som": "true"
    }
    """
    dados = request.get_json()

    if not dados:
        return jsonify({'erro': 'Nenhum dado fornecido'}), 400

    atualizadas = []
    falhas = []

    for chave, valor in dados.items():
        if guardar_configuracao(chave, str(valor)):
            atualizadas.append(chave)
        else:
            falhas.append(chave)

    return jsonify({
        'sucesso': len(falhas) == 0,
        'atualizadas': atualizadas,
        'falhas': falhas,
        'mensagem': f'{len(atualizadas)} configuração(ões) atualizada(s).'
    })


# ============================================================
# ROTA: ATUALIZAR CONFIGURAÇÕES (FORMULÁRIO)
# ============================================================

@configuracoes_bp.route('/configuracoes/atualizar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def atualizar():
    """
    Processa o formulário de configurações gerais.
    """
    # Reconhecimento facial
    guardar_configuracao('confianca_minima', request.form.get('confianca_minima', '60'))
    guardar_configuracao('qualidade_minima', request.form.get('qualidade_minima', '60'))

    # Notificações
    guardar_configuracao('notificar_pais', request.form.get('notificar_pais', 'false'))
    guardar_configuracao('alerta_som', request.form.get('alerta_som', 'false'))

    # ESP8266
    esp_ip = request.form.get('esp_ip', '').strip()
    if esp_ip:
        guardar_configuracao('esp_ip', esp_ip)

    flash('✅ Configurações atualizadas com sucesso!', 'success')
    return redirect(url_for('configuracoes.index'))


# ============================================================
# ROTA: CONFIGURAR LINHA VIRTUAL (REDIRECIONA)
# ============================================================

@configuracoes_bp.route('/configurar-zona')
@login_obrigatorio
@admin_obrigatorio
def configurar_zona():
    """
    Página para configurar a linha virtual de deteção.
    O utilizador arrasta a linha no canvas.
    """
    # Obter coordenadas atuais da linha
    linha = {
        'x1': int(obter_configuracao('linha_x1', '0')),
        'y1': int(obter_configuracao('linha_y1', '300')),
        'x2': int(obter_configuracao('linha_x2', '1280')),
        'y2': int(obter_configuracao('linha_y2', '300')),
    }

    return render_template('configurar_zona.html', linha=linha)


# ============================================================
# ROTA: CONFIGURAR CÂMARA (REDIRECIONA)
# ============================================================

@configuracoes_bp.route('/configurar-camara')
@login_obrigatorio
@admin_obrigatorio
def configurar_camara():
    """
    Página para configurar o IP da câmara.
    """
    ip_atual = obter_configuracao('ip_camara', 'Não configurado')

    # Histórico de IPs
    historico = HistoricoIP.query.order_by(HistoricoIP.data.desc()).limit(10).all()

    return render_template(
        'configurar_camara.html',
        ip_atual=ip_atual,
        historico=historico,
    )


# ============================================================
# API: TESTAR CONEXÃO COM A CÂMARA
# ============================================================

@configuracoes_bp.route('/api/camara/testar', methods=['POST'])
@login_obrigatorio
def api_testar_camara():
    """
    Testa se o IP da câmara está acessível.
    Espera JSON: {"ip": "192.168.1.100:8080"}
    """
    from app.services.utils import testar_conexao_camara

    dados = request.get_json()
    if not dados or 'ip' not in dados:
        return jsonify({'erro': 'IP não fornecido'}), 400

    ip = dados['ip'].strip()
    online = testar_conexao_camara(ip)

    return jsonify({
        'ip': ip,
        'online': online,
        'mensagem': '🟢 Câmara online!' if online else '🔴 Não foi possível ligar à câmara.'
    })


# ============================================================
# API: GUARDAR IP DA CÂMARA
# ============================================================

@configuracoes_bp.route('/api/camara/guardar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_guardar_camara():
    """
    Guarda o IP da câmara na BD e regista no histórico.
    Espera JSON: {"ip": "192.168.1.100:8080"}
    """
    from app.services.utils import validar_ip, testar_conexao_camara

    dados = request.get_json()
    if not dados or 'ip' not in dados:
        return jsonify({'erro': 'IP não fornecido'}), 400

    ip = dados['ip'].strip()

    # Validar formato do IP
    if not validar_ip(ip):
        return jsonify({'erro': 'Formato de IP inválido. Use: 192.168.1.100:8080'}), 400

    # Guardar na tabela configuracoes
    guardar_configuracao('ip_camara', ip)

    # Registar no histórico
    from flask import session
    historico = HistoricoIP(
        ip=ip,
        adicionado_por=session.get('usuario_nome', 'Sistema'),
    )
    db.session.add(historico)
    db.session.commit()

    # Testar ligação
    online = testar_conexao_camara(ip)

    return jsonify({
        'sucesso': True,
        'ip': ip,
        'online': online,
        'mensagem': f'✅ IP {ip} guardado com sucesso!'
    })


# ============================================================
# API: STATUS DA CÂMARA
# ============================================================

@configuracoes_bp.route('/api/camara/status')
@login_obrigatorio
def api_status_camara():
    """
    Retorna o IP atual da câmara e se está online.
    """
    from app.services.utils import testar_conexao_camara

    ip = obter_configuracao('ip_camara', '')
    online = testar_conexao_camara(ip) if ip else False

    return jsonify({
        'ip': ip or 'Não configurado',
        'online': online,
        'status': 'online' if online else 'offline',
    })


# ============================================================
# API: TESTAR CONEXÃO COM ESP8266
# ============================================================

@configuracoes_bp.route('/api/esp/testar', methods=['POST'])
@login_obrigatorio
def api_testar_esp():
    """
    Testa se o ESP8266 está acessível.
    Espera JSON: {"ip": "192.168.1.200"}
    """
    from app.services.utils import testar_conexao_esp
    from flask import current_app

    dados = request.get_json()
    if not dados or 'ip' not in dados:
        return jsonify({'erro': 'IP não fornecido'}), 400

    ip = dados['ip'].strip()
    token = current_app.config.get('TOKEN_ESP', '')
    resultado = testar_conexao_esp(ip, token)

    return jsonify({
        'ip': ip,
        'online': resultado.get('online', False),
        'dados': resultado.get('dados'),
        'erro': resultado.get('erro'),
    })


# ============================================================
# API: RESTAURAR CONFIGURAÇÕES PADRÃO
# ============================================================

@configuracoes_bp.route('/api/configuracoes/restaurar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_restaurar_padrao():
    """
    Restaura as configurações para os valores padrão.
    """
    padroes = {
        'linha_x1': '0',
        'linha_y1': '300',
        'linha_x2': '1280',
        'linha_y2': '300',
        'confianca_minima': '60',
        'qualidade_minima': '60',
        'alerta_som': 'true',
        'notificar_pais': 'true',
    }

    for chave, valor in padroes.items():
        guardar_configuracao(chave, valor)

    return jsonify({
        'sucesso': True,
        'mensagem': '✅ Configurações restauradas para o padrão.'
    })