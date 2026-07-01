"""
Blueprint de Visitantes.
Gere o registo, listagem e saída de visitantes.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from app.database import db
from app.models import Visitante
from app.routes.auth import login_obrigatorio
from app.services.utils import gerar_pin
from sqlalchemy import func

visitantes_bp = Blueprint('visitantes', __name__)


# ============================================================
# ROTA: LISTAR VISITANTES
# ============================================================

@visitantes_bp.route('/visitantes')
@login_obrigatorio
def listar():
    """
    Página com a lista de visitantes.
    Mostra visitantes ativos (ainda dentro) e histórico.
    """
    # Parâmetros de filtro
    status = request.args.get('status', 'ativos')  # 'ativos', 'todos', 'historico'
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    pesquisa = request.args.get('pesquisa', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 20

    # Query base
    query = Visitante.query

    # Filtrar por status
    if status == 'ativos':
        query = query.filter(Visitante.hora_saida == None)
    elif status == 'historico':
        query = query.filter(Visitante.hora_saida != None)

    # Filtrar por data
    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Visitante.hora_entrada >= data_inicio_dt)
        except ValueError:
            pass

    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Visitante.hora_entrada <= data_fim_dt)
        except ValueError:
            pass

    # Pesquisar por nome ou motivo
    if pesquisa:
        query = query.filter(
            db.or_(
                Visitante.nome.ilike(f'%{pesquisa}%'),
                Visitante.motivo.ilike(f'%{pesquisa}%'),
                Visitante.autorizado_por.ilike(f'%{pesquisa}%')
            )
        )

    # Ordenar: ativos primeiro, depois por data de entrada
    query = query.order_by(
        Visitante.hora_saida.asc().nullsfirst(),
        Visitante.hora_entrada.desc()
    )

    # Paginação
    total = query.count()
    visitantes = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total + por_pagina - 1) // por_pagina

    # Contadores para os cards
    ativos_agora = Visitante.query.filter(Visitante.hora_saida == None).count()
    total_hoje = Visitante.query.filter(
        func.date(Visitante.hora_entrada) == datetime.now().date()
    ).count()

    return render_template(
        'visitantes.html',
        visitantes=visitantes,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        status=status,
        data_inicio=data_inicio,
        data_fim=data_fim,
        pesquisa=pesquisa,
        ativos_agora=ativos_agora,
        total_hoje=total_hoje,
    )


# ============================================================
# ROTA: CADASTRAR VISITANTE
# ============================================================

@visitantes_bp.route('/visitantes/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
def cadastrar():
    """
    Página de cadastro de novo visitante.
    GET  → formulário
    POST → processa o cadastro
    """
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        motivo = request.form.get('motivo', '').strip()
        autorizado_por = request.form.get('autorizado_por', '').strip()
        gerar_pin_flag = request.form.get('gerar_pin') == '1'

        # Validações
        erros = []
        if not nome or len(nome) < 3:
            erros.append('Nome deve ter pelo menos 3 caracteres.')
        if not motivo:
            erros.append('O motivo da visita é obrigatório.')
        if not autorizado_por:
            erros.append('Indique quem autorizou a visita.')

        if erros:
            for erro in erros:
                flash(f'⚠️ {erro}', 'warning')
            return render_template('visitante_cadastro.html', dados=request.form)

        # Criar visitante
        visitante = Visitante(
            nome=nome,
            motivo=motivo,
            autorizado_por=autorizado_por,
            hora_entrada=datetime.now(),
        )

        # Gerar PIN de acesso se solicitado
        if gerar_pin_flag:
            visitante.pin = gerar_pin(4)

        try:
            db.session.add(visitante)
            db.session.commit()

            mensagem = f'🎉 Visitante {nome} registado com sucesso!'
            if visitante.pin:
                mensagem += f' PIN de acesso: {visitante.pin}'
            flash(mensagem, 'success')

            return redirect(url_for('visitantes.listar'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erro ao registar visitante: {str(e)}', 'danger')
            return render_template('visitante_cadastro.html', dados=request.form)

    # GET → mostrar formulário vazio
    return render_template('visitante_cadastro.html', dados={})


# ============================================================
# ROTA: REGISTAR SAÍDA DO VISITANTE
# ============================================================

@visitantes_bp.route('/visitantes/<int:id>/saida', methods=['POST'])
@login_obrigatorio
def registrar_saida(id):
    """
    Regista a hora de saída de um visitante.
    """
    visitante = Visitante.query.get_or_404(id)

    if visitante.hora_saida:
        flash('⚠️ Este visitante já registou a saída.', 'warning')
        return redirect(url_for('visitantes.listar'))

    visitante.hora_saida = datetime.now()

    # Calcular tempo de permanência
    permanencia = visitante.hora_saida - visitante.hora_entrada
    horas = permanencia.total_seconds() / 3600

    try:
        db.session.commit()
        flash(
            f'👋 Saída de {visitante.nome} registada. '
            f'Permanência: {horas:.1f} hora(s).',
            'info'
        )
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao registar saída: {str(e)}', 'danger')

    return redirect(url_for('visitantes.listar'))


# ============================================================
# ROTA: EDITAR VISITANTE
# ============================================================

@visitantes_bp.route('/visitantes/<int:id>/editar', methods=['GET', 'POST'])
@login_obrigatorio
def editar(id):
    """
    Edita os dados de um visitante.
    """
    visitante = Visitante.query.get_or_404(id)

    if request.method == 'POST':
        visitante.nome = request.form.get('nome', visitante.nome).strip()
        visitante.motivo = request.form.get('motivo', visitante.motivo).strip()
        visitante.autorizado_por = request.form.get(
            'autorizado_por', visitante.autorizado_por
        ).strip()

        try:
            db.session.commit()
            flash('✅ Dados do visitante atualizados.', 'success')
            return redirect(url_for('visitantes.listar'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erro: {str(e)}', 'danger')

    return render_template('visitante_cadastro.html', visitante=visitante, modo_edicao=True)


# ============================================================
# ROTA: GERAR NOVO PIN
# ============================================================

@visitantes_bp.route('/visitantes/<int:id>/novo-pin', methods=['POST'])
@login_obrigatorio
def novo_pin(id):
    """
    Gera um novo PIN para o visitante.
    """
    visitante = Visitante.query.get_or_404(id)

    if visitante.hora_saida:
        flash('⚠️ Visitante já saiu. Não é possível gerar PIN.', 'warning')
        return redirect(url_for('visitantes.listar'))

    visitante.pin = gerar_pin(4)

    try:
        db.session.commit()
        flash(f'🔑 Novo PIN gerado: {visitante.pin}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro: {str(e)}', 'danger')

    return redirect(url_for('visitantes.listar'))


# ============================================================
# API: LISTAR VISITANTES (JSON)
# ============================================================

@visitantes_bp.route('/api/visitantes')
@login_obrigatorio
def api_listar():
    """
    API que retorna visitantes em JSON.
    """
    status = request.args.get('status', 'ativos')
    limite = request.args.get('limite', 50, type=int)

    query = Visitante.query

    if status == 'ativos':
        query = query.filter(Visitante.hora_saida == None)
    elif status == 'historico':
        query = query.filter(Visitante.hora_saida != None)

    visitantes = query.order_by(Visitante.hora_entrada.desc()).limit(limite).all()

    return jsonify([v.to_dict() for v in visitantes])


# ============================================================
# API: VALIDAR PIN
# ============================================================

@visitantes_bp.route('/api/visitantes/validar-pin', methods=['POST'])
def api_validar_pin():
    """
    API para validar o PIN de um visitante.
    Chamada pelo sistema de reconhecimento ou teclado na porta.

    Espera JSON: {"pin": "1234"}
    Retorna: {"valido": true, "visitante": {...}} ou {"valido": false}
    """
    dados = request.get_json()

    if not dados or 'pin' not in dados:
        return jsonify({'valido': False, 'erro': 'PIN não fornecido'}), 400

    pin = dados['pin'].strip()

    visitante = Visitante.query.filter(
        Visitante.pin == pin,
        Visitante.hora_saida == None
    ).first()

    if visitante:
        return jsonify({
            'valido': True,
            'visitante': visitante.to_dict()
        })
    else:
        return jsonify({
            'valido': False,
            'erro': 'PIN inválido ou visitante já saiu'
        })