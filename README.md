# Cuyum v1.2

Cuyum es un sistema experimental de monitoreo sísmico multicelda basado en datos SeedLink.

Escucha estaciones sísmicas remotas, organiza sensores alrededor de un centro geográfico, mantiene estado vivo local, fusiona información de varias celdas y publica un monitor web junto con salidas JSON para visualización y nodos externos.

> Cuyum no reemplaza fuentes sísmicas oficiales, sistemas certificados de alerta temprana ni procedimientos institucionales de emergencia.

## Características

- Lectura en vivo mediante SeedLink.
- Celda local y hasta cuatro celdas regionales.
- Organización automática de sensores según ubicación.
- Evaluación de disponibilidad y latencia.
- Fusión multicelda.
- Registro reciente de eventos.
- Monitor web.
- Salida JSON.
- Interfaces para nodos y ESP32.
- Recentrado geográfico del sistema.

## Requisitos

- Linux / Xubuntu
- Python 3.13
- ObsPy 1.5.0
- conexión a Internet para servicios FDSN y SeedLink

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Arranque

```bash
./start_cuyum_v1_2.sh
```

Monitor local:

```text
http://127.0.0.1:5050/app
```

## Detención

```bash
./stop_cuyum_v1_2.sh
```

## Recentrar Cuyum

```bash
./scripts/cuyum_recenter_live.sh "Mendoza" -32.8895 -68.8458
```

## Estado multicelda

```bash
./scripts/show_multicell_status_v1_2.sh
```

## Rutas principales

Públicas:

```text
/app
/json
/reg
```

Internas / dispositivos:

```text
/health
/api/node/poll?node_id=node_01
/api/esp32/poll?node_id=node_01
/api/network/state
/api/cells/<cell_id>
```

## Estructura

```text
cuyum_v_1_2/
├── app/
├── config/
├── docs/
├── scripts/
├── static/
├── templates/
├── requirements.txt
├── start_cuyum_v1_2.sh
└── stop_cuyum_v1_2.sh
```

`runtime/`, `runtime_logs/`, entornos virtuales, backups y archivos de desarrollo local no forman parte del repositorio.

## Idioma técnico

El núcleo técnico usa inglés para variables, estados, contratos JSON y logs. La interfaz para usuarios puede presentar traducciones al español.

Ver `docs/language.md`.

## Estado del proyecto

Cuyum v1.2 es software experimental para educación, observación y validación técnica. No debe interpretarse como un sistema oficial de alerta sísmica.

## Licencia

Cuyum se distribuye bajo GNU General Public License v3.0 or later (GPL-3.0-or-later).
Ver el archivo `LICENSE`.
