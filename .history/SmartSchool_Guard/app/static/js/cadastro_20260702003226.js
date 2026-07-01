/**
 * SmartSchool Guard - Dashboard
 * Gerencia o painel principal com atualização em tempo real.
 */

let graficoMovimento = null;
let intervaloDashboard = null;

// ============================================================
// INICIALIZAÇÃO DO DASHBOARD
// ============================================================

function inicializarDashboard(dadosIniciais) {
    criarGraficoMovimento(dadosIniciais);
    iniciarPollingDashboard();

    // Botão Atualizar
    const btnAtualizar = document.getElementById('btn-atualizar');
    if (btnAtualizar) {
        btnAtualizar.addEventListener('click', function () {
            carregarDadosDashboard();
            atualizarGraficoMovimento();
            mostrarToast('Dashboard atualizado!', 'success', 2000);
        });
    }

    // Botão Tela Cheia
    const btnTelaCheia = document.getElementById('btn-tela-cheia');
    if (btnTelaCheia) {
        btnTelaCheia.addEventListener('click', alternarTelaCheia);
    }
}

// ============================================================
// POLLING DO DASHBOARD
// ============================================================

function iniciarPollingDashboard() {
    if (intervaloDashboard) clearInterval(intervaloDashboard);
    intervaloDashboard = setInterval(carregarDadosDashboard, CONFIG.POLLING_DASHBOARD);
}

function carregarDadosDashboard() {
    fetch(CONFIG.API_DASHBOARD)
        .then(response => response.json())
        .then(data => {
            atualizarCards(data);
            atualizarUltimosRegistos(data.ultimos_registos || []);
            atualizarSidebar(data);
            atualizarTimestamp();
        })
        .catch(error => {
            console.error('Erro ao carregar dados do dashboard:', error);
        });
}

// ============================================================
// ATUALIZAR CARDS
// ============================================================

function atualizarCards(data) {
    // Animar transição dos números
    animarValor('card-presentes', data.presentes_hoje || 0);
    animarValor('card-entradas', data.entradas_hoje || 0);
    animarValor('card-alertas', data.alertas_ativos || 0);
    animarValor('card-visitantes', data.visitantes_ativos || 0);

    // Atualizar lista de presentes
    if (data.alunos_presentes) {
        atualizarTabelaPresentes(data.alunos_presentes);
    }
}

function animarValor(elementoId, novoValor) {
    const elemento = document.getElementById(elementoId);
    if (!elemento) return;

    const valorAtual = parseInt(elemento.textContent) || 0;

    if (valorAtual === novoValor) {
        elemento.textContent = novoValor;
        return;
    }

    // Animação simples de contagem
    const duracao = 500; // ms
    const inicio = performance.now();
    const diff = novoValor - valorAtual;

    function atualizar(agora) {
        const decorrido = agora - inicio;
        const progresso = Math.min(decorrido / duracao, 1);

        // Easing ease-out
        const ease = 1 - Math.pow(1 - progresso, 3);
        const atual = Math.round(valorAtual + diff * ease);

        elemento.textContent = atual;

        if (progresso < 1) {
            requestAnimationFrame(atualizar);
        }
    }

    requestAnimationFrame(atualizar);
}

// ============================================================
// ATUALIZAR ÚLTIMOS REGISTOS
// ============================================================

function atualizarUltimosRegistos(registos) {
    const container = document.getElementById('lista-ultimos-registos');
    if (!container) return;

    if (!registos || registos.length === 0) {
        container.innerHTML = `
            <div class="list-group-item text-center text-muted py-4">
                <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                Nenhum registo hoje
            </div>
        `;
        return;
    }

    container.innerHTML = registos.map(r => `
        <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-2">
            <div>
                <small class="fw-bold d-block">${r.aluno_nome || 'Desconhecido'}</small>
                <small class="text-muted">
                    ${r.hora || '--:--:--'}
                    ${r.confianca ? ` · ${Math.round(r.confianca)}%` : ''}
                </small>
            </div>
            <span class="badge ${r.tipo === 'entrada' ? 'bg-success' : 'bg-warning'} rounded-pill">
                <i class="bi bi-box-arrow-${r.tipo === 'entrada' ? 'in' : ''}-right me-1"></i>
                ${r.tipo === 'entrada' ? 'Entrada' : 'Saída'}
            </span>
        </div>
    `).join('');
}

// ============================================================
// ATUALIZAR TABELA DE PRESENTES
// ============================================================

function atualizarTabelaPresentes(presentes) {
    const tbody = document.getElementById('tabela-alunos-presentes');
    const totalSpan = document.getElementById('total-presentes-lista');
    if (!tbody) return;

    if (totalSpan) {
        totalSpan.textContent = presentes.length;
    }

    if (!presentes || presentes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted py-4">
                    <i class="bi bi-emoji-neutral fs-3 d-block mb-2"></i>
                    Nenhum aluno presente no momento
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = presentes.map(p => `
        <tr>
            <td>
                <i class="bi bi-person-circle me-2 text-success"></i>
                ${p.nome}
            </td>
            <td>${p.turma || '---'}</td>
            <td>${p.hora_entrada || '--:--'}</td>
            <td>${p.tempo_presente || '---'}</td>
        </tr>
    `).join('');
}

// ============================================================
// GRÁFICO DE MOVIMENTO DIÁRIO
// ============================================================

function criarGraficoMovimento(dadosIniciais) {
    const ctx = document.getElementById('grafico-movimento');
    if (!ctx) return;

    if (graficoMovimento) {
        graficoMovimento.destroy();
    }

    graficoMovimento = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dadosIniciais.labels,
            datasets: [
                {
                    label: 'Entradas',
                    data: dadosIniciais.entradas,
                    backgroundColor: 'rgba(25, 135, 84, 0.7)',
                    borderColor: 'rgb(25, 135, 84)',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Saídas',
                    data: dadosIniciais.saidas,
                    backgroundColor: 'rgba(255, 193, 7, 0.7)',
                    borderColor: 'rgb(255, 193, 7)',
                    borderWidth: 1,
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                    },
                },
            },
        },
    });
}

function atualizarGraficoMovimento() {
    fetch('/api/dashboard/grafico-movimento')
        .then(response => response.json())
        .then(data => {
            if (graficoMovimento) {
                graficoMovimento.data.labels = data.horas;
                graficoMovimento.data.datasets[0].data = data.entradas;
                graficoMovimento.data.datasets[1].data = data.saidas;
                graficoMovimento.update();
            }
        })
        .catch(error => {
            console.error('Erro ao atualizar gráfico:', error);
        });
}

// ============================================================
// TIMESTAMP DE ATUALIZAÇÃO
// ============================================================

function atualizarTimestamp() {
    const elemento = document.getElementById('ultima-atualizacao');
    if (elemento) {
        const agora = new Date();
        elemento.textContent = `Atualizado: ${agora.toLocaleTimeString('pt-PT')}`;
    }
}