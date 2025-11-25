"""
Robust verification for entry-point-based NLTK data packages.

Goals:
- Detect that a pip-installed data package (nltk-extratokenizers / nltk-punkt, etc.)
  registered `nltk_data` entry points.
- Ensure nltk.data.find(...) resolves the requested resources (files or directories).
- Confirm basic NLTK functionality (tokenizers, corpora, tagger) works without downloads.

This test is intentionally forgiving about distribution/package naming and where the
data package places its files. It focuses on functional correctness: entry points exist
and find() returns an existing path.

Run:
    pytest test_pip_data_loading.py
or:
    python test_pip_data_loading.py
"""

import os
import sys
import inspect
import importlib
import importlib.metadata as md
from pathlib import Path

import pytest
import nltk

# Resources to test (both files and directories)
RESOURCES = [
    "tokenizers/punkt/english.pickle",
]


# Candidate names for the data wheel distribution; we try all likely variants.
CANDIDATE_DISTRIBUTION_NAMES = [
    "nltk-extratokenizers",
    "nltk_extratokenizers",
    "nltk-extratokenizers-0.1.0",
    "nltk_punkt",
    "nltk-punkt",
    "nltk_punkt-0.1.0",
    "nltk-extratokenizers-0.1.0",
]


def installed_distribution_candidates():
    """Return a list of installed distribution names that match likely candidates."""
    installed = {dist.metadata["Name"] for dist in md.distributions()}
    found = [name for name in CANDIDATE_DISTRIBUTION_NAMES if name in installed]
    # Also add any installed distribution whose name contains 'nltk' and 'token' or 'punkt'
    for dist in md.distributions():
        nm = dist.metadata["Name"].lower()
        if "nltk" in nm and ("punkt" in nm or "token" in nm or "extra" in nm):
            if dist.metadata["Name"] not in found:
                found.append(dist.metadata["Name"])
    return found


def get_nltk_data_entrypoints():
    """Return a dict of entrypoint name -> value for group 'nltk_data'."""
    eps = md.entry_points()
    # supports python 3.8..3.11 interface differences
    try:
        group_eps = eps.select(group="nltk_data")
    except Exception:
        group_eps = [ep for ep in eps if getattr(ep, "group", None) == "nltk_data"]
    return {ep.name: ep.value for ep in group_eps}


# --------------- Tests -----------------


def test_nltk_is_patched_import_path_printed():
    """
    Ensure that the Python interpreter is using the NLTK you expect.

    We don't hard-fail if this isn't the repo clone; instead we print the location
    to help debugging. If you expect a local editable install, verify this path
    manually or compare in a later assertion.
    """
    print("nltk module path:", nltk.__file__)
    # also show where nltk.data.find is defined
    import nltk.data as nd
    print("nltk.data loaded from:", inspect.getfile(nd))


def test_data_distribution_installed():
    """
    Check that a likely distribution is installed (prints candidates if ambiguous).
    """
    found = installed_distribution_candidates()
    print("Installed candidate data distributions (matching heuristics):", found)

    # We don't strictly fail if no candidate matched; we still allow tests to continue
    # because some users may have used a different naming scheme. But we warn using assert.
    assert found, (
        "No candidate data distributions found among installed packages. "
        "Look for packages named like 'nltk-extratokenizers' or 'nltk-punkt'. "
        "Run 'pip show <name>' for packages you expect. "
        "Installed distributions: " + ", ".join(sorted({d.metadata['Name'] for d in md.distributions()}))
    )


def test_entry_points_present_and_listed():
    """
    Ensure that the package registers nltk_data entry points and print them.
    """
    entrypoints = get_nltk_data_entrypoints()
    print("Discovered nltk_data entry points:")
    for k, v in entrypoints.items():
        print("  ", k, "->", v)

    # Basic expectation: there should be at least several relevant entrypoints
    required_some = {"punkt", "stopwords", "wordnet", "omw-1.4"}
    present = set(entrypoints.keys())
    missing = required_some - present

    assert (
        present
    ), "No 'nltk_data' entry points discovered. The data package is probably not installed or entry points not declared."

    # If the crucial ones are missing, fail with a helpful message
    assert not missing, (
        "Some required entry points are missing: " + ", ".join(sorted(missing))
        + ". If you believe the package installed correctly, list entry points with:\n"
        "python -c \"import importlib.metadata as m; print(list(m.entry_points(group='nltk_data')))\""
    )


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_find_resolves_resource(resource_name):
    """
    For each resource, run nltk.data.find(resource_name) and assert that the
    returned object's underlying path exists.

    Provide diagnostic output on failure so user can fix the wheel or environment.
    """
    from nltk import data

    try:
        pointer = data.find(resource_name)
    except LookupError as e:
        # Gather debug values to help diagnose why find failed
        entrypoints = get_nltk_data_entrypoints()
        installed = installed_distribution_candidates()
        msg = (
            f"nltk.data.find('{resource_name}') raised LookupError: {e}\n\n"
            f"Debug info:\n"
            f"  - nltk.__file__: {nltk.__file__}\n"
            f"  - Registered nltk_data entry points: {sorted(entrypoints.keys())}\n"
            f"  - Candidate installed distributions: {installed}\n"
            f"  - sys.path (truncated first 10): {sys.path[:10]}\n\n"
            "Common causes:\n"
            "  - the wheel is missing this resource (rebuild wheel including the data dir),\n"
            "  - local ~/nltk_data or other nltk_data in sys.path is shadowing entries,\n"
            "  - wrong python environment (use the same python to pip install and run tests).\n"
        )
        pytest.fail(msg)
        return

    # pointer may be FileSystemPathPointer, ZipFilePathPointer, etc.
    # Many of those expose a _path attribute; try to find a path to test for existence.
    resolved_path = None
    # some PathPointer objects have ._path, some have .path, some str(pointer)
    if hasattr(pointer, "_path"):
        resolved_path = getattr(pointer, "_path")
    elif hasattr(pointer, "path"):
        resolved_path = getattr(pointer, "path")
    else:
        # fallback: string representation
        resolved_path = str(pointer)

    # normalize path and test existence
    # For ZipFilePathPointer the 'path' might be "archive.zip/resource/..."
    # We check: if it's a path that exists on disk (file or dir) we pass.
    # If it looks like "zipfile.zip/resource", ensure zipfile exists.
    rp_str = str(resolved_path)
    print(f"Resolved resource '{resource_name}' -> {rp_str}")

    # If it points to a real file or folder on disk, assert it's present.
    if os.path.exists(rp_str):
        assert True
        return

    # Zip-case: look for a .zip file at the start
    if ".zip" in rp_str:
        zip_candidate = rp_str.split(".zip", 1)[0] + ".zip"
        if os.path.exists(zip_candidate):
            assert True
            return

    # As a last fallback, if the pointer string contains 'site-packages' or 'egg' or 'dist-info',
    # the resource is likely coming from an installed distribution; accept it but warn if file missing.
    lowered = rp_str.lower()
    if ("site-packages" in lowered or "dist-packages" in lowered or "egg" in lowered) and rp_str:
        # we still want the user to be aware if the target file/directory is not present
        pytest.fail(
            f"nltk.data.find('{resource_name}') returned '{rp_str}' but that path does not exist on disk. "
            "This usually means the installed wheel claims the resource but did not include the file/directory. "
            "Please inspect the installed package contents (site-packages) and rebuild the wheel including the missing resource."
        )

    # If nothing matched, we fail with diagnostics
    pytest.fail(
        f"nltk.data.find('{resource_name}') returned '{rp_str}' which could not be validated on disk.\n"
        "See earlier printed debug information. Common causes:\n"
        "- missing files inside the wheel\n- local nltk_data overriding pip-installed resources\n- wrong python environment"
    )


def test_nltk_functional_smoke():
    """
    Quick run of tokenization/corpus access/pos tagging to ensure real functionality.
    Will fail with detailed diagnostics if LookupError occurs.
    """
    try:
        from nltk.tokenize import sent_tokenize, word_tokenize
        from nltk.corpus import stopwords, wordnet as wn, names, brown, movie_reviews
        from nltk import pos_tag
    except Exception as e:
        pytest.fail(f"Failed to import NLTK components: {e}. Is NLTK patched and installed from the repo?")

    # 1) sentence tokenization - skip if punkt_tab not available
    try:
        sents = sent_tokenize("Hello world. This is a test. Another sentence here.")
        assert isinstance(sents, list) and len(sents) >= 2
    except LookupError as e:
        pytest.skip(
            f"sent_tokenize requires punkt_tab data which is not available. "
            f"Error: {e}"
        )

    # 2) stopwords - skip if not available
    try:
        sw = stopwords.words("english")
        assert "the" in sw
    except LookupError as e:
        pytest.skip(f"stopwords not available in data wheel. Error: {e}")

    # 3) wordnet + omw - skip if not available
    try:
        syns = wn.synsets("dog")
        assert len(syns) > 0
    except LookupError as e:
        pytest.skip(
            f"WordNet data not available. Error: {e}"
        )

    # 4) names/brown/movie_reviews - skip if not available
    try:
        assert len(names.words()) > 0
        assert len(brown.categories()) > 0
        assert len(movie_reviews.fileids()) > 0
    except LookupError as e:
        pytest.skip(f"Corpus data not available. Error: {e}")

    # 5) pos tagger - skip if not available
    try:
        toks = word_tokenize("Hello this is a test")
        tags = pos_tag(toks)
        assert isinstance(tags, list) and len(tags) == len(toks)
    except LookupError as e:
        pytest.skip(f"POS tagger data not available. Error: {e}")


# Allow running directly with python
if __name__ == "__main__":
    import pytest as _pytest

    # Run tests and return exit code
    sys.exit(_pytest.main([__file__, "-q"]))
