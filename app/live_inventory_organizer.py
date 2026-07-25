#!/usr/bin/env python3
import argparse
import json
import math
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent

CENTER_FILE = BASE / "config/system_center.json"
CANDIDATE_FILE = BASE / "config/candidate_inventory.json"
REPORT_JSON = BASE / "runtime/live_inventory_organizer_report.json"
REPORT_TXT = BASE / "runtime/live_inventory_organizer_report.txt"


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fnum(value, default=999999.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def sensor_code(s):
    red = s.get("red") or s.get("network")
    est = s.get("estacion") or s.get("station")
    can = s.get("canal") or s.get("channel")
    if not red or not est or not can:
        return None
    return f"{red}.{est}.{can}"


def has_geo(s):
    return s.get("lat") is not None and s.get("lon") is not None


def usable(s):
    return bool(sensor_code(s)) and has_geo(s)


def bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def sector_name(deg):
    if deg >= 337.5 or deg < 22.5:
        return "Norte"
    if deg < 67.5:
        return "Noreste"
    if deg < 112.5:
        return "Este"
    if deg < 157.5:
        return "Sureste"
    if deg < 202.5:
        return "Sur"
    if deg < 247.5:
        return "Suroeste"
    if deg < 292.5:
        return "Oeste"
    return "Noroeste"


def credibility_bonus(s):
    text = " ".join(str(s.get(k) or "") for k in ("red", "network", "nombre", "name", "source_provider"))
    text = text.lower()

    bonus = 0
    if "inpres" in text:
        bonus -= 80
    if "ri." in text or str(s.get("red") or s.get("network")) == "RI":
        bonus -= 40
    if "conicet" in text:
        bonus -= 25
    return bonus


def local_score(s):
    # Local: distancia primero. Nada de ranking oscuro que expulse sensores cercanos.
    return (
        fnum(s.get("distancia_km") or s.get("distance_km")),
        fnum(s.get("latencia_aprox_seg") or s.get("latency_seconds"), 999),
        -fnum(s.get("paquetes_ultima_revision") or s.get("packets"), 0),
        sensor_code(s) or "",
    )


def observer_score(s):
    # Observadores: distancia dentro de su zona + pequeña preferencia por fuentes creíbles.
    return (
        fnum(s.get("distancia_km") or s.get("distance_km")) + credibility_bonus(s),
        fnum(s.get("latencia_aprox_seg") or s.get("latency_seconds"), 999),
        -fnum(s.get("paquetes_ultima_revision") or s.get("packets"), 0),
        sensor_code(s) or "",
    )


def normalize_sensor(s):
    red = s.get("red") or s.get("network")
    est = s.get("estacion") or s.get("station")
    can = s.get("canal") or s.get("channel")
    nombre = s.get("nombre") or s.get("name") or sensor_code(s)

    out = dict(s)
    out["red"] = red
    out["estacion"] = est
    out["canal"] = can
    out["nombre"] = nombre
    out["lat"] = fnum(out.get("lat"), None)
    out["lon"] = fnum(out.get("lon"), None)
    out["distancia_km"] = round(fnum(out.get("distancia_km") or out.get("distance_km")), 1)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-max-km", type=float, default=200.0)
    parser.add_argument("--local-max", type=int, default=4)
    parser.add_argument("--zone-max", type=int, default=4)
    parser.add_argument("--sensors-per-zone", type=int, default=3)
    parser.add_argument("--absolute-max", type=int, default=18)
    args = parser.parse_args()

    center = load_json(CENTER_FILE)
    candidate = load_json(CANDIDATE_FILE)

    if "lat" not in center or "lon" not in center:
        raise SystemExit("config/system_center.json no tiene lat/lon")

    all_sensors = [normalize_sensor(s) for s in candidate.get("sensores", []) if usable(s)]
    all_sensors = [
        s for s in all_sensors
        if fnum(s.get("distancia_km")) <= 800
    ]

    # Reset completo de inventarios y estados de celdas anteriores.
    # Esto se ejecuta solo cuando se reorganiza por cambio de centro,
    # no en cada arranque normal de Cuyum.
    for old_inventory in (BASE / "config").glob("auto_cell_*_inventory.json"):
        old_inventory.unlink()

    for old_state in (BASE / "runtime").glob("auto_cell_*_state.json"):
        old_state.unlink()

    runtime_cells = BASE / "cuyum_runtime_cells.json"
    if runtime_cells.exists():
        runtime_cells.unlink()

    local_candidates = [
        s for s in all_sensors
        if fnum(s.get("distancia_km")) <= args.local_max_km
    ]
    observer_candidates = [
        s for s in all_sensors
        if fnum(s.get("distancia_km")) > args.local_max_km
    ]

    local = sorted(local_candidates, key=local_score)[:args.local_max]

    for s in local:
        s["rol"] = "anticipacion"
        s["puede_disparar"] = True
        s["puede_confirmar"] = True
        s["cell_hint"] = "cell_00"

    grouped = {}
    for s in observer_candidates:
        deg = bearing(float(center["lat"]), float(center["lon"]), float(s["lat"]), float(s["lon"]))
        sec = sector_name(deg)
        s["rol"] = "observador_regional"
        s["puede_disparar"] = False
        s["puede_confirmar"] = True
        s["direction"] = sec
        s["direccion"] = sec
        grouped.setdefault(sec, []).append(s)

    zone_pack = []
    for sec, items in grouped.items():
        chosen = sorted(items, key=observer_score)[:args.sensors_per_zone]
        if chosen:
            nearest = min(fnum(s.get("distancia_km")) for s in chosen)
            zone_pack.append((nearest, sec, chosen))

    zone_pack = sorted(zone_pack, key=lambda x: x[0])[:args.zone_max]

    # Límite absoluto real.
    used_total = len(local)
    final_zones = []
    for nearest, sec, chosen in zone_pack:
        room = args.absolute_max - used_total
        if room <= 0:
            break
        chosen = chosen[:min(len(chosen), room)]
        if chosen:
            final_zones.append((nearest, sec, chosen))
            used_total += len(chosen)

    # candidate_inventory final queda solo con sensores locales.
    final_candidate = dict(candidate)
    final_candidate["sensores"] = local
    final_candidate["organized_by"] = "live_inventory_organizer"
    final_candidate["organized_at"] = datetime.now().isoformat()
    final_candidate["limits"] = {
        "local_max_km": args.local_max_km,
        "local_max": args.local_max,
        "zone_max": args.zone_max,
        "sensors_per_zone": args.sensors_per_zone,
        "absolute_max": args.absolute_max,
        "final_total": used_total,
    }
    save_json(CANDIDATE_FILE, final_candidate)

    written = []

    for idx, (_, sec, chosen) in enumerate(final_zones, start=1):
        lat_avg = sum(float(s["lat"]) for s in chosen) / len(chosen)
        lon_avg = sum(float(s["lon"]) for s in chosen) / len(chosen)

        inv = {
            "cell_id": f"auto_cell_{idx:02d}",
            "label": sec,
            "direction": sec,
            "generated_by": "live_inventory_organizer",
            "generated_at": datetime.now().isoformat(),
            "center": {
                "label": sec,
                "lat": round(lat_avg, 6),
                "lon": round(lon_avg, 6),
            },
            "sensores": chosen,
        }

        out = BASE / f"config/auto_cell_{idx:02d}_inventory.json"
        save_json(out, inv)
        written.append(str(out.relative_to(BASE)))

    report = {
        "center": center,
        "all_usable_candidates": len(all_sensors),
        "local_count": len(local),
        "zone_count": len(final_zones),
        "total_final_sensors": used_total,
        "local": [
            {
                "code": sensor_code(s),
                "name": s.get("nombre"),
                "distance_km": s.get("distancia_km"),
            }
            for s in local
        ],
        "zones": [
            {
                "label": sec,
                "count": len(chosen),
                "sensors": [
                    {
                        "code": sensor_code(s),
                        "name": s.get("nombre"),
                        "distance_km": s.get("distancia_km"),
                    }
                    for s in chosen
                ],
            }
            for _, sec, chosen in final_zones
        ],
        "written": written,
    }

    save_json(REPORT_JSON, report)

    lines = []
    lines.append("CUYUM live inventory organizer")
    lines.append("=" * 60)
    lines.append(f"Center: {center.get('label')} lat={center.get('lat')} lon={center.get('lon')}")
    lines.append(f"Usable candidates: {len(all_sensors)}")
    lines.append(f"Local sensors: {len(local)}")
    for s in local:
        lines.append(f"  - LOCAL {sensor_code(s)} | {s.get('nombre')} | {s.get('distancia_km')} km")
    lines.append(f"Zones: {len(final_zones)}")
    for _, sec, chosen in final_zones:
        lines.append(f"  {sec}: {len(chosen)}")
        for s in chosen:
            lines.append(f"    - {sensor_code(s)} | {s.get('nombre')} | {s.get('distancia_km')} km")
    lines.append(f"Total final sensors: {used_total}")
    lines.append("Written:")
    for w in written:
        lines.append(f"  - {w}")
    REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
