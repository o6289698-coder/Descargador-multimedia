import os
import shutil
import uuid
from flask import Flask, render_template_string, request, jsonify, send_file, after_this_request
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

        <div class="heart-section">
            <button type="button" class="heart-btn" id="heart-btn">❤️</button>
            <div id="love-message" class="love-message">Te amo Alexa</div>
        </div>
    </div>

    <script>
        document.getElementById('download-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = "Procesando descarga en el servidor... espera un momento.";
            
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
                        <a href="/download_file?file=${encodeURIComponent(data.file_id)}&name=${encodeURIComponent(data.title)}&ext=${format}" class="download-btn">Descargar ${format.toUpperCase()}</a>
                    `;
                } else {
                    resultDiv.innerHTML = `<p style="color: #ff5252;">Error: ${data.error}</p>`;
                }
            } catch (err) {
                resultDiv.innerHTML = `<p style="color: #ff5252;">Error de conexión con el servidor.</p>`;
            }
        });

        document.getElementById('heart-btn').addEventListener('click', () => {
            const msg = document.getElementById('love-message');
            msg.style.display = (msg.style.display === 'block') ? 'none' : 'block';
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

    file_id = str(uuid.uuid4())
    out_template = f'/tmp/{file_id}.%(ext)s'

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': out_template,
        'format': 'bestaudio/best' if formato == 'mp3' else 'best',
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'ios', 'mweb']
            }
        }
    }

    # Intentar usar cookies solo si existen y no están vacías
    secret_cookies = '/etc/secrets/cookies.txt'
    temp_cookies = '/tmp/cookies.txt'

    if os.path.exists(secret_cookies) and os.path.getsize(secret_cookies) > 0:
        shutil.copy(secret_cookies, temp_cookies)
        ydl_opts['cookiefile'] = temp_cookies

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'archivo')
            thumbnail = info.get('thumbnail', '')

            actual_filename = None
            for f in os.listdir('/tmp'):
                if f.startswith(file_id):
                    actual_filename = f
                    break

            if not actual_filename:
                return jsonify({'success': False, 'error': 'No se pudo generar el archivo.'})

            return jsonify({
                'success': True,
                'title': title,
                'thumbnail': thumbnail,
                'file_id': actual_filename
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download_file')
def download_file():
    file_id = request.args.get('file')
    name = request.args.get('name', 'video')
    ext = request.args.get('ext', 'mp4')
    
    file_path = os.path.join('/tmp', file_id)

    if not os.path.exists(file_path):
        return "El archivo ya no está disponible.", 404

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        return response

    return send_file(file_path, as_attachment=True, download_name=f"{name}.{ext}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
