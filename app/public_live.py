import json
import os
from datetime import datetime, timezone

from multicell_fusion import build_multicell_state
import event_journal

LOCAL_STATE_FILE = "runtime/state_cell_00_seedlink.json"
AUTO_CELL_01_STATE_FILE = "runtime/auto_cell_01_state.json"
SENSOR_CATALOG_FILE = "config/sensor_catalog.json"
SENSOR_GEO_OVERRIDES_FILE = "config/sensor_geo_overrides.json"
SYSTEM_CENTER_FILE = "config/system_center.json"

HOME_FALLBACK = {"lat": -32.8895, "lon": -68.8458, "label": "Local point"}
MAX_PUBLIC_SENSORS = 80


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def system_center():
    data = read_json(SYSTEM_CENTER_FILE)
    if isinstance(data, dict):
        lat = _as_float(data.get("lat"), None)
        lon = _as_float(data.get("lon"), None)
        if lat is not None and lon is not None:
            return {
                "lat": lat,
                "lon": lon,
                "label": data.get("label") or data.get("name") or HOME_FALLBACK.get("label", "Local point")
            }
    return dict(HOME_FALLBACK)


def _as_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default



def _pick(data, english_key, legacy_key=None, default=None):
    """Read English-core key first, then temporary legacy key."""
    if not isinstance(data, dict):
        return default
    if english_key in data:
        return data.get(english_key)
    if legacy_key and legacy_key in data:
        return data.get(legacy_key)
    return default


def _pick_dict(data, english_key, legacy_key=None):
    value = _pick(data, english_key, legacy_key, {})
    return value if isinstance(value, dict) else {}


def _pick_list(data, english_key, legacy_key=None):
    value = _pick(data, english_key, legacy_key, [])
    return value if isinstance(value, list) else []


def _as_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
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


def _human_class(label):
    if label is None:
        return "waiting"

    key = str(label).strip().lower()

    aliases = {
        "high": "strong",
        "strong": "strong",
        "strong_cell": "strong",

        "good": "good",
        "good_cell": "good",

        "minimal": "minimal",
        "minimum": "minimal",
        "minimal_cell": "minimal",

        "regular": "single station",
        "listening": "single station",
        "single_station": "single station",

        "blind_zone": "no recent data",
        "stale_cell": "no recent data",
        "no data": "no recent data",
        "no recent data": "no recent data",

        "context": "context",
        "observer_context": "context",
    }

    return aliases.get(key, str(label))


def _network_label_en(label):
    text = str(label or "").strip()
    return text or "unknown network"

def _human_state(label):
    text = str(label or "normal").strip().lower()

    if text in ("normal", "ok"):
        return "normal"
    if text == "observation":
        return "observation"
    if text in ("verification", "watch"):
        return "verification"
    if text in ("warning", "anticipation", "confirmation"):
        return "warning"

    return text


def _sensor_quality_label(score):
    value = _as_float(score, None)
    if value is None:
        return None
    if value >= 0.86:
        return "high"
    if value >= 0.72:
        return "good"
    if value >= 0.50:
        return "regular"
    return "under_review"


def _cell_label_lookup(display_cells):
    out = {}
    for c in display_cells or []:
        cell_id = c.get("cell_id")
        if not cell_id:
            continue
        short = c.get("short_label") or c.get("direction_label") or cell_id
        label = "Local" if short == "Local" or cell_id == "cell_00" else _direction_name(short)
        out[cell_id] = label
    return out

def _direction_name(label):
    value = str(label or "").strip().upper()
    names = {
        "N": "North",
        "NE": "Northeast",
        "E": "East",
        "SE": "Southeast",
        "S": "South",
        "SW": "Southwest",
        "W": "West",
        "NW": "Northwest",
        "LOCAL": "Local",
    }
    return names.get(value, str(label or "").strip() or "Zone")


def _cell_inventories():
    import glob

    out = {}

    for path in sorted(glob.glob("config/auto_cell_*_inventory.json")):
        inventory = read_json(path) or {}
        if not isinstance(inventory, dict):
            continue

        cell_id = inventory.get("cell_id")
        if not cell_id:
            continue

        out[cell_id] = inventory

    return out



def _sensor_geo_overrides():
    data = read_json(SENSOR_GEO_OVERRIDES_FILE) or {}
    sensors = data.get("sensors", {}) if isinstance(data, dict) else {}
    out = {}
    for key, value in sensors.items():
        lat = _as_float(value.get("lat"), None)
        lon = _as_float(value.get("lon"), None)
        if lat is None or lon is None:
            continue
        source = value.get("source") or "sensor_geo_overrides"
        name = value.get("name") or key
        out[str(key)] = {
            "lat": lat,
            "lon": lon,
            "name": name,
            "locality": value.get("locality") or name,
            "source": source,
            "approx_location": bool(value.get("approx_location", True)),
        }
    return out


def _catalog_scores():
    catalog = read_json(SENSOR_CATALOG_FILE) or {}
    sensors = catalog.get("sensors", {}) if isinstance(catalog, dict) else {}
    out = {}
    for key, s in sensors.items():
        out[key] = {
            "score_service": s.get("score_service"),
            "score_latency": s.get("score_latency"),
            "score_credibility": s.get("score_credibility"),
            "score_selection": s.get("score_selection"),
            "confidence_state": s.get("confidence_state"),
            "operational_state": s.get("operational_state"),
            "latency_seconds": s.get("latency_last_seconds"),
        }
    return out


def _sensor_locations_from_runtime():
    locations = {}

    import glob
    for inv_path in sorted(glob.glob("config/auto_cell_*_inventory.json")):
        auto_inv = read_json(inv_path) or {}
        for item in auto_inv.get("sensors", []) or []:
            key = _sensor_key(
                item.get("network"),
                item.get("station"),
                item.get("channel"),
            )
            lat = _as_float(item.get("lat"), None)
            lon = _as_float(item.get("lon"), None)

            if key and lat is not None and lon is not None:
                locations[key] = {
                    "lat": lat,
                    "lon": lon,
                    "name": item.get("name") or item.get("site") or key,
                    "locality": item.get("locality") or item.get("name") or item.get("site") or key,
                    "cell_id": auto_inv.get("cell_id", "auto_cell_01"),
                    "direction": item.get("direction") or auto_inv.get("direction"),
                    "provider": item.get("provider") or auto_inv.get("server_name"),
                    "source": "auto_cell_inventory",
                }

    candidate = read_json("config/candidate_inventory.json") or {}
    for item in candidate.get("sensors", []) or []:
        key = _sensor_key(
            item.get("network"),
            item.get("station"),
            item.get("channel"),
        )
        lat = _as_float(item.get("lat"), None)
        lon = _as_float(item.get("lon"), None)
        if key and lat is not None and lon is not None:
            locations.setdefault(key, {
                "lat": lat,
                "lon": lon,
                "name": item.get("name") or item.get("site") or key,
                "locality": item.get("locality") or item.get("name") or item.get("site") or key,
                "cell_id": "candidate_inventory",
                "direction": item.get("direction"),
                "provider": item.get("provider") or item.get("source_provider"),
                "source": "candidate_inventory",
            })
    return locations


def _live_sensors_from_states():
    sensors = {}

    local_state = read_json(LOCAL_STATE_FILE) or {}
    zone = (local_state.get("zones", {}) or {}).get("local_adaptive_zone", {})
    for key, s in (zone.get("sensors", {}) or {}).items():
        sensor_id = s.get("sensor_id") or key
        role = str(s.get("role", "")).strip().lower()
        is_observer = role == "regional_observer"

        sensors[sensor_id] = {
            "sensor_id": sensor_id,
            "cell_id": "regional_observers" if is_observer else "cell_00",
            "cell_label": "Observers" if is_observer else "Local",
            "name": s.get("name") or sensor_id,
            "locality": s.get("locality") or s.get("name") or sensor_id,
            "network": s.get("network"),
            "station": s.get("station"),
            "channel": s.get("channel"),
            "role": s.get("role"),
            "state": s.get("sensor_state", "active"),
            "calibrated": bool(s.get("calibrated", False)),
            "flag": bool(s.get("flag", False)),
            "latency_seconds": _as_float(s.get("latency_seconds"), None),
            "ratio": _as_float(s.get("ratio"), None),
            "distance_km": _as_float(s.get("distance_km"), None),
            "has_location": False,
        }

    import glob
    for state_path in sorted(glob.glob("runtime/auto_cell_*_state.json")):
        auto_state = read_json(state_path) or {}
        auto_label = auto_state.get("cell_id") or state_path.split("/")[-1].replace("_state.json", "")
        for key, s in (_pick_dict(auto_state, "sensors") or {}).items():
            sensor_id = s.get("key") or key
            name = s.get("name") or sensor_id
            sensors[sensor_id] = {
                "sensor_id": sensor_id,
                "cell_id": auto_label,
                "cell_label": auto_label,
                "name": name,
                "locality": name,
                "network": s.get("network"),
                "station": s.get("station"),
                "channel": s.get("channel"),
                "role": s.get("role"),
                "state": s.get("sensor_state", "active"),
                "calibrated": bool(s.get("calibrated", False)),
                "flag": bool(s.get("flag", False)),
                "latency_seconds": _as_float(s.get("latency_seconds"), None),
                "ratio": _as_float(s.get("ratio"), None),
                "distance_km": _as_float(s.get("distance_km"), None),
                "warning_seconds": _as_float(s.get("effective_warning_seconds"), None),
                "direction": s.get("direction"),
                "has_location": False,
            }

    locations = _sensor_locations_from_runtime()
    overrides = _sensor_geo_overrides()
    scores = _catalog_scores()
    for key, s in sensors.items():
        loc = locations.get(key) or overrides.get(key)
        if loc:
            lat = loc.get("lat")
            lon = loc.get("lon")
            source = loc.get("source") or "runtime"
            approx = bool(loc.get("approx_location", False))
            s.update({
                "lat": lat,
                "lon": lon,
                "has_location": True,
                "direction": s.get("direction") or loc.get("direction"),
                "provider": loc.get("provider"),
                "location_source": source,
                "approx_location": approx,
                "locality": loc.get("locality") or loc.get("name"),
            })
            # Public JSON representation: lat/lon grouped together.
            # Flat lat/lon fields are retained for the current web map.
            if lat is not None and lon is not None:
                s["coords"] = {
                    "lat": lat,
                    "lon": lon,
                }
            s["location"] = {
                "approx": approx,
                "source": source,
            }
            if loc.get("name") and (not s.get("name") or s.get("name") == key):
                s["name"] = loc.get("name")
        if key in scores:
            s.update({k: v for k, v in scores[key].items() if v is not None})
            q = _sensor_quality_label(scores[key].get("score_selection"))
            if q:
                s["quality_label"] = q

    return list(sensors.values())[:MAX_PUBLIC_SENSORS]




def _public_display_cells(display_cells, sensors=None):
    out = []
    sensors = sensors or []
    local_sensors = [
        s for s in sensors
        if s.get("cell_id") == "cell_00"
        and str(s.get("state") or "").lower() == "active"
    ]
    local_calibrated = [
        s for s in local_sensors
        if bool(s.get("calibrated", False))
    ]

    for c in display_cells or []:
        short = c.get("short_label") or c.get("direction_label") or c.get("cell_id") or "Zone"
        if short != "Local":
            short = _direction_name(short)

        is_local = c.get("cell_id") == "cell_00"

        out.append({
            "cell_id": c.get("cell_id"),
            "label": "Local" if is_local else (c.get("label") or short),
            "role": c.get("role"),
            "class": c.get("class"),
            "class_label": _human_class(c.get("class_label") or c.get("class")),
            "state": c.get("state"),
            "state_label": _human_state(c.get("state_label")),
            "fresh": bool(c.get("fresh", False)),
            "sensors_active": _as_int(c.get("sensors_active", 0)),
            "sensors_calibrated": _as_int(c.get("sensors_calibrated", 0)),
            "warning_seconds": _as_float(c.get("warning_seconds"), None),
            "direction_label": c.get("direction_label"),
        })

    return out[:6]


def _public_cells_for_map(fused_cells):
    runtime = _cell_inventories()
    out = []
    for cell_id, c in (fused_cells or {}).items():
        rc = runtime.get(cell_id, {}) if isinstance(runtime, dict) else {}
        center = rc.get("center", {}) if isinstance(rc, dict) else {}
        lat = _as_float(center.get("lat"), None)
        lon = _as_float(center.get("lon"), None)
        if lat is None or lon is None:
            if cell_id == "cell_00":
                home = system_center()
                lat, lon = home["lat"], home["lon"]
            else:
                continue
        direction = c.get("direction_label") or rc.get("direction") or ""
        label = "Local" if cell_id == "cell_00" else (c.get("label") or rc.get("label") or _direction_name(direction or c.get("short_label") or cell_id))
        class_raw = (
            c.get("cell_class_label")
            or c.get("class_label")
            or c.get("display_class_label")
            or c.get("cell_class")
            or c.get("class")
        )
        state_raw = (
            c.get("display_state_label")
            or c.get("state_label")
            or c.get("state")
        )
        out.append({
            "cell_id": cell_id,
            "label": label,
            "role": c.get("role"),
            "class_label": _human_class(class_raw),
            "state_label": _human_state(state_raw),
            "lat": lat,
            "lon": lon,
            "sensors_active": _as_int(c.get("active_sensors", c.get("sensors_active", 0))),
            "warning_seconds": _as_float(c.get("effective_warning_seconds", c.get("warning_seconds", 0)), 0),
            "direction_label": direction,
        })
    return out


def _map_center(sensors, cells):
    points = []
    for s in sensors:
        if s.get("has_location") and s.get("lat") is not None and s.get("lon") is not None:
            points.append((s["lat"], s["lon"]))
    for c in cells:
        if c.get("lat") is not None and c.get("lon") is not None:
            points.append((c["lat"], c["lon"]))
    if not points:
        home = system_center()
        return {"lat": home["lat"], "lon": home["lon"], "zoom": 6}
    lat = sum(p[0] for p in points) / len(points)
    lon = sum(p[1] for p in points) / len(points)
    return {"lat": round(lat, 5), "lon": round(lon, 5), "zoom": 6}



def _active_sensor_public(s):
    return str(s.get("state") or "").lower() in (
        "active", "calibrating"
    )


def _public_cells_from_display(public_cells, sensors, center):
    by_id = {}

    for s in sensors or []:
        cid = s.get("cell_id")
        if not cid:
            continue
        by_id.setdefault(cid, []).append(s)

    out = []

    for c in public_cells or []:
        cid = c.get("cell_id")
        if not cid or cid == "regional_observers":
            continue

        items = by_id.get(cid, [])

        lat = None
        lon = None

        if cid == "cell_00":
            lat = _as_float(center.get("lat"), None)
            lon = _as_float(center.get("lon"), None)
        else:
            pts = []
            for s in items:
                slat = _as_float(s.get("lat"), None)
                slon = _as_float(s.get("lon"), None)
                if slat is not None and slon is not None:
                    pts.append((slat, slon))

            if pts:
                lat = sum(x for x, _ in pts) / len(pts)
                lon = sum(y for _, y in pts) / len(pts)

        if lat is None or lon is None:
            continue

        active_count = len([s for s in items if _active_sensor_public(s)])
        calibrated_count = len([
            s for s in items
            if bool(s.get("calibrated", False))
        ])

        if active_count == 0:
            active_count = _as_int(c.get("sensors_active", 0))

        out.append({
            "cell_id": cid,
            "label": c.get("label") or cid,
            "role": c.get("role"),
            "class_label": _human_class(c.get("class_label") or c.get("class")),
            "state_label": _human_state(c.get("state_label") or c.get("state")),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "sensors_active": active_count,
            "sensors_calibrated": calibrated_count,
            "warning_seconds": _as_float(c.get("warning_seconds"), 0.0),
            "direction_label": c.get("direction_label") or c.get("direction") or "",
        })

    return out


def build_public_live():
    fused = build_multicell_state()
    event_journal.record_fused_snapshot(fused)
    net = fused.get("network", {})
    event = fused.get("event", {})
    display = fused.get("display", {})

    sensors = _live_sensors_from_states()
    public_cells = _public_display_cells(fused.get("display_cells", []), sensors)
    label_lookup = _cell_label_lookup(public_cells)
    for sensor in sensors:
        cid = sensor.get("cell_id")
        if cid in label_lookup:
            sensor["cell_label"] = label_lookup[cid]
    center = system_center()
    cells_map = _public_cells_from_display(public_cells, sensors, center)

    map_center = _map_center(sensors, cells_map)

    alert_active = bool(event.get("sound", False)) or str(event.get("level", "normal")).lower() != "normal"
    poll_ms = 1500 if alert_active else 5000

    display_public = {
        "title": display.get("title", "Cuyum"),
        "network": display.get("network") or _network_label_en(net.get("label", "Cuyum network")),
        "status": _human_state(display.get("status", "normal")),
        "message": display.get("message", "normal"),
        "sound": bool(display.get("sound", False)),
    }

    return {
        "system": "Cuyum",
        "mode": "public_live_v1_2",
        "experimental": True,
        "updated_at": fused.get("updated_at", now_iso()),
        "poll": {
            "normal_ms": 5000,
            "alert_ms": 1500,
            "next_ms": poll_ms,
        },
        "display": display_public,
        "display_cells": public_cells,
        "network": {
            "mode": net.get("mode"),
            "label": _network_label_en(net.get("label")),
            "cells_active": net.get("cells_active", 0),
            "cells_configured": net.get("cells_configured", 0),
            "sensors_active": len([s for s in sensors if _active_sensor_public(s)]),
            "sensors_calibrated": len([s for s in sensors if bool(s.get("calibrated", False))]),
        },
        "alert": {
            "active": alert_active,
            "level": event.get("level", "normal"),
            "message": display_public["message"],
            "sound": bool(event.get("sound", False)),
            "buzzer_seconds": _as_int(event.get("buzzer_seconds", 0)),
        },
        "map": map_center,
        "system_center": center,
        "map_center": map_center,
        "cells": cells_map,
        "sensors": sensors,
        "notice": "Experimental network. It does not replace official sources or institutional procedures.",
    }
