#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

PYTHONPATH=app python3 - <<'PY'
from multicell_fusion import build_node_poll, build_multicell_state

def safe(data, key, default="-"):
    if isinstance(data, dict):
        value = data.get(key, default)
        return default if value is None else value
    return default

poll = build_node_poll("node_01")
state = build_multicell_state()

network = state.get("network", {})
cells = state.get("cells", {})
display_cells = poll.get("display_cells", [])

print("==============================================")
print("        CUYUM 1.3 - MULTICELL STATUS")
print("==============================================")
print()

print("Network")
print(f"- level: {safe(poll, 'level')}")
print(f"- mode: {safe(network, 'mode')}")
print(f"- quality: {safe(network, 'quality')}")
print(f"- cells_active: {safe(network, 'cells_active')}")
print(f"- cells_configured: {safe(poll, 'cells_configured')}")
print(f"- total_active_sensors: {safe(network, 'total_active_sensors')}")
print(f"- total_calibrated_sensors: {safe(network, 'total_calibrated_sensors')}")
print(f"- sound: {safe(poll, 'sound')}")
print(f"- buzzer_seconds: {safe(poll, 'buzzer_seconds')}")
print(f"- ratio_max: {safe(network, 'ratio_max')}")
print()

print("Cells")
for cell in display_cells:
    print(
        f"- {safe(cell, 'cell_id')}: "
        f"class={safe(cell, 'class')} "
        f"fresh={safe(cell, 'fresh')} "
        f"active={safe(cell, 'sensors_active')} "
        f"calibrated={safe(cell, 'sensors_calibrated')} "
        f"warning_seconds={safe(cell, 'warning_seconds')}"
    )

print()

print("Cell details")
for cell_id in sorted(cells.keys()):
    cell = cells[cell_id]
    print(
        f"- {cell_id}: "
        f"role={safe(cell, 'role')} "
        f"class={safe(cell, 'cell_class')} "
        f"fresh={safe(cell, 'fresh')} "
        f"active={safe(cell, 'active_sensors')} "
        f"calibrated={safe(cell, 'calibrated_sensors')} "
        f"quality={safe(cell, 'network_quality')} "
        f"watch={safe(cell, 'can_raise_watch')} "
        f"trigger={safe(cell, 'can_trigger_anticipation')} "
        f"age_seconds={safe(cell, 'age_seconds')}"
    )

print()

print("Capability")
print(f"- strong_cells: {safe(network, 'strong_cells')}")
print(f"- good_cells: {safe(network, 'good_cells')}")
print(f"- minimal_cells: {safe(network, 'minimal_cells')}")
print(f"- single_station_cells: {safe(network, 'single_station_cells')}")
print(f"- early_warning_cells_active: {safe(network, 'early_warning_cells_active')}")
print(f"- trigger_capable_early_warning_cells: {safe(network, 'trigger_capable_early_warning_cells')}")
PY
