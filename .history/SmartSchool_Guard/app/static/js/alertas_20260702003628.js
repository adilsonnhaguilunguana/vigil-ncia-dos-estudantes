/**
 * SmartSchool Guard - Alertas
 * Gerencia polling e exibição de alertas.
 */

// ============================================================
// RESOLVER ALERTA (COM CONFIRMAÇÃO)
// ============================================================

function resolverAlerta(id, nome) {
    if (confirm(`Deseja marcar o alerta como resolvido?\n\n"${nome}"`)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/alertas/${id}/resolver`;

        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            input.value = csrfToken.content;
            form.appendChild(input);
        }

        document.body.appendChild(form);
        form.submit();
    }
}

// ============================================================
// FILTROS DE ALERTAS
// ============================================================

function filtrarPorSeveridade(severidade) {
    atualizarParametroURL('severidade', severidade);
}

function filtrarPorTipo(tipo) {
    atualizarParametroURL('tipo', tipo);
}

function filtrarPendentes() {
    atualizarParametroURL('resolvido', '0');
}

function filtrarResolvidos() {
    atualizarParametroURL('resolvido', '1');
}