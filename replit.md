# Descargador multimedia

Aplicación web en español para convertir enlaces públicos de YouTube y Facebook en archivos MP4 o MP3 mediante Flask, yt-dlp y una interfaz React.

## Run & Operate

- `python main.py` — run the Flask API server for publication on `0.0.0.0:8080`
- `python artifacts/api-server/server.py` — run the Flask API server locally (port 8080)
- `pnpm --filter @workspace/descargador-multimedia run dev` — run the React frontend
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- The API uses the workspace's Python environment with `flask`, `yt-dlp`, and the system `ffmpeg` binary.

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/descargador-multimedia/src/` — Spanish user interface and interaction states.
- `main.py` — publication entrypoint that loads the Flask app and binds exactly to `0.0.0.0:8080`.
- `artifacts/api-server/server.py` — Flask routes, URL validation, yt-dlp options, and streamed file responses.
- `lib/api-spec/openapi.yaml` — shared metadata/platform API contract and generated client source.

## Architecture decisions

- The frontend is a Vite/React artifact, while the download API runs as the existing `/api` service using Flask to honor the requested Python stack.
- Metadata is inspected before a download so the UI can confirm the detected title and format.
- Video quality is mapped to yt-dlp format selectors: low up to 480p, medium up to 720p, and high up to 1080p.
- YouTube extraction uses current mobile/browser player clients with IPv4 and browser headers to reduce common automated-request failures.
- Downloaded bytes are written to a temporary directory and removed after the response closes; media is not persisted in the app.
- Only public YouTube and Facebook hostnames are accepted, playlists are disabled, and individual downloads are capped at 512 MB.

## Product

Users paste a public video link, choose video MP4 or audio MP3, preview the detected media, and download the converted file directly to their device. The interface exposes supported platforms and friendly errors for unavailable or restricted content.

## User preferences

The interface should remain in Spanish and feel modern, clear, and friendly.

## Gotchas

- MP3 conversion and MP4 merging require `ffmpeg`.
- The API route must preserve the `/api` prefix because the shared proxy routes the Flask service by path.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
