import json
import os
from collections import Counter
from datetime import datetime, timezone

# Observation mode: detection is visible, but sound output is disabled.
OBSERVATION_MODE_NO_SOUND = True

LOCAL_STATE_FILE = "runtime/state_cell_00_seedlink.json"
AUTO_CELL_01_STATE_FILE = "runtime/auto_cell_01_state.json"
AUTO_CELLS_RUNTIME_FILE = "cuyum_runtime_cells.json"

# No debe ser demasiado agresivo: algunos lectores escriben por tandas.
# If this time is exceeded, the cell is not considered fresh for decisions.
MAX_CELL_AGE_SECONDS = 180

CELL_CLASS_LABELS = {
    "strong_cell": "alta",
    "good_cell": "buena",
    "minimal_cell": "mínima",
    "single_station": "escucha",
    "stale_cell": "sin datos recientes",
    "blind_zone": "sin cobertura",
}

CLASS_RANK = {
    "strong_cell": 5,
    "good_cell": 4,
    "minimal_cell": 3,
    "single_station": 2,
    "blind_zone": 1,
    "stale_cell": 0,
}


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


def _parse_iso(value):
    if not value:
        return None
    try:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _age_seconds(value):
    dt = _parse_iso(value)
    if not dt:
        return None
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())


def _is_fresh(value, max_age_seconds=MAX_CELL_AGE_SECONDS):
    age = _age_seconds(value)
    if age is None:
        return False, None
    return age <= max_age_seconds, round(age, 1)



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


def _as_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _quality_estado(quality):
    if isinstance(quality, dict):
        return str(quality.get("state", quality.get("estado", "unknown")))
    if quality is None:
        return "unknown"
    return str(quality)


def _ratio_max_from_sensors(sensors):
    ratios = []
    for sensor in (sensors or {}).values():
        ratios.append(_as_float(sensor.get("ratio", 0), 0))
    return round(max(ratios), 2) if ratios else 0



def _english_code(value):
    mapping = {
        "multicelda_fuerte": "high_multicell",
        "multicelda_parcial": "partial_multicell",
        "remota_sin_local": "remote_only",
        "degradada": "degraded",
        "buena": "good",
        "alta": "high",
        "regular": "regular",
        "desconocida": "unknown",
        "strong": "strong",
        "good": "good",
        "minimum_viable": "minimum_viable",
        "weak_context": "weak_context",
        "insufficient": "insufficient",
        "no_data": "no_data",
        "unknown": "unknown",
        "sin_estado": "no_state",
        "sin cobertura": "blind_zone",
        "sin datos recientes": "stale",
        "observacion_sin_sonido": "observation_without_sound",
    }
    return mapping.get(value, value)


def _max_effective_warning(sensors):
    values = []
    for sensor in (sensors or {}).values():
        values.append(_as_float(_pick(sensor, "effective_warning_seconds", "aviso_util", 0), 0))
    return round(max(values), 1) if values else 0


def _best_direction_from_sensors(sensors):
    directions = []
    for sensor in (sensors or {}).values():
        d = str(sensor.get("direction", "")).strip().upper()
        if d and d not in ("NONE", "NULL", "?"):
            directions.append(d)
    if not directions:
        return ""
    # Si hay empate, preferir la dirección del primer sensor de mayor prioridad, ya que suele ser el principal.
    counts = Counter(directions)
    most_common = counts.most_common()
    if most_common and most_common[0][1] > 1:
        return most_common[0][0]
    for sensor in sorted((sensors or {}).values(), key=lambda x: _as_int(_pick(x, "priority", "prioridad", 999), 999)):
        d = str(sensor.get("direction", "")).strip().upper()
        if d:
            return d
    return most_common[0][0] if most_common else ""


def _sanitize_level(level):
    """Nunca exponer 'urgente' por un solo sensor. Biblioteca escolar: lenguaje prudente."""
    value = str(level or "normal")
    low = value.lower()
    if "urgente" in low:
        return "observacion"
    if low in ("atención_local", "atención", "high", "critico", "alto"):
        return "vigilancia"
    return value


def _safe_message(message, confirming_stations=0, sound=False):
    """Mensajes seguros para pantalla/ESP32: sin 'urgente' ni tono de servicio técnico."""
    msg = str(message or "normal")
    low = msg.lower()
    if "urgente" in low or "anomal" in low or "atención" in low:
        if sound:
            return "Señal en verificación por la red Cuyum"
        if _as_int(confirming_stations, 0) >= 2:
            return "Señal local en verificación"
        if _as_int(confirming_stations, 0) == 1:
            return "Señal aislada sin confirmación"
        return "Observación de red sin confirmación"
    return msg


def _display_state_label(estado, confirming_stations=0, sound=False):
    low = str(estado or "normal").lower()
    if sound:
        return "aviso"
    if "urgente" in low or "atención" in low or "anomal" in low:
        if _as_int(confirming_stations, 0) >= 2:
            return "verificación"
        return "observación"
    if low in ("normal", "ok"):
        return "normal"
    return _sanitize_level(estado)


def classify_cell(active_sensors, fresh=True):
    """Microcell policy: 3=strong, 2=good, 1=listening, 0=blind."""
    if not fresh:
        return "stale_cell"
    n = _as_int(active_sensors, 0)
    if n >= 3:
        return "strong_cell"
    if n == 2:
        return "good_cell"
    if n == 1:
        return "single_station"
    return "blind_zone"


def cell_can_raise_watch(cell_class):
    return cell_class in ("strong_cell", "good_cell", "minimal_cell")


def cell_can_trigger_anticipation(cell_class):
    # A minimal cell can inform watch state, but should not trigger sound by itself.
    return cell_class in ("strong_cell", "good_cell")


def _base_cell(cell_id, label, role, source_file):
    return {
        "cell_id": cell_id,
        "label": label,
        "short_label": "Local" if cell_id == "cell_00" else cell_id,
        "direction_label": "",
        "role": role,
        "source_file": source_file,
        "fresh": False,
        "age_seconds": None,
        "estado": "sin_estado",
        "raw_estado": "sin_estado",
        "display_state_label": "sin datos",
        "flag": False,
        "calidad_red": "sin_estado",
        "sensores_activos": 0,
        "sensores_calibrados": 0,
        "anticipacion_activos": 0,
        "confirmacion_activos": 0,
        "estaciones_confirmando": 0,
        "estaciones_confirmando_lista": [],
        "ratio_max": 0,
        "effective_warning_seconds": 0,
        "cell_class": "stale_cell",
        "cell_class_label": CELL_CLASS_LABELS["stale_cell"],
        "can_raise_watch": False,
        "can_trigger_anticipation": False,
        "feeds_esp32": False,
        "ultima_actualizacion": None,
    }


def _finish_cell(cell):
    cell_class = classify_cell(cell.get("sensores_activos", 0), cell.get("fresh", False))
    cell["cell_class"] = cell_class
    cell["cell_class_label"] = CELL_CLASS_LABELS.get(cell_class, cell_class)
    cell["can_raise_watch"] = cell_can_raise_watch(cell_class)
    cell["can_trigger_anticipation"] = cell_can_trigger_anticipation(cell_class)
    cell["display_state_label"] = _display_state_label(
        cell.get("estado"), cell.get("estaciones_confirmando", 0), False
    )

    cell["state"] = cell.get("estado")
    cell["active_sensors"] = _as_int(cell.get("active_sensors", cell.get("sensores_activos", 0)), 0)
    cell["calibrated_sensors"] = _as_int(cell.get("calibrated_sensors", cell.get("sensores_calibrados", 0)), 0)
    cell["confirming_stations"] = _as_int(cell.get("confirming_stations", cell.get("estaciones_confirmando", 0)), 0)
    cell["confirming_station_list"] = cell.get("confirming_station_list", cell.get("estaciones_confirmando_lista", []))
    cell["network_quality"] = _english_code(cell.get("network_quality", cell.get("calidad_red")))

    return cell


def _local_cell(local_data):
    cell = _base_cell("cell_00", "Local / control", "local_control", LOCAL_STATE_FILE)
    if not local_data:
        return _finish_cell(cell)

    zona = (local_data or {}).get("zones", {}).get("local_adaptive_zone", {}) or (local_data or {}).get("zonas", {}).get("cordillera_cuyo_adaptativa", {})
    if not zona:
        # Compatibilidad por si alguna versión vieja escribía el estado plano.
        zona = local_data or {}

    quality = zona.get("network_quality", zona.get("calidad_red", {}))
    fresh, age = _is_fresh(zona.get("updated_at") or zona.get("ultima_actualizacion") or local_data.get("updated_at") or local_data.get("ultima_actualizacion"))
    sensors = _pick_dict(zona, "sensors", "sensores")
    raw_estado = zona.get("estado", (local_data.get("esp32", {}) or {}).get("nivel", "sin_estado"))
    confirming_stations = _as_int(_pick(zona, "confirming_stations", "estaciones_confirmando", 0), 0)

    active_sensor_items = [
        s for s in sensors.values()
        if _pick(s, "sensor_state", "estado_sensor", s.get("state")) in ("activo", "active")
    ]
    calibrated_sensor_items = [
        s for s in sensors.values()
        if _pick(s, "calibrated", "calibrado", False)
    ]
    validating_sensor_items = [
        s for s in active_sensor_items
        if bool(_pick(s, "can_confirm", "puede_confirmar", False))
        or bool(_pick(s, "can_trigger", "puede_disparar", False))
    ]
    observer_sensor_items = [
        s for s in active_sensor_items
        if s not in validating_sensor_items
    ]

    active_sensors_raw = _as_int(
        _pick(
            zona,
            "active_sensors",
            "sensores_activos",
            _pick(quality, "active_sensors", "sensores_activos", 0) if isinstance(quality, dict) else 0
        ),
        0
    )
    calibrated_sensors_raw = _as_int(
        _pick(
            zona,
            "calibrated_sensors",
            "sensores_calibrados",
            _pick(quality, "calibrated_sensors", "sensores_calibrados", 0) if isinstance(quality, dict) else 0
        ),
        0
    )

    validating_sensors = len(validating_sensor_items) if active_sensor_items else active_sensors_raw
    observer_sensors = len(observer_sensor_items) if active_sensor_items else 0

    cell.update({
        "fresh": fresh,
        "age_seconds": age,
        "raw_estado": raw_estado,
        "estado": _sanitize_level(raw_estado),
        "flag": bool(zona.get("flag", False)),
        "calidad_red": _quality_estado(quality),
        "sensores_activos": validating_sensors,
        "sensores_calibrados": min(validating_sensors, calibrated_sensors_raw),
        "sensores_activos_totales": active_sensors_raw,
        "sensores_calibrados_totales": calibrated_sensors_raw,
        "sensores_observadores": observer_sensors,
        "anticipacion_activos": _as_int(quality.get("anticipacion_activos", 0) if isinstance(quality, dict) else zona.get("anticipacion_activos", 0)),
        "confirmacion_activos": _as_int(quality.get("confirmacion_activos", 0) if isinstance(quality, dict) else zona.get("confirmacion_activos", 0)),
        "estaciones_confirmando": confirming_stations,
        "estaciones_confirmando_lista": _pick_list(zona, "confirming_station_list", "estaciones_confirmando_lista"),
        "ratio_max": _as_float(_pick(zona, "ratio_max", None, 0), _ratio_max_from_sensors(sensors)),
        "effective_warning_seconds": 0,
        "feeds_esp32": True,
        "ultima_actualizacion": zona.get("updated_at") or zona.get("ultima_actualizacion") or local_data.get("updated_at") or local_data.get("ultima_actualizacion"),
    })
    cell["display_state_label"] = _display_state_label(raw_estado, confirming_stations, False)
    return _finish_cell(cell)


def _auto_cell_01(auto_data):
    cell = _base_cell("auto_cell_01", "Célula automática 1", "early_warning", AUTO_CELL_01_STATE_FILE)
    if not auto_data:
        return _finish_cell(cell)

    fresh, age = _is_fresh(auto_data.get("updated_at", auto_data.get("ultima_actualizacion")))
    sensors = _pick_dict(auto_data, "sensors", "sensores")
    quality = auto_data.get("network_quality", auto_data.get("calidad_red", {}))

    # Prefer top-level reader fields; if missing, use network_quality; if missing, count active/calibrated sensors.
    active_sensors = _pick(auto_data, "active_sensors", "sensores_activos")
    calibrated_sensors = _pick(auto_data, "calibrated_sensors", "sensores_calibrados")
    if active_sensors is None and isinstance(quality, dict):
        active_sensors = _pick(quality, "active_sensors", "sensores_activos")
    if calibrated_sensors is None and isinstance(quality, dict):
        calibrated_sensors = _pick(quality, "calibrated_sensors", "sensores_calibrados")
    if active_sensors is None:
        active_sensors = sum(1 for s in sensors.values() if _pick(s, "sensor_state", "estado_sensor", s.get("state")) in ("activo", "active"))
    if calibrated_sensors is None:
        calibrated_sensors = sum(1 for s in sensors.values() if _pick(s, "calibrated", "calibrado", False))

    direction_label = _best_direction_from_sensors(sensors)
    short_label = direction_label or auto_data.get("cell_id", "C1")
    raw_estado = auto_data.get("state", auto_data.get("estado", "normal"))

    cell.update({
        "cell_id": auto_data.get("cell_id", "auto_cell_01"),
        "label": auto_data.get("label") or short_label or auto_data.get("cell_id", "auto_cell"),
        "short_label": short_label,
        "direction_label": direction_label,
        "role": auto_data.get("role", "early_warning"),
        "fresh": fresh,
        "age_seconds": age,
        "raw_estado": raw_estado,
        "estado": _sanitize_level(raw_estado),
        "flag": bool(auto_data.get("flag", False)),
        "calidad_red": _quality_estado(quality),
        "sensores_activos": _as_int(active_sensors, 0),
        "sensores_calibrados": _as_int(calibrated_sensors, 0),
        "anticipacion_activos": _as_int(active_sensors, 0),
        "confirmacion_activos": 0,
        "estaciones_confirmando": _as_int(auto_data.get("confirming_stations", auto_data.get("estaciones_confirmando", 0))),
        "estaciones_confirmando_lista": auto_data.get("confirming_station_list", auto_data.get("estaciones_confirmando_lista", [])),
        "ratio_max": _ratio_max_from_sensors(sensors),
        "effective_warning_seconds": _as_float(_pick(auto_data, "effective_warning_seconds", "aviso_util", 0), _max_effective_warning(sensors)) or _max_effective_warning(sensors),
        "feeds_esp32": bool(auto_data.get("feeds_esp32", False)),
        "ultima_actualizacion": auto_data.get("updated_at", auto_data.get("ultima_actualizacion")),
    })
    return _finish_cell(cell)


def _build_display_cells(cells):
    ordered = sorted(
        cells,
        key=lambda c: (
            0 if c.get("cell_id") == "cell_00" else 1,
            -CLASS_RANK.get(c.get("cell_class"), 0),
            -_as_float(c.get("effective_warning_seconds", 0), 0),
            c.get("cell_id", ""),
        ),
    )
    display_cells = []
    for c in ordered:
        item = {
            "cell_id": c.get("cell_id"),
            "short_label": c.get("short_label") or c.get("cell_id"),
            "role": c.get("role"),
            "class": c.get("cell_class"),
            "class_label": c.get("cell_class_label"),
            "state": c.get("estado"),
            "state_label": c.get("display_state_label", "normal"),
            "fresh": c.get("fresh"),
            "sensors_active": _as_int(c.get("sensores_activos", 0), 0),
            "sensors_calibrated": _as_int(c.get("sensores_calibrados", 0), 0),
            "sensors_total_active": _as_int(c.get("sensores_activos_totales", c.get("sensores_activos", 0)), 0),
            "sensors_total_calibrated": _as_int(c.get("sensores_calibrados_totales", c.get("sensores_calibrados", 0)), 0),
            "observer_sensors": _as_int(c.get("sensores_observadores", 0), 0),
            "confirming": _as_int(c.get("estaciones_confirmando", 0), 0),
            "ratio_max": _as_float(c.get("ratio_max", 0), 0),
            "can_trigger_anticipation": bool(c.get("can_trigger_anticipation", False)),
        }
        if c.get("role") == "early_warning":
            item["warning_seconds"] = _as_float(c.get("effective_warning_seconds", 0), 0)
            item["direction_label"] = c.get("direction_label", "")
        display_cells.append(item)
    return display_cells


def build_multicell_state():
    import glob
    local_data = leer_json(LOCAL_STATE_FILE)
    runtime = leer_json(AUTO_CELLS_RUNTIME_FILE)

    local = _local_cell(local_data)
    auto_cells = []
    for state_path in sorted(glob.glob("runtime/auto_cell_*_state.json"))[:4]:
        auto_data = leer_json(state_path)
        if auto_data:
            auto_cells.append(_auto_cell_01(auto_data))
    cells = [local] + auto_cells

    active_cells = [c for c in cells if c.get("fresh") and _as_int(c.get("sensores_activos", 0)) > 0]
    active_early = [c for c in active_cells if c.get("role") == "early_warning" and c.get("can_raise_watch")]
    strong_cells = [c for c in active_cells if c.get("cell_class") == "strong_cell"]
    good_cells = [c for c in active_cells if c.get("cell_class") == "good_cell"]
    minimal_cells = [c for c in active_cells if c.get("cell_class") == "minimal_cell"]
    single_station_cells = [c for c in active_cells if c.get("cell_class") == "single_station"]
    blind_cells = [c for c in cells if c.get("cell_class") in ("stale_cell", "blind_zone")]

    strong_early = [c for c in active_early if c.get("cell_class") == "strong_cell"]
    good_early = [c for c in active_early if c.get("cell_class") == "good_cell"]
    minimal_early = [c for c in active_early if c.get("cell_class") == "minimal_cell"]
    trigger_capable_early = [c for c in active_early if c.get("can_trigger_anticipation")]

    total_active_sensors = sum(_as_int(c.get("sensores_activos", 0)) for c in active_cells)
    total_calibrated_sensors = sum(_as_int(c.get("sensores_calibrados", 0)) for c in active_cells)
    total_confirming_stations = sum(_as_int(c.get("estaciones_confirmando", 0)) for c in active_cells)
    ratio_max = round(max([_as_float(c.get("ratio_max", 0)) for c in active_cells] or [0]), 2)

    local_active = local in active_cells
    local_ok = local_active and local.get("cell_class") in ("strong_cell", "good_cell", "minimal_cell")

    if local_ok and strong_early:
        network_mode = "multicell"
        network_quality = "high_multicell"
        network_label = "red multicelda alta"
    elif local_ok and (good_early or minimal_early):
        network_mode = "multicell_partial"
        network_quality = "partial_multicell"
        network_label = "red multicelda parcial"
    elif local_ok:
        network_mode = "local_only"
        network_quality = local.get("calidad_red", "local")
        network_label = "red local activa"
    elif active_early:
        network_mode = "remote_only"
        network_quality = "remota_sin_local"
        network_label = "solo zona remota activa"
    elif active_cells:
        network_mode = "partial"
        network_quality = "parcial"
        network_label = "red parcial"
    else:
        network_mode = "degraded"
        network_quality = "degradada"
        network_label = "red degradada"

    # Conservative rule: a minimal cell does not trigger by itself. Strong/good cells can raise experimental anticipation if internally confirmed.
    early_flags = [
        c for c in trigger_capable_early
        if c.get("flag") and _as_int(c.get("estaciones_confirmando", 0)) >= 2
    ]
    minimal_watch_flags = [
        c for c in minimal_early
        if c.get("flag") and _as_int(c.get("estaciones_confirmando", 0)) >= 2
    ]

    local_esp32 = (local_data or {}).get("esp32", {})
    local_raw_sonar = bool(local_esp32.get("sonar", False))
    local_confirming = _as_int(local.get("estaciones_confirmando", 0), 0)
    local_flag = bool(local.get("fresh") and (local.get("flag") or local_raw_sonar))

    event_level = "normal"
    event_message = "normal multicelda" if network_mode.startswith("multicell") else "normal"
    sound = False
    buzzer_segundos = 0
    led_nivel = 0

    if local_flag:
        # Un solo sensor con pico no es urgente ni atención. Cuyum lo informa con lenguaje bajo y sin sonido.
        if local_raw_sonar:
            event_level = "confirmacion_local"
            event_message = _safe_message(local_esp32.get("mensaje"), local_confirming, sound=True)
            sound = True
            buzzer_segundos = _as_int(local_esp32.get("buzzer_segundos", 5), 5)
            led_nivel = _as_int(local_esp32.get("led_nivel", 3), 3)
        elif local_confirming >= 2:
            event_level = "vigilancia_local"
            event_message = "Señal local en verificación"
            sound = False
            buzzer_segundos = 0
            led_nivel = 1
        else:
            event_level = "observacion"
            event_message = "Señal aislada sin confirmación"
            sound = False
            buzzer_segundos = 0
            led_nivel = 0
    elif early_flags:
        cell = early_flags[0]
        event_level = "multicell_anticipation"
        event_message = f"{cell.get('short_label', cell.get('cell_id'))}: señal en verificación"
        sound = True
        buzzer_segundos = 5
        led_nivel = 2
    elif minimal_watch_flags:
        cell = minimal_watch_flags[0]
        event_level = "multicell_watch"
        event_message = f"{cell.get('short_label', cell.get('cell_id'))}: vigilancia de red"
        sound = False
        buzzer_segundos = 0
        led_nivel = 1

    display_cells = _build_display_cells(cells)
    display_status = _display_state_label(event_level, total_confirming_stations, sound)
    display_message = _safe_message(event_message, total_confirming_stations, sound)

    if OBSERVATION_MODE_NO_SOUND:
        if event_level != "normal":
            display_status = "observacion"
            display_message = "Señal detectada"
        sound = False
        buzzer_segundos = 0
        led_nivel = 1 if event_level != "normal" else 0

    return {
        "sistema": "Cuyum",
        "modo": "multicell_fusion_v1_2_display_cells",
        "experimental": True,
        "advertencia": "Red experimental. No reemplaza fuentes oficiales ni procedimientos institucionales.",
        "ultima_actualizacion": ahora_iso(),
        "cell_policy": {
            "strong_cell_min_sensors": 3,
            "good_cell_min_sensors": 2,
            "minimal_cell_min_sensors": 0,
            "single_station_min_sensors": 1,
            "minimal_cell_can_trigger_attention": False,
            "minimal_cell_can_raise_watch": False,
            "single_sensor_event_policy": "observacion_sin_sonido",
        },
        "display": {
            "title": "Cuyum v1.2",
            "network": network_label,
            "status": display_status,
            "message": display_message,
            "sound": sound,
            "cells": display_cells,
        },
        "display_cells": display_cells,
        "network": {
            "mode": network_mode,
            "quality": _english_code(network_quality),
            "label": network_label,
            "cells_configured": len(cells),
            "cells_active": len(active_cells),
            "early_warning_cells_active": len(active_early),
            "strong_cells": len(strong_cells),
            "good_cells": len(good_cells),
            "minimal_cells": len(minimal_cells),
            "single_station_cells": len(single_station_cells),
            "blind_or_stale_cells": len(blind_cells),
            "strong_early_warning_cells": len(strong_early),
            "good_early_warning_cells": len(good_early),
            "minimal_early_warning_cells": len(minimal_early),
            "trigger_capable_early_warning_cells": len(trigger_capable_early),
            "sensores_activos_total": total_active_sensors,
            "sensores_calibrados_total": total_calibrated_sensors,
            "estaciones_confirmando_total": total_confirming_stations,
            "total_active_sensors": total_active_sensors,
            "total_calibrated_sensors": total_calibrated_sensors,
            "total_confirming_stations": total_confirming_stations,
            "ratio_max": ratio_max,
        },
        "event": {
            "level": event_level,
            "message": display_message,
            "sonar": sound,
            "buzzer_segundos": buzzer_segundos,
            "led_nivel": led_nivel,
            "sound": sound,
            "buzzer_seconds": buzzer_segundos,
            "led_level": led_nivel,
            "early_flags": [c.get("cell_id") for c in early_flags],
            "minimal_watch_flags": [c.get("cell_id") for c in minimal_watch_flags],
        },
        "cells": {c["cell_id"]: c for c in cells},
        "runtime_cells_generated_at": (runtime or {}).get("generated_at"),
    }


def build_node_poll(node_id="node_01"):
    fused = build_multicell_state()
    net = fused["network"]
    event = fused["event"]
    cells = fused["cells"]
    display = fused.get("display", {})
    display_cells = fused.get("display_cells", [])
    local = cells.get("cell_00", {})
    auto01 = cells.get("auto_cell_01", {})

    respuesta = {
        # Campos viejos: el ESP32 actual no se rompe.
        "node_id": node_id,
        "level": event["level"],
        "message": event["message"],
        "sound": event.get("sound", event["sonar"]),
        "buzzer_seconds": event.get("buzzer_seconds", event["buzzer_segundos"]),
        "led_level": event.get("led_level", event["led_nivel"]),
        "network_quality": net["quality"],
        "active_sensors": net.get("total_active_sensors", net["sensores_activos_total"]),
        "calibrated_sensors": net.get("total_calibrated_sensors", net["sensores_calibrados_total"]),
        "total_confirming_stations": net.get("total_confirming_stations", net["estaciones_confirmando_total"]),
        "cell_00_active_sensors": local.get("active_sensors", local.get("sensores_activos", 0)),
        "auto_cell_01_active_sensors": auto01.get("active_sensors", auto01.get("sensores_activos", 0)),
        "auto_cell_01_warning_seconds": auto01.get("effective_warning_seconds", 0),

        "sonar": event["sonar"],
        "buzzer_segundos": event["buzzer_segundos"],
        "led_nivel": event["led_nivel"],
        "magnitud_estimada": 0,
        "nivel": event["level"],
        "mensaje": event["message"],
        "calidad_red": net["quality"],
        "sensores_activos": net["sensores_activos_total"],
        "sensores_calibrados": net["sensores_calibrados_total"],
        "anticipacion_activos": _as_int(local.get("anticipacion_activos", 0)) + sum(
            _as_int(c.get("sensores_activos", 0))
            for c in cells.values()
            if c.get("role") == "early_warning" and c.get("fresh") and c.get("can_raise_watch")
        ),
        "confirmacion_activos": _as_int(local.get("confirmacion_activos", 0)),
        "estaciones_confirmando": net["estaciones_confirmando_total"],
        "ratio_max": net["ratio_max"],
        "ultima_actualizacion": fused["ultima_actualizacion"],

        # Portable fields for ESP32 multicell compatibility.
        "display": display,
        "display_cells": display_cells,
        "display_status": display.get("status", event["level"]),
        "display_message": display.get("message", event["message"]),

        # New multicell fields: the current ESP32 sketch ignores them; the next sketch can display them.
        "network_mode": net["mode"],
        "network_label": net["label"],
        "cells_configured": net["cells_configured"],
        "cells_active": net["cells_active"],
        "early_warning_cells_active": net["early_warning_cells_active"],
        "strong_cells": net["strong_cells"],
        "good_cells": net["good_cells"],
        "minimal_cells": net["minimal_cells"],
        "single_station_cells": net["single_station_cells"],
        "blind_or_stale_cells": net["blind_or_stale_cells"],
        "strong_early_warning_cells": net["strong_early_warning_cells"],
        "good_early_warning_cells": net["good_early_warning_cells"],
        "minimal_early_warning_cells": net["minimal_early_warning_cells"],
        "trigger_capable_early_warning_cells": net["trigger_capable_early_warning_cells"],
        "multicell_message": event["message"],

        # Compatibilidad temporal: campos específicos existentes. No usarlos en firmware portable nuevo.
        "cell_00_estado": local.get("estado"),
        "cell_00_class": local.get("cell_class"),
        "cell_00_class_label": local.get("cell_class_label"),
        "cell_00_fresh": local.get("fresh"),
        "cell_00_sensores_activos": local.get("sensores_activos", 0),

        "auto_cell_01_estado": auto01.get("estado"),
        "auto_cell_01_class": auto01.get("cell_class"),
        "auto_cell_01_class_label": auto01.get("cell_class_label"),
        "auto_cell_01_fresh": auto01.get("fresh"),
        "auto_cell_01_sensores_activos": auto01.get("sensores_activos", 0),
        "auto_cell_01_aviso_util": auto01.get("effective_warning_seconds", 0),
    }
    return respuesta
