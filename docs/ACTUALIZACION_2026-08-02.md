# Actualización técnica — 2 de agosto de 2026

## Red y procesamiento de señales

Se incorporó protección contra señales individuales persistentemente elevadas.

Una estación que permanece durante un período prolongado por encima de su línea de base deja de renovar indefinidamente una observación. En ese caso, su línea de base vuelve a adaptarse gradualmente.

Esta protección busca reducir falsos positivos producidos por ruido persistente o cambios sostenidos en una estación.

La confirmación de eventos continúa dependiendo de la coincidencia temporal entre sensores y celdas.

## Interfaz en vivo

Los marcadores de sensores de `/app` ahora se actualizan sin ser destruidos y creados nuevamente en cada consulta.

Esto permite que los cuadros emergentes de los sensores permanezcan abiertos mientras el mapa recibe nuevos datos.

## Selector de idioma

Se retiraron los fondos con banderas de los selectores de idioma de `/app` y `/web`.

Se conservaron:

- el emoji de diálogo;
- las etiquetas ES y EN;
- la posición;
- las dimensiones;
- el comportamiento del selector.

## Idioma para clientes físicos

El endpoint `/lite` publica ahora:

```json
{
  "enable_english": false,
  "language": "es"
}
```

Cuando la configuración global de inglés está habilitada, publica:

```json
{
  "enable_english": true,
  "language": "en"
}
```

Esto permite que clientes físicos, incluido el ESP32, consulten `https://cuyum.ar/lite` y seleccionen el idioma correspondiente.

Ante una respuesta incompleta o un error de conexión, los clientes deben utilizar español como idioma predeterminado.

## Sonido de alerta

Se incorporó el archivo:

`static/audio/cuyum_5_chirps_320kbps.mp3`

Este recurso contiene los cinco chirps de referencia de Cuyum y puede ser utilizado por Telegram, demostraciones y clientes externos.
