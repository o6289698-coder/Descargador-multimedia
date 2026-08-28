# Descargador de Videos y Audio (YouTube / Facebook)

App en Flask + yt-dlp con interfaz en español (Tailwind CSS) para descargar
videos en MP4 o audio en MP3.

## 1. Subir a GitHub

```bash
cd descargador-app
git init
git add .
git commit -m "App lista para producción"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

## 2. Desplegar en Render

1. Entra a https://render.com y crea un **New Web Service**.
2. Conecta tu cuenta de GitHub y selecciona este repositorio.
3. Configura:
   - **Runtime**: Python 3
   - **Build Command**:
     ```
     apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt
     ```
     (ffmpeg es obligatorio: sin él, yt-dlp no puede convertir a MP3 ni unir
     video+audio en MP4)
   - **Start Command**:
     ```
     gunicorn main:app
     ```
   - Render asigna automáticamente la variable de entorno `PORT`; la app ya
     está configurada para escuchar en `0.0.0.0` y usar ese puerto (por
     defecto 8080 si no está definida).
4. Haz clic en **Create Web Service** y espera el despliegue.

## Sobre el bloqueo 403 de YouTube

YouTube bloquea con frecuencia las IPs de los servidores en la nube
(Render, Railway, Heroku, etc.). Esta versión de `main.py` mitiga eso:

- Usa el cliente de **Android** de YouTube como primera opción (en vez del
  cliente web), y si falla, reintenta con `web_creator`, `android` y `tv`.
- Si aun así ves errores 403, lo más probable es que Render haya cambiado de
  IP y esté temporalmente en una lista de bloqueo de YouTube. Mantener
  `yt-dlp` actualizado (`pip install -U yt-dlp`) es la solución más efectiva,
  ya que YouTube cambia sus protecciones seguido y el proyecto libera
  actualizaciones para evadirlas.

## Notas

- Los archivos descargados se guardan temporalmente en el servidor y se
  borran automáticamente después de enviarse al usuario.
- Respeta los términos de servicio y derechos de autor del contenido que
  descargues.
