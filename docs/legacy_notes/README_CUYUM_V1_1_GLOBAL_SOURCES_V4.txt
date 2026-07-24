CUYUM v1.1 - Fuentes globales v4b rápido

Este parche corrige el v4 anterior, que podía quedar demasiado tiempo esperando respuestas FDSN.

Cambios:
- IRIS legado queda desactivado por defecto para evitar advertencias repetidas.
- RESIF y GEONET quedan desactivados por defecto.
- Quedan activos EARTHSCOPE y GEOFON.
- Timeout FDSN corto: 8 segundos.
- Consulta canales en una sola llamada por proveedor/centro.
- Muestra progreso visible por zona y centro.
- Si se interrumpe con Ctrl+C, intenta guardar reporte parcial.

Uso:
  cd ~/cuyum_v_1_1
  ./ejecutar_dryrun_zonas_v4.sh

Luego:
  ./ejecutar_prueba_seedlink_v4.sh

Archivos:
- cuyum_data_sources.json: editar proveedores y tiempos.
- cell_candidates_report_v4.txt/json: salida del dry-run.
- seedlink_probe_v4_report.txt/json: salida de prueba en vivo.
- inventory_cells_v4_suggested.json: inventario sugerido, no aplicado automáticamente.
