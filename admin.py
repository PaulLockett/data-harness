"""Daemon socket lifecycle + self-maintenance for data-harness.

DH_NAME namespaces /tmp/dh-<name>.{sock,pid,log}. ensure_daemon is idempotent
and self-heals stale sockets. The daemon is a long-running Python process
holding DuckDB + lazy models + Atomic[Capabilities].

Self-maintenance: run_doctor (diagnose), run_setup (first-run bootstrap),
run_update (git pull or PyPI upgrade), print_update_banner (daily-rate-limited
update nag, printed by run.py before ensure_daemon).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
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
GH_RELEASES = "https://api.github.com/repos/PaulLockett/data-harness/releases/latest"
VERSION_CACHE = Path("/tmp/dh-version-cache.json")
VERSION_CACHE_TTL = 24 * 3600


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
    """Installed version of the data-harness package. Empty string if unknown."""
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("data-harness")
        except PackageNotFoundError:
            return ""
    except Exception:
        return ""


def _repo_dir():
    """Return the repo root if this install is an editable git clone, else None."""
    p = Path(__file__).resolve().parent
    return p if (p / ".git").is_dir() else None


def _install_mode():
    """"git" for editable clone, "pypi" for an installed wheel, "unknown" otherwise."""
    if _repo_dir():
        return "git"
    return "pypi" if _version() else "unknown"


def _cache_read():
    try:
        return json.loads(VERSION_CACHE.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _cache_write(data):
    try:
        VERSION_CACHE.write_text(json.dumps(data))
    except OSError:
        pass


def _latest_release_tag(force=False):
    """Return latest release tag from GitHub, or None. Cached for 24h."""
    cache = _cache_read()
    now = time.time()
    if not force and cache.get("tag") and now - cache.get("fetched_at", 0) < VERSION_CACHE_TTL:
        return cache["tag"]
    try:
        req = urllib.request.Request(GH_RELEASES, headers={"Accept": "application/vnd.github+json"})
        tag = json.loads(urllib.request.urlopen(req, timeout=5).read()).get("tag_name") or ""
    except Exception:
        return cache.get("tag")  # fall back to last known
    tag = tag.lstrip("v")
    _cache_write({**cache, "tag": tag, "fetched_at": now})
    return tag or None


def _version_tuple(v):
    """Best-effort semver parse. Non-numeric components sort as 0, so pre-releases may not rank perfectly."""
    parts = []
    for s in (v or "").split("."):
        m = ""
        for ch in s:
            if ch.isdigit():
                m += ch
            else:
                break
        parts.append(int(m) if m else 0)
    return tuple(parts)


def check_for_update():
    """(current, latest, newer_available). latest may be None when GitHub is unreachable and the cache is empty."""
    cur = _version()
    latest = _latest_release_tag()
    newer = bool(cur and latest and _version_tuple(latest) > _version_tuple(cur))
    return cur, latest, newer


def print_update_banner(out=None):
    """Print the update banner to stderr once per day. Silent when up-to-date or offline."""
    out = out or sys.stderr
    cache = _cache_read()
    today = time.strftime("%Y-%m-%d")
    if cache.get("banner_shown_on") == today:
        return
    cur, latest, newer = check_for_update()
    if not newer:
        return
    print(f"[data-harness] update available: {cur} -> {latest}", file=out)
    print("[data-harness] agents: run `dh --update -y` to upgrade and restart the daemon", file=out)
    _cache_write({**cache, "banner_shown_on": today})


def _suggest_profile():
    """Read live capabilities and suggest a profile name from profiles/. Fallback laptop-cpu."""
    here = Path(__file__).resolve().parent
    try:
        import capabilities as _caps_mod
        c = _caps_mod.detect()
        regime = (getattr(c, "regime", "") or "").lower().replace("_", "-")
    except Exception:
        return "laptop-cpu"
    if regime == "hosted-only":
        regime = "hosted-api-only"
    if regime and (here / "profiles" / f"{regime}.toml").exists():
        return regime
    return "laptop-cpu"


def run_doctor():
    """Read-only diagnostics. Exit 0 iff python + capabilities/deadlines/profiles + daemon all healthy."""
    import platform

    here = Path(__file__).resolve().parent
    cur = _version()
    mode = _install_mode()
    cur_display = cur or "(unknown)"
    latest = _latest_release_tag()
    newer = bool(cur and latest and _version_tuple(latest) > _version_tuple(cur))

    py_ok = sys.version_info >= (3, 11)
    cap_ok = (here / "capabilities.py").exists()
    dl_ok = (here / "deadlines.py").exists()
    pyproj_ok = (here / "pyproject.toml").exists()
    profiles_ok = (here / "profiles" / "base.toml").exists()
    daemon = daemon_alive()
    env_path = here / ".env"

    def row(label, ok, detail=""):
        mark = "ok  " if ok else "FAIL"
        print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")

    print("data-harness doctor")
    print(f"  platform          {platform.system()} {platform.release()}")
    print(f"  python            {sys.version.split()[0]}")
    if cur:
        print(f"  version           {cur} ({mode})")
    elif mode == "unknown":
        print( "  version           (not installed — `uv tool install -e .` from the repo)")
    else:
        print(f"  version           (unknown) ({mode})")
    if latest:
        print(f"  latest release    {latest}" + (" (update available — run `dh --update -y`)" if newer else ""))
    else:
        print("  latest release    (could not reach github)")
    print(f"  daemon            {'alive' if daemon else 'not running (will auto-start on next `dh` call)'}")
    print(f"  .env              {'present at ' + str(env_path) if env_path.exists() else 'missing (optional — cp .env.example .env to enable hosted-API skills)'}")

    row("python >= 3.11", py_ok, "" if py_ok else "data-harness requires Python 3.11+")
    row("capabilities.py", cap_ok, "" if cap_ok else f"missing at {here / 'capabilities.py'}")
    row("deadlines.py", dl_ok, "" if dl_ok else f"missing at {here / 'deadlines.py'}")
    row("pyproject.toml", pyproj_ok, "" if pyproj_ok else f"missing at {here / 'pyproject.toml'}")
    row("profiles/base.toml", profiles_ok, "" if profiles_ok else "expected at profiles/base.toml")

    return 0 if (py_ok and cap_ok and dl_ok and pyproj_ok and profiles_ok) else 1


def run_setup():
    """First-run bootstrap. Runs doctor, surfaces .env / profile guidance, warms the daemon.

    Read-only — never writes .env. Exit 0 on success, non-zero on failure."""
    print("data-harness setup: bootstrapping...")

    rc = run_doctor()
    if rc != 0:
        print()
        print("doctor reported FAIL — fix the items above and rerun `dh --setup`.", file=sys.stderr)
        return rc

    here = Path(__file__).resolve().parent
    env_path = here / ".env"
    env_example = here / ".env.example"
    print()
    if env_path.exists():
        print(f"  .env             present at {env_path}")
    elif env_example.exists():
        print( "  .env             missing — to enable hosted-API skills, copy:")
        print(f"                       cp {env_example} {env_path}")
        print( "                       and fill in any provider keys you have.")
    else:
        print("  .env             missing (and no .env.example to copy from)")

    user_md = Path.home() / ".data-harness" / "USER.md"
    if user_md.exists():
        print(f"  USER.md          present at {user_md}")
    else:
        print( "  USER.md          missing — your next agent session will bootstrap one")
        print( "                       via meta-skills/interview/.")

    suggested = _suggest_profile()
    current_profile = os.environ.get("DH_PROFILE", "")
    if current_profile:
        print(f"  DH_PROFILE       set to {current_profile!r}")
    else:
        print(f"  DH_PROFILE       not set — recommended for this machine: {suggested!r}")
        print(f"                       export DH_PROFILE={suggested}")

    print()
    print("warming the daemon...")
    try:
        ensure_daemon(wait=30.0)
        print("daemon is up.")
    except RuntimeError as e:
        print(f"daemon failed to come up: {e}", file=sys.stderr)
        print("rerun `dh --doctor` for diagnostics.", file=sys.stderr)
        return 1

    print()
    print("ready. Try:")
    print("  dh caps                                  # confirm the detected hardware")
    print("  dh check-skill domain-skills/_template   # one fixture green")
    print("  make check-all-skills                    # every fixture green")
    return 0


def _prompt_yes(question, default_yes=True, yes=False):
    if yes:
        return True
    suffix = "[Y/n]" if default_yes else "[y/N]"
    try:
        ans = input(f"{question} {suffix} ").strip().lower()
    except EOFError:
        return default_yes
    if not ans:
        return default_yes
    return ans.startswith("y")


def run_update(yes=False):
    """Pull the latest version and (after prompt) restart the daemon so it picks up changed code.

    Exit 0 on success, non-zero on failure."""
    cur, latest, newer = check_for_update()
    if cur and latest and not newer:
        print(f"data-harness is up to date ({cur}).")
        return 0
    if cur and latest:
        print(f"updating data-harness: {cur} -> {latest}")
    elif latest:
        print(f"installed version unknown; will try to update to {latest}.")
    else:
        print("could not reach github; will try to update anyway.")

    mode = _install_mode()
    if mode == "git":
        repo = _repo_dir()
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
        if status.returncode != 0:
            print(f"git status failed: {status.stderr.strip()}", file=sys.stderr)
            return 1
        if status.stdout.strip():
            print(f"refusing to update: uncommitted changes in {repo}", file=sys.stderr)
            print(f"commit or stash them first, or run `git -C {repo} pull` yourself.", file=sys.stderr)
            return 1
        r = subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"])
        if r.returncode != 0:
            return r.returncode
        # Pick up new dependencies for an editable tool install.
        subprocess.run(["uv", "tool", "install", "-e", str(repo), "--force"], check=False)
    elif mode == "pypi":
        tool_upgrade = subprocess.run(["uv", "tool", "upgrade", "data-harness"])
        if tool_upgrade.returncode != 0:
            pip = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "data-harness"])
            if pip.returncode != 0:
                return pip.returncode
    else:
        print("unknown install mode; can't auto-update.", file=sys.stderr)
        return 1

    # Invalidate banner cache so the new version doesn't keep nagging.
    cache = _cache_read()
    cache.pop("banner_shown_on", None)
    _cache_write(cache)

    if daemon_alive():
        if _prompt_yes("restart the running daemon so it picks up the new code?", default_yes=True, yes=yes):
            restart_daemon()
            print("daemon stopped; it will auto-restart on next `dh` call.")
        else:
            print("daemon left running on old code. run `dh` and it'll use the new code after the daemon recycles.")
    print("update complete.")
    return 0
