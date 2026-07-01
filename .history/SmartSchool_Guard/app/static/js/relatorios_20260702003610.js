/**
 * SmartSchool Guard - Relatórios
 * Gerencia gráficos e exportação de relatórios.
 */

let graficoFrequencia = null;
let graficoAssiduidade = null;
let graficoHorasPico = null;

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    const tipo = obterParametroURL('tipo') || 'frequencia';

    switch (tipo) {
        case 'frequencia':
            carregarFrequenciaDiaria();
            break;
        case 'assiduidade':
            carregarAssiduidadeTurma();
            break;
        case 'horas-pico':
            carregarHorasPico();
            break;
        case 'atrasos':
            carregarAtrasos();
            break;
    }
});

// ============================================================
// FREQUÊNCIA DIÁRIA
// ============================================================

function carregarFrequenciaDiaria() {
    const dataInicio = obterParametroURL('data_inicio') || '';
    const dataFim = obterParametroURL('data_fim') || '';
    const turma = obterParametroURL('turma') || '';

    fetch(`/api/relatorios/frequencia-diaria?data_inicio=${dataInicio}&data_fim=${dataFim}&turma=${turma}`)
        .then(response => response.json())
        .then(data => {
            if (!data || data.erro) {
                console.error('Erro:', data?.erro);
                return;
            }

            const ctx = document.getElementById('grafico-frequencia');
            if (!ctx) return;

            if (graficoFrequencia) graficoFrequencia.destroy();

            graficoFrequencia = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => formatarData(d.data)),
                    datasets: [
                        {
                            label: 'Entradas',
                            data: data.map(d => d.entradas),
                            borderColor: 'rgb(25, 135, 84)',
                            backgroundColor: 'rgba(25, 135, 84, 0.1)',
                            fill: true,
                            tension: 0.3,
                        },
                        {
                            label: 'Saídas',
                            data: data.map(d => d.saidas),
                            borderColor: 'rgb(255, 193, 7)',
                            backgroundColor: 'rgba(255, 193, 7, 0.1)',
                            fill: true,
                            tension: 0.3,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                    },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } },
                    },
                },
            });
        })
        .catch(error => console.error('Erro ao carregar frequência:', error));
}

// ============================================================
// ASSIDUIDADE POR TURMA
// ============================================================

function carregarAssiduidadeTurma() {
    const dataInicio = obterParametroURL('data_inicio') || '';
    const dataFim = obterParametroURL('data_fim') || '';

    fetch(`/api/relatorios/assiduidade-turma?data_inicio=${dataInicio}&data_fim=${dataFim}`)
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('grafico-assiduidade');
            if (!ctx) return;

            if (graficoAssiduidade) graficoAssiduidade.destroy();

            const cores = data.map(d => {
                if (d.percentagem >= 90) return 'rgba(25, 135, 84, 0.7)';
                if (d.percentagem >= 75) return 'rgba(255, 193, 7, 0.7)';
                return 'rgba(220, 53, 69, 0.7)';
            });

            graficoAssiduidade = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.turma),
                    datasets: [{
                        label: 'Assiduidade (%)',
                        data: data.map(d => d.percentagem),
                        backgroundColor: cores,
                        borderRadius: 4,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } },
                    },
                },
            });
        })
        .catch(error => console.error('Erro ao carregar assiduidade:', error));
}

// ============================================================
// HORAS DE PICO
// ============================================================

function carregarHorasPico() {
    const dataInicio = obterParametroURL('data_inicio') || '';
    const dataFim = obterParametroURL('data_fim') || '';

    fetch(`/api/relatorios/horas-pico?data_inicio=${dataInicio}&data_fim=${dataFim}`)
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('grafico-horas-pico');
            if (!ctx) return;

            if (graficoHorasPico) graficoHorasPico.destroy();

            graficoHorasPico = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.horas,
                    datasets: [
                        {
                            label: 'Entradas',
                            data: data.entradas,
                            backgroundColor: 'rgba(25, 135, 84, 0.7)',
                            borderRadius: 4,
                        },
                        {
                            label: 'Saídas',
                            data: data.saidas,
                            backgroundColor: 'rgba(255, 193, 7, 0.7)',
                            borderRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top' } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });
        })
        .catch(error => console.error('Erro ao carregar horas de pico:', error));
}

// ============================================================
// EXPORTAÇÃO
// ============================================================

function exportarCSV(tipo) {
    const params = new URLSearchParams(window.location.search);
    let url = `/relatorios/exportar/csv?${params.toString()}`;

    if (tipo === 'alunos') {
        url = '/relatorios/exportar/alunos-csv';
    }

    window.open(url, '_blank');
}