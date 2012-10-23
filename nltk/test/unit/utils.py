# -*- coding: utf-8 -*-
from __future__ import absolute_import
from unittest import TestCase
from functools import wraps
from nose.plugins.skip import SkipTest

def skip(reason):
    """
    Unconditionally skip a test.
    """
    def decorator(test_item):
        if not (isinstance(test_item, type) and issubclass(test_item, TestCase)):
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