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


def test_cpu_time_is_the_work_and_the_charge_rule_is_deterministic():
    cpu, wall = timing.cpu_and_wall(lambda: (spin(0.2), time.sleep(0.05)))
    assert 0.15 <= cpu <= 0.35 and wall >= cpu + 0.04, (cpu, wall)
    # the rule itself, on fixed numbers: a quarter of the wall time on the CPU
    # is still judged as work (4x contention), less is judged as waiting
    assert timing.charge(0.30, 1.0) == 0.30
    assert timing.charge(0.20, 1.0) == 1.0
    assert timing.charge(0.20, 1.0, cpu_bound=True) == 0.20
    assert timing.charge(0.90, 1.0, cpu_bound=False) == 1.0


def test_a_waiting_block_is_charged_its_wall_time():
    cpu, wall = timing.cpu_and_wall(time.sleep, 0.2)
    assert wall >= 0.2 and cpu < 0.1, (cpu, wall)
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
    ok, best = timing.within_budget(lambda: spin(0.05), 0.5)
    assert ok and 0.02 <= best <= 0.2, best
    ok, best = timing.within_budget(lambda: time.sleep(0.3), 0.2, repeats=1)
    assert not ok and best >= 0.3, best


def test_assert_subquadratic_separates_linear_from_quadratic_cpu_work():
    timing.assert_subquadratic(lambda n: spin(n / 1_000_000), 150_000, 600_000)
    with pytest.raises(AssertionError):
        timing.assert_subquadratic(
            lambda n: spin((n / 1_000_000) ** 2 * 4), 200_000, 800_000, reps=2
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
    run = timing.run_in_process(_spin_child, (0.3,), budget=5.0)
    assert run.finished and run.exitcode == 0, run
    assert run.cpu is not None and run.charged == run.cpu, run
    assert run.cpu >= 0.25, run  # the child's own clock, not the parent's
    assert run.within_budget


def test_a_child_over_budget_fails_whether_it_spins_or_sleeps():
    spinning = timing.run_in_process(_spin_child, (0.5,), budget=0.2)
    sleeping = timing.run_in_process(_sleep_child, (0.5,), budget=0.2)
    assert spinning.finished and not spinning.within_budget, spinning
    assert sleeping.finished and not sleeping.within_budget, sleeping
    assert sleeping.charged == sleeping.wall >= 0.5, sleeping


def test_a_hanging_child_is_terminated_at_the_hard_deadline():
    run = timing.run_in_process(_sleep_child, (30,), budget=0.2, hard_deadline=1.0)
    assert not run.finished and not run.within_budget, run
    assert run.wall < 10, run


def test_a_child_exit_code_is_reported_with_its_cpu_time():
    run = timing.run_in_process(_exit_child, (3,), budget=5.0)
    assert run.finished and run.exitcode == 3, run
    assert run.cpu is not None and run.within_budget, run


def test_finishes_within_charges_a_thread_its_cpu_time():
    finished, exc, charged = timing.finishes_within(0.5, lambda: spin(0.2))
    assert finished and exc is None and 0.15 <= charged < 0.5, (finished, charged)
    finished, exc, charged = timing.finishes_within(0.2, lambda: time.sleep(0.4))
    assert not finished and charged >= 0.4, (finished, charged)
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
