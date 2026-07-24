from pathlib import Path

path = Path("multicell_fusion.py")
text = path.read_text(encoding="utf-8")
original = text

helpers = r'''
def _to_english_code(value):
    mapping = {
        "multicelda_fuerte": "high_multicell",
        "multicelda_parcial": "partial_multicell",
        "remota_sin_local": "remote_only",
        "degradada": "degraded",
        "buena": "good",
        "desconocida": "unknown",
        "sin_estado": "no_state",
        "observacion_sin_sonido": "observation_without_sound",
    }
    return mapping.get(value, value)


def _normalize_cell_aliases(cell):
    if not isinstance(cell, dict):
        return cell

    pairs = [
        ("active_sensors", "sensores_activos"),
        ("calibrated_sensors", "sensores_calibrados"),
        ("confirming_stations", "estaciones_confirmando"),
        ("confirming_station_list", "estaciones_confirmando_lista"),
        ("network_quality", "calidad_red"),
    ]

    for english_key, legacy_key in pairs:
        if english_key not in cell and legacy_key in cell:
            cell[english_key] = cell.get(legacy_key)

    if "network_quality" in cell:
        cell["network_quality"] = _to_english_code(cell.get("network_quality"))

    return cell


def _normalize_network_aliases(network):
    if not isinstance(network, dict):
        return network

    pairs = [
        ("total_active_sensors", "sensores_activos_total"),
        ("total_calibrated_sensors", "sensores_calibrados_total"),
        ("total_confirming_stations", "estaciones_confirmando_total"),
        ("sound", "sonar"),
    ]

    for english_key, legacy_key in pairs:
        if english_key not in network and legacy_key in network:
            network[english_key] = network.get(legacy_key)

    if "quality" in network:
        network["quality"] = _to_english_code(network.get("quality"))

    policy = network.get("policy")
    if isinstance(policy, dict) and "single_sensor_event_policy" in policy:
        policy["single_sensor_event_policy"] = _to_english_code(policy.get("single_sensor_event_policy"))

    return network


def _normalize_poll_aliases(poll):
    if not isinstance(poll, dict):
        return poll

    pairs = [
        ("level", "nivel"),
        ("message", "mensaje"),
        ("network_quality", "calidad_red"),
        ("active_sensors", "sensores_activos"),
        ("calibrated_sensors", "sensores_calibrados"),
        ("sound", "sonar"),
        ("buzzer_seconds", "buzzer_segundos"),
        ("led_level", "led_nivel"),
        ("cell_00_active_sensors", "cell_00_sensores_activos"),
        ("auto_cell_01_active_sensors", "auto_cell_01_sensores_activos"),
        ("auto_cell_01_warning_seconds", "auto_cell_01_aviso_util"),
    ]

    for english_key, legacy_key in pairs:
        if english_key not in poll and legacy_key in poll:
            poll[english_key] = poll.get(legacy_key)

    if "network_quality" in poll:
        poll["network_quality"] = _to_english_code(poll.get("network_quality"))

    return poll
'''

if "def _normalize_cell_aliases" not in text:
    marker = "def _legacy_network_quality"
    idx = text.find(marker)
    if idx == -1:
        marker = "def _pick"
        idx = text.find(marker)
    if idx == -1:
        raise SystemExit("insert marker not found")
    text = text[:idx] + helpers + "\n\n" + text[idx:]

text = text.replace("return cell", "return _normalize_cell_aliases(cell)")
text = text.replace('"network": network,', '"network": _normalize_network_aliases(network),')
text = text.replace("return poll", "return _normalize_poll_aliases(poll)")

if text != original:
    path.write_text(text, encoding="utf-8")
    print("updated multicell_fusion.py")
else:
    print("no changes")
