# Cuyum 1.3

Cuyum es un sistema experimental de monitoreo sísmico multicelda basado en datos SeedLink.

Escucha estaciones sísmicas remotas, organiza sensores alrededor de un centro geográfico, mantiene estado vivo, fusiona información de varias celdas y publica un monitor web junto con salidas JSON para visualización, nodos externos y dispositivos ESP32.

> Cuyum no reemplaza fuentes sísmicas oficiales, sistemas certificados de alerta temprana ni procedimientos institucionales de emergencia.

## Forma oficial de ejecución

Cuyum 1.3 se instala, inicia, detiene, actualiza y ejecuta exclusivamente mediante Docker Compose.

No existen modos alternativos soportados.


## Arquitectura

```text
Internet
   |
HTTP 80 / HTTPS 443
   |
Caddy
   |
red interna de Docker
   |
Cuyum:5050
   |
lectores SeedLink, fusión multicelda, API y monitor web
```

El puerto `5050` es interno y no debe publicarse directamente en Internet.

## Interfaces públicas

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

## Requisitos

- Linux.
- Docker Engine.
- Docker Compose.
- Dominio apuntando al servidor para el despliegue público.
- Puertos 80 y 443 disponibles.

## Preparación

```bash
git clone https://github.com/abelseru/cuyum.git
cd cuyum

cp setup.env.example setup.env
mkdir -p runtime persistent secrets
```

Editar:

```bash
nano setup.env
nano secrets/telegram_bot_token.txt
chmod 600 setup.env secrets/telegram_bot_token.txt
```

## Iniciar Cuyum

```bash
docker compose up -d --build
```

Cuando el usuario no tenga permisos sobre Docker:

```bash
sudo docker compose up -d --build
```

## Verificar

```bash
docker compose ps
docker compose logs --tail=100 cuyum
docker compose logs --tail=100 caddy
```

Pruebas HTTP:

```bash
curl -sS -o /dev/null -w 'GET /app: HTTP %{http_code}\n' https://cuyum.ar/app
curl -sS -o /dev/null -w 'GET /lite: HTTP %{http_code}\n' https://cuyum.ar/lite
```

## Detener Cuyum

```bash
docker compose down
```

Con permisos administrativos:

```bash
sudo docker compose down
```

No se deben matar procesos Python individualmente. El contenedor utiliza `restart: unless-stopped` y Docker puede volver a iniciarlos.

## Reiniciar

```bash
docker compose restart
```

## Actualizar

```bash
git pull --ff-only origin main
docker compose up -d --build
docker compose ps
```

## Telegram

El destino se configura en `setup.env`:

```text
TELEGRAM_CHAT_ID=-1000000000000
```

El token se guarda únicamente en:

```text
secrets/telegram_bot_token.txt
```

`setup.env` y `secrets/` están excluidos de Git.

## Firmware ESP32

```text
firmware/esp32/cuyum_esp32/cuyum_esp32.ino
firmware/esp32/cuyum_esp32/config.example.h
```

Crear la configuración privada:

```bash
cp firmware/esp32/cuyum_esp32/config.example.h    firmware/esp32/cuyum_esp32/config.h
```

La URL pública recomendada es:

```cpp
const char* STATUS_URL = "https://cuyum.ar/lite";
```

`config.h` está excluido de Git.

## Datos persistentes

```text
runtime/      estado temporal y registros de ejecución
persistent/   información que debe sobrevivir reconstrucciones
config/       configuración e inventarios activos
secrets/      secretos privados
```

## Documentación

```text
docs/API.md
docs/ARCHITECTURE.md
docs/VPS_DEPLOYMENT.md
docs/CONFIRMED_MULTISIGNALS_SCHEMA.md
docs/language.md
```

## Licencia

GNU General Public License v3.0 or later. Ver `LICENSE`.
