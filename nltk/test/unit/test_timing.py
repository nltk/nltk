# Natural Language Toolkit: tests for the suite's timing rule
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The timing rule the DoS budget and scaling tests rely on: a CPU-bound block
is charged its CPU time, so a descheduled interpreter does not inflate it, and
a waiting block is charged its wall time, so a hang that sleeps or blocks is
still seen. Real sleeps and real spinning, nothing mocked."""

import sys
import threading
import time

import pytest

from nltk.test.unit import timing


def spin(seconds):
    deadline = time.process_time() + seconds
    while time.process_time() < deadline:
        pass


def test_cpu_time_is_the_work_and_the_charge_rule_is_deterministic():
    # the sleep beside the work must show in the wall clock and not in CPU
    # time; a 0.1 s sleep leaves a 0.05 s margin over the two 15.6 ms ticks
    # Windows can lose between its CPU clock and the spin's end
    cpu, wall = timing.cpu_and_wall(lambda: (spin(0.2), time.sleep(0.1)))
    assert 0.15 <= cpu <= 0.35 and wall >= cpu + 0.05, (cpu, wall)
    # the rule itself, on fixed numbers: half the wall time on the CPU is
    # judged as work, less is judged as waiting, a declaration overrides
    assert timing.charge(0.60, 1.0) == 0.60
    assert timing.charge(0.40, 1.0) == 1.0
    assert timing.charge(0.20, 1.0, cpu_bound=True) == 0.20
    assert timing.charge(0.90, 1.0, cpu_bound=False) == 1.0


def test_a_waiting_block_is_charged_its_wall_time():
    cpu, wall = timing.cpu_and_wall(time.sleep, 0.2)
    # Windows can return from a sleep a millisecond early on its coarse timer
    assert wall >= 0.19 and cpu < 0.1, (cpu, wall)
    assert timing.charge(cpu, wall) == wall


def test_budget_passes_a_declared_cpu_block_whatever_the_stall_beside_it():
    # a stall of the kind a loaded runner injects: the wall clock is over
    # budget, the charged CPU time of the declared computing block is not
    with timing.budget(0.45, cpu_bound=True) as measured:
        spin(0.3)
        time.sleep(0.2)
    assert measured.charged == measured.cpu < 0.45 < measured.wall


def test_the_wall_ceiling_bounds_a_wait_even_for_a_declared_cpu_block():
    assert timing.hard_deadline_for(0.01) == 60.0
    assert timing.hard_deadline_for(30) == 120.0
    # the ceiling check on fixed numbers, through the same assertion the
    # context manager makes (its wall must stay under the ceiling)
    clock = timing.budget(0.5, cpu_bound=True)
    clock.__enter__()
    clock._wall -= timing.hard_deadline_for(0.5)  # as if 60 s had passed
    with pytest.raises(AssertionError, match="budget 0.5s"):
        clock.__exit__(None, None, None)


def test_a_stall_longer_than_the_work_is_treated_as_waiting():
    # the rule cannot tell a long stall from a wait, so it takes the wall
    # clock, the side that never hides a hang
    with pytest.raises(AssertionError, match="budget 0.45s"):
        with timing.budget(0.45):
            spin(0.1)
            time.sleep(0.4)


@pytest.mark.parametrize("hang", [lambda: spin(0.4), lambda: time.sleep(0.4)])
def test_budget_fails_a_block_over_budget_whether_it_spins_or_waits(hang):
    with pytest.raises(AssertionError, match="budget 0.2s"):
        with timing.budget(0.2):
            hang()


def test_budget_does_not_mask_an_exception_from_the_block():
    with pytest.raises(KeyError):
        with timing.budget(0.001):
            spin(0.05)
            raise KeyError("from the block")


def test_within_budget_keeps_the_fastest_charged_run():
    ok, best = timing.within_budget(lambda: spin(0.05), 0.5, cpu_bound=True)
    assert ok and 0.02 <= best <= 0.2, best
    ok, best = timing.within_budget(lambda: time.sleep(0.3), 0.2, repeats=1)
    assert not ok and best >= 0.29, best


def test_scaling_ratio_times_the_small_side_as_a_block_of_calls():
    # both sides of a linear sink run for about as long: the small op is
    # called SMALL_BLOCK times per rep inside one timed block, the big op once,
    # and the sides interleave so no side's samples all land in one stretch
    calls, order = {}, []

    def op(n):
        calls[n] = calls.get(n, 0) + 1
        order.append(n)
        spin(n / 1_000_000)

    ratio = timing.scaling_ratio(op, 150_000, 600_000, reps=2, cpu_bound=True)
    assert calls == {150_000: 2 * timing.SMALL_BLOCK, 600_000: 2}, calls
    assert order == ([150_000] * timing.SMALL_BLOCK + [600_000]) * 2, order
    assert 2.0 < ratio < 8.0, ratio


def test_scaling_samples_pair_each_big_run_with_the_small_block_beside_it():
    samples = timing.scaling_samples(
        lambda n: spin(n / 1_000_000), 150_000, 600_000, reps=2
    )
    assert len(samples) == 2
    for s in samples:
        # per-call seconds on both clocks, and a calibration rate beside
        # each side: the chunk costs milliseconds, never nothing
        assert 0.1 <= s.small_cpu <= 0.4 and s.small_wall >= s.small_cpu * 0.9, s
        assert 0.4 <= s.big_cpu <= 1.6 and s.big_wall >= s.big_cpu * 0.9, s
        assert 0 < s.small_rate < 0.1 and 0 < s.big_rate < 0.1, s
        assert "ScalingSample(" in repr(s)


def test_calibration_rate_reads_the_chunk_cost_after_a_resolvable_run():
    cpu, wall = timing.cpu_and_wall(timing.calibration_rate)
    assert timing.CALIBRATION_SECONDS <= cpu < 1.0, (cpu, wall)
    rate = timing.calibration_rate()
    assert 0 < rate < timing.CALIBRATION_SECONDS, rate


def _sample(
    small_cpu, big_cpu, small_rate=1.0, big_rate=1.0, small_wall=None, big_wall=None
):
    return timing.ScalingSample(
        small_cpu,
        small_cpu if small_wall is None else small_wall,
        small_rate,
        big_cpu,
        big_cpu if big_wall is None else big_wall,
        big_rate,
    )


def _min_of_each_side(samples, noise_floor=0.1):
    """The rule this suite used before: the fastest small block against the
    fastest big run, whichever reps they came from and whatever the core's
    rate was during each; kept here as the oracle the paired rule replaces."""
    return min(s.big_cpu for s in samples) / max(
        min(s.small_cpu for s in samples), noise_floor
    )


def test_paired_ratio_is_the_median_of_the_per_rep_ratios_on_a_calm_machine():
    samples = [_sample(0.2, 0.8), _sample(0.2, 1.0), _sample(0.25, 0.8)]
    assert timing.paired_ratio(samples, cpu_bound=True) == 4.0
    # two reps: the mean of the two ratios; one rep: that ratio
    assert timing.paired_ratio(samples[:2], cpu_bound=True) == 4.5
    assert timing.paired_ratio(samples[1:2], cpu_bound=True) == 5.0
    with pytest.raises(ValueError):
        timing.paired_ratio([])


def test_paired_ratio_normalises_a_speed_change_inside_a_pair_by_the_units():
    # the big run of every rep landed in a stretch three times slower than
    # its small block (the units beside it read 3 ms a chunk against 1 ms):
    # the raw seconds say 12x for a linear sink, the normalised ones 4x
    samples = [_sample(0.2, 2.4, small_rate=0.001, big_rate=0.003)] * 3
    assert _min_of_each_side(samples) == pytest.approx(12.0)
    assert timing.paired_ratio(samples, cpu_bound=True) == pytest.approx(4.0)
    # and the reverse change cannot hide a quadratic sink: a 16x sink whose
    # small blocks ran in the slow stretch reads 5.3x in raw seconds and 16x
    # once each side is normalised by the units beside it
    samples = [_sample(0.3, 1.6, small_rate=0.003, big_rate=0.001)] * 3
    assert _min_of_each_side(samples) == pytest.approx(16 / 3)
    assert timing.paired_ratio(samples, cpu_bound=True) == pytest.approx(16.0)


def test_paired_ratio_keeps_the_floor_on_the_normalised_small_seconds():
    # the shape of the macOS failure on develop: every small block under the
    # floor on a fast core, every big run in a stretch three times slower;
    # the old rule read the floored small against the slowed big as 10.4x
    samples = [
        _sample(0.06, 1.04, small_rate=0.001, big_rate=0.003),
        _sample(0.06, 1.10, small_rate=0.001, big_rate=0.003),
        _sample(0.06, 1.20, small_rate=0.001, big_rate=0.003),
    ]
    assert _min_of_each_side(samples) == pytest.approx(10.4)
    ratio = timing.paired_ratio(samples, cpu_bound=True)
    # normalised to the run's median rate the small block is 0.12 s and the
    # big run 0.73 s, a 6.1x reading for a 4x sink whose big runs were
    # slower than the drift alone explains; well under the 8x bar
    assert 5.5 < ratio < 6.5, ratio
    # the floor still bites once the normalised small seconds are under it:
    # a 0.04 s small block at every rate reads as a 0.1 s one
    samples = [_sample(0.04, 0.3)] * 3
    assert timing.paired_ratio(samples, cpu_bound=True) == pytest.approx(3.0)


def test_paired_ratio_sees_a_quadratic_whose_last_big_run_got_the_core_alone():
    # the ubuntu shape on develop: a sibling shared the core until the last
    # big run, so the fastest big against the slowest small read a 16x oracle
    # at 5.3x; paired by rep and normalised it reads 16x
    shared, alone = 0.003, 0.001
    samples = [
        _sample(0.3, 4.8, small_rate=shared, big_rate=shared),
        _sample(0.3, 4.8, small_rate=shared, big_rate=shared),
        _sample(0.3, 1.6, small_rate=shared, big_rate=alone),
    ]
    assert _min_of_each_side(samples) == pytest.approx(16 / 3)
    assert timing.paired_ratio(samples, cpu_bound=True) == pytest.approx(16.0)


def test_paired_ratio_judges_a_waiting_op_on_the_wall_clock_too():
    # CPU seconds say 1x, the wall clock says 16x: a sink that sleeps n**2
    # must still read quadratic, so the higher ratio is kept when the big
    # run spent under half its wall time on the CPU, or when so declared
    sleeping = [_sample(0.1, 0.1, small_wall=0.1, big_wall=1.6)] * 3
    assert timing.paired_ratio(sleeping) == 16.0
    assert timing.paired_ratio(sleeping, cpu_bound=False) == 16.0
    assert timing.paired_ratio(sleeping, cpu_bound=True) == 1.0
    # a computing op stretched by a descheduled stretch is judged on its CPU
    # seconds while it kept the CPU for half its wall time; stalled longer
    # than it worked it is treated as waiting, the side that never hides a hang
    computing = [_sample(0.2, 0.8, small_wall=0.2, big_wall=1.2)] * 3
    assert timing.paired_ratio(computing) == 4.0
    stalled = [_sample(0.2, 0.8, small_wall=0.2, big_wall=3.0)] * 3
    assert timing.paired_ratio(stalled) == 15.0


def test_assert_subquadratic_separates_linear_from_quadratic_cpu_work():
    timing.assert_subquadratic(
        lambda n: spin(n / 1_000_000), 150_000, 600_000, cpu_bound=True
    )
    with pytest.raises(AssertionError) as failure:
        timing.assert_subquadratic(
            lambda n: spin((n / 1_000_000) ** 2 * 4),
            200_000,
            800_000,
            reps=2,
            cpu_bound=True,
        )
    # the message carries the samples, so a red CI cell can be traced
    assert "ScalingSample(" in str(failure.value)


# === the runner regimes, simulated with real spinning ===
# Spinning threads share the interpreter lock, so a sample or calibration unit
# taken while they spin costs more CPU for the same work, as on a loaded runner.


def _work(n):
    x = 0
    for _ in range(n):
        x += 1
    return x


class _Siblings:
    """``count`` threads that spin in pure Python while ``spinning`` is set."""

    def __init__(self, count):
        self.spinning, self.stopped = threading.Event(), False
        self.threads = [
            threading.Thread(target=self._run, daemon=True) for _ in range(count)
        ]

    def _run(self):
        # a sibling holds the lock for whole switch intervals, as a worker
        # process on the other hyperthread holds its share of the core
        while not self.stopped:
            if self.spinning.wait(0.01):
                _work(40_000)

    def __enter__(self):
        for thread in self.threads:
            thread.start()
        return self

    def __exit__(self, *exc):
        self.stopped = True
        self.spinning.set()
        for thread in self.threads:
            thread.join()
        return False


_REGIME_SIBLINGS = 2

#: Clean CPU seconds of one small call of a regime sink: the floor of the
#: rule, so the clean sample is the one the floor would take as it stands
#: and the slowed samples, two siblings on, sit well over it on any core.
_REGIME_SMALL_SECONDS = 0.1


def _regime_sizes():
    """``(small, big)`` iterations sized on this core so a clean small call
    costs about ``_REGIME_SMALL_SECONDS`` of CPU time."""
    per_iteration = timing.calibration_rate() / timing.CALIBRATION_CHUNK
    small = int(_REGIME_SMALL_SECONDS / per_iteration)
    return small, 4 * small


def _regime_samples(sink, spin_at):
    """Samples of ``sink(n, small)`` under a regime: ``spin_at(call_index,
    n, big)`` says whether the siblings spin from the start of that call."""
    if not getattr(sys, "_is_gil_enabled", lambda: True)():
        pytest.skip("the regimes are simulated with threads taking turns at the GIL")
    small, big = _regime_sizes()
    calls = []
    with _Siblings(_REGIME_SIBLINGS) as siblings:
        # a regime that begins loaded was loaded before the measurement
        # started, as a sibling worker already runs when a test begins, so
        # the first calibration unit reads the loaded rate too
        if spin_at(0, small, big):
            siblings.spinning.set()

        def op(n):
            if spin_at(len(calls), n, big):
                siblings.spinning.set()
            else:
                siblings.spinning.clear()
            calls.append(n)
            sink(n, small)

        samples = timing.scaling_samples(op, small, big)
    assert len(calls) == 3 * (timing.SMALL_BLOCK + 1), calls
    return samples


def _linear(n, small):
    _work(n)


def _quadratic(n, small):
    _work(n * n // small)


def _verdicts(samples):
    return (
        timing.paired_ratio(samples, cpu_bound=True),
        _min_of_each_side(samples),
    )


def test_regime_a_lasting_slowdown_from_the_first_big_run_on():
    # the core slows for good once the first big run starts, so only the
    # first small block is fast: the old rule reads a linear sink at 12x,
    # paired and normalised it reads near 4x
    def slow_from_first_big(index, n, big):
        return index >= timing.SMALL_BLOCK

    samples = _regime_samples(_linear, slow_from_first_big)
    assert samples[1].small_cpu >= 1.5 * samples[0].small_cpu, samples
    paired, old = _verdicts(samples)
    assert paired < timing.QUADRATIC_RATIO <= old, (paired, old, samples)
    # the quadratic sink reads over the bar under both rules in this regime
    samples = _regime_samples(_quadratic, slow_from_first_big)
    paired, old = _verdicts(samples)
    assert paired >= timing.QUADRATIC_RATIO and old >= timing.QUADRATIC_RATIO, (
        paired,
        old,
        samples,
    )


def test_regime_a_sibling_through_the_small_blocks_that_idles_for_the_last_big_run():
    # the ubuntu shape: a sibling shares the core until the last big run, so
    # the old rule reads the fastest big (alone) against a shared small block,
    # a 16x quadratic sink under 8x; paired by rep two wholly shared pairs read 16x
    last_big = 3 * (timing.SMALL_BLOCK + 1) - 1

    def shared_until_last_big(index, n, big):
        return index < last_big

    samples = _regime_samples(_quadratic, shared_until_last_big)
    assert samples[0].big_cpu >= 1.5 * samples[2].big_cpu, samples
    paired, old = _verdicts(samples)
    assert old < timing.QUADRATIC_RATIO <= paired, (paired, old, samples)
    # the linear sink stays under the bar under both rules in this regime
    samples = _regime_samples(_linear, shared_until_last_big)
    paired, old = _verdicts(samples)
    assert paired < timing.QUADRATIC_RATIO and old < timing.QUADRATIC_RATIO, (
        paired,
        old,
        samples,
    )


def test_regime_a_fast_window_for_one_small_block():
    # the macOS shape: one fast window that a single small block gets. The
    # old rule keeps that block as the small side and reads a linear sink at
    # 16x; paired by rep the window is one pair of three and the median is near 4x
    second_block = range(timing.SMALL_BLOCK + 1, 2 * timing.SMALL_BLOCK + 1)

    def slow_except_second_block(index, n, big):
        return index not in second_block

    samples = _regime_samples(_linear, slow_except_second_block)
    assert samples[0].small_cpu >= 1.5 * samples[1].small_cpu, samples
    paired, old = _verdicts(samples)
    assert paired < timing.QUADRATIC_RATIO <= old, (paired, old, samples)
    # the quadratic sink reads over the bar under both rules in this regime
    samples = _regime_samples(_quadratic, slow_except_second_block)
    paired, old = _verdicts(samples)
    assert paired >= timing.QUADRATIC_RATIO and old >= timing.QUADRATIC_RATIO, (
        paired,
        old,
        samples,
    )


# ---- child processes and threads --------------------------------------------
def _spin_child(seconds):
    spin(seconds)


def _sleep_child(seconds):
    time.sleep(seconds)


def _exit_child(code):
    import sys

    spin(0.05)
    sys.exit(code)


def test_a_child_that_computes_is_charged_its_own_cpu_time():
    # a declared computing child: the stretch a loaded runner adds to its wall
    # time (2.2x to 2.7x on the macOS cells) must not reach the charge
    run = timing.run_in_process(_spin_child, (0.3,), budget=5.0, cpu_bound=True)
    assert run.finished and run.exitcode == 0, run
    assert run.cpu is not None and run.charged == run.cpu, run
    assert run.cpu >= 0.25, run  # the child's own clock, not the parent's
    assert run.within_budget


def test_an_undeclared_child_is_judged_by_the_share_rule_on_fixed_numbers():
    computing = timing.ChildRun(True, 0, 0.6, 1.0, budget=0.8)
    stretched = timing.ChildRun(True, 0, 0.3, 1.0, budget=0.8)
    assert computing.charged == 0.6 and computing.within_budget
    assert stretched.charged == 1.0 and not stretched.within_budget
    assert timing.ChildRun(True, 0, 0.3, 1.0, budget=0.8, cpu_bound=True).within_budget
    assert not timing.ChildRun(False, None, None, 60.0, budget=0.8).within_budget


def test_a_child_over_budget_fails_whether_it_spins_or_sleeps():
    spinning = timing.run_in_process(_spin_child, (0.5,), budget=0.2)
    sleeping = timing.run_in_process(_sleep_child, (0.5,), budget=0.2)
    assert spinning.finished and not spinning.within_budget, spinning
    assert sleeping.finished and not sleeping.within_budget, sleeping
    assert sleeping.charged == sleeping.wall >= 0.49, sleeping


def test_a_hanging_child_is_terminated_at_the_hard_deadline():
    run = timing.run_in_process(_sleep_child, (30,), budget=0.2, hard_deadline=1.0)
    assert not run.finished and not run.within_budget, run
    assert run.wall < 10, run


def test_a_child_exit_code_is_reported_with_its_cpu_time():
    run = timing.run_in_process(_exit_child, (3,), budget=5.0)
    assert run.finished and run.exitcode == 3, run
    assert run.cpu is not None and run.within_budget, run


def test_finishes_within_charges_a_thread_its_cpu_time():
    finished, exc, charged = timing.finishes_within(
        0.5, lambda: spin(0.2), cpu_bound=True
    )
    assert finished and exc is None and 0.15 <= charged < 0.5, (finished, charged)
    finished, exc, charged = timing.finishes_within(0.2, lambda: time.sleep(0.4))
    assert not finished and charged >= 0.39, (finished, charged)
    finished, exc, _ = timing.finishes_within(1.0, lambda: 1 / 0)
    assert finished and isinstance(exc, ZeroDivisionError)


def test_run_subprocess_judges_a_child_interpreter():
    import sys

    completed, run = timing.run_subprocess(
        [
            sys.executable,
            "-c",
            "import time\nt=time.process_time()\nwhile time.process_time()-t<0.3: pass",
        ],
        budget=5.0,
        cpu_bound=True,
    )
    assert (
        completed is not None and completed.returncode == 0 and run.within_budget
    ), run
    completed, run = timing.run_subprocess(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        budget=0.2,
        hard_deadline=1.0,
    )
    assert completed is None and not run.finished, run


def test_run_subprocess_charges_a_child_its_own_cpu_time_on_every_platform():
    import sys

    # a child that computes for 0.3 s and then waits a full second, over a
    # 1 s budget: a declared computing child must read its CPU time on every
    # platform, so the wait never reaches the charge and the wall clock does
    completed, run = timing.run_subprocess(
        [
            sys.executable,
            "-c",
            "import time\nt=time.process_time()\n"
            "while time.process_time()-t<0.3: pass\ntime.sleep(1.0)",
        ],
        budget=1.0,
        cpu_bound=True,
        capture_output=True,
    )
    assert completed is not None and completed.returncode == 0, run
    assert run.cpu is not None and run.charged == run.cpu, run
    assert 0.25 <= run.cpu < 1.0 <= run.wall, run
    assert run.within_budget, run
