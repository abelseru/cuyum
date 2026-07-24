#!/usr/bin/env python3
import json
import sys
import math
import argparse
from pathlib import Path
from datetime import datetime, timezone

CENTER_FILE = Path("config/system_center.json")

CATALOG_FILES = [
    Path("config/seedlink_station_catalog.json"),
    Path("config/sensor_geo_overrides.json"),
]

OUT_JSON = Path("runtime/bootstrap_world_report.json")
OUT_TXT = Path("runtime/bootstrap_world_report.txt")
PLAN_JSON = Path("runtime/bootstrap_apply_plan.json")
PLAN_TXT = Path("runtime/bootstrap_apply_plan.txt")
PREVIEW_DIR = Path("runtime/bootstrap_preview")

LOCAL_RADIUS_KM = 250
REGIONAL_RADIUS_KM = 900
NEIGHBOR_RADIUS_KM = 70
MIN_VALIDATING_NEIGHBORS = 2
LOCAL_TARGET_VALIDATORS = 4
LOCAL_MIN_VALIDATORS = 2

def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def normalize_center(raw):
    if not raw:
        raise SystemExit("[error] falta config/system_center.json")
    if "system_center" in raw:
        raw = raw["system_center"]
    return {
        "label": raw.get("label", "Local"),
        "lat": float(raw["lat"]),
        "lon": float(raw["lon"]),
    }

def km(a, b):
    R = 6371
    lat1, lon1 = math.radians(float(a["lat"])), math.radians(float(a["lon"]))
    lat2, lon2 = math.radians(float(b["lat"])), math.radians(float(b["lon"]))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def bearing_degrees(a, b):
    lat1 = math.radians(float(a["lat"]))
    lat2 = math.radians(float(b["lat"]))
    dlon = math.radians(float(b["lon"]) - float(a["lon"]))

    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def direction_label_from_bearing(deg):
    directions = [
        ("Norte", 337.5, 360.0),
        ("Norte", 0.0, 22.5),
        ("Noreste", 22.5, 67.5),
        ("Este", 67.5, 112.5),
        ("Sureste", 112.5, 157.5),
        ("Sur", 157.5, 202.5),
        ("Suroeste", 202.5, 247.5),
        ("Oeste", 247.5, 292.5),
        ("Noroeste", 292.5, 337.5),
    ]

    for label, start, end in directions:
        if start <= deg < end:
            return label

    return "Zona"


def group_center(group):
    if not group:
        return None
    return {
        "lat": sum(float(s["lat"]) for s in group) / len(group),
        "lon": sum(float(s["lon"]) for s in group) / len(group),
    }


def public_group_label(center, group):
    c = group_center(group)
    if not c:
        return "Zona"
    return direction_label_from_bearing(bearing_degrees(center, c))



def sensor_code(obj):
    return (
        obj.get("sensor_id")
        or obj.get("code")
        or obj.get("trace_id")
        or obj.get("trace_id_last")
        or ".".join(
            str(x)
            for x in [
                obj.get("network") or obj.get("red"),
                obj.get("station") or obj.get("estacion"),
                obj.get("channel") or obj.get("canal"),
            ]
            if x
        )
        or None
    )

def looks_like_sensor_key(key):
    if not isinstance(key, str):
        return False
    parts = key.split(".")
    return len(parts) >= 3 and all(parts[:3])


def collect(obj, source, out, inherited_code=None):
    if isinstance(obj, dict):
        lat = obj.get("lat")
        lon = obj.get("lon")
        code = sensor_code(obj) or inherited_code
        name = obj.get("name") or obj.get("nombre") or obj.get("site") or obj.get("localidad") or code

        if code:
            try:
                key = code
                current = out.get(key, {})

                # Merge metadata even when this source has no coordinates.
                # This lets candidate_inventory provide role/can_confirm/can_trigger
                # while sensor_geo_overrides provides lat/lon.
                merged = {**current, **obj}
                merged["_code"] = code
                merged["_name"] = name or current.get("_name") or code
                merged["_source"] = current.get("_source") or source

                if lat is not None and lon is not None:
                    merged["lat"] = float(lat)
                    merged["lon"] = float(lon)
                elif "lat" not in merged or "lon" not in merged:
                    # Keep partial metadata only if coordinates may arrive from another source later.
                    pass

                out[key] = merged
            except Exception:
                pass

        for k, v in obj.items():
            next_code = k if looks_like_sensor_key(k) else inherited_code
            collect(v, source, out, next_code)

    elif isinstance(obj, list):
        for v in obj:
            collect(v, source, out, inherited_code)

def classify(center, sensors):
    rows = []
    for s in sensors:
        d = km(center, s)
        can_confirm = s.get("can_confirm", s.get("puede_confirmar"))
        can_trigger = s.get("can_trigger", s.get("puede_disparar"))

        item = {
            "code": s["_code"],
            "name": s.get("_name"),
            "lat": s["lat"],
            "lon": s["lon"],
            "distance_km": round(d, 1),
            "role": s.get("role") or s.get("rol"),
            "state": s.get("operational_state") or s.get("state") or s.get("estado"),
            "source": s.get("_source"),
            "can_confirm": bool(can_confirm),
            "can_trigger": bool(can_trigger),
        }

        role_text = str(item.get("role") or "").strip().lower()
        observer_only = role_text in ("observador_regional", "regional_observer", "observer_only")
        validator_capable = bool(item["can_confirm"] or item["can_trigger"])

        if observer_only:
            if d <= REGIONAL_RADIUS_KM:
                item["candidate_class"] = "regional_observer"
            else:
                item["candidate_class"] = "out_of_range"
        elif validator_capable and d <= LOCAL_RADIUS_KM:
            item["candidate_class"] = "local_or_near"
        elif d <= REGIONAL_RADIUS_KM:
            item["candidate_class"] = "regional_observer"
        else:
            item["candidate_class"] = "out_of_range"

        rows.append(item)

    rows.sort(key=lambda x: x["distance_km"])
    return rows

def neighbor_groups(rows):
    usable = [
        r for r in rows
        if r["candidate_class"] == "local_or_near"
        and (r.get("can_confirm") or r.get("can_trigger"))
    ]
    groups = []
    used = set()

    for seed in usable:
        if seed["code"] in used:
            continue

        group = []
        for s in usable:
            if s["code"] in used:
                continue
            if km(seed, s) <= NEIGHBOR_RADIUS_KM:
                group.append(s)

        if len(group) >= MIN_VALIDATING_NEIGHBORS:
            group = sorted(group, key=lambda x: x["distance_km"])
            for s in group:
                used.add(s["code"])
            groups.append(group)

    return groups

def split_code(code):
    parts = str(code).split(".")
    network = parts[0] if len(parts) > 0 else ""
    station = parts[1] if len(parts) > 1 else ""
    channel = parts[2] if len(parts) > 2 else ""
    return network, station, channel


def preview_sensor_entry(sensor, role, can_confirm, can_trigger):
    network, station, channel = split_code(sensor["code"])
    return {
        "red": network,
        "estacion": station,
        "canal": channel,
        "nombre": sensor.get("name") or sensor["code"],
        "lat": sensor.get("lat"),
        "lon": sensor.get("lon"),
        "rol": role,
        "puede_confirmar": bool(can_confirm),
        "puede_disparar": bool(can_trigger),
        "distancia_km": sensor.get("distance_km"),
    }


def write_preview_files(plan):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    sensors = []

    for s in plan.get("local_validators", []):
        sensors.append(preview_sensor_entry(
            s,
            "anticipacion",
            True,
            True
        ))

    for s in plan.get("reserve_context", []):
        sensors.append(preview_sensor_entry(
            s,
            "anticipacion_secundaria",
            True,
            True
        ))

    for s in plan.get("regional_observers", []):
        sensors.append(preview_sensor_entry(
            s,
            "observador_regional",
            False,
            False
        ))

    candidate_inventory = {
        "generated_by": "cuyum_bootstrap_world",
        "mode": "preview",
        "center": plan["center"],
        "sensores": sensors,
    }

    (PREVIEW_DIR / "candidate_inventory.preview.json").write_text(
        json.dumps(candidate_inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    # Remove stale extra-cell previews from previous runs.
    for stale in PREVIEW_DIR.glob("auto_cell_*_inventory.preview.json"):
        stale.unlink()

    extra_preview_files = []
    for i, group in enumerate(plan.get("extra_validating_groups", []), 1):
        label = public_group_label(plan["center"], group)
        center = group_center(group)
        auto_inventory = {
            "generated_by": "cuyum_bootstrap_world",
            "mode": "preview",
            "cell_id": f"auto_cell_{i:02d}",
            "label": label,
            "short_label": label,
            "role": "early_warning",
            "center": center,
            "sensors": [
                preview_sensor_entry(s, "anticipacion", True, True)
                for s in group
            ],
        }

        filename = PREVIEW_DIR / f"auto_cell_{i:02d}_inventory.preview.json"
        filename.write_text(
            json.dumps(auto_inventory, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        extra_preview_files.append(filename)

    summary = []
    summary.append("CUYUM bootstrap preview")
    summary.append("=" * 72)
    summary.append(f"Center: {plan['center']['label']} ({plan['center']['lat']}, {plan['center']['lon']})")
    summary.append(f"Coverage possible: {plan['coverage_possible']}")
    summary.append("")
    summary.append("Would write:")
    summary.append("- config/candidate_inventory.json")
    if extra_preview_files:
        for filename in extra_preview_files:
            summary.append(f"- {filename.name}")
    summary.append("")
    summary.append("Sensors:")
    for s in sensors:
        summary.append(
            f"- {s['rol']:<24} | {s['nombre']} | "
            f"{s['red']}.{s['estacion']}.{s['canal']} | "
            f"confirm={s['puede_confirmar']} trigger={s['puede_disparar']}"
        )

    (PREVIEW_DIR / "README.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

    return summary


def split_code(code):
    parts = str(code).split(".")
    network = parts[0] if len(parts) > 0 else ""
    station = parts[1] if len(parts) > 1 else ""
    channel = parts[2] if len(parts) > 2 else ""
    return network, station, channel


def preview_sensor_entry(sensor, role, can_confirm, can_trigger):
    network, station, channel = split_code(sensor["code"])
    return {
        "red": network,
        "estacion": station,
        "canal": channel,
        "nombre": sensor.get("name") or sensor["code"],
        "lat": sensor.get("lat"),
        "lon": sensor.get("lon"),
        "rol": role,
        "puede_confirmar": bool(can_confirm),
        "puede_disparar": bool(can_trigger),
        "distancia_km": sensor.get("distance_km"),
    }


def write_preview_files(plan):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    sensors = []

    for s in plan.get("local_validators", []):
        sensors.append(preview_sensor_entry(
            s,
            "anticipacion",
            True,
            True
        ))

    for s in plan.get("reserve_context", []):
        sensors.append(preview_sensor_entry(
            s,
            "anticipacion_secundaria",
            True,
            True
        ))

    for s in plan.get("regional_observers", []):
        sensors.append(preview_sensor_entry(
            s,
            "observador_regional",
            False,
            False
        ))

    candidate_inventory = {
        "generated_by": "cuyum_bootstrap_world",
        "mode": "preview",
        "center": plan["center"],
        "sensores": sensors,
    }

    (PREVIEW_DIR / "candidate_inventory.preview.json").write_text(
        json.dumps(candidate_inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    summary = []
    summary.append("CUYUM bootstrap preview")
    summary.append("=" * 72)
    summary.append(f"Center: {plan['center']['label']} ({plan['center']['lat']}, {plan['center']['lon']})")
    summary.append(f"Coverage possible: {plan['coverage_possible']}")
    summary.append("")
    summary.append("Would write:")
    summary.append("- config/candidate_inventory.json")
    summary.append("")
    summary.append("Sensors:")
    for s in sensors:
        summary.append(
            f"- {s['rol']:<24} | {s['nombre']} | "
            f"{s['red']}.{s['estacion']}.{s['canal']} | "
            f"confirm={s['puede_confirmar']} trigger={s['puede_disparar']}"
        )

    (PREVIEW_DIR / "README.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

    return summary


def apply_preview_to_config():
    source = PREVIEW_DIR / "candidate_inventory.preview.json"
    target = Path("config/candidate_inventory.json")

    if not source.exists():
        raise SystemExit("[error] preview not found. Run with --preview first.")

    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("config") / f"backups_bootstrap_apply_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if target.exists():
        backup = backup_dir / "candidate_inventory.json"
        backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

    data = json.loads(source.read_text(encoding="utf-8"))

    if not data.get("sensores") and "--force-empty-apply" not in sys.argv:
        raise SystemExit(
            "[error] preview has no sensors. Refusing to apply empty inventory. "
            "Use --force-empty-apply only if you intentionally want no coverage."
        )

    data["mode"] = "applied"
    data["applied_at"] = datetime.now().isoformat()

    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = []
    lines.append("CUYUM bootstrap apply")
    lines.append("=" * 72)
    lines.append(f"Source: {source}")
    lines.append(f"Target: {target}")
    lines.append(f"Backup: {backup_dir}")
    lines.append(f"Sensors written: {len(data.get('sensores', []))}")

    return lines


def group_excess_validators(candidates):
    candidates = sorted(
        candidates,
        key=lambda s: (
            s.get("distance_km", 999999),
            str(s.get("code", ""))
        )
    )

    groups = []
    used = set()

    for seed in candidates:
        if seed["code"] in used:
            continue

        group = []
        for s in candidates:
            if s["code"] in used:
                continue
            if km(seed, s) <= NEIGHBOR_RADIUS_KM:
                group.append(s)

        if len(group) >= MIN_VALIDATING_NEIGHBORS:
            group = sorted(
                group,
                key=lambda s: (
                    s.get("distance_km", 999999),
                    str(s.get("code", ""))
                )
            )[:LOCAL_TARGET_VALIDATORS]

            for s in group:
                used.add(s["code"])

            groups.append(group)

    leftovers = [s for s in candidates if s["code"] not in used]
    return groups, leftovers


def build_apply_plan(center, near, regional, groups):
    local_candidates = [
        s for s in near
        if s.get("can_confirm") or s.get("can_trigger")
    ]

    local_candidates = sorted(
        local_candidates,
        key=lambda s: (
            s.get("distance_km", 999999),
            str(s.get("code", ""))
        )
    )

    primary = local_candidates[:LOCAL_TARGET_VALIDATORS]
    used = {s["code"] for s in primary}

    regional_validator_candidates = [
        s for s in regional
        if s.get("can_confirm") or s.get("can_trigger")
    ]

    true_observers = [
        s for s in regional
        if not (s.get("can_confirm") or s.get("can_trigger"))
    ]

    excess_candidates = [
        s for s in (local_candidates[LOCAL_TARGET_VALIDATORS:] + regional_validator_candidates)
        if s["code"] not in used
    ]

    extra_groups, leftover_validators = group_excess_validators(excess_candidates)

    for g in extra_groups:
        for s in g:
            used.add(s["code"])

    reserve_context = [
        r for r in near
        if r["code"] not in used
        and not any(r["code"] == s["code"] for s in primary)
    ]

    reserve_context.extend(leftover_validators)

    observers = [
        r for r in true_observers
        if r["code"] not in used
    ]

    coverage_possible = len(primary) >= LOCAL_MIN_VALIDATORS

    plan = {
        "center": center,
        "coverage_possible": coverage_possible,
        "validating_groups_count": len(groups),
        "extra_validating_groups_count": len(extra_groups),
        "local_or_near_count": len(near),
        "regional_observer_count": len(observers),
        "actions": [],
        "local_validators": primary,
        "extra_validating_groups": extra_groups,
        "reserve_context": reserve_context,
        "regional_observers": observers,
    }

    if coverage_possible:
        plan["actions"].append({
            "action": "keep_or_create_candidate_inventory",
            "description": "Create local/control inventory with up to 4 validators, plus reserve/context sensors and observers."
        })

        if extra_groups:
            plan["actions"].append({
                "action": "create_extra_directional_cells",
                "description": "Create additional validating zones from unused neighboring sensors."
            })
        else:
            plan["actions"].append({
                "action": "no_extra_directional_cells",
                "description": "No unused neighboring validator group is available for another zone."
            })

        plan["actions"].append({
            "action": "evaluate_auto_cells",
            "description": "Create auto-cells only from separated non-overlapping groups."
        })
    else:
        plan["actions"].append({
            "action": "disable_validating_cells",
            "description": "Do not create validating cells because the current catalog has no usable validator group near this center."
        })
        plan["actions"].append({
            "action": "write_no_coverage_report",
            "description": "Keep public display honest: no coverage sufficient for validation with current known catalog."
        })

    return plan


def write_apply_plan(plan):
    PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = []
    center = plan["center"]
    lines.append("CUYUM bootstrap apply plan")
    lines.append("=" * 72)
    lines.append(f"Center: {center['label']} ({center['lat']}, {center['lon']})")
    lines.append(f"Coverage possible: {plan['coverage_possible']}")
    lines.append(f"Validating groups: {plan['validating_groups_count']}")
    lines.append(f"Local/near sensors: {plan['local_or_near_count']}")
    lines.append(f"Regional observers: {plan['regional_observer_count']}")
    lines.append("")
    lines.append("Planned actions:")
    for a in plan["actions"]:
        lines.append(f"- {a['action']}: {a['description']}")

    lines.append("")
    lines.append("Local validators:")
    if plan["local_validators"]:
        for s in plan["local_validators"]:
            lines.append(f"- {s['name']} | {s['code']} | {s['distance_km']} km")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Extra validating groups:")
    extra_groups = plan.get("extra_validating_groups", [])
    if extra_groups:
        for i, group in enumerate(extra_groups, 1):
            lines.append(f"- zone candidate {i}: {len(group)} sensors")
            for s in group:
                lines.append(f"  - {s['name']} | {s['code']} | {s['distance_km']} km")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Reserve/context:")
    if plan["reserve_context"]:
        for s in plan["reserve_context"]:
            lines.append(f"- {s['name']} | {s['code']} | {s['distance_km']} km")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Regional observers:")
    if plan["regional_observers"]:
        for s in plan["regional_observers"]:
            lines.append(f"- {s['name']} | {s['code']} | {s['distance_km']} km")
    else:
        lines.append("- none")

    PLAN_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def parse_args():
    parser = argparse.ArgumentParser(description="Cuyum bootstrap by geographic center")
    parser.add_argument("--lat", type=float, help="system center latitude")
    parser.add_argument("--lon", type=float, help="system center longitude")
    parser.add_argument("--label", default=None, help="system center label")
    parser.add_argument("--preview", action="store_true", help="write preview files only")
    parser.add_argument("--plan", action="store_true", help="write apply plan")
    parser.add_argument("--apply", action="store_true", help="apply preview to config/candidate_inventory.json")
    parser.add_argument("--force-empty-apply", action="store_true", help="allow applying an empty/no-coverage inventory")
    return parser.parse_args()


def resolve_center(args):
    if args.lat is not None or args.lon is not None:
        if args.lat is None or args.lon is None:
            raise SystemExit("[error] use --lat and --lon together")
        return {
            "label": args.label or "Local",
            "lat": float(args.lat),
            "lon": float(args.lon),
        }
    return normalize_center(load_json(CENTER_FILE))


def main():
    args = parse_args()
    center = resolve_center(args)

    by_code = {}
    for path in CATALOG_FILES:
        data = load_json(path)
        if data is not None:
            collect(data, str(path), by_code)

    sensors = list(by_code.values())
    rows = classify(center, sensors)
    groups = neighbor_groups(rows)

    near = [r for r in rows if r["candidate_class"] == "local_or_near"]
    regional = [r for r in rows if r["candidate_class"] == "regional_observer"]
    out = [r for r in rows if r["candidate_class"] == "out_of_range"]

    plan = build_apply_plan(center, near, regional, groups)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "center": center,
        "policy": {
            "local_radius_km": LOCAL_RADIUS_KM,
            "regional_radius_km": REGIONAL_RADIUS_KM,
            "neighbor_radius_km": NEIGHBOR_RADIUS_KM,
            "min_validating_neighbors": MIN_VALIDATING_NEIGHBORS,
        },
        "known_positioned_sensors": len(sensors),
        "local_or_near": near,
        "regional_observers": regional,
        "out_of_range_count": len(out),
        "neighbor_groups": groups,
        "coverage_summary": {
            "validating_groups": len(groups),
            "local_or_near_count": len(near),
            "regional_observer_count": len(regional),
            "coverage_possible": len(groups) > 0,
        },
    }

    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = []
    lines.append("CUYUM bootstrap world report")
    lines.append("=" * 72)
    lines.append(f"Center: {center['label']} ({center['lat']}, {center['lon']})")
    lines.append(f"Known positioned sensors: {len(sensors)}")
    lines.append(f"Local/near sensors <= {LOCAL_RADIUS_KM} km: {len(near)}")
    lines.append(f"Regional observers <= {REGIONAL_RADIUS_KM} km: {len(regional)}")
    lines.append(f"Validating neighbor groups: {len(groups)}")
    lines.append("")
    lines.append("Nearest sensors:")
    for r in rows[:30]:
        lines.append(
            f"- {r['distance_km']:7.1f} km | {r['candidate_class']:<18} | "
            f"{r['name']} | {r['code']} | {r['source']}"
        )

    lines.append("")
    lines.append("Neighbor groups:")
    if not groups:
        lines.append("- none")
    else:
        for i, g in enumerate(groups, 1):
            lines.append(f"- group {i}: {len(g)} sensors")
            for s in g:
                lines.append(f"  - {s['distance_km']:7.1f} km | {s['name']} | {s['code']}")

    lines.append("")
    lines.append("Recommendation:")
    if plan.get("coverage_possible"):
        primary = plan.get("local_validators", [])
        extra_groups = plan.get("extra_validating_groups", [])
        reserve = plan.get("reserve_context", [])
        observers = plan.get("regional_observers", [])

        lines.append(f"- Create/keep local/control inventory with {len(primary)} validating sensors.")
        for s in primary:
            lines.append(f"  - validator: {s['name']} | {s['code']}")

        if extra_groups:
            lines.append(f"- Create {len(extra_groups)} extra directional validating zone(s) from unused sensors.")
            for i, group in enumerate(extra_groups, 1):
                lines.append(f"  - extra zone {i}: {len(group)} sensors")
                for s in group:
                    lines.append(f"    - validator: {s['name']} | {s['code']}")
        else:
            lines.append("- No extra directional validating zones available from unused sensors.")

        if reserve:
            lines.append(f"- Keep {len(reserve)} nearby sensors as reserve/context.")
            for s in reserve:
                lines.append(f"  - reserve/context: {s['name']} | {s['code']}")

        if observers:
            lines.append(f"- Keep {len(observers)} regional observers.")
            for s in observers:
                lines.append(f"  - observer: {s['name']} | {s['code']}")

        lines.append("- Coverage is possible with current known catalog.")
    else:
        lines.append("- Do not create validating cells for this center.")
        lines.append("- Coverage is not supported by current known catalog.")
        lines.append("- More global SeedLink station metadata is needed.")

    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print()
    print(f"Written: {OUT_TXT}")
    print(f"Written: {OUT_JSON}")

    if args.plan:
        plan_lines = write_apply_plan(plan)
        print()
        print("\n".join(plan_lines))
        print()
        print(f"Written: {PLAN_TXT}")
        print(f"Written: {PLAN_JSON}")

    if args.preview:
        preview_lines = write_preview_files(plan)
        print()
        print("\n".join(preview_lines))
        print()
        print(f"Written: {PREVIEW_DIR / 'README.txt'}")
        print(f"Written: {PREVIEW_DIR / 'candidate_inventory.preview.json'}")

    if args.apply:
        if not args.preview:
            write_preview_files(plan)
        apply_lines = apply_preview_to_config()
        print()
        print("\n".join(apply_lines))

if __name__ == "__main__":
    main()
