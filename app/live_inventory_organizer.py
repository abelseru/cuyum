#!/usr/bin/env python3
import argparse
import json
import math
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent

CENTER_FILE = BASE / "config/system_center.json"
CANDIDATE_FILE = BASE / "config/candidate_inventory.json"
STATION_CATALOG_FILE = BASE / "config/seedlink_station_catalog.json"
GEO_OVERRIDES_FILE = BASE / "config/sensor_geo_overrides.json"
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


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def catalog_items_to_sensors(catalog, center):
    raw = catalog.get("sensors") or catalog.get("sensores") or catalog.get("stations") or catalog

    if isinstance(raw, dict):
        items = list(raw.values())
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    out = []

    for item in items:
        if not isinstance(item, dict):
            continue

        s = dict(item)

        red = s.get("red") or s.get("network")
        est = s.get("estacion") or s.get("station")
        can = s.get("canal") or s.get("channel")

        if not red or not est or not can:
            sid = s.get("sensor_id") or s.get("id") or ""
            parts = str(sid).split(".")
            if len(parts) >= 3:
                red = red or parts[0]
                est = est or parts[1]
                can = can or parts[-1]

        s["red"] = red
        s["estacion"] = est
        s["canal"] = can
        s["nombre"] = s.get("nombre") or s.get("name") or s.get("station_name") or f"{red}.{est}.{can}"

        lat = fnum(s.get("lat"), None)
        lon = fnum(s.get("lon"), None)

        if lat is None or lon is None:
            continue

        s["lat"] = lat
        s["lon"] = lon

        dist = fnum(s.get("distancia_km") or s.get("distance_km"), None)
        if dist is None:
            dist = haversine_km(center["lat"], center["lon"], lat, lon)

        s["distancia_km"] = round(dist, 1)

        if red and est and can:
            out.append(s)

    return out


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


def station_key(s):
    red = s.get("red") or s.get("network")
    est = s.get("estacion") or s.get("station")
    if not red or not est:
        return sensor_code(s)
    return f"{red}.{est}"


def channel_priority(s):
    canal = str(s.get("canal") or s.get("channel") or "").upper()
    order = {
        "BHZ": 0,
        "HHZ": 1,
        "EHZ": 2,
        "SHZ": 3,
    }
    return order.get(canal, 99)


def apply_geo_overrides(sensors, overrides):
    if not isinstance(overrides, dict):
        return sensors

    # El archivo puede venir como {"RI.LPCA.EHZ": {...}} o {"sensors": {...}}
    table = overrides.get("sensors") if isinstance(overrides.get("sensors"), dict) else overrides

    out = []
    for s in sensors:
        code = sensor_code(s)
        key_station = station_key(s)

        ov = None
        if code in table:
            ov = table.get(code)
        elif key_station in table:
            ov = table.get(key_station)

        if isinstance(ov, dict):
            s = dict(s)
            s["_has_geo_override"] = True
            if ov.get("lat") is not None:
                s["lat"] = ov.get("lat")
            if ov.get("lon") is not None:
                s["lon"] = ov.get("lon")
            if ov.get("name") or ov.get("nombre"):
                s["nombre"] = ov.get("nombre") or ov.get("name")
            if ov.get("localidad"):
                s["localidad"] = ov.get("localidad")

        out.append(s)

    return out


def dedupe_physical_stations(sensors):
    best = {}

    for s in sensors:
        key = station_key(s)
        if not key:
            continue

        current = best.get(key)
        if current is None:
            best[key] = s
            continue

        # Misma estación física: preferir canal vertical broadband y luego menor distancia.
        new_rank = (
            0 if s.get("_has_geo_override") else 1,
            channel_priority(s),
            fnum(s.get("distancia_km")),
            sensor_code(s) or "",
        )
        old_rank = (
            0 if current.get("_has_geo_override") else 1,
            channel_priority(current),
            fnum(current.get("distancia_km")),
            sensor_code(current) or "",
        )

        if new_rank < old_rank:
            best[key] = s

    return list(best.values())



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
    station_catalog = load_json(STATION_CATALOG_FILE)
    geo_overrides = load_json(GEO_OVERRIDES_FILE)

    if "lat" not in center or "lon" not in center:
        raise SystemExit("config/system_center.json no tiene lat/lon")

    # Fuente principal: catálogo completo recién reconstruido para este centro.
    # candidate_inventory puede venir ya podado; no debe decidir la selección final.
    catalog_sensors = catalog_items_to_sensors(station_catalog, center)

    if catalog_sensors:
        source_name = "seedlink_station_catalog"
        source_sensors = catalog_sensors
    else:
        source_name = "candidate_inventory"
        source_sensors = candidate.get("sensores", [])

    all_sensors = [normalize_sensor(s) for s in source_sensors if usable(s)]
    all_sensors = apply_geo_overrides(all_sensors, geo_overrides)

    # Recalcular distancia después de aplicar overrides.
    recalculated = []
    for s in all_sensors:
        if not usable(s):
            continue
        s = normalize_sensor(s)
        s["distancia_km"] = round(
            haversine_km(center["lat"], center["lon"], s["lat"], s["lon"]),
            1
        )
        recalculated.append(s)

    all_sensors = [
        s for s in recalculated
        if fnum(s.get("distancia_km")) <= 800
    ]

    # Una estación física cuenta una sola vez.
    all_sensors = dedupe_physical_stations(all_sensors)

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
        s["role"] = "early_warning"
        s["puede_disparar"] = True
        s["puede_confirmar"] = True
        s["cell_hint"] = "cell_00"

    grouped = {}
    for s in observer_candidates:
        deg = bearing(float(center["lat"]), float(center["lon"]), float(s["lat"]), float(s["lon"]))
        sec = sector_name(deg)
        s["rol"] = "observador_regional"
        s["role"] = "regional_observer"
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
        "source": source_name,
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
