# Cuyum v1.2 - Archivos activos

## Arranque

- `start_cuyum_v1_2.sh`: arranca Cuyum.
- `stop_cuyum_v1_2.sh`: detiene Cuyum.
- `ver_multicelda_v1_2.sh`: inspección del estado multicelda.

## Servidor y API

- `plain_python_server.py`
- `public_api_v1.py`
- `public_live.py`

## Monitor

- `templates/live_cuyum.html`
- `static/live_cuyum.js`
- `static/live_cuyum.css`
- `static/cuyum_logo.jpg`

## Lectores y procesos

- `cell_00_seedlink_reader.py`
- `auto_cell_seedlink_reader.py`
- `periodic_discovery.sh`
- `seedlink_discovery.py`
- `sensor_auditor.py`
- `retention_cleaner.py`
- `event_journal.py`
- `multicell_fusion.py`

## Inventarios y herramientas activas

- `candidate_inventory.json`
- `auto_inventory_cells.json`
- `auto_cell_01_inventory.json`
- `ejecutar_auto_celdas.sh`
- `generar_inventory_auto_cell_01.py`
- `cuyum_auto_cells.py`
- `sensor_catalog.json`
- `sensor_geo_overrides.json`

## Runtime activo

- `state_cell_00_seedlink.json`
- `auto_cell_01_state.json`
- `events_recent.jsonl`
- `event_journal_state.json`
- `audit_recent.jsonl`

## Legacy en cuarentena

- Flask legacy server.
- Scripts viejos reemplazados.
- JSON antiguos que no participan del arranque actual.
