import pytest

import nltk.data


def test_find_raises_exception():
    with pytest.raises(LookupError):
        nltk.data.find("no_such_resource/foo")


def test_find_raises_exception_with_full_resource_name():
    no_such_thing = "no_such_thing/bar"
    with pytest.raises(LookupError) as exc:
        nltk.data.find(no_such_thing)
    assert no_such_thing in str(exc.value)


def test_find_missing_entry_in_installed_package_demotes_download_hint():
    # Uses a well-known corpus expected to be present in CI.
    try:
        assert nltk.data.find("corpora/stopwords/english").file_size() > 0
    except LookupError:
        pytest.skip("stopwords corpus not available in this test environment")

    with pytest.raises(LookupError) as exc:
        nltk.data.find("corpora/stopwords/spanglish")

    s = str(exc.value)

    # Must reference the specific missing resource that was requested.
    assert "Attempted to load 'corpora/stopwords/spanglish'" in s

    # Error must not misleadingly claim that the entire 'stopwords' resource is missing.
    assert "Resource 'stopwords' not found" not in s

    # Downloader hint should remain present.
    assert "nltk.download('stopwords')" in s
