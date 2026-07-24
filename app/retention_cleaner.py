import json
import os
from datetime import datetime, timezone, timedelta

CONFIG_FILE = "config_cuyum.json"
JSONL_RETENTION = {
    "runtime/audit_recent.jsonl": "audit_days",
    "runtime/events_recent.jsonl": "events_days",
}
LOG_FILES = [
    "logs_servidor.txt",
    "logs_lector.txt",
    "logs_descubridor.txt",
    "logs_sensor_auditor.txt",
    "logs_auto_cell_01.txt",
]


def now_utc():
    return datetime.now(timezone.utc)


def read_config():
    if not os.path.exists(CONFIG_FILE):
        return {"retention": {"logs_days": 7, "audit_days": 31, "events_days": 31, "max_log_mb": 10}}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def trim_jsonl(path, days):
    if not os.path.exists(path):
        return
    cutoff = now_utc() - timedelta(days=int(days))
    kept = []
    total = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            total += 1
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            ts = parse_timestamp(item.get("timestamp") or item.get("ultima_actualizacion"))
            if ts is None:
                continue
            if ts >= cutoff:
                kept.append(json.dumps(item, ensure_ascii=False))

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
    os.replace(tmp, path)
    print(f"{path}: {total} -> {len(kept)} lines kept")


def trim_log_if_needed(path, max_mb):
    if not os.path.exists(path):
        return
    max_bytes = int(max_mb * 1024 * 1024)
    size = os.path.getsize(path)
    if size <= max_bytes:
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()[-5000:]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"{path}: trimmed by size, kept last {len(lines)} lines")


def main():
    config = read_config()
    retention = config.get("retention", {})

    for path, key in JSONL_RETENTION.items():
        days = retention.get(key, 31)
        trim_jsonl(path, days)

    max_log_mb = float(retention.get("max_log_mb", 10))
    for path in LOG_FILES:
        trim_log_if_needed(path, max_log_mb)

    print("Retention cleanup finished")


if __name__ == "__main__":
    main()
