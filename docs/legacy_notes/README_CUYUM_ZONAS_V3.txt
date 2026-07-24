CUYUM v1.1 - ZONAS v3
======================

Este parche NO modifica el sistema vivo.
No cambia el ESP32.
No arranca más lectores.
No toca el servidor actual.

Agrega:

- cuyum_zones_setup.json
  Archivo manual para editar las coordenadas de las zonas.
  Cada zona tiene 3 centros de preferencia:
  priority 1 = centro preferido
  priority 2 = failover 1
  priority 3 = failover 2

- cell_manager_dry_run_v3.py
  Prueba las zonas y genera un reporte.
  Primero intenta el centro 1 de cada zona.
  Si no alcanza, intenta el centro 2.
  Si no alcanza, intenta el centro 3.
  Si tampoco alcanza, combina candidatos de los 3 centros.
  No comparte sensores principales entre zonas salvo que en el futuro se decida una excepción explícita.

- ejecutar_dryrun_zonas_v3.sh
  Lanza el reporte desde doble clic o terminal.

- ver_zonas_cuyum.html
  Visor simple HTML5.
  Abrir con navegador.
  Cargar cuyum_zones_setup.json.
  Sirve para ver con los propios ojos dónde quedaron los centros.

Uso:

cd ~/cuyum_v_1_1
./ejecutar_dryrun_zonas_v3.sh

Luego revisar:

cat cell_candidates_report_v3.txt

Para ver las zonas:

abrir ver_zonas_cuyum.html con el navegador
cargar cuyum_zones_setup.json desde el botón de archivo

