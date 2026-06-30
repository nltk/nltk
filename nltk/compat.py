# Natural Language Toolkit: Compatibility
#
# Copyright (C) 2001-2026 NLTK Project
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
from functools import wraps

# ======= Compatibility for datasets that care about Python versions ========

# The following datasets have a /PY3 subdirectory containing
# a full copy of the data which has been re-encoded or repickled.
DATA_UPDATES = []

_PY3_DATA_UPDATES = [os.path.join(*path_list) for path_list in DATA_UPDATES]


def add_py3_data(path):
    """Rewrite a corpus data path to use the ``/PY3`` subdirectory when available.

    Some NLTK corpora ship a ``/PY3`` subdirectory that contains data
    re-encoded or re-pickled for Python 3.  This function checks whether
    *path* refers to one of those corpora (via ``_PY3_DATA_UPDATES``) and, if
    so, inserts ``/PY3`` at the appropriate position in the path string.

    Args:
        path (str): The original corpus file path.

    Returns:
        str: The (possibly rewritten) path pointing to the ``/PY3`` variant,
        or the original *path* unchanged if no rewrite is needed.
    """
    for item in _PY3_DATA_UPDATES:
        if item in str(path) and "/PY3" not in str(path):
            pos = path.index(item) + len(item)
            if path[pos : pos + 4] == ".zip":
                pos += 4
            path = path[:pos] + "/PY3" + path[pos:]
            break
    return path


# for use in adding /PY3 to the second (filename) argument
# of the file pointers in data.py
def py3_data(init_func):
    """Decorator that rewrites the filename argument of a file-pointer initialiser to use ``/PY3`` data.

    Wraps *init_func* so that its second positional argument (the filename) is
    passed through :func:`add_py3_data` before the original function is called.
    This is used in ``nltk/data.py`` to transparently redirect corpus readers
    to the Python-3-compatible copy of a dataset.

    Args:
        init_func (Callable): The ``__init__`` (or similar) method to wrap.

    Returns:
        Callable: A wrapped version of *init_func* with the same signature,
        where the second positional argument is automatically rewritten.
    """

    def _decorator(*args, **kwargs):
        args = (args[0], add_py3_data(args[1])) + args[2:]
        return init_func(*args, **kwargs)

    return wraps(init_func)(_decorator)
