import os
import subprocess
import sys
import tempfile

import pytest


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="PYTHONSAFEPATH / -P exist only on Python 3.11+.",
)
def test_safe_path_blocks_cwd_import():
    """
    NLTK's CI runs with PYTHONSAFEPATH=1 (see .github/workflows/ci.yml and the
    "Module import hijacking" section of SECURITY.md) so the interpreter does
    not auto-prepend the current working directory to sys.path. A module placed
    in the CWD must therefore NOT be importable, mitigating CWD module
    hijacking (CWE-426).

    Runs a child interpreter (inheriting the ambient PYTHONSAFEPATH) whose CWD
    contains a decoy module and asserts the decoy cannot be imported.
    """
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "cwd_decoy.py"), "w") as f:
            f.write("print('DECOY_IMPORTED')\n")

        res = subprocess.run(
            [sys.executable, "-c", "import cwd_decoy"],
            cwd=d,
            env=os.environ.copy(),  # inherits PYTHONSAFEPATH from CI
            capture_output=True,
            text=True,
        )

    assert res.returncode != 0, (
        "CWD module was importable: PYTHONSAFEPATH / -P is not in effect.\n"
        f"stdout: {res.stdout!r}\nstderr: {res.stderr!r}"
    )
    assert "DECOY_IMPORTED" not in res.stdout


def test_wordnet_app_reference_decode_rejects_wrong_types():
    """
    nltk.app.wordnet_app.Reference.decode() unpickles attacker-controlled,
    base64-encoded data straight from the wordnet browser's lookup_ URLs via
    RestrictedUnpickler. Every malformed input must surface as ValueError,
    since that's the only exception type the lookup_ route in do_GET catches.
    """
    import base64
    import pickle

    from nltk.app.wordnet_app import Reference

    good = base64.urlsafe_b64encode(pickle.dumps(("dog", {}), -1)).decode()
    ref = Reference.decode(good)
    assert ref.word == "dog"
    assert ref.synset_relations == {}

    bad_payloads = [
        (42, {}),
        ([[[1]]], {}),
        (None, {}),
        ("dog", []),
        ("dog", {"dog.n.01": ["not", "a", "set"]}),
        ("dog", {"dog.n.01": frozenset()}),
        ("dog", {42: {"hypernym"}}),
        42,
        ("dog",),
        ("dog", {}, "extra"),
    ]
    for bad_payload in bad_payloads:
        bad = base64.urlsafe_b64encode(pickle.dumps(bad_payload, -1)).decode()
        try:
            Reference.decode(bad)
            raise AssertionError(f"Reference.decode should reject {bad_payload!r}")
        except ValueError:
            pass

    for bad_string in ["not valid base64!!!", "", "====", "aGVsbG8="]:
        try:
            Reference.decode(bad_string)
            raise AssertionError(f"Reference.decode should reject {bad_string!r}")
        except ValueError:
            pass
