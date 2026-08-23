import multiprocessing
import sys


def _mp_ctx():
    """Cross-platform multiprocessing context for test subprocess workers."""
    return multiprocessing.get_context(
        "spawn" if sys.platform.startswith("win") else "fork"
    )
