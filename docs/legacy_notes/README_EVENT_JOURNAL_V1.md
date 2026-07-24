# Cuyum Event Journal v1

Este parche separa dos cosas:

- `/api/public/live`: estado vivo actual para la página.
- `/api/public/events`: registros recientes de señales, cambios de cobertura y decisiones del sistema.

## Archivos

- `events_recent.jsonl`: caja negra liviana de eventos significativos.
- `audit_recent.jsonl`: auditoría técnica de sensores. También se usa como respaldo para mostrar registros recientes ya existentes.
- `event_journal_state.json`: estado chico de deduplicación. No es histórico.

## Retención

`events_recent.jsonl` se recorta automáticamente a los últimos 31 días. También se limita por cantidad de líneas para evitar crecimiento indefinido.

La configuración puede ajustarse en `config_cuyum.json`:

```json
{
  "retention": {
    "events_days": 31,
    "max_events_lines": 5000
  }
}
```

## Endpoints

- `/api/public/live`: estado vivo.
- `/api/public/events`: registros recientes.

## No modifica

No modifica ESP32, mapa, reglas de alerta ni lectores SeedLink.
