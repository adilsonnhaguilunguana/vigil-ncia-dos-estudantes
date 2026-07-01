"""
Blueprint de Alunos.
Gere o CRUD de alunos: listar, cadastrar, visualizar, editar e remover.
"""

import os
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, current_app
)
from werkzeug.utils import secure_filename
from datetime import datetime
from app.database import db
from app.models import Aluno, Registo, SessaoAtiva
from app.routes.auth import login_obrigatorio, admin_obrigatorio
from app.services.utils import (
    verificar_qualidade_foto,
    gerar_nome_ficheiro,
    validar_telefone,
    validar_numero_aluno,
    redimensionar_imagem,
)

alunos_bp = Blueprint('alunos', __name__)


# ============================================================
# ROTA: LISTAR ALUNOS
# ============================================================

@alunos_bp.route('/alunos')
@login_obrigatorio
def listar():
    """
    Página com a lista de todos os alunos cadastrados.
    Suporta filtros: turma, pesquisa por nome/número, ativos/inativos.
    """
    # Parâmetros de filtro
    turma = request.args.get('turma', '')
    pesquisa = request.args.get('pesquisa', '').strip()
    mostrar_inativos = request.args.get('inativos', '0') == '1'

    # Query base
    query = Aluno.query

    # Filtrar por turma
    if turma:
        query = query.filter_by(turma=turma)

    # Filtrar por nome ou número (pesquisa)
    if pesquisa:
        query = query.filter(
            db.or_(
                Aluno.nome.ilike(f'%{pesquisa}%'),
                Aluno.numero.ilike(f'%{pesquisa}%')
            )
        )

    # Filtrar ativos/inativos
    if not mostrar_inativos:
        query = query.filter_by(activo=True)

    # Ordenar e executar
    alunos = query.order_by(Aluno.nome.asc()).all()

    # Lista de turmas únicas para o filtro
    turmas = db.session.query(Aluno.turma).filter(
        Aluno.turma != None,
        Aluno.turma != ''
    ).distinct().order_by(Aluno.turma).all()
    turmas = [t[0] for t in turmas]

    return render_template(
        'alunos.html',
        alunos=alunos,
        turmas=turmas,
        turma_selecionada=turma,
        pesquisa=pesquisa,
        mostrar_inativos=mostrar_inativos,
        total=len(alunos),
    )


# ============================================================
# ROTA: CADASTRAR ALUNO
# ============================================================

@alunos_bp.route('/alunos/cadastrar', methods=['GET', 'POST'])
@login_obrigatorio
@admin_obrigatorio
def cadastrar():
    """
    Página de cadastro de novo aluno.
    GET  → formulário
    POST → processa o cadastro com verificação de qualidade da foto
    """
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        numero = request.form.get('numero', '').strip()
        turma = request.form.get('turma', '').strip()
        telefone_pai = request.form.get('telefone_pai', '').strip()
        nome_pai = request.form.get('nome_pai', '').strip()

        # ==========================================
        # VALIDAÇÕES
        # ==========================================
        erros = []

        if not nome or len(nome) < 3:
            erros.append('Nome deve ter pelo menos 3 caracteres.')

        if not numero or not validar_numero_aluno(numero):
            erros.append('Número do aluno inválido.')

        # Verificar se o número já existe
        if Aluno.query.filter_by(numero=numero).first():
            erros.append(f'O número {numero} já está cadastrado.')

        if telefone_pai and not validar_telefone(telefone_pai):
            erros.append('Número de telefone do pai inválido.')

        # Verificar se foi enviada uma foto
        if 'foto' not in request.files or not request.files['foto'].filename:
            erros.append('É necessário enviar uma foto do aluno.')

        if erros:
            for erro in erros:
                flash(f'⚠️ {erro}', 'warning')
            return render_template('cadastro.html', dados=request.form)

        # ==========================================
        # PROCESSAR FOTO
        # ==========================================
        foto = request.files['foto']
        nome_ficheiro = f'{numero}_{nome.lower().replace(" ", "_")}.jpg'
        nome_ficheiro = secure_filename(nome_ficheiro)

        # Criar pasta de alunos se não existir
        pasta_alunos = current_app.config['ALUNOS_FOLDER']
        os.makedirs(pasta_alunos, exist_ok=True)

        # Caminho temporário e final
        caminho_temp = os.path.join(pasta_alunos, f'temp_{nome_ficheiro}')
        caminho_final = os.path.join(pasta_alunos, nome_ficheiro)

        # Guardar a foto temporariamente
        foto.save(caminho_temp)

        # Verificar qualidade da foto
        qualidade = verificar_qualidade_foto(caminho_temp)
        qualidade_minima = current_app.config['QUALIDADE_MINIMA']

        if qualidade['aprovada']:
            # Foto aprovada → redimensionar e guardar
            redimensionar_imagem(caminho_temp, caminho_final)
            os.remove(caminho_temp)  # remover temporária

            flash(
                f'✅ Foto aprovada! Qualidade: {qualidade["pontuacao_total"]}%',
                'success'
            )
        else:
            # Foto recusada → remover e mostrar dicas
            os.remove(caminho_temp)
            flash(
                f'❌ Foto recusada. Qualidade: {qualidade["pontuacao_total"]}% '
                f'(mínimo: {qualidade_minima}%)',
                'danger'
            )
            for dica in qualidade['dicas']:
                flash(dica, 'warning')
            return render_template('cadastro.html', dados=request.form)

        # ==========================================
        # GUARDAR NA BASE DE DADOS
        # ==========================================
        aluno = Aluno(
            nome=nome,
            numero=numero,
            turma=turma if turma else None,
            foto_path=f'alunos/{nome_ficheiro}',
            telefone_pai=telefone_pai if telefone_pai else None,
            nome_pai=nome_pai if nome_pai else None,
            activo=True,
        )

        try:
            db.session.add(aluno)
            db.session.commit()
            flash(f'🎉 Aluno {nome} cadastrado com sucesso!', 'success')
            return redirect(url_for('alunos.listar'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erro ao guardar: {str(e)}', 'danger')
            return render_template('cadastro.html', dados=request.form)

    # GET → mostrar formulário vazio
    return render_template('cadastro.html', dados={})


# ============================================================
# ROTA: DETALHES DO ALUNO
# ============================================================

@alunos_bp.route('/alunos/<int:id>')
@login_obrigatorio
def detalhes(id):
    """
    Página de detalhes de um aluno.
    Mostra dados pessoais, foto, histórico de registos e estatísticas.
    """
    aluno = Aluno.query.get_or_404(id)

    # Últimos 30 registos
    registos = Registo.query.filter_by(aluno_id=aluno.id).order_by(
        Registo.hora.desc()
    ).limit(30).all()

    # Estatísticas do mês atual
    hoje = datetime.now()
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0)

    entradas_mes = Registo.query.filter(
        Registo.aluno_id == aluno.id,
        Registo.tipo == 'entrada',
        Registo.hora >= inicio_mes
    ).count()

    saidas_mes = Registo.query.filter(
        Registo.aluno_id == aluno.id,
        Registo.tipo == 'saida',
        Registo.hora >= inicio_mes
    ).count()

    # Sessão atual (se estiver presente)
    sessao_ativa = SessaoAtiva.query.filter_by(
        aluno_id=aluno.id,
        hora_saida=None
    ).first()

    return render_template(
        'aluno_detalhes.html',
        aluno=aluno,
        registos=registos,
        entradas_mes=entradas_mes,
        saidas_mes=saidas_mes,
        sessao_ativa=sessao_ativa,
    )


# ============================================================
# ROTA: EDITAR ALUNO
# ============================================================

@alunos_bp.route('/alunos/<int:id>/editar', methods=['GET', 'POST'])
@login_obrigatorio
@admin_obrigatorio
def editar(id):
    """
    Página de edição de dados do aluno.
    """
    aluno = Aluno.query.get_or_404(id)

    if request.method == 'POST':
        aluno.nome = request.form.get('nome', aluno.nome).strip()
        aluno.turma = request.form.get('turma', '').strip() or None
        aluno.telefone_pai = request.form.get('telefone_pai', '').strip() or None
        aluno.nome_pai = request.form.get('nome_pai', '').strip() or None

        # Atualizar foto se for enviada uma nova
        if 'foto' in request.files and request.files['foto'].filename:
            foto = request.files['foto']
            nome_ficheiro = f'{aluno.numero}_{aluno.nome.lower().replace(" ", "_")}.jpg'
            nome_ficheiro = secure_filename(nome_ficheiro)

            pasta_alunos = current_app.config['ALUNOS_FOLDER']
            caminho_final = os.path.join(pasta_alunos, nome_ficheiro)

            # Guardar temporária para verificar qualidade
            caminho_temp = os.path.join(pasta_alunos, f'temp_{nome_ficheiro}')
            foto.save(caminho_temp)

            qualidade = verificar_qualidade_foto(caminho_temp)

            if qualidade['aprovada']:
                redimensionar_imagem(caminho_temp, caminho_final)
                os.remove(caminho_temp)
                aluno.foto_path = f'alunos/{nome_ficheiro}'
                flash('✅ Foto atualizada com sucesso!', 'success')
            else:
                os.remove(caminho_temp)
                flash(
                    f'❌ Foto recusada ({qualidade["pontuacao_total"]}%). '
                    'Os outros dados foram atualizados.',
                    'warning'
                )

        try:
            db.session.commit()
            flash('✅ Dados atualizados com sucesso!', 'success')
            return redirect(url_for('alunos.detalhes', id=aluno.id))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erro ao atualizar: {str(e)}', 'danger')

    return render_template('aluno_detalhes.html', aluno=aluno, modo_edicao=True)


# ============================================================
# ROTA: DESATIVAR ALUNO
# ============================================================

@alunos_bp.route('/alunos/<int:id>/desativar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def desativar(id):
    """
    Desativa um aluno (não remove da BD).
    """
    aluno = Aluno.query.get_or_404(id)
    aluno.activo = False

    try:
        db.session.commit()
        flash(f'🔒 Aluno {aluno.nome} desativado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro: {str(e)}', 'danger')

    return redirect(url_for('alunos.listar'))


# ============================================================
# ROTA: REATIVAR ALUNO
# ============================================================

@alunos_bp.route('/alunos/<int:id>/reativar', methods=['POST'])
@login_obrigatorio
@admin_obrigatorio
def reativar(id):
    """
    Reativa um aluno desativado.
    """
    aluno = Aluno.query.get_or_404(id)
    aluno.activo = True

    try:
        db.session.commit()
        flash(f'✅ Aluno {aluno.nome} reativado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro: {str(e)}', 'danger')

    return redirect(url_for('alunos.listar'))


# ============================================================
# API: BUSCAR ALUNO (AUTOCOMPLETE)
# ============================================================

@alunos_bp.route('/api/alunos/buscar')
@login_obrigatorio
def api_buscar():
    """
    API para autocomplete de alunos.
    Retorna JSON com alunos que correspondem à pesquisa.
    """
    termo = request.args.get('q', '').strip()

    if len(termo) < 2:
        return jsonify([])

    alunos = Aluno.query.filter(
        db.or_(
            Aluno.nome.ilike(f'%{termo}%'),
            Aluno.numero.ilike(f'%{termo}%')
        ),
        Aluno.activo == True
    ).limit(10).all()

    return jsonify([
        {
            'id': a.id,
            'nome': a.nome,
            'numero': a.numero,
            'turma': a.turma,
            'foto': a.foto_path,
        }
        for a in alunos
    ])


# ============================================================
# API: LISTAR ALUNOS (JSON)
# ============================================================

@alunos_bp.route('/api/alunos')
@login_obrigatorio
def api_listar():
    """
    API que retorna lista de alunos em JSON.
    Usado pelo sistema de reconhecimento e outras partes.
    """
    alunos = Aluno.query.filter_by(activo=True).order_by(Aluno.nome).all()
    return jsonify([a.to_dict() for a in alunos])