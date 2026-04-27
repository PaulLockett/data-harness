"""dh — data-harness CLI. Reads Python from stdin, exec's it with helpers preloaded.

Self-maintenance: --doctor, --setup, --update [-y].
Subcommands: check-skill, caps, models — dispatch to their own modules.
"""
import sys

from admin import (
    _version,
    ensure_daemon,
    print_update_banner,
    run_doctor,
    run_setup,
    run_update,
)
from helpers import *  # noqa: F401,F403 — exec namespace; pre-import substrate

HELP = """data-harness (dh)

Read SKILL.md for the default workflow. Helpers are pre-imported; daemon auto-starts.

Typical usage:
  dh <<'PY'
  print(glance(load("/etc/hostname")))
  PY

Self-maintenance:
  dh --version                   print the installed version
  dh --doctor                    diagnose install + capabilities + daemon
  dh --setup                     interactive first-run bootstrap
  dh --update [-y]               pull the latest version (agents: pass -y)

Subcommands:
  dh check-skill <path>          run skill against its fixtures (predicate-first)
  dh caps [--dry-run-resolve P]  print Capabilities snapshot; pre-flight a skill plan
  dh models <action>             pull | list | clear | which
"""


def main():
    args = sys.argv[1:]
    if not args:
        if sys.stdin.isatty():
            sys.exit("dh reads Python from stdin. Use:\n  dh <<'PY'\n  print(caps())\n  PY")
        print_update_banner()
        ensure_daemon()
        exec(sys.stdin.read(), globals())
        return
    cmd = args[0]
    if cmd in {"-h", "--help"}:
        print(HELP); return
    if cmd == "--version":
        print(_version() or "unknown"); return
    if cmd == "--doctor":
        sys.exit(run_doctor())
    if cmd == "--setup":
        sys.exit(run_setup())
    if cmd == "--update":
        yes = any(a in {"-y", "--yes"} for a in args[1:])
        sys.exit(run_update(yes=yes))
    if cmd == "check-skill":
        from check_skill import main as ck_main
        sys.exit(ck_main(args[1:]))
    if cmd == "caps":
        from capabilities_cli import main as caps_main
        sys.exit(caps_main(args[1:]))
    if cmd == "models":
        from models_cli import main as models_main
        sys.exit(models_main(args[1:]))
    sys.exit(f"unknown command: {cmd}\n\n{HELP}")


if __name__ == "__main__":
    main()
