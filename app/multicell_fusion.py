import json
import os
from collections import Counter
from datetime import datetime, timezone

# Observation mode: detection is visible, but sound output is disabled.
OBSERVATION_MODE_NO_SOUND = True

LOCAL_STATE_FILE = "runtime/state_cell_00_seedlink.json"
AUTO_CELL_01_STATE_FILE = "runtime/auto_cell_01_state.json"

# Do not make this too aggressive: some readers write in batches.
# If this time is exceeded, the cell is not considered fresh for decisions.
MAX_CELL_AGE_SECONDS = 180

CELL_CLASS_LABELS = {
    "strong_cell": "strong",
    "good_cell": "good",
    "minimal_cell": "minimal",
    "single_station": "single station",
    "stale_cell": "no recent data",
    "blind_zone": "no coverage",
}

CLASS_RANK = {
    "strong_cell": 5,
    "good_cell": 4,
    "minimal_cell": 3,
    "single_station": 2,
    "blind_zone": 1,
    "stale_cell": 0,
}


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


def _quality_state(quality):
    if isinstance(quality, dict):
        return str(quality.get("state", "unknown"))
    if quality is None:
        return "unknown"
    return str(quality)


def _ratio_max_from_sensors(sensors):
    ratios = []
    for sensor in (sensors or {}).values():
        ratios.append(_as_float(sensor.get("ratio", 0), 0))
    return round(max(ratios), 2) if ratios else 0



def _english_code(value):
    return value


def _max_effective_warning(sensors):
    values = []
    for sensor in (sensors or {}).values():
        values.append(_as_float(sensor.get("effective_warning_seconds", 0), 0))
    return round(max(values), 1) if values else 0


def _best_direction_from_sensors(sensors):
    directions = []
    for sensor in (sensors or {}).values():
        d = str(sensor.get("direction", "")).strip().upper()
        if d and d not in ("NONE", "NULL", "?"):
            directions.append(d)
    if not directions:
        return ""
    # On ties, prefer the direction of the highest-priority sensor, which is usually the primary one.
    counts = Counter(directions)
    most_common = counts.most_common()
    if most_common and most_common[0][1] > 1:
        return most_common[0][0]
    for sensor in sorted((sensors or {}).values(), key=lambda x: _as_int(x.get("priority", 999), 999)):
        d = str(sensor.get("direction", "")).strip().upper()
        if d:
            return d
    return most_common[0][0] if most_common else ""


def _sanitize_level(level):
    """Never expose an urgent state from a single sensor. Use conservative wording."""
    value = str(level or "normal")
    low = value.lower()
    if "urgent" in low:
        return "observation"
    if low in ("local_attention", "attention", "high", "critical"):
        return "watch"
    return value


def _safe_message(message, confirming_stations=0, sound=False):
    """Safe display/node messages without urgent or technical-service wording."""
    msg = str(message or "normal")
    low = msg.lower()
    if "urgent" in low or "anomal" in low or "attention" in low:
        if sound:
            return "Signal under verification by the Cuyum network"
        if _as_int(confirming_stations, 0) >= 2:
            return "Local signal under verification"
        if _as_int(confirming_stations, 0) == 1:
            return "Isolated signal without confirmation"
        return "Network observation without confirmation"
    return msg


def _display_state_label(state, confirming_stations=0, sound=False):
    low = str(state or "normal").lower()
    if sound:
        return "warning"
    if "urgent" in low or "attention" in low or "anomal" in low:
        if _as_int(confirming_stations, 0) >= 2:
            return "verification"
        return "observation"
    if low in ("normal", "ok"):
        return "normal"
    return _sanitize_level(state)


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
        "state": "no_state",
        "raw_state": "no_state",
        "display_state_label": "no data",
        "flag": False,
        "network_quality": "no_state",
        "active_sensors": 0,
        "calibrated_sensors": 0,
        "anticipation_active": 0,
        "confirmation_active": 0,
        "confirming_stations": 0,
        "confirming_station_list": [],
        "ratio_max": 0,
        "effective_warning_seconds": 0,
        "cell_class": "stale_cell",
        "cell_class_label": CELL_CLASS_LABELS["stale_cell"],
        "can_raise_watch": False,
        "can_trigger_anticipation": False,
        "feeds_esp32": False,
        "updated_at": None,
    }


def _finish_cell(cell):
    cell_class = classify_cell(cell.get("active_sensors", 0), cell.get("fresh", False))
    cell["cell_class"] = cell_class
    cell["cell_class_label"] = CELL_CLASS_LABELS.get(cell_class, cell_class)
    cell["can_raise_watch"] = cell_can_raise_watch(cell_class)
    cell["can_trigger_anticipation"] = cell_can_trigger_anticipation(cell_class)
    cell["display_state_label"] = _display_state_label(
        cell.get("state"), cell.get("confirming_stations", 0), False
    )

    cell["state"] = cell.get("state")
    cell["active_sensors"] = _as_int(cell.get("active_sensors", cell.get("active_sensors", 0)), 0)
    cell["calibrated_sensors"] = _as_int(cell.get("calibrated_sensors", 0), 0)
    cell["confirming_stations"] = _as_int(cell.get("confirming_stations", cell.get("confirming_stations", 0)), 0)
    cell["confirming_station_list"] = cell.get("confirming_station_list", [])
    cell["network_quality"] = _english_code(cell.get("network_quality"))

    return cell


def _local_cell(local_data):
    cell = _base_cell("cell_00", "Local / control", "local_control", LOCAL_STATE_FILE)
    if not local_data:
        return _finish_cell(cell)

    zone = (local_data or {}).get("zones", {}).get("local_adaptive_zone", {})
    if not zone:
        # Flat state input.
        zone = local_data or {}

    quality = zone.get("network_quality", {})
    fresh, age = _is_fresh(zone.get("updated_at") or local_data.get("updated_at"))
    sensors = _pick_dict(zone, "sensors")
    raw_state = zone.get("state", (local_data.get("esp32", {}) or {}).get("level", "no_state"))
    confirming_stations = _as_int(zone.get("confirming_stations", 0), 0)

    active_sensor_items = [
        s for s in sensors.values()
        if s.get("sensor_state", s.get("state")) == "active"
    ]
    calibrated_sensor_items = [
        s for s in sensors.values()
        if s.get("calibrated", False)
    ]
    validating_sensor_items = [
        s for s in active_sensor_items
        if bool(s.get("can_confirm", False))
        or bool(s.get("can_trigger", False))
    ]
    observer_sensor_items = [
        s for s in active_sensor_items
        if s not in validating_sensor_items
    ]

    active_sensors_raw = _as_int(
        zone.get(
            "active_sensors",
            quality.get("active_sensors", 0) if isinstance(quality, dict) else 0
        ),
        0
    )
    calibrated_sensors_raw = _as_int(
        zone.get(
            "calibrated_sensors",
            quality.get("calibrated_sensors", 0) if isinstance(quality, dict) else 0
        ),
        0
    )

    validating_sensors = len(validating_sensor_items) if active_sensor_items else active_sensors_raw
    observer_sensors = len(observer_sensor_items) if active_sensor_items else 0

    cell.update({
        "fresh": fresh,
        "age_seconds": age,
        "raw_state": raw_state,
        "state": _sanitize_level(raw_state),
        "flag": bool(zone.get("flag", False)),
        "network_quality": _quality_state(quality),
        "active_sensors": validating_sensors,
        "calibrated_sensors": min(validating_sensors, calibrated_sensors_raw),
        "total_active_sensors": active_sensors_raw,
        "total_calibrated_sensors": calibrated_sensors_raw,
        "observer_sensors": observer_sensors,
        "anticipation_active": _as_int(quality.get("anticipation_active", 0) if isinstance(quality, dict) else zone.get("anticipation_active", 0)),
        "confirmation_active": _as_int(quality.get("confirmation_active", 0) if isinstance(quality, dict) else zone.get("confirmation_active", 0)),
        "confirming_stations": confirming_stations,
        "confirming_station_list": zone.get("confirming_station_list", []),
        "ratio_max": _as_float(_pick(zone, "ratio_max", None, 0), _ratio_max_from_sensors(sensors)),
        "effective_warning_seconds": 0,
        "feeds_esp32": True,
        "updated_at": zone.get("updated_at") or local_data.get("updated_at"),
    })
    cell["display_state_label"] = _display_state_label(raw_state, confirming_stations, False)
    return _finish_cell(cell)


def _auto_cell_01(auto_data):
    cell = _base_cell("auto_cell_01", "Automatic cell 1", "early_warning", AUTO_CELL_01_STATE_FILE)
    if not auto_data:
        return _finish_cell(cell)

    fresh, age = _is_fresh(auto_data.get("updated_at"))
    sensors = _pick_dict(auto_data, "sensors")
    quality = auto_data.get("network_quality", {})

    # Prefer top-level reader fields; if missing, use network_quality; if missing, count active/calibrated sensors.
    active_sensors = auto_data.get("active_sensors")
    calibrated_sensors = auto_data.get("calibrated_sensors")
    if active_sensors is None and isinstance(quality, dict):
        active_sensors = quality.get("active_sensors")
    if calibrated_sensors is None and isinstance(quality, dict):
        calibrated_sensors = quality.get("calibrated_sensors")
    if active_sensors is None:
        active_sensors = sum(1 for s in sensors.values() if s.get("sensor_state", s.get("state")) == "active")
    if calibrated_sensors is None:
        calibrated_sensors = sum(1 for s in sensors.values() if s.get("calibrated", False))

    direction_label = _best_direction_from_sensors(sensors)
    short_label = direction_label or auto_data.get("cell_id", "C1")
    raw_state = auto_data.get("state", "normal")

    cell.update({
        "cell_id": auto_data.get("cell_id", "auto_cell_01"),
        "label": auto_data.get("label") or short_label or auto_data.get("cell_id", "auto_cell"),
        "short_label": short_label,
        "direction_label": direction_label,
        "role": auto_data.get("role", "early_warning"),
        "fresh": fresh,
        "age_seconds": age,
        "raw_state": raw_state,
        "state": _sanitize_level(raw_state),
        "flag": bool(auto_data.get("flag", False)),
        "network_quality": _quality_state(quality),
        "active_sensors": _as_int(active_sensors, 0),
        "calibrated_sensors": _as_int(calibrated_sensors, 0),
        "anticipation_active": _as_int(active_sensors, 0),
        "confirmation_active": 0,
        "confirming_stations": _as_int(auto_data.get("confirming_stations", 0)),
        "confirming_station_list": auto_data.get("confirming_station_list", []),
        "ratio_max": _ratio_max_from_sensors(sensors),
        "effective_warning_seconds": _as_float(auto_data.get("effective_warning_seconds", 0), _max_effective_warning(sensors)) or _max_effective_warning(sensors),
        "feeds_esp32": bool(auto_data.get("feeds_esp32", False)),
        "updated_at": auto_data.get("updated_at"),
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
            "state": c.get("state"),
            "state_label": c.get("display_state_label", "normal"),
            "fresh": c.get("fresh"),
            "sensors_active": _as_int(c.get("active_sensors", 0), 0),
            "sensors_calibrated": _as_int(c.get("calibrated_sensors", 0), 0),
            "sensors_total_active": _as_int(c.get("total_active_sensors", c.get("active_sensors", 0)), 0),
            "sensors_total_calibrated": _as_int(c.get("total_calibrated_sensors", c.get("calibrated_sensors", 0)), 0),
            "observer_sensors": _as_int(c.get("observer_sensors", 0), 0),
            "confirming": _as_int(c.get("confirming_stations", 0), 0),
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
    local_data = read_json(LOCAL_STATE_FILE)

    local = _local_cell(local_data)
    auto_cells = []
    for state_path in sorted(glob.glob("runtime/auto_cell_*_state.json"))[:4]:
        auto_data = read_json(state_path)
        if auto_data:
            auto_cells.append(_auto_cell_01(auto_data))
    cells = [local] + auto_cells

    active_cells = [c for c in cells if c.get("fresh") and _as_int(c.get("active_sensors", 0)) > 0]
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

    total_active_sensors = sum(_as_int(c.get("active_sensors", 0)) for c in active_cells)
    total_calibrated_sensors = sum(_as_int(c.get("calibrated_sensors", 0)) for c in active_cells)
    total_confirming_stations = sum(_as_int(c.get("confirming_stations", 0)) for c in active_cells)
    ratio_max = round(max([_as_float(c.get("ratio_max", 0)) for c in active_cells] or [0]), 2)

    local_active = local in active_cells
    local_ok = local_active and local.get("cell_class") in ("strong_cell", "good_cell", "minimal_cell")

    if local_ok and strong_early:
        network_mode = "multicell"
        network_quality = "high_multicell"
        network_label = "high multicell network"
    elif local_ok and (good_early or minimal_early):
        network_mode = "multicell_partial"
        network_quality = "partial_multicell"
        network_label = "partial multicell network"
    elif local_ok:
        network_mode = "local_only"
        network_quality = local.get("network_quality", "local")
        network_label = "active local network"
    elif active_early:
        network_mode = "remote_only"
        network_quality = "remote_without_local"
        network_label = "remote zone only"
    elif active_cells:
        network_mode = "partial"
        network_quality = "partial"
        network_label = "partial network"
    else:
        network_mode = "degraded"
        network_quality = "degraded"
        network_label = "degraded network"

    # Conservative rule: a minimal cell does not trigger by itself. Strong/good cells can raise experimental anticipation if internally confirmed.
    early_flags = [
        c for c in trigger_capable_early
        if c.get("flag") and _as_int(c.get("confirming_stations", 0)) >= 2
    ]
    minimal_watch_flags = [
        c for c in minimal_early
        if c.get("flag") and _as_int(c.get("confirming_stations", 0)) >= 2
    ]

    local_esp32 = (local_data or {}).get("esp32", {})
    local_raw_sound = bool(local_esp32.get("sound", False))
    local_confirming = _as_int(local.get("confirming_stations", 0), 0)
    local_flag = bool(local.get("fresh") and (local.get("flag") or local_raw_sound))

    event_level = "normal"
    event_message = "normal multicell" if network_mode.startswith("multicell") else "normal"
    sound = False
    buzzer_seconds = 0
    led_level = 0

    if local_flag:
        # A single sensor peak is neither urgent nor an attention state. Report it quietly and without sound.
        if local_raw_sound:
            event_level = "local_confirmation"
            event_message = _safe_message(local_esp32.get("message"), local_confirming, sound=True)
            sound = True
            buzzer_seconds = _as_int(local_esp32.get("buzzer_seconds", 5), 5)
            led_level = _as_int(local_esp32.get("led_level", 3), 3)
        elif local_confirming >= 2:
            event_level = "local_watch"
            event_message = "Local signal under verification"
            sound = False
            buzzer_seconds = 0
            led_level = 1
        else:
            event_level = "observation"
            event_message = "Isolated signal without confirmation"
            sound = False
            buzzer_seconds = 0
            led_level = 0
    elif early_flags:
        cell = early_flags[0]
        event_level = "multicell_anticipation"
        event_message = f"{cell.get('short_label', cell.get('cell_id'))}: signal under verification"
        sound = True
        buzzer_seconds = 5
        led_level = 2
    elif minimal_watch_flags:
        cell = minimal_watch_flags[0]
        event_level = "multicell_watch"
        event_message = f"{cell.get('short_label', cell.get('cell_id'))}: network watch"
        sound = False
        buzzer_seconds = 0
        led_level = 1

    display_cells = _build_display_cells(cells)
    display_status = _display_state_label(event_level, total_confirming_stations, sound)
    display_message = _safe_message(event_message, total_confirming_stations, sound)

    if OBSERVATION_MODE_NO_SOUND:
        if event_level != "normal":
            display_status = "observation"
            display_message = "Signal detected"
        sound = False
        buzzer_seconds = 0
        led_level = 1 if event_level != "normal" else 0

    return {
        "system": "Cuyum",
        "mode": "multicell_fusion_v1_3_display_cells",
        "experimental": True,
        "warning": "Experimental network. It does not replace official sources or institutional procedures.",
        "updated_at": now_iso(),
        "cell_policy": {
            "strong_cell_min_sensors": 3,
            "good_cell_min_sensors": 2,
            "minimal_cell_min_sensors": 0,
            "single_station_min_sensors": 1,
            "minimal_cell_can_trigger_attention": False,
            "minimal_cell_can_raise_watch": False,
            "single_sensor_event_policy": "observation_no_sound",
        },
        "display": {
            "title": "Cuyum 1.3",
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
            "total_active_sensors": total_active_sensors,
            "total_calibrated_sensors": total_calibrated_sensors,
            "total_confirming_stations": total_confirming_stations,
            "ratio_max": ratio_max,
        },
        "event": {
            "level": event_level,
            "message": display_message,
            "sound": sound,
            "buzzer_seconds": buzzer_seconds,
            "led_level": led_level,
            "early_flags": [c.get("cell_id") for c in early_flags],
            "minimal_watch_flags": [c.get("cell_id") for c in minimal_watch_flags],
        },
        "cells": {c["cell_id"]: c for c in cells},
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

    early_flag_ids = set(
        event.get("early_flags", []) or []
    )

    attention_cell = None

    for cell in display_cells:
        if cell.get("cell_id") in early_flag_ids:
            attention_cell = cell
            break

    if attention_cell is None:
        confirming_cells = [
            cell
            for cell in display_cells
            if int(cell.get("confirming", 0) or 0) > 0
        ]

        if confirming_cells:
            attention_cell = max(
                confirming_cells,
                key=lambda cell: int(
                    cell.get("confirming", 0) or 0
                ),
            )

    attention_direction = ""
    attention_direction_label = ""
    attention_confirming = 0

    if attention_cell is not None:
        attention_direction = str(
            attention_cell.get("direction")
            or attention_cell.get("short_label")
            or attention_cell.get("cell_id")
            or ""
        )

        attention_direction_label = str(
            attention_cell.get("direction_label")
            or attention_cell.get("short_label")
            or attention_direction
        )

        attention_confirming = int(
            attention_cell.get("confirming", 0) or 0
        )

    if attention_confirming <= 0:
        attention_confirming = int(
            net.get("total_confirming_stations", 0) or 0
        )

    response = {
        # Canonical node payload.
        "node_id": node_id,
        "level": event["level"],
        "message": event["message"],
        "sound": event["sound"],
        "buzzer_seconds": event["buzzer_seconds"],
        "led_level": event["led_level"],
        "network_quality": net["quality"],
        "active_sensors": net["total_active_sensors"],
        "calibrated_sensors": net["total_calibrated_sensors"],
        "total_confirming_stations": net["total_confirming_stations"],
        "cell_00_active_sensors": local.get("active_sensors", 0),
        "auto_cell_01_active_sensors": auto01.get("active_sensors", 0),
        "auto_cell_01_warning_seconds": auto01.get("effective_warning_seconds", 0),
        "ratio_max": net["ratio_max"],

        "attention": {
            "active": bool(event["sound"]),
            "direction": attention_direction,
            "direction_label": attention_direction_label,
            "confirming_sensors": attention_confirming,
        },

        # Multicell display fields.
        "display": display,
        "display_cells": display_cells,
        "display_status": display.get("status", event["level"]),
        "display_message": display.get("message", event["message"]),

        # Multicell network fields.
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

        # Cell-specific diagnostic fields.
        "cell_00_class": local.get("cell_class"),
        "cell_00_class_label": local.get("cell_class_label"),
        "cell_00_fresh": local.get("fresh"),

        "auto_cell_01_class": auto01.get("cell_class"),
        "auto_cell_01_class_label": auto01.get("cell_class_label"),
        "auto_cell_01_fresh": auto01.get("fresh"),
    }
    return response
