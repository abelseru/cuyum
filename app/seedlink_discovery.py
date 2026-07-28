import json
import signal
from collections import defaultdict
from datetime import datetime, timezone

from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient


INVENTORY_FILE = "config/candidate_inventory.json"
REVIEW_DURATION_SECONDS = 60
MAX_ALIVE_LATENCY_SECONDS = 30


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_inventory():
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_inventory(data):
    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def simple_energy(trace):
    data = trace.data
    if data is None or len(data) == 0:
        return 0.0
    return sum(abs(float(x)) for x in data) / len(data)


def sensor_key(network, station, channel):
    return f"{network}.{station}.{channel}"


def sensor_key_from_trace(trace_id):
    parts = trace_id.split(".")
    if len(parts) < 4:
        return None

    network = parts[0]
    station = parts[1]
    channel = parts[3]

    return sensor_key(network, station, channel)


class ReviewTimeout(Exception):
    pass


def stop_on_timeout(signum, frame):
    raise ReviewTimeout()


class ReviewClient(EasySeedLinkClient):
    def __init__(self, server, valid_keys):
        super().__init__(server)
        self.valid_keys = valid_keys
        self.stats = defaultdict(
            lambda: {
                "packets": 0,
                "total_energy": 0.0,
                "last_end": None,
                "sampling_rate": None,
                "trace_id": None,
            }
        )

    def on_data(self, trace):
        key = sensor_key_from_trace(trace.id)

        if key not in self.valid_keys:
            return

        energy = simple_energy(trace)

        stat = self.stats[key]
        stat["packets"] += 1
        stat["total_energy"] += energy
        stat["last_end"] = trace.stats.endtime
        stat["sampling_rate"] = trace.stats.sampling_rate
        stat["trace_id"] = trace.id

        print(
            f"OK {key:<15} packets={stat['packets']:<3} "
            f"energy={energy:8.2f} end={trace.stats.endtime}"
        )

    def on_seedlink_error(self):
        print("SeedLink error")

    def on_terminate(self):
        print("SeedLink connection terminated")


def main():
    inventory = load_inventory()
    server = inventory.get(
        "seedlink_server",
        "rtserve.earthscope.org:18000",
    )

    sensors = inventory.get("sensors", [])

    enabled_sensors = [
        sensor
        for sensor in sensors
        if sensor.get("state", "active") != "disabled"
    ]

    valid_keys = {
        sensor_key(
            sensor["network"],
            sensor["station"],
            sensor["channel"],
        )
        for sensor in enabled_sensors
    }

    print("==============================================")
    print("SeedLink discovery review")
    print("Server:", server)
    print("Inventory:", INVENTORY_FILE)
    print("Sensors to review:", len(enabled_sensors))
    print("Duration:", REVIEW_DURATION_SECONDS, "seconds")
    print("==============================================")

    if not enabled_sensors:
        print("No enabled sensors to review.")
        inventory["updated_at"] = now_iso()
        inventory["review_duration_seconds"] = REVIEW_DURATION_SECONDS
        save_inventory(inventory)
        return

    client = ReviewClient(server, valid_keys)

    for sensor in enabled_sensors:
        key = sensor_key(
            sensor["network"],
            sensor["station"],
            sensor["channel"],
        )

        print(
            f"Selecting {key} "
            f"| state={sensor.get('state', 'active')} "
            f"| {sensor.get('name') or key}"
        )

        client.select_stream(
            sensor["network"],
            sensor["station"],
            sensor["channel"],
        )

    signal.signal(signal.SIGALRM, stop_on_timeout)
    signal.alarm(REVIEW_DURATION_SECONDS)

    try:
        client.run()
    except ReviewTimeout:
        print("")
        print("Review time finished.")
    except KeyboardInterrupt:
        print("")
        print("Stopped manually.")
    finally:
        signal.alarm(0)

    now = UTCDateTime()
    reviewed_at = now_iso()

    for sensor in enabled_sensors:
        key = sensor_key(
            sensor["network"],
            sensor["station"],
            sensor["channel"],
        )

        stat = client.stats.get(key)

        sensor["reviewed_at"] = reviewed_at

        if stat is None or stat["packets"] == 0:
            sensor["availability_state"] = "down"
            sensor["packets_last_revision"] = 0
            sensor["approx_latency_seconds"] = None
            sensor["mean_review_energy"] = None
            sensor["review_note"] = "no packets received during review"
            sensor.pop("trace_id_last_revision", None)
            sensor.pop("sampling_rate_hz", None)
            continue

        latency = float(now - stat["last_end"])
        mean_energy = stat["total_energy"] / stat["packets"]

        if latency <= MAX_ALIVE_LATENCY_SECONDS:
            availability_state = "active"
            review_note = "recent packets received"
        else:
            availability_state = "high_latency"
            review_note = "packets received with high latency"

        sensor["availability_state"] = availability_state
        sensor["trace_id_last_revision"] = stat["trace_id"]
        sensor["packets_last_revision"] = stat["packets"]
        sensor["approx_latency_seconds"] = round(latency, 1)
        sensor["sampling_rate_hz"] = stat["sampling_rate"]
        sensor["mean_review_energy"] = round(mean_energy, 2)
        sensor["review_note"] = review_note

    inventory["updated_at"] = reviewed_at
    inventory["review_duration_seconds"] = REVIEW_DURATION_SECONDS

    save_inventory(inventory)

    print("")
    print("Inventory updated:", INVENTORY_FILE)
    print("Summary:")

    for sensor in enabled_sensors:
        key = sensor_key(
            sensor["network"],
            sensor["station"],
            sensor["channel"],
        )

        print(
            f"{key} "
            f"availability={sensor.get('availability_state')} "
            f"packets={sensor.get('packets_last_revision')} "
            f"latency={sensor.get('approx_latency_seconds')}"
        )


if __name__ == "__main__":
    main()
