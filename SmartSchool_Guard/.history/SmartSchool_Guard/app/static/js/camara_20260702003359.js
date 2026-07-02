/**
 * SmartSchool Guard - Configuração da Câmara IP
 * Gerencia o teste e salvamento do IP da câmara.
 */

document.addEventListener('DOMContentLoaded', function () {
    inicializarPaginaCamara();
});

function inicializarPaginaCamara() {
    const btnTestar = document.getElementById('btn-testar');
    const btnGuardar = document.getElementById('btn-guardar');

    if (btnTestar) btnTestar.addEventListener('click', testarCamara);
    if (btnGuardar) btnGuardar.addEventListener('click', guardarCamara);

    // Verificar status atual
    verificarStatusAtual();
}

// ============================================================
// VERIFICAR STATUS ATUAL
// ============================================================

function verificarStatusAtual() {
    fetch('/api/camara/configurada')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('status-badge');
            if (!badge) return;

            if (data.configurada && data.online) {
                badge.className = 'badge bg-success ms-2';
                badge.textContent = 'Online';
            } else if (data.configurada && !data.online) {
                badge.className = 'badge bg-danger ms-2';
                badge.textContent = 'Offline';
            } else {
                badge.className = 'badge bg-secondary ms-2';
                badge.textContent = 'Não configurada';
            }
        })
        .catch(() => {
            const badge = document.getElementById('status-badge');
            if (badge) {
                badge.className = 'badge bg-secondary ms-2';
                badge.textContent = 'Erro';
            }
        });
}

// ============================================================
// TESTAR LIGAÇÃO
// ============================================================

function testarCamara() {
    const inputIP = document.getElementById('input-ip');
    const resultadoDiv = document.getElementById('resultado-teste');
    const previewImg = document.getElementById('preview-imagem');
    const placeholder = document.getElementById('preview-placeholder');

    if (!inputIP || !inputIP.value.trim()) {
        mostrarToast('Digite o IP da câmara primeiro.', 'warning');
        return;
    }

    const ip = inputIP.value.trim();

    // Mostrar loading
    if (resultadoDiv) {
        resultadoDiv.classList.remove('d-none');
        resultadoDiv.innerHTML = `
            <div class="alert alert-info">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                A testar ligação para <strong>${ip}</strong>...
            </div>
        `;
    }

    fetch('/api/camara/testar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: ip }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.online) {
                // Mostrar sucesso
                if (resultadoDiv) {
                    resultadoDiv.innerHTML = `
                        <div class="alert alert-success">
                            <i class="bi bi-check-circle-fill me-2"></i>
                            ${data.mensagem}
                        </div>
                    `;
                }

                // Mostrar preview
                if (previewImg && placeholder) {
                    previewImg.src = `/api/camara/snapshot?t=${Date.now()}`;
                    previewImg.style.display = 'block';
                    placeholder.style.display = 'none';
                }

                mostrarToast('Câmara online!', 'success');

            } else {
                // Mostrar erro com dicas
                if (resultadoDiv) {
                    let html = `
                        <div class="alert alert-danger">
                            <i class="bi bi-x-circle-fill me-2"></i>
                            ${data.erro || 'Não foi possível ligar à câmara.'}
                        </div>
                    `;

                    if (data.dicas && data.dicas.length > 0) {
                        html += '<div class="alert alert-warning"><strong>Dicas:</strong><ul class="mb-0 mt-1">';
                        data.dicas.forEach(dica => {
                            html += `<li>${dica}</li>`;
                        });
                        html += '</ul></div>';
                    }

                    resultadoDiv.innerHTML = html;
                }

                // Esconder preview
                if (previewImg && placeholder) {
                    previewImg.style.display = 'none';
                    placeholder.style.display = 'flex';
                }

                mostrarToast('Câmara offline. Verifique as dicas.', 'warning');
            }
        })
        .catch(error => {
            console.error('Erro ao testar câmara:', error);
            if (resultadoDiv) {
                resultadoDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        Erro de conexão. Verifique a rede.
                    </div>
                `;
            }
            mostrarToast('Erro ao testar a câmara.', 'error');
        });
}

// ============================================================
// GUARDAR IP
// ============================================================

function guardarCamara() {
    const inputIP = document.getElementById('input-ip');

    if (!inputIP || !inputIP.value.trim()) {
        mostrarToast('Digite o IP da câmara primeiro.', 'warning');
        return;
    }

    const ip = inputIP.value.trim();

    fetch('/api/camara/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: ip }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.sucesso) {
                // Atualizar IP atual
                const ipAtual = document.getElementById('ip-atual');
                if (ipAtual) ipAtual.textContent = ip;

                // Atualizar badge
                const badge = document.getElementById('status-badge');
                if (badge) {
                    if (data.online) {
                        badge.className = 'badge bg-success ms-2';
                        badge.textContent = 'Online';
                    } else {
                        badge.className = 'badge bg-warning ms-2';
                        badge.textContent = 'Guardado (Offline)';
                    }
                }

                mostrarToast(data.mensagem, data.online ? 'success' : 'warning');

            } else {
                mostrarToast(data.erro || 'Erro ao guardar.', 'error');
            }
        })
        .catch(error => {
            console.error('Erro ao guardar IP:', error);
            mostrarToast('Erro ao guardar o IP.', 'error');
        });
}