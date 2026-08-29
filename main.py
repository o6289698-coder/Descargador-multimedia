import os
import uuid
import tempfile
import threading
import time

from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# Carpeta temporal donde se guardan las descargas antes de enviarlas al usuario
DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "descargas_app")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def limpiar_archivos_viejos(carpeta, minutos=30):
    """Borra archivos con más de X minutos para no llenar el disco del servidor."""
    ahora = time.time()
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        try:
            if os.path.isfile(ruta) and ahora - os.path.getmtime(ruta) > minutos * 60:
                os.remove(ruta)
        except OSError:
            pass


def opciones_base():
    """
    Opciones comunes de yt-dlp. Para YouTube, forzamos clientes de
    Android/iOS (en vez del cliente web), que suelen evitar el bloqueo
    403 Forbidden que YouTube aplica a las IPs de muchos servidores en
    la nube (Render, Railway, etc.).
    """
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "com.google.android.youtube/19.09.37 "
                "(Linux; U; Android 14) gzip"
            )
        },
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/descargar", methods=["POST"])
def descargar():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    formato = data.get("formato", "mp4")

    if not url:
        return jsonify({"error": "Por favor pega un enlace válido."}), 400

    if formato not in ("mp4", "mp3"):
        return jsonify({"error": "Formato no válido."}), 400

    threading.Thread(target=limpiar_archivos_viejos, args=(DOWNLOAD_DIR,)).start()

    id_unico = str(uuid.uuid4())
    plantilla_salida = os.path.join(DOWNLOAD_DIR, f"{id_unico}.%(ext)s")

    ydl_opts = opciones_base()
    ydl_opts["outtmpl"] = plantilla_salida

    if formato == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
        })

    def intentar_descarga(opciones):
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get("title", "descarga")

    try:
        titulo = intentar_descarga(ydl_opts)
    except Exception:
        # Reintento con clientes alternativos por si el primer intento
        # fue bloqueado (403) o cambió algo en YouTube
        try:
            ydl_opts_alt = dict(ydl_opts)
            ydl_opts_alt["extractor_args"] = {
                "youtube": {"player_client": ["web_creator", "android", "tv"]}
            }
            titulo = intentar_descarga(ydl_opts_alt)
        except Exception as segundo_error:
            return jsonify({
                "error": (
                    "No se pudo descargar el video. Puede que el enlace sea "
                    "privado, no exista, o la plataforma esté bloqueando la "
                    f"solicitud temporalmente. Detalle: {segundo_error}"
                )
            }), 500

    extension = "mp3" if formato == "mp3" else "mp4"
    ruta_archivo = os.path.join(DOWNLOAD_DIR, f"{id_unico}.{extension}")

    if not os.path.exists(ruta_archivo):
        candidatos = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(id_unico)]
        if candidatos:
            ruta_archivo = os.path.join(DOWNLOAD_DIR, candidatos[0])
        else:
            return jsonify({"error": "No se encontró el archivo generado."}), 500

    nombre_descarga = f"{titulo}.{extension}".replace("/", "-")

    @after_this_request
    def eliminar_despues(response):
        def borrar():
            time.sleep(5)
            try:
                os.remove(ruta_archivo)
            except OSError:
                pass
        threading.Thread(target=borrar).start()
        return response

    return send_file(ruta_archivo, as_attachment=True, download_name=nombre_descarga)


if __name__ == "__main__":
    # Render (y muchos PaaS) esperan que la app escuche en 0.0.0.0
    # y usan la variable de entorno PORT; por defecto usamos 8080.
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
