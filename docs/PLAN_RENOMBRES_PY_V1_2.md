# Plan de nombres Python para Cuyum v1.2 Transparente

Fecha: 2026-07-16T09:56:42-03:00  
Carpeta: /home/usuario/cuyum_v_1_2

## Criterio

Este documento no renombra nada por sí solo. Su objetivo es detectar archivos `.py` con nombres en español, nombres históricos o nombres largos, y proponer una transición hacia nombres más trazables para capacitación.

Regla de seguridad:

- Primero se mueve lo experimental a `laboratorio/`.
- Después se prueban los scripts de arranque.
- Recién al final se renombran archivos del núcleo.
- Si un archivo es importado o llamado por scripts, no se renombra sin actualizar referencias.

## Archivos Python revisados

| Archivo actual | Propuesta posible | Motivo | Referencias detectadas | Criterio |
|---|---|---:|---:|---|
| `auto_cell_seedlink_reader.py` | `—` | sin observación fuerte | 11 | conservar: ya está en inglés o aceptable |
| `buscar_estaciones_mendoza.py` | `find_mendoza_stations.py` | nombre en español | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `calibrar_seedlink_cercanos.py` | `calibrate_nearby_seedlink.py` | nombre en español | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `cell_manager_dry_run.py` | `—` | sin observación fuerte | 3 | mover primero a laboratorio; renombrar después si se conserva |
| `cell_manager_dry_run_v2.py` | `—` | nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `cell_manager_dry_run_v3.py` | `—` | nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `cell_manager_dry_run_v4.py` | `—` | nombre histórico o largo | 2 | mover primero a laboratorio; renombrar después si se conserva |
| `confirmar_cell02_v4d.py` | `confirm_cell02.py` | nombre en español,nombre histórico o largo | 2 | mover primero a laboratorio; renombrar después si se conserva |
| `cuyum_auto_cells.py` | `—` | sin observación fuerte | 2 | conservar: ya está en inglés o aceptable |
| `descubridor_seedlink.py` | `seedlink_discovery.py` | sin observación fuerte | 8 | evaluar manualmente |
| `event_journal.py` | `—` | sin observación fuerte | 8 | conservar: ya está en inglés o aceptable |
| `generar_inventory_auto_cell_01.py` | `generate_auto_cell_inventory.py` | nombre en español,demasiado largo | 6 | evaluar manualmente |
| `inventario_seedlink_vivo.py` | `seedlink_inventory_live.py` | nombre en español | 1 | evaluar manualmente |
| `monitor_central_completo_demo.py` | `demo_monitor.py` | nombre en español,nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `multicell_fusion.py` | `—` | sin observación fuerte | 7 | conservar: ya está en inglés o aceptable |
| `probar_seedlink_candidatos.py` | `test_seedlink_candidates.py` | nombre en español | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `public_live.py` | `—` | sin observación fuerte | 8 | conservar: ya está en inglés o aceptable |
| `retention_cleaner.py` | `—` | sin observación fuerte | 10 | conservar: ya está en inglés o aceptable |
| `seedlink_probe_from_v3.py` | `—` | nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `seedlink_probe_v4.py` | `—` | nombre histórico o largo | 2 | mover primero a laboratorio; renombrar después si se conserva |
| `seedlink_probe_v4c_chunked.py` | `—` | nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `sensor_auditor.py` | `—` | sin observación fuerte | 13 | conservar: ya está en inglés o aceptable |
| `servidor_json_completo_demo.py` | `demo_server.py` | nombre en español,nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `servidor_json_seedlink.py` | `server.py` | nombre en español | 15 | posponer: núcleo llamado por scripts de arranque |
| `simulador_evento.py` | `event_simulator.py` | nombre en español | 6 | evaluar manualmente |
| `test_01_fdsn_historico.py` | `test_fdsn_history.py` | nombre en español | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `test_02_energia.py` | `test_signal_energy.py` | nombre en español | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `test_03_json_local.py` | `test_local_json.py` | nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `test_04_monitor_central_local.py` | `test_local_monitor.py` | nombre en español,nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `test_05_servidor_json_local.py` | `test_local_server.py` | nombre en español,nombre histórico o largo | 1 | mover primero a laboratorio; renombrar después si se conserva |
| `test_fdsn_reciente_mendoza.py` | `test_recent_mendoza_fdsn.py` | nombre en español | 1 | mover primero a laboratorio; renombrar después si se conserva |
