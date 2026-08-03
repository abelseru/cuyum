def clean_sensor(sensor):
    return {
        "sensor_id": sensor.get("sensor_id"),
        "cell_id": sensor.get("cell_id"),
        "cell_label": sensor.get("cell_label"),
        "name": sensor.get("name"),
        "locality": sensor.get("locality"),
        "network": sensor.get("network"),
        "station": sensor.get("station"),
        "channel": sensor.get("channel"),
        "role": sensor.get("role"),
        "state": sensor.get("state"),
        "calibrated": bool(sensor.get("calibrated")),
        "signal": bool(sensor.get("flag")),
        "latency_seconds": sensor.get("latency_seconds"),
        "ratio": sensor.get("ratio"),
        "distance_km": sensor.get("distance_km"),
        "location": {
            "available": bool(sensor.get("has_location")),
            "approx": bool(sensor.get("approx_location")),
            "source": sensor.get("location_source"),
            "lat": sensor.get("lat"),
            "lon": sensor.get("lon"),
        },
        "quality": {
            "confidence": sensor.get("confidence_state"),
            "operational": sensor.get("operational_state"),
            "label": sensor.get("quality_label"),
        },
    }


def clean_cell(cell):
    return {
        "cell_id": cell.get("cell_id"),
        "label": cell.get("label") or cell.get("short_label"),
        "role": cell.get("role"),
        "class": cell.get("class"),
        "class_label": cell.get("class_label"),
        "state": cell.get("state"),
        "state_label": cell.get("state_label"),
        "fresh": bool(cell.get("fresh")),
        "active_sensors": cell.get("sensors_active"),
        "calibrated_sensors": cell.get("sensors_calibrated"),
        "warning_seconds": cell.get("warning_seconds"),
        "direction_label": cell.get("direction_label"),
        "location": {
            "lat": cell.get("lat"),
            "lon": cell.get("lon"),
        },
    }


def build_public_v1(raw):
    display = raw.get("display") or {}
    alert = raw.get("alert") or {}
    network = raw.get("network") or {}

    cells = raw.get("display_cells") or raw.get("cells") or []
    sensors = raw.get("sensors") or []

    return {
        "system": "Cuyum",
        "version": "v1",
        "experimental": True,
        "updated_at": raw.get("updated_at"),
        "status": {
            "level": alert.get("level") or display.get("status") or "normal",
            "label": display.get("status") or "normal",
            "message": normalize_event_summary(display.get("message") or alert.get("message") or "no relevant signals"),
            "sound": bool(display.get("sound") or alert.get("sound")),
            "buzzer_seconds": alert.get("buzzer_seconds") or 0,
        },
        "poll": {
            "normal_ms": (raw.get("poll") or {}).get("normal_ms"),
            "attention_ms": (raw.get("poll") or {}).get("alert_ms"),
            "next_ms": (raw.get("poll") or {}).get("next_ms"),
        },
        "network": {
            "mode": network.get("mode"),
            "label": network.get("label"),
            "active_cells": network.get("cells_active"),
            "configured_cells": network.get("cells_configured"),
            "active_sensors": network.get("sensors_active"),
            "calibrated_sensors": network.get("sensors_calibrated"),
        },
        "map": raw.get("map") or {},
        "cells": [clean_cell(cell) for cell in cells],
        "sensors": [clean_sensor(sensor) for sensor in sensors],
        "notice": raw.get("notice"),
    }

def normalize_event_level(level):
    if level is None:
        return None

    value = str(level).strip()

    allowed = {
        "normal",
        "observation",
        "watch",
        "warning",
        "availability",
        "network_state",
        "shared_signal",
        "isolated_signal",
        "local_watch",
        "local_confirmation",
        "multicell_watch",
        "multicell_anticipation",
        "simulation",
    }

    return value if value in allowed else value


def normalize_event_summary(summary):
    if summary is None:
        return None
    return str(summary)


def clean_event(event):
    cell = event.get("cell") or {}
    sensor = event.get("sensor") or {}
    coords = sensor.get("coords") or {}
    location = sensor.get("location") or {}

    cell_id = event.get("cell_id") or cell.get("id")
    cell_label = event.get("cell_label") or cell.get("label")

    if cell_id == "cell_01":
        cell_id = "auto_cell_01"
        if not cell_label or cell_label == "Local":
            cell_label = "Anticipation cell"
    elif cell_id == "cell_00":
        cell_label = cell_label or "Local"
    sensor_id = event.get("sensor_id") or sensor.get("id")
    sensor_label = event.get("sensor_name") or sensor.get("name")
    station = event.get("station") or sensor.get("station")
    locality = event.get("locality") or sensor.get("locality")

    lat = event.get("lat")
    lon = event.get("lon")
    if lat is None:
        lat = sensor.get("lat")
    if lon is None:
        lon = sensor.get("lon")
    if lat is None:
        lat = coords.get("lat")
    if lon is None:
        lon = coords.get("lon")

    source = event.get("source") or "Cuyum"
    if str(source).lower() == "cuyum":
        source = "Cuyum"

    out = {
        "timestamp": event.get("timestamp"),
        "type": event.get("type"),
        "level": normalize_event_level(event.get("level") or event.get("public_level") or event.get("event_level")),
        "summary": normalize_event_summary(event.get("summary") or event.get("message")),
        "cell_id": cell_id,
        "sensor_id": sensor_id,
        "source": source,
        "sound": bool(event.get("sound", False)),
        "buzzer_seconds": event.get("buzzer_seconds") or 0,
    }

    if cell_label:
        out["cell_label"] = cell_label
    if sensor_label:
        out["sensor_label"] = sensor_label
    if station:
        out["station"] = station
    if locality:
        out["locality"] = locality

    if lat is not None and lon is not None:
        out["location_available"] = True
        out["lat"] = lat
        out["lon"] = lon
    else:
        out["location_available"] = False

    location_source = event.get("location_source") or location.get("source") or sensor.get("location_source")
    if location_source:
        out["location_source"] = location_source

    approx_location = event.get("approx_location")
    if approx_location is None:
        approx_location = location.get("approx")
    if approx_location is None:
        approx_location = sensor.get("approx_location")
    if approx_location is not None:
        out["approx_location"] = bool(approx_location)

    if event.get("type") in {"system_decision", "sound_alert"} and not sensor_id:
        out["scope"] = "network"

    system = event.get("system") or {}

    if event.get("type") == "sound_alert":
        out["event_level"] = system.get("event_level")
        out["cells_active"] = system.get("cells_active")
        out["sensors_active"] = system.get("sensors_active")
        out["buzzer_seconds"] = system.get(
            "buzzer_seconds",
            out.get("buzzer_seconds", 0),
        )

    multisignal = event.get("multisignal") or {}

    if event.get("type") == "multisignal":
        for key in (
            "record_id",
            "direction",
            "direction_label",
            "warning_seconds",
        ):
            value = multisignal.get(key)

            if value is not None:
                out[key] = value

    signal = event.get("signal") or {}

    for key in ("ratio_max", "companions", "judgement"):
        value = event.get(key)

        if value is None:
            value = signal.get(key)

        if value is not None:
            out[key] = value

    return out


def build_events_v1(raw):
    events = raw.get("events") if isinstance(raw, dict) else []

    clean_events = []
    for event in events or []:
        if isinstance(event, dict):
            clean_events.append(clean_event(event))

    return {
        "system": "Cuyum",
        "version": "v1",
        "experimental": True,
        "updated_at": raw.get("updated_at") if isinstance(raw, dict) else None,
        "timezone": "UTC",
        "timestamps_format": "ISO 8601",
        "comparison_policy": "manual_external",
        "retention_days": raw.get("retention_days") if isinstance(raw, dict) else None,
        "count": len(clean_events),
        "description": "Recent public observations and events generated automatically by Cuyum.",
        "notice": (
            "All timestamps in this record are expressed in UTC. "
            "Observations are generated automatically by Cuyum and do not "
            "constitute official seismic confirmation. Any comparison with "
            "competent authority records must be performed externally and "
            "under the responsibility of the person conducting it."
        ),
        "events": clean_events,
    }
