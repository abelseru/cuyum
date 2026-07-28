import json
import time
import math
from statistics import median
from datetime import datetime, timezone
from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient


INVENTORY_FILE = "config/candidate_inventory.json"
OUTPUT_FILE = "runtime/state_cell_00_seedlink.json"

BASELINE_PACKETS = 5
FACTOR_FLAG = 2.5
STRONG_FLAG_FACTOR = 4.0
EVENT_WINDOW_SECONDS = 10
MAX_LATENCY_SECONDS = 20

PREVIOUS_BASELINE_WEIGHT = 0.97
NEW_ENERGY_WEIGHT = 0.03


def now_iso():
    return datetime.now(timezone.utc).isoformat()



def normalize_sensor_config(s):
    return {
        "network": s.get("network"),
        "station": s.get("station"),
        "channel": s.get("channel"),
        "role": s.get("role", "early_warning"),
        "name": s.get("name"),
        "distance_km": s.get("distance_km"),
        "priority": s.get("priority"),
        "state": s.get("state", "candidate"),
        "can_trigger": bool(s.get("can_trigger", True)),
        "can_confirm": bool(s.get("can_confirm", True)),
    }


def load_inventory():
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    server = data.get("seedlink_server", "rtserve.earthscope.org:18000")

    sensors = []
    for raw in data.get("sensors", []):
        s = normalize_sensor_config(raw)
        if s.get("state") in ["disabled", "down", "suspect"]:
            continue
        sensors.append(s)

    return server, sensors, data


def simple_energy(trace):
    data = trace.data
    if data is None or len(data) == 0:
        return 0.0
    return sum(abs(float(x)) for x in data) / len(data)


def experimental_magnitude(energy):
    if energy <= 0:
        return 0.0
    return round(math.log10(energy + 1), 2)


def extract_trace_key(trace_id):
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
    active = [
        s for s in calibrated
        if s.get("sensor_state") == "active"
    ]

    early_warning_sensors = [
        s for s in active
        if s.get("role") in ["early_warning", "secondary_early_warning"]
    ]

    confirmation = [
        s for s in active
        if s.get("role") in ["local_confirmation", "external_confirmation"]
    ]

    total_active = len(active)
    total_early_warning = len(early_warning_sensors)
    total_confirmation = len(confirmation)

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
        "confirmation_active": total_confirmation
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
        return "urgent_observation"

    return "normal"


def build_node_output(level, led_level, magnitude, message, network_quality):
    if network_quality.get("state") == "insufficient" and level == "normal":
        return {
            "sound": False,
            "buzzer_seconds": 0,
            "led_level": 1,
            "estimated_magnitude": 0,
            "level": "insufficient_network",
            "message": "Insufficient sources"
        }

    if level in ["internal_notice", "experimental_critical"]:
        return {
            "sound": True,
            "buzzer_seconds": 5,
            "led_level": led_level,
            "estimated_magnitude": magnitude,
            "level": level,
            "message": message
        }

    if level == "urgent_observation":
        return {
            "sound": False,
            "buzzer_seconds": 0,
            "led_level": led_level,
            "estimated_magnitude": magnitude,
            "level": level,
            "message": message
        }

    return {
        "sound": False,
        "buzzer_seconds": 0,
        "led_level": 0,
        "estimated_magnitude": 0,
        "level": "normal",
        "message": "normal"
    }


def led_for_level(level):
    if level == "experimental_critical":
        return 10
    if level == "internal_notice":
        return 7
    if level == "urgent_observation":
        return 4
    return 0


class AdaptiveSeedLinkReader(EasySeedLinkClient):
    def __init__(self, server, sensors, inventory):
        super().__init__(server)

        self.server = server
        self.sensors = sensors
        self.inventory = inventory

        self.baseline_history = {}
        self.base = {}
        self.sensor_states = {}
        self.recent_flags = {}

        self.sensor_map = {}
        for s in self.sensors:
            self.sensor_map[sensor_config_key(s)] = s

    def on_data(self, trace):
        trace_id = trace.id
        key = extract_trace_key(trace_id)

        if key not in self.sensor_map:
            return

        cfg = self.sensor_map[key]

        energy = simple_energy(trace)
        magnitude = experimental_magnitude(energy)

        now = UTCDateTime()
        latency = float(now - trace.stats.endtime)

        if latency > MAX_LATENCY_SECONDS:
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
                "latency_seconds": round(latency, 1),
                "updated_at": now_iso()
            }
            self.write_state()
            print(f"DISCARDED {trace_id} latency={round(latency, 1)}s")
            return

        if key not in self.baseline_history:
            self.baseline_history[key] = []

        self.baseline_history[key].append(energy)

        calibrated = key in self.base

        if not calibrated:
            if len(self.baseline_history[key]) >= BASELINE_PACKETS:
                self.base[key] = median(self.baseline_history[key][-BASELINE_PACKETS:])
                calibrated = True
                print("BASELINE DEFINED:", key, "baseline=", round(self.base[key], 2))
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
                    "baseline_packets": len(self.baseline_history[key]),
                    "baseline_packets_required": BASELINE_PACKETS,
                    "current_energy": round(energy, 2),
                    "baseline_energy": None,
                    "ratio": None,
                    "estimated_magnitude": magnitude,
                    "flag": False,
                    "strong_flag": False,
                    "latency_seconds": round(latency, 1),
                    "updated_at": now_iso()
                }
                self.write_state()
                print(f"CALIBRATING {trace_id} {len(self.baseline_history[key])}/{BASELINE_PACKETS}")
                return

        sensor_baseline = self.base[key]

        ratio = energy / sensor_baseline if sensor_baseline > 0 else 0

        can_trigger = bool(cfg.get("can_trigger", True))
        can_confirm = bool(cfg.get("can_confirm", True))

        raw_flag = ratio >= FACTOR_FLAG
        raw_strong_flag = ratio >= STRONG_FLAG_FACTOR

        flag = raw_flag and can_confirm
        strong_flag = raw_strong_flag and can_trigger

        if not raw_flag:
            self.base[key] = (
                self.base[key] * PREVIOUS_BASELINE_WEIGHT
                + energy * NEW_ENERGY_WEIGHT
            )

        if flag:
            self.recent_flags[cfg["station"]] = {
                "sensor_id": key,
                "trace_id": trace_id,
                "station": cfg["station"],
                "role": cfg["role"],
                "name": cfg["name"],
                "distance_km": cfg["distance_km"],
                "current_energy": round(energy, 2),
                "baseline_energy": round(sensor_baseline, 2),
                "ratio": round(ratio, 2),
                "estimated_magnitude": magnitude,
                "strong_flag": strong_flag,
                "can_trigger": can_trigger,
                "can_confirm": can_confirm,
                "timestamp": float(now.timestamp),
                "updated_at": now_iso()
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
            "can_confirm": can_confirm,
            "current_energy": round(energy, 2),
            "baseline_energy": round(self.base[key], 2),
            "ratio": round(ratio, 2),
            "estimated_magnitude": magnitude,
            "flag": flag,
            "strong_flag": strong_flag,
            "latency_seconds": round(latency, 1),
            "updated_at": now_iso()
        }

        self.clear_expired_flags(float(now.timestamp))
        self.write_state()

        print(
            f"{trace_id} energy={round(energy, 2)} "
            f"base={round(sensor_baseline, 2)} ratio={round(ratio, 2)} "
            f"flag={flag} strong={strong_flag}"
        )

    def clear_expired_flags(self, now_ts):
        expired = []

        for station, data in self.recent_flags.items():
            age = now_ts - data.get("timestamp", now_ts)
            if age > EVENT_WINDOW_SECONDS:
                expired.append(station)

        for station in expired:
            del self.recent_flags[station]

    def build_zone(self):
        confirming_stations = list(self.recent_flags.keys())

        has_strong_early_signal = False
        max_magnitude = 0
        ratio_max = 0

        for data in self.recent_flags.values():
            max_magnitude = max(max_magnitude, data["estimated_magnitude"])
            ratio_max = max(ratio_max, data["ratio"])

            if (
                data["strong_flag"]
                and data["role"] in ["early_warning", "secondary_early_warning"]
            ):
                has_strong_early_signal = True

        level = event_level_from_signals(
            confirming_stations,
            has_strong_early_signal
        )

        network_quality = calculate_network_quality(self.sensor_states)
        led = led_for_level(level)

        if level == "experimental_critical":
            message = "Experimental critical state: several independent stations confirming"
        elif level == "internal_notice":
            message = "Experimental internal warning: regional anomaly detected"
        elif level == "urgent_observation":
            message = "Urgent observation: one station detected anomaly"
        else:
            message = "normal"

        esp32 = build_node_output(level, led, max_magnitude, message, network_quality)

        zone = {
            "state": level,
            "flag": level != "normal",
            "mode": "adaptive_seedlink",
            "calibration": "continuous",
            "event_window_seconds": EVENT_WINDOW_SECONDS,
            "total_sensors": len(self.sensors),
            "total_sensors_legacy": len(self.sensors),
            "calibrated_sensors": network_quality.get("calibrated_sensors", 0),
            
            "active_sensors": network_quality.get("active_sensors", 0),
            
            "flagged_sensors": sum(
                1 for s in self.sensor_states.values()
                if s.get("flag")
            ),
            "confirming_stations": len(confirming_stations),
            "confirming_station_list": confirming_stations,
            "estimated_magnitude": max_magnitude,
            "ratio_max": round(ratio_max, 2),
            "network_quality": network_quality,
            
            "led_level": led,
            "sound": esp32["sound"],
            "sound": esp32["sound"],
            "buzzer_seconds": esp32["buzzer_seconds"],
            "message": message,
            "updated_at": now_iso(),
            "recent_flags": self.recent_flags,
            "sensors": self.sensor_states
        }

        return zone, esp32

    def write_state(self):
        zone, esp32 = self.build_zone()

        output = {
            "group": "zone_group_01",
            "mode": "adaptive_seedlink_v2",
            "system": "Nogues Experimental Monitoring Node",
            "warning": (
                "Experimental school system. Does not replace official sources. "
                "Human verification required."
            ),
            "seedlink_server": self.server,
            "inventory_file": INVENTORY_FILE,
            "updated_at": now_iso(),
            "esp32": esp32,
            "zones": {
                "local_adaptive_zone": zone
            }
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def on_seedlink_error(self):
        print("ERROR SeedLink")

    def on_terminate(self):
        print("Connection terminated")


def main():
    server, sensors, inventory = load_inventory()

    print("==============================================")
    print("Local cell reader - SeedLink adaptive V2")
    print("Server:", server)
    print("Inventory:", INVENTORY_FILE)
    print("Output file:", OUTPUT_FILE)
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
