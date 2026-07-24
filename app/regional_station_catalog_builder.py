import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from obspy import UTCDateTime
from obspy.clients.fdsn import Client


BASE = Path(".")
SYSTEM_CENTER_FILE = BASE / "config/system_center.json"
OUT_PREVIEW = BASE / "config/seedlink_station_catalog.preview.json"
REPORT_FILE = BASE / "runtime/regional_station_catalog_report.txt"

DEFAULT_CHANNELS = ["BHZ", "HHZ", "EHZ", "SHZ"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_center(args):
    if args.lat is not None and args.lon is not None:
        return {
            "label": args.label or "Custom center",
            "lat": float(args.lat),
            "lon": float(args.lon),
        }

    data = load_json(SYSTEM_CENTER_FILE, {})
    if "lat" not in data or "lon" not in data:
        raise SystemExit("ERROR: config/system_center.json does not contain lat/lon")

    return {
        "label": data.get("label") or data.get("name") or "System center",
        "lat": float(data["lat"]),
        "lon": float(data["lon"]),
    }


def channel_rank(channel):
    order = {"BHZ": 0, "HHZ": 1, "EHZ": 2, "SHZ": 3}
    return order.get(channel, 99)


def add_sensor(sensors, item):
    key = f"{item['network']}.{item['station']}.{item['channel']}"

    old = sensors.get(key)
    if old is None:
        sensors[key] = item
        return

    old_rank = channel_rank(old.get("channel"))
    new_rank = channel_rank(item.get("channel"))

    if new_rank < old_rank:
        sensors[key] = item
        return

    if new_rank == old_rank and item.get("distance_km", 999999) < old.get("distance_km", 999999):
        sensors[key] = item


def fetch_provider(provider, center, max_km, channels, timeout):
    client = Client(provider, timeout=timeout)

    max_radius_degrees = max_km / 111.19
    channel_expr = ",".join(channels)
    now = UTCDateTime()

    inv = client.get_stations(
        latitude=center["lat"],
        longitude=center["lon"],
        maxradius=max_radius_degrees,
        channel=channel_expr,
        level="channel",
        startbefore=now,
        endafter=now,
    )

    found = []

    for net in inv:
        for sta in net:
            for cha in sta:
                lat = getattr(cha, "latitude", None)
                lon = getattr(cha, "longitude", None)

                if lat is None or lon is None:
                    lat = getattr(sta, "latitude", None)
                    lon = getattr(sta, "longitude", None)

                if lat is None or lon is None:
                    continue

                dist = haversine_km(center["lat"], center["lon"], lat, lon)

                if dist > max_km:
                    continue

                code = f"{net.code}.{sta.code}.{cha.code}"

                found.append({
                    "sensor_id": code,
                    "network": net.code,
                    "station": sta.code,
                    "channel": cha.code,
                    "location": cha.location_code or "",
                    "name": sta.site.name if getattr(sta, "site", None) and sta.site.name else sta.code,
                    "lat": round(float(lat), 6),
                    "lon": round(float(lon), 6),
                    "distance_km": round(float(dist), 1),
                    "source_provider": provider,
                    "source": "fdsn_station_service",
                    "server": "rtserve.earthscope.org",
                    "server_note": "SeedLink availability is not guaranteed by FDSN metadata; liveness must be tested later.",
                    "can_confirm": True,
                    "can_trigger": True,
                    "role": "candidate",
                })

    return found


def build_catalog(center, max_km, providers, channels, timeout):
    sensors = {}
    provider_results = []

    for provider in providers:
        provider = provider.strip()
        if not provider:
            continue

        try:
            found = fetch_provider(provider, center, max_km, channels, timeout)
            provider_results.append({
                "provider": provider,
                "ok": True,
                "count": len(found),
                "error": None,
            })

            for item in found:
                add_sensor(sensors, item)

        except Exception as exc:
            provider_results.append({
                "provider": provider,
                "ok": False,
                "count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            })

    ordered = dict(
        sorted(
            sensors.items(),
            key=lambda kv: (
                kv[1].get("distance_km", 999999),
                channel_rank(kv[1].get("channel")),
                kv[0],
            )
        )
    )

    return {
        "version": 2,
        "description": "Regional SeedLink station metadata catalog generated from FDSN station services. SeedLink liveness still needs a separate test.",
        "generated_at": now_iso(),
        "center": center,
        "max_distance_km": max_km,
        "channels": channels,
        "providers": provider_results,
        "sensors": ordered,
    }


def write_report(catalog):
    lines = []
    center = catalog["center"]

    lines.append("CUYUM regional station catalog preview")
    lines.append("=" * 60)
    lines.append(f"Generated: {catalog['generated_at']}")
    lines.append(f"Center: {center.get('label')} lat={center.get('lat')} lon={center.get('lon')}")
    lines.append(f"Max distance: {catalog['max_distance_km']} km")
    lines.append(f"Channels: {', '.join(catalog['channels'])}")
    lines.append("")
    lines.append("Providers:")
    for p in catalog["providers"]:
        status = "OK" if p["ok"] else "ERROR"
        lines.append(f"- {p['provider']}: {status}, count={p['count']}, error={p['error']}")
    lines.append("")
    lines.append(f"Sensors found: {len(catalog['sensors'])}")
    lines.append("")

    for i, (code, s) in enumerate(catalog["sensors"].items(), 1):
        lines.append(
            f"{i:03d}. {code:<14} "
            f"{s.get('name',''):<32} "
            f"{s.get('distance_km'):>7} km "
            f"lat={s.get('lat')} lon={s.get('lon')} "
            f"provider={s.get('source_provider')}"
        )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build a regional station catalog preview for Cuyum.")
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--max-km", type=float, default=800)
    parser.add_argument("--provider", action="append", default=None)
    parser.add_argument("--channels", default=",".join(DEFAULT_CHANNELS))
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--apply", action="store_true", help="Apply preview to config/seedlink_station_catalog.json")
    args = parser.parse_args()

    center = read_center(args)
    providers = args.provider or ["IRIS"]
    channels = [x.strip().upper() for x in args.channels.split(",") if x.strip()]

    catalog = build_catalog(center, args.max_km, providers, channels, args.timeout)

    save_json(OUT_PREVIEW, catalog)
    write_report(catalog)

    print(f"Written: {OUT_PREVIEW}")
    print(f"Written: {REPORT_FILE}")
    print(f"Sensors found: {len(catalog['sensors'])}")

    if args.apply:
        target = BASE / "config/seedlink_station_catalog.json"
        backup = BASE / f"config/seedlink_station_catalog.json.backup_before_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if target.exists():
            backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Backup: {backup}")
        save_json(target, catalog)
        print(f"Applied: {target}")


if __name__ == "__main__":
    main()
