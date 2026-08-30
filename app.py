import os
import tempfile
from flask import Flask, request, jsonify, send_from_directory, send_file, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Por favor ingresa un enlace válido'}), 400

    ydl_opts = {'quiet': True, 'no_warnings': True}

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
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats
            })
    except Exception as e:
        return jsonify({'error': 'No se pudo procesar el video. Verifica la URL.'}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    format_type = data.get('type')

    if not url or not format_id:
        return jsonify({'error': 'Parámetros incompletos'}), 400

    temp_dir = tempfile.mkdtemp()

    if format_type == 'audio':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
    else:
        ydl_opts = {
            'format': f'{format_id}+bestaudio/bestvideo+bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'quiet': True,
        }

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
        return jsonify({'error': 'Error al procesar la descarga.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
