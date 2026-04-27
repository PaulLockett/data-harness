"""DuckDB conn + lazy model clients + Atomic[Capabilities] holder. One daemon per DH_NAME."""
from __future__ import annotations

import json
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path

import capabilities as _caps_mod


NAME = os.environ.get("DH_NAME", "default")
SOCK = f"/tmp/dh-{NAME}.sock"
PID = f"/tmp/dh-{NAME}.pid"
LOG = f"/tmp/dh-{NAME}.log"


def _log(msg: str) -> None:
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def _started_at() -> float:
    """Module-load time, used as 'daemon started'."""
    return _started_ts


_started_ts = time.monotonic()


class Daemon:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.lock = threading.Lock()
        # Detect Capabilities and publish via _caps_mod.current().
        c = _caps_mod.detect()
        _caps_mod._set_current(c)
        try:
            _caps_mod.start_adaptivity_loop(cadence_seconds=3.0)
        except Exception as e:
            _log(f"adaptivity_loop_failed: {e}")

    # ─── meta dispatch ───────────────────────────────────────────────────

    def handle_meta(self, msg: dict) -> dict:
        op = msg.get("meta")
        if op == "ping":
            return {"meta": "pong"}
        if op == "status":
            c = _caps_mod.current()
            return {
                "meta": "status",
                "name": NAME,
                "uptime_s": time.monotonic() - _started_ts,
                "regime": c.regime,
                "ram_avail_gb": round(c.ram_available_bytes / 1e9, 2),
                "has_gpu": c.has_gpu,
                "scratch_dir": str(Path(os.environ.get("DH_SCRATCH_DIR", "~/.data-harness")).expanduser()),
            }
        if op == "shutdown":
            self.shutdown_event.set()
            return {"meta": "shutting-down"}
        if op == "caps":
            c = _caps_mod.current()
            try:
                return {"meta": "caps", "data": _caps_to_dict(c)}
            except Exception as e:
                return {"meta": "caps", "error": str(e)}
        return {"meta": "error", "error": f"unknown meta op: {op}"}

    # ─── server loop ─────────────────────────────────────────────────────

    def serve(self):
        try:
            os.unlink(SOCK)
        except FileNotFoundError:
            pass
        Path(PID).write_text(str(os.getpid()))
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(SOCK)
        srv.listen(8)
        srv.settimeout(0.5)
        _log(f"daemon up (pid={os.getpid()}, name={NAME})")
        while not self.shutdown_event.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()
        try:
            srv.close()
        finally:
            for path in (SOCK, PID):
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass
            try:
                _caps_mod.stop_adaptivity_loop()
            except Exception:
                pass
            _log("daemon down")

    def _handle_conn(self, conn):
        try:
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(1 << 16)
                if not chunk:
                    return
                data += chunk
            msg = json.loads(data.decode().strip())
            response = self.handle_meta(msg) if "meta" in msg else {"error": "unsupported"}
            conn.sendall((json.dumps(response) + "\n").encode())
        except Exception as e:
            try:
                conn.sendall((json.dumps({"error": str(e)}) + "\n").encode())
            except Exception:
                pass
        finally:
            conn.close()


def _caps_to_dict(c: "_caps_mod.Capabilities") -> dict:
    """Flatten a Capabilities object to a JSON-safe dict (best-effort)."""
    out = {}
    for f in c.__dataclass_fields__:
        v = getattr(c, f)
        if isinstance(v, (str, int, float, bool, type(None))):
            out[f] = v
        elif isinstance(v, (list, tuple)):
            out[f] = [_caps_to_dict(x) if hasattr(x, "__dataclass_fields__") else _safe(x) for x in v]
        elif hasattr(v, "__dataclass_fields__"):
            out[f] = _caps_to_dict(v)
        elif hasattr(v, "value"):
            out[f] = v.value
        elif isinstance(v, dict):
            out[f] = {k: _safe(x) for k, x in v.items()}
        else:
            out[f] = _safe(v)
    out["regime"] = c.regime
    out["has_gpu"] = c.has_gpu
    return out


def _safe(v):
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    return str(v)


def _signal_handler(signum, frame):
    _log(f"signal {signum} received")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    Daemon().serve()


if __name__ == "__main__":
    main()
