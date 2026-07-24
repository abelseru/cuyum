CUYUM v1.1 - SeedLink Probe v4c
================================

Este parche NO modifica el sistema vivo.
No toca el ESP32.
No arranca lectores nuevos.

Problema corregido:
La prueba v4 intentaba seleccionar demasiados streams al mismo tiempo.
Eso podía producir falsos no_data, incluso para sensores que antes habían respondido.

Qué hace v4c:
- Lee cell_candidates_report_v4.json.
- Prueba cada zona por tandas pequeñas.
- Prueba varios servidores SeedLink configurados en cuyum_data_sources.json.
- Se detiene por zona cuando encuentra 6 sensores seedlink_ok.
- Si se interrumpe con Ctrl+C, guarda reporte parcial.

Uso:
  cd ~/cuyum_v_1_1
  ./ejecutar_prueba_seedlink_v4c.sh

Archivos generados:
  seedlink_probe_v4c_report.txt
  seedlink_probe_v4c_report.json
  inventory_cells_v4c_suggested.json

Criterio:
  5 o 6 seedlink_ok  -> zona candidata a célula viva
  3 o 4 seedlink_ok  -> zona débil / contexto
  0 a 2 seedlink_ok  -> no activar todavía

