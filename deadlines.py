# deadlines.py — absolute-monotonic deadline + budget propagation
# ~130 lines. The code IS the doc.
# Discipline: always pass absolute time.monotonic(); never raw durations.
#             Children descend by min(parent, now + child_seconds).
#             Per-primitive cancellation by kind. Default graceful degrade.

from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Optional
import subprocess
import time

# ─── Exceptions ──────────────────────────────────────────────────────

class BudgetExceeded(Exception):
    """Raised when a Deadline expires or a Budget cap is hit."""


# ─── Deadline and Budget types ───────────────────────────────────────

@dataclass(frozen=True)
class Deadline:
    """Absolute monotonic deadline. Use descend() to pass to children."""
    t: float  # absolute time.monotonic()

    @classmethod
    def in_seconds(cls, secs: float) -> "Deadline":
        """Construct from a duration (only at API entry)."""
        return cls(time.monotonic() + secs)

    @classmethod
    def never(cls) -> "Deadline":
        """Sentinel for 'no deadline'."""
        return cls(float("inf"))

    def remaining(self) -> float:
        """Seconds until expiry (0 if past)."""
        return max(0.0, self.t - time.monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0

    def check(self) -> None:
        """Raise BudgetExceeded if expired."""
        if self.expired():
            raise BudgetExceeded("deadline reached")

    def descend(self, child_seconds: float) -> "Deadline":
        """Child = min(self, now + child_seconds). Never extends parent."""
        return Deadline(min(self.t, time.monotonic() + child_seconds))


@dataclass
class Budget:
    """Deadline + optional dollar cap + running spend tally."""
    deadline: Deadline
    max_dollars: Optional[float] = None
    spent_dollars: float = 0.0

    def remaining_seconds(self) -> float:
        return self.deadline.remaining()

    def remaining_dollars(self) -> float:
        if self.max_dollars is None:
            return float("inf")
        return max(0.0, self.max_dollars - self.spent_dollars)

    def spend(self, dollars: float) -> None:
        """Record spend. Raises BudgetExceeded if cap hit."""
        self.spent_dollars += dollars
        if self.max_dollars is not None and self.spent_dollars > self.max_dollars:
            raise BudgetExceeded(f"dollar cap {self.max_dollars} exceeded ({self.spent_dollars})")

    def descend(self, child_seconds: float, child_dollars: Optional[float] = None) -> "Budget":
        """Child Budget; deadline + dollars both descend by min."""
        child_dl = self.deadline.descend(child_seconds)
        if self.max_dollars is None and child_dollars is None:
            return Budget(deadline=child_dl, max_dollars=None, spent_dollars=self.spent_dollars)
        cap = min(self.remaining_dollars(), child_dollars or float("inf"))
        return Budget(deadline=child_dl, max_dollars=cap, spent_dollars=0.0)


# ─── Deadline stack (thread-safe via contextvars) ────────────────────

_deadline_stack: ContextVar[tuple] = ContextVar("dh_deadline_stack", default=())


def current_deadline() -> Deadline:
    """Topmost active deadline, or never()."""
    stack = _deadline_stack.get()
    return stack[-1] if stack else Deadline.never()


@contextmanager
def push_deadline(dl: Deadline) -> Iterator[Deadline]:
    """Push a deadline; pop on exit."""
    stack = _deadline_stack.get() + (dl,)
    token = _deadline_stack.set(stack)
    try:
        yield dl
    finally:
        _deadline_stack.reset(token)


# ─── Cancellation by primitive kind ──────────────────────────────────

@contextmanager
def deadline_scope(dl: Deadline, *, kind: str = "cooperative",
                   grace: Optional[float] = None) -> Iterator[Deadline]:
    """Scope enforcing dl for a primitive of the given kind.

    kinds:
      atomic_short — no enforcement; trusted (<100ms)
      cooperative  — primitive checks dl.check() at iteration boundaries
      cpu_heavy    — runner kills via multiprocessing.Pool.terminate()
      subprocess   — runner terminates Popen on overrun
      io           — use anyio.fail_after() in async code (this scope is sync)

    Default is graceful degrade: finish current step, switch policy for next.
    """
    if grace is None:
        grace = min(2.0, 0.1 * dl.remaining())

    if kind == "io":
        raise NotImplementedError(
            "Use `async with anyio.fail_after(dl.remaining()):` for io kind; "
            "deadline_scope is for sync primitives."
        )
    if kind not in {"atomic_short", "cooperative", "cpu_heavy", "subprocess"}:
        raise ValueError(f"unknown deadline_scope kind: {kind}")

    # All sync kinds: push deadline; primitives check or runner enforces.
    # Termination semantics for cpu_heavy/subprocess live in helpers.bulk()
    # and the subprocess primitive respectively (see cancel_subprocess below).
    with push_deadline(dl):
        yield dl


@contextmanager
def cancel_subprocess(proc: subprocess.Popen, *, dl: Deadline,
                      grace: float = 2.0) -> Iterator[None]:
    """Terminate proc on dl expiry; SIGKILL after grace."""
    try:
        yield
    finally:
        if proc.poll() is None:
            if dl.expired():
                proc.terminate()
                try:
                    proc.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


# ─── Russell-Zilberstein iterative-doubling shim ─────────────────────

def iterative_doubling(contract_fn, *, dl: Deadline,
                       initial_seconds: float = 1.0):
    """Convert a contract algorithm to interruptible via iterative doubling.

    Calls contract_fn(t) with t = initial_seconds, 2t, 4t, ... until the next
    doubling would exceed dl. Returns the last completed result (best-so-far).
    Worst-case 4x overhead vs native interruptible.

    contract_fn must accept a time budget in seconds and either return a
    result or raise BudgetExceeded if it can't finish within t.
    """
    t = initial_seconds
    last_result = None
    while True:
        if t > dl.remaining():
            return last_result
        try:
            last_result = contract_fn(t)
            t *= 2
        except BudgetExceeded:
            return last_result


# ─── End deadlines.py ────────────────────────────────────────────────
