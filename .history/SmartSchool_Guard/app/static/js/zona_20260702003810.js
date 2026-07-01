/**
 * SmartSchool Guard - Configuração da Linha Virtual
 * Permite arrastar e configurar a linha de detecção no canvas.
 */

// ============================================================
// VARIÁVEIS GLOBAIS
// ============================================================

let canvas = null;
let ctx = null;
let linha = {
    x1: 0, y1: 300,
    x2: 1280, y2: 300
};
let arrastando = null;     // 'p1', 'p2', ou null
let offsetX = 0;
let offsetY = 0;
let escalaX = 1;
let escalaY = 1;

// Cores
const COR_LINHA = '#00e5ff';        // Ciano
const COR_PONTA = '#00b8d4';        // Ciano escuro
const COR_LINHA_ARRAS = '#ffab00';  // Âmbar (durante arrasto)
const COR_TEXTO = '#ffffff';

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    inicializarCanvas();
    carregarConfiguracaoAtual();
    inicializarBotoes();
});

function inicializarCanvas() {
    canvas = document.getElementById('canvas-zona');
    if (!canvas) return;

    ctx = canvas.getContext('2d');

    // Tamanho do canvas (responsivo)
    redimensionarCanvas();

    // Eventos de mouse
    canvas.addEventListener('mousedown', iniciarArrasto);
    canvas.addEventListener('mousemove', duranteArrasto);
    canvas.addEventListener('mouseup', finalizarArrasto);
    canvas.addEventListener('mouseleave', finalizarArrasto);

    // Eventos de toque (mobile)
    canvas.addEventListener('touchstart', iniciarArrastoTouch, { passive: false });
    canvas.addEventListener('touchmove', duranteArrastoTouch, { passive: false });
    canvas.addEventListener('touchend', finalizarArrasto);

    // Redimensionar quando a janela mudar
    window.addEventListener('resize', () => {
        redimensionarCanvas();
        desenharLinha();
    });
}

function redimensionarCanvas() {
    if (!canvas) return;

    const container = canvas.parentElement;
    const largura = container.clientWidth - 20;
    const altura = Math.min(largura * 0.5625, 500); // proporção 16:9

    canvas.width = largura;
    canvas.height = altura;

    // Escala baseada no tamanho original (1280x720)
    escalaX = largura / 1280;
    escalaY = altura / 720;
}

// ============================================================
// CARREGAR CONFIGURAÇÃO ATUAL
// ============================================================

function carregarConfiguracaoAtual() {
    fetch('/api/zona')
        .then(response => response.json())
        .then(data => {
            linha.x1 = data.x1;
            linha.y1 = data.y1;
            linha.x2 = data.x2;
            linha.y2 = data.y2;

            // Atualizar campos de input
            document.getElementById('input-x1').value = linha.x1;
            document.getElementById('input-y1').value = linha.y1;
            document.getElementById('input-x2').value = linha.x2;
            document.getElementById('input-y2').value = linha.y2;

            // Atualizar checkbox de ativação
            const checkboxAtiva = document.getElementById('checkbox-linha-ativa');
            if (checkboxAtiva) {
                checkboxAtiva.checked = data.ativa;
            }

            // Atualizar direção de entrada
            const selectDirecao = document.getElementById('select-direcao');
            if (selectDirecao && data.direcao_entrada) {
                selectDirecao.value = data.direcao_entrada;
            }

            desenharLinha();
        })
        .catch(error => {
            console.error('Erro ao carregar configuração da zona:', error);
            mostrarToast('Erro ao carregar configuração da linha virtual.', 'error');
        });
}

// ============================================================
// BOTÕES
// ============================================================

function inicializarBotoes() {
    const btnGuardar = document.getElementById('btn-guardar-zona');
    const btnRestaurar = document.getElementById('btn-restaurar-zona');
    const btnAtualizarCoords = document.getElementById('btn-atualizar-coordenadas');
    const checkboxAtiva = document.getElementById('checkbox-linha-ativa');

    if (btnGuardar) btnGuardar.addEventListener('click', guardarConfiguracao);
    if (btnRestaurar) btnRestaurar.addEventListener('click', restaurarPadrao);
    if (btnAtualizarCoords) btnAtualizarCoords.addEventListener('click', atualizarPorInput);
    if (checkboxAtiva) checkboxAtiva.addEventListener('change', alternarLinhaAtiva);
}

// ============================================================
// DESENHAR LINHA NO CANVAS
// ============================================================

function desenharLinha() {
    if (!ctx || !canvas) return;

    // Limpar canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Fundo escuro semi-transparente
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Converter coordenadas para escala do canvas
    const x1 = linha.x1 * escalaX;
    const y1 = linha.y1 * escalaY;
    const x2 = linha.x2 * escalaX;
    const y2 = linha.y2 * escalaY;

    // Desenhar grid de referência
    desenharGrid();

    // Desenhar linha tracejada de guia
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.setLineDash([]);

    // Desenhar linha principal
    const cor = arrastando ? COR_LINHA_ARRAS : COR_LINHA;
    ctx.strokeStyle = cor;
    ctx.lineWidth = 3;
    ctx.shadowColor = cor;
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Desenhar pontos de arrasto
    desenharPonta(x1, y1, 'P1');
    desenharPonta(x2, y2, 'P2');

    // Desenhar rótulos de direção
    desenharRotulos(x1, y1, x2, y2);

    // Atualizar coordenadas em tempo real
    atualizarDisplayCoordenadas();
}

function desenharGrid() {
    const passo = 50 * escalaX;

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 0.5;

    // Linhas verticais
    for (let x = 0; x < canvas.width; x += passo) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }

    // Linhas horizontais
    for (let y = 0; y < canvas.height; y += passo) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
}

function desenharPonta(x, y, rotulo) {
    // Círculo externo
    ctx.fillStyle = COR_PONTA;
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();

    // Círculo interno
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();

    // Rótulo
    ctx.fillStyle = COR_TEXTO;
    ctx.font = 'bold 12px Poppins, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(rotulo, x, y - 18);
}

function desenharRotulos(x1, y1, x2, y2) {
    const centroX = (x1 + x2) / 2;
    const centroY = (y1 + y2) / 2;

    ctx.fillStyle = 'rgba(0, 255, 100, 0.9)';
    ctx.font = 'bold 14px Poppins, sans-serif';
    ctx.textAlign = 'center';

    // Rótulo ENTRADA (acima da linha)
    ctx.fillText('⬇ ENTRADA', centroX, centroY - 20);

    // Rótulo SAÍDA (abaixo da linha)
    ctx.fillStyle = 'rgba(255, 100, 100, 0.9)';
    ctx.fillText('⬆ SAÍDA', centroX, centroY + 30);

    // Linha central indicando direção
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(centroX, centroY - 40);
    ctx.lineTo(centroX, centroY + 55);
    ctx.stroke();
    ctx.setLineDash([]);
}

function atualizarDisplayCoordenadas() {
    const displayX1 = document.getElementById('display-x1');
    const displayY1 = document.getElementById('display-y1');
    const displayX2 = document.getElementById('display-x2');
    const displayY2 = document.getElementById('display-y2');

    if (displayX1) displayX1.textContent = linha.x1;
    if (displayY1) displayY1.textContent = linha.y1;
    if (displayX2) displayX2.textContent = linha.x2;
    if (displayY2) displayY2.textContent = linha.y2;
}

// ============================================================
// ARRASTO (MOUSE)
// ============================================================

function iniciarArrasto(evento) {
    const mouse = obterPosicaoMouse(evento);
    arrastando = verificarPontoClicado(mouse.x, mouse.y);

    if (arrastando) {
        const ponto = arrastando === 'p1'
            ? { x: linha.x1 * escalaX, y: linha.y1 * escalaY }
            : { x: linha.x2 * escalaX, y: linha.y2 * escalaY };

        offsetX = mouse.x - ponto.x;
        offsetY = mouse.y - ponto.y;

        canvas.style.cursor = 'grabbing';
        evento.preventDefault();
    }
}

function duranteArrasto(evento) {
    if (!arrastando) return;

    const mouse = obterPosicaoMouse(evento);
    const x = Math.round((mouse.x - offsetX) / escalaX);
    const y = Math.round((mouse.y - offsetY) / escalaY);

    // Limitar ao frame (0-1280, 0-720)
    const xLimitado = Math.max(0, Math.min(1280, x));
    const yLimitado = Math.max(0, Math.min(720, y));

    if (arrastando === 'p1') {
        linha.x1 = xLimitado;
        linha.y1 = yLimitado;
    } else if (arrastando === 'p2') {
        linha.x2 = xLimitado;
        linha.y2 = yLimitado;
    }

    desenharLinha();
    evento.preventDefault();
}

function finalizarArrasto() {
    arrastando = null;
    if (canvas) canvas.style.cursor = 'default';
    desenharLinha();
}

// ============================================================
// ARRASTO (TOUCH)
// ============================================================

function iniciarArrastoTouch(evento) {
    if (evento.touches.length === 1) {
        evento.preventDefault();
        const touch = obterPosicaoTouch(evento);
        arrastando = verificarPontoClicado(touch.x, touch.y);

        if (arrastando) {
            const ponto = arrastando === 'p1'
                ? { x: linha.x1 * escalaX, y: linha.y1 * escalaY }
                : { x: linha.x2 * escalaX, y: linha.y2 * escalaY };

            offsetX = touch.x - ponto.x;
            offsetY = touch.y - ponto.y;
        }
    }
}

function duranteArrastoTouch(evento) {
    if (!arrastando || evento.touches.length !== 1) return;

    evento.preventDefault();
    const touch = obterPosicaoTouch(evento);
    const x = Math.round((touch.x - offsetX) / escalaX);
    const y = Math.round((touch.y - offsetY) / escalaY);

    const xLimitado = Math.max(0, Math.min(1280, x));
    const yLimitado = Math.max(0, Math.min(720, y));

    if (arrastando === 'p1') {
        linha.x1 = xLimitado;
        linha.y1 = yLimitado;
    } else if (arrastando === 'p2') {
        linha.x2 = xLimitado;
        linha.y2 = yLimitado;
    }

    desenharLinha();
}

// ============================================================
// UTILITÁRIOS DE POSIÇÃO
// ============================================================

function obterPosicaoMouse(evento) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: evento.clientX - rect.left,
        y: evento.clientY - rect.top,
    };
}

function obterPosicaoTouch(evento) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: evento.touches[0].clientX - rect.left,
        y: evento.touches[0].clientY - rect.top,
    };
}

function verificarPontoClicado(mouseX, mouseY) {
    const raio = 15; // raio de detecção do clique

    const p1x = linha.x1 * escalaX;
    const p1y = linha.y1 * escalaY;
    const p2x = linha.x2 * escalaX;
    const p2y = linha.y2 * escalaY;

    const distP1 = Math.sqrt((mouseX - p1x) ** 2 + (mouseY - p1y) ** 2);
    const distP2 = Math.sqrt((mouseX - p2x) ** 2 + (mouseY - p2y) ** 2);

    if (distP1 < raio) return 'p1';
    if (distP2 < raio) return 'p2';
    return null;
}

// ============================================================
// ATUALIZAR POR INPUT MANUAL
// ============================================================

function atualizarPorInput() {
    const x1 = parseInt(document.getElementById('input-x1').value);
    const y1 = parseInt(document.getElementById('input-y1').value);
    const x2 = parseInt(document.getElementById('input-x2').value);
    const y2 = parseInt(document.getElementById('input-y2').value);

    if (isNaN(x1) || isNaN(y1) || isNaN(x2) || isNaN(y2)) {
        mostrarToast('Preencha todas as coordenadas com valores numéricos.', 'warning');
        return;
    }

    linha.x1 = Math.max(0, Math.min(1280, x1));
    linha.y1 = Math.max(0, Math.min(720, y1));
    linha.x2 = Math.max(0, Math.min(1280, x2));
    linha.y2 = Math.max(0, Math.min(720, y2));

    desenharLinha();
    mostrarToast('Coordenadas atualizadas no canvas.', 'info');
}

// ============================================================
// GUARDAR CONFIGURAÇÃO
// ============================================================

function guardarConfiguracao() {
    const direcaoEntrada = document.getElementById('select-direcao')?.value || 'cima_para_baixo';

    const dados = {
        x1: linha.x1,
        y1: linha.y1,
        x2: linha.x2,
        y2: linha.y2,
        direcao_entrada: direcaoEntrada,
    };

    fetch('/api/zona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados),
    })
        .then(response => response.json())
        .then(data => {
            if (data.sucesso) {
                mostrarToast(data.mensagem || 'Linha virtual guardada com sucesso!', 'success');
            } else {
                mostrarToast(data.erro || 'Erro ao guardar.', 'error');
            }
        })
        .catch(error => {
            console.error('Erro ao guardar zona:', error);
            mostrarToast('Erro de conexão ao guardar.', 'error');
        });
}

// ============================================================
// RESTAURAR PADRÃO
// ============================================================

function restaurarPadrao() {
    if (!confirm('Restaurar a linha virtual para a posição padrão?\n(y=300, horizontal)')) {
        return;
    }

    fetch('/api/zona/restaurar', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.sucesso) {
                linha.x1 = data.coordenadas.x1;
                linha.y1 = data.coordenadas.y1;
                linha.x2 = data.coordenadas.x2;
                linha.y2 = data.coordenadas.y2;

                desenharLinha();
                mostrarToast('Linha virtual restaurada para o padrão.', 'info');
            }
        })
        .catch(error => {
            console.error('Erro ao restaurar:', error);
            mostrarToast('Erro ao restaurar.', 'error');
        });
}

// ============================================================
// ALTERNAR LINHA ATIVA
// ============================================================

function alternarLinhaAtiva(evento) {
    const ativa = evento.target.checked;

    fetch('/api/zona/ativar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ativa: ativa }),
    })
        .then(response => response.json())
        .then(data => {
            mostrarToast(data.mensagem, data.ativa ? 'success' : 'info');
        })
        .catch(error => {
            console.error('Erro ao alternar linha:', error);
            evento.target.checked = !ativa; // reverter
        });
}