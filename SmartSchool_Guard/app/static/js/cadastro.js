/**
 * SmartSchool Guard - Cadastro de Alunos
 * Streaming ao vivo via IP Webcam + captura quando o utilizador clica.
 */

let streamUrl = '';
let fotoCapturada = null;

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    carregarStreamCamara();
    inicializarBotoes();
    inicializarFormulario();
});

// ============================================================
// CARREGAR STREAM DA CÂMARA IP
// ============================================================

function carregarStreamCamara() {
    fetch('/api/camara')
        .then(response => response.json())
        .then(data => {
            if (data.ip && data.ip !== 'Não configurado') {
                streamUrl = `http://${data.ip}/video`;
                ligarStream();
            } else {
                mostrarAvisoCamaraNaoConfigurada();
            }
        })
        .catch(() => {
            mostrarAvisoCamaraNaoConfigurada();
        });
}

function ligarStream() {
    const video = document.getElementById('video-preview');
    const placeholder = document.getElementById('placeholder-camera');
    const btnCapturar = document.getElementById('btn-capturar');

    if (!video) return;

    // Mostrar o elemento de vídeo
    video.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';

    // Carregar o stream MJPEG da IP Webcam
    video.src = streamUrl;
    video.play().catch(() => {
        console.log('Tentando carregar stream...');
    });

    // Ativar botão de capturar
    if (btnCapturar) btnCapturar.disabled = false;

    // Atualizar status
    const statusBadge = document.getElementById('status-stream');
    if (statusBadge) {
        statusBadge.textContent = '📹 Stream ao vivo';
        statusBadge.className = 'badge bg-success';
    }
}

function mostrarAvisoCamaraNaoConfigurada() {
    const placeholder = document.getElementById('placeholder-camera');
    const video = document.getElementById('video-preview');
    const btnCapturar = document.getElementById('btn-capturar');

    if (video) video.style.display = 'none';
    if (placeholder) {
        placeholder.style.display = 'flex';
        placeholder.innerHTML = `
            <i class="bi bi-camera-video-off fs-1 mb-2 text-warning"></i>
            <p class="mb-1 fw-bold">Câmara IP não configurada</p>
            <small class="text-muted">
                Vá em <strong>Configurações → Câmara IP</strong> para configurar
            </small>
        `;
    }
    if (btnCapturar) btnCapturar.disabled = true;
}

// ============================================================
// BOTÕES
// ============================================================

function inicializarBotoes() {
    const btnCapturar = document.getElementById('btn-capturar');
    const btnNovaFoto = document.getElementById('btn-nova-foto');

    if (btnCapturar) btnCapturar.addEventListener('click', capturarFoto);
    if (btnNovaFoto) btnNovaFoto.addEventListener('click', resetarFoto);
}

// ============================================================
// CAPTURAR FOTO DO STREAM
// ============================================================

function capturarFoto() {
    const video = document.getElementById('video-preview');
    const canvas = document.getElementById('canvas-preview');
    const fotoPreview = document.getElementById('foto-preview');
    const previewContainer = document.getElementById('preview-container');
    const qualidadeContainer = document.getElementById('qualidade-container');
    const inputFile = document.getElementById('input-foto');
    const btnCapturar = document.getElementById('btn-capturar');
    const btnNovaFoto = document.getElementById('btn-nova-foto');

    if (!video || !video.src) {
        mostrarToast('⚠️ Stream da câmara não está ativo.', 'warning');
        return;
    }

    // Configurar canvas com o tamanho do vídeo
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    // Desenhar o frame atual do vídeo no canvas
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Converter para blob
    canvas.toBlob(function (blob) {
        fotoCapturada = new File([blob], 'captura.jpg', { type: 'image/jpeg' });

        // Mostrar preview
        const url = URL.createObjectURL(blob);
        fotoPreview.src = url;
        previewContainer.classList.remove('d-none');

        // Atualizar input file
        const dt = new DataTransfer();
        dt.items.add(fotoCapturada);
        inputFile.files = dt.files;

        // Verificar qualidade
        if (qualidadeContainer) {
            qualidadeContainer.classList.remove('d-none');
            verificarQualidadePreview(blob);
        }

        // Esconder stream, mostrar preview
        video.style.display = 'none';
        previewContainer.style.display = 'block';

        // Atualizar botões
        if (btnCapturar) btnCapturar.style.display = 'none';
        if (btnNovaFoto) btnNovaFoto.style.display = 'inline-block';

        mostrarToast('📸 Foto capturada! Se não estiver boa, clique em "Nova Foto".', 'success');

    }, 'image/jpeg', 0.9);
}

// ============================================================
// TIRAR NOVA FOTO (VOLTAR AO STREAM)
// ============================================================

function resetarFoto() {
    const video = document.getElementById('video-preview');
    const previewContainer = document.getElementById('preview-container');
    const qualidadeContainer = document.getElementById('qualidade-container');
    const inputFile = document.getElementById('input-foto');
    const btnCapturar = document.getElementById('btn-capturar');
    const btnNovaFoto = document.getElementById('btn-nova-foto');

    // Limpar
    fotoCapturada = null;
    inputFile.value = '';

    // Mostrar stream de novo
    video.style.display = 'block';
    previewContainer.style.display = 'none';
    if (qualidadeContainer) qualidadeContainer.classList.add('d-none');

    // Atualizar botões
    if (btnCapturar) btnCapturar.style.display = 'inline-block';
    if (btnNovaFoto) btnNovaFoto.style.display = 'none';

    mostrarToast('📹 Pode capturar novamente.', 'info');
}

// ============================================================
// VERIFICAÇÃO DE QUALIDADE (CLIENTE)
// ============================================================

function verificarQualidadePreview(blob) {
    const barra = document.getElementById('barra-qualidade');
    const texto = document.getElementById('texto-qualidade');
    const dicas = document.getElementById('dicas-qualidade');

    if (!barra) return;

    const img = new Image();
    img.src = URL.createObjectURL(blob);

    img.onload = function () {
        let pontuacao = 0;
        let mensagens = [];

        // Resolução
        if (img.width >= 300 && img.height >= 300) {
            pontuacao += 15;
        } else {
            mensagens.push('📏 Resolução baixa.');
        }

        // Proporção
        const proporcao = img.width / img.height;
        if (proporcao > 0.5 && proporcao < 2.0) {
            pontuacao += 10;
        }

        // Tamanho do ficheiro
        if (blob.size > 50000) {
            pontuacao += 10;
        }

        // Base para nitidez e rosto (verificado pelo servidor)
        pontuacao += 40;

        pontuacao = Math.min(pontuacao, 100);

        // Animar
        let progresso = 0;
        const intervalo = setInterval(() => {
            progresso += 3;
            if (progresso >= pontuacao) {
                progresso = pontuacao;
                clearInterval(intervalo);

                if (pontuacao >= 70) {
                    barra.className = 'progress-bar bg-success';
                    dicas.innerHTML = '<span class="text-success">✅ Pré-análise OK. O servidor fará a verificação final.</span>';
                } else {
                    barra.className = 'progress-bar bg-warning';
                    dicas.innerHTML = '<span class="text-warning">⚠️ Tente melhorar a iluminação e posicionar o rosto.</span>';
                }
            }
            barra.style.width = progresso + '%';
            texto.textContent = progresso + '%';
        }, 20);
    };
}

// ============================================================
// FORMULÁRIO
// ============================================================

function inicializarFormulario() {
    const form = document.getElementById('form-cadastro');
    if (!form) return;

    form.addEventListener('submit', function (evento) {
        const inputFile = document.getElementById('input-foto');

        if (!inputFile || !inputFile.files || inputFile.files.length === 0) {
            evento.preventDefault();
            mostrarToast('⚠️ Capture uma foto primeiro.', 'warning');
            return false;
        }

        const nome = document.getElementById('nome');
        if (nome && nome.value.trim().length < 3) {
            evento.preventDefault();
            mostrarToast('⚠️ Nome deve ter pelo menos 3 caracteres.', 'warning');
            nome.focus();
            return false;
        }

        const numero = document.getElementById('numero');
        if (numero && !numero.value.trim()) {
            evento.preventDefault();
            mostrarToast('⚠️ Número do aluno é obrigatório.', 'warning');
            numero.focus();
            return false;
        }

        return true;
    });
}