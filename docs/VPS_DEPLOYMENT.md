# Cuyum v1.2 — Manual de despliegue en VPS

Este manual explica cómo instalar **Cuyum v1.2** en un VPS Linux partiendo de una máquina vacía, tal como lo haría cualquier escuela, docente, laboratorio o institución que descargue el proyecto desde GitHub.

Objetivo final:

```text
https://cuyum.ar/app
https://cuyum.ar/json
https://cuyum.ar/reg
```

> Cuyum es experimental. No reemplaza fuentes sísmicas oficiales, sistemas certificados de alerta temprana ni procedimientos institucionales de emergencia.

## 1. Arquitectura

```text
Estaciones sísmicas / SeedLink
            |
            v
         Cuyum
     127.0.0.1:5050
            |
            v
          Nginx
        80 / 443
            |
            v
          HTTPS
            |
            v
        cuyum.ar
```

- **GitHub**: fuente oficial del código.
- **VPS**: computadora Linux encendida 24/7.
- **venv**: entorno Python aislado.
- **SeedLink**: entrada de datos sísmicos.
- **Cuyum**: procesa sensores y publica estado.
- **systemd**: inicia y detiene Cuyum como servicio.
- **Nginx**: recibe conexiones públicas y las pasa a Cuyum.
- **DNS**: hace que `cuyum.ar` apunte al VPS.
- **HTTPS**: cifra la comunicación.

# PARTE A — Preparar el VPS

## 2. Contratar el VPS

Conviene elegir Ubuntu LTS o Debian estable. El proveedor entregará normalmente:

```text
IP pública: AAA.BBB.CCC.DDD
usuario inicial: root
contraseña o clave SSH
```

En este manual `AAA.BBB.CCC.DDD` debe reemplazarse por la IP real.

## 3. Entrar por SSH

Desde una PC Linux:

```bash
ssh root@AAA.BBB.CCC.DDD
```

A partir de aquí los comandos se ejecutan dentro del VPS salvo que se indique lo contrario.

## 4. Actualizar e instalar herramientas

```bash
apt update
apt upgrade -y
apt install -y git python3 python3-venv python3-pip nginx
```

Comprobar:

```bash
python3 --version
git --version
nginx -v
```

# PARTE B — Instalar Cuyum

## 5. Clonar desde GitHub

```bash
cd /opt
git clone https://github.com/abelseru/cuyum.git
cd cuyum
```

Seleccionar exactamente la versión 1.2.0:

```bash
git fetch --tags
git checkout v1.2.0
git describe --tags --exact-match
```

Debe mostrar:

```text
v1.2.0
```

No se copia la carpeta personal de desarrollo. No se trasladan manualmente `venv/`, `runtime/`, `runtime_logs/`, backups, snapshots ni `local_archive/`.

## 6. Crear el entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Comprobar ObsPy:

```bash
python -c "import obspy; print(obspy.__version__)"
```

# PARTE C — Primera ejecución

## 7. Arrancar manualmente

```bash
cd /opt/cuyum
source venv/bin/activate
./start_cuyum_v1_2.sh
```

El arranque debe comprobar, entre otras, estas rutas:

```text
200  http://127.0.0.1:5050/app
200  http://127.0.0.1:5050/json
200  http://127.0.0.1:5050/reg
200  http://127.0.0.1:5050/lite
```

La red puede tardar un poco en pasar de `local_only` a `multicell` mientras se estabilizan las fuentes SeedLink.

## 8. Probar desde el VPS

```bash
curl http://127.0.0.1:5050/json
```

Las interfaces públicas canónicas son:

```text
/app
/json
/reg
```

No deben crearse rutas públicas paralelas para representar lo mismo.

## 9. Detener la prueba

```bash
./stop_cuyum_v1_2.sh
ss -ltnp | grep ':5050' || true
```

# PARTE D — Configurar el dominio

## 10. DNS de cuyum.ar

En el panel DNS crear un registro A:

```text
Tipo: A
Nombre: @
Valor: AAA.BBB.CCC.DDD
```

Para `www.cuyum.ar`, usar otro A o un CNAME hacia `cuyum.ar` según el proveedor.

Comprobar después de la propagación:

```bash
getent hosts cuyum.ar
```

La IP devuelta debe coincidir con la IP pública del VPS.

# PARTE E — Nginx

## 11. Objetivo

No conviene publicar Cuyum como `http://cuyum.ar:5050`. Nginx será la puerta de entrada:

```text
Internet :443
     |
   Nginx
     |
127.0.0.1:5050
     |
   Cuyum
```

## 12. Configurar Nginx

Crear:

```bash
nano /etc/nginx/sites-available/cuyum
```

Contenido:

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name cuyum.ar www.cuyum.ar;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }
}
```

Activar:

```bash
ln -s /etc/nginx/sites-available/cuyum /etc/nginx/sites-enabled/cuyum
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

# PARTE F — systemd

## 13. Por qué systemd

El VPS puede reiniciarse. Cuyum debe volver sin intervención manual.

La versión 1.2 inicia varios procesos en segundo plano mediante sus scripts actuales. Para desplegarla sin introducir una arquitectura paralela, systemd envolverá esos scripts.

## 14. Crear el servicio

Crear:

```bash
nano /etc/systemd/system/cuyum.service
```

Contenido inicial:

```ini
[Unit]
Description=Cuyum v1.2 seismic monitoring
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/cuyum
ExecStart=/opt/cuyum/start_cuyum_v1_2.sh
ExecStop=/opt/cuyum/stop_cuyum_v1_2.sh
User=root

[Install]
WantedBy=multi-user.target
```

Esta configuración conserva exactamente el modelo operativo actual de Cuyum. Más adelante puede endurecerse con un usuario de servicio dedicado.

## 15. Activar el servicio

```bash
systemctl daemon-reload
systemctl enable cuyum
systemctl start cuyum
systemctl status cuyum
```

Probar:

```bash
curl http://127.0.0.1:5050/json
```

Comandos habituales:

```bash
systemctl start cuyum
systemctl stop cuyum
systemctl restart cuyum
systemctl status cuyum
```

# PARTE G — Firewall

## 16. Puertos públicos

Normalmente sólo deben exponerse:

```text
22/tcp   SSH
80/tcp   HTTP
443/tcp  HTTPS
```

No hace falta publicar 5050 directamente a Internet.

Con UFW:

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

Antes de activar un firewall remoto, comprobar siempre que SSH esté permitido.

# PARTE H — HTTPS

## 17. Antes del certificado

Deben cumplirse estas condiciones:

1. `cuyum.ar` apunta a la IP correcta.
2. Nginx está activo.
3. El puerto 80 es accesible desde Internet.
4. Cuyum responde detrás de Nginx.

Probar desde una conexión externa:

```text
http://cuyum.ar/app
```

## 18. Instalar Certbot

Las instrucciones de Certbot pueden cambiar. Para Ubuntu conviene consultar la guía oficial para la versión exacta del sistema y Nginx.

Una instalación habitual mediante Snap es:

```bash
apt install -y snapd
snap install core
snap refresh core
snap install --classic certbot
ln -s /snap/bin/certbot /usr/local/bin/certbot
```

Si el enlace ya existe, no se recrea.

## 19. Obtener HTTPS

```bash
certbot --nginx -d cuyum.ar -d www.cuyum.ar
```

Después comprobar:

```text
https://cuyum.ar/app
https://cuyum.ar/json
https://cuyum.ar/reg
```

Probar renovación automática:

```bash
certbot renew --dry-run
```

# PARTE I — Prueba de reinicio

## 20. La prueba decisiva

```bash
reboot
```

Después volver por SSH y comprobar:

```bash
systemctl status cuyum
systemctl status nginx
curl http://127.0.0.1:5050/json
```

Finalmente, desde un navegador externo:

```text
https://cuyum.ar/app
```

Si funciona después del reinicio, la instalación básica 24/7 está completa.

# PARTE J — Recentrar Cuyum

## 21. Cambiar el centro

Ejemplo Mendoza:

```bash
cd /opt/cuyum
./scripts/cuyum_recenter_live.sh "Mendoza" -32.8895 -68.8458
```

Después esperar la estabilización y revisar:

```bash
./scripts/show_multicell_status_v1_2.sh
```

# PARTE K — Actualizar Cuyum

## 22. Instalar una nueva versión

Supongamos que se publica `v1.2.1`:

```bash
systemctl stop cuyum
cd /opt/cuyum
git fetch --tags
git checkout v1.2.1
source venv/bin/activate
python -m pip install -r requirements.txt
systemctl start cuyum
```

Comprobar:

```bash
systemctl status cuyum
curl http://127.0.0.1:5050/json
```

Para una instalación fijada a tags es preferible saber exactamente qué versión se ejecuta, en lugar de usar `git pull` a ciegas.

# PARTE L — Diagnóstico

## 23. Cuyum no responde

```bash
systemctl status cuyum
ss -ltnp | grep ':5050'
curl http://127.0.0.1:5050/json
```

Si `/json` funciona localmente pero el dominio no, el problema probablemente está en Nginx, DNS, HTTPS o firewall.

## 24. Nginx no responde

```bash
systemctl status nginx
nginx -t
journalctl -u nginx --no-pager -n 100
```

## 25. Hay pocas estaciones

```bash
cd /opt/cuyum
./scripts/show_multicell_status_v1_2.sh
```

Una estación sin datos no significa necesariamente que Cuyum esté roto. SeedLink depende de servidores y estaciones externos que pueden presentar indisponibilidad o latencia temporal.

## 26. Ver procesos Cuyum

```bash
ps aux | grep -E 'cell_00_seedlink_reader|auto_cell_seedlink_reader|plain_python_server|seedlink_discovery|sensor_auditor' | grep -v grep
```

## 27. Logs

```bash
ls -lh /opt/cuyum/runtime_logs
```

Para inspeccionar uno:

```bash
tail -n 100 /opt/cuyum/runtime_logs/NOMBRE_DEL_LOG
```

# PARTE M — Seguridad básica

## 28. Reglas simples

- Mantener Linux actualizado.
- Utilizar claves SSH cuando sea posible.
- No publicar contraseñas, tokens ni claves privadas en Git.
- No abrir puertos innecesarios.
- Exponer 80/443 mediante Nginx.
- No publicar 5050 directamente salvo necesidad técnica explícita.
- Mantener HTTPS activo.
- Hacer copias de seguridad antes de cambios importantes.

## 29. Usuario dedicado — mejora posterior

Una vez validado el despliegue puede crearse un usuario `cuyum` y dejar de ejecutar el servicio como root. Antes debe comprobarse que tenga permisos sobre los directorios que Cuyum necesita modificar, especialmente:

```text
runtime/
runtime_logs/
config/
```

No conviene introducir ese endurecimiento durante la primera instalación sin verificar el flujo de recentrado y escritura.

# PARTE N — Qué no hacer

## 30. Evitar

No copiar el `venv` de otra computadora.

No copiar la carpeta personal del desarrollador.

No publicar:

```text
runtime/
runtime_logs/
backups/
local_archive/
```

No convertir `:5050` en la URL pública definitiva.

No inventar aliases públicos para `/app`, `/json` y `/reg`.

No modificar silenciosamente una instalación etiquetada como `v1.2.0` sin registrar los cambios.

# PARTE O — Lista de comprobación

```text
[ ] El VPS responde por SSH
[ ] Git está instalado
[ ] Python y venv funcionan
[ ] Cuyum fue clonado desde GitHub
[ ] El tag correcto está seleccionado
[ ] requirements.txt se instaló
[ ] Cuyum crea runtime/ desde cero
[ ] /app responde localmente
[ ] /json responde localmente
[ ] /reg responde localmente
[ ] cuyum.ar apunta al VPS
[ ] Nginx reenvía a 127.0.0.1:5050
[ ] HTTPS funciona
[ ] Certbot pasa renew --dry-run
[ ] systemd arranca Cuyum
[ ] El VPS fue reiniciado
[ ] Cuyum volvió automáticamente
[ ] 5050 no está expuesto deliberadamente a Internet
```

# Resumen de emergencia

Arrancar:

```bash
systemctl start cuyum
```

Detener:

```bash
systemctl stop cuyum
```

Reiniciar:

```bash
systemctl restart cuyum
```

Estado:

```bash
systemctl status cuyum
```

Probar Cuyum directamente:

```bash
curl http://127.0.0.1:5050/json
```

Diagnóstico multicelda:

```bash
cd /opt/cuyum
./scripts/show_multicell_status_v1_2.sh
```

Sitio público:

```text
https://cuyum.ar/app
```

JSON público:

```text
https://cuyum.ar/json
```

Eventos recientes:

```text
https://cuyum.ar/reg
```

## Referencias

- Repositorio Cuyum: https://github.com/abelseru/cuyum
- Certbot: https://certbot.eff.org/
- Nginx: https://nginx.org/
- systemd: https://systemd.io/

## Licencia

Cuyum se distribuye bajo **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.

Ver `LICENSE`.
