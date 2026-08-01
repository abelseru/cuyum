# Cuyum 1.3 — Interfaces HTTP

## Direcciones base

Ejecución local tradicional:

```text
http://127.0.0.1:5050
```

Despliegue público:

```text
https://cuyum.ar
```

En Docker, Cuyum continúa escuchando en el puerto interno `5050`, pero ese puerto no se publica directamente en Internet. Caddy recibe las conexiones HTTP/HTTPS y las reenvía al servicio `cuyum:5050` dentro de la red de Docker.

## Interfaces públicas canónicas

### GET /app

Monitor web destinado a personas.

```text
https://cuyum.ar/app
```

### GET /json

Estado vivo canónico de Cuyum.

```text
https://cuyum.ar/json
```

### GET /reg

Registros públicos recientes.

```text
https://cuyum.ar/reg
```

## Interfaces internas y de dispositivos

### GET /health

Comprobación básica del servidor.

### GET /lite

Interfaz compacta para dispositivos ESP32 y clientes livianos.

```text
https://cuyum.ar/lite
```

### GET /api/network/state

Estado técnico de la red multicelda.

### GET /api/cells/<cell_id>

Estado técnico de una celda específica.

Ejemplo:

```text
/api/cells/cell_00
```

## Política de contratos

Las interfaces públicas canónicas son:

```text
/app
/json
/reg
```

Cuyum no mantiene alias públicos paralelos para el mismo contrato de estado vivo.

`/lite` es una interfaz deliberadamente compacta para dispositivos y no sustituye a `/json`.

## Disponibilidad

El healthcheck de Docker consulta internamente:

```text
http://127.0.0.1:5050/lite
```

Esto comprueba que el servidor HTTP del contenedor responda sin exponer el puerto `5050` al exterior.

## Advertencia

Cuyum es experimental y no reemplaza información sísmica oficial ni sistemas certificados de alerta temprana.
