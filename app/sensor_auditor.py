import json
import os
import time
import retention_cleaner
import event_journal
from datetime import datetime, timezone

CONFIG_FILE = "config_cuyum.json"
STATE_FILE = "runtime/state_cell_00_seedlink.json"
INVENTORY_FILE = "config/candidate_inventory.json"
CATALOG_FILE = "config/sensor_catalog.json"
AUDIT_FILE = "runtime/audit_recent.jsonl"
DEFAULT_INTERVAL_SECONDS = 60


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"WARN could not read {path}: {exc}", flush=True)
        return default


def atomic_write_json(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def append_jsonl(path, item):
    item = dict(item)
    item.setdefault("timestamp", now_iso())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def sensor_key_from_parts(network, station, channel):
    return f"{network}.{station}.{channel}"


def inventory_map(inventory):
    result = {}
    for sensor in (inventory or {}).get("sensors", []):
        try:
            key = sensor_key_from_parts(
                sensor["network"],
                sensor["station"],
                sensor["channel"],
            )
            result[key] = sensor
        except KeyError:
            continue
    return result


def first_zone_from_state(state):
    zone = (
        (state or {})
        .get("zones", {})
        .get("local_adaptive_zone", {})
    )
    return "cell_00", "local_adaptive_zone", zone


def latency_score(latency):
    if latency is None:
        return 0.5
    try:
        latency = float(latency)
    except Exception:
        return 0.5
    if latency <= 5:
        return 1.0
    if latency <= 10:
        return 0.8
    if latency <= 20:
        return 0.6
    if latency <= 30:
        return 0.4
    return 0.2


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def confidence_state(entry, scoring):
    revisions = entry.get("revisions_total", 0)
    if revisions < scoring.get("candidate_min_revisions", 3):
        return "candidate"

    score = entry.get("score_selection", 0.5)
    if score >= 0.85:
        return "preferred"
    if score >= 0.70:
        return "reliable"
    if score >= 0.50:
        return "observed"
    if score >= 0.35:
        return "low_score"
    return "suspicious"


def recalc_scores(entry, scoring):
    total = max(1, entry.get("revisions_total", 0))
    alive = entry.get("revisions_alive", 0)
    entry["score_service"] = round(clamp(alive / total), 3)

    entry["score_latency"] = round(latency_score(entry.get("latency_last_seconds")), 3)

    flags_total = entry.get("flags_total", 0)
    if flags_total <= 0:
        entry["score_credibility"] = round(scoring.get("initial_credibility", 0.5), 3)
    else:
        confirmed = entry.get("flags_confirmed_by_cell", 0)
        with_peer = entry.get("flags_with_peer", 0)
        solo = entry.get("flags_solo", 0)
        credibility = (
            0.50
            + 0.35 * (confirmed / flags_total)
            + 0.15 * (with_peer / flags_total)
            - 0.30 * (solo / flags_total)
        )
        entry["score_credibility"] = round(clamp(credibility), 3)

    sw = scoring.get("service_weight", 0.4)
    lw = scoring.get("latency_weight", 0.3)
    cw = scoring.get("credibility_weight", 0.3)
    total_weight = sw + lw + cw
    if total_weight <= 0:
        sw, lw, cw, total_weight = 0.4, 0.3, 0.3, 1.0

    selection = (
        sw * entry["score_service"]
        + lw * entry["score_latency"]
        + cw * entry["score_credibility"]
    ) / total_weight
    entry["score_selection"] = round(clamp(selection), 3)
    entry["confidence_state"] = confidence_state(entry, scoring)


def base_entry(key, inv=None, current=None, cell_id="cell_00"):
    inv = inv or {}
    current = current or {}

    return {
        "sensor_id": key,
        "network": current.get("network", inv.get("network")),
        "station": current.get("station", inv.get("station")),
        "channel": current.get("channel", inv.get("channel")),
        "trace_id_last": current.get("trace_id"),
        "name": current.get("name", inv.get("name")),
        "role": current.get("role", inv.get("role")),
        "distance_km": current.get("distance_km", inv.get("distance_km")),
        "cells": {cell_id: "active"},
        "operational_state": "unknown",
        "confidence_state": "candidate",
        "first_seen_at": now_iso(),
        "last_seen_at": None,
        "last_counted_update": None,
        "revisions_total": 0,
        "revisions_alive": 0,
        "revisions_down": 0,
        "packets_total_observed": 0,
        "latency_last_seconds": None,
        "latency_average_seconds": None,
        "latency_max_seconds": None,
        "flags_total": 0,
        "flags_solo": 0,
        "flags_with_peer": 0,
        "flags_confirmed_by_cell": 0,
        "last_flag_event_key": None,
        "score_service": 0.5,
        "score_latency": 0.5,
        "score_credibility": 0.5,
        "score_selection": 0.5,
        "can_trigger": bool(current.get("can_trigger", inv.get("can_trigger", False))),
        "can_confirm": bool(current.get("can_confirm", inv.get("can_confirm", True))),
        "autoexpansion_use": "active",
        "notes": []
    }


def update_latency(entry, latency):
    if latency is None:
        return
    try:
        latency = round(float(latency), 1)
    except Exception:
        return
    old_avg = entry.get("latency_average_seconds")
    n = max(1, entry.get("revisions_alive", 1))
    if old_avg is None:
        entry["latency_average_seconds"] = latency
    else:
        entry["latency_average_seconds"] = round(((float(old_avg) * (n - 1)) + latency) / n, 2)
    entry["latency_last_seconds"] = latency
    old_max = entry.get("latency_max_seconds")
    entry["latency_max_seconds"] = latency if old_max is None else max(float(old_max), latency)


def judge_flags(zone, catalog, cell_id):
    flags = zone.get("recent_flags", {}) or {}
    active_flags = list(flags.values())
    total_flags = len(active_flags)

    for flag in active_flags:
        key = flag.get("sensor_id")
        if not key or key not in catalog["sensors"]:
            continue
        event_key = f"{key}|{flag.get('timestamp')}|{flag.get('updated_at')}"
        entry = catalog["sensors"][key]
        if entry.get("last_flag_event_key") == event_key:
            continue

        companions = max(0, total_flags - 1)
        entry["flags_total"] = entry.get("flags_total", 0) + 1
        if companions >= 2:
            judgement = "confirmed_by_cell"
            entry["flags_confirmed_by_cell"] = entry.get("flags_confirmed_by_cell", 0) + 1
        elif companions == 1:
            judgement = "with_peer"
            entry["flags_with_peer"] = entry.get("flags_with_peer", 0) + 1
        else:
            judgement = "solo"
            entry["flags_solo"] = entry.get("flags_solo", 0) + 1

        entry["last_flag_event_key"] = event_key
        event_item = {
            "type": "sensor_flag_judgement",
            "cell_id": cell_id,
            "sensor_id": key,
            "station": flag.get("station"),
            "ratio": flag.get("ratio"),
            "magnitude_experimental": flag.get("estimated_magnitude"),
            "companions": companions,
            "judgement": judgement
        }
        append_jsonl(AUDIT_FILE, event_item)
        event_journal.record_sensor_judgement(
            cell_id=cell_id,
            sensor_id=key,
            station=flag.get("station"),
            ratio=flag.get("ratio"),
            companions=companions,
            judgement=judgement,
            magnitude_experimental=flag.get("estimated_magnitude"),
        )


def audit_once():
    config = read_json(CONFIG_FILE, default={}) or {}
    scoring = config.get("scoring", {})
    state = read_json(STATE_FILE, default={}) or {}
    inventory = read_json(INVENTORY_FILE, default={}) or {}
    catalog = read_json(CATALOG_FILE, default={
        "version": 1,
        "project": "Cuyum",
        "updated_at": None,
        "sensors": {}
    }) or {"version": 1, "project": "Cuyum", "updated_at": None, "sensors": {}}

    catalog.setdefault("version", 1)
    catalog.setdefault("project", "Cuyum")
    catalog.setdefault("sensors", {})

    inv_map = inventory_map(inventory)
    cell_id, zone_key, zone = first_zone_from_state(state)
    current_sensors = zone.get("sensors", {}) or {}

    all_keys = set(inv_map.keys()) | set(current_sensors.keys())
    changed_states = []

    for key in sorted(all_keys):
        inv = inv_map.get(key, {})
        current = current_sensors.get(key, {})
        sensors = catalog["sensors"]
        if key not in sensors:
            sensors[key] = base_entry(key, inv=inv, current=current, cell_id=cell_id)
            append_jsonl(AUDIT_FILE, {
                "type": "sensor_registered",
                "cell_id": cell_id,
                "sensor_id": key,
                "name": sensors[key].get("name"),
                "role": sensors[key].get("role")
            })

        entry = sensors[key]
        entry.setdefault("cells", {})[cell_id] = "active" if current else "inventory"
        entry["network"] = current.get("network", inv.get("network", entry.get("network")))
        entry["station"] = current.get("station", inv.get("station", entry.get("station")))
        entry["channel"] = current.get("channel", inv.get("channel", entry.get("channel")))
        entry["trace_id_last"] = current.get("trace_id", entry.get("trace_id_last"))
        entry["name"] = current.get("name", inv.get("name", entry.get("name")))
        entry["role"] = current.get("role", inv.get("role", entry.get("role")))
        entry["distance_km"] = current.get("distance_km", inv.get("distance_km", entry.get("distance_km")))
        entry["can_trigger"] = bool(current.get("can_trigger", inv.get("can_trigger", entry.get("can_trigger", False))))
        entry["can_confirm"] = bool(current.get("can_confirm", inv.get("can_confirm", entry.get("can_confirm", True))))

        update_marker = current.get("updated_at")
        sensor_state = current.get("sensor_state") or inv.get("availability_state", "unknown")
        previous_state = entry.get("operational_state")
        entry["operational_state"] = sensor_state

        if update_marker and entry.get("last_counted_update") != update_marker:
            entry["last_counted_update"] = update_marker
            entry["last_seen_at"] = update_marker
            entry["revisions_total"] = entry.get("revisions_total", 0) + 1

            alive_states = {"active", "alive", "calibrating"}
            if sensor_state in alive_states:
                entry["revisions_alive"] = entry.get("revisions_alive", 0) + 1
            else:
                entry["revisions_down"] = entry.get("revisions_down", 0) + 1

            packets = inv.get("packets_last_revision")
            if isinstance(packets, int):
                entry["packets_total_observed"] = entry.get("packets_total_observed", 0) + packets

            update_latency(entry, current.get("latency_seconds", inv.get("approx_latency_seconds")))

        if previous_state != sensor_state:
            changed_states.append((key, previous_state, sensor_state))
            append_jsonl(AUDIT_FILE, {
                "type": "sensor_state_change",
                "cell_id": cell_id,
                "sensor_id": key,
                "from": previous_state,
                "to": sensor_state
            })
            event_journal.record_sensor_state_change(cell_id, key, previous_state, sensor_state)

    judge_flags(zone, catalog, cell_id)

    for entry in catalog["sensors"].values():
        recalc_scores(entry, scoring)

    catalog["updated_at"] = now_iso()
    catalog["source_state_file"] = STATE_FILE
    catalog["source_inventory_file"] = INVENTORY_FILE
    catalog["cell_observed"] = cell_id
    catalog["zone_key"] = zone_key

    atomic_write_json(CATALOG_FILE, catalog)
    print(f"Auditor updated: {len(catalog['sensors'])} sensors | state_changes={len(changed_states)}", flush=True)


def main():
    interval = DEFAULT_INTERVAL_SECONDS
    print("Cuyum sensor auditor started", flush=True)
    next_retention_run = 0
    while True:
        try:
            audit_once()
            now = time.time()
            if now >= next_retention_run:
                retention_cleaner.main()
                next_retention_run = now + 86400
        except KeyboardInterrupt:
            print("Auditor stopped manually", flush=True)
            return
        except Exception as exc:
            print(f"ERROR auditor: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
