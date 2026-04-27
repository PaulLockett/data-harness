# capabilities.py — typed-limits introspection + declared-profile merge + adaptivity
# ~360 lines. The code IS the doc.
#
# Discipline:
#   - Skills query computed flags (caps.has_gpu, caps.is_offline, caps.ram_available_bytes).
#   - Skills NEVER branch on caps.regime == "..." (linter rejects this).
#   - Skills NEVER import psutil / torch.cuda / nvidia-ml-py directly.
#   - Heavy imports (psutil, torch, pynvml) are lazy — keep cold-start fast.
#   - Declared-vs-observed: honor min(declared, observed). WARN if declared exceeds observed.

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Thread, Lock
from typing import Optional
import os
import platform
import shutil
import socket
import subprocess
import time
import warnings


# ─── Enums ────────────────────────────────────────────────────────────

class Backend(Enum):
    CPU = "cpu"; CUDA = "cuda"; MPS = "mps"; ROCM = "rocm"; XPU = "xpu"


class Precision(Enum):
    FP32 = "fp32"; FP16 = "fp16"; BF16 = "bf16"
    INT8 = "int8"; INT4 = "int4"; FP8 = "fp8"


class Mode(Enum):
    """gcc -O analog: declared optimization preference, orthogonal to introspection."""
    LATENCY = "latency"   # -O3: throughput, accept memory bloat
    BALANCED = "balanced" # -O2: portable default
    SIZE = "size"         # -Os: minimum memory, accept slowdown
    NATIVE = "native"     # -march=native: every available hardware feature
    PORTABLE = "portable" # works everywhere, no risk of OOM


class Tenancy(Enum):
    EXCLUSIVE = "exclusive"; SHARED = "shared"; BURSTABLE = "burstable"


# ─── Component dataclasses ────────────────────────────────────────────

@dataclass(frozen=True)
class GPUInfo:
    index: int
    name: str
    sm_major: int
    sm_minor: int
    total_vram_bytes: int
    free_vram_bytes: int
    other_processes_vram_bytes: int = 0

    @property
    def supports_fp16(self) -> bool: return (self.sm_major, self.sm_minor) >= (7, 0)
    @property
    def supports_int8(self) -> bool: return (self.sm_major, self.sm_minor) >= (7, 5)
    @property
    def supports_bf16(self) -> bool: return (self.sm_major, self.sm_minor) >= (8, 0)
    @property
    def supports_fp8(self) -> bool: return (self.sm_major, self.sm_minor) >= (8, 9)
    @property
    def supports_mxfp4(self) -> bool: return self.sm_major >= 10


@dataclass(frozen=True)
class MemoryWatermarks:
    """Dask-style 4-stage watermarks. Crossings drive adaptivity loop events."""
    target_bytes: int  # 60% — start spilling caches
    spill_bytes: int   # 70% — switch tabular ops to streaming
    pause_bytes: int   # 80% — refuse new skill kickoffs
    panic_bytes: int   # 95% — abort current op

    @classmethod
    def for_total(cls, total: int) -> "MemoryWatermarks":
        return cls(
            target_bytes=int(total * 0.60),
            spill_bytes=int(total * 0.70),
            pause_bytes=int(total * 0.80),
            panic_bytes=int(total * 0.95),
        )


@dataclass(frozen=True)
class StorageMount:
    path: str
    fstype: str  # 'ext4', 'overlay', 'tmpfs', 'apfs', 'nfs', ...
    free_bytes: int
    is_ephemeral: bool = False
    measured_write_MBps: Optional[float] = None


@dataclass(frozen=True)
class NetworkInfo:
    online: bool
    egress_allowed: bool
    measured_bandwidth_MBps: Optional[float] = None
    measured_latency_ms: Optional[float] = None


@dataclass(frozen=True)
class ProviderState:
    name: str
    api_key_present: bool
    requests_remaining: Optional[int] = None
    tokens_remaining: Optional[int] = None
    headroom_fraction: float = 1.0  # 1.0 fresh, 0.0 throttled
    last_429_at: Optional[float] = None
    pricebook_in_per_Mtok: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Capabilities:
    # ---------- compute ----------
    cpu_logical: int
    cpu_physical: int
    cpu_apple_p_cores: Optional[int]
    cpu_apple_e_cores: Optional[int]
    cpu_features: frozenset
    cpu_load_1m: float
    arch: str
    os: str
    # ---------- memory ----------
    ram_total_bytes: int
    ram_available_bytes: int
    cgroup_memory_max: Optional[int]
    swap_pressure: float
    watermarks: MemoryWatermarks
    # ---------- accelerators ----------
    gpus: tuple[GPUInfo, ...]
    mps_recommended_max_bytes: Optional[int]
    backends: frozenset
    precisions: frozenset
    # ---------- storage ----------
    cwd_mount: StorageMount
    cache_mount: StorageMount
    scratch_mount: StorageMount
    hf_cache_size_bytes: int
    # ---------- network & providers ----------
    network: NetworkInfo
    providers: tuple[ProviderState, ...]
    # ---------- environment ----------
    in_container: bool
    in_kubernetes: bool
    in_ci: bool
    on_battery: bool
    tenancy: Tenancy
    # ---------- declared policy ----------
    mode: Mode = Mode.BALANCED
    declared: dict = field(default_factory=dict)

    # ---------- computed flags (the only things skills branch on) ----------
    @property
    def has_gpu(self) -> bool:
        return any(g.free_vram_bytes > (1 << 30) for g in self.gpus)

    @property
    def best_gpu(self) -> Optional[GPUInfo]:
        return max(self.gpus, key=lambda g: g.free_vram_bytes, default=None)

    @property
    def can_quantize_int4(self) -> bool:
        return self.has_gpu or "avx2" in self.cpu_features

    @property
    def is_offline(self) -> bool:
        return not self.network.egress_allowed

    @property
    def is_throttled_thermally(self) -> bool:
        # Heuristic: detected by daemon via tokens/s EWMA; placeholder
        return False

    @property
    def is_shared(self) -> bool:
        return self.tenancy != Tenancy.EXCLUSIVE

    @property
    def regime(self) -> str:
        """Named tier — used by models.py resolve tables and CI matrix labels.
        SKILLS MUST NOT BRANCH ON THIS. Linter (tools/lint_skills.py) rejects
        `caps.regime ==` in skill code."""
        if self.is_offline and not self.has_gpu and self.ram_available_bytes < (8 << 30):
            return "TINY"
        if not self.has_gpu and self.ram_available_bytes < (32 << 30):
            return "LAPTOP-CPU"
        if self.has_gpu and self.best_gpu.free_vram_bytes < (16 << 30):
            return "LAPTOP-GPU"
        if self.has_gpu and self.best_gpu.free_vram_bytes < (40 << 30):
            return "WORKSTATION"
        if len(self.gpus) >= 8:
            return "SERVER-MULTI"
        if self.has_gpu:
            return "SERVER-1GPU"
        return "HOSTED-ONLY" if any(p.api_key_present for p in self.providers) else "TINY"


# ─── Detection ────────────────────────────────────────────────────────

def _detect_cpu():
    """Return (logical, physical, apple_p, apple_e, features, load_1m, arch, os)."""
    import psutil
    logical = min(
        os.cpu_count() or 1,
        len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1),
        psutil.cpu_count(logical=True) or 1,
    )
    physical = psutil.cpu_count(logical=False) or logical

    apple_p = apple_e = None
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            apple_p = int(subprocess.check_output(["sysctl", "-n", "hw.perflevel0.physicalcpu"]).strip())
            apple_e = int(subprocess.check_output(["sysctl", "-n", "hw.perflevel1.physicalcpu"]).strip())
        except Exception:
            pass

    feats = _detect_cpu_features()
    load_1m = (os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0) / max(1, logical)
    return logical, physical, apple_p, apple_e, frozenset(feats), load_1m, platform.machine(), platform.system()


def _detect_cpu_features() -> set[str]:
    """py-cpuinfo + Apple sysctl for FEAT_*."""
    feats: set[str] = set()
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        feats.update(info.get("flags", []))
    except Exception:
        pass
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        feats.add("neon")  # always on Apple Silicon
        for feat in ["FEAT_BF16", "FEAT_I8MM", "FEAT_DotProd", "FEAT_FP16"]:
            try:
                v = subprocess.check_output(
                    ["sysctl", "-n", f"hw.optional.arm.{feat}"],
                    stderr=subprocess.DEVNULL,
                ).strip()
                if v == b"1":
                    feats.add(feat.lower())
            except Exception:
                pass
    return feats


def _detect_cgroup_memory() -> Optional[int]:
    """Read cgroup memory.max; returns None if not in a cgroup. CRITICAL inside containers."""
    p = Path("/sys/fs/cgroup/memory.max")  # cgroup v2
    if p.exists():
        v = p.read_text().strip()
        if v != "max":
            return int(v)
    p = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")  # cgroup v1
    if p.exists():
        try:
            v = int(p.read_text().strip())
            if v < (1 << 62):
                return v
        except Exception:
            pass
    return None


def _detect_memory():
    """Return (total, available, cgroup_max, swap_pressure)."""
    import psutil
    vm = psutil.virtual_memory()
    cg = _detect_cgroup_memory()
    total = min(vm.total, cg) if cg else vm.total
    available = min(vm.available, cg) if cg else vm.available
    swap_pressure = 0.0  # daemon maintains rolling sin/sout EWMA; placeholder
    return total, available, cg, swap_pressure


def _detect_gpus() -> tuple[GPUInfo, ...]:
    """Enumerate CUDA devices via torch + add reserved-but-not-allocated as recoverable."""
    try:
        import torch
        if not torch.cuda.is_available():
            return ()
    except Exception:
        return ()
    gpus = []
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        free, total = torch.cuda.mem_get_info(i)
        try:
            recoverable = torch.cuda.memory_reserved(i) - torch.cuda.memory_allocated(i)
            free += recoverable
        except Exception:
            pass
        other = _nvml_other_processes_vram(i)
        gpus.append(GPUInfo(
            index=i, name=props.name,
            sm_major=props.major, sm_minor=props.minor,
            total_vram_bytes=total, free_vram_bytes=free,
            other_processes_vram_bytes=other,
        ))
    return tuple(gpus)


def _nvml_other_processes_vram(device: int) -> int:
    """VRAM consumed by other processes on this GPU (signal of contention)."""
    try:
        import pynvml  # nvidia-ml-py exposes the pynvml module
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(device)
        my_pid = os.getpid()
        return sum(
            (p.usedGpuMemory or 0)
            for p in pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            if p.pid != my_pid
        )
    except Exception:
        return 0


def _detect_mps_max() -> Optional[int]:
    """Apple MPS recommended max memory."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return torch.mps.recommended_max_memory()
    except Exception:
        pass
    return None


def _detect_storage() -> tuple[StorageMount, StorageMount, StorageMount]:
    """Detect cwd, HF cache, and scratch mounts. Three separate calls — they may live on different volumes in containers."""
    import psutil
    cwd_path = os.getcwd()
    hf_path = os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
    scratch_path = os.environ.get("DH_SCRATCH_DIR", str(Path.home() / ".data-harness"))
    Path(scratch_path).expanduser().mkdir(parents=True, exist_ok=True)
    Path(hf_path).expanduser().mkdir(parents=True, exist_ok=True)

    parts = {p.mountpoint: p for p in psutil.disk_partitions(all=True)}

    def mount_for(path: str) -> StorageMount:
        path = str(Path(path).expanduser())
        u = shutil.disk_usage(path)
        match = max((mp for mp in parts if path.startswith(mp)), key=len, default="/")
        fstype = parts[match].fstype if match in parts else "unknown"
        return StorageMount(
            path=path, fstype=fstype, free_bytes=u.free,
            is_ephemeral=fstype in ("overlay", "tmpfs"),
        )

    return mount_for(cwd_path), mount_for(hf_path), mount_for(scratch_path)


def _detect_hf_cache_size() -> int:
    try:
        from huggingface_hub import scan_cache_dir
        return scan_cache_dir().size_on_disk
    except Exception:
        return 0


def _detect_network() -> NetworkInfo:
    """TCP probe to 1.1.1.1:443. Bandwidth/latency measured separately and cached."""
    try:
        s = socket.create_connection(("1.1.1.1", 443), timeout=2)
        s.close()
        online = True
    except Exception:
        online = False
    egress_allowed = online  # refined by user policy / declared profile
    return NetworkInfo(online=online, egress_allowed=egress_allowed)


def _detect_providers() -> tuple[ProviderState, ...]:
    """Snapshot provider state from env vars. Rate-limit headroom updated event-driven by daemon."""
    out = []
    for name, env in [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("google", "GOOGLE_API_KEY"),
        ("voyage", "VOYAGE_API_KEY"),
        ("cohere", "COHERE_API_KEY"),
    ]:
        out.append(ProviderState(name=name, api_key_present=bool(os.environ.get(env))))
    return tuple(out)


def _detect_environment():
    """Return (in_container, in_kubernetes, in_ci, on_battery, tenancy)."""
    import psutil
    in_container = Path("/.dockerenv").exists() or _detect_cgroup_memory() is not None
    in_k8s = "KUBERNETES_SERVICE_HOST" in os.environ
    in_ci = any(os.environ.get(k) for k in
                ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "JENKINS_URL", "BUILDKITE"])

    bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    on_battery = bat is not None and not bat.power_plugged

    if in_k8s or (in_container and _detect_cgroup_memory() is not None):
        tenancy = Tenancy.SHARED
    else:
        tenancy = Tenancy.EXCLUSIVE

    return in_container, in_k8s, in_ci, on_battery, tenancy


# ─── Profile loading ──────────────────────────────────────────────────

PROFILE_DIR = Path(__file__).parent / "profiles"


def load_profile(name: str) -> dict:
    """Load a TOML profile, resolving the `extends` chain (cap depth 3)."""
    try:
        import tomllib  # py3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore

    visited: set[str] = set()

    def _load(n: str, depth: int) -> dict:
        if depth > 3:
            raise ValueError(f"Profile inheritance depth >3 starting at {name}")
        if n in visited:
            raise ValueError(f"Profile inheritance cycle through {n}")
        visited.add(n)
        path = PROFILE_DIR / f"{n}.toml"
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")
        data = tomllib.loads(path.read_text())
        parent = data.pop("extends", None)
        if parent:
            base = _load(parent, depth + 1)
            data = _deep_merge(base, data)
        return data

    return _load(name, 0)


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursive dict merge; overlay wins."""
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _parse_bytes(s) -> int:
    """Parse '12 GiB' / '500 MB' / int → bytes."""
    if isinstance(s, int):
        return s
    s = str(s).strip()
    units = {"B": 1, "KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12,
             "KiB": 1 << 10, "MiB": 1 << 20, "GiB": 1 << 30, "TiB": 1 << 40}
    for u, m in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if s.endswith(u):
            return int(float(s[:-len(u)].strip()) * m)
    return int(s)


# ─── Detect + merge ───────────────────────────────────────────────────

def detect(declared_profile: Optional[str] = None) -> Capabilities:
    """Build a fresh Capabilities snapshot from introspection + declared profile.

    Discipline: honor min(declared, observed) for any limit. WARN if declared > observed.
    """
    profile_name = declared_profile or os.environ.get("DH_PROFILE", "base")
    declared = load_profile(profile_name)

    cpu_log, cpu_phys, p_cores, e_cores, feats, load_1m, arch, os_name = _detect_cpu()
    ram_total, ram_avail, cg_mem, swap_p = _detect_memory()

    # Apply min(declared, observed) for memory budget
    if "memory" in declared and "budget_bytes" in declared["memory"]:
        decl_ram = _parse_bytes(declared["memory"]["budget_bytes"])
        if decl_ram > ram_avail:
            warnings.warn(
                f"declared RAM budget {decl_ram} exceeds observed available {ram_avail}; "
                f"honoring observed.",
                stacklevel=2,
            )
        ram_avail = min(ram_avail, decl_ram)

    gpus = _detect_gpus()
    mps_max = _detect_mps_max()

    # Apply min(declared, observed) for VRAM budget
    if gpus and "gpu" in declared and "budget_bytes" in declared["gpu"]:
        decl_vram = _parse_bytes(declared["gpu"]["budget_bytes"])
        if decl_vram > gpus[0].free_vram_bytes:
            warnings.warn(
                f"declared VRAM budget {decl_vram} exceeds observed {gpus[0].free_vram_bytes}; "
                f"honoring observed.",
                stacklevel=2,
            )
        # rebuild GPU 0 with capped free
        g0 = gpus[0]
        gpus = (
            GPUInfo(
                index=g0.index, name=g0.name,
                sm_major=g0.sm_major, sm_minor=g0.sm_minor,
                total_vram_bytes=g0.total_vram_bytes,
                free_vram_bytes=min(g0.free_vram_bytes, decl_vram),
                other_processes_vram_bytes=g0.other_processes_vram_bytes,
            ),
            *gpus[1:],
        )

    cwd_m, cache_m, scratch_m = _detect_storage()
    network = _detect_network()
    providers = _detect_providers()
    in_cont, in_k8s, in_ci, on_bat, tenancy = _detect_environment()
    hf_size = _detect_hf_cache_size()

    # Network egress can be narrowed by profile but never widened
    if "network" in declared and declared["network"].get("allow_egress") is False:
        network = NetworkInfo(
            online=network.online, egress_allowed=False,
            measured_bandwidth_MBps=network.measured_bandwidth_MBps,
            measured_latency_ms=network.measured_latency_ms,
        )

    # Backend & precision support
    backends = {Backend.CPU}
    precisions = {Precision.FP32}
    if gpus:
        backends.add(Backend.CUDA)
        for g in gpus:
            if g.supports_fp16: precisions.add(Precision.FP16)
            if g.supports_bf16: precisions.add(Precision.BF16)
            if g.supports_int8: precisions.add(Precision.INT8)
            if g.supports_fp8:  precisions.add(Precision.FP8)
        precisions.add(Precision.INT4)  # quantized models always available
    if mps_max:
        backends.add(Backend.MPS)
        precisions.add(Precision.FP16)

    mode_str = declared.get("mode", {}).get("default", os.environ.get("DH_MODE", "balanced"))
    mode = Mode(mode_str)

    return Capabilities(
        cpu_logical=cpu_log, cpu_physical=cpu_phys,
        cpu_apple_p_cores=p_cores, cpu_apple_e_cores=e_cores,
        cpu_features=feats, cpu_load_1m=load_1m,
        arch=arch, os=os_name,
        ram_total_bytes=ram_total, ram_available_bytes=ram_avail,
        cgroup_memory_max=cg_mem, swap_pressure=swap_p,
        watermarks=MemoryWatermarks.for_total(ram_avail),
        gpus=gpus, mps_recommended_max_bytes=mps_max,
        backends=frozenset(backends), precisions=frozenset(precisions),
        cwd_mount=cwd_m, cache_mount=cache_m, scratch_mount=scratch_m,
        hf_cache_size_bytes=hf_size,
        network=network, providers=providers,
        in_container=in_cont, in_kubernetes=in_k8s, in_ci=in_ci,
        on_battery=on_bat, tenancy=tenancy,
        mode=mode, declared=declared,
    )


# ─── Atomic ref + adaptivity loop ────────────────────────────────────

_caps_ref: Optional[Capabilities] = None
_caps_lock = Lock()
_adaptivity_thread: Optional[Thread] = None
_adaptivity_stop: bool = False
_min_dwell_seconds: float = 30.0  # hysteresis: don't downgrade more than once per 30s


def current() -> Capabilities:
    """Snapshot the daemon's current Capabilities. Cheap; safe to call per primitive."""
    if _caps_ref is None:
        return detect()
    return _caps_ref


def _set_current(c: Capabilities) -> None:
    """Atomic immutable replacement (frozen dataclass)."""
    global _caps_ref
    with _caps_lock:
        _caps_ref = c


def start_adaptivity_loop(cadence_seconds: float = 3.0) -> None:
    """Start the background poller. Idempotent."""
    global _adaptivity_thread, _adaptivity_stop
    if _adaptivity_thread and _adaptivity_thread.is_alive():
        return
    _adaptivity_stop = False
    _set_current(detect())
    last_replace_at = [time.monotonic()]

    def _loop():
        while not _adaptivity_stop:
            try:
                fresh = detect(os.environ.get("DH_PROFILE"))
                if _meaningful_change(_caps_ref, fresh, last_replace_at[0]):
                    _set_current(fresh)
                    last_replace_at[0] = time.monotonic()
            except Exception:
                pass  # never let adaptivity loop crash the daemon
            time.sleep(cadence_seconds)

    _adaptivity_thread = Thread(target=_loop, daemon=True, name="dh-adaptivity")
    _adaptivity_thread.start()


def stop_adaptivity_loop() -> None:
    global _adaptivity_stop
    _adaptivity_stop = True


def _meaningful_change(old: Optional[Capabilities], new: Capabilities,
                       last_replace_at: float) -> bool:
    """Return True if a field changed enough to warrant atomic replacement.

    Hysteresis: most changes require >= _min_dwell_seconds since last replacement.
    Hard signals (battery flip, network down, watermark crossing) bypass dwell.
    """
    if old is None:
        return True

    # Hard signals — always react
    if old.on_battery != new.on_battery:
        return True
    if old.network.online != new.network.online:
        return True
    # RAM watermark crossings (panic / pause)
    if (old.ram_available_bytes > old.watermarks.panic_bytes) != \
       (new.ram_available_bytes > new.watermarks.panic_bytes):
        return True
    if (old.ram_available_bytes > old.watermarks.pause_bytes) != \
       (new.ram_available_bytes > new.watermarks.pause_bytes):
        return True

    # Soft signals — apply dwell time
    if time.monotonic() - last_replace_at < _min_dwell_seconds:
        return False

    # Provider headroom big swing
    for o, n in zip(old.providers, new.providers):
        if abs(o.headroom_fraction - n.headroom_fraction) > 0.2:
            return True
    # GPU contention shifted by >2GB
    for og, ng in zip(old.gpus, new.gpus):
        if abs(og.other_processes_vram_bytes - ng.other_processes_vram_bytes) > (2 << 30):
            return True

    return False


# ─── dry_run_resolve ─────────────────────────────────────────────────

def dry_run_resolve(plan_path: str | Path) -> list[dict]:
    """Pre-flight: show which models/backends would resolve for each primitive in a plan,
    without consuming compute or downloading weights.

    plan_path: a skill folder (parses its SKILL.md for declared primitive calls)
               or a YAML/JSON listing primitive calls explicitly.

    Returns: [{primitive, primary, chosen, fits, reason}] per call.
    """
    raise NotImplementedError(
        "Wire to models.resolve(... dry_run=True) once models.py exists. "
        "The dry_run path must skip download decisions and model loading; only "
        "consult the resolve table + capability fits."
    )


# ─── End capabilities.py ─────────────────────────────────────────────
