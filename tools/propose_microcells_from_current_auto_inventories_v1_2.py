#!/usr/bin/env python3
from pathlib import Path
import json
import math

INPUTS = [
    "config/auto_cell_01_inventory.json",
    "config/auto_cell_02_inventory.json",
]

OUTPUT_JSON = Path("audits/proposed_microcells_from_current_auto_inventories_v1_2.json")
OUTPUT_TXT = Path("audits/proposed_microcells_from_current_auto_inventories_v1_2.txt")

CLUSTER_RADIUS_KM = 70
MIN_CELL_DISTANCE_KM = 120
SENSORS_PER_CELL = 3
MIN_SENSORS_PER_CELL = 2

HOME = {
    "label": "Mendoza ciudad",
    "lat": -32.8895,
    "lon": -68.8458,
}

def km(a, b):
    R = 6371
    lat1, lon1 = math.radians(float(a["lat"])), math.radians(float(a["lon"]))
    lat2, lon2 = math.radians(float(b["lat"])), math.radians(float(b["lon"]))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def bearing_deg(a, b):
    lat1 = math.radians(float(a["lat"]))
    lat2 = math.radians(float(b["lat"]))
    dlon = math.radians(float(b["lon"]) - float(a["lon"]))
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def direction_label(b):
    labels = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return labels[int((b + 22.5) // 45) % 8]

def load_sensors():
    by_key = {}

    for filename in INPUTS:
        path = Path(filename)
        if not path.exists():
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        sensors = data.get("sensors") or data.get("sensores") or []
        if isinstance(sensors, dict):
            sensors = list(sensors.values())

        for s in sensors:
            lat = s.get("lat")
            lon = s.get("lon")
            if lat is None or lon is None:
                continue

            code = (
                s.get("sensor_id")
                or s.get("code")
                or s.get("trace_id")
                or s.get("clave")
                or f"{s.get('network', '')}.{s.get('station', '')}.{s.get('channel', '')}"
            )

            name = s.get("name") or s.get("nombre") or s.get("site") or s.get("locality") or code
            station = s.get("station") or s.get("estacion") or code
            key = code or name

            item = dict(s)
            item["_source_file"] = filename
            item["_code"] = code
            item["_name"] = name
            item["_station"] = station
            item["lat"] = float(lat)
            item["lon"] = float(lon)

            # Prefer higher warning time when choosing, then stable deterministic order.
            try:
                item["_warning"] = float(s.get("effective_warning_seconds") or 0)
            except Exception:
                item["_warning"] = 0.0

            by_key[key] = item

    return list(by_key.values())

def centroid(items):
    return {
        "lat": sum(float(s["lat"]) for s in items) / len(items),
        "lon": sum(float(s["lon"]) for s in items) / len(items),
    }

def build_clusters(sensors):
    remaining = sorted(
        sensors,
        key=lambda s: (-float(s.get("_warning", 0)), str(s.get("_name", "")))
    )

    raw_clusters = []

    while remaining:
        seed = remaining[0]
        group = []

        for s in remaining:
            if km(seed, s) <= CLUSTER_RADIUS_KM:
                group.append(s)

        group_keys = {id(s) for s in group}
        remaining = [s for s in remaining if id(s) not in group_keys]

        group = sorted(group, key=lambda s: (-float(s.get("_warning", 0)), str(s.get("_name", ""))))
        raw_clusters.append(group)

    return raw_clusters

def propose_cells(raw_clusters):
    cells = []
    isolated = []

    for group in raw_clusters:
        if len(group) < MIN_SENSORS_PER_CELL:
            isolated.extend(group)
            continue

        primary = group[:SENSORS_PER_CELL]
        reserve = group[SENSORS_PER_CELL:]
        center = centroid(primary)

        too_close = False
        for c in cells:
            if km(center, c["center"]) < MIN_CELL_DISTANCE_KM:
                too_close = True
                break

        if too_close:
            isolated.extend(group)
            continue

        b = bearing_deg(HOME, center)
        cells.append({
            "cell_id": f"auto_cell_{len(cells) + 1:02d}",
            "role": "early_warning",
            "status": "strong_cell" if len(primary) >= 3 else "good_cell",
            "label": f"{direction_label(b)}",
            "center": {
                "lat": round(center["lat"], 5),
                "lon": round(center["lon"], 5),
            },
            "direction": direction_label(b),
            "primary": primary,
            "reserve_or_context": reserve,
        })

    return cells, isolated

def clean_sensor(s):
    return {
        "code": s.get("_code"),
        "name": s.get("_name"),
        "station": s.get("_station"),
        "lat": s.get("lat"),
        "lon": s.get("lon"),
        "effective_warning_seconds": s.get("effective_warning_seconds"),
        "direction": s.get("direction"),
        "source_file": s.get("_source_file"),
    }

def main():
    sensors = load_sensors()
    raw_clusters = build_clusters(sensors)
    cells, isolated = propose_cells(raw_clusters)

    result = {
        "policy": {
            "cluster_radius_km": CLUSTER_RADIUS_KM,
            "min_cell_distance_km": MIN_CELL_DISTANCE_KM,
            "sensors_per_cell": SENSORS_PER_CELL,
            "min_sensors_per_cell": MIN_SENSORS_PER_CELL,
            "isolated_sensor_policy": "observer_only",
        },
        "input_files": INPUTS,
        "loaded_sensors": len(sensors),
        "raw_clusters_count": len(raw_clusters),
        "proposed_cells_count": len(cells),
        "proposed_cells": [
            {
                **{k: v for k, v in c.items() if k not in ("primary", "reserve_or_context")},
                "primary": [clean_sensor(s) for s in c["primary"]],
                "reserve_or_context": [clean_sensor(s) for s in c["reserve_or_context"]],
            }
            for c in cells
        ],
        "observer_only": [clean_sensor(s) for s in isolated],
    }

    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = []
    lines.append("CUYUM v1.2 - Proposed microcells from current auto inventories")
    lines.append("=" * 72)
    lines.append(f"Loaded sensors: {len(sensors)}")
    lines.append(f"Raw dense clusters: {len(raw_clusters)}")
    lines.append(f"Proposed cells: {len(cells)}")
    lines.append(f"Observer-only sensors: {len(isolated)}")
    lines.append("")
    lines.append("Policy:")
    lines.append(f"- cluster_radius_km: {CLUSTER_RADIUS_KM}")
    lines.append(f"- min_cell_distance_km: {MIN_CELL_DISTANCE_KM}")
    lines.append(f"- sensors_per_cell: {SENSORS_PER_CELL}")
    lines.append(f"- min_sensors_per_cell: {MIN_SENSORS_PER_CELL}")
    lines.append("")

    for c in cells:
        lines.append("-" * 72)
        lines.append(f"{c['cell_id']} | {c['status']} | direction={c['direction']} | center={c['center']}")
        lines.append("Primary:")
        for s in c["primary"]:
            lines.append(f"  - {s.get('_name')} | {s.get('_code')} | warning={s.get('effective_warning_seconds')} | {s['lat']},{s['lon']}")
        if c["reserve_or_context"]:
            lines.append("Reserve/context:")
            for s in c["reserve_or_context"]:
                lines.append(f"  - {s.get('_name')} | {s.get('_code')} | warning={s.get('effective_warning_seconds')} | {s['lat']},{s['lon']}")
        lines.append("")

    if isolated:
        lines.append("-" * 72)
        lines.append("Observer-only / not enough separated coverage:")
        for s in isolated:
            lines.append(f"  - {s.get('_name')} | {s.get('_code')} | warning={s.get('effective_warning_seconds')} | {s['lat']},{s['lon']}")

    OUTPUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written: {OUTPUT_TXT}")
    print(f"Written: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
