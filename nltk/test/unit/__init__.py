import multiprocessing
import sys


def _mp_ctx():
    # macOS + newer Python versions are more fragile with fork in pooled workers.
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return multiprocessing.get_context("spawn")
    return multiprocessing.get_context("fork")
