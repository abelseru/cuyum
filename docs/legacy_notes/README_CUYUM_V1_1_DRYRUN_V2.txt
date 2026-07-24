CUYUM v1.1 - DRY-RUN CELULAS v2

Este parche no modifica el sistema vivo.
No inicia nuevos lectores.
No cambia el ESP32.
No cambia servidor Flask.

Archivos agregados:
- config_cells_v1_1_dryrun_v2.json
- cell_manager_dry_run_v2.py
- ejecutar_dryrun_celulas_v2.sh

Uso:
cd ~/cuyum_v_1_1
source venv/bin/activate
./ejecutar_dryrun_celulas_v2.sh

Salida:
- cell_candidates_report_v2.txt
- cell_candidates_report_v2.json

Criterios nuevos:
- cell_00 hereda la célula viva actual.
- Ningún sensor queda como principal en más de una célula.
- Si faltan sensores, el reporte muestra huecos y reservas compartidas, pero no las elige como principales.
- Se elige un solo canal por estación.
- Se priorizan sensores ya conocidos y vivos por encima de sensores nuevos.
- El reporte marca cobertura pobre sin forzar una célula falsa.
