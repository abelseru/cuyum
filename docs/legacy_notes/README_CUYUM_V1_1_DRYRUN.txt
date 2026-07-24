CUYUM v1.1 - Dry-run de células
================================

Este parche NO cambia el sistema vivo.
No toca el lector SeedLink actual.
No toca el ESP32.
No toca inventario_candidatos.json.
No cambia arrancar_sistema.sh.

Agrega:

- config_cuyum_v1_1_dryrun.json
- cell_manager_dry_run.py
- ejecutar_dryrun_celulas.sh

Objetivo:

Probar la idea de 1 célula local de control + 3 células de anticipación:

- cell_00: local_control
- cell_01: early_warning
- cell_02: early_warning
- cell_03: early_warning

Las células usan coordenadas, no nombres geográficos hardcodeados.
El script calcula dirección humana desde el centro del proyecto:
N, NE, E, SE, S, SO, O, NO.

Uso:

cd ~/cuyum_v_1_1
source venv/bin/activate
./ejecutar_dryrun_celulas.sh

Salidas generadas:

- cell_candidates_report.json
- cell_candidates_report.txt

Si el reporte encuentra pocos sensores, no significa que el sistema actual esté fallando.
Significa que falta ampliar descubrimiento, proveedores o radio de búsqueda.
