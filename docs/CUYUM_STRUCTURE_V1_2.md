# Cuyum v1.2 - Estructura enseñable

## Arranque y detención

- `start_cuyum_v1_2.sh`: arranca Cuyum.
- `stop_cuyum_v1_2.sh`: detiene Cuyum.

## Lectores

Los lectores escuchan datos SeedLink y actualizan archivos JSON de estado.

- `cell_00_seedlink_reader.py`: celda local.
- `auto_cell_seedlink_reader.py`: celda automática externa.

## Estado runtime

Los JSON runtime son datos vivos del sistema. No se editan manualmente durante operación.

- `state_cell_00_seedlink.json`
- `auto_cell_01_state.json`
- `events_recent.jsonl`
- `event_journal_state.json`
- `auto_cell_01_inventory.json`

## Fusión

- `multicell_fusion.py`: combina celdas y calcula el estado general.

## Servidor

- `plain_python_server.py`: publica el monitor, la API y compatibilidad ESP32.

## API pública limpia

- `public_api_v1.py`: transforma datos internos en una API limpia.

Rutas principales:

- `/json`
- `/api/v1/cells`
- `/api/v1/sensors`
- `/reg`

## Monitor

- `templates/app_cuyum.html`
- `static/app_cuyum.js`
- `static/app_cuyum.css`

## Simulación

El botón `🔊 Probar simulación` es cosmético:

- no modifica JSON,
- no crea eventos,
- no toca lectores,
- dura 10 segundos.

## Legacy

Los archivos viejos se conservan en cuarentena. No se borran hasta varios días de prueba estable.
