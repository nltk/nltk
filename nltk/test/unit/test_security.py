import os
import subprocess
import sys
import tempfile


def test_module_hijacking_prevention():
    """Ensure inline imports do not resolve from the current working directory."""
    with tempfile.TemporaryDirectory() as d:
        # 1. Attacker payload that prints a flag when imported
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('HIJACK_SUCCESS')\n")

        # 2. Victim script explicitly importing the function to avoid NLTK namespace collisions
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

        # 5. Print raw output on failure so pytest captures it fully without truncation
        if "HIJACK_SUCCESS" in res.stdout or res.returncode != 0:
            print("--- SUBPROCESS STDOUT ---\n", res.stdout)
            print("--- SUBPROCESS STDERR ---\n", res.stderr)

        # 6. Verify the exploit failed and the script executed normally
        assert (
            "HIJACK_SUCCESS" not in res.stdout
        ), "Security Failure: Loaded module from CWD."
        assert res.returncode == 0, "Victim script failed unexpectedly."


def test_wordnet_app_reference_decode_rejects_wrong_types():
    """
    nltk.app.wordnet_app.Reference.decode() unpickles attacker-controlled,
    base64-encoded data straight from the wordnet browser's lookup_ URLs via
    RestrictedUnpickler. RestrictedUnpickler blocks class/function
    reconstruction, but it does not guarantee the *type* of what it returns:
    pickle's built-in list/dict/int/etc. opcodes never go through the
    blocked path. Without a type check, a single crafted lookup_<pickle> URL
    (e.g. decoding to an int instead of a str) crashed the server with an
    uncaught AttributeError in page_from_reference()'s word.split(",").
    """
    import base64
    import pickle

    from nltk.app.wordnet_app import Reference

    # A legitimate reference still round-trips correctly.
    good = base64.urlsafe_b64encode(pickle.dumps(("dog", {}), -1)).decode()
    ref = Reference.decode(good)
    assert ref.word == "dog"
    assert ref.synset_relations == {}

    # Malformed references (wrong type for word or synset_relations) must be
    # rejected here, rather than accepted and left to crash downstream code.
    for bad_payload in [(42, {}), ([[[1]]], {}), (None, {}), ("dog", [])]:
        bad = base64.urlsafe_b64encode(pickle.dumps(bad_payload, -1)).decode()
        try:
            Reference.decode(bad)
            raise AssertionError(f"Reference.decode should reject {bad_payload!r}")
        except ValueError:
            pass
