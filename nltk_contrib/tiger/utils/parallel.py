# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Support module for using the `multiprocessing` module."""

try:
    import processing as multiprocessing
    HAS_PROCESSING = True
except ImportError:
    try:
        import multiprocessing
        HAS_PROCESSING = True
    except ImportError:
        HAS_PROCESSING = False    

__all__ = ["use_parallel_processing"]

if HAS_PROCESSING:
    CPU_COUNT = multiprocessing.cpuCount()
else:
    CPU_COUNT = 1
    multiprocessing = None


def use_parallel_processing():
    """Returns `True` if the query evaluator can run parallelized, `False` otherwise.
    
    For the parallelized version, two conditions have to be fulfilled:
     * the `multiprocessing` module is present
     * the system has more than one CPU
    """
    return HAS_PROCESSING and CPU_COUNT > 1

