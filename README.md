# Cuyum 1.3

Cuyum es un sistema experimental de monitoreo sísmico multicelda basado en datos SeedLink.

Escucha estaciones sísmicas remotas, organiza sensores alrededor de un centro geográfico, mantiene estado vivo local, fusiona información de varias celdas y publica un monitor web junto con salidas JSON para visualización, nodos externos y dispositivos ESP32.

> Cuyum no reemplaza fuentes sísmicas oficiales, sistemas certificados de alerta temprana ni procedimientos institucionales de emergencia.

## Características

- Lectura en vivo mediante SeedLink.
- Celda local y hasta cuatro celdas regionales.
- Organización automática de sensores según ubicación.
- Evaluación de disponibilidad y latencia.
- Fusión multicelda.
- Registro reciente de eventos confirmados.
- Monitor web público.
- Salidas JSON.
- Interfaz compacta para ESP32.
- Publicación opcional en Telegram.
- Recentrado geográfico del sistema.
- Despliegue público mediante Docker Compose y Caddy.

## Interfaces públicas

Instalación pública oficial:

```text
https://cuyum.ar/app
https://cuyum.ar/json
https://cuyum.ar/reg
https://cuyum.ar/lite
```

Rutas principales:

```text
/app                 monitor humano
/json                estado vivo canónico
/reg                 registros públicos recientes
/lite                interfaz compacta para ESP32
/health              comprobación básica del servidor
/api/network/state   estado técnico de la red
/api/cells/<cell_id> estado técnico de una celda
```

## Dos formas de ejecutar Cuyum

Cuyum puede ejecutarse de dos maneras. No deben mezclarse los comandos de una modalidad con la otra.

### Modo tradicional

Se inicia con:

```bash
./start_cuyum.sh
```

Se detiene con:

```bash
./stop_cuyum.sh
```

En esta modalidad los procesos Python se ejecutan directamente en el sistema.

### Modo Docker

Se inicia con:

```bash
docker compose up -d --build
```

Se detiene con:

```bash
docker compose down
```

Si el usuario no tiene permisos para acceder a Docker:

```bash
sudo docker compose up -d --build
sudo docker compose down
```

En esta modalidad `./stop_cuyum.sh` no detiene los contenedores. Docker puede volver a iniciar procesos terminados manualmente porque el servicio usa `restart: unless-stopped`.

## Ejecución local tradicional

Requisitos:

- Linux o Xubuntu.
- Python 3.13.
- ObsPy 1.5.0.
- Conexión a Internet para FDSN y SeedLink.

Instalación:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Arranque:

```bash
./start_cuyum.sh
```

Monitor local:

```text
http://127.0.0.1:5050/app
```

Detención:

```bash
./stop_cuyum.sh
```

## Despliegue público con Docker

Arquitectura:

```text
Internet
   |
HTTPS 443
   |
Caddy
   |
red interna de Docker
   |
Cuyum:5050
```

El puerto `5050` no se publica directamente en Internet.

Preparación básica:

```bash
cp setup.env.example setup.env
mkdir -p runtime persistent secrets
nano setup.env
nano secrets/telegram_bot_token.txt
chmod 600 setup.env secrets/telegram_bot_token.txt
docker compose up -d --build
```

Comprobación:

```bash
docker compose ps
docker compose logs --tail=100 cuyum
docker compose logs --tail=100 caddy
```

Detención completa:

```bash
docker compose down
```

Manual completo:

```text
docs/VPS_DEPLOYMENT.md
```

## Configuración de Telegram

El identificador del canal o grupo se guarda en `setup.env`:

```text
TELEGRAM_CHAT_ID=-1000000000000
```

El token del bot se guarda exclusivamente en:

```text
secrets/telegram_bot_token.txt
```

El token, `setup.env` y todo el directorio `secrets/` están excluidos de Git.

## Firmware ESP32

Firmware:

```text
firmware/esp32/cuyum_esp32/cuyum_esp32.ino
```

Plantilla pública:

```text
firmware/esp32/cuyum_esp32/config.example.h
```

Configuración privada:

```text
firmware/esp32/cuyum_esp32/config.h
```

Preparación:

```bash
cp firmware/esp32/cuyum_esp32/config.example.h    firmware/esp32/cuyum_esp32/config.h
```

Luego se completan en `config.h`:

```cpp
const char* WIFI_SSID = "...";
const char* WIFI_PASSWORD = "...";
const char* STATUS_URL = "https://cuyum.ar/lite";
```

`config.h` está excluido de Git para evitar publicar credenciales Wi-Fi.

El firmware admite:

```text
https://cuyum.ar/lite
http://IP_LOCAL:5050/lite
```

## Recentrar Cuyum

```bash
./scripts/cuyum_recenter_live.sh "Mendoza" -32.8895 -68.8458
```

## Estado multicelda

```bash
./scripts/show_multicell_status.sh
```

## Directorios persistentes y privados

```text
runtime/      estado temporal y registros de ejecución
persistent/   información que debe sobrevivir reconstrucciones
secrets/      secretos privados de la instalación
config/       configuración e inventarios activos
```

En Docker, estos directorios se montan desde el host dentro del contenedor.

## Documentación

```text
docs/API.md
docs/ARCHITECTURE.md
docs/VPS_DEPLOYMENT.md
docs/CONFIRMED_MULTISIGNALS_SCHEMA.md
docs/language.md
```

## Estado del proyecto

Cuyum 1.3 es software experimental para educación, observación y validación técnica. No debe interpretarse como un sistema oficial de alerta sísmica.

## Licencia

Cuyum se distribuye bajo GNU General Public License v3.0 or later.

Ver `LICENSE`.
