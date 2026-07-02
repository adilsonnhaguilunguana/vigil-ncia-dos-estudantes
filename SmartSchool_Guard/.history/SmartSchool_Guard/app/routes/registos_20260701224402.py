"""
Blueprint de Registos.
Gere o histórico de entradas e saídas dos alunos.
"""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
from app.database import db
from app.models import Registo, Aluno
from app.routes.auth import login_obrigatorio
from sqlalchemy import func, and_

registos_bp = Blueprint('registos', __name__)


# ============================================================
# ROTA: LISTAR REGISTOS
# ============================================================

@registos_bp.route('/registos')
@login_obrigatorio
def listar():
    """
    Página com o histórico de registos de entradas e saídas.
    Suporta filtros por data, turma, tipo, e pesquisa.
    """
    # Parâmetros de filtro
    pagina = request.args.get('pagina', 1, type=int)
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    tipo = request.args.get('tipo', '')          # 'entrada', 'saida', ou ''
    turma = request.args.get('turma', '')
    pesquisa = request.args.get('pesquisa', '').strip()
    por_pagina = 50  # registos por página

    # Query base
    query = Registo.query.join(Aluno)

    # Filtrar por data de início
    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Registo.hora >= data_inicio_dt)
        except ValueError:
            pass

    # Filtrar por data de fim
    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            # Fim do dia
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Registo.hora <= data_fim_dt)
        except ValueError:
            pass

    # Filtrar por tipo (entrada/saída)
    if tipo in ['entrada', 'saida']:
        query = query.filter(Registo.tipo == tipo)

    # Filtrar por turma
    if turma:
        query = query.filter(Aluno.turma == turma)

    # Filtrar por nome ou número do aluno
    if pesquisa:
        query = query.filter(
            db.or_(
                Aluno.nome.ilike(f'%{pesquisa}%'),
                Aluno.numero.ilike(f'%{pesquisa}%')
            )
        )

    # Ordenar do mais recente para o mais antigo
    query = query.order_by(Registo.hora.desc())

    # Paginação
    total = query.count()
    registos = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    # Lista de turmas para o filtro
    turmas = db.session.query(Aluno.turma).filter(
        Aluno.turma != None,
        Aluno.turma != ''
    ).distinct().order_by(Aluno.turma).all()
    turmas = [t[0] for t in turmas]

    # Estatísticas do período filtrado
    stats = {
        'total': total,
        'entradas': query.filter(Registo.tipo == 'entrada').count() if total > 0 else 0,
        'saidas': query.filter(Registo.tipo == 'saida').count() if total > 0 else 0,
    }

    return render_template(
        'registos.html',
        registos=registos,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo=tipo,
        turma=turma,
        pesquisa=pesquisa,
        turmas=turmas,
        stats=stats,
    )


# ============================================================
# API: REGISTOS (JSON)
# ============================================================

@registos_bp.route('/api/registos')
@login_obrigatorio
def api_listar():
    """
    API que retorna registos em JSON.
    Suporta os mesmos filtros da página HTML.
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    tipo = request.args.get('tipo', '')
    limite = request.args.get('limite', 100, type=int)

    query = Registo.query.join(Aluno)

    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Registo.hora >= data_inicio_dt)
        except ValueError:
            pass

    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Registo.hora <= data_fim_dt)
        except ValueError:
            pass

    if tipo in ['entrada', 'saida']:
        query = query.filter(Registo.tipo == tipo)

    registos = query.order_by(Registo.hora.desc()).limit(limite).all()

    return jsonify([r.to_dict() for r in registos])


# ============================================================
# API: ESTATÍSTICAS DIÁRIAS
# ============================================================

@registos_bp.route('/api/registos/estatisticas')
@login_obrigatorio
def api_estatisticas():
    """
    Retorna estatísticas de registos para um período.
    Útil para gráficos nos relatórios.
    """
    dias = request.args.get('dias', 7, type=int)
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias)

    # Contagem diária
    estatisticas = db.session.query(
        func.date(Registo.hora).label('data'),
        func.sum(db.case((Registo.tipo == 'entrada', 1), else_=0)).label('entradas'),
        func.sum(db.case((Registo.tipo == 'saida', 1), else_=0)).label('saidas'),
    ).filter(
        Registo.hora >= data_inicio,
        Registo.hora <= data_fim
    ).group_by(
        func.date(Registo.hora)
    ).order_by(
        func.date(Registo.hora)
    ).all()

    return jsonify([
        {
            'data': str(e.data),
            'entradas': int(e.entradas or 0),
            'saidas': int(e.saidas or 0),
            'total': int((e.entradas or 0) + (e.saidas or 0)),
        }
        for e in estatisticas
    ])


# ============================================================
# API: REGISTOS DE UM ALUNO ESPECÍFICO
# ============================================================

@registos_bp.route('/api/registos/aluno/<int:aluno_id>')
@login_obrigatorio
def api_registos_aluno(aluno_id):
    """
    Retorna os registos de um aluno específico em JSON.
    """
    limite = request.args.get('limite', 30, type=int)

    registos = Registo.query.filter_by(aluno_id=aluno_id).order_by(
        Registo.hora.desc()
    ).limit(limite).all()

    return jsonify([r.to_dict() for r in registos])


# ============================================================
# API: RESUMO DO DIA ATUAL
# ============================================================

@registos_bp.route('/api/registos/resumo-hoje')
@login_obrigatorio
def api_resumo_hoje():
    """
    Retorna um resumo dos registos de hoje.
    """
    hoje = datetime.now().date()

    total_entradas = Registo.query.filter(
        Registo.tipo == 'entrada',
        func.date(Registo.hora) == hoje
    ).count()

    total_saidas = Registo.query.filter(
        Registo.tipo == 'saida',
        func.date(Registo.hora) == hoje
    ).count()

    # Última entrada e última saída
    ultima_entrada = Registo.query.filter(
        Registo.tipo == 'entrada',
        func.date(Registo.hora) == hoje
    ).order_by(Registo.hora.desc()).first()

    ultima_saida = Registo.query.filter(
        Registo.tipo == 'saida',
        func.date(Registo.hora) == hoje
    ).order_by(Registo.hora.desc()).first()

    return jsonify({
        'data': str(hoje),
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'ultima_entrada': {
            'hora': ultima_entrada.hora.strftime('%H:%M:%S'),
            'aluno': ultima_entrada.aluno.nome if ultima_entrada else None,
        } if ultima_entrada else None,
        'ultima_saida': {
            'hora': ultima_saida.hora.strftime('%H:%M:%S'),
            'aluno': ultima_saida.aluno.nome if ultima_saida else None,
        } if ultima_saida else None,
    })