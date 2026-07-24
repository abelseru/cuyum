# Cuyum v1.2b - Auto cell reader English-core migration

Date: 2026-07-16T11:01:02
Mode: apply
Changed: True

## Scope

This migration touches only:

- `auto_cell_reader_seedlink.py`

## Rule

Internal code moves to English identifiers. Temporary Spanish compatibility keys are preserved where current modules still consume them.

## Backup

When applied, the original file is copied into:

- `backups_v1_2b_english_core/auto_cell_reader_seedlink.py.<timestamp>.bak`

## Next validation

```bash
cd ~/cuyum_v_1_2
python3 -m py_compile auto_cell_reader_seedlink.py
./detener_cuyum_v1_2.sh
./iniciar_cuyum_visible_v1_2.sh
./ver_multicelda_v1_2.sh
```

## Diff

```diff
--- auto_cell_reader_seedlink.py.before
+++ auto_cell_reader_seedlink.py.after
@@ -9,8 +9,8 @@
 from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
 
 PAQUETES_BASE = 5
-FACTOR_FLAG = 2.5
-FACTOR_FLAG_FUERTE = 4.0
+FLAG_FACTOR = 2.5
+STRONG_FLAG_FACTOR = 4.0
 VENTANA_EVENTO_SEGUNDOS = 10
 LATENCIA_MAXIMA_SEGUNDOS = 20
 PESO_BASE_ANTERIOR = 0.97
@@ -21,48 +21,48 @@
     return datetime.now(timezone.utc).isoformat()
 
 
-def energia_simple(trace):
+def energy_simple(trace):
     datos = trace.data
     if datos is None or len(datos) == 0:
         return 0.0
     return sum(abs(float(x)) for x in datos) / len(datos)
 
 
-def magnitud_experimental(energia):
-    if energia <= 0:
+def magnitude_experimental(energy):
+    if energy <= 0:
         return 0.0
-    return round(math.log10(energia + 1), 2)
-
-
-def extraer_clave_trace(trace_id):
+    return round(math.log10(energy + 1), 2)
+
+
+def extraer_key_trace(trace_id):
     partes = trace_id.split('.')
     if len(partes) < 4:
         return trace_id
     return f'{partes[0]}.{partes[1]}.{partes[3]}'
 
 
-def clave_sensor_cfg(sensor):
+def sensor_config_key(sensor):
     return f"{sensor['red']}.{sensor['estacion']}.{sensor['canal']}"
 
 
-def cargar_inventario(path):
+def load_inventory(path):
     data = json.loads(Path(path).read_text(encoding='utf-8'))
-    server = data.get('server_seedlink') or data.get('servidor_seedlink') or 'rtserve.earthscope.org:18000'
-    sensores = []
-    for s in data.get('sensores', []):
+    server = data.get('server_seedlink') or data.get('server_seedlink') or 'rtserve.earthscope.org:18000'
+    sensors = []
+    for s in data.get('sensors', []):
         if s.get('estado') in ['deshabilitado', 'caido', 'sospechoso']:
             continue
-        sensores.append(s)
-    return server, sensores, data
-
-
-def calcular_calidad_red(estado_sensores, minimo=5):
-    sensores = list(estado_sensores.values())
-    calibrados = [s for s in sensores if s.get('calibrado')]
-    activos = [s for s in calibrados if s.get('estado_sensor') == 'activo']
+        sensors.append(s)
+    return server, sensors, data
+
+
+def calculate_network_quality(sensor_states, minimo=5):
+    sensors = list(sensor_states.values())
+    calibrated = [s for s in sensors if s.get('calibrado')]
+    activos = [s for s in calibrated if s.get('estado_sensor') == 'activo']
     total = len(activos)
     if total >= 6:
-        estado = 'fuerte'
+        estado = 'strong'
     elif total >= minimo:
         estado = 'minima_viable'
     elif total >= 3:
@@ -73,175 +73,175 @@
         estado = 'sin_datos'
     return {
         'estado': estado,
-        'sensores_activos': total,
-        'sensores_calibrados': len(calibrados),
+        'sensors_activos': total,
+        'sensors_calibrated': len(calibrated),
         'min_good_sensors': minimo
     }
 
 
 def nivel_por_evento(flags):
-    cantidad = len(flags)
-    fuerte = any(x.get('flag_fuerte') for x in flags.values())
-    if cantidad >= 3:
-        return 'observacion_externa_fuerte'
-    if cantidad >= 2:
-        return 'observacion_externa'
-    if cantidad == 1 and fuerte:
-        return 'observacion_externa'
-    if cantidad == 1:
+    count = len(flags)
+    strong = any(x.get('flag_strong') for x in flags.values())
+    if count >= 3:
+        return 'external_observation_strong'
+    if count >= 2:
+        return 'external_observation'
+    if count == 1 and strong:
+        return 'external_observation'
+    if count == 1:
         return 'actividad_aislada'
     return 'normal'
 
 
 class AutoCellReader(EasySeedLinkClient):
-    def __init__(self, server, sensores, inventario, output_path):
+    def __init__(self, server, sensors, inventory, output_path):
         super().__init__(server)
         self.server = server
-        self.sensores = sensores
-        self.inventario = inventario
+        self.sensors = sensors
+        self.inventory = inventory
         self.output_path = Path(output_path)
-        self.cell_id = inventario.get('cell_id', 'auto_cell_01')
-        self.label = inventario.get('label', self.cell_id)
+        self.cell_id = inventory.get('cell_id', 'auto_cell_01')
+        self.label = inventory.get('label', self.cell_id)
         self.historial_base = {}
         self.base = {}
-        self.estado_sensores = {}
-        self.flags_recientes = {}
-        self.mapa = {clave_sensor_cfg(s): s for s in sensores}
+        self.sensor_states = {}
+        self.recent_flags = {}
+        self.mapa = {sensor_config_key(s): s for s in sensors}
 
     def on_data(self, trace):
-        clave = extraer_clave_trace(trace.id)
-        if clave not in self.mapa:
+        key = extraer_key_trace(trace.id)
+        if key not in self.mapa:
             return
-        cfg = self.mapa[clave]
-        energia = energia_simple(trace)
-        magnitud = magnitud_experimental(energia)
+        cfg = self.mapa[key]
+        energy = energy_simple(trace)
+        magnitude = magnitude_experimental(energy)
         ahora = UTCDateTime()
-        latencia = float(ahora - trace.stats.endtime)
-
-        if latencia > LATENCIA_MAXIMA_SEGUNDOS:
-            self.estado_sensores[clave] = self.estado_base(trace.id, clave, cfg, 'latencia_alta', False, latencia, energia, magnitud)
+        latency = float(ahora - trace.stats.endtime)
+
+        if latency > LATENCIA_MAXIMA_SEGUNDOS:
+            self.sensor_states[key] = self.base_state(trace.id, key, cfg, 'latency_alta', False, latency, energy, magnitude)
             self.escribir_estado()
-            print(f'DESCARTADO {trace.id} latencia={round(latencia, 1)}s')
+            print(f'DESCARTADO {trace.id} latency={round(latency, 1)}s')
             return
 
-        self.historial_base.setdefault(clave, []).append(energia)
-        calibrado = clave in self.base
+        self.historial_base.setdefault(key, []).append(energy)
+        calibrado = key in self.base
         if not calibrado:
-            if len(self.historial_base[clave]) >= PAQUETES_BASE:
-                self.base[clave] = median(self.historial_base[clave][-PAQUETES_BASE:])
+            if len(self.historial_base[key]) >= PAQUETES_BASE:
+                self.base[key] = median(self.historial_base[key][-PAQUETES_BASE:])
                 calibrado = True
-                print('BASE DEFINIDA:', clave, 'base=', round(self.base[clave], 2))
+                print('BASE DEFINIDA:', key, 'base=', round(self.base[key], 2))
             else:
-                st = self.estado_base(trace.id, clave, cfg, 'calibrando', False, latencia, energia, magnitud)
-                st['paquetes_base'] = len(self.historial_base[clave])
+                st = self.base_state(trace.id, key, cfg, 'calibrando', False, latency, energy, magnitude)
+                st['paquetes_base'] = len(self.historial_base[key])
                 st['paquetes_base_necesarios'] = PAQUETES_BASE
-                self.estado_sensores[clave] = st
+                self.sensor_states[key] = st
                 self.escribir_estado()
-                print(f'CALIBRANDO {trace.id} {len(self.historial_base[clave])}/{PAQUETES_BASE}')
+                print(f'CALIBRANDO {trace.id} {len(self.historial_base[key])}/{PAQUETES_BASE}')
                 return
 
-        base_sensor = self.base[clave]
-        ratio = energia / base_sensor if base_sensor > 0 else 0
-        flag = ratio >= FACTOR_FLAG
-        flag_fuerte = ratio >= FACTOR_FLAG_FUERTE
+        sensor_baseline = self.base[key]
+        ratio = energy / sensor_baseline if sensor_baseline > 0 else 0
+        flag = ratio >= FLAG_FACTOR
+        flag_strong = ratio >= STRONG_FLAG_FACTOR
 
         if not flag:
-            self.base[clave] = self.base[clave] * PESO_BASE_ANTERIOR + energia * PESO_ENERGIA_NUEVA
+            self.base[key] = self.base[key] * PESO_BASE_ANTERIOR + energy * PESO_ENERGIA_NUEVA
 
         if flag:
-            self.flags_recientes[cfg['estacion']] = {
-                'clave': clave,
+            self.recent_flags[cfg['estacion']] = {
+                'key': key,
                 'trace_id': trace.id,
                 'estacion': cfg['estacion'],
-                'nombre': cfg.get('nombre', clave),
+                'nombre': cfg.get('nombre', key),
                 'distancia_km': cfg.get('distancia_km'),
-                'energia_actual': round(energia, 2),
-                'energia_base': round(base_sensor, 2),
+                'energy_actual': round(energy, 2),
+                'energy_base': round(sensor_baseline, 2),
                 'ratio': round(ratio, 2),
-                'magnitud_estimada': magnitud,
-                'flag_fuerte': flag_fuerte,
+                'magnitude_estimada': magnitude,
+                'flag_strong': flag_strong,
                 'tiempo': float(ahora.timestamp),
                 'ultima_actualizacion': ahora_iso()
             }
 
-        self.estado_sensores[clave] = {
+        self.sensor_states[key] = {
             'trace_id': trace.id,
-            'clave': clave,
+            'key': key,
             'red': cfg['red'],
             'estacion': cfg['estacion'],
             'canal': cfg['canal'],
             'rol': cfg.get('rol', 'anticipacion'),
-            'nombre': cfg.get('nombre', clave),
+            'nombre': cfg.get('nombre', key),
             'distancia_km': cfg.get('distancia_km'),
-            'prioridad': cfg.get('prioridad'),
+            'priority': cfg.get('priority'),
             'estado_sensor': 'activo',
             'calibrado': True,
-            'energia_actual': round(energia, 2),
-            'energia_base': round(self.base[clave], 2),
+            'energy_actual': round(energy, 2),
+            'energy_base': round(self.base[key], 2),
             'ratio': round(ratio, 2),
-            'magnitud_estimada': magnitud,
+            'magnitude_estimada': magnitude,
             'flag': flag,
-            'flag_fuerte': flag_fuerte,
-            'latencia_segundos': round(latencia, 1),
+            'flag_strong': flag_strong,
+            'latency_segundos': round(latency, 1),
             'effective_warning_seconds': cfg.get('effective_warning_seconds'),
             'direction': cfg.get('direction'),
             'ultima_actualizacion': ahora_iso()
         }
         self.limpiar_flags_viejos(float(ahora.timestamp))
         self.escribir_estado()
-        print(f'{trace.id} energia={round(energia,2)} base={round(base_sensor,2)} ratio={round(ratio,2)} flag={flag} fuerte={flag_fuerte}')
-
-    def estado_base(self, trace_id, clave, cfg, estado, calibrado, latencia, energia, magnitud):
+        print(f'{trace.id} energy={round(energy,2)} base={round(sensor_baseline,2)} ratio={round(ratio,2)} flag={flag} strong={flag_strong}')
+
+    def base_state(self, trace_id, key, cfg, estado, calibrado, latency, energy, magnitude):
         return {
             'trace_id': trace_id,
-            'clave': clave,
+            'key': key,
             'red': cfg['red'],
             'estacion': cfg['estacion'],
             'canal': cfg['canal'],
             'rol': cfg.get('rol', 'anticipacion'),
-            'nombre': cfg.get('nombre', clave),
+            'nombre': cfg.get('nombre', key),
             'distancia_km': cfg.get('distancia_km'),
             'estado_sensor': estado,
             'calibrado': calibrado,
-            'energia_actual': round(energia, 2),
-            'magnitud_estimada': magnitud,
+            'energy_actual': round(energy, 2),
+            'magnitude_estimada': magnitude,
             'flag': False,
-            'flag_fuerte': False,
-            'latencia_segundos': round(latencia, 1),
+            'flag_strong': False,
+            'latency_segundos': round(latency, 1),
             'effective_warning_seconds': cfg.get('effective_warning_seconds'),
             'direction': cfg.get('direction'),
             'ultima_actualizacion': ahora_iso()
         }
 
     def limpiar_flags_viejos(self, ahora_ts):
-        for estacion in list(self.flags_recientes.keys()):
-            if ahora_ts - self.flags_recientes[estacion]['tiempo'] > VENTANA_EVENTO_SEGUNDOS:
-                del self.flags_recientes[estacion]
+        for estacion in list(self.recent_flags.keys()):
+            if ahora_ts - self.recent_flags[estacion]['tiempo'] > VENTANA_EVENTO_SEGUNDOS:
+                del self.recent_flags[estacion]
 
     def escribir_estado(self):
-        calidad = calcular_calidad_red(self.estado_sensores, self.inventario.get('min_good_sensors', 5))
-        nivel = nivel_por_evento(self.flags_recientes)
+        quality = calculate_network_quality(self.sensor_states, self.inventory.get('min_good_sensors', 5))
+        nivel = nivel_por_evento(self.recent_flags)
         salida = {
             'cell_id': self.cell_id,
             'label': self.label,
-            'role': self.inventario.get('role', 'early_warning'),
+            'role': self.inventory.get('role', 'early_warning'),
             'modo': 'auto_cell_parallel_seedlink_reader',
             'experimental': True,
             'feeds_esp32': False,
-            'advertencia': 'Prueba paralela. No modifica el servidor principal ni el ESP32.',
-            'servidor_seedlink': self.server,
-            'archivo_inventario': self.inventario.get('_inventory_path'),
+            'advertencia': 'Prueba paralela. No modifica el server principal ni el ESP32.',
+            'server_seedlink': self.server,
+            'archivo_inventory': self.inventory.get('_inventory_path'),
             'ultima_actualizacion': ahora_iso(),
             'estado': nivel,
             'flag': nivel != 'normal',
-            'calidad_red': calidad,
-            'sensores_totales': len(self.sensores),
-            'sensores_activos': calidad['sensores_activos'],
-            'sensores_calibrados': calidad['sensores_calibrados'],
-            'estaciones_confirmando': len(self.flags_recientes),
-            'estaciones_confirmando_lista': list(self.flags_recientes.keys()),
-            'flags_recientes': self.flags_recientes,
-            'sensores': self.estado_sensores
+            'quality_red': quality,
+            'sensors_totales': len(self.sensors),
+            'sensors_activos': quality['sensors_activos'],
+            'sensors_calibrated': quality['sensors_calibrated'],
+            'confirming_stations': len(self.recent_flags),
+            'confirming_station_list': list(self.recent_flags.keys()),
+            'recent_flags': self.recent_flags,
+            'sensors': self.sensor_states
         }
         tmp = self.output_path.with_suffix('.tmp')
         tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding='utf-8')
@@ -257,18 +257,18 @@
 def main():
     inv_path = sys.argv[1] if len(sys.argv) > 1 else 'inventory_auto_cell_01.json'
     out_path = sys.argv[2] if len(sys.argv) > 2 else 'state_auto_cell_01.json'
-    server, sensores, inventario = cargar_inventario(inv_path)
-    inventario['_inventory_path'] = inv_path
+    server, sensors, inventory = load_inventory(inv_path)
+    inventory['_inventory_path'] = inv_path
     print('==============================================')
     print('CUYUM v1.2 - LECTOR PARALELO AUTO_CELL_01')
     print('Servidor:', server)
     print('Inventario:', inv_path)
     print('Salida:', out_path)
-    print('Sensores cargados:', len(sensores))
+    print('Sensores cargados:', len(sensors))
     print('Alimenta ESP32: NO')
     print('==============================================')
-    client = AutoCellReader(server, sensores, inventario, out_path)
-    for sensor in sensores:
+    client = AutoCellReader(server, sensors, inventory, out_path)
+    for sensor in sensors:
         print(f"Seleccionando {sensor['red']}.{sensor['estacion']}.{sensor['canal']} | {sensor.get('nombre','')} | ETA útil={sensor.get('effective_warning_seconds')}")
         client.select_stream(sensor['red'], sensor['estacion'], sensor['canal'])
     print('')
```
