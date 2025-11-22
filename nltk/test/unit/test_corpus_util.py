"""
Tests for nltk.corpus.util module
"""

import pytest

from nltk.corpus.util import _make_bound_method


class TestMakeBoundMethod:
    """Tests for _make_bound_method function"""

    def test_creates_bound_method(self):
        """Test that _make_bound_method creates a proper bound method"""

        class TestClass:
            def __init__(self, value):
                self.value = value

        def test_func(self):
            return self.value * 2

        obj = TestClass(5)
        bound_method = _make_bound_method(test_func, obj)

        # verify it's callable
        assert callable(bound_method)

        # verify it returns the correct value
        assert bound_method() == 10

    def test_bound_method_has_correct_self(self):
        """Test that the bound method has correct self binding"""

        class Counter:
            def __init__(self):
                self.count = 0

        def increment(self):
            self.count += 1
            return self.count

        obj = Counter()
        bound_increment = _make_bound_method(increment, obj)

        # call multiple times and verify state changes
        assert bound_increment() == 1
        assert bound_increment() == 2
        assert obj.count == 2

    def test_bound_method_with_arguments(self):
        """Test that bound method works with additional arguments"""

        class Multiplier:
            def __init__(self, base):
                self.base = base

        def multiply(self, factor):
            return self.base * factor

        obj = Multiplier(3)
        bound_multiply = _make_bound_method(multiply, obj)

        assert bound_multiply(4) == 12
        assert bound_multiply(10) == 30
