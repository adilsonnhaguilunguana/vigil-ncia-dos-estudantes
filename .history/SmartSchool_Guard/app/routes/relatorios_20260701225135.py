"""
Blueprint de Relatórios.
Gere relatórios de frequência, assiduidade, padrões de atraso e exportação.
"""

from flask import Blueprint, render_template, request, jsonify, Response
from datetime import datetime, timedelta
from app.database import db
from app.models import Aluno, Registo, Visitante, SessaoAtiva
from app.routes.auth import login_obrigatorio
from sqlalchemy import func, and_, extract
import csv
import io

relatorios_bp = Blueprint('relatorios', __name__)


# ============================================================
# ROTA: PÁGINA DE RELATÓRIOS
# ============================================================

@relatorios_bp.route('/relatorios')
@login_obrigatorio
def index():
    """
    Página principal de relatórios.
    Oferece diferentes tipos de relatórios e gráficos.
    """
    tipo = request.args.get('tipo', 'frequencia')  # tipo de relatório

    # Datas padrão: últimos 30 dias
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=30)

    # Lista de turmas para filtros
    turmas = db.session.query(Aluno.turma).filter(
        Aluno.turma != None,
        Aluno.turma != ''
    ).distinct().order_by(Aluno.turma).all()
    turmas = [t[0] for t in turmas]

    return render_template(
        'relatorios.html',
        tipo=tipo,
        data_inicio=data_inicio.strftime('%Y-%m-%d'),
        data_fim=data_fim.strftime('%Y-%m-%d'),
        turmas=turmas,
    )


# ============================================================
# API: FREQUÊNCIA DIÁRIA
# ============================================================

@relatorios_bp.route('/api/relatorios/frequencia-diaria')
@login_obrigatorio
def api_frequencia_diaria():
    """
    Retorna dados de frequência diária para gráficos.
    Total de entradas e saídas por dia no período.
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    turma = request.args.get('turma', '')

    if not data_inicio or not data_fim:
        return jsonify({'erro': 'Datas obrigatórias'}), 400

    try:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido'}), 400

    query = db.session.query(
        func.date(Registo.hora).label('data'),
        func.sum(db.case((Registo.tipo == 'entrada', 1), else_=0)).label('entradas'),
        func.sum(db.case((Registo.tipo == 'saida', 1), else_=0)).label('saidas'),
    ).filter(
        Registo.hora >= data_inicio_dt,
        Registo.hora <= data_fim_dt
    )

    # Filtrar por turma
    if turma:
        query = query.join(Aluno).filter(Aluno.turma == turma)

    dados = query.group_by(func.date(Registo.hora)).order_by('data').all()

    return jsonify([
        {
            'data': str(d.data),
            'entradas': int(d.entradas or 0),
            'saidas': int(d.saidas or 0),
            'total': int((d.entradas or 0) + (d.saidas or 0)),
        }
        for d in dados
    ])


# ============================================================
# API: ASSIDUIDADE POR TURMA
# ============================================================

@relatorios_bp.route('/api/relatorios/assiduidade-turma')
@login_obrigatorio
def api_assiduidade_turma():
    """
    Retorna percentagem de presenças por turma no período.
    Calcula: (dias com entrada / total de dias letivos) * 100
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    if not data_inicio or not data_fim:
        return jsonify({'erro': 'Datas obrigatórias'}), 400

    try:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido'}), 400

    # Total de dias no período
    total_dias = (data_fim_dt - data_inicio_dt).days + 1

    # Total de alunos por turma
    turmas = db.session.query(
        Aluno.turma,
        func.count(Aluno.id).label('total_alunos')
    ).filter(
        Aluno.activo == True,
        Aluno.turma != None,
        Aluno.turma != ''
    ).group_by(Aluno.turma).all()

    resultado = []
    for turma, total_alunos in turmas:
        if total_alunos == 0:
            continue

        # Total de entradas da turma no período
        total_entradas = Registo.query.join(Aluno).filter(
            Aluno.turma == turma,
            Aluno.activo == True,
            Registo.tipo == 'entrada',
            Registo.hora >= data_inicio_dt,
            Registo.hora <= data_fim_dt
        ).count()

        # Máximo de entradas possíveis (todos os alunos, todos os dias)
        maximo_entradas = total_alunos * total_dias

        # Percentagem de assiduidade
        percentagem = (total_entradas / maximo_entradas * 100) if maximo_entradas > 0 else 0

        resultado.append({
            'turma': turma,
            'total_alunos': total_alunos,
            'total_entradas': total_entradas,
            'dias_letivos': total_dias,
            'percentagem': round(percentagem, 1),
        })

    # Ordenar por percentagem (maior primeiro)
    resultado.sort(key=lambda x: x['percentagem'], reverse=True)

    return jsonify(resultado)


# ============================================================
# API: PADRÕES DE ATRASO
# ============================================================

@relatorios_bp.route('/api/relatorios/atrasos')
@login_obrigatorio
def api_atrasos():
    """
    Retorna alunos com entradas após um horário definido.
    Padrão: entradas após as 08:00 são consideradas atrasos.
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    hora_limite = request.args.get('hora_limite', '08:00')  # Hora limite configurável
    turma = request.args.get('turma', '')
    limite = request.args.get('limite', 20, type=int)

    try:
        hora_limite_h, hora_limite_m = map(int, hora_limite.split(':'))
    except ValueError:
        return jsonify({'erro': 'Formato de hora inválido. Use HH:MM'}), 400

    if not data_inicio or not data_fim:
        return jsonify({'erro': 'Datas obrigatórias'}), 400

    try:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido'}), 400

    query = db.session.query(
        Aluno.id,
        Aluno.nome,
        Aluno.numero,
        Aluno.turma,
        func.count(Registo.id).label('total_atrasos'),
    ).join(Registo).filter(
        Registo.tipo == 'entrada',
        Registo.hora >= data_inicio_dt,
        Registo.hora <= data_fim_dt,
        func.extract('hour', Registo.hora) > hora_limite_h
    )

    # Adicionar condição para minutos se a hora for igual
    # Ex: se hora_limite = 08:00, considera atraso se hora > 8 OU (hora = 8 E minuto > 0)
    query = query.filter(
        db.or_(
            func.extract('hour', Registo.hora) > hora_limite_h,
            db.and_(
                func.extract('hour', Registo.hora) == hora_limite_h,
                func.extract('minute', Registo.hora) > hora_limite_m
            )
        )
    )

    if turma:
        query = query.filter(Aluno.turma == turma)

    dados = query.group_by(
        Aluno.id, Aluno.nome, Aluno.numero, Aluno.turma
    ).order_by(
        func.count(Registo.id).desc()
    ).limit(limite).all()

    return jsonify([
        {
            'id': d.id,
            'nome': d.nome,
            'numero': d.numero,
            'turma': d.turma,
            'total_atrasos': d.total_atrasos,
        }
        for d in dados
    ])


# ============================================================
# API: HORAS DE PICO
# ============================================================

@relatorios_bp.route('/api/relatorios/horas-pico')
@login_obrigatorio
def api_horas_pico():
    """
    Retorna distribuição de entradas/saídas por hora do dia.
    Útil para identificar horas de maior movimento.
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    if not data_inicio or not data_fim:
        return jsonify({'erro': 'Datas obrigatórias'}), 400

    try:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido'}), 400

    # Entradas por hora
    entradas = db.session.query(
        func.extract('hour', Registo.hora).label('hora'),
        func.count(Registo.id).label('total')
    ).filter(
        Registo.tipo == 'entrada',
        Registo.hora >= data_inicio_dt,
        Registo.hora <= data_fim_dt
    ).group_by('hora').order_by('hora').all()

    # Saídas por hora
    saidas = db.session.query(
        func.extract('hour', Registo.hora).label('hora'),
        func.count(Registo.id).label('total')
    ).filter(
        Registo.tipo == 'saida',
        Registo.hora >= data_inicio_dt,
        Registo.hora <= data_fim_dt
    ).group_by('hora').order_by('hora').all()

    # Preencher todas as horas (6h às 18h)
    horas = list(range(6, 19))
    dados_entradas = {int(e.hora): e.total for e in entradas}
    dados_saidas = {int(s.hora): s.total for s in saidas}

    return jsonify({
        'horas': [f'{h:02d}:00' for h in horas],
        'entradas': [dados_entradas.get(h, 0) for h in horas],
        'saidas': [dados_saidas.get(h, 0) for h in horas],
    })


# ============================================================
# API: VISITANTES NO PERÍODO
# ============================================================

@relatorios_bp.route('/api/relatorios/visitantes')
@login_obrigatorio
def api_visitantes_periodo():
    """
    Retorna estatísticas de visitantes no período.
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    if not data_inicio or not data_fim:
        return jsonify({'erro': 'Datas obrigatórias'}), 400

    try:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido'}), 400

    total_visitantes = Visitante.query.filter(
        Visitante.hora_entrada >= data_inicio_dt,
        Visitante.hora_entrada <= data_fim_dt
    ).count()

    # Visitantes por dia
    por_dia = db.session.query(
        func.date(Visitante.hora_entrada).label('data'),
        func.count(Visitante.id).label('total')
    ).filter(
        Visitante.hora_entrada >= data_inicio_dt,
        Visitante.hora_entrada <= data_fim_dt
    ).group_by('data').order_by('data').all()

    # Motivos mais comuns
    motivos = db.session.query(
        Visitante.motivo,
        func.count(Visitante.id).label('total')
    ).filter(
        Visitante.hora_entrada >= data_inicio_dt,
        Visitante.hora_entrada <= data_fim_dt
    ).group_by(Visitante.motivo).order_by(func.count(Visitante.id).desc()).limit(10).all()

    return jsonify({
        'total_visitantes': total_visitantes,
        'por_dia': [
            {'data': str(d.data), 'total': d.total}
            for d in por_dia
        ],
        'motivos_comuns': [
            {'motivo': m.motivo, 'total': m.total}
            for m in motivos
        ],
    })


# ============================================================
# EXPORTAÇÃO CSV: REGISTOS
# ============================================================

@relatorios_bp.route('/relatorios/exportar/csv')
@login_obrigatorio
def exportar_csv():
    """
    Exporta os registos filtrados para ficheiro CSV.
    """
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    tipo = request.args.get('tipo', '')
    turma = request.args.get('turma', '')

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

    if turma:
        query = query.filter(Aluno.turma == turma)

    registos = query.order_by(Registo.hora.desc()).limit(5000).all()

    # Criar CSV em memória
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # Cabeçalho
    writer.writerow([
        'ID', 'Aluno', 'Número', 'Turma', 'Tipo',
        'Data/Hora', 'Confiança (%)', 'Direção', 'Método'
    ])

    # Dados
    for r in registos:
        writer.writerow([
            r.id,
            r.aluno.nome if r.aluno else 'N/A',
            r.aluno.numero if r.aluno else 'N/A',
            r.aluno.turma if r.aluno else 'N/A',
            r.tipo,
            r.hora.strftime('%d/%m/%Y %H:%M:%S') if r.hora else '',
            f'{r.confianca:.1f}' if r.confianca else '',
            r.direcao or '',
            r.metodo or 'facial',
        ])

    # Retornar como download
    output.seek(0)
    nome_ficheiro = f'registos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={nome_ficheiro}'
        }
    )


# ============================================================
# EXPORTAÇÃO CSV: ALUNOS
# ============================================================

@relatorios_bp.route('/relatorios/exportar/alunos-csv')
@login_obrigatorio
def exportar_alunos_csv():
    """
    Exporta a lista de alunos para ficheiro CSV.
    """
    alunos = Aluno.query.filter_by(activo=True).order_by(Aluno.nome).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        'ID', 'Nome', 'Número', 'Turma', 'Telefone do Pai',
        'Nome do Pai', 'Data Cadastro', 'Presente Agora'
    ])

    for a in alunos:
        writer.writerow([
            a.id,
            a.nome,
            a.numero,
            a.turma or '',
            a.telefone_pai or '',
            a.nome_pai or '',
            a.data_cadastro.strftime('%d/%m/%Y') if a.data_cadastro else '',
            'Sim' if a.presente else 'Não',
        ])

    output.seek(0)
    nome_ficheiro = f'alunos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={nome_ficheiro}'
        }
    )