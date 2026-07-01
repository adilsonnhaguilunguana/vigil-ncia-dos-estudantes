"""
Blueprint de Alertas.
Gere a lista, visualização e resolução de alertas de segurança.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from app.database import db
from app.models import Alerta
from app.routes.auth import login_obrigatorio, admin_obrigatorio
from sqlalchemy import func

alertas_bp = Blueprint('alertas', __name__)


# ============================================================
# ROTA: LISTAR ALERTAS
# ============================================================

@alertas_bp.route('/alertas')
@login_obrigatorio
def listar():
    """
    Página com a lista de alertas.
    Suporta filtros por tipo, severidade, status e data.
    """
    # Parâmetros de filtro
    tipo = request.args.get('tipo', '')              # 'desconhecido', 'emergencia'
    severidade = request.args.get('severidade', '')  # 'info', 'aviso', 'alerta', 'critico'
    resolvido = request.args.get('resolvido', '')    # '0', '1', ou ''
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 20

    # Query base
    query = Alerta.query

    # Filtrar por tipo
    if tipo:
        query = query.filter(Alerta.tipo == tipo)

    # Filtrar por severidade
    if severidade:
        query = query.filter(Alerta.severidade == severidade)

    # Filtrar por status (resolvido ou não)
    if resolvido == '0':
        query = query.filter(Alerta.resolvido == False)
    elif resolvido == '1':
        query = query.filter(Alerta.resolvido == True)

    # Filtrar por data
    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Alerta.hora >= data_inicio_dt)
        except ValueError:
            pass

    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Alerta.hora <= data_fim_dt)
        except ValueError:
            pass

    # Ordenar do mais recente para o mais antigo
    query = query.order_by(Alerta.hora.desc())

    # Paginação
    total = query.count()
    alertas = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    # Contadores para os cards de resumo
    alertas_ativos = Alerta.query.filter_by(resolvido=False).count()
    criticos_ativos = Alerta.query.filter_by(resolvido=False, severidade='critico').count()
    alertas_hoje = Alerta.query.filter(
        func.date(Alerta.hora) == datetime.now().date()
    ).count()

    return render_template(
        'alertas.html',
        alertas=alertas,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        tipo=tipo,
        severidade=severidade,
        resolvido=resolvido,
        data_inicio=data_inicio,
        data_fim=data_fim,
        alertas_ativos=alertas_ativos,
        criticos_ativos=criticos_ativos,
        alertas_hoje=alertas_hoje,
    )


# ============================================================
# ROTA: DETALHES DO ALERTA
# ============================================================

@alertas_bp.route('/alertas/<int:id>')
@login_obrigatorio
def detalhes(id):
    """
    Página com detalhes de um alerta específico.
    Mostra a foto do momento do alerta (se existir).
    """
    alerta = Alerta.query.get_or_404(id)
    return render_template('alerta_detalhes.html', alerta=alerta)


# ============================================================
# ROTA: RESOLVER ALERTA
# ============================================================

@alertas_bp.route('/alertas/<int:id>/resolver', methods=['POST'])
@login_obrigatorio
def resolver(id):
    """
    Marca um alerta como resolvido.
    """
    alerta = Alerta.query.get_or_404(id)

    if alerta.resolvido:
        flash('⚠️ Este alerta já está resolvido.', 'warning')
        return redirect(url_for('alertas.detalhes', id=id))

    alerta.resolvido = True

    try:
        db.session.commit()
        flash('✅ Alerta marcado como resolvido.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao resolver alerta: {str(e)}', 'danger')

    return redirect(url_for('alertas.detalhes', id=id))


# ============================================================
# ROTA: RESOLVER TODOS OS ALERTAS
# ============================================================

@alertas_bp.route('/alertas/resolver-todos', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def resolver_todos():
    """
    Marca todos os alertas não resolvidos como resolvidos.
    """
    alertas_pendentes = Alerta.query.filter_by(resolvido=False).all()
    total = len(alertas_pendentes)

    if total == 0:
        flash('✅ Não há alertas pendentes.', 'info')
        return redirect(url_for('alertas.listar'))

    for alerta in alertas_pendentes:
        alerta.resolvido = True

    try:
        db.session.commit()
        flash(f'✅ {total} alerta(s) marcado(s) como resolvido(s).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro: {str(e)}', 'danger')

    return redirect(url_for('alertas.listar'))


# ============================================================
# API: LISTAR ALERTAS (JSON)
# ============================================================

@alertas_bp.route('/api/alertas')
@login_obrigatorio
def api_listar():
    """
    API que retorna alertas em JSON.
    """
    resolvido = request.args.get('resolvido', '0')
    limite = request.args.get('limite', 50, type=int)

    query = Alerta.query

    if resolvido == '0':
        query = query.filter(Alerta.resolvido == False)
    elif resolvido == '1':
        query = query.filter(Alerta.resolvido == True)

    alertas = query.order_by(Alerta.hora.desc()).limit(limite).all()

    return jsonify([a.to_dict() for a in alertas])


# ============================================================
# API: NOVOS ALERTAS (POLLING)
# ============================================================

@alertas_bp.route('/api/alertas/novos')
@login_obrigatorio
def api_novos_alertas():
    """
    API para polling de novos alertas (não resolvidos).
    O dashboard.js chama esta rota a cada 10 segundos.
    """
    ultimo_id = request.args.get('ultimo_id', 0, type=int)

    alertas = Alerta.query.filter(
        Alerta.resolvido == False,
        Alerta.id > ultimo_id
    ).order_by(Alerta.hora.desc()).all()

    return jsonify({
        'total_ativos': Alerta.query.filter_by(resolvido=False).count(),
        'novos': [a.to_dict() for a in alertas],
    })


# ============================================================
# API: CRIAR ALERTA (USADO PELO SISTEMA DE RECONHECIMENTO)
# ============================================================

@alertas_bp.route('/api/alertas/criar', methods=['POST'])
def api_criar():
    """
    API interna para criar um alerta.
    Chamada pelo sistema de reconhecimento quando detecta algo.

    Espera JSON:
    {
        "tipo": "desconhecido",
        "descricao": "Pessoa desconhecida detectada",
        "severidade": "alerta",
        "frame_path": "frames/frame_20240601_080000.jpg"
    }
    """
    dados = request.get_json()

    if not dados:
        return jsonify({'erro': 'Dados inválidos'}), 400

    alerta = Alerta(
        tipo=dados.get('tipo', 'desconhecido'),
        descricao=dados.get('descricao', ''),
        severidade=dados.get('severidade', 'medio'),
        frame_path=dados.get('frame_path'),
    )

    try:
        db.session.add(alerta)
        db.session.commit()
        return jsonify({'sucesso': True, 'id': alerta.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# ============================================================
# API: ESTATÍSTICAS DE ALERTAS
# ============================================================

@alertas_bp.route('/api/alertas/estatisticas')
@login_obrigatorio
def api_estatisticas():
    """
    Retorna estatísticas de alertas para gráficos.
    """
    # Total por severidade (não resolvidos)
    por_severidade = db.session.query(
        Alerta.severidade,
        func.count(Alerta.id)
    ).filter(
        Alerta.resolvido == False
    ).group_by(Alerta.severidade).all()

    # Total por tipo
    por_tipo = db.session.query(
        Alerta.tipo,
        func.count(Alerta.id)
    ).filter(
        Alerta.resolvido == False
    ).group_by(Alerta.tipo).all()

    # Alertas nos últimos 7 dias
    ultimos_7_dias = db.session.query(
        func.date(Alerta.hora).label('data'),
        func.count(Alerta.id)
    ).filter(
        Alerta.hora >= func.now() - func.interval('7 days')
    ).group_by(
        func.date(Alerta.hora)
    ).order_by('data').all()

    return jsonify({
        'por_severidade': [
            {'severidade': s, 'total': t}
            for s, t in por_severidade
        ],
        'por_tipo': [
            {'tipo': tp, 'total': t}
            for tp, t in por_tipo
        ],
        'ultimos_7_dias': [
            {'data': str(d), 'total': t}
            for d, t in ultimos_7_dias
        ],
    })