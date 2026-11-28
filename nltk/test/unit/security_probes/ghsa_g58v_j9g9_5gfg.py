import os
import tempfile

import nltk.data
from nltk.corpus.reader.api import CorpusReader

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-g58v-j9g9-5gfg")
def probe_ghsa_g58v_j9g9_5gfg():
    """Verify CorpusReader path resolution prevents symlink traversals outside

    the designated corpus root directory (GHSA-g58v-j9g9-5gfg).
    """
    with tempfile.TemporaryDirectory() as auth_dir, tempfile.TemporaryDirectory() as unauth_dir:
        auth_real = os.path.realpath(auth_dir)
        unauth_real = os.path.realpath(unauth_dir)

        orig_path = list(nltk.data.path)
        nltk.data.path.extend([auth_real, unauth_real])

        try:
            root_dir = os.path.join(auth_real, "corpus_root")
            os.makedirs(root_dir, exist_ok=True)

            target_file = os.path.join(unauth_real, "secret.txt")
            with open(target_file, "w") as f:
                f.write("sensitive content")

            symlink_path = os.path.join(root_dir, "symlink_dir")
            os.symlink(unauth_real, symlink_path)

            reader = CorpusReader(root_dir, r".*")

            try:
                resolved = reader.abspath(os.path.join("symlink_dir", "secret.txt"))
                return VULNERABLE, f"Symlink escape permitted: {resolved}"
            except (PermissionError, ValueError) as e:
                return FIXED, f"Symlink escape blocked by path containment: {e}"
        finally:
            nltk.data.path = orig_path
