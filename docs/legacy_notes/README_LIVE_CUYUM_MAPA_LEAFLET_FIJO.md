# Cuyum Live - mapa real fijo

Hotfix para volver a un mapa real con OpenStreetMap, pero sin zoom ni navegación del usuario.

- La página sigue descargando un solo JSON cada ciclo desde `/api/public/live`.
- Modo normal: 5 segundos.
- Modo alerta: 1,5 segundos.
- Los tiles del mapa se cargan como recursos visuales del navegador, no como JSON de estado.
- Se agregan coordenadas de visualización para sensores locales heredados que no traían lat/lon en el estado vivo.
- Las coordenadas de `sensor_geo_overrides.json` son solo para mapa público; no se usan para alertas.
