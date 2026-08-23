import multiprocessing
import sys


def _mp_ctx():
    """Return multiprocessing context suitable for tests on this platform."""
    # macOS/Windows: prefer spawn for stability with pooled workers.
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return multiprocessing.get_context("spawn")

    # Other platforms: prefer fork when available, else fall back to spawn.
    available = set(multiprocessing.get_all_start_methods())
    method = "fork" if "fork" in available else "spawn"
    return multiprocessing.get_context(method)
