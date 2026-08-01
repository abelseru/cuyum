# Cuyum 1.3 — Arquitectura

## Flujo general

```text
FDSN / SeedLink
       |
catálogo de estaciones
       |
inventario de candidatos
       |
organizador de inventario vivo
       |
lectores de celdas
       |
fusión multicelda
       |
servidor HTTP de Cuyum
       |
Caddy / HTTPS
       |
web, JSON, Telegram y ESP32
```

## Componentes principales

- `app/cell_00_seedlink_reader.py`: lector de la celda local.
- `app/auto_cell_seedlink_reader.py`: lector reutilizable para las celdas regionales automáticas.
- `app/live_inventory_organizer.py`: construye y mantiene las selecciones de sensores locales y regionales.
- `app/multicell_fusion.py`: combina los estados de las distintas celdas en un estado de red.
- `app/event_journal.py`: administra registros recientes de ejecución.
- `app/plain_python_server.py`: servidor HTTP interno de Cuyum; escucha en el puerto `5050`.
- `app/telegram_notice.py`: genera y envía publicaciones a Telegram.

Telegram obtiene el destino desde `TELEGRAM_CHAT_ID` y el token desde `secrets/telegram_bot_token.txt`.

## Modalidades de ejecución

### Tradicional

Los procesos Python se ejecutan directamente en el sistema.

```bash
./start_cuyum.sh
./stop_cuyum.sh
```

### Docker

Los procesos Python se ejecutan dentro del contenedor `cuyum`.

```bash
docker compose up -d --build
docker compose down
```

Si el usuario no tiene permisos sobre `/var/run/docker.sock`, debe usar `sudo` o configurar correctamente su pertenencia al grupo `docker`.

`./stop_cuyum.sh` no detiene un contenedor Docker.

## Procesos dentro del contenedor

`docker-entrypoint.sh` inicia:

1. limpieza por retención;
2. lector de `cell_00`;
3. lectores automáticos regionales;
4. revisión SeedLink periódica cada 15 minutos;
5. auditor de sensores;
6. servidor HTTP.

Si muere uno de los procesos principales, el contenedor finaliza con error. Docker Compose puede reiniciarlo mediante:

```text
restart: unless-stopped
```

Por eso no debe intentarse detener Docker matando procesos Python individualmente. Se debe usar `docker compose down` o `docker compose stop`.

## Arquitectura Docker

Servicios:

```text
cuyum
caddy
```

### Servicio cuyum

- Se construye desde `Dockerfile`.
- Usa Python 3.13.
- Escucha internamente en `5050`.
- No publica ese puerto en el host.
- Recibe variables desde `setup.env`.
- Monta configuración, estado, datos persistentes y secretos.

### Servicio caddy

- Usa la imagen `caddy:2-alpine`.
- Publica los puertos `80` y `443`.
- Espera a que Cuyum esté saludable.
- Reenvía las solicitudes a `cuyum:5050`.
- Conserva certificados y configuración interna en volúmenes Docker.

## Persistencia

```text
./runtime     -> /app/runtime
./persistent  -> /app/persistent
./config      -> /app/config
./secrets     -> /app/secrets, solo lectura
```

## Seguridad de red

Los únicos puertos web publicados por el despliegue son:

```text
80/tcp
443/tcp
443/udp
```

El puerto `5050` permanece dentro de la red de Docker.

## Advertencia

Cuyum es experimental y no constituye un sistema certificado de alerta sísmica.
