import json
import os
from datetime import datetime, timezone, timedelta

CONFIG_FILE = "config_cuyum.json"
EVENTS_FILE = "runtime/events_recent.jsonl"
AUDIT_FILE = "runtime/audit_recent.jsonl"
STATE_FILE = "runtime/event_journal_state.json"
SENSOR_GEO_OVERRIDES_FILE = "config/sensor_geo_overrides.json"
LOCAL_STATE_FILE = "runtime/state_cell_00_seedlink.json"
AUTO_CELL_01_STATE_FILE = "runtime/auto_cell_01_state.json"
DEFAULT_RETENTION_DAYS = 31
DEFAULT_MAX_LINES = 5000


IMPORTANT_AUDIT_TYPES = {"sensor_flag_judgement"}


def now_utc():
    return datetime.now(timezone.utc)


def now_iso():
    return now_utc().isoformat()


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json_atomic(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def parse_time(value):
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def read_config():
    data = read_json(CONFIG_FILE, {}) or {}
    retention = data.get("retention", {}) if isinstance(data, dict) else {}
    return {
        "events_days": int(retention.get("events_days", DEFAULT_RETENTION_DAYS)),
        "max_events_lines": int(retention.get("max_events_lines", DEFAULT_MAX_LINES)),
    }


def _line_timestamp(item):
    return parse_time(item.get("timestamp") or item.get("updated_at"))


def trim_jsonl(path=EVENTS_FILE, days=None, max_lines=None):
    cfg = read_config()
    days = int(days if days is not None else cfg["events_days"])
    max_lines = int(max_lines if max_lines is not None else cfg["max_events_lines"])
    if not os.path.exists(path):
        return {"kept": 0, "total": 0}

    cutoff = now_utc() - timedelta(days=days)
    kept = []
    total = 0
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            total += 1
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            ts = _line_timestamp(item)
            if ts is None or ts < cutoff:
                continue
            kept.append(json.dumps(item, ensure_ascii=False))

    if max_lines > 0 and len(kept) > max_lines:
        kept = kept[-max_lines:]

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
    os.replace(tmp, path)
    return {"kept": len(kept), "total": total}


def append_event(event, dedupe_key=None, min_interval_seconds=0):
    """Append a significant Cuyum event with retention and lightweight de-duplication."""
    if not isinstance(event, dict):
        return False
    item = dict(event)
    item.setdefault("timestamp", now_iso())
    item.setdefault("source", "cuyum")
    item = _enrich_sensor_event(item)

    state = read_json(STATE_FILE, {}) or {}
    recent = state.setdefault("recent", {})
    key = dedupe_key or item.get("dedupe_key")
    if key:
        previous = recent.get(key, {})
        previous_ts = parse_time(previous.get("timestamp"))
        fingerprint = item.get("fingerprint")
        same_fingerprint = fingerprint is not None and previous.get("fingerprint") == fingerprint
        if previous_ts and min_interval_seconds > 0:
            elapsed = (now_utc() - previous_ts).total_seconds()
            if same_fingerprint and elapsed < min_interval_seconds:
                return False
        elif same_fingerprint:
            return False
        recent[key] = {
            "timestamp": item["timestamp"],
            "fingerprint": fingerprint,
        }
        # Prevent internal state from growing indefinitely.
        if len(recent) > 300:
            ordered = sorted(recent.items(), key=lambda kv: kv[1].get("timestamp", ""))[-200:]
            state["recent"] = dict(ordered)

    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

    write_json_atomic(STATE_FILE, state)
    trim_jsonl(EVENTS_FILE)
    return True


def _safe_cell_label(cell_id):
    if cell_id in ("cell_00", "cell_01"):
        return "Local"
    if cell_id == "cell_00":
        return "Local"
    return cell_id or "Zone"



def _as_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _sensor_key(network=None, station=None, channel=None, code=None, key=None):
    if key:
        return str(key)
    if code:
        return str(code)

    parts = [network, station, channel]
    if all(parts):
        return f"{network}.{station}.{channel}"

    return ""


def _sensor_geo_overrides():
    data = read_json(SENSOR_GEO_OVERRIDES_FILE, {}) or {}
    sensors = data.get("sensors", {}) if isinstance(data, dict) else {}
    out = {}

    for key, value in sensors.items():
        lat = _as_float(value.get("lat"), None)
        lon = _as_float(value.get("lon"), None)
        name = value.get("name") or key
        locality = value.get("locality") or name
        source = value.get("source") or "sensor_geo_overrides"

        item = {
            "id": str(key),
            "name": name,
            "locality": locality,
            "location_source": source,
            "approx_location": bool(value.get("approx_location", True)),
        }

        if lat is not None and lon is not None:
            item["lat"] = lat
            item["lon"] = lon

        out[str(key)] = item

    return out


def _runtime_sensor_locations():
    import glob

    out = {}

    for inv_path in sorted(glob.glob("config/auto_cell_*_inventory.json")):
        inventory = read_json(inv_path, {}) or {}
        cell_id = inventory.get("cell_id")

        for sensor in inventory.get("sensors", []) or []:
            key = _sensor_key(
                sensor.get("network"),
                sensor.get("station"),
                sensor.get("channel"),
            )
            if not key:
                continue

            name = sensor.get("name") or sensor.get("site") or key
            lat = _as_float(sensor.get("lat"), None)
            lon = _as_float(sensor.get("lon"), None)

            meta = {
                "id": key,
                "name": name,
                "locality": sensor.get("locality") or name,
                "cell_id": cell_id,
                "location_source": "auto_cell_inventory",
                "approx_location": bool(sensor.get("approx_location", False)),
                "provider": sensor.get("provider") or inventory.get("server_name"),
            }

            if lat is not None and lon is not None:
                meta["lat"] = lat
                meta["lon"] = lon

            out[key] = meta

    return out


def _live_sensor_names():
    import glob

    out = {}

    local_state = read_json(LOCAL_STATE_FILE, {}) or {}
    local_zone = (
        (local_state.get("zones") or {})
        .get("local_adaptive_zone", {})
    )

    for key, sensor in (local_zone.get("sensors") or {}).items():
        sensor_id = sensor.get("sensor_id") or sensor.get("key") or key
        out[sensor_id] = {
            "id": sensor_id,
            "station": sensor.get("station"),
            "name": sensor.get("name") or sensor_id,
            "locality": sensor.get("locality") or sensor.get("name") or sensor_id,
            "cell_id": "cell_00",
            "state": sensor.get("sensor_state"),
            "latency_seconds": _as_float(sensor.get("latency_seconds"), None),
        }

    for state_path in sorted(glob.glob("runtime/auto_cell_*_state.json")):
        auto_state = read_json(state_path, {}) or {}
        cell_id = auto_state.get("cell_id")

        for key, sensor in (auto_state.get("sensors") or {}).items():
            sensor_id = sensor.get("sensor_id") or sensor.get("key") or key
            out[sensor_id] = {
                "id": sensor_id,
                "station": sensor.get("station"),
                "name": sensor.get("name") or sensor_id,
                "locality": sensor.get("locality") or sensor.get("name") or sensor_id,
                "cell_id": cell_id,
                "state": sensor.get("sensor_state"),
                "latency_seconds": _as_float(sensor.get("latency_seconds"), None),
            }

    return out


def _sensor_metadata(sensor_id=None, station=None):
    if not sensor_id and not station:
        return None
    candidates = []
    if sensor_id:
        candidates.append(str(sensor_id))
    if station:
        st = str(station)
        candidates.extend([k for k in _sensor_geo_overrides().keys() if f".{st}." in k])

    combined = {}
    # Priority: live names, runtime locations, then visual overrides to complete missing coordinates.
    for source in (_live_sensor_names(), _runtime_sensor_locations(), _sensor_geo_overrides()):
        for key in candidates:
            if key in source:
                combined.update({k: v for k, v in source[key].items() if v is not None})
    if not combined:
        return None
    combined.setdefault("id", sensor_id or station)
    combined.setdefault("name", combined.get("id"))
    combined.setdefault("locality", combined.get("name"))
    return combined


def _enrich_sensor_event(event):
    if not isinstance(event, dict):
        return event
    sid = event.get("sensor_id")
    station = event.get("station")
    meta = _sensor_metadata(sid, station)
    if not meta:
        return event

    sensor_info = {
        "id": sid or meta.get("id"),
        "station": station or event.get("station"),
        "name": meta.get("name"),
        "locality": meta.get("locality"),
        "lat": meta.get("lat"),
        "lon": meta.get("lon"),
        "location_source": meta.get("location_source"),
        "approx_location": bool(meta.get("approx_location", False)),
    }
    # Remove null values to keep the JSON compact and readable.
    sensor_info = {k: v for k, v in sensor_info.items() if v is not None}
    event.setdefault("sensor", sensor_info)

    # Flat fields keep simple consumers easy to use.
    event.setdefault("sensor_name", meta.get("name"))
    event.setdefault("locality", meta.get("locality"))
    if meta.get("lat") is not None and meta.get("lon") is not None:
        event.setdefault("lat", meta.get("lat"))
        event.setdefault("lon", meta.get("lon"))
        event.setdefault("location_source", meta.get("location_source"))
        event.setdefault("approx_location", bool(meta.get("approx_location", False)))
    if meta.get("cell_id") and not event.get("cell_id"):
        event["cell_id"] = meta.get("cell_id")
        event["cell_label"] = _safe_cell_label(meta.get("cell_id"))
    return event


def record_sensor_judgement(cell_id, sensor_id, station=None, ratio=None, companions=0,
                            judgement=None, magnitude_experimental=None):
    try:
        ratio_value = float(ratio)
    except Exception:
        ratio_value = None
    companions_int = int(companions or 0)
    judgement_text = str(judgement or "").strip()

    if ratio_value is None:
        return False
    if ratio_value < 2.5 and companions_int <= 0:
        return False

    if judgement_text == "confirmed_by_cell" or companions_int >= 2:
        public_level = "watch"
        summary = "coincident signal within one cell"
        throttle = 180
    elif judgement_text == "with_peer" or companions_int == 1:
        public_level = "shared_signal"
        summary = "shared signal from nearby sensors"
        throttle = 300
    else:
        public_level = "isolated_signal"
        summary = "isolated signal without confirmation"
        throttle = 900

    rounded_ratio = round(ratio_value, 2)
    event = {
        "type": "sensor_signal",
        "public_level": public_level,
        "summary": summary,
        "cell_id": cell_id,
        "cell_label": _safe_cell_label(cell_id),
        "sensor_id": sensor_id,
        "station": station,
        "ratio_max": rounded_ratio,
        "companions": companions_int,
        "judgement": judgement_text,
        "sound": False,
    }
    if magnitude_experimental is not None:
        event["magnitude_experimental_internal"] = magnitude_experimental
    event["fingerprint"] = f"{public_level}|{companions_int}|{int(rounded_ratio)}"
    return append_event(
        event,
        dedupe_key=f"sensor_signal:{cell_id}:{sensor_id}:{public_level}",
        min_interval_seconds=throttle,
    )



def record_sensor_state_change(cell_id, sensor_id, from_state, to_state):
    """Publish only meaningful sensor loss and recovery transitions."""
    from_text = str(from_state or "unknown").lower()
    to_text = str(to_state or "unknown").lower()

    if from_text == to_text:
        return False

    unavailable_states = {
        "down",
        "no_data",
        "offline",
        "unavailable",
    }

    from_unavailable = from_text in unavailable_states
    to_unavailable = to_text in unavailable_states

    if not (from_unavailable or to_unavailable):
        return False

    event = {
        "type": "sensor_availability",
        "public_level": "availability",
        "summary": "sensor without data" if to_unavailable else "sensor recovered",
        "cell_id": cell_id,
        "cell_label": _safe_cell_label(cell_id),
        "sensor_id": sensor_id,
        "from": str(from_state or "unknown"),
        "to": str(to_state or "unknown"),
        "sound": False,
        "fingerprint": f"{from_text}->{to_text}",
    }

    return append_event(
        event,
        dedupe_key=f"sensor_availability:{cell_id}:{sensor_id}",
        min_interval_seconds=900,
    )


def record_fused_snapshot(fused):
    """Record significant system decisions, not routine live-state snapshots."""
    if not isinstance(fused, dict):
        return False

    network = fused.get("network", {}) or {}
    event = fused.get("event", {}) or {}
    display = fused.get("display", {}) or {}

    level = str(event.get("level", "normal") or "normal").lower()
    sound = bool(event.get("sound", False))
    cells_active = network.get("cells_active")
    sensors_active = network.get("sensors_active")
    buzzer_seconds = event.get("buzzer_seconds", 0)

    # Normal observation and routine coverage changes are live state,
    # not public historical events.
    if level in ("normal", "observation") and not sound:
        return False

    return append_event({
        "type": "system_decision",
        "public_level": "warning" if sound else "watch",
        "summary": display.get("message") or event.get("message") or "Cuyum decision",
        "event_level": level,
        "sound": sound,
        "buzzer_seconds": buzzer_seconds,
        "cells_active": cells_active,
        "sensors_active": sensors_active,
        "fingerprint": f"{level}|{sound}|{buzzer_seconds}",
    }, dedupe_key="system_decision", min_interval_seconds=60)


def _iter_jsonl(path, limit=1000):
    if not os.path.exists(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items[-limit:]


def _audit_to_public(item):
    """Convert internal audit records into public events while filtering noise."""
    if item.get("type") != "sensor_flag_judgement":
        return None

    ratio = _as_float(item.get("ratio"), None)
    if ratio is None:
        return None
    companions = int(item.get("companions") or 0)
    judgement = item.get("judgement")

    # Filtro de importancia:
    # - cell coincidence: always relevant;
    # - shared signal: relevant only above a moderate threshold;
    # - isolated signal: relevant only when clearly strong.
    if judgement == "confirmed_by_cell" or companions >= 2:
        level = "watch"
        summary = "coincident signal within one cell"
    elif judgement == "with_peer" or companions == 1:
        if ratio < 3.0:
            return None
        level = "shared_signal"
        summary = "shared signal from nearby sensors"
    else:
        if ratio < 6.0:
            return None
        level = "isolated_signal"
        summary = "intense isolated signal"

    return {
        "type": "sensor_signal",
        "source": "audit_recent",
        "timestamp": item.get("timestamp"),
        "public_level": level,
        "summary": summary,
        "cell_id": item.get("cell_id"),
        "cell_label": _safe_cell_label(item.get("cell_id")),
        "sensor_id": item.get("sensor_id"),
        "station": item.get("station"),
        "ratio_max": round(ratio, 2),
        "companions": companions,
        "judgement": judgement,
        "sound": False,
    }


def _compact_event(item):
    """Compact public output: enough for traceability without duplication."""
    item = _enrich_sensor_event(dict(item))
    sensor = item.get("sensor") or {}
    cell_id = item.get("cell_id")
    cell_label = item.get("cell_label") or _safe_cell_label(cell_id)

    out = {
        "timestamp": item.get("timestamp"),
        "type": item.get("type"),
        "level": item.get("public_level") or item.get("event_level") or "event",
        "summary": item.get("summary") or item.get("message") or "Cuyum event",
        "sound": bool(item.get("sound", False)),
    }

    if cell_id or cell_label:
        out["cell"] = {"id": cell_id, "label": cell_label}

    if item.get("type") in ("sensor_signal", "sensor_availability") or sensor:
        lat = sensor.get("lat") if sensor.get("lat") is not None else item.get("lat")
        lon = sensor.get("lon") if sensor.get("lon") is not None else item.get("lon")
        sensor_obj = {
            "id": sensor.get("id") or item.get("sensor_id"),
            "name": sensor.get("name") or item.get("sensor_name"),
            "station": sensor.get("station") or item.get("station"),
            "locality": sensor.get("locality") or item.get("locality"),
        }
        if lat is not None and lon is not None:
            sensor_obj["coords"] = {
                "lat": lat,
                "lon": lon,
            }
        location = {
            "approx": bool(sensor.get("approx_location", item.get("approx_location", False))),
            "source": sensor.get("location_source") or item.get("location_source"),
        }
        location = {k: v for k, v in location.items() if v is not None and v != ""}
        if location:
            sensor_obj["location"] = location
        sensor_obj = {k: v for k, v in sensor_obj.items() if v is not None and v != ""}
        if sensor_obj:
            out["sensor"] = sensor_obj

    if item.get("type") == "sensor_signal":
        signal = {
            "ratio_max": item.get("ratio_max"),
            "companions": item.get("companions"),
            "judgement": item.get("judgement"),
        }
        signal = {k: v for k, v in signal.items() if v is not None and v != ""}
        if signal:
            out["signal"] = signal

    if item.get("type") == "system_decision":
        out["system"] = {
            "event_level": item.get("event_level"),
            "cells_active": item.get("cells_active"),
            "sensors_active": item.get("sensors_active"),
            "buzzer_seconds": item.get("buzzer_seconds", 0),
        }
        out["system"] = {k: v for k, v in out["system"].items() if v is not None}

    return out


def _is_publicly_relevant(item):
    t = item.get("type")
    if t == "sensor_signal":
        level = item.get("public_level")
        ratio = _as_float(item.get("ratio_max"), None)
        companions = int(item.get("companions") or 0)
        if level == "watch" or companions >= 2:
            return True
        if level == "shared_signal" and (ratio is None or ratio >= 3.0):
            return True
        if level == "isolated_signal" and ratio is not None and ratio >= 6.0:
            return True
        return False
    if t == "system_decision":
        return True
    if t == "sensor_availability":
        return True
    # Network/cell snapshots, calibration, and latency are live state or internal audit.
    return False


def build_public_events(limit=100, include_audit=True):
    trim_jsonl(EVENTS_FILE)
    limit = max(1, min(int(limit or 100), 300))

    events = [x for x in _iter_jsonl(EVENTS_FILE, limit=limit * 4) if _is_publicly_relevant(x)]
    if include_audit:
        audit = [_audit_to_public(x) for x in _iter_jsonl(AUDIT_FILE, limit=limit * 6) if x.get("type") in IMPORTANT_AUDIT_TYPES]
        events.extend([x for x in audit if x])

    def sort_key(item):
        return parse_time(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)

    events = sorted(events, key=sort_key, reverse=True)

    unique = []
    seen = set()
    recent_by_signal = {}
    for e in events:
        dt = parse_time(e.get("timestamp"))
        # Prevent a sustained signal from the same sensor from filling the public output.
        if e.get("type") == "sensor_signal" and dt:
            bucket_key = (e.get("type"), e.get("sensor_id"), e.get("public_level"))
            previous = recent_by_signal.get(bucket_key)
            if previous and abs((previous - dt).total_seconds()) < 900:
                continue
            recent_by_signal[bucket_key] = dt

        sig = (e.get("timestamp"), e.get("type"), e.get("sensor_id"), e.get("cell_id"), e.get("public_level"))
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(_compact_event(e))
        if len(unique) >= limit:
            break

    cfg = read_config()
    return {
        "sistema": "Cuyum",
        "modo": "public_events_v2_compacto",
        "updated_at": now_iso(),
        "retention_days": cfg["events_days"],
        "max_events_lines": cfg["max_events_lines"],
        "count": len(unique),
        "description": "Recent significant records. Full live state is in /api/public/live.",
        "filters": {
            "sensor_signal": "zone coincidences, shared signals, or intense isolated signals",
            "system_decision": "non-normal public decisions made by Cuyum",
            "coverage_noise": "calibration, latency, and normal snapshots are not published here"
        },
        "events": unique,
    }
