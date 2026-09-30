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

import threading
import time

#: A block whose CPU time is at least this share of its wall time is judged on
#: CPU time; below it the block was mostly waiting and the wall clock applies.
#: Under xdist a 3-core runner stretched 0.20 s of CPU to 0.55 s of wall, under
#: this share, so a call site that knows its sink computes declares it with
#: ``cpu_bound=True`` and skips the heuristic; the share itself stays at a half
#: so no undeclared block is judged more leniently than before.
CPU_BOUND_SHARE = 0.5

#: A scaling factor at or above this reads as super-linear (quadratic ~16x);
#: a linear sink stays near 4x, so the gap is wide on any machine.
QUADRATIC_RATIO = 8.0


def cpu_and_wall(func, *args, **kwargs):
    """``(cpu_seconds, wall_seconds)`` this process spent in ``func``."""
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    func(*args, **kwargs)
    return time.process_time() - cpu_start, time.perf_counter() - wall_start


def charge(cpu_seconds, wall_seconds, cpu_bound=None):
    """The seconds charged to a block: CPU when CPU-bound, wall otherwise.

    ``cpu_bound`` declares it (True: the sink computes, so its CPU time is its
    cost; False: it waits, so the wall clock is); ``None`` decides by the share
    of wall time the block spent on the CPU.
    """
    if cpu_bound is None:
        cpu_bound = cpu_seconds >= CPU_BOUND_SHARE * wall_seconds
    return cpu_seconds if cpu_bound else wall_seconds


def charged(func, *args, cpu_bound=None, **kwargs):
    """Seconds charged to one call of ``func``."""
    return charge(*cpu_and_wall(func, *args, **kwargs), cpu_bound=cpu_bound)


class budget:
    """``with budget(seconds):`` fails if the block's charged time exceeds it.

    The check runs only when the block completed (an exception the block
    raised propagates unchanged). ``cpu``, ``wall`` and ``charged`` hold the
    measurement afterwards, for messages. Whatever clock is charged, a block
    whose wall time passed ``hard_deadline_for(seconds)`` fails too: CPU time
    bounds the work, and that ceiling bounds a wait no runner load explains.
    """

    def __init__(self, seconds, what="the block", cpu_bound=None):
        self.seconds, self.what, self.cpu_bound = seconds, what, cpu_bound
        self.cpu = self.wall = self.charged = None

    def __enter__(self):
        self._cpu, self._wall = time.process_time(), time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cpu = time.process_time() - self._cpu
        self.wall = time.perf_counter() - self._wall
        self.charged = charge(self.cpu, self.wall, self.cpu_bound)
        if exc_type is None:
            assert self.charged < self.seconds and self.wall < hard_deadline_for(
                self.seconds
            ), (
                f"{self.what} took {self.charged:.2f}s charged "
                f"({self.cpu:.2f}s CPU, {self.wall:.2f}s wall), "
                f"budget {self.seconds}s"
            )
        return False


def within_budget(func, seconds, repeats=3, cpu_bound=None):
    """``(ok, seconds)``: the fastest of ``repeats`` charged runs, ok if under.

    Min-of-k because one run on a loaded runner is noise; contention only adds
    time, so the minimum is closest to the code's own cost. A run whose wall
    time passed ``hard_deadline_for(seconds)`` is never ok.
    """
    runs = [cpu_and_wall(func) for _ in range(repeats)]
    best = min(charge(cpu, wall, cpu_bound) for cpu, wall in runs)
    ceiling = hard_deadline_for(seconds)
    return best < seconds and min(wall for _, wall in runs) < ceiling, best


def scaling_ratio(op, small, big, reps=3, noise_floor=0.1, cpu_bound=None):
    """Fastest-of-``reps`` ``op(big)`` over ``op(small)`` (``big`` == 4*``small``).

    A load-invariant scaling factor: a linear sink is ~4x, a pre-patch O(n**2)
    sink ~16x. The floor is multiplicative so a sub-second quadratic is not
    hidden by additive slack. The small and big runs alternate so a burst of
    load cannot land on one side only, the cheap small side gets ``reps``
    extra runs, and each side keeps its minimum on both clocks. A CPU-bound op
    is judged in CPU time; an op that mostly waits is judged on the wall clock
    and the higher of the two ratios is kept, so the fallback only tightens.
    ``cpu_bound`` declares the op's kind and skips the heuristic.
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
    wall_ratio = wall[big] / max(wall[small], noise_floor)
    if cpu_bound is True:
        return cpu_ratio
    if cpu_bound is False or cpu[big] < CPU_BOUND_SHARE * wall[big]:
        return max(cpu_ratio, wall_ratio)
    return cpu_ratio


def assert_subquadratic(
    op, small, big, factor=QUADRATIC_RATIO, noise_floor=0.1, reps=3, cpu_bound=None
):
    """Assert ``op(big)`` (big == 4*small) costs under ``factor`` times ``op(small)``."""
    ratio = scaling_ratio(
        op, small, big, reps=reps, noise_floor=noise_floor, cpu_bound=cpu_bound
    )
    assert ratio < factor, (small, big, ratio)


# ---------------------------------------------------------------------------
# Work done in a child process or on a thread
# ---------------------------------------------------------------------------
# A hang detector runs the sink in a child and joins it with a deadline. The
# same rule applies: the child is charged its own CPU time when it computed and
# its wall time when it waited, and only a child that is still running at a
# generous hard deadline is a hang. The budget the test names stays the same
# number; it now bounds the work rather than the runner's queue.


def hard_deadline_for(budget):
    """The wall-clock deadline after which a child is a hang, not merely slow."""
    return max(4.0 * budget, 60.0)


def _children_cpu_seconds():
    """CPU seconds of every reaped child so far, or ``None`` where unknown."""
    try:
        import resource
    except ImportError:  # Windows
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _child_main(target, args, report_q):
    """Run ``target(*args)`` in the child and report its (CPU, wall) seconds.

    The deltas bracket the call itself: a spawned child first imports the
    test module and with it nltk, several CPU seconds that are the runner's
    cost, not the sink's. ``sys.exit`` inside the target still reports.
    """
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    try:
        target(*args)
    finally:
        report_q.put(
            (time.process_time() - cpu_start, time.perf_counter() - wall_start)
        )


class ChildRun:
    """What happened to a child: whether it finished, its exit code, and the
    CPU, wall and charged seconds; ``within_budget`` is the verdict."""

    def __init__(self, finished, exitcode, cpu, wall, budget, cpu_bound=None):
        self.finished, self.exitcode, self.budget = finished, exitcode, budget
        self.cpu, self.wall = cpu, wall
        self.charged = charge(cpu, wall, cpu_bound) if cpu is not None else wall
        self.within_budget = finished and self.charged < budget

    def __repr__(self):
        cpu = "unknown" if self.cpu is None else f"{self.cpu:.2f}s"
        return (
            f"ChildRun(finished={self.finished}, exit={self.exitcode}, "
            f"cpu={cpu}, wall={self.wall:.2f}s, charged={self.charged:.2f}s, "
            f"budget={self.budget}s)"
        )


def run_in_process(
    target, args=(), *, budget, hard_deadline=None, context=None, cpu_bound=None
):
    """Run ``target(*args)`` in a child process and judge it against ``budget``.

    The child is joined until ``hard_deadline`` (``hard_deadline_for(budget)``
    by default), then terminated: a child still running then is a hang and
    ``finished`` is False. A child that returned is charged the CPU and wall
    seconds of the call itself, which it reports back at exit (``sys.exit``
    included) with interpreter startup and imports excluded; where the report
    is missing it is charged the reaped children's CPU time, or its wall time
    where neither is known. ``within_budget`` is True when that charge is under
    ``budget``. ``args`` may carry the caller's own result queue as before.
    """
    if context is None:
        from nltk.test.unit import _mp_ctx

        context = _mp_ctx()
    if hard_deadline is None:
        hard_deadline = hard_deadline_for(budget)
    report_q = context.Queue()
    proc = context.Process(target=_child_main, args=(target, args, report_q))
    children_before = _children_cpu_seconds()
    started = time.perf_counter()
    proc.start()
    proc.join(hard_deadline)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return ChildRun(
            False, proc.exitcode, None, time.perf_counter() - started, budget
        )
    wall = time.perf_counter() - started
    try:
        cpu, wall = report_q.get(timeout=1.0)  # the call itself, startup excluded
    except Exception:  # noqa: BLE001  (the child left by os._exit or crashed)
        cpu = None
        children_after = _children_cpu_seconds()
        if children_before is not None and children_after is not None:
            cpu = children_after - children_before
    return ChildRun(True, proc.exitcode, cpu, wall, budget, cpu_bound)


def finishes_within(seconds, fn, hard_deadline=None, cpu_bound=None):
    """Run ``fn`` on a daemon thread; ``(finished, exception, charged)``.

    ``finished`` is True when ``fn`` returned or raised with less than
    ``seconds`` charged to it: the process CPU time it accumulated when it
    computed (the caller only waits), or its wall time when it waited. A
    thread still running at ``hard_deadline`` is a hang and reads False.
    """
    if hard_deadline is None:
        hard_deadline = hard_deadline_for(seconds)
    done, outcome = threading.Event(), {}

    def run():
        try:
            outcome["value"] = fn()
        except BaseException as exc:  # noqa: BLE001  (handed to the caller)
            outcome["exc"] = exc
        finally:
            done.set()

    cpu_start, wall_start = time.process_time(), time.perf_counter()
    threading.Thread(target=run, daemon=True).start()
    returned = done.wait(hard_deadline)
    charged = charge(
        time.process_time() - cpu_start, time.perf_counter() - wall_start, cpu_bound
    )
    return returned and charged < seconds, outcome.get("exc"), charged


def run_subprocess(cmd, budget, hard_deadline=None, cpu_bound=None, **kwargs):
    """``subprocess.run(cmd, ...)`` judged against ``budget`` like a child.

    Returns ``(completed, run)``: ``completed`` is the ``CompletedProcess`` or
    ``None`` when the command was still running at ``hard_deadline`` (a hang,
    killed), and ``run`` is a :class:`ChildRun` charging the reaped children's
    CPU time where the platform reports it and the wall time otherwise.
    """
    import subprocess

    if hard_deadline is None:
        hard_deadline = hard_deadline_for(budget)
    children_before = _children_cpu_seconds()
    started = time.perf_counter()
    try:
        completed = subprocess.run(cmd, timeout=hard_deadline, **kwargs)
    except subprocess.TimeoutExpired:
        return None, ChildRun(False, None, None, time.perf_counter() - started, budget)
    wall = time.perf_counter() - started
    children_after = _children_cpu_seconds()
    cpu = None
    if children_before is not None and children_after is not None:
        cpu = children_after - children_before
    return completed, ChildRun(True, completed.returncode, cpu, wall, budget, cpu_bound)
