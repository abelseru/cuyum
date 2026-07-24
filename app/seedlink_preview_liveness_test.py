import argparse
import json
import signal
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient


BASE = Path(".")
DEFAULT_INVENTORY = BASE / "runtime/bootstrap_preview/candidate_inventory.preview.json"
OUT_JSON = BASE / "runtime/seedlink_preview_liveness_result.json"
OUT_TXT = BASE / "runtime/seedlink_preview_liveness_result.txt"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sensor_key(s):
    return f"{s['red']}.{s['estacion']}.{s['canal']}"


def trace_key(trace_id):
    parts = trace_id.split(".")
    if len(parts) < 4:
        return None
    return f"{parts[0]}.{parts[1]}.{parts[3]}"


def simple_energy(trace):
    data = trace.data
    if data is None or len(data) == 0:
        return 0.0
    return sum(abs(float(x)) for x in data) / len(data)


class TimeDone(Exception):
    pass


def stop_by_time(signum, frame):
    raise TimeDone()


class PreviewClient(EasySeedLinkClient):
    def __init__(self, server, valid_keys):
        super().__init__(server)
        self.valid_keys = valid_keys
        self.stats = defaultdict(lambda: {
            "packets": 0,
            "energy_total": 0.0,
            "last_end": None,
            "sampling_rate": None,
            "trace_id": None,
        })

    def on_data(self, trace):
        key = trace_key(trace.id)
        if key not in self.valid_keys:
            return

        energy = simple_energy(trace)
        s = self.stats[key]
        s["packets"] += 1
        s["energy_total"] += energy
        s["last_end"] = trace.stats.endtime
        s["sampling_rate"] = trace.stats.sampling_rate
        s["trace_id"] = trace.id

        print(
            f"OK {key:<15} packets={s['packets']:<3} "
            f"energy={energy:8.2f} end={trace.stats.endtime}"
        )

    def on_seedlink_error(self):
        print("SeedLink error")

    def on_terminate(self):
        print("SeedLink terminated")


def write_report(result):
    lines = []
    center = result.get("center", {})
    lines.append("CUYUM SeedLink preview liveness test")
    lines.append("=" * 60)
    lines.append(f"Generated: {result.get('generated_at')}")
    lines.append(f"Center: {center.get('label')} lat={center.get('lat')} lon={center.get('lon')}")
    lines.append(f"Server: {result.get('server')}")
    lines.append(f"Duration: {result.get('duration_seconds')} seconds")
    lines.append("")
    lines.append(f"Alive sensors: {result.get('alive_count')}")
    lines.append(f"Total sensors: {result.get('total_count')}")
    lines.append("")
    for s in result.get("sensors", []):
        lines.append(
            f"{s.get('status').upper():<8} "
            f"{s.get('code'):<14} "
            f"packets={s.get('packets'):<3} "
            f"latency={s.get('latency_seconds')} "
            f"freq={s.get('sampling_rate')} "
            f"{s.get('name')}"
        )

    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Test SeedLink liveness for candidate inventory preview.")
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--duration", type=int, default=90)
    parser.add_argument("--max-latency", type=float, default=60)
    args = parser.parse_args()

    inv = load_json(args.inventory)
    server = inv.get("seedlink_server") or inv.get("servidor_seedlink") or "rtserve.earthscope.org:18000"
    sensors = inv.get("sensores", [])
    keys = {sensor_key(s) for s in sensors}

    print("==============================================")
    print("SeedLink preview liveness test")
    print("Server:", server)
    print("Inventory:", args.inventory)
    print("Sensors:", len(sensors))
    print("Duration:", args.duration)
    print("==============================================")

    client = PreviewClient(server, keys)

    for s in sensors:
        print(f"Selecting {sensor_key(s)} | {s.get('nombre')}")
        client.select_stream(s["red"], s["estacion"], s["canal"])

    signal.signal(signal.SIGALRM, stop_by_time)
    signal.alarm(args.duration)

    try:
        client.run()
    except TimeDone:
        print("")
        print("Time window finished.")
    except KeyboardInterrupt:
        print("")
        print("Stopped manually.")
    except Exception as exc:
        print(f"reader_error: {type(exc).__name__}: {exc}")

    now = UTCDateTime()
    result_sensors = []

    for s in sensors:
        key = sensor_key(s)
        stat = client.stats.get(key)
        packets = 0 if stat is None else stat["packets"]

        item = dict(s)
        item["code"] = key

        if not stat or packets == 0 or stat["last_end"] is None:
            item["status"] = "down"
            item["packets"] = 0
            item["latency_seconds"] = None
            item["sampling_rate"] = None
            item["trace_id"] = None
            item["energy_average"] = None
        else:
            latency = float(now - stat["last_end"])
            item["status"] = "alive" if latency <= args.max_latency else "high_latency"
            item["packets"] = packets
            item["latency_seconds"] = round(latency, 1)
            item["sampling_rate"] = stat["sampling_rate"]
            item["trace_id"] = stat["trace_id"]
            item["energy_average"] = round(stat["energy_total"] / packets, 2)

        result_sensors.append(item)

    alive_count = sum(1 for s in result_sensors if s["status"] == "alive")

    result = {
        "generated_at": now_iso(),
        "center": inv.get("center", {}),
        "server": server,
        "duration_seconds": args.duration,
        "max_latency_seconds": args.max_latency,
        "total_count": len(result_sensors),
        "alive_count": alive_count,
        "sensors": result_sensors,
    }

    save_json(OUT_JSON, result)
    write_report(result)

    print("")
    print(f"Written: {OUT_JSON}")
    print(f"Written: {OUT_TXT}")
    print(f"Alive sensors: {alive_count}/{len(result_sensors)}")


if __name__ == "__main__":
    main()
