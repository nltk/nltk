#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pytest
import sys

NLTK_TEST_DIR = os.path.dirname(__file__)

if __name__ == "__main__":
    # allow passing extra options and running individual tests
    # Examples:
    #
    #    python runtests.py semantics.doctest
    #    python runtests.py semantics.doctest -v  # verbosity of 1
    #    python runtests.py -vv --durations=10  # show 10 slowest tests
    #
    # (TODO)
    #    python runtests.py --with-id -v
    #    python runtests.py --with-id -v nltk.featstruct

    args = sys.argv[1:]
    if not args:
        args = []

    # Running from the test directory allows pytest to recognize
    # the pytest.ini file
    os.chdir(NLTK_TEST_DIR)

    pytest.main(args)
