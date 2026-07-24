# Cuyum v1.1 - eventos públicos compactos

Este hotfix reduce `/api/public/events` a registros significativos.

No publica:

- snapshots normales de red o célula;
- cambios de calibración;
- latencia alta normalizada;
- transiciones de arranque como 0, 1, 2, 3 sensores.

Sí publica:

- señales coincidentes en una zona;
- señales compartidas por sensores;
- señales aisladas intensas;
- decisiones públicas no normales del sistema;
- caídas o recuperaciones reales de sensores.

La retención se mantiene:

- `events_recent.jsonl`: últimos 31 días según `config_cuyum.json`;
- máximo de líneas: `max_events_lines`;
- `event_journal_state.json` se recorta internamente.

La salida pública se compacta para que no duplique nombre, localidad y coordenadas en campos planos y anidados.
