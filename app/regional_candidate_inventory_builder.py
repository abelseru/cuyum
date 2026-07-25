import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(".")
CATALOG_FILE = BASE / "config/seedlink_station_catalog.preview.json"
OUT_PREVIEW = BASE / "runtime/bootstrap_preview/candidate_inventory.preview.json"
REPORT_FILE = BASE / "runtime/regional_candidate_inventory_report.txt"

CHANNEL_PRIORITY = {
    "BHZ": 0,
    "HHZ": 1,
    "EHZ": 2,
    "SHZ": 3,
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def station_key(sensor):
    return f"{sensor.get('network')}.{sensor.get('station')}"


def channel_rank(channel):
    return CHANNEL_PRIORITY.get(str(channel or "").upper(), 99)


def role_for_distance(distance_km, index):
    if index <= 4:
        return "early_warning"
    return "regional_observer"


def build_candidate_inventory(catalog, max_sensors):
    center = catalog.get("center", {})
    sensors_raw = list((catalog.get("sensors") or {}).values())

    # Deduplicate by network.station, preferring channel priority and then nearest distance.
    by_station = {}
    for s in sensors_raw:
        key = station_key(s)
        if key in ["None.None", "."]:
            continue

        old = by_station.get(key)
        if old is None:
            by_station[key] = s
            continue

        old_rank = channel_rank(old.get("channel"))
        new_rank = channel_rank(s.get("channel"))

        if new_rank < old_rank:
            by_station[key] = s
        elif new_rank == old_rank and float(s.get("distance_km", 999999)) < float(old.get("distance_km", 999999)):
            by_station[key] = s

    ordered = sorted(
        by_station.values(),
        key=lambda s: (
            float(s.get("distance_km", 999999)),
            channel_rank(s.get("channel")),
            s.get("network", ""),
            s.get("station", ""),
        )
    )

    selected = ordered[:max_sensors]

    sensors = []
    for i, s in enumerate(selected, 1):
        distance = float(s.get("distance_km", 0))
        role = role_for_distance(distance, i)

        sensors.append({
            "network": s.get("network"),
            "station": s.get("station"),
            "channel": s.get("channel"),
            "name": s.get("name") or s.get("station"),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "role": role,
            "can_confirm": bool(s.get("can_confirm", True)),
            "can_trigger": bool(s.get("can_trigger", True)) and role == "early_warning",
            "distance_km": round(distance, 1),
            "state": "pending_review",
            "review_note": "pending SeedLink liveness test",
            "source": "regional_station_catalog_builder",
            "source_provider": s.get("source_provider"),
        })

    return {
        "generated_by": "regional_candidate_inventory_builder",
        "generated_at": now_iso(),
        "mode": "preview",
        "center": {
            "label": center.get("label", "System center"),
            "lat": center.get("lat"),
            "lon": center.get("lon"),
        },
        "seedlink_server": "rtserve.earthscope.org:18000",
        "selection_policy": {
            "max_sensors": max_sensors,
            "dedupe": "one channel per network.station",
            "channel_priority": ["BHZ", "HHZ", "EHZ", "SHZ"],
            "note": "This preview is not applied to the live system until SeedLink liveness is tested."
        },
        "sensors": sensors,
    }


def write_report(inv):
    lines = []
    center = inv.get("center", {})
    lines.append("CUYUM regional candidate inventory preview")
    lines.append("=" * 60)
    lines.append(f"Generated: {inv.get('generated_at')}")
    lines.append(f"Center: {center.get('label')} lat={center.get('lat')} lon={center.get('lon')}")
    lines.append(f"SeedLink server: {inv.get('seedlink_server')}")
    lines.append(f"Sensors selected: {len(inv.get('sensors', []))}")
    lines.append("")
    for i, s in enumerate(inv.get("sensors", []), 1):
        lines.append(
            f"{i:02d}. {s.get('network')}.{s.get('station')}.{s.get('channel'):<4} "
            f"{s.get('name',''):<36} "
            f"{s.get('distance_km'):>7} km "
            f"role={s.get('role')} "
            f"trigger={s.get('can_trigger')}"
        )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build candidate inventory preview from regional station catalog preview.")
    parser.add_argument("--max-sensors", type=int, default=6)
    parser.add_argument("--apply", action="store_true", help="Apply preview to config/candidate_inventory.json")
    args = parser.parse_args()

    if not CATALOG_FILE.exists():
        raise SystemExit("ERROR: missing config/seedlink_station_catalog.preview.json. Run regional_station_catalog_builder.py first.")

    catalog = load_json(CATALOG_FILE)
    inv = build_candidate_inventory(catalog, args.max_sensors)

    save_json(OUT_PREVIEW, inv)
    write_report(inv)

    print(f"Written: {OUT_PREVIEW}")
    print(f"Written: {REPORT_FILE}")
    print(f"Sensors selected: {len(inv.get('sensors', []))}")

    if args.apply:
        target = BASE / "config/candidate_inventory.json"
        backup = BASE / f"config/candidate_inventory.json.backup_before_regional_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if target.exists():
            backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Backup: {backup}")
        save_json(target, inv)
        print(f"Applied: {target}")


if __name__ == "__main__":
    main()
