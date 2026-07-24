# Cuyum v1.2

Cuyum es un sistema experimental de monitoreo sísmico escolar basado en lectores SeedLink, fusión multicelda, archivos JSON locales, monitor web y salida para nodos ESP32.

## Arranque

```bash
./start_cuyum_v1_2.sh
```

## Detención

```bash
./stop_cuyum_v1_2.sh
```

## Monitor

Local:

```text
http://127.0.0.1:5050/app
```

Red local:

```text
http://192.168.1.37:5050/app
```

## Rutas principales

```text
/app                 Monitor humano
/json                Estado vivo completo para la app y depuración
/reg                 Registros recientes
/api/node/poll       Consulta para nodo ESP32
/api/esp32/poll      Consulta compatible para ESP32
/health              Estado básico del servidor
```

## Estructura del proyecto

```text
cuyum_v_1_2/
├── app/              Código Python del servidor, fusión, lectores y auditoría
├── config/           Inventarios, catálogos y configuración editable
├── runtime/          Estado vivo generado por Cuyum
├── runtime_logs/     Logs de ejecución local
├── static/           CSS, JS, logo y recursos del monitor
├── templates/        HTML del monitor
├── scripts/          Herramientas auxiliares
├── docs/             Documentación
├── tools/            Utilidades de laboratorio
├── start_cuyum_v1_2.sh
└── stop_cuyum_v1_2.sh
```

## Contrato actual

Las rutas públicas canónicas son `/app`, `/json` y `/reg`.

Las rutas antiguas `/live`, `/api/public/live`, `/api/v1/live`, `/estado.json`, `/inventario.json` y `/sensores.json` fueron retiradas del servidor principal.

## Nota de uso

Cuyum v1.2 es experimental. Los datos se usan para observación, aprendizaje, validación técnica y visualización escolar. No reemplaza fuentes oficiales ni procedimientos institucionales.
