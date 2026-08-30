async function obtenerInfo() {
    const url = document.getElementById('videoUrl').value;
    const msg = document.getElementById('statusMsg');
    const preview = document.getElementById('preview');

    if (!url) {
        msg.textContent = "Por favor ingresa un enlace.";
        return;
    }

    msg.textContent = "Analizando video y obteniendo formatos...";
    preview.style.display = 'none';

    try {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('thumb').src = data.thumbnail;
            document.getElementById('videoTitle').textContent = data.title;
            
            const select = document.getElementById('formatSelect');
            select.innerHTML = '';

            data.formats.forEach(f => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify({ format_id: f.format_id, type: f.type });
                opt.textContent = f.label;
                select.appendChild(opt);
            });

            preview.style.display = 'block';
            msg.textContent = "";
        } else {
            msg.textContent = "Error: " + (data.error || "No se pudo obtener el video.");
        }
    } catch (err) {
        msg.textContent = "Error al conectar con el servidor.";
    }
}

async function descargar() {
    const url = document.getElementById('videoUrl').value;
    const formatValue = document.getElementById('formatSelect').value;
    const msg = document.getElementById('statusMsg');

    if (!formatValue) return;

    const selectedFormat = JSON.parse(formatValue);
    msg.textContent = "Procesando descarga, por favor espera un momento...";

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                format_id: selectedFormat.format_id,
                type: selectedFormat.type
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = "video_descargado";
            document.body.appendChild(a);
            a.click();
            a.remove();
            msg.textContent = "¡Descarga iniciada con éxito!";
        } else {
            msg.textContent = "Error al procesar la descarga en el servidor.";
        }
    } catch (err) {
        msg.textContent = "Error al realizar la descarga.";
    }
}

function mostrarMensajeAmor() {
    const loveMsg = document.getElementById('loveMsg');
    loveMsg.textContent = "❤️ Te amo mi Alexa ❤️";
    loveMsg.classList.add('visible');

    const heartBtn = document.getElementById('heartBtn');
    heartBtn.style.transform = 'scale(1.4)';
    setTimeout(() => {
        heartBtn.style.transform = 'scale(1)';
    }, 200);
}
