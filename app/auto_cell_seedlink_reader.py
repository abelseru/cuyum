#!/usr/bin/env python3
import json
import math
from statistics import median
from datetime import datetime, timezone
from pathlib import Path
import sys
from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient

PAQUETES_BASE = 5
FLAG_FACTOR = 2.5
STRONG_FLAG_FACTOR = 4.0
VENTANA_EVENTO_SEGUNDOS = 10
LATENCIA_MAXIMA_SEGUNDOS = 20
PESO_BASE_ANTERIOR = 0.97
PESO_ENERGIA_NUEVA = 0.03


def ahora_iso():
    return datetime.now(timezone.utc).isoformat()


def energy_simple(trace):
    datos = trace.data
    if datos is None or len(datos) == 0:
        return 0.0
    return sum(abs(float(x)) for x in datos) / len(datos)


def magnitude_experimental(energy):
    if energy <= 0:
        return 0.0
    return round(math.log10(energy + 1), 2)


def extraer_key_trace(trace_id):
    partes = trace_id.split('.')
    if len(partes) < 4:
        return trace_id
    return f'{partes[0]}.{partes[1]}.{partes[3]}'


def sensor_config_key(sensor):
    return f"{sensor['network']}.{sensor['station']}.{sensor['channel']}"


def load_inventory(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    server = data.get('seedlink_server') or data.get('seedlink_server') or 'rtserve.earthscope.org:18000'
    sensors = []
    for s in data.get('sensors', data.get('sensores', [])):
        if s.get('estado') in ['deshabilitado', 'caido', 'sospechoso']:
            continue
        sensors.append(s)
    return server, sensors, data


def calculate_network_quality(sensor_states, minimo=5):
    sensors = list(sensor_states.values())
    calibrated = [
        s for s in sensors
        if s.get('calibrated', s.get('calibrated', False))
    ]
    active = [
        s for s in calibrated
        if s.get('sensor_state', s.get('estado_sensor')) in ('active', 'activo')
    ]
    total = len(active)
    if total >= 6:
        state = 'strong'
    elif total >= minimo:
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
        'sensors_calibrated': len(calibrated),
        'min_good_sensors': minimo
    }


def event_level_from_flags(flags):
    count = len(flags)
    strong = any(x.get('flag_strong') for x in flags.values())
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
        self.historial_base = {}
        self.base = {}
        self.sensor_states = {}
        self.recent_flags = {}
        self.mapa = {sensor_config_key(s): s for s in sensors}

    def on_data(self, trace):
        key = extraer_key_trace(trace.id)
        if key not in self.mapa:
            return
        cfg = self.mapa[key]
        energy = energy_simple(trace)
        magnitude = magnitude_experimental(energy)
        ahora = UTCDateTime()
        latency = float(ahora - trace.stats.endtime)

        if latency > LATENCIA_MAXIMA_SEGUNDOS:
            self.sensor_states[key] = self.base_state(trace.id, key, cfg, 'latency_alta', False, latency, energy, magnitude)
            self.escribir_estado()
            print(f'DESCARTADO {trace.id} latency={round(latency, 1)}s')
            return

        self.historial_base.setdefault(key, []).append(energy)
        calibrado = key in self.base
        if not calibrado:
            if len(self.historial_base[key]) >= PAQUETES_BASE:
                self.base[key] = median(self.historial_base[key][-PAQUETES_BASE:])
                calibrado = True
                print('BASE DEFINIDA:', key, 'base=', round(self.base[key], 2))
            else:
                st = self.base_state(trace.id, key, cfg, 'calibrando', False, latency, energy, magnitude)
                st['paquetes_base'] = len(self.historial_base[key])
                st['paquetes_base_necesarios'] = PAQUETES_BASE
                self.sensor_states[key] = st
                self.escribir_estado()
                print(f'CALIBRATING {trace.id} {len(self.historial_base[key])}/{PAQUETES_BASE}')
                return

        sensor_baseline = self.base[key]
        ratio = energy / sensor_baseline if sensor_baseline > 0 else 0
        flag = ratio >= FLAG_FACTOR
        flag_strong = ratio >= STRONG_FLAG_FACTOR

        if not flag:
            self.base[key] = self.base[key] * PESO_BASE_ANTERIOR + energy * PESO_ENERGIA_NUEVA

        if flag:
            self.recent_flags[cfg['station']] = {
                'key': key,
                'trace_id': trace.id,
                'station': cfg['station'],
                'name': cfg.get('name', key),
                'distance_km': cfg.get('distance_km'),
                'energy_actual': round(energy, 2),
                'energy_base': round(sensor_baseline, 2),
                'ratio': round(ratio, 2),
                'magnitude_estimada': magnitude,
                'flag_strong': flag_strong,
                'timestamp': float(ahora.timestamp),
                'updated_at': ahora_iso()
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
            'energy_actual': round(energy, 2),
            'energy_base': round(self.base[key], 2),
            'ratio': round(ratio, 2),
            'magnitude_estimada': magnitude,
            'flag': flag,
            'flag_strong': flag_strong,
            'latency_seconds': round(latency, 1),
            'effective_warning_seconds': cfg.get('effective_warning_seconds'),
            'direction': cfg.get('direction'),
            'updated_at': ahora_iso()
        }
        self.limpiar_flags_viejos(float(ahora.timestamp))
        self.escribir_estado()
        print(f'{trace.id} energy={round(energy,2)} base={round(sensor_baseline,2)} ratio={round(ratio,2)} flag={flag} strong={flag_strong}')

    def base_state(self, trace_id, key, cfg, estado, calibrado, latency, energy, magnitude):
        return {
            'trace_id': trace_id,
            'key': key,
            'network': cfg['network'],
            'station': cfg['station'],
            'channel': cfg['channel'],
            'role': cfg.get('role', 'early_warning'),
            'name': cfg.get('name', key),
            'distance_km': cfg.get('distance_km'),
            'sensor_state': estado,
            'calibrated': calibrado,
            'energy_actual': round(energy, 2),
            'magnitude_estimada': magnitude,
            'flag': False,
            'flag_strong': False,
            'latency_seconds': round(latency, 1),
            'effective_warning_seconds': cfg.get('effective_warning_seconds'),
            'direction': cfg.get('direction'),
            'updated_at': ahora_iso()
        }

    def limpiar_flags_viejos(self, ahora_ts):
        for estacion in list(self.recent_flags.keys()):
            if ahora_ts - self.recent_flags[estacion]['timestamp'] > VENTANA_EVENTO_SEGUNDOS:
                del self.recent_flags[estacion]

    def escribir_estado(self):
        quality = calculate_network_quality(self.sensor_states, self.inventory.get('min_good_sensors', 5))
        level = event_level_from_flags(self.recent_flags)
        salida = {
            'cell_id': self.cell_id,
            'label': self.label,
            'role': self.inventory.get('role', 'early_warning'),
            'mode': 'auto_cell_parallel_seedlink_reader',
            'experimental': True,
            'feeds_esp32': False,
            'notice': 'Parallel test. Does not modify the main server or ESP32.',
            'seedlink_server': self.server,
            'inventory_file': self.inventory.get('_inventory_path'),
            'updated_at': ahora_iso(),
            'state': level,
            'flag': level != 'normal',
            'network_quality': quality,
            'total_sensors': len(self.sensors),
            'active_sensors': quality['active_sensors'],
            'sensors_calibrated': quality['sensors_calibrated'],
            'confirming_stations': len(self.recent_flags),
            'confirming_station_list': list(self.recent_flags.keys()),
            'recent_flags': self.recent_flags,
            'sensors': self.sensor_states
        }
        tmp = self.output_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding='utf-8')
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
