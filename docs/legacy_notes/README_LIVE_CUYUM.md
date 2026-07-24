# Cuyum Live mínimo

Este parche agrega una página pública liviana para Cuyum:

- `/live`
- `/api/public/live`

La página descarga **un solo JSON** por ciclo:

- modo normal: cada 5 segundos
- modo alerta: cada 1,5 segundos

El navegador dibuja el resto: estado, zonas, sensores y mapa. No recalcula la red ni consulta endpoints separados.

## Archivos agregados

- `public_live.py`
- `templates/live_cuyum.html`
- `static/live_cuyum.css`
- `static/live_cuyum.js`

## Archivo modificado

- `servidor_json_seedlink.py`

## Cómo probar

```bash
cd ~/cuyum_v_1_1
./detener_cuyum_v1_1.sh
./iniciar_cuyum_visible_v1_1.sh
```

Esperar 2 o 3 minutos de calentamiento multicelda y abrir:

```text
http://127.0.0.1:5000/live
```

También se puede abrir desde otro equipo de la misma red:

```text
http://IP_DE_LA_PC:5000/live
```

El botón **Activar audio** habilita el sonido de alertas en navegadores y celulares. Sin tocar ese botón, el navegador normalmente bloquea audio automático.

## VPS futuro

En VPS la idea es publicar:

```text
https://live.cuyum.ar
```

y dejar `/api/public/live` detrás de Nginx con caché corta.
