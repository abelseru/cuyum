from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from html import escape
import json
import mimetypes
import time
import traceback

from multicell_fusion import build_node_poll, build_multicell_state
from public_live import build_public_live
from public_api_v1 import build_public_v1, build_events_v1


HOST = "0.0.0.0"
PORT = 5050

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent if APP_DIR.name == "app" else APP_DIR
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

CACHE_SECONDS = 1.0
CACHE = {}


def cached(key, builder):
    now = time.time()
    item = CACHE.get(key)

    if item and now - item["time"] < CACHE_SECONDS:
        return item["data"]

    data = builder()
    CACHE[key] = {
        "time": now,
        "data": data,
    }
    return data



def build_public_events_payload():
    try:
        import event_journal

        for name in (
            "public_events_payload",
            "build_public_events_payload",
            "build_public_events",
            "public_events",
            "recent_public_events",
        ):
            fn = getattr(event_journal, name, None)
            if callable(fn):
                return fn()

    except Exception:
        traceback.print_exc()

    events_path = BASE_DIR / "runtime/events_recent.jsonl"
    events = []

    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue

    return {
        "system": "Cuyum",
        "mode": "plain_python_events_fallback",
        "count": len(events),
        "events": events[-100:],
    }

def json_bytes(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def file_bytes(path):
    return Path(path).read_bytes()



def read_compat_json(path, fallback):
    try:
        path = Path(path)
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def build_regional_preview_payload():
    summary = read_compat_json(
        BASE_DIR / "runtime/regional_auto_preview_summary.json",
        {},
    )
    alive_inventory = read_compat_json(
        BASE_DIR / "runtime/bootstrap_preview/candidate_inventory.alive.preview.json",
        {},
    )

    center = summary.get("center") or alive_inventory.get("center") or {}
    classification = summary.get("classification") or {}

    sensors = []
    for s in alive_inventory.get("sensores", []):
        sensors.append({
            "code": f"{s.get('red')}.{s.get('estacion')}.{s.get('canal')}",
            "network": s.get("red"),
            "station": s.get("estacion"),
            "channel": s.get("canal"),
            "name": s.get("nombre"),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "distance_km": s.get("distancia_km"),
            "role": s.get("rol"),
            "status": s.get("estado"),
            "packets": s.get("paquetes_ultima_revision"),
            "latency_seconds": s.get("latencia_aprox_seg"),
            "sampling_rate": s.get("frecuencia_hz"),
            "can_trigger": bool(s.get("puede_disparar")),
        })

    return {
        "system": "Cuyum",
        "mode": "regional_preview",
        "live_system_modified": False,
        "center": center,
        "capability": classification.get("capability"),
        "public_status": classification.get("public_status"),
        "local_trigger_allowed": bool(classification.get("local_trigger_allowed", False)),
        "local_alive_count": classification.get("local_alive_count", 0),
        "regional_alive_count": classification.get("regional_alive_count", len(sensors)),
        "fdsn_sensors_found": summary.get("fdsn_sensors_found"),
        "candidates_tested": summary.get("candidates_tested"),
        "alive_count": summary.get("alive_count", len(sensors)),
        "seedlink_server": summary.get("seedlink_server") or alive_inventory.get("seedlink_server"),
        "sensors": sensors,
        "source_files": {
            "summary": "runtime/regional_auto_preview_summary.json",
            "alive_inventory": "runtime/bootstrap_preview/candidate_inventory.alive.preview.json",
        },
    }


def regional_preview_html(data):
    center = data.get("center") or {}
    sensors = data.get("sensors") or []

    capability_labels = {
        "local_coverage_available": "Cobertura local experimental disponible",
        "minimal_local_observation": "Observación local mínima",
        "regional_observation_only": "Observación regional disponible",
        "minimal_regional_observation": "Observación regional mínima",
        "no_live_coverage": "Sin cobertura viva por SeedLink actual",
        None: "Sin datos de preview regional",
    }

    capability = data.get("capability")
    status_label = capability_labels.get(capability, str(capability or "Sin datos"))

    rows = []
    for s in sensors:
        rows.append(
            "<tr>"
            f"<td>{escape(str(s.get('code', '')))}</td>"
            f"<td>{escape(str(s.get('name', '')))}</td>"
            f"<td>{escape(str(s.get('distance_km', '')))}</td>"
            f"<td>{escape(str(s.get('packets', '')))}</td>"
            f"<td>{escape(str(s.get('latency_seconds', '')))}</td>"
            f"<td>{'No' if not s.get('can_trigger') else 'Sí'}</td>"
            "</tr>"
        )

    rows_html = "\n".join(rows) if rows else (
        "<tr><td colspan='6'>No hay sensores vivos en el preview regional.</td></tr>"
    )

    trigger_label = "deshabilitado" if not data.get("local_trigger_allowed") else "habilitado"

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Cuyum - Vista regional</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <style>
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      background: #111827;
      color: #e5e7eb;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin-bottom: 4px;
      font-size: 28px;
    }}
    .sub {{
      color: #9ca3af;
      margin-bottom: 22px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }}
    .card {{
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 14px;
      padding: 14px;
    }}
    .label {{
      color: #9ca3af;
      font-size: 13px;
    }}
    .value {{
      margin-top: 4px;
      font-size: 20px;
      font-weight: 700;
    }}
    .notice {{
      background: #172554;
      border: 1px solid #1d4ed8;
      border-radius: 14px;
      padding: 14px;
      margin: 18px 0;
      line-height: 1.45;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #1f2937;
      border-radius: 14px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid #374151;
      padding: 10px;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #111827;
      color: #cbd5e1;
    }}
    a {{
      color: #93c5fd;
    }}
  </style>
</head>
<body>
<main>
  <h1>Cuyum / Vista regional experimental</h1>
  <div class="sub">Pantalla separada del monitor vivo principal. No modifica Mendoza live.</div>

  <section class="cards">
    <div class="card">
      <div class="label">Centro evaluado</div>
      <div class="value">{escape(str(center.get('label', 'Sin centro')))}</div>
    </div>
    <div class="card">
      <div class="label">Estado</div>
      <div class="value">{escape(status_label)}</div>
    </div>
    <div class="card">
      <div class="label">Sensores vivos</div>
      <div class="value">{escape(str(data.get('alive_count', len(sensors))))}</div>
    </div>
    <div class="card">
      <div class="label">Disparo local</div>
      <div class="value">{escape(trigger_label)}</div>
    </div>
  </section>

  <section class="cards">
    <div class="card">
      <div class="label">Sensores locales vivos ≤ 200 km</div>
      <div class="value">{escape(str(data.get('local_alive_count', 0)))}</div>
    </div>
    <div class="card">
      <div class="label">Sensores regionales vivos</div>
      <div class="value">{escape(str(data.get('regional_alive_count', 0)))}</div>
    </div>
    <div class="card">
      <div class="label">Candidatos probados</div>
      <div class="value">{escape(str(data.get('candidates_tested', '')))}</div>
    </div>
    <div class="card">
      <div class="label">Servidor SeedLink</div>
      <div class="value" style="font-size:15px">{escape(str(data.get('seedlink_server', '')))}</div>
    </div>
  </section>

  <div class="notice">
    Esta vista muestra observación regional. No debe presentarse como cobertura local cuando no hay sensores vivos cercanos suficientes.
    Fuente JSON: <a href="/json/regional-preview">/json/regional-preview</a>
  </div>

  <h2>Sensores vivos del preview</h2>
  <table>
    <thead>
      <tr>
        <th>Sensor</th>
        <th>Nombre</th>
        <th>Km</th>
        <th>Paquetes</th>
        <th>Latencia s</th>
        <th>Dispara</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</main>
</body>
</html>"""


class CuyumHandler(BaseHTTPRequestHandler):
    server_version = "CuyumPlainPython/1.0"

    def log_message(self, fmt, *args):
        print(
            f"{self.address_string()} - {self.log_date_time_string()} - {fmt % args}",
            flush=True,
        )

    def send_bytes(self, body, status=200, content_type="application/octet-stream"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def send_json(self, data, status=200):
        self.send_bytes(
            json_bytes(data),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def send_text(self, text, status=200):
        self.send_bytes(
            text.encode("utf-8"),
            status=status,
            content_type="text/plain; charset=utf-8",
        )

    def not_found(self, path):
        self.send_json(
            {
                "error": "not_found",
                "path": path,
            },
            status=404,
        )

    def serve_static(self, path):
        relative = path.removeprefix("/static/")

        if ".." in relative or relative.startswith("/"):
            self.not_found(path)
            return

        file_path = STATIC_DIR / relative

        if not file_path.exists() or not file_path.is_file():
            self.not_found(path)
            return

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_bytes(file_bytes(file_path), content_type=content_type)

    def serve_live(self):
        candidates = [
            TEMPLATE_DIR / "live.html",
            TEMPLATE_DIR / "public_live.html",
            TEMPLATE_DIR / "index.html",
            TEMPLATE_DIR / "cuyum_live.html",
            TEMPLATE_DIR / "live_cuyum.html",
            STATIC_DIR / "live.html",
            STATIC_DIR / "index.html",
            BASE_DIR / "live.html",
            BASE_DIR / "index.html",
        ]

        for path in candidates:
            if path.exists():
                self.send_bytes(
                    file_bytes(path),
                    content_type="text/html; charset=utf-8",
                )
                return

        found = []
        for folder in (TEMPLATE_DIR, STATIC_DIR, BASE_DIR):
            if folder.exists():
                for item in folder.glob("*.html"):
                    found.append(str(item.relative_to(BASE_DIR)))

        self.send_json(
            {
                "error": "live_page_not_found",
                "checked": [str(p.relative_to(BASE_DIR)) for p in candidates],
                "html_files_found": found,
            },
            status=404,
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/":
                self.redirect("/app")
                return

            if path == "/health":
                self.send_json({
                    "system": "Cuyum",
                    "server": "plain_python",
                    "status": "ok",
                    "endpoints": [
                        "/app",
                        "/json",
                        "/regional-preview",
                        "/json/regional-preview",
                        "/reg",
                        "/api/node/poll?node_id=node_01",
                        "/api/esp32/poll?node_id=node_01",
                    ],
                })
                return

            if path in ("/app", "/app/"):
                self.serve_live()
                return

            if path.startswith("/static/"):
                self.serve_static(path)
                return

            if path == "/json":
                self.send_json(cached("public_live", build_public_live))
                return

            if path == "/json/regional-preview":
                self.send_json(cached("regional_preview", build_regional_preview_payload))
                return

            if path == "/regional-preview":
                html = regional_preview_html(
                    cached("regional_preview", build_regional_preview_payload)
                )
                self.send_bytes(
                    html.encode("utf-8"),
                    content_type="text/html; charset=utf-8",
                )
                return


            if path == "/reg":
                raw_events = cached("public_events", build_public_events_payload)
                self.send_json(build_events_v1(raw_events))
                return

            if path == "/api/node/poll" or path == "/api/esp32/poll":
                node_id = query.get("node_id", ["node_01"])[0]
                self.send_json(
                    cached(
                        f"node_poll:{node_id}",
                        lambda: build_node_poll(node_id),
                    )
                )
                return

            if path == "/api/network/state":
                self.send_json(cached("network_state", build_multicell_state))
                return

            if path.startswith("/api/cells/"):
                cell_id = path.split("/")[-1]
                state = cached("network_state", build_multicell_state)
                cell = state.get("cells", {}).get(cell_id)

                if cell is None:
                    self.send_json(
                        {
                            "error": "cell_not_found",
                            "cell_id": cell_id,
                        },
                        status=404,
                    )
                    return

                self.send_json(cell)
                return

            self.not_found(path)

        except Exception as exc:
            traceback.print_exc()
            self.send_json(
                {
                    "error": "server_error",
                    "message": str(exc),
                },
                status=500,
            )


def main():
    server = ThreadingHTTPServer((HOST, PORT), CuyumHandler)
    print(f"Cuyum plain Python server running on http://{HOST}:{PORT}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopped manually.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
