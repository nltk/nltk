from nltk.internals import find_binary, find_jar


def check_binary(binary: str, **args):
    """Skip a test via `pytest.skip` if the `binary` executable is not found.
    Keyword arguments are passed to `nltk.internals.find_binary`."""
    import pytest

    try:
        path = find_binary(binary, **args)
    except LookupError:
        pytest.skip(f"Skipping test because the {binary} binary was not found.")
    from nltk.pathsec import untrusted_executable_reason

    # the doctests run the tool through the trusted spawn, so a found binary it
    # refuses (apt's or Homebrew's dot, a link whose text climbs with '..')
    # skips with the reason; the real-Graphviz tests assert that refusal
    reason = untrusted_executable_reason(path)
    if reason is not None:
        pytest.skip(
            f"Skipping test because the {binary} binary at {path!r} is refused by "
            f"the trusted spawn: {reason}"
        )


def check_jar(name_pattern: str, **args):
    """Skip a test via `pytest.skip` if the `name_pattern` jar is not found.
    Keyword arguments are passed to `nltk.internals.find_jar`.

    TODO: Investigate why the CoreNLP tests that rely on this check_jar failed
    on the CI. https://github.com/nltk/nltk/pull/3060#issuecomment-1268355108
    """
    import pytest

    pytest.skip(
        "Skipping test because the doctests requiring jars are inconsistent on the CI."
    )
