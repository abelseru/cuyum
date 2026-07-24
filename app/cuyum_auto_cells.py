#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuyum v1.2 - Auto-celdas
Does not modify the live system.

Objetivo:
- Mantener cell_00 como local/control.
- Build external cells from sensors already observed through SeedLink.
- Do not create cells that cannot provide at least 10 useful seconds of warning.
- Avoid overlap among primary sensors.

En esta primera versión el script usa cachés/reportes existentes del trabajo v4:
- inventory_cell_02_live_v4d.json
- inventory_cells_v4c_suggested.json
- seedlink_probe_v4c_report.json
- cell_candidates_report_v4.json

Si no hay caché suficiente, no inventa cobertura: deja reporte de no creación.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

APP_DIR = Path(__file__).resolve().parent
BASE = APP_DIR.parent


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(name: str, default: Any = None) -> Any:
    p = BASE / name
    if not p.exists():
        return default
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(name: str, data: Any) -> None:
    with (BASE / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1-a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def direction_label(b: float) -> str:
    labels = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return labels[int((b + 22.5) // 45) % 8]


def effective_warning_seconds(distance_km: float, cfg: Dict[str, Any]) -> float:
    prop = cfg.get("propagation_model", {})
    v = float(prop.get("assumed_s_wave_km_s", 3.5))
    decision = float(prop.get("decision_latency_seconds", 3))
    margin = float(prop.get("safety_margin_seconds", 2))
    return distance_km / v - decision - margin


def parse_code(code: str) -> Tuple[str, str, str]:
    parts = code.split(".")
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return code, "", ""


def station_key(code: str) -> str:
    n, s, _ = parse_code(code)
    return f"{n}.{s}"


def load_coordinate_index() -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for fname in ["cell_candidates_report_v4.json", "cell_candidates_report_v3.json", "cell_candidates_report_v2.json"]:
        data = load_json(fname, {})
        results = data.get("results") or data.get("cells") or []
        if not isinstance(results, list):
            continue
        for res in results:
            for key in ["candidate_pool", "principals_preview", "primary", "reserve_or_context"]:
                arr = res.get(key) or []
                if not isinstance(arr, list):
                    continue
                for item in arr:
                    code = item.get("code")
                    if not code:
                        continue
                    lat, lon = item.get("lat"), item.get("lon")
                    if lat is None or lon is None:
                        continue
                    idx[code] = item
    return idx


def load_local_live(cfg: Dict[str, Any]) -> Dict[str, Any]:
    home = cfg["project"]["home"]
    local_codes: List[Dict[str, Any]] = []

    # Prefer current estado JSON if available.
    estado = load_json("runtime/state_cell_00_seedlink.json", {}) or load_json("estado_grupo_01.json", {}) or {}
    # The exact live-state schema changed across prototypes, so also read sensor_catalog.
    catalog = load_json("config/sensor_catalog.json", {}) or {}
    if isinstance(catalog, dict):
        for code, meta in catalog.items():
            if not isinstance(meta, dict):
                continue
            op = str(meta.get("operational_state", meta.get("state", ""))).lower()
            if op in ["activo", "active", "preferred", "reliable", "observed", ""]:
                if any(code.endswith(ch) for ch in [".BHZ", ".HHZ", ".EHZ", ".SHZ"]):
                    local_codes.append({
                        "code": code,
                        "site": meta.get("site", meta.get("station_name", "catalog")),
                        "score": float(meta.get("score_selection", meta.get("score", 0.5))),
                        "source": "sensor_catalog"
                    })
    # No legacy local fallback.
    # cell_00 must be built only from real local inventory/catalog entries.
    # If no local sensors are available for the selected center, it remains reference_only.
    local_codes = [
        item for item in local_codes
        if item.get("source") not in ["fallback", "legacy_live_cell"]
        and item.get("site") != "legacy_live_cell"
    ]

    # Sort and keep target amount.
    target = int(cfg["cell_generation"].get("local_sensors_per_cell", cfg["cell_generation"].get("sensors_per_cell", 5)))
    local_codes = sorted(local_codes, key=lambda x: x.get("score", 0), reverse=True)[:target]

    status = "active_reference" if local_codes else "reference_only"
    message = (
        "Local/control zone. It does not count as early warning; it is used for immediate warning, coherence, and scoring."
        if local_codes
        else "Reference center only. No local live sensor inventory is available for this center."
    )

    return {
        "cell_id": "cell_00",
        "role": "local_control",
        "status": status,
        "label": home.get("label", "home"),
        "center": {"lat": home["lat"], "lon": home["lon"]},
        "primary": local_codes,
        "reserve_or_context": [],
        "effective_warning_seconds": 0,
        "message": message
    }


def add_coords_and_metrics(sensor: Dict[str, Any], coord_idx: Dict[str, Dict[str, Any]], cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    code = sensor.get("code")
    if not code:
        return None
    base = dict(sensor)
    src = coord_idx.get(code)
    if src:
        base.setdefault("lat", src.get("lat"))
        base.setdefault("lon", src.get("lon"))
        base.setdefault("site", src.get("site"))
        base.setdefault("center_label", src.get("center_label"))
        base.setdefault("provider", src.get("provider"))
    if base.get("lat") is None or base.get("lon") is None:
        return None
    home = cfg["project"]["home"]
    dist = haversine_km(float(home["lat"]), float(home["lon"]), float(base["lat"]), float(base["lon"]))
    b = bearing_deg(float(home["lat"]), float(home["lon"]), float(base["lat"]), float(base["lon"]))
    max_dist = float(cfg["cell_generation"].get("max_sensor_distance_from_home_km", 800))
    if dist > max_dist:
        return None

    base["distance_from_home_km"] = round(dist, 1)
    base["bearing_deg"] = round(b, 1)
    base["direction"] = direction_label(b)
    base["effective_warning_seconds"] = round(effective_warning_seconds(dist, cfg), 1)
    base["station_key"] = station_key(code)
    return base


def load_confirmed_live_external(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load external candidate sensors from:
    - current live auto-cell inventories: config/auto_cell_*_inventory.json
    - current sensor catalog: config/sensor_catalog.json

    This function only builds a candidate pool. The clustering policy later decides
    whether a sensor group is valid, duplicated, isolated, or only context/reserve.
    """
    coord_idx = load_coordinate_index()
    sensors: Dict[str, Dict[str, Any]] = {}

    def code_from_parts(item: Dict[str, Any]) -> Optional[str]:
        code = item.get("code") or item.get("sensor_id")
        if code:
            return str(code)

        network = item.get("network")
        station = item.get("station")
        channel = item.get("channel")
        if network and station and channel:
            return f"{network}.{station}.{channel}"

        return None

    def ingest(item: Dict[str, Any], source_role: str) -> None:
        if not isinstance(item, dict):
            return

        code = code_from_parts(item)
        if not code:
            return

        if not any(code.endswith(ch) for ch in [".BHZ", ".HHZ", ".EHZ", ".SHZ"]):
            return

        state = str(item.get("state", item.get("operational_state", "active"))).lower()
        if state in ["disabled", "down", "caido", "deshabilitado", "suspect", "sospechoso"]:
            return

        can_trigger = item.get("can_trigger", True)
        can_confirm = item.get("can_confirm", True)

        # Remote validating candidates should be able to participate.
        # Pure observers can remain in catalogs, but they should not become validating auto-cells.
        if can_trigger is False and can_confirm is False:
            return

        normalized = {
            "code": code,
            "site": item.get("site", item.get("name", item.get("station_name", code))),
            "lat": item.get("lat", item.get("latitude")),
            "lon": item.get("lon", item.get("longitude")),
            "packets": item.get("packets", item.get("confirmation_packets", item.get("packets_total_observed", 1))),
            "latency_seconds": item.get("latency_seconds", item.get("confirmed_latency_seconds", item.get("latency_last_seconds", 999))),
            "source_role": source_role,
            "live_status": item.get("live_status", item.get("state", item.get("operational_state", "catalog"))),
            "can_trigger": can_trigger,
            "can_confirm": can_confirm,
            "score": item.get("score_selection", item.get("score", 0.5)),
        }

        # Keep best version of the same code.
        old = sensors.get(code)
        if old is None:
            sensors[code] = normalized
            return

        new_rank = (
            int(normalized.get("packets", 0) or 0),
            -float(normalized.get("latency_seconds", 999) or 999),
            float(normalized.get("score", 0) or 0)
        )
        old_rank = (
            int(old.get("packets", 0) or 0),
            -float(old.get("latency_seconds", 999) or 999),
            float(old.get("score", 0) or 0)
        )

        if new_rank > old_rank:
            sensors[code] = normalized

    # 1) Current live auto-cell inventories.
    for inv_path in sorted((BASE / "config").glob("auto_cell_*_inventory.json")):
        inv = load_json(str(inv_path.relative_to(BASE)), {}) or {}
        if not isinstance(inv, dict):
            continue

        for s in inv.get("sensors", []) or []:
            ingest(s, f"live_inventory:{inv_path.name}:sensor")

        for s in inv.get("reserves", []) or []:
            ingest(s, f"live_inventory:{inv_path.name}:reserve")

        for s in inv.get("primary", []) or []:
            ingest(s, f"live_inventory:{inv_path.name}:primary")

        for s in inv.get("reserve_or_context", []) or []:
            ingest(s, f"live_inventory:{inv_path.name}:reserve_or_context")

    # 2) Current nested sensor catalog.
    catalog = load_json("config/sensor_catalog.json", {}) or {}
    if isinstance(catalog, dict):
        catalog_sensors = catalog.get("sensors", catalog)
        if isinstance(catalog_sensors, dict):
            for code, meta in catalog_sensors.items():
                if not isinstance(meta, dict):
                    continue
                item = dict(meta)
                item.setdefault("code", code)
                ingest(item, "sensor_catalog")

    enriched: List[Dict[str, Any]] = []
    for s in sensors.values():
        e = add_coords_and_metrics(s, coord_idx, cfg)
        if e:
            enriched.append(e)

    min_warn = float(cfg["cell_generation"].get("min_effective_warning_seconds", 10))
    filtered = [
        s for s in enriched
        if float(s.get("effective_warning_seconds", -999)) >= min_warn
    ]

    return filtered

def cluster_live_sensors(sensors: List[Dict[str, Any]], cfg: Dict[str, Any], used_station_keys: set) -> List[Dict[str, Any]]:
    """
    Build external microcells from live SeedLink sensors.

    Policy:
    - A validating auto-cell needs at least 2 different stations.
    - Ideal size is 3 primary sensors.
    - Once a dense geographic group is used, the whole dense group is marked as assigned.
      This avoids splitting the same city/cluster into auto_cell_01 and auto_cell_02.
    - Isolated sensors are not promoted to validating cells.
    """
    gen = cfg["cell_generation"]

    target = int(gen.get("sensors_per_cell", 3))
    minimum = int(gen.get("min_sensors_per_cell", 2))
    reserve_count = int(gen.get("reserve_sensors_per_cell", 3))

    cluster_radius = float(gen.get("cluster_radius_km", 70))
    min_cell_dist = float(gen.get("min_cell_distance_km", 120))
    dense_exclusion = float(gen.get("dense_cluster_exclusion_km", 90))

    max_external = max(0, int(gen.get("target_total_cells_including_local", 5)) - 1)

    available = [
        s for s in sensors
        if s.get("station_key") not in used_station_keys
        and s.get("lat") is not None
        and s.get("lon") is not None
    ]

    # Best sensors first: more packets, lower latency, more useful warning.
    available.sort(
        key=lambda s: (
            -float(s.get("effective_warning_seconds", 0) or 0),
            float(s.get("latency_seconds", 999) or 999),
            -(int(s.get("packets", 0) or 0))
        )
    )

    clusters: List[Dict[str, Any]] = []
    assigned_keys: set = set()
    covered_points: List[Tuple[float, float]] = []

    def is_covered(sensor: Dict[str, Any]) -> bool:
        lat = float(sensor["lat"])
        lon = float(sensor["lon"])
        for clat, clon in covered_points:
            if haversine_km(lat, lon, clat, clon) < dense_exclusion:
                return True
        return False

    while len(clusters) < max_external:
        seed = None
        for s in available:
            key = s["station_key"]
            if key in assigned_keys:
                continue
            if is_covered(s):
                assigned_keys.add(key)
                continue
            seed = s
            break

        if not seed:
            break

        # Build dense group around this seed.
        raw_group = []
        for s in available:
            key = s["station_key"]
            if key in assigned_keys:
                continue

            d = haversine_km(
                float(seed["lat"]),
                float(seed["lon"]),
                float(s["lat"]),
                float(s["lon"])
            )

            if d <= cluster_radius:
                raw_group.append(s)

        # Deduplicate by station, keeping the best channel/version.
        dedup: Dict[str, Dict[str, Any]] = {}
        for s in raw_group:
            k = s["station_key"]
            old = dedup.get(k)
            if old is None:
                dedup[k] = s
                continue

            new_rank = (
                int(s.get("packets", 0) or 0),
                -float(s.get("latency_seconds", 999) or 999),
                float(s.get("effective_warning_seconds", 0) or 0)
            )
            old_rank = (
                int(old.get("packets", 0) or 0),
                -float(old.get("latency_seconds", 999) or 999),
                float(old.get("effective_warning_seconds", 0) or 0)
            )

            if new_rank > old_rank:
                dedup[k] = s

        group = list(dedup.values())
        group.sort(
            key=lambda s: (
                -float(s.get("effective_warning_seconds", 0) or 0),
                float(s.get("latency_seconds", 999) or 999),
                -(int(s.get("packets", 0) or 0))
            )
        )

        # If the group is too small, it is isolated or weak. It is not a validating cell.
        if len(group) < minimum:
            assigned_keys.add(seed["station_key"])
            continue

        primary = group[:target]
        reserve = group[target:target + reserve_count]

        lat = sum(float(s["lat"]) for s in primary) / len(primary)
        lon = sum(float(s["lon"]) for s in primary) / len(primary)

        # Avoid duplicate/nearby auto-cell centers.
        too_close = False
        for c in clusters:
            cd = haversine_km(lat, lon, c["center"]["lat"], c["center"]["lon"])
            if cd < min_cell_dist:
                too_close = True
                break

        # Avoid splitting a dense area already represented by another accepted cell.
        if not too_close:
            for s in primary:
                if is_covered(s):
                    too_close = True
                    break

        if too_close:
            for s in group:
                assigned_keys.add(s["station_key"])
            continue

        home = cfg["project"]["home"]
        dist_home = haversine_km(float(home["lat"]), float(home["lon"]), lat, lon)
        b = bearing_deg(float(home["lat"]), float(home["lon"]), lat, lon)
        warn = effective_warning_seconds(dist_home, cfg)

        clusters.append({
            "cell_id": f"auto_cell_{len(clusters)+1:02d}",
            "role": "early_warning",
            "status": "strong_cell" if len(primary) >= 3 else "good_cell",
            "label": f"Auto {direction_label(b)} / {primary[0].get('center_label') or primary[0].get('site') or 'grupo vivo'}",
            "center": {"lat": round(lat, 5), "lon": round(lon, 5)},
            "direction": direction_label(b),
            "distance_from_home_km": round(dist_home, 1),
            "effective_warning_seconds": round(warn, 1),
            "primary": primary,
            "reserve_or_context": reserve,
            "message": "Cell automatically generated from live SeedLink sensors. Dense source areas are not split into duplicate cells."
        })

        # Important: mark the whole dense group as assigned, not only primary.
        for s in group:
            assigned_keys.add(s["station_key"])

        # Mark accepted primary area as covered.
        for s in primary:
            used_station_keys.add(s["station_key"])
            covered_points.append((float(s["lat"]), float(s["lon"])))

    return clusters

def text_report(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("CUYUM v1.2 - AUTO CELDAS")
    lines.append("Does not modify the live system.")
    lines.append("Design default: auto-cells from live sensors, without overlapping primary sensors.")
    lines.append(f"Generado: {data['generated_at']}")
    lines.append("")
    cfg = data["config_summary"]
    lines.append(f"Home: {cfg['home_label']} lat={cfg['home_lat']} lon={cfg['home_lon']}")
    lines.append(f"Objetivo total incluyendo local: {cfg['target_total_cells_including_local']}")
    lines.append(f"Sensors per cell: {cfg['sensors_per_cell']} | minimum: {cfg['min_sensors_per_cell']}")
    lines.append(f"Minimum useful ETA rule: {cfg['min_effective_warning_seconds']} s")
    lines.append(f"Distancia mínima equivalente aprox: {cfg['approx_min_distance_km']} km")
    lines.append("")
    lines.append("="*72)
    for cell in data["cells"]:
        lines.append(f"{cell['cell_id']} | role={cell['role']} | status={cell['status']}")
        lines.append(f"Etiqueta: {cell.get('label','')}")
        if cell["role"] == "early_warning":
            lines.append(f"Direction={cell.get('direction')} | home_distance={cell.get('distance_from_home_km')} km | useful_warning≈{cell.get('effective_warning_seconds')} s")
        else:
            lines.append(cell.get("message", ""))
        lines.append(f"Primary: {len(cell.get('primary', []))} | Reserves/context: {len(cell.get('reserve_or_context', []))}")
        for i, s in enumerate(cell.get("primary", []), 1):
            extra = ""
            if cell["role"] == "early_warning":
                extra = f" packets={s.get('packets','?')} lat={s.get('latency_seconds','?')}s dir={s.get('direction','?')} warning={s.get('effective_warning_seconds','?')}s"
            lines.append(f"  {i:02d}. {s.get('code','?'):<14} {s.get('site','')}{extra}")
        if cell.get("reserve_or_context"):
            lines.append("Reserves/context:")
            for i, s in enumerate(cell.get("reserve_or_context", [])[:8], 1):
                lines.append(f"  R{i:02d}. {s.get('code','?'):<14} {s.get('site','')} packets={s.get('packets','?')} lat={s.get('latency_seconds','?')}s")
        lines.append("")
        lines.append("="*72)
    if data.get("not_created"):
        lines.append("Cells not created:")
        for item in data["not_created"]:
            lines.append(f"- {item['cell_id']}: {item['reason']}")
        lines.append("")
    lines.append("Archivos generados:")
    lines.append("- auto_cells_report.txt")
    lines.append("- auto_cells_report.json")
    lines.append("- config/auto_inventory_cells.json")
    lines.append("- cuyum_runtime_cells.json")
    return "\n".join(lines) + "\n"


def main() -> None:
    cfg = load_json("cuyum_auto_config.json")
    if not cfg:
        raise SystemExit("ERROR: falta cuyum_auto_config.json")

    gen = cfg["cell_generation"]
    prop = cfg["propagation_model"]
    approx_min_dist = (float(gen.get("min_effective_warning_seconds", 10)) + float(prop.get("decision_latency_seconds", 3)) + float(prop.get("safety_margin_seconds", 2))) * float(prop.get("assumed_s_wave_km_s", 3.5))

    local = load_local_live(cfg)
    used = {station_key(s["code"]) for s in local.get("primary", []) if s.get("code")}

    live = load_confirmed_live_external(cfg)
    clusters = cluster_live_sensors(live, cfg, used)

    target_total = int(gen.get("target_total_cells_including_local", 4))
    not_created = []
    for i in range(len(clusters) + 1, target_total):
        not_created.append({
            "cell_id": f"auto_cell_{i:02d}",
            "reason": "no other sufficiently separated live SeedLink sensor group was found with at least 10 useful warning seconds"
        })

    cells = [local] + clusters
    data = {
        "generated_at": now_iso(),
        "description": "Cuyum v1.2 auto-cells. Not automatically applied to the live system.",
        "config_summary": {
            "home_label": cfg["project"]["home"].get("label"),
            "home_lat": cfg["project"]["home"].get("lat"),
            "home_lon": cfg["project"]["home"].get("lon"),
            "target_total_cells_including_local": target_total,
            "sensors_per_cell": gen.get("sensors_per_cell"),
            "min_sensors_per_cell": gen.get("min_sensors_per_cell"),
            "min_effective_warning_seconds": gen.get("min_effective_warning_seconds"),
            "approx_min_distance_km": round(approx_min_dist, 1),
            "mode": gen.get("mode", "auto")
        },
        "input_files_used": [
            name for name in [
                "cuyum_auto_config.json",
                "cell_candidates_report_v4.json",
                "inventory_cell_02_live_v4d.json",
                "inventory_cells_v4c_suggested.json",
                "config/sensor_catalog.json"
            ] if (BASE / name).exists()
        ],
        "cells": cells,
        "not_created": not_created
    }

    # Minimal runtime inventory shape.
    runtime = {
        "generated_at": data["generated_at"],
        "mode": "auto",
        "warning_rule": "early_warning cells require at least 10 estimated useful seconds; otherwise they are excluded or kept as local/control.",
        "cells": {}
    }
    for c in cells:
        runtime["cells"][c["cell_id"]] = {
            "role": c["role"],
            "status": c["status"],
            "label": c.get("label"),
            "center": c.get("center"),
            "direction": c.get("direction"),
            "effective_warning_seconds": c.get("effective_warning_seconds"),
            "primary": c.get("primary", []),
            "reserve_or_context": c.get("reserve_or_context", [])
        }

    save_json("auto_cells_report.json", data)
    save_json("config/auto_inventory_cells.json", runtime)
    save_json("cuyum_runtime_cells.json", runtime)
    (BASE / "auto_cells_report.txt").write_text(text_report(data), encoding="utf-8")


if __name__ == "__main__":
    main()
