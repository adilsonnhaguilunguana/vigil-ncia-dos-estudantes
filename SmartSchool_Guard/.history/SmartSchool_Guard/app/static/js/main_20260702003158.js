/**
 * SmartSchool Guard - JavaScript Principal
 * Funções globais usadas em todas as páginas.
 */

// ============================================================
// CONFIGURAÇÕES GLOBAIS
// ============================================================

const CONFIG = {
    // Intervalos de polling (milissegundos)
    POLLING_DASHBOARD: 5000,    // 5 segundos
    POLLING_ALERTAS: 10000,     // 10 segundos
    POLLING_STATUS: 30000,      // 30 segundos

    // URLs das APIs
    API_DASHBOARD: '/api/dashboard/dados',
    API_PRESENTES: '/api/presentes',
    API_ALERTAS_NOVOS: '/api/alertas/novos',
    API_CAMARA_STATUS: '/api/camara/configurada',
    API_ESP_STATUS: '/api/esp/testar',
};

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    inicializarTooltips();
    inicializarPopovers();
    atualizarStatusSistema();
    iniciarPollingAlertas();

    // Atualizar status a cada 30 segundos
    setInterval(atualizarStatusSistema, CONFIG.POLLING_STATUS);
});

// ============================================================
// TOOLTIPS E POPOVERS (BOOTSTRAP)
// ============================================================

function inicializarTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
}

function inicializarPopovers() {
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => {
        new bootstrap.Popover(popover);
    });
}

// ============================================================
// NOTIFICAÇÕES TOAST
// ============================================================

function mostrarToast(mensagem, tipo = 'info', duracao = 5000) {
    // Criar container de toasts se não existir
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }

    // Cores por tipo
    const cores = {
        'success': 'bg-success text-white',
        'error': 'bg-danger text-white',
        'warning': 'bg-warning',
        'info': 'bg-info',
    };

    const icones = {
        'success': 'bi-check-circle-fill',
        'error': 'bi-x-circle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'info': 'bi-info-circle-fill',
    };

    // Criar elemento toast
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast ${cores[tipo] || cores['info']}" role="alert">
            <div class="toast-header">
                <i class="bi ${icones[tipo] || icones['info']} me-2"></i>
                <strong class="me-auto">SmartSchool Guard</strong>
                <small>Agora</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${mensagem}
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: duracao });
    toast.show();

    // Remover do DOM após esconder
    toastElement.addEventListener('hidden.bs.toast', function () {
        toastElement.remove();
    });
}

// ============================================================
// STATUS DO SISTEMA (CÂMARA + ESP)
// ============================================================

function atualizarStatusSistema() {
    atualizarStatusCamara();
    atualizarStatusESP();
}

function atualizarStatusCamara() {
    const badge = document.getElementById('status-camara');
    if (!badge) return;

    fetch(CONFIG.API_CAMARA_STATUS)
        .then(response => response.json())
        .then(data => {
            if (data.configurada && data.online) {
                badge.className = 'badge bg-success';
                badge.innerHTML = '<i class="bi bi-camera-video me-1"></i> Câmara: Online';
            } else if (data.configurada && !data.online) {
                badge.className = 'badge bg-danger';
                badge.innerHTML = '<i class="bi bi-camera-video-off me-1"></i> Câmara: Offline';
            } else {
                badge.className = 'badge bg-secondary';
                badge.innerHTML = '<i class="bi bi-camera-video-off me-1"></i> Câmara: --';
            }
        })
        .catch(() => {
            if (badge) {
                badge.className = 'badge bg-secondary';
                badge.innerHTML = '<i class="bi bi-camera-video-off me-1"></i> Câmara: --';
            }
        });
}

function atualizarStatusESP() {
    const badge = document.getElementById('status-esp');
    if (!badge) return;

    // O ESP só é verificado se houver IP configurado
    badge.className = 'badge bg-secondary';
    badge.innerHTML = '<i class="bi bi-cpu me-1"></i> ESP: --';
}

// ============================================================
// POLLING DE ALERTAS (BADGE NA NAVBAR)
// ============================================================

let ultimoAlertaId = 0;

function iniciarPollingAlertas() {
    setInterval(verificarNovosAlertas, CONFIG.POLLING_ALERTAS);
    verificarNovosAlertas(); // primeira verificação imediata
}

function verificarNovosAlertas() {
    const badge = document.getElementById('badge-alertas');
    if (!badge) return;

    fetch(`${CONFIG.API_ALERTAS_NOVOS}?ultimo_id=${ultimoAlertaId}`)
        .then(response => response.json())
        .then(data => {
            const total = data.total_ativos || 0;
            const novos = data.novos || [];

            // Atualizar badge
            if (total > 0) {
                badge.classList.remove('d-none');
                badge.textContent = total;
            } else {
                badge.classList.add('d-none');
            }

            // Atualizar último ID
            if (novos.length > 0) {
                ultimoAlertaId = Math.max(...novos.map(a => a.id));

                // Mostrar toast para cada novo alerta crítico
                novos.forEach(alerta => {
                    if (alerta.severidade === 'critico' || alerta.severidade === 'alerta') {
                        mostrarToast(
                            `🚨 Novo alerta: ${alerta.tipo.toUpperCase()} - ${alerta.descricao.substring(0, 50)}...`,
                            'error',
                            10000
                        );
                    }
                });
            }

            // Atualizar sidebar se existir
            const sidebarAlertas = document.getElementById('sidebar-alertas');
            if (sidebarAlertas) {
                sidebarAlertas.textContent = total;
            }
        })
        .catch(() => {
            // Silencioso - evita spam no console
        });
}

// ============================================================
// CONFIRMAÇÕES GENÉRICAS
// ============================================================

function confirmarAcao(mensagem, callback) {
    if (confirm(mensagem)) {
        callback();
    }
}

// ============================================================
// FORMATAÇÃO DE DADOS
// ============================================================

function formatarData(data) {
    if (!data) return '---';
    const d = new Date(data);
    return d.toLocaleDateString('pt-PT');
}

function formatarHora(data) {
    if (!data) return '---';
    const d = new Date(data);
    return d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
}

function formatarDataHora(data) {
    if (!data) return '---';
    const d = new Date(data);
    return d.toLocaleString('pt-PT');
}

function tempoPassado(data) {
    if (!data) return '---';

    const agora = new Date();
    const passado = new Date(data);
    const segundos = Math.floor((agora - passado) / 1000);

    if (segundos < 60) return 'agora mesmo';
    if (segundos < 3600) return `${Math.floor(segundos / 60)} min`;
    if (segundos < 86400) return `${Math.floor(segundos / 3600)}h`;
    return `${Math.floor(segundos / 86400)} dias`;
}

// ============================================================
// MANIPULAÇÃO DE URL
// ============================================================

function atualizarParametroURL(param, valor) {
    const url = new URL(window.location.href);
    if (valor) {
        url.searchParams.set(param, valor);
    } else {
        url.searchParams.delete(param);
    }
    window.location.href = url.toString();
}

function obterParametroURL(param) {
    const url = new URL(window.location.href);
    return url.searchParams.get(param) || '';
}

// ============================================================
// TELA CHEIA
// ============================================================

function alternarTelaCheia() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
    } else {
        document.exitFullscreen();
    }
}

// ============================================================
// SIDEBAR - ATUALIZAÇÃO DOS NÚMEROS
// ============================================================

function atualizarSidebar(dados) {
    const presentes = document.getElementById('sidebar-presentes');
    const entradas = document.getElementById('sidebar-entradas');
    const saidas = document.getElementById('sidebar-saidas');

    if (presentes) presentes.textContent = dados.presentes_hoje || '--';
    if (entradas) entradas.textContent = dados.entradas_hoje || '--';
    if (saidas) saidas.textContent = dados.saidas_hoje || '--';
}