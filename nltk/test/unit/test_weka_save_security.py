"""
Regression tests for the file-write hardening in ``nltk.classify.weka``
(GHSA-8mgp-746c-j5xp).

``ARFF_Formatter.write`` opened a caller-supplied ``outfile`` path with a bare
``open()``, so ARFF data could be written to any path outside the allowed NLTK
data roots. The write is now routed through the ``nltk.pathsec`` sandbox, which
refuses an out-of-sandbox destination before any bytes are written.

Coverage is deliberately layered so a regression cannot slip through any single
check:

* the exploit itself, end-to-end through ``ARFF_Formatter.write``, in several
  escape shapes: an absolute path outside the sandbox, a ``..`` traversal that
  starts inside the root and climbs out, and an in-root symlink whose target is
  outside (each defeats a naive prefix check but not pathsec's realpath /
  ``O_NOFOLLOW`` validation);
* a runtime spy proving the write actually *calls* ``pathsec_open`` with the
  caller's path, not merely that the module imports it;
* a bytecode guard on ``write.__code__.co_names`` proving the compiled function
  references ``pathsec_open`` and never a bare ``open`` / ``builtins.open``,
  robust against source reformatting or aliasing that a substring grep misses.

The ``pathsec_sandbox`` fixture (nltk/test/unit/conftest.py) supplies both a
trusted ``root`` and an ``outside`` dir. The outside dir lives under the real
``$HOME``, never a temp dir: a private per-user system temp is itself an allowed
pathsec root on macOS, which would make a temp target a false "outside".
"""

import os
from pathlib import Path

import pytest

import nltk.pathsec as pathsec

# The ``pathsec_sandbox`` / ``restricted_sandbox`` fixtures come from
# nltk/test/unit/conftest.py.


def test_arff_formatter_write_refuses_outside_path(pathsec_sandbox):
    """weka.ARFF_Formatter.write: a caller-supplied ``outfile`` path outside the
    sandbox must be refused before any data is written."""
    from nltk.classify.weka import ARFF_Formatter

    target_file = pathsec_sandbox.outside / "attack.arff"

    # NEGATIVE CONTROL: prove the target is genuinely outside every root.
    with pytest.raises(PermissionError):
        pathsec.open(str(target_file), "w")

    # ATTACK: write() to an outside path string.
    formatter = ARFF_Formatter(["yes", "no"], [("f1", "NUMERIC")])
    with pytest.raises(PermissionError):
        formatter.write(str(target_file), [])

    # Containment: nothing was written outside the sandbox.
    assert not target_file.exists()


@pytest.mark.parametrize("shape", ["traversal", "symlink"])
def test_arff_formatter_write_refuses_escape_shapes(pathsec_sandbox, shape):
    """weka.ARFF_Formatter.write must refuse escapes that resolve outside the
    sandbox even though the literal path begins inside the trusted root:

    * ``traversal``: a path under the root with enough ``..`` segments to climb
      above every allowed root;
    * ``symlink``: an in-root symlink whose target is the outside dir, so a
      write "into" it would land the bytes outside the sandbox.

    Both bypass a naive ``startswith(root)`` check but not pathsec's
    realpath / ``O_NOFOLLOW`` validation.
    """
    from nltk.classify.weka import ARFF_Formatter

    root, outside = pathsec_sandbox
    if shape == "traversal":
        # A path that textually begins inside the trusted root but, via ``..``,
        # resolves to the (writable) outside dir. A naive startswith(root) check
        # is satisfied; pathsec's realpath validation is not. The relative path is
        # computed from the *realpath* of each dir so the ``..`` count matches the
        # physical tree (macOS resolves /var -> /private/var, which would
        # otherwise skew a lexical relpath). Landing on a writable target is
        # deliberate: a leak here is pathsec failing to refuse, not the OS
        # refusing an unwritable ancestor.
        real_root = os.path.realpath(str(root))
        rel = os.path.relpath(os.path.realpath(str(outside)), start=real_root)
        target_file = Path(real_root) / rel / "attack.arff"
        leaked = outside / "attack.arff"
    else:  # symlink
        link = root / "evil_link"
        os.symlink(str(outside), str(link))
        target_file = link / "attack.arff"
        leaked = outside / "attack.arff"

    formatter = ARFF_Formatter(["yes", "no"], [("f1", "NUMERIC")])
    with pytest.raises(PermissionError):
        formatter.write(str(target_file), [])
    assert not leaked.exists(), "escape must not have written outside the sandbox"


def test_arff_formatter_write_accepts_in_sandbox_path(restricted_sandbox):
    """A destination inside an allowed data root is written normally (so the guard
    does not break the legitimate path), with LF line endings so the ARFF file is
    byte-identical across platforms."""
    from nltk.classify.weka import ARFF_Formatter

    target = os.path.join(restricted_sandbox, "ok.arff")
    formatter = ARFF_Formatter(["yes", "no"], [("f1", "NUMERIC")])
    formatter.write(target, [])
    assert os.path.exists(target)
    assert b"\r" not in Path(target).read_bytes(), "ARFF write must be LF-only"


def test_arff_write_calls_pathsec_open_at_runtime(restricted_sandbox, monkeypatch):
    """Runtime proof (not a substring grep): ``ARFF_Formatter.write`` must route
    its output through ``pathsec_open``. We spy on the name the module actually
    binds and assert the write went through it exactly once, with the caller's
    ``outfile``. A revert to a bare ``open()`` leaves the spy uncalled."""
    from nltk.classify import weka
    from nltk.classify.weka import ARFF_Formatter

    calls = []
    real = weka.pathsec_open

    def spy(path, *args, **kwargs):
        calls.append(path)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(weka, "pathsec_open", spy)

    target = os.path.join(restricted_sandbox, "spy.arff")
    ARFF_Formatter(["yes", "no"], [("f1", "NUMERIC")]).write(target, [])
    assert calls == [target], "write() must open its output via pathsec_open once"
    assert os.path.exists(target)


def test_arff_write_bytecode_references_pathsec_not_bare_open():
    """Leak-proof static guard at the *bytecode* level: the compiled
    ``ARFF_Formatter.write`` must reference the ``pathsec_open`` global and must
    NOT reference a bare ``open`` (a global ``open(...)`` or the ``open``
    attribute of ``builtins.open``). ``co_names`` lists every global/attribute
    name the function body references, so this catches a revert to ``open(...)``
    regardless of source formatting, aliasing, or comments a substring grep would
    miss."""
    from nltk.classify.weka import ARFF_Formatter

    names = ARFF_Formatter.write.__code__.co_names
    assert "pathsec_open" in names, "write() must reference pathsec_open"
    assert "open" not in names, (
        "write() references a bare 'open'; the output sink must go through "
        "pathsec_open, not open() / builtins.open()"
    )
