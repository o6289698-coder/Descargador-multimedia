from __future__ import annotations

import atexit
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, Response, after_this_request, jsonify, request, send_file


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "fb.watch",
}
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
TEMP_DIRS: set[str] = set()


def cleanup_temp_dir(path: str) -> None:
    TEMP_DIRS.discard(path)
    shutil.rmtree(path, ignore_errors=True)


@atexit.register
def cleanup_on_exit() -> None:
    for path in list(TEMP_DIRS):
        cleanup_temp_dir(path)


def normalized_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".")


def validate_input(
    url: object, media_format: object, quality: object
) -> tuple[tuple[str, str, str] | None, str | None]:
    if not isinstance(url, str) or len(url) < 8 or len(url) > 2048:
        return None, "Pega un enlace válido."
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or normalized_host(url) not in ALLOWED_HOSTS:
        return None, "Solo se admiten enlaces públicos de YouTube o Facebook."
    if media_format not in {"video", "audio"}:
        return None, "Selecciona un formato válido."
    if quality not in {"low", "medium", "high"}:
        return None, "Selecciona una calidad de video válida."
    return (url, media_format, quality), None


def ydl_options(
    output_dir: str, media_format: str, quality: str, *, download: bool
) -> dict:
    options: dict = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 25,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 3,
        "file_access_retries": 3,
        "restrictfilenames": True,
        "outtmpl": str(Path(output_dir) / "%(title)s.%(ext)s"),
        "max_filesize": MAX_DOWNLOAD_BYTES,
        "overwrites": True,
        "skip_download": not download,
        "cachedir": False,
        "geo_bypass": True,
        "force_ipv4": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                "AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36"
            ),
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "ios", "web_safari"],
            }
        },
    }
    if media_format == "video":
        max_height = {"low": 480, "medium": 720, "high": 1080}[quality]
        if quality == "low":
            video_format = (
                f"worstvideo[height<={max_height}][ext=mp4]+"
                "worstaudio[ext=m4a]/"
                f"worst[height<={max_height}][ext=mp4]/worst"
            )
        else:
            video_format = (
                f"bestvideo[height<={max_height}][ext=mp4]+"
                "bestaudio[ext=m4a]/"
                f"best[height<={max_height}][ext=mp4]/"
                f"best[height<={max_height}]"
            )
        options.update(
            {
                "format": video_format,
                "merge_output_format": "mp4",
            }
        )
    else:
        options.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
    return options


def friendly_error(error: Exception) -> str:
    message = str(error).lower()
    if "private" in message or "login" in message or "sign in" in message:
        return "Este contenido es privado o requiere iniciar sesión."
    if "not available" in message or "unavailable" in message:
        return "El contenido no está disponible en este momento."
    if "max-filesize" in message or "filesize" in message:
        return "El archivo supera el límite de 512 MB."
    return "No pudimos procesar el enlace. Comprueba que sea público e inténtalo de nuevo."


def format_duration(value: object) -> int | None:
    if isinstance(value, (int, float)) and value >= 0:
        return round(value)
    return None


@app.get("/api/healthz")
def health() -> Response:
    return jsonify({"status": "ok"})


@app.get("/api/platforms")
def platforms() -> Response:
    return jsonify(
        [
            {"id": "youtube", "name": "YouTube", "color": "#ff0033"},
            {"id": "facebook", "name": "Facebook", "color": "#1877f2"},
        ]
    )


@app.post("/api/download/metadata")
def metadata() -> Response:
    payload = request.get_json(silent=True) or {}
    validated, error = validate_input(
        payload.get("url"), payload.get("format"), payload.get("quality")
    )
    if error:
        return jsonify({"error": error}), 400
    url, media_format, quality = validated

    try:
        with yt_dlp.YoutubeDL(
            ydl_options(tempfile.gettempdir(), media_format, quality, download=False)
        ) as ydl:
            info = ydl.extract_info(url, download=False)
        title = str(info.get("title") or "archivo multimedia")
        extension = "mp3" if media_format == "audio" else "mp4"
        filename = f"{re.sub(r'[^A-Za-z0-9À-ÿ _-]', '', title).strip()[:120] or 'archivo'}.{extension}"
        return jsonify(
            {
                "title": title,
                "duration": format_duration(info.get("duration")),
                "uploader": info.get("uploader") or info.get("channel"),
                "thumbnail": info.get("thumbnail"),
                "format": media_format,
                "filename": filename,
            }
        )
    except Exception as exc:
        return jsonify({"error": friendly_error(exc)}), 422


@app.get("/api/download")
def download() -> Response:
    validated, error = validate_input(
        request.args.get("url"),
        request.args.get("format"),
        request.args.get("quality"),
    )
    if error:
        return jsonify({"error": error}), 400
    url, media_format, quality = validated

    output_dir = tempfile.mkdtemp(prefix="media-download-")
    TEMP_DIRS.add(output_dir)
    try:
        with yt_dlp.YoutubeDL(
            ydl_options(output_dir, media_format, quality, download=True)
        ) as ydl:
            info = ydl.extract_info(url, download=True)
            requested_title = str(info.get("title") or "archivo multimedia")

        files = [path for path in Path(output_dir).iterdir() if path.is_file()]
        if not files:
            raise RuntimeError("download did not produce a file")
        downloaded = max(files, key=lambda path: path.stat().st_mtime)
        extension = "mp3" if media_format == "audio" else downloaded.suffix.lstrip(".") or "mp4"
        safe_title = re.sub(r"[^A-Za-z0-9À-ÿ _-]", "", requested_title).strip()[:120] or "archivo"
        filename = f"{safe_title}.{extension}"

        @after_this_request
        def remove_temp(response: Response) -> Response:
            response.call_on_close(lambda: cleanup_temp_dir(output_dir))
            return response

        return send_file(downloaded, as_attachment=True, download_name=filename, max_age=0)
    except Exception as exc:
        cleanup_temp_dir(output_dir)
        return jsonify({"error": friendly_error(exc)}), 422


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
    )
