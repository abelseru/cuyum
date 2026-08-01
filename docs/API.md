# Cuyum 1.3 — API HTTP

## Base pública

```text
https://cuyum.ar
```

## Rutas

### GET /app

Monitor web para personas.

### GET /json

Estado vivo canónico.

### GET /reg

Registros públicos recientes.

### GET /lite

Estado compacto para ESP32 y clientes livianos.

### GET /health

Comprobación básica del servidor.

### GET /api/network/state

Estado técnico de la red multicelda.

### GET /api/cells/<cell_id>

Estado técnico de una celda.

Ejemplo:

```text
/api/cells/cell_00
```

## Red interna

Dentro de Docker, Cuyum escucha en:

```text
http://cuyum:5050
```

Caddy publica las rutas mediante HTTPS. El puerto `5050` no debe exponerse directamente en el host.

## Healthcheck

El healthcheck del contenedor consulta internamente:

```text
http://127.0.0.1:5050/lite
```

## Pruebas

```bash
curl -sS https://cuyum.ar/lite
curl -sS https://cuyum.ar/json
```

Para verificar el código HTTP de `/app`:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://cuyum.ar/app
```

No usar `curl -I` como prueba principal porque envía el método `HEAD`.

## Contratos públicos

Las interfaces canónicas son:

```text
/app
/json
/reg
/lite
```

## Advertencia

Cuyum es experimental y no reemplaza información sísmica oficial.
