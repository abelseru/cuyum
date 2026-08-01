# Cuyum 1.3 — Arquitectura

## Regla de operación

Cuyum 1.3 se ejecuta exclusivamente mediante Docker Compose.

No se soporta la ejecución directa de procesos Python desde el host. Los antiguos scripts de inicio y detención fueron retirados para evitar procesos duplicados, conflictos con el puerto `5050` y diferencias entre instalaciones.

## Flujo general

```text
FDSN / SeedLink
       |
catálogo e inventarios
       |
lectores de celdas
       |
fusión multicelda
       |
servidor HTTP interno
       |
Caddy
       |
HTTPS público
       |
web, JSON, Telegram y ESP32
```

## Servicios Docker

### cuyum

- Se construye desde `Dockerfile`.
- Ejecuta `docker-entrypoint.sh`.
- Usa Python 3.13.
- Escucha en el puerto interno `5050`.
- No publica el puerto `5050` en el host.
- Monta `config/`, `runtime/`, `persistent/` y `secrets/`.
- Usa `restart: unless-stopped`.

### caddy

- Usa `caddy:2-alpine`.
- Publica los puertos 80 y 443.
- Gestiona HTTPS.
- Reenvía solicitudes a `cuyum:5050`.
- Espera a que Cuyum esté saludable.

## Procesos internos

`docker-entrypoint.sh` administra los procesos de Cuyum dentro del contenedor:

- lector de la celda local;
- lectores de celdas automáticas;
- descubrimiento SeedLink periódico;
- auditor de sensores;
- servidor HTTP.

No deben iniciarse copias paralelas de estos procesos en el host.

## Arranque y detención

Inicio:

```bash
docker compose up -d --build
```

Detención:

```bash
docker compose down
```

No se deben usar `pkill`, `kill` ni scripts heredados como mecanismo normal de detención.

## Red

```text
Internet -> Caddy:443 -> cuyum:5050
```

Puertos públicos:

```text
80/tcp
443/tcp
443/udp
```

Puerto interno:

```text
5050/tcp
```

## Persistencia

```text
./runtime     -> /app/runtime
./persistent  -> /app/persistent
./config      -> /app/config
./secrets     -> /app/secrets, solo lectura
```

## Archivos generados durante la ejecución

Cuyum puede modificar inventarios como:

```text
config/candidate_inventory.json
config/sensor_catalog.json
```

Antes de restaurarlos con Git se debe detener Cuyum mediante:

```bash
docker compose down
```

## Componentes principales

- `app/cell_00_seedlink_reader.py`
- `app/auto_cell_seedlink_reader.py`
- `app/live_inventory_organizer.py`
- `app/multicell_fusion.py`
- `app/plain_python_server.py`
- `app/telegram_notice.py`
- `docker-entrypoint.sh`
- `compose.yaml`
- `Caddyfile`

## Advertencia

Cuyum es experimental y no constituye un sistema certificado de alerta sísmica.
