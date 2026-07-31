from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json
import mimetypes
import time
import traceback
from collections import deque
from threading import Lock

from multicell_fusion import build_node_poll, build_multicell_state
from public_live import build_public_live
from public_api_v1 import build_events_v1


HOST = "0.0.0.0"
PORT = 5050

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent if APP_DIR.name == "app" else APP_DIR
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

CACHE_SECONDS = 1.0
CACHE = {}

STATUS_REQUEST_TIMES = deque()
STATUS_REQUEST_LOCK = Lock()


def record_status_request():
    now = time.monotonic()

    with STATUS_REQUEST_LOCK:
        STATUS_REQUEST_TIMES.append(now)

        while STATUS_REQUEST_TIMES and now - STATUS_REQUEST_TIMES[0] > 60.0:
            STATUS_REQUEST_TIMES.popleft()


def status_activity_snapshot():
    now = time.monotonic()

    with STATUS_REQUEST_LOCK:
        while STATUS_REQUEST_TIMES and now - STATUS_REQUEST_TIMES[0] > 60.0:
            STATUS_REQUEST_TIMES.popleft()

        last_second = sum(
            1
            for timestamp in STATUS_REQUEST_TIMES
            if now - timestamp <= 1.0
        )

        last_5_seconds = sum(
            1
            for timestamp in STATUS_REQUEST_TIMES
            if now - timestamp <= 5.0
        )

        last_minute = len(STATUS_REQUEST_TIMES)

    return {
        "status_requests_last_second": last_second,
        "status_requests_last_5_seconds": last_5_seconds,
        "status_requests_last_minute": last_minute,
        "equivalent_active_clients": last_5_seconds,
    }


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

    def serve_web(self):
        path = TEMPLATE_DIR / "web.html"

        if path.exists():
            self.send_bytes(
                file_bytes(path),
                content_type="text/html; charset=utf-8",
            )
            return

        self.send_json(
            {
                "error": "web_page_not_found",
                "checked": str(path.relative_to(BASE_DIR)),
            },
            status=404,
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/":
                self.redirect("/web")
                return

            if path == "/health":
                self.send_json({
                    "system": "Cuyum",
                    "server": "plain_python",
                    "status": "ok",
                    "endpoints": [
                        "/app",
                        "/json",
                        "/reg",
                        "/lite",
                    ],
                })
                return

            if path in ("/app", "/app/"):
                self.serve_live()
                return


            if path in ("/web", "/web/"):
                self.serve_web()
                return



            if path.startswith("/static/"):
                self.serve_static(path)
                return

            if path == "/json":
                record_status_request()

                payload = dict(
                    cached("public_live", build_public_live)
                )

                existing_statistics = payload.get("statistics", {})

                if not isinstance(existing_statistics, dict):
                    existing_statistics = {}

                payload["statistics"] = {
                    **existing_statistics,
                    **status_activity_snapshot(),
                }

                self.send_json(payload)
                return


            if path == "/reg":
                raw_events = cached("public_events", build_public_events_payload)
                self.send_json(build_events_v1(raw_events))
                return

            if path == "/lite":
                record_status_request()

                payload = dict(
                    cached(
                        "lite_status",
                        lambda: build_node_poll("node_01"),
                    )
                )

                existing_statistics = payload.get(
                    "statistics",
                    {},
                )

                if not isinstance(existing_statistics, dict):
                    existing_statistics = {}

                payload["statistics"] = {
                    **existing_statistics,
                    **status_activity_snapshot(),
                }

                self.send_json(payload)
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
