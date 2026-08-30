import os
import requests
from flask import Flask, render_template_string, request, jsonify

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
            resultDiv.innerHTML = "Obteniendo enlace de descarga...";
            
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
                        <a href="${data.download_url}" target="_blank" class="download-btn">Descargar ${format.toUpperCase()}</a>
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

    # Configuración de la petición a la API pública de Cobalt
    payload = {
        "url": url,
        "downloadMode": "audio" if formato == "mp3" else "auto"
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.cobalt.tools/", json=payload, headers=headers)
        res_data = response.json()

        if response.status_code == 200 and "url" in res_data:
            return jsonify({
                'success': True,
                'download_url': res_data['url']
            })
        else:
            error_msg = res_data.get('text', 'No se pudo obtener el enlace.')
            return jsonify({'success': False, 'error': error_msg})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
