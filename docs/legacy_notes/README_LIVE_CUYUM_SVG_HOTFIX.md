CUYUM v1.1 - HOTFIX LIVE SVG

Este hotfix reemplaza el mapa Leaflet por un mapa SVG propio, fijo y liviano.

Cambios:
- /live ya no depende de Leaflet ni de tiles externos.
- No hay zoom ni navegación libre.
- El navegador descarga un solo JSON por ciclo: /api/public/live.
- Modo normal: usa el intervalo indicado por el servidor, normalmente 5000 ms.
- Modo alerta: usa el intervalo indicado por el servidor, normalmente 1500 ms.
- El mapa calcula automáticamente un encuadre alrededor de sensores y zonas ubicables.
- Muestra zonas, sensores ubicados y una nota de sensores sin ubicación exacta.

Instalación:
1. Copiar/arrastrar estos archivos dentro de ~/cuyum_v_1_1 aceptando reemplazar.
2. Reiniciar Cuyum:
   ./detener_cuyum_v1_1.sh
   ./iniciar_cuyum_visible_v1_1.sh
3. Abrir:
   http://127.0.0.1:5000/live
   o desde otro equipo de la red:
   http://IP_DE_LA_PC:5000/live
