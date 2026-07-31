#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent

TOKEN_FILE = PROJECT_DIR / "secrets" / "telegram_bot_token.txt"
TEXT_FILE = PROJECT_DIR / "config" / "ui_es.json"
STATE_FILE = PROJECT_DIR / "runtime" / "telegram_notice_state.json"

CHAT_ID = "-1003849390782"
TARGET_EVENT_LEVEL = "multicell_anticipation"


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError(f"Token file does not exist: {TOKEN_FILE}")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise RuntimeError("Telegram token file is empty.")

    if ":" not in token:
        raise RuntimeError("Telegram token does not appear valid.")

    return token


def load_ui_texts() -> dict[str, Any]:
    if not TEXT_FILE.exists():
        raise RuntimeError(f"UI text file does not exist: {TEXT_FILE}")

    try:
        return json.loads(TEXT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {TEXT_FILE}: {error}"
        ) from error


def load_notice_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"active": False}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {"active": False}


def save_notice_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = STATE_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    os.replace(temporary_file, STATE_FILE)


def translate_direction(
    direction: str,
    texts: dict[str, Any],
) -> str:
    internal_value = str(direction or "").strip().lower()
    translations = texts.get("directions", {})

    return translations.get(internal_value, internal_value)


def build_notice(
    direction: str,
    seconds: int,
    texts: dict[str, Any],
) -> str:
    telegram_texts = texts["telegram"]

    visible_direction = translate_direction(
        direction,
        texts,
    )

    detection_line = telegram_texts["detected_signals"]

    detection_line = detection_line.replace(
        "[dirección]",
        visible_direction,
    )

    detection_line = detection_line.replace(
        "[segundos]",
        str(seconds),
    )

    return "\n".join(
        [
            detection_line,
            telegram_texts["experimental_record"],
            telegram_texts["not_official"],
        ]
    )


def send_message(text: str) -> dict[str, Any]:
    token = load_token()

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    encoded_data = urllib.parse.urlencode(
        {
            "chat_id": CHAT_ID,
            "text": text,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded_data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        response_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Telegram HTTP error {error.code}: "
            f"{response_body}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to Telegram: {error.reason}"
        ) from error

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram rejected the message: {result}"
        )

    return result


def as_seconds(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def get_notice_data(
    fused: dict[str, Any],
) -> tuple[str, str, int] | None:
    event = fused.get("event", {}) or {}

    if event.get("level") != TARGET_EVENT_LEVEL:
        return None

    early_flags = event.get("early_flags", []) or []

    if not early_flags:
        return None

    cell_id = str(early_flags[0])

    cells = fused.get("cells", {}) or {}
    cell = cells.get(cell_id, {}) or {}

    direction = (
        cell.get("direction_label")
        or cell.get("direction")
        or cell.get("short_label")
        or cell_id
    )

    seconds = as_seconds(
        cell.get(
            "effective_warning_seconds",
            cell.get("warning_seconds", 0),
        )
    )

    return cell_id, str(direction), seconds


def publish_fused_notice(
    fused: dict[str, Any],
) -> bool:
    state = load_notice_state()
    notice_data = get_notice_data(fused)

    if notice_data is None:
        if state.get("active"):
            save_notice_state({"active": False})

        return False

    if state.get("active"):
        return False

    cell_id, direction, seconds = notice_data

    texts = load_ui_texts()
    message = build_notice(
        direction,
        seconds,
        texts,
    )

    result = send_message(message)

    save_notice_state(
        {
            "active": True,
            "cell_id": cell_id,
            "direction": direction,
            "seconds": seconds,
            "message_id": result["result"]["message_id"],
        }
    )

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Send a Cuyum experimental notice "
            "to Telegram."
        )
    )

    parser.add_argument(
        "direction",
        help="Internal direction, for example: southwest.",
    )

    parser.add_argument(
        "seconds",
        type=int,
        help="Estimated remaining propagation seconds.",
    )

    arguments = parser.parse_args()

    if arguments.seconds < 0:
        print(
            "ERROR: seconds cannot be negative.",
            file=sys.stderr,
        )
        return 1

    try:
        texts = load_ui_texts()

        message = build_notice(
            arguments.direction,
            arguments.seconds,
            texts,
        )

        result = send_message(message)

    except RuntimeError as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print("Telegram notice sent.")
    print(
        f"Message ID: "
        f"{result['result']['message_id']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

