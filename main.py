from __future__ import annotations

import importlib.util
from pathlib import Path


SERVER_PATH = Path(__file__).parent / "server.py"
spec = importlib.util.spec_from_file_location("descargador_api", SERVER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"No se pudo cargar el servidor Flask desde {SERVER_PATH}")

server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)
app = server_module.app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
