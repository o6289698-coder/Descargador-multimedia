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

    # Estrategia de múltiples clientes (Fallback en cadena)
    # Si YouTube bloquea la petición de Android, yt-dlp intenta automáticamente con iOS, Web Móvil o TV
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb', 'tv_embedded']
            }
        }
    }

    # Selección de formato compatible para entrega directa
    if formato == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'best[vcodec!=none][acodec!=none]/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url')
            
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
    
