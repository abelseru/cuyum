import json
import os
from datetime import datetime, timezone

from multicell_fusion import build_multicell_state
import event_journal

LOCAL_STATE_FILE = "runtime/state_cell_00_seedlink.json"
AUTO_CELL_01_STATE_FILE = "runtime/auto_cell_01_state.json"
RUNTIME_CELLS_FILE = "cuyum_runtime_cells.json"
AUTO_INVENTORY_FILE = "config/auto_inventory_cells.json"
INVENTORY_AUTO_CELL_01_FILE = "config/auto_cell_01_inventory.json"
SENSOR_CATALOG_FILE = "config/sensor_catalog.json"
SENSOR_GEO_OVERRIDES_FILE = "config/sensor_geo_overrides.json"
SYSTEM_CENTER_FILE = "config/system_center.json"

HOME_FALLBACK = {"lat": -32.8895, "lon": -68.8458, "label": "Punto local"}
MAX_PUBLIC_SENSORS = 80


def ahora_iso():
    return datetime.now(timezone.utc).isoformat()


def leer_json(ruta):
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def system_center():
    data = leer_json(SYSTEM_CENTER_FILE)
    if isinstance(data, dict):
        lat = _as_float(data.get("lat"), None)
        lon = _as_float(data.get("lon"), None)
        if lat is not None and lon is not None:
            return {
                "lat": lat,
                "lon": lon,
                "label": data.get("label") or data.get("name") or HOME_FALLBACK.get("label", "Punto local")
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


def _sensor_key(red=None, estacion=None, canal=None, code=None, clave=None):
    if clave:
        return str(clave)
    if code:
        return str(code)
    parts = [red, estacion, canal]
    if all(parts):
        return f"{red}.{estacion}.{canal}"
    return ""


def _human_class(label):
    text = str(label or "").strip().lower()
    table = {
        "strong_cell": "high",
        "good_cell": "good",
        "minimal_cell": "minimal",
        "single_station": "listening",
        "blind_zone": "waiting",
        "stale_cell": "waiting",
        "alta": "high",
        "buena": "good",
        "mínima": "minimal",
        "minima": "minimal",
        "escucha": "listening",
        "en espera": "waiting",
        "high": "high",
        "good": "good",
        "minimal": "minimal",
        "listening": "listening",
        "waiting": "waiting",
    }
    return table.get(text, text or "unknown")


def _network_label_en(label):
    text = str(label or "").strip().lower()
    table = {
        "red multicelda alta": "high multicell network",
        "red multicelda parcial": "partial multicell network",
        "red local activa": "active local network",
        "red degradada": "degraded network",
        "red parcial": "partial network",
        "high multicell network": "high multicell network",
        "partial multicell network": "partial multicell network",
        "active local network": "active local network",
        "degraded network": "degraded network",
        "partial network": "partial network",
    }
    return table.get(text, text or "unknown network")

def _human_state(label):
    text = str(label or "normal").strip().lower()
    if "urgente" in text:
        return "observación"
    if text in ("normal", "ok"):
        return "normal"
    if text in ("observacion", "observación"):
        return "observación"
    if text in ("verificación", "verificacion", "vigilancia"):
        return "verificación"
    if text in ("aviso", "anticipacion", "anticipación", "confirmacion", "confirmación"):
        return "aviso"
    return text




def _sensor_quality_label(score):
    value = _as_float(score, None)
    if value is None:
        return None
    if value >= 0.86:
        return "alta"
    if value >= 0.72:
        return "buena"
    if value >= 0.50:
        return "regular"
    return "en revisión"


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
        "N": "Norte",
        "NE": "Noreste",
        "E": "Este",
        "SE": "Sureste",
        "S": "Sur",
        "SO": "Suroeste",
        "SW": "Suroeste",
        "O": "Oeste",
        "W": "Oeste",
        "NO": "Noroeste",
        "NW": "Noroeste",
        "LOCAL": "Local",
    }
    return names.get(value, str(label or "").strip() or "Zona")


def _runtime_cells():
    data = leer_json(RUNTIME_CELLS_FILE) or leer_json(AUTO_INVENTORY_FILE) or {}
    return data.get("cells", {}) if isinstance(data, dict) else {}


def _inventory_auto_cell_01():
    return leer_json(INVENTORY_AUTO_CELL_01_FILE) or {}



def _sensor_geo_overrides():
    data = leer_json(SENSOR_GEO_OVERRIDES_FILE) or {}
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
            "locality": value.get("localidad") or value.get("locality") or name,
            "source": source,
            "approx_location": bool(value.get("approx_location", True)) or "aproximada" in str(source).lower(),
        }
    return out


def _catalog_scores():
    catalog = leer_json(SENSOR_CATALOG_FILE) or {}
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
    runtime = _runtime_cells()
    for cell_id, cell in runtime.items():
        for group_name in ("primary", "reserve_or_context", "reservas"):
            items = cell.get(group_name, []) or []
            for item in items:
                key = item.get("code") or _sensor_key(item.get("red"), item.get("estacion"), item.get("canal"))
                lat = _as_float(item.get("lat"), None)
                lon = _as_float(item.get("lon"), None)
                if key and lat is not None and lon is not None:
                    locations[key] = {
                        "lat": lat,
                        "lon": lon,
                        "name": item.get("site") or item.get("nombre") or key,
                        "locality": item.get("localidad") or item.get("locality") or item.get("site") or item.get("nombre") or key,
                        "cell_id": cell_id,
                        "direction": item.get("direction") or cell.get("direction"),
                        "provider": item.get("provider") or item.get("server_name"),
                    }
    import glob
    for inv_path in sorted(glob.glob("config/auto_cell_*_inventory.json")):
        auto_inv = leer_json(inv_path) or {}
        for group_name in ("sensors", "sensores", "reserves", "reservas"):
            for item in auto_inv.get(group_name, []) or []:
                key = _sensor_key(item.get("network", item.get("red")), item.get("station", item.get("estacion")), item.get("channel", item.get("canal")))
                lat = _as_float(item.get("lat"), None)
                lon = _as_float(item.get("lon"), None)
                if key and lat is not None and lon is not None:
                    locations[key] = {
                        "lat": lat,
                        "lon": lon,
                        "name": item.get("name") or item.get("nombre") or item.get("site") or key,
                        "locality": item.get("locality") or item.get("localidad") or item.get("name") or item.get("nombre") or item.get("site") or key,
                        "cell_id": auto_inv.get("cell_id", "auto_cell_01"),
                        "direction": item.get("direction") or auto_inv.get("direction"),
                        "provider": item.get("provider") or auto_inv.get("server_name"),
                    }
    return locations


def _live_sensors_from_states():
    sensors = {}

    local_state = leer_json(LOCAL_STATE_FILE) or {}
    zona = (local_state.get("zonas", {}) or {}).get("cordillera_cuyo_adaptativa", {})
    for key, s in (_pick_dict(zona, "sensors", "sensores") or {}).items():
        sensor_id = s.get("sensor_id", s.get("clave")) or key
        sensors[sensor_id] = {
            "sensor_id": sensor_id,
            "cell_id": "cell_00",
            "cell_label": "Local",
            "name": s.get("name", s.get("nombre")) or sensor_id,
            "locality": s.get("locality", s.get("localidad")) or s.get("name", s.get("nombre")) or sensor_id,
            "localidad": s.get("locality", s.get("localidad")) or s.get("name", s.get("nombre")) or sensor_id,
            "network": s.get("network", s.get("red")),
            "station": s.get("station", s.get("estacion")),
            "channel": s.get("channel", s.get("canal")),
            "role": s.get("role", s.get("rol")),
            "state": s.get("sensor_state", s.get("estado_sensor", "active")),
            "calibrated": bool(s.get("calibrated", s.get("calibrado", False))),
            "flag": bool(s.get("flag", False)),
            "latency_seconds": _as_float(s.get("latency_seconds", s.get("latency_segundos", s.get("latencia_segundos"))), None),
            "ratio": _as_float(s.get("ratio"), None),
            "distance_km": _as_float(s.get("distance_km", s.get("distancia_km")), None),
            "has_location": False,
        }

    import glob
    for state_path in sorted(glob.glob("runtime/auto_cell_*_state.json")):
        auto_state = leer_json(state_path) or {}
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
                "localidad": name,
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
                "localidad": loc.get("locality") or loc.get("name"),
            })
            # Presentación humana para el JSON público: lat/lon juntos.
            # Se mantienen lat/lon planos por compatibilidad con el mapa web actual.
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


def _regional_observer_count(sensors):
    count = 0
    calibrated = 0
    for s in sensors or []:
        role = str(s.get("role") or s.get("rol") or "").strip().lower()
        state = str(s.get("state") or s.get("sensor_state") or s.get("estado") or "").strip().lower()
        if role == "observador_regional" and state in ("active", "activo", "vivo"):
            count += 1
            if bool(s.get("calibrated", s.get("calibrado", False))):
                calibrated += 1
    return count, calibrated


def _public_display_cells(display_cells, sensors=None):
    out = []
    for c in display_cells or []:
        short = c.get("short_label") or c.get("direction_label") or c.get("cell_id") or "Zona"
        if short != "Local":
            short = _direction_name(short)
        out.append({
            "cell_id": c.get("cell_id"),
            "label": "Local" if c.get("cell_id") == "cell_00" else (c.get("label") or short),
            "role": c.get("role"),
            "class": c.get("class"),
            "class_label": _human_class(c.get("class_label")),
            "state": c.get("state"),
            "state_label": _human_state(c.get("state_label")),
            "fresh": bool(c.get("fresh", False)),
            "sensors_active": _as_int(c.get("sensors_active", 0)),
            "sensors_calibrated": _as_int(c.get("sensors_calibrated", 0)),
            "warning_seconds": _as_float(c.get("warning_seconds"), None),
            "direction_label": c.get("direction_label"),
        })

    observer_count, observer_calibrated = _regional_observer_count(sensors)
    if observer_count > 0:
        out.append({
            "cell_id": "regional_observers",
            "label": "Observadores",
            "role": "regional_observer",
            "class": "observer_context",
            "class_label": "contexto",
            "state": "normal",
            "state_label": "contexto",
            "fresh": True,
            "sensors_active": observer_count,
            "sensors_calibrated": observer_calibrated,
            "warning_seconds": None,
            "direction_label": None,
        })

    return out[:6]


def _public_cells_for_map(fused_cells):
    runtime = _runtime_cells()
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
            or c.get("estado")
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
            "sensors_active": _as_int(_pick(c, "active_sensors", "sensores_activos", c.get("sensors_active", 0))),
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
    cells_map = _public_cells_for_map(fused.get("cells", {}))
    map_center = _map_center(sensors, cells_map)
    center = system_center()

    alert_active = bool(_pick(event, "sound", "sonar", False)) or str(event.get("level", "normal")).lower() not in ("normal", "observacion")
    poll_ms = 1500 if alert_active else 5000

    display_public = {
        "title": display.get("title", "Cuyum"),
        "network": display.get("network") or _network_label_en(net.get("label", "Cuyum network")),
        "status": _human_state(display.get("status", "normal")),
        "message": display.get("message", "normal"),
        "sound": bool(display.get("sound", False)),
    }

    return {
        "sistema": "Cuyum",
        "modo": "public_live_v1_2",
        "experimental": True,
        "updated_at": fused.get("ultima_actualizacion", ahora_iso()),
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
            "sensors_active": _pick(net, "total_active_sensors", "sensores_activos_total", 0),
            "sensors_calibrated": _pick(net, "total_calibrated_sensors", "sensores_calibrados_total", 0),
        },
        "alert": {
            "active": alert_active,
            "level": event.get("level", "normal"),
            "message": display_public["message"],
            "sound": bool(_pick(event, "sound", "sonar", False)),
            "buzzer_seconds": _as_int(event.get("buzzer_segundos", 0)),
        },
        "map": map_center,
        "system_center": center,
        "map_center": map_center,
        "cells": cells_map,
        "sensors": sensors,
        "notice": "Red experimental. No reemplaza fuentes oficiales ni procedimientos institucionales.",
    }
