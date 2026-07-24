# Cuyum v1.1 - integración multicelda

Este parche integra `cell_00` y `auto_cell_01` en el servidor principal.

## Qué cambia

- El servidor Flask deja de responder solamente con el estado local.
- El endpoint que ya usa el ESP32 sigue siendo el mismo:

```text
/api/node/poll?node_id=node_01
```

- Ese endpoint ahora fusiona:

```text
cell_00       lector local estable
auto_cell_01 célula automática oeste / Chile central
```

## Nuevas rutas

```text
/api/network/state
/api/cells
/api/cells/auto_cell_01
```

## Participación del ESP32

No hace falta cambiar todavía el sketch. El ESP32 sigue consultando la misma URL.

La respuesta ahora incluye campos multicelda como:

```text
network_mode
network_label
cells_active
early_warning_cells_active
auto_cell_01_fresh
auto_cell_01_aviso_util
```

Además, si `auto_cell_01` está viva, `calidad_red` pasa a reflejar la red multicelda y los sensores activos/calibrados pasan a sumar las células activas.

## Arranque

```bash
cd ~/cuyum_v_1_1
./iniciar_cuyum_visible_v1_1.sh
```

Ese arranque inicia automáticamente:

```text
servidor Flask multicelda
lector local cell_00
lector auto_cell_01
descubridor periódico
auditor de sensores
```

## Ver estado multicelda

```bash
cd ~/cuyum_v_1_1
./ver_multicelda_v1_1.sh
```

## Apagado

```bash
cd ~/cuyum_v_1_1
./detener_cuyum_v1_1.sh
```

## Criterio de seguridad

- Si `auto_cell_01` está normal, el ESP32 no suena.
- Si `auto_cell_01` queda vieja o detenida, no se usa para la fusión.
- Una anticipación desde `auto_cell_01` solo activa salida al ESP32 si hay flag grupal y al menos 2 estaciones confirmando dentro de la célula.
- El sistema sigue siendo experimental y no reemplaza fuentes oficiales.
