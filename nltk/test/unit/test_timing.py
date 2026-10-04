# Natural Language Toolkit: tests for the suite's timing rule
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The timing rule the DoS budget and scaling tests rely on: a CPU-bound block
is charged its CPU time, so a descheduled interpreter does not inflate it, and
a waiting block is charged its wall time, so a hang that sleeps or blocks is
still seen. Real sleeps and real spinning; only the runner regimes at the
end replay on a fake clock, through the real measurement."""

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
    # the shape of the macOS failure on develop (its 0.06 s and 1.04 s; the
    # rates are a construction, develop measured no units): small blocks
    # under the floor on a fast core, big runs in a stretch three times slower
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


def test_paired_ratio_reads_a_lasting_slowdown_from_the_first_big_run_on():
    # the macOS 3.12 cell of #3949's third run: the core slows for good as
    # the first big run starts (2.4 ms a chunk before, 7 ms after), and the
    # old rule reads a linear sink at 8.9x off the fast first block
    samples = [
        _sample(0.125, 1.168, small_rate=0.00243, big_rate=0.0047),
        _sample(0.230, 1.120, small_rate=0.0070, big_rate=0.0070),
        _sample(0.226, 1.115, small_rate=0.00779, big_rate=0.00692),
    ]
    assert _min_of_each_side(samples) == pytest.approx(8.92)
    assert 4.5 < timing.paired_ratio(samples, cpu_bound=True) < 5.5


def test_paired_ratio_reads_a_fast_window_for_one_small_block():
    # develop's readings of the tree printer (10.4x on macOS 3.13, 8.0x on
    # Windows 3.10): one fast window that one small block gets, which the
    # old rule keeps as the small side; paired it is one pair of three
    slow, fast = 0.0025, 0.0020
    samples = [
        _sample(0.25, 1.0, small_rate=slow, big_rate=slow),
        _sample(0.125, 1.0, small_rate=slow, big_rate=slow),
        _sample(0.25, 1.0, small_rate=slow, big_rate=slow),
    ]
    assert _min_of_each_side(samples) == 8.0
    assert timing.paired_ratio(samples, cpu_bound=True) == 4.0
    # the units beside the fast block read the slow rate when the window
    # is shorter than the block, as on macOS, where the block fell under
    # the floor: the old rule read 10.4x, paired it is still one pair
    samples[1] = _sample(0.096, 1.0, small_rate=fast, big_rate=slow)
    assert _min_of_each_side(samples) == pytest.approx(10.0)
    assert timing.paired_ratio(samples, cpu_bound=True) == 4.0


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


# === the runner regimes, replayed through the real measurement on a fake clock ===
# A regime says which calls run loaded; the fake clock then advances by the
# clean cost of every call and calibration chunk times its load, exactly.

#: CPU seconds one calibration chunk costs on the fake clock's clean core.
_CLEAN_CHUNK = 0.002

#: Clean CPU seconds of one small call of a regime sink: twice the rule's floor.
_CLEAN_SMALL = 0.2

#: What a loaded stretch multiplies every cost by, a unit's as a sample's.
_LOADED = 3.0


class _FakeClock:
    """``process_time`` and ``perf_counter`` that advance only when a fake op
    or calibration chunk charges its clean cost times the current load, so
    the real ``cpu_and_wall`` and ``calibration_rate`` read exact numbers."""

    def __init__(self):
        self.cpu, self.wall, self.load = 1000.0, 2000.0, 1.0

    def process_time(self):
        return self.cpu

    def perf_counter(self):
        return self.wall

    def charge(self, clean_seconds):
        self.cpu += clean_seconds * self.load
        self.wall += clean_seconds * self.load


def _regime_samples(monkeypatch, sink, spin_at):
    """Samples of ``sink(n)`` under a regime through the real ``scaling_samples``:
    ``spin_at(index)`` says whether the call at that index runs loaded, and a
    calibration unit bears the load of the call that follows it."""
    clock, calls = _FakeClock(), []

    def chunk():
        clock.load = _LOADED if spin_at(len(calls)) else 1.0
        clock.charge(_CLEAN_CHUNK)

    def op(n):
        clock.load = _LOADED if spin_at(len(calls)) else 1.0
        calls.append(n)
        clock.charge(sink(n))

    # only the clock and the chunk are replaced: the sampling, the pairing,
    # the calibration loop and the rule run unchanged on the numbers they read
    monkeypatch.setattr(timing, "time", clock)
    monkeypatch.setattr(timing, "_calibration_chunk", chunk)
    samples = timing.scaling_samples(op, 1, 4)
    assert len(calls) == 3 * (timing.SMALL_BLOCK + 1), calls
    return samples


def _linear(n):
    return _CLEAN_SMALL * n


def _quadratic(n):
    return _CLEAN_SMALL * n * n


def _per_rep(samples):
    """Each rep's reading, the numbers ``paired_ratio`` takes the median of:
    the big run over the small block beside it, each by the rate its units
    read (the reference rate cancels; no small block here is under the floor)."""
    return [(s.big_cpu / s.big_rate) / (s.small_cpu / s.small_rate) for s in samples]


def _verdicts(samples):
    """The paired reading and the old rule's of the same samples."""
    return timing.paired_ratio(samples, cpu_bound=True), _min_of_each_side(samples)


def test_regime_a_lasting_slowdown_from_the_first_big_run_on(monkeypatch):
    # the core slows for good as the first big run starts, so only the first
    # small block is fast; the old rule holds it against every big run and
    # reads a linear sink at 12x, paired it is the first rep of three
    def slow_from_first_big(index):
        return index >= timing.SMALL_BLOCK

    samples = _regime_samples(monkeypatch, _linear, slow_from_first_big)
    # the first block's units straddle the slowdown and read the mean of both
    # states, (1 + _LOADED) / 2, so that rep is normalised by less than it bore
    straddle = (1 + _LOADED) / 2
    assert _per_rep(samples) == pytest.approx([4 * straddle, 4.0, 4.0])
    paired, old = _verdicts(samples)
    assert paired == pytest.approx(4.0) and paired < timing.QUADRATIC_RATIO
    assert old == pytest.approx(4 * _LOADED)
    samples = _regime_samples(monkeypatch, _quadratic, slow_from_first_big)
    assert _per_rep(samples) == pytest.approx([16 * straddle, 16.0, 16.0])
    paired, old = _verdicts(samples)
    assert paired == pytest.approx(16.0) and paired >= timing.QUADRATIC_RATIO
    assert old == pytest.approx(48.0)


def test_regime_a_sibling_through_the_small_blocks_that_idles_for_the_last_big_run(
    monkeypatch,
):
    # the ubuntu shape: a sibling shares the core until the last big run, so
    # the old rule holds the one fast big run against the slowed small blocks
    # and reads a quadratic sink at 5.3x; paired it is the last rep of three
    last_big = 3 * (timing.SMALL_BLOCK + 1) - 1

    def shared_until_last_big(index):
        return index < last_big

    samples = _regime_samples(monkeypatch, _quadratic, shared_until_last_big)
    assert _per_rep(samples) == pytest.approx([16.0, 16.0, 32 / 3])
    paired, old = _verdicts(samples)
    assert paired == pytest.approx(16.0) and paired >= timing.QUADRATIC_RATIO
    assert old == pytest.approx(16 / 3)
    samples = _regime_samples(monkeypatch, _linear, shared_until_last_big)
    assert _per_rep(samples) == pytest.approx([4.0, 4.0, 8 / 3])
    paired, old = _verdicts(samples)
    assert paired == pytest.approx(4.0) and paired < timing.QUADRATIC_RATIO
    assert old == pytest.approx(4 / 3)


def test_regime_a_fast_window_for_one_small_block(monkeypatch):
    # the macOS shape: one fast window that the second small block alone
    # gets; the old rule keeps it as the small side and reads a linear sink
    # at 12x, paired it is one rep of three
    second_block = range(timing.SMALL_BLOCK + 1, 2 * timing.SMALL_BLOCK + 1)

    def slow_except_second_block(index):
        return index not in second_block

    samples = _regime_samples(monkeypatch, _linear, slow_except_second_block)
    # the 8.0: the units beside the fast block straddle its edges and read the
    # mean of both states, so the block is normalised by 2x while it bore 1x;
    # the median rescues the verdict
    assert _per_rep(samples) == pytest.approx([6.0, 8.0, 4.0])
    paired, old = _verdicts(samples)
    assert paired == pytest.approx(6.0) and paired < timing.QUADRATIC_RATIO
    assert old == pytest.approx(12.0)
    samples = _regime_samples(monkeypatch, _quadratic, slow_except_second_block)
    assert _per_rep(samples) == pytest.approx([24.0, 32.0, 16.0])
    paired, old = _verdicts(samples)
    assert paired == pytest.approx(24.0) and paired >= timing.QUADRATIC_RATIO
    assert old == pytest.approx(48.0)


# === regimes beyond the recorded ones: benign, adversarial and broken clocks ===
# Each replays through the real measurement on the fake clock and pins the exact
# reading, the verdict, or the refusal of a sample that cannot be resolved.


def _phases(load):
    """A call's load as ``[(share, load), ...]``: one phase unless given more."""
    return load if isinstance(load, list) else [(1.0, load)]


def _replay(
    monkeypatch, sink, load_of_call, load_of_unit=None, clock=None, tamper=None
):
    """Samples of ``sink(n)`` through the real ``scaling_samples`` on a fake clock.

    ``load_of_call(index)`` is the load of the call at that index, or a list of
    ``(share, load)`` phases charged in turn; ``load_of_unit(index)`` the load
    of the unit measured before the call at ``index`` (that call's first load
    unless given); ``tamper(index, clock)`` runs before the call at ``index``.
    """
    clock, calls = clock or _FakeClock(), []
    if load_of_unit is None:

        def load_of_unit(index):
            return _phases(load_of_call(index))[0][1]

    def chunk():
        clock.load = load_of_unit(len(calls))
        clock.charge(_CLEAN_CHUNK)

    def op(n):
        index = len(calls)
        if tamper is not None:
            tamper(index, clock)
        calls.append(n)
        for share, load in _phases(load_of_call(index)):
            clock.load = load
            clock.charge(sink(n) * share)

    monkeypatch.setattr(timing, "time", clock)
    monkeypatch.setattr(timing, "_calibration_chunk", chunk)
    samples = timing.scaling_samples(op, 1, 4)
    assert len(calls) == 3 * (timing.SMALL_BLOCK + 1), calls
    return samples


def _big_runs():
    """The call indices of the three big runs."""
    return {rep * (timing.SMALL_BLOCK + 1) + timing.SMALL_BLOCK for rep in range(3)}


def _first_half_of_each_block(index):
    """Loaded for the first half of every small block, clean for the rest."""
    if index in _big_runs():
        return 1.0
    position = index % (timing.SMALL_BLOCK + 1)
    return _LOADED if position < timing.SMALL_BLOCK / 2 else 1.0


@pytest.mark.parametrize("load", [1.0, _LOADED])
def test_regime_a_calm_or_uniformly_loaded_machine_reads_the_sink_exactly(
    monkeypatch, load
):
    # the baseline: with every call and unit at one load the normalisation
    # cancels and both rules read the clean ratio
    samples = _replay(monkeypatch, _linear, lambda index: load)
    assert _per_rep(samples) == pytest.approx([4.0, 4.0, 4.0])
    assert _verdicts(samples) == pytest.approx((4.0, 4.0))
    samples = _replay(monkeypatch, _quadratic, lambda index: load)
    assert _verdicts(samples) == pytest.approx((16.0, 16.0))


def test_regime_a_load_confined_to_the_units_cancels(monkeypatch):
    # every unit loaded, every sample clean: the rates all read the loaded
    # rate, so the reference equals each rate and nothing is rescaled
    samples = _replay(monkeypatch, _linear, lambda i: 1.0, lambda i: _LOADED)
    for s in samples:
        assert s.small_rate == s.big_rate == pytest.approx(_LOADED * _CLEAN_CHUNK)
    assert _verdicts(samples) == pytest.approx((4.0, 4.0))
    samples = _replay(monkeypatch, _quadratic, lambda i: 1.0, lambda i: _LOADED)
    assert _verdicts(samples) == pytest.approx((16.0, 16.0))


def test_regime_a_load_confined_to_the_samples_of_both_sides_cancels(monkeypatch):
    # every sample loaded, every unit clean: both sides bear the same load, so
    # the raw ratio is the clean one and the clean units rescale by one
    samples = _replay(monkeypatch, _linear, lambda i: _LOADED, lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((4.0, 4.0))
    samples = _replay(monkeypatch, _quadratic, lambda i: _LOADED, lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((16.0, 16.0))


def test_regime_a_load_confined_to_one_side_is_the_limit_the_units_cannot_see(
    monkeypatch,
):
    # a load on for the samples of one side only and off for every unit leaves
    # no trace in the rates, so that side is read at face value, as the old
    # rule read it: pinned so a change claiming to close it must say how
    big_runs = _big_runs()

    def small_side_only(index):
        return 1.0 if index in big_runs else _LOADED

    samples = _replay(monkeypatch, _quadratic, small_side_only, lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((16 / _LOADED, 16 / _LOADED))
    samples = _replay(monkeypatch, _linear, small_side_only, lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((4 / _LOADED, 4 / _LOADED))

    def big_side_only(index):
        return _LOADED if index in big_runs else 1.0

    # the mirror image is a false red for a linear sink, never a pass
    samples = _replay(monkeypatch, _linear, big_side_only, lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((4 * _LOADED, 4 * _LOADED))
    assert timing.paired_ratio(samples, cpu_bound=True) >= timing.QUADRATIC_RATIO


def test_regime_a_drift_that_reverses_inside_a_rep_on_both_sides_cancels(
    monkeypatch,
):
    # loaded for the first half of every small block and of every big run:
    # both sides bear the same mean load and every unit reads the load of
    # what follows it, so the normalisation cancels exactly
    big_runs = _big_runs()

    def half_loaded(index):
        if index in big_runs:
            return [(0.5, _LOADED), (0.5, 1.0)]
        return _first_half_of_each_block(index)

    samples = _replay(monkeypatch, _linear, half_loaded)
    assert _per_rep(samples) == pytest.approx([4.0, 4.0, 4.0])
    assert _verdicts(samples) == pytest.approx((4.0, 4.0))
    samples = _replay(monkeypatch, _quadratic, half_loaded)
    assert _verdicts(samples) == pytest.approx((16.0, 16.0))


def test_regime_a_reversal_inside_the_small_blocks_only_misreads_by_the_straddle(
    monkeypatch,
):
    # loaded for the first half of every small block only: the block bore the
    # mean of both states and its units read it, but the big run's units read
    # clean and then the next block's load, so each rep is off by the straddle
    straddle = (1 + _LOADED) / 2
    samples = _replay(monkeypatch, _linear, _first_half_of_each_block)
    assert _verdicts(samples) == pytest.approx((4 / straddle, 4 / straddle))
    samples = _replay(monkeypatch, _quadratic, _first_half_of_each_block)
    assert _verdicts(samples) == pytest.approx((16 / straddle, 16 / straddle))
    # at the bar for a 3x load, under it beyond: the straddle at its worst,
    # the same under the old rule, pinned as the limit it is
    assert 16 / straddle >= timing.QUADRATIC_RATIO


def test_regime_a_small_block_under_the_floor_is_a_budget_on_the_big_run(
    monkeypatch,
):
    # the floor's stated limit: a clean small side under 0.1 s is read as
    # 0.1 s, so a quadratic sink is over the bar only from half the floor up;
    # hence every shipped probe keeps its small side at 2.5x the floor
    for clean_small in (0.04, 0.05, 0.1):
        samples = _replay(monkeypatch, lambda n: clean_small * n * n, lambda i: 1.0)
        expected = 16 * clean_small / max(clean_small, 0.1)
        assert timing.paired_ratio(samples, cpu_bound=True) == pytest.approx(expected)


def test_regime_a_sink_quadratic_only_above_a_size_reads_what_the_sizes_see(
    monkeypatch,
):
    # cost c * n plus c * (n - knee) ** 2 / knee above the knee: with the knee
    # at the small size the big run pays 4 + 9 and reads 13x; with the knee at
    # the big size neither pays and it reads 4x, so the sizes decide, not the rule
    def with_knee(knee):
        return lambda n: _CLEAN_SMALL * (n + max(0, n - knee) ** 2 / knee)

    samples = _replay(monkeypatch, with_knee(1), lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((13.0, 13.0))
    assert timing.paired_ratio(samples, cpu_bound=True) >= timing.QUADRATIC_RATIO
    samples = _replay(monkeypatch, with_knee(4), lambda i: 1.0)
    assert _verdicts(samples) == pytest.approx((4.0, 4.0))


class _QuantisedClock(_FakeClock):
    """``process_time`` in 15.6 ms steps, as Windows reports it: the first
    chunks of a unit read no elapsed time at all."""

    TICK = 0.015625

    def process_time(self):
        return self.cpu // self.TICK * self.TICK


def test_regime_a_quantised_cpu_clock_resolves_the_unit_and_keeps_the_verdict(
    monkeypatch,
):
    clock = _QuantisedClock()
    monkeypatch.setattr(timing, "time", clock)
    monkeypatch.setattr(
        timing, "_calibration_chunk", lambda: clock.charge(_CLEAN_CHUNK)
    )
    # the unit reads zero for its first chunks, then whole ticks, and ends on
    # a whole chunk past CALIBRATION_SECONDS: within one tick of the clean rate
    rate = timing.calibration_rate()
    assert clock.cpu - 1000.0 >= timing.CALIBRATION_SECONDS
    assert rate == pytest.approx(
        _CLEAN_CHUNK, rel=clock.TICK / timing.CALIBRATION_SECONDS
    )
    # a unit's elapsed overshoots by up to a tick (16% of 0.1 s) and a sample's
    # by a tick in 0.8 s, so a per-rep reading is within 20% and the verdicts
    # keep their 2x margin to the bar
    samples = _replay(monkeypatch, _linear, lambda i: 1.0, clock=_QuantisedClock())
    assert _per_rep(samples) == pytest.approx([4.0, 4.0, 4.0], rel=0.2)
    assert timing.paired_ratio(samples, cpu_bound=True) < timing.QUADRATIC_RATIO
    samples = _replay(monkeypatch, _quadratic, lambda i: 1.0, clock=_QuantisedClock())
    assert _per_rep(samples) == pytest.approx([16.0, 16.0, 16.0], rel=0.2)
    assert timing.paired_ratio(samples, cpu_bound=True) >= timing.QUADRATIC_RATIO


class _FrozenCpuClock(_FakeClock):
    """A CPU clock that never advances while the wall clock does."""

    def charge(self, clean_seconds):
        self.wall += clean_seconds * self.load


def test_regime_a_cpu_clock_that_stops_is_refused_not_spun_on(monkeypatch):
    clock = _FrozenCpuClock()
    monkeypatch.setattr(timing, "time", clock)
    monkeypatch.setattr(
        timing, "_calibration_chunk", lambda: clock.charge(_CLEAN_CHUNK)
    )
    with pytest.raises(ValueError, match="CPU clock advanced 0.000s"):
        timing.calibration_rate()
    # refused at the suite's hard deadline, not after an open-ended spin
    assert clock.wall - 2000.0 == pytest.approx(
        timing.hard_deadline_for(timing.CALIBRATION_SECONDS), abs=_CLEAN_CHUNK
    )
    with pytest.raises(ValueError, match="CPU clock"):
        _replay(monkeypatch, _linear, lambda i: 1.0, clock=_FrozenCpuClock())


def test_regime_a_clock_that_jumps_backwards_is_refused(monkeypatch):
    # inside a big run: the sample's CPU seconds go negative and the rule
    # refuses the run rather than read a negative ratio as linear
    def back_during_the_second_big_run(index, clock):
        if index == 2 * timing.SMALL_BLOCK + 1:
            clock.cpu -= 10.0

    samples = _replay(
        monkeypatch, _linear, lambda i: 1.0, tamper=back_during_the_second_big_run
    )
    assert samples[1].big_cpu < 0
    with pytest.raises(ValueError, match="unresolvable sample"):
        timing.paired_ratio(samples, cpu_bound=True)
    # inside a calibration unit: the unit refuses before any sample is taken
    clock = _FakeClock()
    monkeypatch.setattr(timing, "time", clock)

    def chunk_then_jump_back():
        clock.charge(_CLEAN_CHUNK)
        clock.cpu -= 1.0

    monkeypatch.setattr(timing, "_calibration_chunk", chunk_then_jump_back)
    with pytest.raises(ValueError, match="CPU clock advanced -"):
        timing.calibration_rate()


@pytest.mark.parametrize(
    "broken",
    [
        _sample(0.2, 0.0),
        _sample(0.2, -0.2),
        _sample(-0.2, 0.8),
        _sample(0.2, 0.8, big_rate=0.0),
        _sample(0.2, 0.8, small_rate=-0.001),
        _sample(float("nan"), 0.8),
        _sample(0.2, float("inf")),
        _sample(0.2, 0.8, big_wall=0.0),
    ],
    ids=[
        "big run read no CPU time",
        "big run read negative CPU time",
        "small block read negative CPU time",
        "zero rate",
        "negative rate",
        "nan reading",
        "infinite reading",
        "big run read no wall time",
    ],
)
def test_paired_ratio_refuses_a_sample_it_cannot_resolve(broken):
    # read as ratios these were 0.0, -0.67, 48 (floored), ZeroDivisionError, a
    # negative ratio, nan, inf and 4.0: a probe reports FIXED on most of them
    samples = [_sample(0.2, 0.8), broken, _sample(0.2, 0.8)]
    with pytest.raises(ValueError, match="unresolvable sample") as refusal:
        timing.paired_ratio(samples, cpu_bound=True)
    assert repr(broken) in str(refusal.value)
    with pytest.raises(ValueError, match="unresolvable sample"):
        timing.paired_ratio(samples)


def test_paired_ratio_keeps_a_small_block_under_resolution_on_the_floor():
    # a small block that read no CPU time at all is the floor's case, not a
    # refusal: the verdict is the budget on the big run, as on develop
    samples = [_sample(0.0, 0.3)] * 3
    assert timing.paired_ratio(samples, cpu_bound=True) == pytest.approx(3.0)
    samples = [_sample(0.0, 0.3, small_wall=0.0)] * 3
    assert timing.paired_ratio(samples) == pytest.approx(3.0)


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
