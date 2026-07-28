#!/usr/bin/env python3
import json
import math
from statistics import median
from datetime import datetime, timezone
from pathlib import Path
import sys
from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient

BASELINE_PACKETS = 5
FLAG_FACTOR = 2.5
STRONG_FLAG_FACTOR = 4.0
EVENT_WINDOW_SECONDS = 10
MAX_LATENCY_SECONDS = 20
PREVIOUS_BASELINE_WEIGHT = 0.97
NEW_ENERGY_WEIGHT = 0.03


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def energy_simple(trace):
    data = trace.data
    if data is None or len(data) == 0:
        return 0.0
    return sum(abs(float(x)) for x in data) / len(data)


def experimental_magnitude(energy):
    if energy <= 0:
        return 0.0
    return round(math.log10(energy + 1), 2)


def extract_trace_key(trace_id):
    parts = trace_id.split('.')
    if len(parts) < 4:
        return trace_id
    return f'{parts[0]}.{parts[1]}.{parts[3]}'


def sensor_config_key(sensor):
    return f"{sensor['network']}.{sensor['station']}.{sensor['channel']}"


def load_inventory(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    server = data.get('seedlink_server') or 'rtserve.earthscope.org:18000'
    sensors = []
    for s in data.get('sensors', []):
        if s.get('state') in ['disabled', 'down', 'suspect']:
            continue
        sensors.append(s)
    return server, sensors, data


def calculate_network_quality(sensor_states, minimum=5):
    sensors = list(sensor_states.values())
    calibrated = [
        s for s in sensors
        if s.get('calibrated', False)
    ]
    active = [
        s for s in calibrated
        if s.get('sensor_state') == 'active'
    ]
    total = len(active)
    if total >= 6:
        state = 'strong'
    elif total >= minimum:
        state = 'minimum_viable'
    elif total >= 3:
        state = 'weak_context'
    elif total >= 1:
        state = 'insufficient'
    else:
        state = 'no_data'
    return {
        'state': state,
        'active_sensors': total,
        'calibrated_sensors': len(calibrated),
        'min_good_sensors': minimum
    }


def event_level_from_flags(flags):
    count = len(flags)
    strong = any(x.get('strong_flag') for x in flags.values())
    if count >= 3:
        return 'external_observation_strong'
    if count >= 2:
        return 'external_observation'
    if count == 1 and strong:
        return 'external_observation'
    if count == 1:
        return 'isolated_activity'
    return 'normal'


class AutoCellReader(EasySeedLinkClient):
    def __init__(self, server, sensors, inventory, output_path):
        super().__init__(server)
        self.server = server
        self.sensors = sensors
        self.inventory = inventory
        self.output_path = Path(output_path)
        self.cell_id = inventory.get('cell_id', 'auto_cell_01')
        self.label = inventory.get('label', self.cell_id)
        self.baseline_history = {}
        self.base = {}
        self.sensor_states = {}
        self.recent_flags = {}
        self.sensor_map = {sensor_config_key(s): s for s in sensors}

    def on_data(self, trace):
        key = extract_trace_key(trace.id)
        if key not in self.sensor_map:
            return
        cfg = self.sensor_map[key]
        energy = energy_simple(trace)
        magnitude = experimental_magnitude(energy)
        now = UTCDateTime()
        latency = float(now - trace.stats.endtime)

        if latency > MAX_LATENCY_SECONDS:
            self.sensor_states[key] = self.base_state(trace.id, key, cfg, 'high_latency', False, latency, energy, magnitude)
            self.write_state()
            print(f'DISCARDED {trace.id} latency={round(latency, 1)}s')
            return

        self.baseline_history.setdefault(key, []).append(energy)
        calibrated = key in self.base
        if not calibrated:
            if len(self.baseline_history[key]) >= BASELINE_PACKETS:
                self.base[key] = median(self.baseline_history[key][-BASELINE_PACKETS:])
                calibrated = True
                print('BASELINE DEFINED:', key, 'baseline=', round(self.base[key], 2))
            else:
                st = self.base_state(trace.id, key, cfg, 'calibrating', False, latency, energy, magnitude)
                st['baseline_packets'] = len(self.baseline_history[key])
                st['baseline_packets_required'] = BASELINE_PACKETS
                self.sensor_states[key] = st
                self.write_state()
                print(f'CALIBRATING {trace.id} {len(self.baseline_history[key])}/{BASELINE_PACKETS}')
                return

        sensor_baseline = self.base[key]
        ratio = energy / sensor_baseline if sensor_baseline > 0 else 0
        flag = ratio >= FLAG_FACTOR
        strong_flag = ratio >= STRONG_FLAG_FACTOR

        if not flag:
            self.base[key] = self.base[key] * PREVIOUS_BASELINE_WEIGHT + energy * NEW_ENERGY_WEIGHT

        if flag:
            self.recent_flags[cfg['station']] = {
                'key': key,
                'trace_id': trace.id,
                'station': cfg['station'],
                'name': cfg.get('name', key),
                'distance_km': cfg.get('distance_km'),
                'current_energy': round(energy, 2),
                'baseline_energy': round(sensor_baseline, 2),
                'ratio': round(ratio, 2),
                'estimated_magnitude': magnitude,
                'strong_flag': strong_flag,
                'timestamp': float(now.timestamp),
                'updated_at': now_iso()
            }

        self.sensor_states[key] = {
            'trace_id': trace.id,
            'key': key,
            'network': cfg['network'],
            'station': cfg['station'],
            'channel': cfg['channel'],
            'role': cfg.get('role', 'early_warning'),
            'name': cfg.get('name', key),
            'distance_km': cfg.get('distance_km'),
            'priority': cfg.get('priority'),
            'sensor_state': 'active',
            'calibrated': True,
            'current_energy': round(energy, 2),
            'baseline_energy': round(self.base[key], 2),
            'ratio': round(ratio, 2),
            'estimated_magnitude': magnitude,
            'flag': flag,
            'strong_flag': strong_flag,
            'latency_seconds': round(latency, 1),
            'effective_warning_seconds': cfg.get('effective_warning_seconds'),
            'direction': cfg.get('direction'),
            'updated_at': now_iso()
        }
        self.clear_expired_flags(float(now.timestamp))
        self.write_state()
        print(f'{trace.id} energy={round(energy,2)} base={round(sensor_baseline,2)} ratio={round(ratio,2)} flag={flag} strong={strong_flag}')

    def base_state(self, trace_id, key, cfg, state, calibrated, latency, energy, magnitude):
        return {
            'trace_id': trace_id,
            'key': key,
            'network': cfg['network'],
            'station': cfg['station'],
            'channel': cfg['channel'],
            'role': cfg.get('role', 'early_warning'),
            'name': cfg.get('name', key),
            'distance_km': cfg.get('distance_km'),
            'sensor_state': state,
            'calibrated': calibrated,
            'current_energy': round(energy, 2),
            'estimated_magnitude': magnitude,
            'flag': False,
            'strong_flag': False,
            'latency_seconds': round(latency, 1),
            'effective_warning_seconds': cfg.get('effective_warning_seconds'),
            'direction': cfg.get('direction'),
            'updated_at': now_iso()
        }

    def clear_expired_flags(self, now_ts):
        for station in list(self.recent_flags.keys()):
            if now_ts - self.recent_flags[station]['timestamp'] > EVENT_WINDOW_SECONDS:
                del self.recent_flags[station]

    def write_state(self):
        quality = calculate_network_quality(self.sensor_states, self.inventory.get('min_good_sensors', 5))
        level = event_level_from_flags(self.recent_flags)
        output = {
            'cell_id': self.cell_id,
            'label': self.label,
            'role': self.inventory.get('role', 'early_warning'),
            'mode': 'auto_cell_parallel_seedlink_reader',
            'experimental': True,
            'feeds_esp32': False,
            'notice': 'Parallel test. Does not modify the main server or ESP32.',
            'seedlink_server': self.server,
            'inventory_file': self.inventory.get('_inventory_path'),
            'updated_at': now_iso(),
            'state': level,
            'flag': level != 'normal',
            'network_quality': quality,
            'total_sensors': len(self.sensors),
            'active_sensors': quality['active_sensors'],
            'calibrated_sensors': quality['calibrated_sensors'],
            'confirming_stations': len(self.recent_flags),
            'confirming_station_list': list(self.recent_flags.keys()),
            'recent_flags': self.recent_flags,
            'sensors': self.sensor_states
        }
        tmp = self.output_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.output_path)

    def on_seedlink_error(self):
        print('ERROR SeedLink')

    def on_terminate(self):
        print('Connection terminated')


def main():
    import time
    import traceback

    inv_path = sys.argv[1] if len(sys.argv) > 1 else 'config/auto_cell_01_inventory.json'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'runtime/auto_cell_01_state.json'

    retry_seconds = 30

    while True:
        try:
            server, sensors, inventory = load_inventory(inv_path)
            inventory['_inventory_path'] = inv_path

            print('==============================================')
            print('CUYUM v1.2 - AUTO_CELL_01 PARALLEL READER')
            print('Server:', server)
            print('Inventory:', inv_path)
            print('Output:', out_path)
            print('Loaded sensors:', len(sensors))
            print('Feeds ESP32: NO')
            print('==============================================')

            client = AutoCellReader(server, sensors, inventory, out_path)

            for sensor in sensors:
                print(
                    f"Selecting {sensor['network']}.{sensor['station']}.{sensor['channel']} "
                    f"| {sensor.get('name','')} "
                    f"| useful ETA={sensor.get('effective_warning_seconds')}"
                )
                client.select_stream(sensor['network'], sensor['station'], sensor['channel'])

            print('')
            print('Listening auto_cell_01. Stop with Ctrl+C or use the stop script.')
            print('')

            client.run()

        except KeyboardInterrupt:
            print('')
            print('Stopped manually.')
            break

        except Exception as exc:
            print('')
            print(f'auto_cell_01 reader error: {exc}')
            traceback.print_exc()
            print(f'Retrying auto_cell_01 in {retry_seconds} seconds...')
            print('')
            time.sleep(retry_seconds)


if __name__ == '__main__':
    main()
