# Cuyum Server v1.2 - Estado actual

## Servidor

El servidor operativo actual es Cuyum Server.

- Archivo principal: `plain_python_server.py`
- Puerto de prueba: `5050`
- Script de inicio: `start_cuyum_server_v1_2.sh`
- Script de detención: `stop_cuyum_server_v1_2.sh`

El servidor anterior queda como respaldo temporal.

- Flask legacy server: `servidor_json_seedlink.py`

## Live

Monitor actual:

- URL local: `http://127.0.0.1:5050/app`
- URL LAN: `http://192.168.1.37:5050/app`

Estado del live:

- Botón de audio con latido inicial.
- Botón `🔊 Probar simulación`.
- Simulación cosmética de 10 segundos.
- La simulación no altera JSON reales.
- La simulación no crea eventos reales.
- La simulación no toca lectores SeedLink.

## API pública limpia

Enlaces visibles del monitor:

- Estado actual: `/json`
- Registros recientes: `/reg`

Rutas API v1:

- `/json`
- `/api/v1/cells`
- `/api/v1/sensors`
- `/reg`

## Compatibilidad legacy

Se mantienen por compatibilidad:

- `/json`
- `/api/public/events`
- `/api/network/state`
- `/api/node/poll`
- `/api/esp32/poll`
- `/estado.json`
- `/inventario.json`
- `/sensores.json`

## Criterio de idioma

- Código nuevo: inglés.
- Scripts nuevos: inglés.
- API pública técnica: inglés.
- Mensajes humanos del live: español claro.
- JSON internos legacy: se conservan hasta refactor por adaptadores.

## Microcell layout validated

Cuyum v1.2 was validated with the current app/config/runtime layout.

Observed state:

- Server: `app/plain_python_server.py`
- Port: `5050`
- `cell_00`: fresh, 5 active sensors
- `auto_cell_01`: fresh, 2 active sensors
- `auto_cell_02`: fresh, 3 active sensors
- Active cells: 3
- Configured cells: 3
- Network mode: `multicell`
- Network quality: `high_multicell`
- Sound: false
- Buzzer seconds: 0

This confirms the reduced microcell layout is operational.

## Local reader reconnect loop validated

`app/cell_00_seedlink_reader.py` was patched to keep running after temporary SeedLink/DNS/network errors.

Validation:

- `cell_00_seedlink_reader.py` starts correctly.
- `cell_00` returns to `fresh=True`.
- Network mode returns to `multicell`.
- Network quality returns to `high_multicell`.
- Active cells: 3.
- Active sensors: 11.
- Sound: false.
- Buzzer seconds: 0.

This prevents the local cell from staying down after a temporary connection failure.

## Microcell and regional observer policy applied

Cuyum was adjusted to avoid presenting overlapping remote microcells as separate zones.

Validation:

- `auto_cell_02` was disabled because it overlapped the same dense remote sensor group as `auto_cell_01`.
- `auto_cell_01` remains active with 3 primary sensors.
- `cell_00` remains active as local/control cell.
- San Juan / IGSV and La Paz / INPRES were reclassified as `observador_regional`.
- Regional observers no longer count as local validating sensors.
- `cell_00` now reports 4 validating active sensors instead of 6.
- Network now reports 7 validating active sensors instead of 9.
- Active configured cells: 2.
- Sound: false.
- Buzzer seconds: 0.

Current conceptual layout:

- Local/control validating cell: 4 sensors.
- Remote early-warning cell: 3 sensors.
- Regional observers: 2 sensors.

## Microcell and regional observer policy applied

Cuyum was adjusted to avoid presenting overlapping remote microcells as separate zones.

Validation:

- `auto_cell_02` was disabled because it overlapped the same dense remote sensor group as `auto_cell_01`.
- `auto_cell_01` remains active with 3 primary sensors.
- `cell_00` remains active as local/control cell.
- San Juan / IGSV and La Paz / INPRES were reclassified as `observador_regional`.
- Regional observers no longer count as local validating sensors.
- `cell_00` now reports 4 validating active sensors instead of 6.
- Network now reports 7 validating active sensors instead of 9.
- Active configured cells: 2.
- Sound: false.
- Buzzer seconds: 0.

Current conceptual layout:

- Local/control validating cell: 4 sensors.
- Remote early-warning cell: 3 sensors.
- Regional observers: 2 sensors.

## Local reader reconnect loop validated

`app/cell_00_seedlink_reader.py` was patched to keep running after temporary SeedLink/DNS/network errors.

Validation:

- `cell_00_seedlink_reader.py` starts correctly.
- `cell_00` returns to `fresh=True`.
- Network mode returns to `multicell`.
- Network quality returns to `high_multicell`.
- Active cells: 3.
- Active sensors: 11.
- Sound: false.
- Buzzer seconds: 0.

This prevents the local cell from staying down after a temporary connection failure.

## Local reader reconnect loop validated

`app/cell_00_seedlink_reader.py` was patched to keep running after temporary SeedLink/DNS/network errors.

Validation:

- `cell_00_seedlink_reader.py` starts correctly.
- `cell_00` returns to `fresh=True`.
- Network mode returns to `multicell`.
- Network quality returns to `high_multicell`.
- Active cells: 3.
- Active sensors: 11.
- Sound: false.
- Buzzer seconds: 0.

This prevents the local cell from staying down after a temporary connection failure.

## Auto-cell generation note

After the reconnect loop validation, the auto-cell inventory was regenerated/reduced to one remote auto-cell.

Current validated structure:

- `cell_00`: local control cell.
- `auto_cell_01`: remote early-warning cell, southwest/west group.
- `auto_cell_02`, `auto_cell_03`, and `auto_cell_04`: not created because no additional sufficiently separated live SeedLink sensor group was available.

This is intentional and preferred over splitting the same dense Chile/Santiago sensor area into multiple artificial cells.

Current operational reading may therefore show:

- Active cells: 2.
- Active sensors: 7.
- Network mode: `multicell`.
- Network quality: `high_multicell`.

The target remains up to 5 total cells including local, but only geographically valid cells should be created.

## Portable auto-cell policy validated

The auto-cell generator was updated to remove legacy local fallbacks.

Validated behavior:

- No `legacy_live_cell` entries are generated.
- No generic `fallback` local sensors are generated.
- `cell_00` becomes `reference_only` when no real local inventory is available.
- Remote sensors farther than `max_sensor_distance_from_home_km` are excluded.
- Mendoza still generates one valid remote cell around the Chile/Suroeste group.
- Caracas does not inherit Mendoza/Chile sensors.
- Caracas does not create artificial remote cells from sensors thousands of kilometers away.

Current distance guard:

- `max_sensor_distance_from_home_km`: 800

This makes Cuyum safer for reuse in other cities or countries without silently inheriting Mendoza-specific assumptions.

## Regional discovery prototype validated

A regional station discovery path was tested without modifying the live Mendoza system.

For Caracas, Cuyum generated a real FDSN regional station catalog instead of reusing Mendoza-specific inventories.

Preview results:

- Regional center: Caracas
- FDSN provider tested: IRIS / EarthScope
- Regional stations found within 800 km: 109
- Candidate stations selected for SeedLink test: 90
- SeedLink server tested: rtserve.earthscope.org:18000
- Alive stations found: 5

Alive regional stations:

- PR.ACPR.HHZ | International School of Aruba UNESCO | 405.7 km | trigger disabled
- IU.SDV.BHZ | Santo Domingo, Venezuela | 445.8 km | trigger disabled
- CU.GRGR.BHZ | Grenville, Grenada | 601.1 km | trigger disabled
- CM.OCA.HHZ | Ocana, Norte de Santander, Colombia | 746.6 km | trigger disabled
- G.FDFM.BHZ | Morne la Rosette, Martinique, France | 782.3 km | trigger disabled

Conclusion:

Cuyum is no longer limited to a manually written Mendoza sensor list in principle. A regional discovery and liveness workflow now exists in preview form.

However, for Caracas the alive sensors are distant regional observers, not close local validators. Therefore Caracas should not be presented as having local early-warning coverage through the current SeedLink server.

Honest public status for Caracas would be:

- Local coverage: insufficient
- Regional observation: available
- Local trigger: disabled
- Experimental status only

Files produced by the preview workflow:

- app/regional_station_catalog_builder.py
- app/regional_candidate_inventory_builder.py
- app/seedlink_preview_liveness_test.py
- config/seedlink_station_catalog.preview.json
- runtime/bootstrap_preview/candidate_inventory.preview.json
- runtime/seedlink_preview_liveness_result.json
- runtime/bootstrap_preview/candidate_inventory.alive.preview.json
- runtime/regional_station_catalog_report.txt
- runtime/regional_candidate_inventory_report.txt
- runtime/regional_alive_candidate_report.txt

This workflow must remain separate from the live Mendoza configuration until an explicit apply step is implemented with safety checks.

## Future autonomous regional workflow

The regional discovery workflow must become an autonomous Cuyum routine.

Future expected behavior:

1. Read the configured system center.
2. Build a regional FDSN station catalog around that center.
3. Select candidate sensors without duplicating stations.
4. Test SeedLink liveness for the selected candidates.
5. Keep only live sensors.
6. Classify the real capability.
7. Apply live configuration only if safety rules allow it.

Automatic capability policy:

- 3 or more live sensors within 200 km:
  - local experimental coverage available
  - local trigger may be allowed after additional validation

- 1 or 2 live sensors within 200 km:
  - minimal local observation only
  - local trigger disabled

- 0 live sensors within 200 km and 3 or more live regional sensors:
  - regional observation only
  - local trigger disabled

- 0 live sensors:
  - no live coverage through the current SeedLink server
  - local trigger disabled

Validated Caracas result:

- FDSN stations found within 800 km: 109
- SeedLink candidates tested: 90
- Live regional sensors: 5
- Live local sensors within 200 km: 0
- Capability: regional_observation_only
- Local trigger allowed: false

This confirms that Cuyum can discover and evaluate a new region, but it must not automatically present distant regional sensors as local early-warning coverage.
