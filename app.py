import os
import tempfile
import random
from flask import Flask, request, jsonify, send_from_directory, send_file, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)

# Lista de User-Agents reales para rotación
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
]

def get_anti_bot_opts():
    """Genera opciones avanzadas para burlar la detección de bots."""
    return {
        'quiet': True,
        'no_warnings': True,
        'user_agent': random.choice(USER_AGENTS),
        'referer': 'https://www.google.com/',
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'no_color': True,
        # Configuración específica para evadir restricciones de YouTube
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'ios', 'web'],
                'skip': ['dash', 'hls']
            }
        },
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.json or {}
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Por favor ingresa un enlace válido'}), 400

    ydl_opts = get_anti_bot_opts()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [{
                'format_id': 'audio_mp3',
                'label': 'Audio MP3 (Mejor Calidad)',
                'ext': 'mp3',
                'type': 'audio'
            }]

            raw_formats = info.get('formats', [])
            seen_resolutions = set()

            for f in reversed(raw_formats):
                height = f.get('height')
                vcodec = f.get('vcodec')

                if height and vcodec != 'none':
                    res_label = f"{height}p"
                    if res_label not in seen_resolutions and height >= 144:
                        seen_resolutions.add(res_label)
                        formats.append({
                            'format_id': f.get('format_id'),
                            'label': f"Video MP4 ({res_label})",
                            'ext': 'mp4',
                            'type': 'video',
                            'height': height
                        })

            return jsonify({
                'title': info.get('title', 'Video sin título'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'formats': formats
            })
    except Exception as e:
        return jsonify({'error': f'Plataforma bloqueó la petición temporalmente. Reintenta en unos segundos.'}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json or {}
    url = data.get('url')
    format_id = data.get('format_id')
    format_type = data.get('type')

    if not url or not format_id:
        return jsonify({'error': 'Parámetros incompletos'}), 400

    temp_dir = tempfile.mkdtemp()
    ydl_opts = get_anti_bot_opts()

    if format_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': f'{format_id}+bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if format_type == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'

            @after_this_request
            def cleanup(response):
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                    os.rmdir(temp_dir)
                except Exception:
                    pass
                return response

            return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'No se pudo completar la descarga.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
