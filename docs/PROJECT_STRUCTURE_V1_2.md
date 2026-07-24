# Estructura enseñable de Cuyum v1.2

## Idea general

Cuyum se organiza en partes simples:

1. Lectores SeedLink
2. Archivos JSON de estado
3. Fusión multicelda
4. Servidor Cuyum
5. Monitor live
6. ESP32 / clientes externos

## Lectores

Los lectores escuchan datos sísmicos y producen estado local.

Ejemplos:

- `cell_00_seedlink_reader.py`
- `auto_cell_seedlink_reader.py`

## Estado runtime

Los lectores escriben JSON. Estos archivos son datos vivos del sistema.

No se editan manualmente durante operación normal.

## Fusión

`multicell_fusion.py` combina las celdas y decide el estado general de la red.

## Servidor

`plain_python_server.py` publica:

- el monitor live,
- la API pública,
- la compatibilidad para ESP32.

## API pública limpia

`public_api_v1.py` transforma datos internos legacy en una salida pública ordenada.

Rutas principales:

- `/json`
- `/api/v1/cells`
- `/api/v1/sensors`
- `/reg`

## Monitor live

Archivos:

- `templates/app_cuyum.html`
- `static/app_cuyum.js`
- `static/app_cuyum.css`

## Legacy

Los archivos viejos o reemplazados se guardan en:

- `quarantine_v1_2/`

No se borran hasta confirmar que el sistema funciona varios días sin ellos.
