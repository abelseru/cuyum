# Cuyum live - hotfix mapa real

Este parche reemplaza el mapa territorial anterior por un SVG fijo con contornos provinciales/regionales simplificados.

Objetivo:
- no usar tiles externos;
- no usar zoom ni navegación;
- mostrar contornos de Mendoza, San Juan, San Luis, Neuquén y regiones cercanas de Chile;
- mostrar sensores ubicables como puntos claros;
- no tapar el mapa con etiquetas grandes;
- mantener una sola consulta a `/api/public/live` por ciclo.

También agrega `sensor_geo_overrides.json` para ubicar sensores heredados que el inventario viejo no traía con lat/lon. Esos datos son solo para visualización; no se usan para decisiones de alerta.
