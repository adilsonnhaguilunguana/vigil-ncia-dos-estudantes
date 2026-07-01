"""
Blueprint da Zona de Detecção.
Gere a API da linha virtual para deteção de entrada/saída.
"""

from flask import Blueprint, request, jsonify
from app.routes.auth import login_obrigatorio, admin_obrigatorio
from app.services.utils import obter_configuracao, guardar_configuracao

zona_bp = Blueprint('zona', __name__)


# ============================================================
# ROTA: OBTER COORDENADAS DA LINHA VIRTUAL
# ============================================================

@zona_bp.route('/api/zona')
@login_obrigatorio
def api_obter():
    """
    Retorna as coordenadas atuais da linha virtual de deteção.

    Resposta:
    {
        "x1": 0,
        "y1": 300,
        "x2": 1280,
        "y2": 300,
        "ativa": true
    }
    """
    return jsonify({
        'x1': int(obter_configuracao('linha_x1', '0')),
        'y1': int(obter_configuracao('linha_y1', '300')),
        'x2': int(obter_configuracao('linha_x2', '1280')),
        'y2': int(obter_configuracao('linha_y2', '300')),
        'ativa': obter_configuracao('linha_ativa', 'true') == 'true',
    })


# ============================================================
# ROTA: ATUALIZAR COORDENADAS DA LINHA VIRTUAL
# ============================================================

@zona_bp.route('/api/zona', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_atualizar():
    """
    Atualiza as coordenadas da linha virtual.
    Chamado quando o utilizador arrasta a linha no browser.

    Espera JSON:
    {
        "x1": 100,
        "y1": 350,
        "x2": 1180,
        "y2": 350
    }
    """
    dados = request.get_json()

    if not dados:
        return jsonify({'erro': 'Dados não fornecidos'}), 400

    # Validar coordenadas
    x1 = dados.get('x1')
    y1 = dados.get('y1')
    x2 = dados.get('x2')
    y2 = dados.get('y2')

    if None in (x1, y1, x2, y2):
        return jsonify({'erro': 'Todas as coordenadas (x1, y1, x2, y2) são obrigatórias'}), 400

    try:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    except (ValueError, TypeError):
        return jsonify({'erro': 'Coordenadas devem ser números inteiros'}), 400

    # Validar limites razoáveis (frame da câmara: 1280x720)
    if not (0 <= x1 <= 1920 and 0 <= y1 <= 1080):
        return jsonify({'erro': 'Coordenada 1 fora dos limites (0-1920, 0-1080)'}), 400
    if not (0 <= x2 <= 1920 and 0 <= y2 <= 1080):
        return jsonify({'erro': 'Coordenada 2 fora dos limites (0-1920, 0-1080)'}), 400

    # Guardar na BD
    guardar_configuracao('linha_x1', str(x1))
    guardar_configuracao('linha_y1', str(y1))
    guardar_configuracao('linha_x2', str(x2))
    guardar_configuracao('linha_y2', str(y2))

    # Guardar direção configurada (opcional)
    direcao_entrada = dados.get('direcao_entrada', 'cima_para_baixo')
    if direcao_entrada in ['cima_para_baixo', 'baixo_para_cima', 'esquerda_para_direita', 'direita_para_esquerda']:
        guardar_configuracao('direcao_entrada', direcao_entrada)

    return jsonify({
        'sucesso': True,
        'mensagem': '✅ Linha virtual atualizada com sucesso!',
        'coordenadas': {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
        }
    })


# ============================================================
# ROTA: ATIVAR/DESATIVAR LINHA VIRTUAL
# ============================================================

@zona_bp.route('/api/zona/ativar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_ativar():
    """
    Ativa ou desativa a linha virtual de deteção.

    Espera JSON: {"ativa": true} ou {"ativa": false}
    """
    dados = request.get_json()

    if not dados or 'ativa' not in dados:
        return jsonify({'erro': 'Campo "ativa" é obrigatório'}), 400

    ativa = dados['ativa']
    if not isinstance(ativa, bool):
        return jsonify({'erro': '"ativa" deve ser true ou false'}), 400

    guardar_configuracao('linha_ativa', str(ativa).lower())

    return jsonify({
        'sucesso': True,
        'ativa': ativa,
        'mensagem': '✅ Linha virtual ativada.' if ativa else '⏸️ Linha virtual desativada.'
    })


# ============================================================
# ROTA: RESTAURAR LINHA PADRÃO
# ============================================================

@zona_bp.route('/api/zona/restaurar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def api_restaurar():
    """
    Restaura a linha virtual para as coordenadas padrão.
    Linha horizontal no meio do frame (y=300).
    """
    padrao = {
        'linha_x1': '0',
        'linha_y1': '300',
        'linha_x2': '1280',
        'linha_y2': '300',
        'linha_ativa': 'true',
        'direcao_entrada': 'cima_para_baixo',
    }

    for chave, valor in padrao.items():
        guardar_configuracao(chave, valor)

    return jsonify({
        'sucesso': True,
        'mensagem': '✅ Linha virtual restaurada para o padrão.',
        'coordenadas': {
            'x1': 0,
            'y1': 300,
            'x2': 1280,
            'y2': 300,
        }
    })


# ============================================================
# ROTA: OBTER DIREÇÃO DE ENTRADA CONFIGURADA
# ============================================================

@zona_bp.route('/api/zona/direcao')
@login_obrigatorio
def api_direcao():
    """
    Retorna a direção considerada como 'entrada'.
    """
    direcao = obter_configuracao('direcao_entrada', 'cima_para_baixo')

    return jsonify({
        'direcao_entrada': direcao,
        'opcoes': [
            {'valor': 'cima_para_baixo', 'descricao': 'Cima → Baixo (padrão)'},
            {'valor': 'baixo_para_cima', 'descricao': 'Baixo → Cima'},
            {'valor': 'esquerda_para_direita', 'descricao': 'Esquerda → Direita'},
            {'valor': 'direita_para_esquerda', 'descricao': 'Direita → Esquerda'},
        ]
    })


# ============================================================
# ROTA: VALIDAR CRUZAMENTO (USO INTERNO)
# ============================================================

@zona_bp.route('/api/zona/validar-cruzamento', methods=['POST'])
def api_validar_cruzamento():
    """
    API interna para validar se um ponto cruzou a linha virtual.
    Chamada pelo sistema de reconhecimento.

    Espera JSON:
    {
        "x_anterior": 320,
        "y_anterior": 250,
        "x_atual": 320,
        "y_atual": 350
    }

    Resposta:
    {
        "cruzou": true,
        "direcao": "cima_para_baixo",
        "tipo": "entrada"
    }
    """
    dados = request.get_json()

    if not dados:
        return jsonify({'erro': 'Dados não fornecidos'}), 400

    x_anterior = dados.get('x_anterior')
    y_anterior = dados.get('y_anterior')
    x_atual = dados.get('x_atual')
    y_atual = dados.get('y_atual')

    if None in (x_anterior, y_anterior, x_atual, y_atual):
        return jsonify({'erro': 'Coordenadas insuficientes'}), 400

    # Obter linha virtual atual
    linha_x1 = int(obter_configuracao('linha_x1', '0'))
    linha_y1 = int(obter_configuracao('linha_y1', '300'))
    linha_x2 = int(obter_configuracao('linha_x2', '1280'))
    linha_y2 = int(obter_configuracao('linha_y2', '300'))
    linha_ativa = obter_configuracao('linha_ativa', 'true') == 'true'

    if not linha_ativa:
        return jsonify({'cruzou': False, 'motivo': 'Linha desativada'})

    # Verificar se o segmento (anterior → atual) cruza a linha
    cruzou = verificar_cruzamento(
        x_anterior, y_anterior, x_atual, y_atual,
        linha_x1, linha_y1, linha_x2, linha_y2
    )

    if not cruzou:
        return jsonify({'cruzou': False})

    # Determinar direção
    # Se y_atual > y_anterior → moveu-se para baixo
    # Se y_atual < y_anterior → moveu-se para cima
    if y_atual > y_anterior:
        direcao = 'cima_para_baixo'
    elif y_atual < y_anterior:
        direcao = 'baixo_para_cima'
    elif x_atual > x_anterior:
        direcao = 'esquerda_para_direita'
    else:
        direcao = 'direita_para_esquerda'

    # Determinar se é entrada ou saída
    direcao_entrada = obter_configuracao('direcao_entrada', 'cima_para_baixo')
    tipo = 'entrada' if direcao == direcao_entrada else 'saida'

    return jsonify({
        'cruzou': True,
        'direcao': direcao,
        'tipo': tipo,
    })


# ============================================================
# FUNÇÃO AUXILIAR: VERIFICAR CRUZAMENTO DE SEGMENTOS
# ============================================================

def verificar_cruzamento(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Verifica se dois segmentos de reta se cruzam.
    Usa o algoritmo de orientação (cross product).

    Segmento A: (x1,y1) → (x2,y2)  (movimento da pessoa)
    Segmento B: (x3,y3) → (x4,y4)  (linha virtual)

    Returns:
        True se os segmentos se cruzam
    """
    def orientacao(ax, ay, bx, by, cx, cy):
        """Calcula a orientação de 3 pontos."""
        val = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
        if val == 0:
            return 0        # colinear
        return 1 if val > 0 else 2  # horário ou anti-horário

    def no_segmento(ax, ay, bx, by, cx, cy):
        """Verifica se o ponto C está no segmento AB."""
        return (
            min(ax, bx) <= cx <= max(ax, bx) and
            min(ay, by) <= cy <= max(ay, by)
        )

    # Calcular orientações
    o1 = orientacao(x1, y1, x2, y2, x3, y3)
    o2 = orientacao(x1, y1, x2, y2, x4, y4)
    o3 = orientacao(x3, y3, x4, y4, x1, y1)
    o4 = orientacao(x3, y3, x4, y4, x2, y2)

    # Caso geral: segmentos cruzam-se
    if o1 != o2 and o3 != o4:
        return True

    # Casos especiais: pontos colineares
    if o1 == 0 and no_segmento(x1, y1, x2, y2, x3, y3):
        return True
    if o2 == 0 and no_segmento(x1, y1, x2, y2, x4, y4):
        return True
    if o3 == 0 and no_segmento(x3, y3, x4, y4, x1, y1):
        return True
    if o4 == 0 and no_segmento(x3, y3, x4, y4, x2, y2):
        return True

    return False