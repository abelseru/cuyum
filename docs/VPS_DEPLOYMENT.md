# Cuyum 1.3 — Despliegue en VPS

Este es el único procedimiento soportado para instalar y operar Cuyum 1.3.

## 1. Arquitectura

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
```

El puerto `5050` no debe exponerse directamente.

## 2. Requisitos

- VPS Linux.
- Acceso administrativo.
- Dominio apuntando a la IP pública.
- Git.
- Docker Engine.
- Docker Compose.
- Puertos 80 y 443 disponibles.

## 3. Clonar desde main

```bash
cd /opt
git clone https://github.com/abelseru/cuyum.git
cd cuyum
git switch main
```

Comprobar:

```bash
git branch --show-current
git log -2 --oneline
```

## 4. Configuración privada

```bash
cp setup.env.example setup.env
mkdir -p runtime persistent secrets
nano setup.env
nano secrets/telegram_bot_token.txt
chmod 600 setup.env secrets/telegram_bot_token.txt
```

Ejemplo de `setup.env`:

```text
CUYUM_DOMAIN=cuyum.ar
TELEGRAM_CHAT_ID=-1000000000000
```

El token de Telegram debe quedar solamente en:

```text
secrets/telegram_bot_token.txt
```

## 5. Validar

```bash
docker compose config >/dev/null &&
echo "Compose válido"
```

## 6. Iniciar

```bash
docker compose up -d --build
docker compose ps
```

El servicio `cuyum` debe aparecer como `healthy`.

## 7. Verificar HTTPS

```bash
curl -sS -o /dev/null -w 'GET /app: HTTP %{http_code}\n' https://cuyum.ar/app
curl -sS -o /dev/null -w 'GET /lite: HTTP %{http_code}\n' https://cuyum.ar/lite
```

La respuesta esperada es `HTTP 200`.

No usar `curl -I` para `/app`, porque envía una petición `HEAD` y el servidor puede responder `501` aunque la ruta funcione correctamente con `GET`.

## 8. Logs

```bash
docker compose logs --tail=100 cuyum
docker compose logs --tail=100 caddy
docker compose logs -f
```

## 9. Detener correctamente

```bash
docker compose down
```

No matar procesos Python individualmente. Docker puede reiniciarlos automáticamente.

## 10. Reiniciar

```bash
docker compose restart
```

## 11. Actualizar desde GitHub

```bash
cd /opt/cuyum
git status
git pull --ff-only origin main
docker compose up -d --build
docker compose ps
```

Si `git status` muestra solamente inventarios generados por Cuyum, primero detener:

```bash
docker compose down
```

Luego decidir conscientemente si se conservan o se restauran. No hacer restauraciones con el contenedor activo.

## 12. Confirmar que 5050 no está publicado

```bash
docker compose ps
```

Para `cuyum` debe verse:

```text
5050/tcp
```

No debe verse:

```text
0.0.0.0:5050->5050/tcp
```

## 13. Copias de seguridad

Respaldar:

```text
setup.env
secrets/
persistent/
config/
```

Ejemplo:

```bash
tar -czf   cuyum-backup-$(date +%Y%m%d-%H%M%S).tar.gz   setup.env secrets persistent config
```

## 14. Diagnóstico

Procesos que reaparecen después de usar `pkill` indican que Docker continúa activo.

Comprobar:

```bash
docker compose ps
sudo ss -ltnp | grep ':5050' || true
```

Detener correctamente:

```bash
docker compose down
```

## 15. Qué no hacer

- No usar scripts heredados de inicio o detención.
- No ejecutar procesos Python de Cuyum directamente en el host.
- No publicar el puerto `5050`.
- No subir `setup.env`.
- No subir `secrets/`.
- No subir el `config.h` real del ESP32.
- No restaurar inventarios mientras Cuyum está activo.
- No usar el VPS como única copia del código.

## 16. Lista de comprobación

```text
[ ] El VPS usa la rama main
[ ] setup.env existe
[ ] El token de Telegram existe
[ ] Compose es válido
[ ] Cuyum está healthy
[ ] Caddy está activo
[ ] /app devuelve HTTP 200
[ ] /lite devuelve HTTP 200
[ ] 5050 no está publicado
[ ] GitHub y VPS apuntan al mismo commit
```

## Advertencia

Cuyum es experimental. No reemplaza información sísmica oficial ni sistemas certificados de alerta temprana.
