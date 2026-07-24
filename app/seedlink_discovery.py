import json
import signal
from datetime import datetime, timezone
from collections import defaultdict
from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient


ARCHIVO_INVENTARIO = "config/candidate_inventory.json"
DURACION_REVISION_SEGUNDOS = 60
LATENCIA_MAXIMA_VIVO_SEGUNDOS = 30


def ahora_iso():
    return datetime.now(timezone.utc).isoformat()


def cargar_inventario():
    with open(ARCHIVO_INVENTARIO, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_inventario(data):
    with open(ARCHIVO_INVENTARIO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def energia_simple(trace):
    datos = trace.data
    if datos is None or len(datos) == 0:
        return 0.0
    return sum(abs(float(x)) for x in datos) / len(datos)


def clave_sensor(red, estacion, canal):
    return f"{red}.{estacion}.{canal}"


def clave_desde_trace(trace_id):
    partes = trace_id.split(".")
    if len(partes) < 4:
        return None

    red = partes[0]
    estacion = partes[1]
    canal = partes[3]

    return clave_sensor(red, estacion, canal)


class TiempoAgotado(Exception):
    pass


def cortar_por_tiempo(signum, frame):
    raise TiempoAgotado()


class ClienteRevision(EasySeedLinkClient):
    def __init__(self, server, claves_validas):
        super().__init__(server)
        self.claves_validas = claves_validas
        self.stats = defaultdict(lambda: {
            "paquetes": 0,
            "energia_total": 0.0,
            "ultima_fin": None,
            "frecuencia": None,
            "trace_id": None
        })

    def on_data(self, trace):
        clave = clave_desde_trace(trace.id)

        if clave not in self.claves_validas:
            return

        energia = energia_simple(trace)

        s = self.stats[clave]
        s["paquetes"] += 1
        s["energia_total"] += energia
        s["ultima_fin"] = trace.stats.endtime
        s["frecuencia"] = trace.stats.sampling_rate
        s["trace_id"] = trace.id

        print(
            f"OK {clave:<15} paquetes={s['paquetes']:<3} "
            f"energia={energia:8.2f} fin={trace.stats.endtime}"
        )

    def on_seedlink_error(self):
        print("ERROR SeedLink")

    def on_terminate(self):
        print("Conexión terminada")


def main():
    inventario = cargar_inventario()
    servidor = inventario.get("servidor_seedlink", "rtserve.earthscope.org:18000")

    sensores = inventario.get("sensores", [])

    claves_validas = set()
    for s in sensores:
        if s.get("estado") == "deshabilitado":
            continue

        claves_validas.add(
            clave_sensor(s["red"], s["estacion"], s["canal"])
        )

    print("==============================================")
    print("Descubridor SeedLink - modo seguro")
    print("Servidor:", servidor)
    print("Inventory:", ARCHIVO_INVENTARIO)
    print("Sensores a revisar:", len(claves_validas))
    print("Duración:", DURACION_REVISION_SEGUNDOS, "segundos")
    print("==============================================")

    client = ClienteRevision(servidor, claves_validas)

    for s in sensores:
        if s.get("estado") == "deshabilitado":
            continue

        print(
            f"Selecting {s['red']}.{s['estacion']}.{s['canal']} "
            f"| estado_actual={s.get('estado')} | {s.get('nombre')}"
        )

        client.select_stream(
            s["red"],
            s["estacion"],
            s["canal"]
        )

    signal.signal(signal.SIGALRM, cortar_por_tiempo)
    signal.alarm(DURACION_REVISION_SEGUNDOS)

    try:
        client.run()
    except TiempoAgotado:
        print("")
        print("Tiempo de revisión terminado.")
    except KeyboardInterrupt:
        print("")
        print("Stopped manually.")

    ahora = UTCDateTime()

    for s in sensores:
        clave = clave_sensor(s["red"], s["estacion"], s["canal"])

        if s.get("estado") == "deshabilitado":
            continue

        stat = client.stats.get(clave)

        if stat is None or stat["paquetes"] == 0:
            s["estado"] = "caido"
            s["ultima_revision"] = ahora_iso()
            s["paquetes_ultima_revision"] = 0
            s["latencia_aprox_seg"] = None
            s["energia_media_revision"] = None
            s["observacion_revision"] = "sin paquetes durante la revisión"
            continue

        latencia = float(ahora - stat["ultima_fin"])
        energia_media = stat["energia_total"] / stat["paquetes"]

        if latencia <= LATENCIA_MAXIMA_VIVO_SEGUNDOS:
            s["estado"] = "vivo"
            s["observacion_revision"] = "recibió paquetes recientes"
        else:
            s["estado"] = "latencia_alta"
            s["observacion_revision"] = "recibió paquetes pero con latencia alta"

        s["ultima_revision"] = ahora_iso()
        s["trace_id_ultima_revision"] = stat["trace_id"]
        s["paquetes_ultima_revision"] = stat["paquetes"]
        s["latencia_aprox_seg"] = round(latencia, 1)
        s["frecuencia_hz"] = stat["frecuencia"]
        s["energia_media_revision"] = round(energia_media, 2)

    inventario["ultima_actualizacion"] = ahora_iso()
    inventario["ultima_revision_segundos"] = DURACION_REVISION_SEGUNDOS

    guardar_inventario(inventario)

    print("")
    print("Inventory updated:", ARCHIVO_INVENTARIO)
    print("Resumen:")

    for s in sensores:
        print(
            f"{s['red']}.{s['estacion']}.{s['canal']} "
            f"estado={s.get('estado')} "
            f"paquetes={s.get('paquetes_ultima_revision')} "
            f"latencia={s.get('latencia_aprox_seg')}"
        )


if __name__ == "__main__":
    main()
