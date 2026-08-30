import os
import shutil
from flask import Flask, render_template_string, request, jsonify
import yt_dlp

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Descargador Multimedia</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #fff; text-align: center; padding: 20px; }
        .container { max-width: 500px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 10px; }
        input[type="text"] { width: 90%; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #333; background: #2a2a2a; color: #fff; }
        select, button { padding: 10px 15px; border-radius: 5px; border: none; font-weight: bold; cursor: pointer; }
        button { background-color: #ff0055; color: white; }
        .result { margin-top: 20px; word-break: break-all; }
        .download-btn { display: inline-block; padding: 12px 24px; background: #00e676; color: #000; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 15px; }
        
        /* Estilos del corazón y mensaje */
        .heart-section { margin-top: 30px; }
        .heart-btn { background: none; border: none; font-size: 2rem; cursor: pointer; color: #ff1744; outline: none; transition: transform 0.2s; }
        .heart-btn:hover { transform: scale(1.2); }
        .love-message { color: #00e676; font-weight: bold; font-size: 1.2rem; margin-top: 10px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Descargador de Video y Audio</h2>
        <form id="download-form">
            <input type="text" id="url" placeholder="Pega el enlace de YouTube aquí..." required><br>
            <select id="format">
                <option value="mp4">Video MP4</option>
                <option value="mp3">Audio MP3</option>
            </select>
            <button type="submit">Procesar</button>
        </form>
        <div id="result" class="result"></div>

        <!-- Corazón inferior -->
        <div class="heart-section">
            <button type="button" class="heart-btn" id="heart-btn">❤️</button>
            <div id="love-message" class="love-message">Te amo Alexa</div>
        </div>
    </div>

    <script>
        document.getElementById('download-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = "Procesando enlace...";
            
            const url = document.getElementById('url').value;
            const format = document.getElementById('format').value;

            try {
                const response = await fetch('/procesar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, format })
                });

                const data = await response.json();
                if (data.success) {
                    resultDiv.innerHTML = `
                        <h3>${data.title}</h3>
                        <img src="${data.thumbnail}" width="100%" style="border-radius: 8px;"><br>
                        <a href="${data.download_url}" target="_blank" download="${data.title}.${format}" class="download-btn">Descargar ${format.toUpperCase()}</a>
                    `;
                } else {
                    resultDiv.innerHTML = `<p style="color: #ff5252;">Error: ${data.error}</p>`;
                }
            } catch (err) {
                resultDiv.innerHTML = `<p style="color: #ff5252;">Error de conexión con el servidor.</p>`;
            }
        });

        // Interacción del corazón
        document.getElementById('heart-btn').addEventListener('click', () => {
            const msg = document.getElementById('love-message');
            if (msg.style.display === 'block') {
                msg.style.display = 'none';
            } else {
                msg.style.display = 'block';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/procesar', methods=['POST'])
def procesar():
    data = request.get_json()
    url = data.get('url')
    formato = data.get('format', 'mp4')

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb']
            }
        }
    }

    # Copia cookies a /tmp para evitar problemas de lectura/escritura en Render
    secret_cookies = '/etc/secrets/cookies.txt'
    temp_cookies = '/tmp/cookies.txt'

    if os.path.exists(secret_cookies):
        shutil.copy(secret_cookies, temp_cookies)
        ydl_opts['cookiefile'] = temp_cookies
    elif os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            download_url = None
            formats = info.get('formats', [])
            
            if formato == 'mp3':
                # Busca el mejor formato solo audio
                for f in reversed(formats):
                    if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url'):
                        download_url = f.get('url')
                        break
            else:
                # Busca el mejor formato combinado (video + audio)
                for f in reversed(formats):
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url'):
                        download_url = f.get('url')
                        break

            # Si no encuentra uno combinado, toma la URL principal de extracción
            if not download_url:
                download_url = info.get('url')

            if not download_url and formats:
                download_url = formats[-1].get('url')

            return jsonify({
                'success': True,
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'download_url': download_url
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
