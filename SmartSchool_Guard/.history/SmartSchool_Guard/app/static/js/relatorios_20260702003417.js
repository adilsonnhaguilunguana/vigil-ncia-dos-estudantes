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
                            backgroundColor: 'rgba(25, 135,