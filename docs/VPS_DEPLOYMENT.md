# Cuyum 1.3 — Despliegue en VPS con Docker y Caddy

Este manual describe el despliegue actual de Cuyum mediante Docker Compose y Caddy.

La arquitectura anterior basada en ejecución directa, entorno virtual, Nginx, Certbot y un servicio systemd propio ya no corresponde a este procedimiento.

## 1. Arquitectura resultante

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

El puerto `5050` existe dentro del contenedor, pero no queda publicado directamente en Internet.

## 2. Importante: no mezclar modos de ejecución

El modo tradicional usa:

```bash
./start_cuyum.sh
./stop_cuyum.sh
```

El modo Docker usa:

```bash
docker compose up -d --build
docker compose down
```

`./stop_cuyum.sh` no detiene un contenedor Docker.

Si se matan manualmente procesos Python dentro del contenedor, Docker puede volver a iniciarlos porque el servicio tiene:

```text
restart: unless-stopped
```

Para detener Docker correctamente se debe usar:

```bash
docker compose down
```

Si el usuario no tiene permisos sobre Docker:

```bash
sudo docker compose down
```

## 3. Requisitos

- VPS Linux con acceso administrativo.
- Dominio propio.
- Registro DNS del dominio apuntando a la IP pública del VPS.
- Git.
- Docker Engine.
- Complemento Docker Compose.
- Puertos públicos 80 y 443 disponibles.

## 4. DNS

Crear un registro `A`:

```text
cuyum.example.com -> IP_PUBLICA_DEL_VPS
```

Comprobar:

```bash
getent hosts cuyum.example.com
```

## 5. Obtener el proyecto

```bash
cd /opt
git clone https://github.com/USUARIO/cuyum.git
cd cuyum
```

## 6. Crear la configuración privada

```bash
cp setup.env.example setup.env
nano setup.env
chmod 600 setup.env
```

Ejemplo:

```text
CUYUM_DOMAIN=cuyum.example.com
TELEGRAM_CHAT_ID=-1000000000000
```

## 7. Preparar directorios persistentes

```bash
mkdir -p runtime persistent secrets
```

## 8. Instalar el token de Telegram

```bash
nano secrets/telegram_bot_token.txt
chmod 600 secrets/telegram_bot_token.txt
```

El archivo debe contener solamente el token, en una línea y sin comillas.

## 9. Validar Compose

```bash
docker compose config >/dev/null &&
echo "Compose válido"
```

Con `sudo`, cuando sea necesario:

```bash
sudo docker compose config >/dev/null &&
echo "Compose válido"
```

## 10. Construir y arrancar

```bash
docker compose up -d --build
docker compose ps
```

O con permisos administrativos:

```bash
sudo docker compose up -d --build
sudo docker compose ps
```

## 11. Detener correctamente

Detener y eliminar contenedores y red del proyecto:

```bash
docker compose down
```

Con `sudo`:

```bash
sudo docker compose down
```

Detener sin eliminar los contenedores:

```bash
docker compose stop
```

Volver a iniciarlos:

```bash
docker compose start
```

No usar `./stop_cuyum.sh` para detener el despliegue Docker.

## 12. Comprobar el sitio público

```bash
curl -I https://cuyum.example.com/app
curl -s https://cuyum.example.com/health
curl -s https://cuyum.example.com/lite
```

## 13. Comprobar que 5050 no esté expuesto

```bash
docker compose ps
```

Para Cuyum debería aparecer solamente:

```text
5050/tcp
```

No debería aparecer:

```text
0.0.0.0:5050->5050/tcp
```

## 14. Logs

```bash
docker compose logs --tail=100 cuyum
docker compose logs --tail=100 caddy
docker compose logs -f
```

## 15. Estado y salud

```bash
docker compose exec -T cuyum   python -c   "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5050/lite', timeout=4).status)"
```

El resultado esperado es `200`.

## 16. Telegram

```bash
docker compose exec -T cuyum sh -c '
test -n "$TELEGRAM_CHAT_ID" &&
echo "TELEGRAM_CHAT_ID configurado"
'
```

El token se lee desde:

```text
/app/secrets/telegram_bot_token.txt
```

## 17. Actualizar desde Git

```bash
git status
git pull --ff-only
docker compose up -d --build
docker compose ps
```

## 18. Copias de seguridad

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

## 19. Diagnóstico de procesos que reaparecen

Si se matan procesos Python y vuelven a aparecer con PID nuevos, comprobar:

```bash
sudo ss -ltnp | grep ':5050' || true
sudo docker compose ps
```

Si aparece `docker-proxy` o el contenedor `cuyum`, detener con:

```bash
sudo docker compose down
```

No continuar restaurando archivos generados por Git mientras Cuyum siga activo, porque volverán a modificarse.

## 20. Qué no hacer

- No publicar el puerto `5050` directamente en Internet.
- No subir `setup.env` a Git.
- No subir `secrets/`.
- No subir el `config.h` real del ESP32.
- No escribir tokens ni identificadores reales dentro del código.
- No borrar `persistent/` durante una actualización.
- No detener Docker mediante `./stop_cuyum.sh`.
- No matar individualmente procesos administrados por Docker.
- No usar el VPS como única copia del código fuente.

## 21. Lista de comprobación

```text
[ ] El dominio apunta al VPS
[ ] Docker y Compose están instalados
[ ] setup.env existe
[ ] El token de Telegram existe
[ ] docker compose config es válido
[ ] cuyum está saludable
[ ] caddy está en ejecución
[ ] /app responde por HTTPS
[ ] /lite responde por HTTPS
[ ] 5050 no está publicado en Internet
[ ] Telegram puede enviar
[ ] El ESP32 consulta la URL HTTPS pública
```

## Advertencia

Cuyum es experimental. No reemplaza información sísmica oficial, sistemas certificados de alerta temprana ni procedimientos institucionales de emergencia.

## Licencia

Cuyum se distribuye bajo GNU General Public License v3.0 or later.

Ver `LICENSE`.
