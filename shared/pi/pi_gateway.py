import base64
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

import requests


ESP32_SNAPSHOT_URL = os.getenv("ESP32_SNAPSHOT_URL", "http://192.168.1.18/snapshot")
SERVER_INFER_URL = os.getenv("SERVER_INFER_URL", "http://192.168.1.20:8001/infer")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "3"))
AUDIO_OUTPUT_DIR = Path(os.getenv("AUDIO_OUTPUT_DIR", "./audio_cache"))
USE_YOLO = os.getenv("USE_YOLO", "true").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_SELECTION = os.getenv("ENABLE_SELECTION", "true").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_TTS = os.getenv("ENABLE_TTS", "true").strip().lower() in {"1", "true", "yes", "on"}


def fetch_snapshot() -> bytes:
    response = requests.get(ESP32_SNAPSHOT_URL, timeout=10)
    response.raise_for_status()
    return response.content


def send_to_server(image_bytes: bytes) -> dict:
    files = {"file": ("snapshot.jpg", image_bytes, "image/jpeg")}
    response = requests.post(
        SERVER_INFER_URL,
        files=files,
        params={
            "use_yolo": str(USE_YOLO).lower(),
            "enable_selection": str(ENABLE_SELECTION).lower(),
            "enable_tts": str(ENABLE_TTS).lower(),
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def save_and_play_audio(result: dict) -> Path | None:
    if not result.get("ok"):
        return None

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = result.get("audio_filename") or "last_tts.wav"
    output_path = AUDIO_OUTPUT_DIR / filename

    audio_base64 = result.get("audio_base64")
    if audio_base64:
        output_path.write_bytes(base64.b64decode(audio_base64))
    else:
        download_url = result.get("audio_download_url")
        if not download_url:
            return None
        download_audio(download_url, output_path)

    play_audio(output_path, mime_type=result.get("audio_mime_type"))
    return output_path


def download_audio(download_url: str, output_path: Path) -> None:
    absolute_url = urljoin(_server_base_url(), download_url)
    response = requests.get(absolute_url, timeout=60)
    response.raise_for_status()
    output_path.write_bytes(response.content)


def play_audio(audio_path: Path, *, mime_type: str | None = None) -> None:
    player = _resolve_audio_player(mime_type=mime_type, suffix=audio_path.suffix.lower())
    if not player:
        print(f"Saved audio to {audio_path}, but no Linux audio player was found.")
        return

    subprocess.run([player, str(audio_path)], check=False)


def _resolve_audio_player(*, mime_type: str | None, suffix: str) -> str | None:
    if mime_type == "audio/mpeg" or suffix == ".mp3":
        for candidate in ("mpg123", "ffplay", "cvlc"):
            if shutil.which(candidate):
                if candidate == "ffplay":
                    return _wrap_ffplay(candidate)
                if candidate == "cvlc":
                    return _wrap_cvlc(candidate)
                return candidate

    for candidate in ("aplay", "paplay", "ffplay", "cvlc"):
        if shutil.which(candidate):
            if candidate == "ffplay":
                return _wrap_ffplay(candidate)
            if candidate == "cvlc":
                return _wrap_cvlc(candidate)
            return candidate

    return None


def _wrap_ffplay(command: str) -> str:
    wrapper = Path(tempfile.gettempdir()) / "pi_gateway_ffplay.sh"
    wrapper.write_text("#!/bin/sh\nexec ffplay -nodisp -autoexit \"$1\"\n", encoding="utf-8")
    wrapper.chmod(0o755)
    return str(wrapper)


def _wrap_cvlc(command: str) -> str:
    wrapper = Path(tempfile.gettempdir()) / "pi_gateway_cvlc.sh"
    wrapper.write_text("#!/bin/sh\nexec cvlc --play-and-exit \"$1\"\n", encoding="utf-8")
    wrapper.chmod(0o755)
    return str(wrapper)


def _server_base_url() -> str:
    if SERVER_INFER_URL.endswith("/infer"):
        return SERVER_INFER_URL[: -len("/infer")]
    return SERVER_INFER_URL.rstrip("/")


def summarize_result(result: dict) -> str:
    if not result.get("ok"):
        return f"ERR: {result.get('message')}"

    product_name = result.get("product_name") or "Unknown"
    price_text = result.get("price_text") or "N/A"
    audio_ready = bool(result.get("audio_base64") or result.get("audio_download_url"))
    return f"OK: {product_name} | {price_text} | audio={'yes' if audio_ready else 'no'}"


def main() -> None:
    while True:
        try:
            image_bytes = fetch_snapshot()
            result = send_to_server(image_bytes)
            print(result)
            audio_path = save_and_play_audio(result)
            if audio_path:
                print(f"Played audio from {audio_path}")
            else:
                print(summarize_result(result))
        except Exception as exc:
            print("Error:", exc)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
