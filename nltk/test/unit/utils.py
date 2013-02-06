# -*- coding: utf-8 -*-
from __future__ import absolute_import
from unittest import TestCase
from functools import wraps
from nose.plugins.skip import SkipTest
from nltk.util import py26

def skip(reason):
    """
    Unconditionally skip a test.
    """
    def decorator(test_item):
        is_test_class = isinstance(test_item, type) and issubclass(test_item, TestCase)

        if is_test_class and py26():
            # Patch all test_ methods to raise SkipText exception.
            # This is necessary for Python 2.6 because its unittest
            # doesn't understand __unittest_skip__.
            for meth_name in (m for m in dir(test_item) if m.startswith('test_')):
                patched_method = skip(reason)(getattr(test_item, meth_name))
                setattr(test_item, meth_name, patched_method)

        if not is_test_class:
            @wraps(test_item)
            def skip_wrapper(*args, **kwargs):
                raise SkipTest(reason)
            skip_wrapper.__name__ = test_item.__name__
            test_item = skip_wrapper

        test_item.__unittest_skip__ = True
        test_item.__unittest_skip_why__ = reason
        return test_item
    return decorator


def skipIf(condition, reason):
    """
    Skip a test if the condition is true.
    """
    if condition:
        return skip(reason)
    return lambda obj: obj