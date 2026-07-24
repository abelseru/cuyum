# Cuyum v1.1 - Prueba paralela de auto_cell_01

Este parche agrega una prueba paralela para la primera célula automática viable detectada por Cuyum:

- `cell_00`: local/control, sigue funcionando como antes.
- `auto_cell_01`: célula externa oeste / Chile central, prueba paralela.

No modifica el servidor principal, no modifica el ESP32 y no cambia el endpoint `/api/node/poll`.

## Archivos agregados

- `generar_inventory_auto_cell_01.py`
- `auto_cell_reader_seedlink.py`
- `iniciar_auto_cell_01_prueba.sh`
- `detener_auto_cell_01_prueba.sh`
- `ver_estado_auto_cell_01.sh`

## Uso

Desde `~/cuyum_v_1_1`:

```bash
chmod +x iniciar_auto_cell_01_prueba.sh detener_auto_cell_01_prueba.sh ver_estado_auto_cell_01.sh
./iniciar_auto_cell_01_prueba.sh
```

La terminal queda abierta como panel vivo de la célula. Para ver resumen desde otra terminal:

```bash
./ver_estado_auto_cell_01.sh
```

Para detener solo esta célula experimental:

```bash
./detener_auto_cell_01_prueba.sh
```

## Archivos generados en ejecución

- `inventory_auto_cell_01.json`
- `state_auto_cell_01.json`
- `logs_auto_cell_01.txt`

## Seguridad

Esta prueba no alimenta al ESP32. Solo sirve para confirmar que la célula oeste puede correr sostenida en paralelo.
