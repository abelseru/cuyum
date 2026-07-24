# Cuyum v1.1 - eventos con coordenadas y localidad

Este hotfix agrega metadatos públicos de sensor a:

- `/api/public/live` para el estado actual.
- `/api/public/events` para registros recientes.

Cada evento de sensor puede incluir ahora:

- `sensor_name`
- `localidad`
- `lat`
- `lon`
- `sensor` como objeto resumido
- `location_source`
- `approx_location`

La retención no cambia: `events_recent.jsonl` sigue limitado por `events_days` y `max_events_lines`.
