import json
import time
import math
from statistics import median
from datetime import datetime, timezone
from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient


ARCHIVO_INVENTARIO = "config/candidate_inventory.json"
ARCHIVO_SALIDA = "runtime/state_cell_00_seedlink.json"

PAQUETES_BASE = 5
FACTOR_FLAG = 2.5
STRONG_FLAG_FACTOR = 4.0
VENTANA_EVENTO_SEGUNDOS = 10
LATENCIA_MAXIMA_SEGUNDOS = 20

PESO_BASE_ANTERIOR = 0.97
PESO_ENERGIA_NUEVA = 0.03


def ahora_iso():
    return datetime.now(timezone.utc).isoformat()


ROLE_MAP = {
    "anticipacion": "early_warning",
    "anticipacion_secundaria": "secondary_early_warning",
    "confirmacion_cuyo": "local_confirmation",
    "confirmacion_este": "external_confirmation",
}

STATUS_MAP = {
    "vivo": "active",
    "activo": "active",
    "candidato": "candidate",
    "deshabilitado": "disabled",
    "caido": "down",
    "sospechoso": "suspect",
}

def normalize_sensor_config(s):
    role = ROLE_MAP.get(s.get("role", s.get("rol")), s.get("role", s.get("rol", "early_warning")))
    status = STATUS_MAP.get(s.get("state", s.get("estado")), s.get("state", s.get("estado", "candidate")))
    return {
        "network": s.get("network", s.get("red")),
        "station": s.get("station", s.get("estacion")),
        "channel": s.get("channel", s.get("canal")),
        "role": role,
        "name": s.get("name", s.get("nombre")),
        "distance_km": s.get("distance_km", s.get("distancia_km")),
        "priority": s.get("priority", s.get("prioridad")),
        "state": status,
        "can_trigger": bool(s.get("can_trigger", s.get("puede_disparar", True))),
        "can_confirm": bool(s.get("can_confirm", s.get("puede_confirmar", True))),
    }


def load_inventory():
    with open(ARCHIVO_INVENTARIO, "r", encoding="utf-8") as f:
        data = json.load(f)

    server = data.get("seedlink_server", data.get("servidor_seedlink", "rtserve.earthscope.org:18000"))

    sensors = []
    for raw in data.get("sensors", data.get("sensores", [])):
        s = normalize_sensor_config(raw)
        if s.get("state") in ["disabled", "down", "suspect"]:
            continue
        sensors.append(s)

    return server, sensors, data


def energia_simple(trace):
    datos = trace.data
    if datos is None or len(datos) == 0:
        return 0.0
    return sum(abs(float(x)) for x in datos) / len(datos)


def magnitud_experimental(energia):
    if energia <= 0:
        return 0.0
    return round(math.log10(energia + 1), 2)


def extraer_clave_trace(trace_id):
    parts = str(trace_id).split(".")

    # ObsPy trace id usually looks like:
    # NETWORK.STATION.LOCATION.CHANNEL
    if len(parts) >= 4:
        network = parts[0]
        station = parts[1]
        channel = parts[3]
        return f"{network}.{station}.{channel}"

    # Fallback for already-normalized NETWORK.STATION.CHANNEL ids.
    if len(parts) >= 3:
        network = parts[0]
        station = parts[1]
        channel = parts[2]
        return f"{network}.{station}.{channel}"

    return str(trace_id)


def sensor_config_key(sensor):
    return f"{sensor['network']}.{sensor['station']}.{sensor['channel']}"


def calculate_network_quality(sensor_states):
    sensors = list(sensor_states.values())

    calibrated = [s for s in sensors if s.get("calibrated")]
    activos = [
        s for s in calibrated
        if s.get("sensor_state") == "active"
    ]

    early_warning_sensors = [
        s for s in activos
        if s.get("role") in ["early_warning", "secondary_early_warning"]
    ]

    confirmacion = [
        s for s in activos
        if s.get("role") in ["local_confirmation", "external_confirmation"]
    ]

    total_active = len(activos)
    total_early_warning = len(early_warning_sensors)
    total_confirmacion = len(confirmacion)

    if total_active >= 4 and total_early_warning >= 2:
        state = "good"
    elif total_active >= 3 and total_early_warning >= 1:
        state = "degraded"
    elif total_active >= 2:
        state = "minimal"
    else:
        state = "insufficient"

    return {
        "state": state,
        "active_sensors": total_active,
        
        "calibrated_sensors": len(calibrated),
        
        "early_warning_active": total_early_warning,
        "confirmation_active": total_confirmacion
    }


def event_level_from_signals(confirming_stations, has_strong_early_signal):
    count = len(confirming_stations)

    if count >= 3:
        return "experimental_critical"

    if count >= 2:
        return "internal_notice"

    if count == 1 and has_strong_early_signal:
        return "internal_notice"

    if count == 1:
        return "observacion_urgente"

    return "normal"


def datos_esp32(level, led_nivel, magnitud, mensaje, network_quality):
    if network_quality.get("state", network_quality.get("estado")) == "insufficient" and level == "normal":
        return {
            "sonar": False,
            "buzzer_segundos": 0,
            "led_nivel": 1,
            "estimated_magnitude": 0,
            "level": "red_insuficiente",
            "mensaje": "Fuentes insuficientes"
        }

    if level in ["internal_notice", "experimental_critical"]:
        return {
            "sonar": True,
            "buzzer_segundos": 5,
            "led_nivel": led_nivel,
            "estimated_magnitude": magnitud,
            "level": level,
            "mensaje": mensaje
        }

    if level == "observacion_urgente":
        return {
            "sonar": False,
            "buzzer_segundos": 0,
            "led_nivel": led_nivel,
            "estimated_magnitude": magnitud,
            "level": level,
            "mensaje": mensaje
        }

    return {
        "sonar": False,
        "buzzer_segundos": 0,
        "led_nivel": 0,
        "estimated_magnitude": 0,
        "level": "normal",
        "mensaje": "normal"
    }


def led_por_nivel(level):
    if level == "experimental_critical":
        return 10
    if level == "internal_notice":
        return 7
    if level == "observacion_urgente":
        return 4
    return 0


class AdaptiveSeedLinkReader(EasySeedLinkClient):
    def __init__(self, server, sensors, inventory):
        super().__init__(server)

        self.server = server
        self.sensors = sensors
        self.inventory = inventory

        self.historial_base = {}
        self.base = {}
        self.sensor_states = {}
        self.flags_recientes = {}

        self.sensor_map = {}
        for s in self.sensors:
            self.sensor_map[sensor_config_key(s)] = s

    def on_data(self, trace):
        trace_id = trace.id
        key = extraer_clave_trace(trace_id)

        if key not in self.sensor_map:
            return

        cfg = self.sensor_map[key]

        energia = energia_simple(trace)
        magnitud = magnitud_experimental(energia)

        ahora = UTCDateTime()
        latencia = float(ahora - trace.stats.endtime)

        if latencia > LATENCIA_MAXIMA_SEGUNDOS:
            self.sensor_states[key] = {
                "trace_id": trace_id,
                "sensor_id": key,
                "network": cfg["network"],
                "station": cfg["station"],
                "channel": cfg["channel"],
                "role": cfg["role"],
                "name": cfg["name"],
                "distance_km": cfg["distance_km"],
                "sensor_state": "high_latency",
                "calibrated": key in self.base,
                "flag": False,
                "strong_flag": False,
                "flag_fuerte": False,
                "latency_seconds": round(latencia, 1),
                "updated_at": ahora_iso()
            }
            self.write_state()
            print(f"DISCARDED {trace_id} latency={round(latencia, 1)}s")
            return

        if key not in self.historial_base:
            self.historial_base[key] = []

        self.historial_base[key].append(energia)

        calibrated = key in self.base

        if not calibrated:
            if len(self.historial_base[key]) >= PAQUETES_BASE:
                self.base[key] = median(self.historial_base[key][-PAQUETES_BASE:])
                calibrated = True
                print("BASE DEFINIDA:", key, "base=", round(self.base[key], 2))
            else:
                self.sensor_states[key] = {
                    "trace_id": trace_id,
                    "sensor_id": key,
                    "network": cfg["network"],
                    "station": cfg["station"],
                    "channel": cfg["channel"],
                    "role": cfg["role"],
                    "name": cfg["name"],
                    "distance_km": cfg["distance_km"],
                    "sensor_state": "calibrating",
                    "calibrated": False,
                    "baseline_packets": len(self.historial_base[key]),
                    "baseline_packets_required": PAQUETES_BASE,
                    "current_energy": round(energia, 2),
                    "baseline_energy": None,
                    "ratio": None,
                    "estimated_magnitude": magnitud,
                    "flag": False,
                    "strong_flag": False,
                "flag_fuerte": False,
                    "latency_seconds": round(latencia, 1),
                    "updated_at": ahora_iso()
                }
                self.write_state()
                print(f"CALIBRATING {trace_id} {len(self.historial_base[key])}/{PAQUETES_BASE}")
                return

        sensor_baseline = self.base[key]

        ratio = energia / sensor_baseline if sensor_baseline > 0 else 0

        can_trigger = bool(cfg.get("can_trigger", True))
        puede_confirmar = bool(cfg.get("can_confirm", True))

        flag_crudo = ratio >= FACTOR_FLAG
        raw_strong_flag = ratio >= STRONG_FLAG_FACTOR

        flag = flag_crudo and puede_confirmar
        strong_flag = raw_strong_flag and can_trigger

        if not flag_crudo:
            self.base[key] = (
                self.base[key] * PESO_BASE_ANTERIOR
                + energia * PESO_ENERGIA_NUEVA
            )

        if flag:
            self.flags_recientes[cfg["station"]] = {
                "sensor_id": key,
                "trace_id": trace_id,
                "station": cfg["station"],
                "role": cfg["role"],
                "name": cfg["name"],
                "distance_km": cfg["distance_km"],
                "current_energy": round(energia, 2),
                "baseline_energy": round(sensor_baseline, 2),
                "ratio": round(ratio, 2),
                "estimated_magnitude": magnitud,
                "strong_flag": strong_flag,
                "flag_fuerte": strong_flag,
                "can_trigger": can_trigger,
                "can_confirm": puede_confirmar,
                "timestamp": float(ahora.timestamp),
                "updated_at": ahora_iso()
            }

        self.sensor_states[key] = {
            "trace_id": trace_id,
            "sensor_id": key,
            "network": cfg["network"],
            "station": cfg["station"],
            "channel": cfg["channel"],
            "role": cfg["role"],
            "name": cfg["name"],
            "distance_km": cfg["distance_km"],
            "priority": cfg.get("priority"),
            "sensor_state": "active",
            "calibrated": True,
            "can_trigger": can_trigger,
            "can_confirm": puede_confirmar,
            "current_energy": round(energia, 2),
            "baseline_energy": round(self.base[key], 2),
            "ratio": round(ratio, 2),
            "estimated_magnitude": magnitud,
            "flag": flag,
            "strong_flag": strong_flag,
                "flag_fuerte": strong_flag,
            "latency_seconds": round(latencia, 1),
            "updated_at": ahora_iso()
        }

        self.limpiar_flags_viejos(float(ahora.timestamp))
        self.write_state()

        print(
            f"{trace_id} energia={round(energia, 2)} "
            f"base={round(sensor_baseline, 2)} ratio={round(ratio, 2)} "
            f"flag={flag} strong={strong_flag}"
        )

    def limpiar_flags_viejos(self, ahora_ts):
        vencidos = []

        for estacion, data in self.flags_recientes.items():
            edad = ahora_ts - data.get("timestamp", data.get("tiempo", ahora_ts))
            if edad > VENTANA_EVENTO_SEGUNDOS:
                vencidos.append(estacion)

        for estacion in vencidos:
            del self.flags_recientes[estacion]

    def build_zone(self):
        confirming_stations = list(self.flags_recientes.keys())

        has_strong_early_signal = False
        magnitud_max = 0
        ratio_max = 0

        for data in self.flags_recientes.values():
            magnitud_max = max(magnitud_max, data["estimated_magnitude"])
            ratio_max = max(ratio_max, data["ratio"])

            if (
                data["flag_fuerte"]
                and data["role"] in ["early_warning", "secondary_early_warning"]
            ):
                has_strong_early_signal = True

        level = event_level_from_signals(
            confirming_stations,
            has_strong_early_signal
        )

        network_quality = calculate_network_quality(self.sensor_states)
        led = led_por_nivel(level)

        if level == "experimental_critical":
            mensaje = "Experimental critical state: several independent stations confirming"
        elif level == "internal_notice":
            mensaje = "Experimental internal warning: regional anomaly detected"
        elif level == "observacion_urgente":
            mensaje = "Urgent observation: one station detected anomaly"
        else:
            mensaje = "normal"

        esp32 = datos_esp32(level, led, magnitud_max, mensaje, network_quality)

        zone = {
            "state": level,
            "flag": level != "normal",
            "modo": "seedlink_adaptativo",
            "calibracion": "continua",
            "ventana_evento_segundos": VENTANA_EVENTO_SEGUNDOS,
            "total_sensors": len(self.sensors),
            "total_sensors_legacy": len(self.sensors),
            "calibrated_sensors": network_quality.get("calibrated_sensors", 0),
            
            "active_sensors": network_quality.get("active_sensors", 0),
            
            "flagged_sensors": sum(
                1 for s in self.sensor_states.values()
                if s.get("flag")
            ),
            "confirming_stations": len(confirming_stations),
            "estaciones_confirmando": len(confirming_stations),
            "confirming_station_list": confirming_stations,
            "estaciones_confirmando_lista": confirming_stations,
            "estimated_magnitude": magnitud_max,
            "ratio_max": round(ratio_max, 2),
            "network_quality": network_quality,
            
            "led_nivel": led,
            "sound": esp32["sonar"],
            "sonar": esp32["sonar"],
            "buzzer_segundos": esp32["buzzer_segundos"],
            "mensaje": mensaje,
            "updated_at": ahora_iso(),
            "flags_recientes": self.flags_recientes,
            "sensors": self.sensor_states,
            "sensors": self.sensor_states
        }

        return zone, esp32

    def write_state(self):
        zone, esp32 = self.build_zone()

        salida = {
            "group": "zone_group_01",
            "modo": "seedlink_adaptativo_v2",
            "sistema": "Nogues Experimental Monitoring Node",
            "advertencia": (
                "Experimental school system. Does not replace official sources. "
                "Requiere verificación humana."
            ),
            "servidor_seedlink": self.server,
            "archivo_inventario": ARCHIVO_INVENTARIO,
            "updated_at": ahora_iso(),
            "esp32": esp32,
            "zones": {
                "local_adaptive_zone": zone
            }
        }

        with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=2)

    def on_seedlink_error(self):
        print("ERROR SeedLink")

    def on_terminate(self):
        print("Connection terminated")


def main():
    server, sensors, inventory = load_inventory()

    print("==============================================")
    print("Local cell reader - SeedLink adaptive V2")
    print("Server:", server)
    print("Inventory:", ARCHIVO_INVENTARIO)
    print("Output file:", ARCHIVO_SALIDA)
    print("Loaded sensors:", len(sensors))
    print("==============================================")

    client = AdaptiveSeedLinkReader(server, sensors, inventory)

    for sensor in sensors:
        print(
            f"Selecting {sensor['network']}.{sensor['station']}.{sensor['channel']} "
            f"| {sensor['role']} | {sensor['distance_km']} km | {sensor['name']}"
        )
        client.select_stream(
            sensor["network"],
            sensor["station"],
            sensor["channel"]
        )

    print("")
    print("Listening. Stop with Ctrl+C.")
    print("")

    while True:
        try:
            client.run()
        except KeyboardInterrupt:
            print("")
            print("Stopped manually.")
            break
        except Exception as exc:
            print(f"reader_error: {type(exc).__name__}: {exc}")
            print("reconnecting in 30 seconds...")
            time.sleep(30)

            try:
                client = AdaptiveSeedLinkReader(server, sensors, inventory)
                for sensor in sensors:
                    client.select_stream(
                        sensor["network"],
                        sensor["station"],
                        sensor["channel"]
                    )
                print("reader_reconnected: client rebuilt")
            except Exception as rebuild_exc:
                print(f"reader_rebuild_error: {type(rebuild_exc).__name__}: {rebuild_exc}")
                print("retrying rebuild in 30 seconds...")
                time.sleep(30)



if __name__ == "__main__":
    main()
