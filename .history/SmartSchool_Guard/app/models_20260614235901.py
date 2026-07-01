"""
Modelos da base de dados (tabelas) usando SQLAlchemy ORM.

Tabelas:
- alunos          → alunos cadastrados no sistema
- registos        → histórico de entradas e saídas
- visitantes      → visitantes autorizados
- alertas         → alertas de segurança
- configuracoes   → configurações do sistema (inclui IP da câmara)
- utilizadores    → contas de acesso ao dashboard
- historico_ips   → histórico de IPs da câmara
- sessoes_ativas  → alunos atualmente dentro da escola
"""

from datetime import datetime
from app.database import db


# ============================================================
# TABELA: alunos
# ============================================================
class Aluno(db.Model):
    __tablename__ = 'alunos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    turma = db.Column(db.String(20))
    foto_path = db.Column(db.String(255))
    embedding_path = db.Column(db.String(255))
    telefone_pai = db.Column(db.String(20))
    nome_pai = db.Column(db.String(100))
    data_cadastro = db.Column(db.DateTime, default=datetime.now)
    activo = db.Column(db.Boolean, default=True)
    presente = db.Column(db.Boolean, default=False)

    # Relações
    registos = db.relationship('Registo', backref='aluno', lazy=True)
    sessoes = db.relationship('SessaoAtiva', backref='aluno', lazy=True)

    def __repr__(self):
        return f'<Aluno {self.numero} - {self.nome}>'

    def to_dict(self):
        """Converte o aluno para dicionário (API JSON)."""
        return {
            'id': self.id,
            'nome': self.nome,
            'numero': self.numero,
            'turma': self.turma,
            'foto_path': self.foto_path,
            'telefone_pai': self.telefone_pai,
            'nome_pai': self.nome_pai,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'activo': self.activo,
            'presente': self.presente,
        }


# ============================================================
# TABELA: registos
# ============================================================
class Registo(db.Model):
    __tablename__ = 'registos'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    tipo = db.Column(db.String(10))          # 'entrada' ou 'saida'
    hora = db.Column(db.DateTime, default=datetime.now)
    confianca = db.Column(db.Float)           # percentagem DeepFace
    direcao = db.Column(db.String(20))        # 'entrada' ou 'saida'
    notificado = db.Column(db.Boolean, default=False)
    frame_path = db.Column(db.String(255))    # foto do momento
    metodo = db.Column(db.String(20), default='facial')  # 'facial', 'manual', 'emergencia'
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f'<Registo {self.tipo} - {self.hora}>'

    def to_dict(self):
        """Converte o registo para dicionário (API JSON)."""
        return {
            'id': self.id,
            'aluno_id': self.aluno_id,
            'aluno_nome': self.aluno.nome if self.aluno else None,
            'tipo': self.tipo,
            'hora': self.hora.isoformat() if self.hora else None,
            'confianca': self.confianca,
            'direcao': self.direcao,
            'notificado': self.notificado,
            'metodo': self.metodo,
        }


# ============================================================
# TABELA: visitantes
# ============================================================
class Visitante(db.Model):
    __tablename__ = 'visitantes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    motivo = db.Column(db.String(255))
    hora_entrada = db.Column(db.DateTime, default=datetime.now)
    hora_saida = db.Column(db.DateTime)
    autorizado_por = db.Column(db.String(100))
    pin = db.Column(db.String(6))            # código de acesso temporário

    def __repr__(self):
        return f'<Visitante {self.nome}>'

    def to_dict(self):
        """Converte o visitante para dicionário (API JSON)."""
        return {
            'id': self.id,
            'nome': self.nome,
            'motivo': self.motivo,
            'hora_entrada': self.hora_entrada.isoformat() if self.hora_entrada else None,
            'hora_saida': self.hora_saida.isoformat() if self.hora_saida else None,
            'autorizado_por': self.autorizado_por,
            'pin': self.pin,
        }


# ============================================================
# TABELA: alertas
# ============================================================
class Alerta(db.Model):
    __tablename__ = 'alertas'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50))           # 'desconhecido', 'emergencia'
    descricao = db.Column(db.Text)
    hora = db.Column(db.DateTime, default=datetime.now)
    resolvido = db.Column(db.Boolean, default=False)
    frame_path = db.Column(db.String(255))    # foto do momento do alerta
    severidade = db.Column(db.String(20), default='medio')
    # severidade: 'info', 'aviso', 'alerta', 'critico'

    def __repr__(self):
        return f'<Alerta {self.tipo} - {self.hora}>'

    def to_dict(self):
        """Converte o alerta para dicionário (API JSON)."""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'descricao': self.descricao,
            'hora': self.hora.isoformat() if self.hora else None,
            'resolvido': self.resolvido,
            'frame_path': self.frame_path,
            'severidade': self.severidade,
        }


# ============================================================
# TABELA: configuracoes
# ============================================================
class Configuracao(db.Model):
    __tablename__ = 'configuracoes'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.Text)
    atualizado_em = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Configuracao {self.chave}={self.valor}>'


# ============================================================
# TABELA: utilizadores (acesso ao dashboard)
# ============================================================
class Utilizador(db.Model):
    __tablename__ = 'utilizadores'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='porteiro')  # 'admin' ou 'porteiro'
    activo = db.Column(db.Boolean, default=True)
    ultimo_acesso = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Utilizador {self.username} ({self.role})>'


# ============================================================
# TABELA: historico_ips (histórico de IPs da câmara)
# ============================================================
class HistoricoIP(db.Model):
    __tablename__ = 'historico_ips'

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    adicionado_por = db.Column(db.String(100))
    data = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<HistoricoIP {self.ip} - {self.data}>'


# ============================================================
# TABELA: sessoes_ativas (alunos dentro da escola)
# ============================================================
class SessaoAtiva(db.Model):
    __tablename__ = 'sessoes_ativas'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    hora_entrada = db.Column(db.DateTime, default=datetime.now)
    hora_saida = db.Column(db.DateTime)

    def __repr__(self):
        return f'<SessaoAtiva Aluno {self.aluno_id}>'

    def to_dict(self):
        """Converte a sessão para dicionário (API JSON)."""
        return {
            'id': self.id,
            'aluno_id': self.aluno_id,
            'aluno_nome': self.aluno.nome if self.aluno else None,
            'aluno_turma': self.aluno.turma if self.aluno else None,
            'hora_entrada': self.hora_entrada.isoformat() if self.hora_entrada else None,
            'hora_saida': self.hora_saida.isoformat() if self.hora_saida else None,
        }