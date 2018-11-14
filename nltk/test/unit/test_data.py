import unittest
import nltk.data
from nose.tools import assert_raises


class TestData(unittest.TestCase):
    def test_find_raises_exception(self):

        with assert_raises(LookupError) as context:
            nltk.data.find('no_such_resource/foo')

        assert type(context.exception) == LookupError, 'Unexpected exception raised'

    def test_find_raises_exception_with_full_resource_name(self):
        no_such_thing = 'no_such_thing/bar'

        with assert_raises(LookupError) as context:
            nltk.data.find(no_such_thing)

        assert no_such_thing in str(
            context.exception
        ), 'Exception message does not include full resource name'
