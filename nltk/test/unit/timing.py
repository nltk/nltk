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

A scaling assertion compares two runs, and the core's rate can change between
them: the macOS runners drift two to three times within a second, and under
xdist a sibling worker shares the core for a stretch and then idles. Taking
the fastest run of each side separately let such a change enter the ratio
directly (a linear sink read 10x, a quadratic oracle 7.4x), so ``scaling_ratio``
interleaves its samples, measures a short calibration unit of fixed
pure-Python work beside each one, normalises every sample by the rate its
units read, and takes the median over the reps of each big run against the
small block measured next to it. The thresholds, the floor, the 4x jump and
the reps are unchanged.
"""

import threading
import time

#: A block whose CPU time is at least this share of its wall time is judged on
#: CPU time, below it on the wall clock. A loaded runner can push a computing
#: block under it (0.20 s CPU took 0.55 s wall), so such a sink declares itself.
CPU_BOUND_SHARE = 0.5

#: A scaling factor at or above this reads as super-linear (quadratic ~16x);
#: a linear sink stays near 4x, so the gap is wide on any machine.
QUADRATIC_RATIO = 8.0

#: Calls of the small op timed as one block in ``scaling_ratio``: a linear
#: sink then runs for about as long on both sides, so a host whose core rate
#: drifts cannot hand the short side a fast window the long side never sees.
SMALL_BLOCK = 4


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


#: CPU seconds of fixed pure-Python work in each calibration unit beside a
#: ``scaling_ratio`` sample: long enough for Windows's 15.6 ms CPU clock to
#: resolve, short enough to read the core's rate at the moment of the sample.
CALIBRATION_SECONDS = 0.1

#: Loop iterations of one calibration chunk, a fixed amount of pure-Python
#: work; a unit times whole chunks and reports the CPU seconds one costs.
CALIBRATION_CHUNK = 50_000


def _calibration_chunk():
    x = 0
    for _ in range(CALIBRATION_CHUNK):
        x += 1
    return x


def calibration_rate():
    """CPU seconds one calibration chunk costs right now.

    Whole chunks are timed until ``CALIBRATION_SECONDS`` of CPU time have
    accumulated, so the reading resolves on every platform while the unit
    stays short against the samples it sits between. The rate rises when
    the core slows (a macOS runner changes its rate two to three times within
    a second) and when a sibling shares the core (an xdist worker on the
    other hyperthread of a hosted runner), which is what a sample measured
    in that stretch must be normalised by.
    """
    chunks, start = 0, time.process_time()
    while True:
        _calibration_chunk()
        chunks += 1
        elapsed = time.process_time() - start
        if elapsed >= CALIBRATION_SECONDS:
            return elapsed / chunks


class ScalingSample:
    """One rep of ``scaling_samples``: a block of ``SMALL_BLOCK`` small calls
    and the big run measured beside it, each with the CPU seconds per call,
    the wall seconds per call and the calibration rate read beside it (the
    mean of the units measured just before and just after it)."""

    __slots__ = (
        "small_cpu",
        "small_wall",
        "small_rate",
        "big_cpu",
        "big_wall",
        "big_rate",
    )

    def __init__(self, small_cpu, small_wall, small_rate, big_cpu, big_wall, big_rate):
        self.small_cpu, self.small_wall = small_cpu, small_wall
        self.small_rate = small_rate
        self.big_cpu, self.big_wall, self.big_rate = big_cpu, big_wall, big_rate

    def __repr__(self):
        return (
            f"ScalingSample(small {self.small_cpu:.3f}s cpu {self.small_wall:.3f}s "
            f"wall at {self.small_rate * 1e3:.2f}ms/chunk, big {self.big_cpu:.3f}s "
            f"cpu {self.big_wall:.3f}s wall at {self.big_rate * 1e3:.2f}ms/chunk)"
        )


def scaling_samples(op, small, big, reps=3):
    """``reps`` interleaved samples of ``op(small)`` and ``op(big)``.

    Each rep times a block of ``SMALL_BLOCK`` calls of the small op and then
    one call of the big op, with a calibration unit measured before, between
    and after them, so every sample is paired with the big or small run
    measured next to it and carries the core's rate at that moment.
    """
    samples = []

    def small_block():
        for _ in range(SMALL_BLOCK):
            op(small)

    rate = calibration_rate()
    for _ in range(reps):
        before = rate
        small_cpu, small_wall = cpu_and_wall(small_block)
        between = calibration_rate()
        big_cpu, big_wall = cpu_and_wall(op, big)
        rate = calibration_rate()
        samples.append(
            ScalingSample(
                small_cpu / SMALL_BLOCK,
                small_wall / SMALL_BLOCK,
                (before + between) / 2,
                big_cpu,
                big_wall,
                (between + rate) / 2,
            )
        )
    return samples


def _median(values):
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def paired_ratio(samples, noise_floor=0.1, cpu_bound=None):
    """The scaling factor read from interleaved samples: the median over the
    reps of the big run over the small block measured beside it.

    CPU seconds are normalised to the run's reference rate (the median of
    the calibration rates its samples carry) before the two sides are
    compared: a sample that ran in a slow stretch is scaled down by the rate
    its own units read, so a speed change between the samples of one pair
    cancels, and pairing with the median keeps a fast or slow window that
    one side alone saw from standing against the other side's best. The
    floor applies to the normalised small seconds, as it applied to the raw
    seconds on a calm machine. Wall seconds are paired the same way without
    the rate (a wait does not speed up with the core); a waiting op keeps the
    higher of its two ratios, so the fallback only tightens.
    """
    if not samples:
        raise ValueError("no samples")
    reference = _median([s.small_rate for s in samples] + [s.big_rate for s in samples])
    cpu_ratios, wall_ratios, shares = [], [], []
    for s in samples:
        small_cpu = s.small_cpu * reference / s.small_rate
        big_cpu = s.big_cpu * reference / s.big_rate
        cpu_ratios.append(big_cpu / max(small_cpu, noise_floor))
        wall_ratios.append(s.big_wall / max(s.small_wall, noise_floor))
        shares.append(s.big_cpu / s.big_wall if s.big_wall else 1.0)
    cpu_ratio, wall_ratio = _median(cpu_ratios), _median(wall_ratios)
    if cpu_bound is True:
        return cpu_ratio
    if cpu_bound is False or _median(shares) < CPU_BOUND_SHARE:
        return max(cpu_ratio, wall_ratio)
    return cpu_ratio


def scaling_ratio(op, small, big, reps=3, noise_floor=0.1, cpu_bound=None):
    """``op(big)`` over ``op(small)`` (``big`` == 4*``small``), paired by rep.

    A load-invariant scaling factor: a linear sink is ~4x, a pre-patch O(n**2)
    sink ~16x. The floor is multiplicative so a sub-second quadratic is not
    hidden by additive slack. The small side is timed as a block of
    ``SMALL_BLOCK`` calls, so a linear sink runs for about as long on both
    sides, and the samples interleave (small block, big run, small block,
    big run, ...) with a calibration unit beside each one; the ratio is the
    median over the reps of each big run against the small block measured
    next to it, both normalised by the rate their units read. The minimum of
    each side taken separately, which this replaces, let a speed change
    between the samples enter the ratio directly: a macOS runner that found a
    fast window for one small block and none for a big run read a linear
    sink at 10x, and an xdist sibling that shared the core through the small
    runs and idled through a big one read a quadratic oracle at 7.4x. A
    CPU-bound op is judged in CPU time; an op that mostly waits is judged on
    the wall clock and the higher of the two ratios is kept, so the fallback
    only tightens. ``cpu_bound`` declares the op's kind and skips the
    heuristic. See :func:`scaling_samples` and :func:`paired_ratio`.
    """
    return paired_ratio(
        scaling_samples(op, small, big, reps=reps),
        noise_floor=noise_floor,
        cpu_bound=cpu_bound,
    )


def assert_subquadratic(
    op, small, big, factor=QUADRATIC_RATIO, noise_floor=0.1, reps=3, cpu_bound=None
):
    """Assert ``op(big)`` (big == 4*small) costs under ``factor`` times ``op(small)``."""
    samples = scaling_samples(op, small, big, reps=reps)
    ratio = paired_ratio(samples, noise_floor=noise_floor, cpu_bound=cpu_bound)
    assert ratio < factor, (small, big, ratio, samples)


# Work done in a child process or on a thread: the same rule, with the budget
# the test names bounding the child's own work and a generous hard deadline
# marking a hang. See run_in_process, finishes_within and run_subprocess.


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


def _process_cpu_seconds(process):
    """CPU seconds a finished ``subprocess.Popen`` spent, read from its process
    handle on Windows (kernel plus user time, kept until the handle closes), or
    ``None`` where the handle or the call is not available."""
    handle = getattr(process, "_handle", None)
    if handle is None:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        times = [wintypes.FILETIME() for _ in range(4)]
        kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        if not kernel32.GetProcessTimes(int(handle), *map(ctypes.byref, times)):
            return None
    except (AttributeError, OSError, TypeError, ValueError):
        return None  # not Windows, or the handle cannot be queried
    kernel, user = times[2], times[3]
    # a FILETIME counts 100 ns intervals in two 32 bit halves
    return sum(
        ((t.dwHighDateTime << 32) | t.dwLowDateTime) / 1e7 for t in (kernel, user)
    )


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
    killed), and ``run`` is a :class:`ChildRun` charging the child's CPU time:
    the reaped children's clock where the platform keeps one, the process
    handle's own times on Windows (which keeps no such clock, so a child used
    to be charged its wall time there, interpreter start-up and imports under a
    loaded runner included), and the wall time where neither can be read.
    ``capture_output``, ``input`` and ``check`` work as in ``subprocess.run``.
    """
    import subprocess

    if hard_deadline is None:
        hard_deadline = hard_deadline_for(budget)
    if kwargs.pop("capture_output", False):
        kwargs["stdout"] = kwargs["stderr"] = subprocess.PIPE
    check = kwargs.pop("check", False)
    stdin_data = kwargs.pop("input", None)
    if stdin_data is not None:
        kwargs["stdin"] = subprocess.PIPE
    children_before = _children_cpu_seconds()
    started = time.perf_counter()
    with subprocess.Popen(cmd, **kwargs) as process:
        try:
            out, err = process.communicate(stdin_data, timeout=hard_deadline)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return None, ChildRun(
                False, None, None, time.perf_counter() - started, budget
            )
        wall = time.perf_counter() - started
        children_after = _children_cpu_seconds()
        if children_before is not None and children_after is not None:
            cpu = children_after - children_before
        else:
            cpu = _process_cpu_seconds(process)  # the handle is still open here
    completed = subprocess.CompletedProcess(process.args, process.returncode, out, err)
    if check:
        completed.check_returncode()
    return completed, ChildRun(True, completed.returncode, cpu, wall, budget, cpu_bound)
