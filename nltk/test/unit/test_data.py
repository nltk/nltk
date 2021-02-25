import nltk.data
import pytest


class TestData:
    def test_find_raises_exception(self):
        with pytest.raises(LookupError):
            nltk.data.find('no_such_resource/foo')

    def test_find_raises_exception_with_full_resource_name(self):
        no_such_thing = 'no_such_thing/bar'

        with pytest.raises(LookupError) as exc:
            nltk.data.find(no_such_thing)
            assert no_such_thing in str(exc), 'Exception message does not include full resource name'
