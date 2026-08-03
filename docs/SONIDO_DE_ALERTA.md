# Sonido de alerta de Cuyum

Archivo de referencia:

`static/audio/cuyum_5_chirps_320kbps.mp3`

## Función

Este archivo contiene el patrón sonoro de cinco chirps utilizado por
Cuyum para representar una alerta o simulación de propagación.

Puede ser utilizado por:

- el bot de Telegram;
- publicaciones y demostraciones;
- clientes físicos;
- sistemas externos que necesiten reproducir el sonido oficial de Cuyum.

## Patrón

- Cantidad de chirps: 5
- Frecuencia principal: 880 Hz
- Forma de onda: cuadrada
- Formato: MP3
- Tasa de bits: 320 kbps

## Uso desde la web

Una vez desplegado, el archivo puede consultarse en:

`https://cuyum.ar/static/audio/cuyum_5_chirps_320kbps.mp3`

## Importante

El archivo es un recurso sonoro de referencia. La lógica que decide cuándo
se produce una observación, una confirmación o una alerta permanece en el
servidor de Cuyum.

La existencia del archivo no implica que cualquier señal individual deba
generar una alerta.
