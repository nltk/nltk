# Natural Language Toolkit: tests for the suite's timing rule
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The timing rule the DoS budget and scaling tests rely on: a CPU-bound block
is charged its CPU time, so a descheduled interpreter does not inflate it, and
a waiting block is charged its wall time, so a hang that sleeps or blocks is
still seen. Real sleeps and real spinning, nothing mocked."""

import time

import pytest

from nltk.test.unit import timing


def spin(seconds):
    deadline = time.process_time() + seconds
    while time.process_time() < deadline:
        pass


def test_a_cpu_bound_block_is_charged_its_cpu_time_not_a_stall_beside_it():
    cpu, wall = timing.cpu_and_wall(lambda: (spin(0.2), time.sleep(0.05)))
    assert 0.15 <= cpu <= 0.35, cpu
    assert timing.charge(cpu, wall) == cpu


def test_a_waiting_block_is_charged_its_wall_time():
    cpu, wall = timing.cpu_and_wall(time.sleep, 0.2)
    assert wall >= 0.2 and cpu < 0.1, (cpu, wall)
    assert timing.charge(cpu, wall) == wall


def test_budget_passes_a_fast_block_that_was_descheduled_beside_its_work():
    # a stall shorter than the work, the shape a loaded runner injects: the
    # wall clock is over budget, the charged CPU time is not
    with timing.budget(0.45) as measured:
        spin(0.3)
        time.sleep(0.2)
    assert measured.charged == measured.cpu < 0.45 < measured.wall


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
    ok, best = timing.within_budget(lambda: spin(0.05), 0.5)
    assert ok and 0.02 <= best <= 0.2, best
    ok, best = timing.within_budget(lambda: time.sleep(0.3), 0.2, repeats=1)
    assert not ok and best >= 0.3, best


def test_scaling_ratio_counts_only_the_time_the_process_runs():
    # a linear op that sleeps beside its small run: the wall clock would read
    # 1.3x, CPU time reads the 4x it is
    def op(n):
        spin(n / 1_000_000)
        if n == 120_000:
            time.sleep(0.25)

    ratio = timing.scaling_ratio(op, 120_000, 480_000)
    assert 3.0 <= ratio <= 5.5, ratio


def test_scaling_ratio_still_sees_a_sink_that_waits_instead_of_computing():
    # one sleep of 0.3 s at the small size and 4.8 s at the big one: still
    # 8.5x if every wake-up is 0.3 s late, as under xdist on a 3-core runner
    def op(n):
        time.sleep(0.3 * (n / 1000) ** 2)

    ratio = timing.scaling_ratio(op, 1000, 4000)
    assert ratio >= timing.QUADRATIC_RATIO, ratio


def test_assert_subquadratic_separates_linear_from_quadratic_cpu_work():
    timing.assert_subquadratic(lambda n: spin(n / 1_000_000), 150_000, 600_000)
    with pytest.raises(AssertionError):
        timing.assert_subquadratic(
            lambda n: spin((n / 1_000_000) ** 2 * 4), 200_000, 800_000, reps=2
        )
