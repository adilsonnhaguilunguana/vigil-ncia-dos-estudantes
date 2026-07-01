/**
 * SmartSchool Guard - Cadastro de Alunos
 * Gerencia captura de foto via webcam e validação do formulário.
 */

let stream = null;
let fotoCapturada = null;

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    inicializarBotoesCamera();
    inicializarFormulario();
});

// ============================================================
// BOTÕES DA CÂMARA
// ============================================================

function inicializarBotoesCamera() {
    const btnLigar = document.getElementById('btn-ligar-camera');
    const btnCapturar = document.getElementById('btn-capturar');
    const btnDesligar = document.getElementById('btn-desligar-camera');

    if (btnLigar) btnLigar.addEventListener('click', ligarCamera);
    if (btnCapturar) btnCapturar.addEventListener('click', capturarFoto);
    if (btnDesligar) btnDesligar.addEventListener('click', desligarCamera);
}

async function ligarCamera() {
    const video = document.getElementById('video-preview');
    const placeholder = document.getElementById('placeholder-camera');
    const btnLigar = document.getElementById('btn-ligar-camera');
    const btnCapturar = document.getElementById('btn-capturar');
    const btnDesligar = document.getElementById('btn-desligar-camera');

    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user',
            },
        });

        video.srcObject = stream;
        video.style.display = 'block';
        placeholder.style.display = 'none';

        btnLigar.disabled = true;
        btnCapturar.disabled = false;
        btnDesligar.disabled = false;

        mostrarToast('Câmara ligada! Posicione o rosto e clique em Capturar.', 'success');

    } catch (error) {
        console.error('Erro ao aceder à câmara:', error);
        mostrarToast('Erro ao aceder à câmara. Verifique as permissões.', 'error');
    }
}

function capturarFoto() {
    const video = document.getElementById('video-preview');
    const canvas = document.getElementById('canvas-preview');
    const fotoPreview = document.getElementById('foto-preview');
    const previewContainer = document.getElementById('preview-container');
    const inputFile = document.getElementById('input-foto');
    const qualidadeContainer = document.getElementById('qualidade-container');

    if (!video || !canvas || !stream) return;

    // Configurar canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Desenhar frame no canvas
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Converter para blob e criar File
    canvas.toBlob(function (blob) {
        fotoCapturada = new File([blob], 'captura.jpg', { type: 'image/jpeg' });

        // Mostrar preview
        const url = URL.createObjectURL(blob);
        fotoPreview.src = url;
        previewContainer.classList.remove('d-none');

        // Criar DataTransfer para o input file
        const dt = new DataTransfer();
        dt.items.add(fotoCapturada);
        inputFile.files = dt.files;

        // Simular verificação de qualidade
        simularVerificacaoQualidade();

        mostrarToast('Foto capturada!', 'success');

    }, 'image/jpeg', 0.9);
}

function desligarCamera() {
    const video = document.getElementById('video-preview');
    const placeholder = document.getElementById('placeholder-camera');
    const btnLigar = document.getElementById('btn-ligar-camera');
    const btnCapturar = document.getElementById('btn-capturar');
    const btnDesligar = document.getElementById('btn-desligar-camera');

    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }

    video.srcObject = null;
    video.style.display = 'none';
    placeholder.style.display = 'flex';

    btnLigar.disabled = false;
    btnCapturar.disabled = true;
    btnDesligar.disabled = true;
}

// ============================================================
// SIMULAÇÃO DE VERIFICAÇÃO DE QUALIDADE
// ============================================================

function simularVerificacaoQualidade() {
    const container = document.getElementById('qualidade-container');
    const barra = document.getElementById('barra-qualidade');
    const texto = document.getElementById('texto-qualidade');
    const dicas = document.getElementById('dicas-qualidade');

    if (!container || !barra) return;

    container.classList.remove('d-none');

    // Simular score aleatório entre 55 e 95
    const score = Math.floor(Math.random() * 41) + 55;

    // Animar barra de progresso
    let progresso = 0;
    const intervalo = setInterval(() => {
        progresso += 2;
        barra.style.width = progresso + '%';
        barra.setAttribute('aria-valuenow', progresso);
        texto.textContent = progresso + '%';

        if (progresso >= score) {
            clearInterval(intervalo);

            // Definir cor
            if (score >= 80) {
                barra.className = 'progress-bar bg-success';
            } else if (score >= 60) {
                barra.className = 'progress-bar bg-warning';
            } else {
                barra.className = 'progress-bar bg-danger';
            }

            texto.textContent = score + '%';

            if (score >= 60) {
                dicas.innerHTML = '<span class="text-success">✅ Qualidade aceitável!</span>';
            } else {
                dicas.innerHTML = '<span class="text-danger">❌ Qualidade baixa. Tente novamente com melhor iluminação.</span>';
            }
        }
    }, 30);
}

// ============================================================
// VALIDAÇÃO DO FORMULÁRIO
// ============================================================

function inicializarFormulario() {
    const form = document.getElementById('form-cadastro');
    if (!form) return;

    form.addEventListener('submit', function (evento) {
        const inputFile = document.getElementById('input-foto');

        if (!inputFile || !inputFile.files || inputFile.files.length === 0) {
            evento.preventDefault();
            mostrarToast('É necessário capturar uma foto do aluno.', 'warning');
            return false;
        }

        const nome = document.getElementById('nome');
        const numero = document.getElementById('numero');

        if (nome && nome.value.trim().length < 3) {
            evento.preventDefault();
            mostrarToast('O nome deve ter pelo menos 3 caracteres.', 'warning');
            nome.focus();
            return false;
        }

        if (numero && !numero.value.trim()) {
            evento.preventDefault();
            mostrarToast('O número do aluno é obrigatório.', 'warning');
            numero.focus();
            return false;
        }

        return true;
    });
}