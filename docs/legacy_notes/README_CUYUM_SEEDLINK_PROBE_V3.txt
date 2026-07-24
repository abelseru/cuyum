CUYUM v1.1 - PRUEBA SEEDLINK v3

Objetivo
--------
Verificar si los sensores propuestos por el dry-run de zonas v3 entregan datos reales
por el servidor SeedLink configurado en inventario_candidatos.json.

No modifica el sistema vivo.
No cambia el ESP32.
No arranca nuevas células permanentes.

Uso
---
1) Ejecutar primero:
   ./ejecutar_dryrun_zonas_v3.sh

2) Ejecutar:
   ./ejecutar_prueba_seedlink_v3.sh

3) Revisar:
   seedlink_probe_v3_report.txt
   seedlink_probe_v3_report.json

Interpretación
--------------
seedlink_ok           = llegó señal suficiente para pensar en célula real
seedlink_weak         = llegó algo, pero poco; posible reserva/cuarentena
seedlink_high_latency = llegó algo viejo/lento; cuidado
no_data               = no llegó nada durante la prueba

Regla sugerida
--------------
No pasar una célula a modo vivo si no tiene al menos 5 sensores seedlink_ok.
Con 3 o 4, usarla solo como contexto/degradada.
Con menos de 3, revisar centros alternativos o descartar por ahora.
