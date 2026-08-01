#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent

TOKEN_FILE = PROJECT_DIR / "secrets" / "telegram_bot_token.txt"
TEXT_FILE = PROJECT_DIR / "config" / "ui_es.json"
STATE_FILE = PROJECT_DIR / "runtime" / "telegram_notice_state.json"
HISTORY_FILE = PROJECT_DIR / "persistent" / "confirmed_multisignals.json"
CHANNEL_CACHE_FILE = PROJECT_DIR / "runtime" / "telegram_channel_cache.json"

CHAT_ID = "-1003849390782"
CHANNEL_USERNAME = "@redcuyum"
CHANNEL_URL = "https://t.me/redcuyum"

TARGET_EVENT_LEVEL = "multicell_anticipation"
MAX_RECENT_EVENTS = 10
CHANNEL_CACHE_SECONDS = 600

PUBLISH_LOCK = Lock()
CHANNEL_LOCK = Lock()


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Token file does not exist: {TOKEN_FILE}"
        )

    token = TOKEN_FILE.read_text(
        encoding="utf-8"
    ).strip()

    if not token:
        raise RuntimeError(
            "Telegram token file is empty."
        )

    if ":" not in token:
        raise RuntimeError(
            "Telegram token does not appear valid."
        )

    return token


def load_ui_texts() -> dict[str, Any]:
    if not TEXT_FILE.exists():
        raise RuntimeError(
            f"UI text file does not exist: {TEXT_FILE}"
        )

    try:
        data = json.loads(
            TEXT_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {TEXT_FILE}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            "UI text file root must be a JSON object."
        )

    return data


def load_notice_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {
            "active": False,
        }

    try:
        data = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {
        "active": False,
    }


def save_notice_state(
    state: dict[str, Any],
) -> None:
    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = STATE_FILE.with_suffix(
        ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(
        temporary_file,
        STATE_FILE,
    )


def translate_direction(
    direction: str,
    texts: dict[str, Any],
) -> str:
    internal_value = str(
        direction or ""
    ).strip().lower()

    translations = texts.get(
        "directions",
        {},
    )

    if not isinstance(translations, dict):
        translations = {}

    return str(
        translations.get(
            internal_value,
            internal_value,
        )
    )


def build_notice(
    direction: str,
    seconds: int,
    texts: dict[str, Any],
) -> str:
    telegram_texts = texts.get(
        "telegram",
        {},
    )

    if not isinstance(telegram_texts, dict):
        raise RuntimeError(
            "Telegram UI texts are missing."
        )

    visible_direction = translate_direction(
        direction,
        texts,
    )

    detection_line = str(
        telegram_texts.get(
            "detected_signals",
            (
                "Señales detectadas:\n"
                "[dirección] - [segundos] segundos restantes."
            ),
        )
    )

    detection_line = detection_line.replace(
        "[dirección]",
        visible_direction,
    )

    detection_line = detection_line.replace(
        "[segundos]",
        str(seconds),
    )

    experimental_record = str(
        telegram_texts.get(
            "experimental_record",
            "Registro automático y experimental.",
        )
    )

    not_official = str(
        telegram_texts.get(
            "not_official",
            "Cuyum no constituye información oficial.",
        )
    )

    return "\n".join(
        [
            detection_line,
            experimental_record,
            not_official,
        ]
    )


def send_message(
    text: str,
) -> dict[str, Any]:
    token = load_token()

    url = (
        f"https://api.telegram.org/"
        f"bot{token}/sendMessage"
    )

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
            f"Could not connect to Telegram: "
            f"{error.reason}"
        ) from error

    if not isinstance(result, dict):
        raise RuntimeError(
            "Telegram returned an invalid response."
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram rejected the message: {result}"
        )

    return result


def load_channel_cache() -> dict[str, Any]:
    if not CHANNEL_CACHE_FILE.exists():
        return {}

    try:
        data = json.loads(
            CHANNEL_CACHE_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def save_channel_cache(
    cache: dict[str, Any],
) -> None:
    CHANNEL_CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = CHANNEL_CACHE_FILE.with_suffix(
        ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            cache,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(
        temporary_file,
        CHANNEL_CACHE_FILE,
    )


def fetch_channel_member_count() -> int:
    token = load_token()

    url = (
        f"https://api.telegram.org/"
        f"bot{token}/getChatMemberCount"
    )

    encoded_data = urllib.parse.urlencode(
        {
            "chat_id": CHANNEL_USERNAME,
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
            timeout=8,
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
            f"Could not connect to Telegram: "
            f"{error.reason}"
        ) from error

    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError(
            f"Telegram rejected member count request: {result}"
        )

    return max(
        0,
        int(result["result"]),
    )


def telegram_channel_snapshot() -> dict[str, Any]:
    with CHANNEL_LOCK:
        cache = load_channel_cache()
        now = datetime.now(timezone.utc)

        cached_at_text = str(
            cache.get("updated_at") or ""
        )

        cached_at = None

        if cached_at_text:
            try:
                cached_at = datetime.fromisoformat(
                    cached_at_text
                )
            except ValueError:
                cached_at = None

        cache_is_fresh = (
            cached_at is not None
            and (now - cached_at).total_seconds()
            < CHANNEL_CACHE_SECONDS
            and isinstance(cache.get("members"), int)
        )

        if cache_is_fresh:
            return {
                "channel": CHANNEL_USERNAME,
                "url": CHANNEL_URL,
                "members": cache["members"],
                "updated_at": cached_at_text,
            }

        try:
            members = fetch_channel_member_count()

            updated_cache = {
                "members": members,
                "updated_at": now.isoformat(),
            }

            save_channel_cache(
                updated_cache
            )

            return {
                "channel": CHANNEL_USERNAME,
                "url": CHANNEL_URL,
                "members": members,
                "updated_at": updated_cache["updated_at"],
            }

        except RuntimeError:
            return {
                "channel": CHANNEL_USERNAME,
                "url": CHANNEL_URL,
                "members": cache.get("members"),
                "updated_at": cache.get("updated_at"),
            }


def as_seconds(
    value: Any,
) -> int:
    try:
        return max(
            0,
            int(round(float(value))),
        )
    except (TypeError, ValueError):
        return 0


def get_notice_data(
    fused: dict[str, Any],
) -> tuple[str, str, int] | None:
    event = fused.get(
        "event",
        {},
    ) or {}

    if event.get("level") != TARGET_EVENT_LEVEL:
        return None

    early_flags = event.get(
        "early_flags",
        [],
    ) or []

    if not early_flags:
        return None

    cell_id = str(
        early_flags[0]
    )

    cells = fused.get(
        "cells",
        {},
    ) or {}

    cell = cells.get(
        cell_id,
        {},
    ) or {}

    direction = (
        cell.get("direction_label")
        or cell.get("direction")
        or cell.get("short_label")
        or cell_id
    )

    seconds = as_seconds(
        cell.get(
            "effective_warning_seconds",
            cell.get(
                "warning_seconds",
                0,
            ),
        )
    )

    return (
        cell_id,
        str(direction),
        seconds,
    )


def load_confirmed_history() -> dict[str, Any]:
    if not HISTORY_FILE.exists():
        return {
            "total": 0,
            "recent": [],
        }

    try:
        data = json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, dict):
            return {
                "total": 0,
                "recent": [],
            }

        total = int(
            data.get(
                "total",
                0,
            ) or 0
        )

        recent = data.get(
            "recent",
            [],
        )

        if not isinstance(recent, list):
            recent = []

        return {
            "total": max(
                0,
                total,
            ),
            "recent": recent[
                -MAX_RECENT_EVENTS:
            ],
        }

    except Exception:
        return {
            "total": 0,
            "recent": [],
        }


def save_confirmed_history(
    history: dict[str, Any],
) -> None:
    HISTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = HISTORY_FILE.with_suffix(
        ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(
        temporary_file,
        HISTORY_FILE,
    )


def record_confirmed_multisignal(
    *,
    cell_id: str,
    direction: str,
    seconds: int,
    texts: dict[str, Any],
) -> dict[str, Any]:
    history = load_confirmed_history()

    record_id = int(
        history.get(
            "total",
            0,
        )
    ) + 1

    event = {
        "id": record_id,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "cell_id": cell_id,
        "direction": direction,
        "direction_label": translate_direction(
            direction,
            texts,
        ),
        "warning_seconds": seconds,
    }

    recent = list(
        history.get(
            "recent",
            [],
        )
    )

    recent.insert(0, event)

    updated_history = {
        "total": record_id,
        "recent": recent[
            :MAX_RECENT_EVENTS
        ],
    }

    save_confirmed_history(
        updated_history
    )

    return event


def confirmed_multisignals_snapshot() -> dict[str, Any]:
    history = load_confirmed_history()

    recent = list(
        history.get(
            "recent",
            [],
        )
    )

    return {
        "total": int(
            history.get(
                "total",
                0,
            )
        ),
        "recent": recent,
    }


def publish_fused_notice(
    fused: dict[str, Any],
) -> bool:
    with PUBLISH_LOCK:
        state = load_notice_state()
        notice_data = get_notice_data(fused)

        if notice_data is None:
            if state.get("active"):
                save_notice_state(
                    {
                        "active": False,
                    }
                )

            return False

        if state.get("active"):
            return False

        cell_id, direction, seconds = notice_data

        texts = load_ui_texts()

        # El registro propio de Cuyum se crea antes de intentar Telegram.
        event = record_confirmed_multisignal(
            cell_id=cell_id,
            direction=direction,
            seconds=seconds,
            texts=texts,
        )

        record_id = int(
            event["id"]
        )

        # El episodio queda marcado inmediatamente para evitar duplicados,
        # incluso si Telegram no está disponible.
        save_notice_state(
            {
                "active": True,
                "cell_id": cell_id,
                "direction": direction,
                "seconds": seconds,
                "record_id": record_id,
            }
        )

        message = build_notice(
            direction,
            seconds,
            texts,
        )

        # No se modifica el mensaje actual:
        # solo se añade una línea vacía y el ID propio de Cuyum.
        message = (
            f"{message.rstrip()}\n\n"
            f"ID #{record_id}"
        )

        try:
            result = send_message(
                message
            )

            # Telegram confirmó la publicación.
            # Su identificador interno no forma parte de la trazabilidad de Cuyum.
            save_notice_state(
                {
                    "active": True,
                    "cell_id": cell_id,
                    "direction": direction,
                    "seconds": seconds,
                    "record_id": record_id,
                }
            )

        except Exception as error:
            print(
                (
                    "Telegram notice error after "
                    f"Cuyum record ID #{record_id}: "
                    f"{error}"
                ),
                file=sys.stderr,
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
        help=(
            "Internal direction, "
            "for example: southwest."
        ),
    )

    parser.add_argument(
        "seconds",
        type=int,
        help=(
            "Estimated remaining "
            "propagation seconds."
        ),
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

        result = send_message(
            message
        )

    except RuntimeError as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        "Telegram notice sent."
    )

    print(
        f"Message ID: "
        f"{result['result']['message_id']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
