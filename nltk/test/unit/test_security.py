import os
import subprocess
import sys
import tempfile


def test_module_hijacking_prevention():
    """Ensure inline imports do not resolve from the current working directory."""
    with tempfile.TemporaryDirectory() as d:
        # 1. Attacker payload that would print a flag if imported
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('HIJACK_SUCCESS')\n")

        # 2. Victim script that triggers the vulnerable import
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                "from nltk.util import parallelize_preprocess\n"
                "list(parallelize_preprocess(str.upper, ['a'], processes=1))\n"
            )

        # 3. Ensure subprocess uses the local, patched NLTK repository
        env = os.environ.copy()
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        env["PYTHONPATH"] = repo_root + (
            os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
        )

        # 4. Execute in the isolated directory
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )

        # 5. Print raw output on failure for debugging
        if res.returncode != 0:
            print("--- SUBPROCESS STDOUT ---\n", res.stdout)
            print("--- SUBPROCESS STDERR ---\n", res.stderr)

        # 6. Verify the exploit was blocked
        assert (
            "HIJACK_SUCCESS" not in res.stdout
        ), "Security Failure: Malicious module was loaded from CWD."

        # 7. The script should fail with ImportError (this is expected and correct)
        #    The test verifies the failure mode is clean and informative
        assert res.returncode != 0, "Security measure should raise ImportError"
        assert (
            "Blocked import of joblib from current working directory" in res.stderr
        ), "Expected security error message not found"
        assert (
            "for security reasons" in res.stderr
        ), "Security error should include explanation"


def test_wordnet_app_reference_decode_rejects_wrong_types():
    """
    nltk.app.wordnet_app.Reference.decode() unpickles attacker-controlled,
    base64-encoded data straight from the wordnet browser's lookup_ URLs via
    RestrictedUnpickler. RestrictedUnpickler blocks class/function
    reconstruction, but it does not guarantee the *type* or *shape* of what
    it returns: pickle's built-in list/dict/int/etc. opcodes never go
    through the blocked path. Without validation, a single crafted
    lookup_<pickle> URL crashed the server, either directly (e.g. decoding
    to an int instead of a str crashed word.split(",") in
    page_from_reference()) or downstream (e.g. a synset_relations dict with
    non-set values crashed toggle_synset_relation()'s .add()/.remove()).
    Every such failure must surface as ValueError, since that's the only
    exception type the lookup_ route in do_GET catches.
    """
    import base64
    import pickle

    from nltk.app.wordnet_app import Reference

    # A legitimate reference still round-trips correctly.
    good = base64.urlsafe_b64encode(pickle.dumps(("dog", {}), -1)).decode()
    ref = Reference.decode(good)
    assert ref.word == "dog"
    assert ref.synset_relations == {}

    # Malformed references must be rejected here, rather than accepted and
    # left to crash downstream code. Covers: wrong type for word; wrong type
    # for synset_relations itself; a synset_relations dict whose keys or
    # values are the wrong type (including frozenset, which looks like a
    # valid set but lacks the .add()/.remove() that toggle_synset_relation()
    # needs, so it must be rejected too, not just non-set types); and
    # payloads that don't even unpack to a (word, synset_relations) pair (a
    # bare int isn't iterable at all; a 1-tuple/3-tuple is the wrong arity).
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

    # Also covers input that isn't valid base64/pickle data at all.
    for bad_string in ["not valid base64!!!", "", "====", "aGVsbG8="]:
        try:
            Reference.decode(bad_string)
            raise AssertionError(f"Reference.decode should reject {bad_string!r}")
        except ValueError:
            pass
