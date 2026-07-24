import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(".")
SUMMARY_JSON = BASE / "runtime/regional_auto_preview_summary.json"
SUMMARY_TXT = BASE / "runtime/regional_auto_preview_summary.txt"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run(cmd):
    print("")
    print(">>>", " ".join(cmd))
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        raise SystemExit(f"ERROR running: {' '.join(cmd)}")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def classify(center, alive):
    local = []
    regional = []

    for s in alive:
        d = float(s.get("distancia_km", 999999))
        if d <= 200:
            local.append(s)
        else:
            regional.append(s)

    if len(local) >= 3:
        capability = "local_coverage_available"
        public_status = "Local coverage available"
        local_trigger_allowed = True
    elif len(local) >= 1:
        capability = "minimal_local_observation"
        public_status = "Minimal local observation only"
        local_trigger_allowed = False
    elif len(regional) >= 3:
        capability = "regional_observation_only"
        public_status = "Regional observation available; local coverage insufficient"
        local_trigger_allowed = False
    elif len(regional) >= 1:
        capability = "minimal_regional_observation"
        public_status = "Minimal regional observation only"
        local_trigger_allowed = False
    else:
        capability = "no_live_coverage"
        public_status = "No live coverage found through current SeedLink server"
        local_trigger_allowed = False

    return {
        "capability": capability,
        "public_status": public_status,
        "local_alive_count": len(local),
        "regional_alive_count": len(regional),
        "local_trigger_allowed": local_trigger_allowed,
    }


def write_summary(summary):
    lines = []
    center = summary["center"]

    lines.append("CUYUM regional auto preview")
    lines.append("=" * 60)
    lines.append(f"Generated: {summary['generated_at']}")
    lines.append(f"Center: {center.get('label')} lat={center.get('lat')} lon={center.get('lon')}")
    lines.append(f"Max distance: {summary['max_km']} km")
    lines.append(f"FDSN provider: {summary['provider']}")
    lines.append(f"SeedLink server: {summary['seedlink_server']}")
    lines.append("")
    lines.append(f"FDSN stations found: {summary['fdsn_sensors_found']}")
    lines.append(f"Candidates tested: {summary['candidates_tested']}")
    lines.append(f"Alive sensors: {summary['alive_count']}")
    lines.append(f"Local alive sensors <= 200 km: {summary['classification']['local_alive_count']}")
    lines.append(f"Regional alive sensors > 200 km: {summary['classification']['regional_alive_count']}")
    lines.append("")
    lines.append(f"Capability: {summary['classification']['capability']}")
    lines.append(f"Public status: {summary['classification']['public_status']}")
    lines.append(f"Local trigger allowed: {summary['classification']['local_trigger_allowed']}")
    lines.append("")
    lines.append("Alive sensors:")
    for s in summary["alive_sensors"]:
        lines.append(
            f"- {s.get('code')} | {s.get('nombre')} | "
            f"{s.get('distancia_km')} km | packets={s.get('packets')} | "
            f"latency={s.get('latency_seconds')} | trigger=False"
        )

    SUMMARY_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run full Cuyum regional discovery preview workflow.")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--max-km", type=float, default=800)
    parser.add_argument("--max-sensors", type=int, default=120)
    parser.add_argument("--duration", type=int, default=180)
    parser.add_argument("--provider", default="IRIS")
    args = parser.parse_args()

    py = "./venv/bin/python"

    run([
        py, "app/regional_station_catalog_builder.py",
        "--lat", str(args.lat),
        "--lon", str(args.lon),
        "--label", args.label,
        "--max-km", str(args.max_km),
        "--provider", args.provider,
    ])

    run([
        py, "app/regional_candidate_inventory_builder.py",
        "--max-sensors", str(args.max_sensors),
    ])

    run([
        py, "app/seedlink_preview_liveness_test.py",
        "--duration", str(args.duration),
    ])

    catalog = load_json("config/seedlink_station_catalog.preview.json")
    liveness = load_json("runtime/seedlink_preview_liveness_result.json")

    alive = [s for s in liveness.get("sensors", []) if s.get("status") == "alive"]
    alive.sort(key=lambda s: float(s.get("distancia_km", 999999)))

    classification = classify(catalog.get("center", {}), alive)

    summary = {
        "generated_at": now_iso(),
        "center": catalog.get("center", {}),
        "max_km": args.max_km,
        "provider": args.provider,
        "seedlink_server": liveness.get("server"),
        "fdsn_sensors_found": len(catalog.get("sensors", {})),
        "candidates_tested": liveness.get("total_count"),
        "alive_count": len(alive),
        "classification": classification,
        "alive_sensors": alive,
        "files": {
            "station_catalog_preview": "config/seedlink_station_catalog.preview.json",
            "candidate_inventory_preview": "runtime/bootstrap_preview/candidate_inventory.preview.json",
            "liveness_result": "runtime/seedlink_preview_liveness_result.json",
            "summary_json": str(SUMMARY_JSON),
            "summary_txt": str(SUMMARY_TXT),
        },
    }

    save_json(SUMMARY_JSON, summary)
    write_summary(summary)

    print("")
    print("Written:", SUMMARY_JSON)
    print("Written:", SUMMARY_TXT)
    print("")
    print(SUMMARY_TXT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
