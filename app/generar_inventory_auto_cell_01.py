#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

SRC = Path('config/auto_inventory_cells.json')
DST = Path('config/auto_cell_01_inventory.json')
CELL_ID = 'auto_cell_01'


def split_code(code):
    parts = code.split('.')
    if len(parts) < 3:
        raise ValueError(f'Código inválido: {code}')
    return parts[0], parts[1], parts[2]


def main():
    if not SRC.exists():
        raise SystemExit('ERROR: no existe config/auto_inventory_cells.json. Ejecutá primero ./ejecutar_auto_celdas.sh')

    data = json.loads(SRC.read_text(encoding='utf-8'))
    cell = data.get('cells', {}).get(CELL_ID)
    if not cell:
        raise SystemExit(f'ERROR: no existe {CELL_ID} en config/auto_inventory_cells.json')

    if cell.get('status') not in {'strong_cell', 'minimum_cell', 'usable_for_live_cell'}:
        raise SystemExit(f'ERROR: {CELL_ID} no está viable. status={cell.get("status")}')

    primary = cell.get('primary', [])
    reserve = cell.get('reserve_or_context', [])

    sensors = []
    for idx, item in enumerate(primary, start=1):
        network, station, channel = split_code(item['code'])
        sensors.append({
            'network': network,
            'station': station,
            'channel': channel,
            'role': 'early_warning',
            'name': item.get('site') or item.get('code'),
            'distance_km': round(float(item.get('distance_from_home_km') or 0), 1),
            'priority': idx,
            'state': 'active',
            'can_trigger': True,
            'can_confirm': True,
            'source': item.get('source_role') or item.get('source') or 'auto_cells',
            'confirmed_latency_seconds': item.get('latency_seconds'),
            'confirmation_packets': item.get('packets'),
            'effective_warning_seconds': item.get('effective_warning_seconds'),
            'direction': item.get('direction'),
            'lat': item.get('lat'),
            'lon': item.get('lon')
        })

    reserve_out = []
    for item in reserve:
        try:
            network, station, channel = split_code(item['code'])
        except Exception:
            continue
        reserve_out.append({
            'network': network,
            'station': station,
            'channel': channel,
            'name': item.get('site') or item.get('code'),
            'state': 'reserve',
            'confirmed_latency_seconds': item.get('latency_seconds'),
            'confirmation_packets': item.get('packets'),
            'effective_warning_seconds': item.get('effective_warning_seconds'),
            'direction': item.get('direction'),
            'lat': item.get('lat'),
            'lon': item.get('lon')
        })

    out = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'description': 'Live inventory for auto_cell_01 parallel test. Does not modify the main system or ESP32.',
        'cell_id': CELL_ID,
        'label': cell.get('label'),
        'role': cell.get('role'),
        'status': cell.get('status'),
        'seedlink_server': 'rtserve.earthscope.org:18000',
        'server_name': 'EarthScope',
        'target_sensors': 6,
        'min_good_sensors': 5,
        'effective_warning_seconds_estimated': cell.get('effective_warning_seconds'),
        'center': cell.get('center'),
        'direction': cell.get('direction'),
        'sensors': sensors,
        'reserves': reserve_out
    }

    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Inventory written: {DST}')
    print(f'Primary sensors: {len(sensors)} | Reserves: {len(reserve_out)}')


if __name__ == '__main__':
    main()
