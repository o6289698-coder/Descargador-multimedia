import os
import glob
import shutil
import uuid
import tempfile
import threading
import time

from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "descargas_app")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Carpeta donde subimos, como "Secret Files" en Render, uno o varios
# archivos de cookies: cookies_1.txt, cookies_2.txt, etc. Esa carpeta es
# de SOLO LECTURA en Render, y yt-dlp necesita poder escribir en el
# archivo de cookies que usa (actualiza tokens al usarlo), así que
# copiamos cada archivo a una carpeta temporal escribible antes de
# pasárselo a yt-dlp.
COOKIES_DIR_ORIGEN = os.environ.get("COOKIES_DIR", "/etc/secrets")
COOKIES_DIR_ESCRIBIBLE = os.path.join(tempfile.gettempdir(), "cookies_writable")
os.makedirs(COOKIES_DIR_ESCRIBIBLE, exist_ok=True)


def obtener_archivos_cookies():
    """
    Copia cada cookies*.txt de la carpeta de solo lectura a una carpeta
    escribible (si no se copio ya) y devuelve las rutas escribibles.
    """
    patrones = sorted(glob.glob(os.path.join(COOKIES_DIR_ORIGEN, "cookies*.txt")))
    rutas_escribibles = []
    for origen in patrones:
        nombre = os.path.basename(origen)
        destino = os.path.join(COOKIES_DIR_ESCRIBIBLE, nombre)
        try:
            if not os.path.exists(destino) or os.path.getmtime(origen) > os.path.getmtime(destino):
                shutil.copyfile(origen, destino)
            rutas_escribibles.append(destino)
        except OSError:
            continue
    return rutas_escribibles


def limpiar_archivos_viejos(carpeta, minutos=30):
    ahora = time.time()
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        try:
            if os.path.isfile(ruta) and ahora - os.path.getmtime(ruta) > minutos * 60:
                os.remove(ruta)
        except OSError:
            pass


ESTRATEGIAS_YOUTUBE = [
    ["android", "ios"],
    ["ios", "android", "web"],
    ["web_creator", "android", "tv"],
    ["tv_embedded", "web"],
]

USER_AGENT_ANDROID = (
    "com.google.android.youtube/19.09.37 (Linux; U; Android 14) gzip"
)


def opciones_base(player_clients=None, archivo_cookies=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "http_headers": {"User-Agent": USER_AGENT_ANDROID},
    }
    if player_clients:
        opts["extractor_args"] = {"youtube": {"player_client": player_clients}}
    if archivo_cookies:
        opts["cookiefile"] = archivo_cookies
    return opts


def extraer_info_con_reintentos(url, opts_extra=None):
    """
    Prueba, en orden, cada combinacion de (archivo de cookies x estrategia
    de cliente) hasta que una funcione. Si no hay archivos de cookies
    configurados, simplemente prueba las estrategias sin cookies.
    """
    es_youtube = "youtube.com" in url or "youtu.be" in url
    estrategias_cliente = ESTRATEGIAS_YOUTUBE if es_youtube else [None]

    archivos_cookies = obtener_archivos_cookies()
    opciones_cookies = [None] + archivos_cookies

    ultimo_error = None
    for cookies in opciones_cookies:
        for clientes in estrategias_cliente:
            opts = opciones_base(clientes, cookies)
            if opts_extra:
                opts.update(opts_extra)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=opts.get("_download", False))
            except Exception as e:
                ultimo_error = e
                continue
    raise ultimo_error


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"error": "Por favor pega un enlace valido."}), 400

    try:
        resultado = extraer_info_con_reintentos(url, opts_extra={"_download": False})
    except Exception as e:
        return jsonify({
            "error": (
                "No se pudo obtener informacion del video. El enlace puede "
                "ser invalido, privado, o la plataforma esta bloqueando "
                f"temporalmente la solicitud. Detalle: {e}"
            )
        }), 500

    calidades_video = []
    vistos = set()
    for f in resultado.get("formats", []):
        altura = f.get("height")
        ext = f.get("ext")
        if altura and ext == "mp4" and altura not in vistos:
            vistos.add(altura)
            calidades_video.append(altura)
    calidades_video.sort(reverse=True)

    return jsonify({
        "titulo": resultado.get("title", "Video"),
        "miniatura": resultado.get("thumbnail"),
        "duracion": resultado.get("duration"),
        "canal": resultado.get("uploader") or resultado.get("channel"),
        "calidades_video": calidades_video if calidades_video else [1080, 720, 480, 360],
    })@app.route("/api/descargar", methods=["POST"])
def descargar():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    formato = data.get("formato", "mp4")
    calidad = data.get("calidad")

    if not url:
        return jsonify({"error": "Por favor pega un enlace valido."}), 400
    if formato not in ("mp4", "mp3"):
        return jsonify({"error": "Formato no valido."}), 400

    threading.Thread(target=limpiar_archivos_viejos, args=(DOWNLOAD_DIR,)).start()

    id_unico = str(uuid.uuid4())
    plantilla_salida = os.path.join(DOWNLOAD_DIR, f"{id_unico}.%(ext)s")

    opts_extra = {"outtmpl": plantilla_salida, "_download": True}

    if formato == "mp3":
        calidad_audio = calidad or "192"
        opts_extra.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(calidad_audio),
            }],
        })
    else:
        if calidad:
            formato_str = (
                f"bestvideo[height<={calidad}][ext=mp4]+bestaudio[ext=m4a]"
                f"/best[height<={calidad}][ext=mp4]/best[height<={calidad}]"
            )
        else:
            formato_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        opts_extra.update({
            "format": formato_str,
            "merge_output_format": "mp4",
        })

    try:
        resultado = extraer_info_con_reintentos(url, opts_extra=opts_extra)
        titulo = resultado.get("title", "descarga")
    except Exception as e:
        return jsonify({
            "error": (
                "No se pudo descargar el video. Puede que el enlace sea "
                "privado, no exista, o la plataforma este bloqueando la "
                f"solicitud temporalmente. Detalle: {e}"
            )
        }), 500

    extension = "mp3" if formato == "mp3" else "mp4"
    ruta_archivo = os.path.join(DOWNLOAD_DIR, f"{id_unico}.{extension}")

    if not os.path.exists(ruta_archivo):
        candidatos = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(id_unico)]
        if candidatos:
            ruta_archivo = os.path.join(DOWNLOAD_DIR, candidatos[0])
        else:
            return jsonify({"error": "No se encontro el archivo generado."}), 500

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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
