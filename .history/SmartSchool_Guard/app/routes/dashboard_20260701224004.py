"""
Blueprint do Dashboard.
Painel principal do sistema com estatísticas em tempo real.
"""

from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
from app.database import db
from app.models import Aluno, Registo, Alerta, Visitante, SessaoAtiva, Configuracao
from app.routes.auth import login_obrigatorio
from sqlalchemy import func, and_

dashboard_bp = Blueprint('dashboard', __name__)


# ============================================================
# ROTA: DASHBOARD PRINCIPAL
# ============================================================

@dashboard_bp.route('/')
@login_obrigatorio
def index():
    """
    Página principal do dashboard.
    Mostra estatísticas gerais e últimos eventos.
    """
    hoje = datetime.now().date()

    # Estatísticas para os cards
    total_alunos = Aluno.query.filter_by(activo=True).count()
    presentes_hoje = SessaoAtiva.query.filter(
        SessaoAtiva.hora_entrada >= hoje,
        SessaoAtiva.hora_saida == None
    ).count()
    entradas_hoje = Registo.query.filter(
        Registo.tipo == 'entrada',
        func.date(Registo.hora) == hoje
    ).count()
    alertas_ativos = Alerta.query.filter_by(resolvido=False).count()
    visitantes_ativos = Visitante.query.filter(
        Visitante.hora_saida == None
    ).count()

    # Últimos registos (10 mais recentes)
    ultimos_registos = Registo.query.order_by(
        Registo.hora.desc()
    ).limit(10).all()

    # Últimos alertas não resolvidos
    ultimos_alertas = Alerta.query.filter_by(resolvido=False).order_by(
        Alerta.hora.desc()
    ).limit(5).all()

    # Alunos presentes agora
    alunos_presentes = SessaoAtiva.query.filter(
        SessaoAtiva.hora_saida == None
    ).order_by(SessaoAtiva.hora_entrada.desc()).all()

    # Status da câmara (lê da BD)
    ip_camara = Configuracao.query.filter_by(chave='ip_camara').first()
    ip_camara = ip_camara.valor if ip_camara else 'Não configurado'

    # Status do ESP8266
    esp_ip = Configuracao.query.filter_by(chave='esp_ip').first()
    esp_ip = esp_ip.valor if esp_ip else 'Não configurado'

    return render_template(
        'dashboard.html',
        # Cards
        total_alunos=total_alunos,
        presentes_hoje=presentes_hoje,
        entradas_hoje=entradas_hoje,
        alertas_ativos=alertas_ativos,
        visitantes_ativos=visitantes_ativos,
        # Tabelas
        ultimos_registos=ultimos_registos,
        ultimos_alertas=ultimos_alertas,
        alunos_presentes=alunos_presentes,
        # Status
        ip_camara=ip_camara,
        esp_ip=esp_ip,
        # Info
        usuario_nome=session.get('usuario_nome', ''),
        usuario_role=session.get('usuario_role', ''),
    )


# ============================================================
# API: DADOS DO DASHBOARD (ATUALIZAÇÃO EM TEMPO REAL)
# ============================================================

@dashboard_bp.route('/api/dashboard/dados')
@login_obrigatorio
def api_dashboard_dados():
    """
    Retorna dados do dashboard em JSON para atualização via JavaScript.
    Chamado a cada 5 segundos pelo dashboard.js.
    """
    hoje = datetime.now().date()

    # Contagens atualizadas
    dados = {
        'presentes_hoje': SessaoAtiva.query.filter(
            SessaoAtiva.hora_entrada >= hoje,
            SessaoAtiva.hora_saida == None
        ).count(),
        'entradas_hoje': Registo.query.filter(
            Registo.tipo == 'entrada',
            func.date(Registo.hora) == hoje
        ).count(),
        'saidas_hoje': Registo.query.filter(
            Registo.tipo == 'saida',
            func.date(Registo.hora) == hoje
        ).count(),
        'alertas_ativos': Alerta.query.filter_by(resolvido=False).count(),
        'visitantes_ativos': Visitante.query.filter(
            Visitante.hora_saida == None
        ).count(),
        # Últimos 5 registos
        'ultimos_registos': [
            {
                'id': r.id,
                'aluno_nome': r.aluno.nome if r.aluno else 'Desconhecido',
                'tipo': r.tipo,
                'hora': r.hora.strftime('%H:%M:%S'),
                'confianca': r.confianca,
            }
            for r in Registo.query.order_by(Registo.hora.desc()).limit(5).all()
        ],
    }

    return jsonify(dados)


# ============================================================
# API: GRÁFICO DE MOVIMENTO DIÁRIO
# ============================================================

@dashboard_bp.route('/api/dashboard/grafico-movimento')
@login_obrigatorio
def api_grafico_movimento():
    """
    Retorna dados para o gráfico de movimento diário (entradas/saídas por hora).
    """
    hoje = datetime.now().date()

    # Entradas por hora
    entradas = db.session.query(
        func.extract('hour', Registo.hora).label('hora'),
        func.count(Registo.id).label('total')
    ).filter(
        Registo.tipo == 'entrada',
        func.date(Registo.hora) == hoje
    ).group_by('hora').order_by('hora').all()

    # Saídas por hora
    saidas = db.session.query(
        func.extract('hour', Registo.hora).label('hora'),
        func.count(Registo.id).label('total')
    ).filter(
        Registo.tipo == 'saida',
        func.date(Registo.hora) == hoje
    ).group_by('hora').order_by('hora').all()

    # Formatar para o gráfico (Chart.js)
    horas = [f'{h:02d}:00' for h in range(6, 19)]  # 06:00 às 18:00
    dados_entradas = [0] * 13
    dados_saidas = [0] * 13

    for e in entradas:
        hora = int(e.hora)
        if 6 <= hora <= 18:
            dados_entradas[hora - 6] = e.total

    for s in saidas:
        hora = int(s.hora)
        if 6 <= hora <= 18:
            dados_saidas[hora - 6] = s.total

    return jsonify({
        'horas': horas,
        'entradas': dados_entradas,
        'saidas': dados_saidas,
    })


# ============================================================
# API: ALUNOS PRESENTES AGORA
# ============================================================

@dashboard_bp.route('/api/presentes')
@login_obrigatorio
def api_presentes():
    """
    Retorna lista de alunos atualmente dentro da escola.
    """
    presentes = SessaoAtiva.query.filter(
        SessaoAtiva.hora_saida == None
    ).order_by(SessaoAtiva.hora_entrada.desc()).all()

    return jsonify([
        {
            'id': p.aluno_id,
            'nome': p.aluno.nome,
            'turma': p.aluno.turma,
            'hora_entrada': p.hora_entrada.strftime('%H:%M:%S'),
            'tempo_presente': str(datetime.now() - p.hora_entrada).split('.')[0],
        }
        for p in presentes
    ])