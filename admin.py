"""Daemon socket lifecycle for data-harness.

DH_NAME namespaces /tmp/dh-<name>.{sock,pid,log}. ensure_daemon is idempotent
and self-heals stale sockets. The daemon is a long-running Python process
holding DuckDB + lazy models + Atomic[Capabilities].
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def _load_env():
    p = Path(__file__).parent / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

NAME = os.environ.get("DH_NAME", "default")


def _paths(name):
    n = name or NAME
    return f"/tmp/dh-{n}.sock", f"/tmp/dh-{n}.pid", f"/tmp/dh-{n}.log"


def _log_tail(name=None, n=20):
    _, _, log = _paths(name)
    try:
        return "\n".join(Path(log).read_text().strip().splitlines()[-n:])
    except (FileNotFoundError, IndexError):
        return ""


def daemon_alive(name=None):
    sock, _, _ = _paths(name)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(sock)
        s.close()
        return True
    except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError):
        return False


def daemon_status(name=None):
    """Return a dict with liveness + (if alive) a few daemon stats."""
    if not daemon_alive(name):
        return {"alive": False, "name": name or NAME}
    try:
        sock, _, _ = _paths(name)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(sock)
        s.sendall(b'{"meta": "status"}\n')
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(1 << 16)
            if not chunk:
                break
            data += chunk
        s.close()
        return {"alive": True, **json.loads(data.decode().strip())}
    except Exception as e:
        return {"alive": True, "stats_error": str(e)}


def ensure_daemon(wait=30.0, name=None):
    """Idempotent. Self-heals stale sockets. Spawns daemon.py via uv run."""
    if daemon_alive(name):
        # Probe with a real meta call; if it doesn't respond cleanly, restart.
        try:
            sock, _, _ = _paths(name)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(sock)
            s.sendall(b'{"meta": "ping"}\n')
            data = b""
            while not data.endswith(b"\n"):
                chunk = s.recv(1 << 16)
                if not chunk:
                    break
                data += chunk
            s.close()
            if b'"pong"' in data or b'"ok"' in data:
                return
        except Exception:
            pass
        restart_daemon(name)

    e = {**os.environ}
    if name:
        e["DH_NAME"] = name
    here = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.Popen(
        ["uv", "run", "--no-sync", "daemon.py"],
        cwd=here,
        env=e,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + wait
    while time.time() < deadline:
        if daemon_alive(name):
            return
        if p.poll() is not None:
            tail = _log_tail(name) or "(no log)"
            raise RuntimeError(f"daemon failed to start; log tail:\n{tail}")
        time.sleep(0.1)
    raise RuntimeError(
        f"daemon {name or NAME} didn't come up in {wait}s; log tail:\n{_log_tail(name)}"
    )


def restart_daemon(name=None):
    """Best-effort shutdown + socket/pid cleanup."""
    sock, pid_path, _ = _paths(name)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(sock)
        s.sendall(b'{"meta": "shutdown"}\n')
        s.close()
    except Exception:
        pass
    # SIGTERM if still alive
    try:
        pid = int(Path(pid_path).read_text().strip())
        os.kill(pid, 15)  # SIGTERM
        for _ in range(20):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                break
        else:
            os.kill(pid, 9)  # SIGKILL
    except (FileNotFoundError, ProcessLookupError, ValueError):
        pass
    for path in (sock, pid_path):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def stop_daemon(name=None):
    """Alias for restart_daemon — semantic clarity at call sites."""
    restart_daemon(name)


def _version():
    try:
        from importlib.metadata import version
        return version("data-harness")
    except Exception:
        return None


def run_doctor():
    """Diagnose install state. Exit 0 iff Python + capabilities + daemon all green."""
    print("data-harness doctor")
    py_ok = sys.version_info >= (3, 11)
    print(f"  python              {'.'.join(map(str, sys.version_info[:3]))} {'[ok]' if py_ok else '[FAIL]'}")
    here = Path(__file__).parent
    cap_ok = (here / "capabilities.py").exists()
    dl_ok = (here / "deadlines.py").exists()
    pyproj_ok = (here / "pyproject.toml").exists()
    profiles_ok = (here / "profiles" / "base.toml").exists()
    print(f"  capabilities.py     {'[ok]' if cap_ok else '[FAIL]'}")
    print(f"  deadlines.py        {'[ok]' if dl_ok else '[FAIL]'}")
    print(f"  pyproject.toml      {'[ok]' if pyproj_ok else '[FAIL]'}")
    print(f"  profiles/base.toml  {'[ok]' if profiles_ok else '[FAIL]'}")
    daemon = daemon_alive()
    print(f"  daemon              {'[ok]' if daemon else '[not running] (will auto-start on next call)'}")
    return 0 if (py_ok and cap_ok and dl_ok and pyproj_ok and profiles_ok) else 1
