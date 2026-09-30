# Natural Language Toolkit: timing for the security and complexity tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Measure the work a test does, not the load on the machine running it.

Every DoS guard in the suite is pinned by a timing assertion: a hostile input
must finish inside a budget, or a sink must scale linearly over a 4x input.
Those assertions used to read the wall clock. A CI runner shared with other
jobs, or the test run itself under xdist, deschedules the interpreter for
stretches that are long against a run of a few hundred milliseconds, and the
wall clock then reports the runner's load rather than the code's cost: a 16x
quadratic read 7.8x on a macOS runner, a 1.2x readline read 2.5x on Windows,
and budgets of a few seconds failed on a laptop running six suites at once.

The rule here, used by every budget and scaling assertion in the suite:

* a block that is **CPU-bound** (the interpreter worked for at least
  ``CPU_BOUND_SHARE`` of its wall time) is charged its **process CPU time**,
  which a descheduled interpreter does not accumulate;
* a block that **mostly waits** (sleep, blocking I/O, a socket, a child process
  doing the work) is charged its **wall time**, since CPU time cannot see it.

The thresholds are the tests' own and are not touched: only the quantity
compared against them changes, from the runner's clock to the code's work.
Where two clocks disagree, the charge can only rise for a waiting block
(``charged`` picks the wall clock) and only fall for a CPU-bound one by the
time it was not running, so a broken guard that spins reads its full cost and
a broken guard that hangs reads its full wait.

Runs must be long enough for the CPU clock to resolve: Windows reports process
CPU time in 15.6 ms steps, so a measured run should take a few tenths of a
second, and the scaling helpers keep a multiplicative noise floor for that.
"""

import time

#: A block whose CPU time is at least this share of its wall time is judged on
#: CPU time; below it the block was mostly waiting and the wall clock applies.
CPU_BOUND_SHARE = 0.5

#: A scaling factor at or above this reads as super-linear (quadratic ~16x);
#: a linear sink stays near 4x, so the gap is wide on any machine.
QUADRATIC_RATIO = 8.0


def cpu_and_wall(func, *args, **kwargs):
    """``(cpu_seconds, wall_seconds)`` this process spent in ``func``."""
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    func(*args, **kwargs)
    return time.process_time() - cpu_start, time.perf_counter() - wall_start


def charge(cpu_seconds, wall_seconds):
    """The seconds charged to a block: CPU when CPU-bound, wall otherwise."""
    if cpu_seconds >= CPU_BOUND_SHARE * wall_seconds:
        return cpu_seconds
    return wall_seconds


def charged(func, *args, **kwargs):
    """Seconds charged to one call of ``func``."""
    return charge(*cpu_and_wall(func, *args, **kwargs))


class budget:
    """``with budget(seconds):`` fails if the block's charged time exceeds it.

    The check runs only when the block completed (an exception the block
    raised propagates unchanged). ``cpu``, ``wall`` and ``charged`` hold the
    measurement afterwards, for messages.
    """

    def __init__(self, seconds, what="the block"):
        self.seconds, self.what = seconds, what
        self.cpu = self.wall = self.charged = None

    def __enter__(self):
        self._cpu, self._wall = time.process_time(), time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cpu = time.process_time() - self._cpu
        self.wall = time.perf_counter() - self._wall
        self.charged = charge(self.cpu, self.wall)
        if exc_type is None:
            assert self.charged < self.seconds, (
                f"{self.what} took {self.charged:.2f}s charged "
                f"({self.cpu:.2f}s CPU, {self.wall:.2f}s wall), "
                f"budget {self.seconds}s"
            )
        return False


def within_budget(func, seconds, repeats=3):
    """``(ok, seconds)``: the fastest of ``repeats`` charged runs, ok if under.

    Min-of-k because one run on a loaded runner is noise; contention only adds
    time, so the minimum is closest to the code's own cost.
    """
    best = min(charged(func) for _ in range(repeats))
    return best < seconds, best


def scaling_ratio(op, small, big, reps=3, noise_floor=0.1):
    """Fastest-of-``reps`` ``op(big)`` over ``op(small)`` (``big`` == 4*``small``).

    A load-invariant scaling factor: a linear sink is ~4x, a pre-patch O(n**2)
    sink ~16x. The floor is multiplicative so a sub-second quadratic is not
    hidden by additive slack. The small and big runs alternate so a burst of
    load cannot land on one side only, the cheap small side gets ``reps``
    extra runs, and each side keeps its minimum on both clocks. A CPU-bound op
    is judged in CPU time; an op that mostly waits is judged on the wall clock
    and the higher of the two ratios is kept, so the fallback only tightens.
    """
    inf = float("inf")
    cpu, wall = {small: inf, big: inf}, {small: inf, big: inf}

    def run(n):
        cpu_seconds, wall_seconds = cpu_and_wall(op, n)
        cpu[n] = min(cpu[n], cpu_seconds)
        wall[n] = min(wall[n], wall_seconds)

    for _ in range(reps):
        run(small)
        run(big)
    for _ in range(reps):
        run(small)
    cpu_ratio = cpu[big] / max(cpu[small], noise_floor)
    if cpu[big] < CPU_BOUND_SHARE * wall[big]:
        return max(cpu_ratio, wall[big] / max(wall[small], noise_floor))
    return cpu_ratio


def assert_subquadratic(
    op, small, big, factor=QUADRATIC_RATIO, noise_floor=0.1, reps=3
):
    """Assert ``op(big)`` (big == 4*small) costs under ``factor`` times ``op(small)``."""
    ratio = scaling_ratio(op, small, big, reps=reps, noise_floor=noise_floor)
    assert ratio < factor, (small, big, ratio)
