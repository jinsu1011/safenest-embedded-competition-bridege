#!/usr/bin/env python3
"""Serve the SafeNest LCD showcase and proxy the live runtime API."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SHOWCASE_TTS = {
    "a": ("DANGER", "danger_fall.wav", "낙상 위험"),
    "b": ("DANGER", "danger_apnea.wav", "무호흡 위험"),
    "c": ("DANGER", "danger_co2.wav", "CO₂ 위험"),
    "d": ("WARNING", "warning_respiration.wav", "호흡 이상 주의"),
    "e": ("WARNING", "warning_co2.wav", "CO₂ 주의"),
    "f": ("WARNING", "warning_no_motion.wav", "장시간 무움직임 주의"),
    "g": ("WARNING", "warning_thermal.wav", "열화상 이상 주의"),
    "h": ("WARNING", "warning_generic.wav", "일반 주의"),
    "i": ("DANGER", "danger_generic.wav", "일반 위험"),
    "j": ("DANGER", "danger_fall.wav", "긴급 낙상"),
    "k": ("DANGER", "danger_apnea.wav", "긴급 무호흡"),
    "l": ("DANGER", "danger_co2.wav", "긴급 CO₂"),
    "m": ("DANGER", "danger_generic.wav", "긴급 복합 위험"),
    "n": ("WARNING", "warning_co2.wav", "CO₂ 주의 · 사람 없음"),
}

LCD_STATES = {
    "normal-empty",
    "normal-occupied",
    "warning",
    "danger",
    "emergency",
    "offline",
}

SHOWCASE_ALERT_COPY = {
    "a": (
        "danger", "낙상 위험", "위험",
        "작업자 낙상이 감지되었습니다",
        "즉시 현장을 확인하고 구조를 요청하세요",
    ),
    "b": (
        "danger", "무호흡 위험", "위험",
        "호흡이 멈춘 것으로 보입니다",
        "즉시 기도를 확보하고 119에 신고하세요",
    ),
    "c": (
        "danger", "CO₂ 위험", "위험",
        "CO₂ 농도가 위험 수준입니다",
        "즉시 대피시키고 강제 환기를 시작하세요",
    ),
    "d": (
        "warning", "호흡 이상 주의", "주의",
        "호흡 패턴에 이상이 있습니다",
        "작업자의 호흡 상태를 확인하세요",
    ),
    "e": (
        "warning", "CO₂ 주의", "주의",
        "CO₂ 농도가 높습니다",
        "환기 후 작업자 상태를 확인하세요",
    ),
    "f": (
        "warning", "장시간 무움직임 주의", "주의",
        "장시간 움직임이 감지되지 않습니다",
        "작업자에게 응답을 요청하세요",
    ),
    "g": (
        "warning", "열화상 이상 주의", "주의",
        "열화상에서 이상 온도가 감지되었습니다",
        "작업자 체온과 주변 열원을 확인하세요",
    ),
    "h": (
        "warning", "일반 주의", "주의",
        "주의가 필요한 상태입니다",
        "작업자 상태를 확인하세요",
    ),
    "i": (
        "danger", "일반 위험", "위험",
        "위험 상황이 감지되었습니다",
        "즉시 현장을 확인하세요",
    ),
    "j": (
        "emergency", "긴급 · 낙상", "긴급",
        "낙상 후 작업자가 반응하지 않습니다",
        "즉시 현장을 확인하고 구조를 요청하세요",
    ),
    "k": (
        "emergency", "긴급 · 무호흡", "긴급",
        "호흡이 멈추고 반응이 없습니다",
        "즉시 기도를 확보하고 119에 신고하세요",
    ),
    "l": (
        "emergency", "긴급 · CO₂ 중독", "긴급",
        "CO₂ 중독이 의심됩니다",
        "즉시 대피시키고 119에 신고하세요",
    ),
    "m": (
        "emergency", "긴급 · 복합 위험", "긴급",
        "고체온·호흡 이상·무움직임이 동시에 감지되었습니다",
        "즉시 현장을 확인하고 구조를 요청하세요",
    ),
    "n": (
        "warning-empty", "환경 주의", "주의",
        "CO₂ 농도가 높습니다",
        "환기 후 작업자 상태를 확인하세요",
    ),
}


class ShowcaseAlert:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._payload: dict[str, str] | None = None

    def set(self, key: str) -> dict[str, str]:
        state, pill, title, subtitle, comment = SHOWCASE_ALERT_COPY[key]
        payload = {
            "key": key,
            "state": state,
            "pill": pill,
            "title": title,
            "subtitle": subtitle,
            "comment": comment,
        }
        with self._lock:
            self._payload = payload
        return payload

    def clear(self) -> None:
        with self._lock:
            self._payload = None

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = dict(self._payload) if self._payload is not None else None
        return {"active": payload is not None, "alert": payload}


class ShowcaseAudioPlayer:
    """Play bounded, pre-recorded showcase alerts without touching runtime TTS."""

    def __init__(self, audio_root: Path, audio_device: str | None) -> None:
        self.audio_root = audio_root
        self.audio_device = audio_device
        self._lock = threading.Lock()
        self._generation = 0
        self._process: subprocess.Popen[bytes] | None = None

    def trigger(self, key: str) -> dict[str, str]:
        level, filename, label = SHOWCASE_TTS[key]
        alert = "danger_siren.wav" if level == "DANGER" else "warning_chime.wav"
        paths = (self.audio_root / alert, self.audio_root / "messages" / filename)
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(", ".join(missing))

        with self._lock:
            self._generation += 1
            generation = self._generation
            previous = self._process
            self._process = None
        if previous is not None and previous.poll() is None:
            previous.terminate()

        threading.Thread(
            target=self._play_sequence,
            args=(generation, paths),
            name=f"showcase-tts-{key}",
            daemon=True,
        ).start()
        return {"key": key, "level": level, "label": label}

    def _play_sequence(self, generation: int, paths: tuple[Path, Path]) -> None:
        for path in paths:
            with self._lock:
                if generation != self._generation:
                    return
                command = ["aplay", "-q"]
                if self.audio_device:
                    command.extend(("-D", self.audio_device))
                command.append(str(path))
                try:
                    process = subprocess.Popen(command)
                except OSError as error:
                    print(f"Showcase TTS failed: {error}", flush=True)
                    return
                self._process = process
            return_code = process.wait()
            with self._lock:
                if self._process is process:
                    self._process = None
                if generation != self._generation:
                    return
            if return_code != 0:
                print(
                    f"Showcase TTS playback failed: {path} (exit {return_code})",
                    flush=True,
                )
                return


class ShowcaseHandler(SimpleHTTPRequestHandler):
    backend = "http://127.0.0.1:8000"
    audio_player: ShowcaseAudioPlayer
    alert: ShowcaseAlert

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/display.html")
            self.end_headers()
            return
        if self.path == "/api/showcase/alert":
            self._json_response(200, self.alert.snapshot())
            return
        if self.path.startswith("/api/"):
            self._proxy("GET")
            return
        if self.path == "/health":
            self._health()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/showcase/tts":
            self._showcase_tts()
            return
        if self.path == "/api/showcase/alert":
            self._showcase_alert()
            return
        if self.path.startswith("/api/"):
            self._proxy("POST")
            return
        self.send_error(404)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def _health(self) -> None:
        status = 200
        backend_status = "ok"
        try:
            with urllib.request.urlopen(
                f"{self.backend}/api/state", timeout=1.5
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"backend returned {response.status}")
        except Exception:
            status = 503
            backend_status = "unavailable"
        body = json.dumps(
            {"service": "lcd-showcase", "backend": backend_status},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _showcase_tts(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError("invalid body length")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            key = str(payload.get("key", "")).lower()
            state = payload.get("state")
            if state is not None and state not in LCD_STATES:
                raise ValueError("unknown LCD state")
            if key not in SHOWCASE_TTS:
                raise ValueError("unsupported showcase TTS key")
            result = {"ok": True, **self.audio_player.trigger(key)}
            result["alert"] = self.alert.set(key)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json_response(422, {"ok": False, "detail": str(error)})
            return
        except FileNotFoundError as error:
            self._json_response(503, {"ok": False, "detail": str(error)})
            return
        self._json_response(202, result)

    def _showcase_alert(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                raise ValueError("invalid body length")
            payload = json.loads(self.rfile.read(length)) if length else {}
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            key = str(payload.get("key", "")).lower()
            if payload.get("clear"):
                self.alert.clear()
            elif key in SHOWCASE_ALERT_COPY:
                self.alert.set(key)
            else:
                raise ValueError('expected {"clear": true} or a known cue key')
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json_response(422, {"ok": False, "detail": str(error)})
            return
        self._json_response(200, {"ok": True, **self.alert.snapshot()})

    def _json_response(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method: str) -> None:
        body = None
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length else b""

        headers = {"Accept": self.headers.get("Accept", "application/json")}
        if content_type := self.headers.get("Content-Type"):
            headers["Content-Type"] = content_type
        request = urllib.request.Request(
            f"{self.backend}{self.path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=3.0) as response:
                response_body = response.read()
                self.send_response(response.status)
                self.send_header(
                    "Content-Type",
                    response.headers.get("Content-Type", "application/json"),
                )
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
        except urllib.error.HTTPError as error:
            response_body = error.read()
            self.send_response(error.code)
            self.send_header(
                "Content-Type",
                error.headers.get("Content-Type", "application/json"),
            )
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            response_body = json.dumps(
                {"detail": "SafeNest backend unavailable", "error": str(error)},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8090, type=int)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--audio-root",
        default=str(
            Path(__file__).resolve().parent.parent
            / "RaspberryPi"
            / "Runtime"
            / "assets"
            / "audio"
        ),
    )
    parser.add_argument(
        "--audio-device",
        default=os.getenv("SAFENEST_TTS_AUDIO_DEVICE", "").strip(),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    handler = lambda *handler_args, **handler_kwargs: ShowcaseHandler(  # noqa: E731
        *handler_args, directory=str(root), **handler_kwargs
    )
    ShowcaseHandler.backend = args.backend.rstrip("/")
    ShowcaseHandler.audio_player = ShowcaseAudioPlayer(
        Path(args.audio_root).resolve(),
        args.audio_device or None,
    )
    ShowcaseHandler.alert = ShowcaseAlert()
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(
        f"SafeNest LCD showcase: http://{args.host}:{args.port}/display.html "
        f"-> {ShowcaseHandler.backend}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
