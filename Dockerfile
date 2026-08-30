FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Forzamos la versión más reciente de yt-dlp en cada build, ya que YouTube
# y Facebook cambian sus protecciones seguido y las actualizaciones de
# yt-dlp son la defensa más importante contra bloqueos.
RUN pip install --no-cache-dir --upgrade yt-dlp

COPY . .

EXPOSE 8080

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--timeout", "120"]
