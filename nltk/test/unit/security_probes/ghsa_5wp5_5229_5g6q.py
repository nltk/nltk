"""GHSA-5wp5-5229-5g6q [high] -- Missing Post-Download Integrity Verification Allows Malicious Package Injection"""

import hashlib
import os
import shutil
import tempfile
import zipfile

from nltk import pathsec

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-5wp5-5229-5g6q")
def _downloader_integrity():
    """Download a package whose bytes do not match its declared sha256.

    Served over file:// (offline), a tampered archive must be refused before it
    is committed to the install tree, and a matching digest must then install so
    the check is proven to run rather than always pass.
    """
    import nltk.data
    from nltk.downloader import Downloader, ErrorMessage, Package

    box = tempfile.mkdtemp()
    # authorize the temp dir as a data root so the download write itself is allowed
    nltk.data.path.insert(0, box)
    try:
        pkgzip = os.path.join(box, "evil.zip")
        # box is registered as a data root above, so this stages INSIDE the
        # sandbox and must go through pathsec like any other in-root write.
        with pathsec.ZipFile(pkgzip, "w") as zf:
            zf.writestr("evil/data.txt", "payload")
        size = os.path.getsize(pkgzip)
        with open(pkgzip, "rb") as fh:
            good = hashlib.sha256(fh.read()).hexdigest()
        dest = os.path.join(box, "dl")
        os.makedirs(dest)
        installed = os.path.join(dest, "corpora", "evil.zip")

        def run(digest):
            pkg = Package(
                id="evil",
                url="file://" + pkgzip,
                subdir="corpora",
                size=size,
                unzipped_size=64,
            )
            pkg.sha256_checksum = digest
            msgs = list(
                Downloader()._download_package(pkg, download_dir=dest, force=True)
            )
            return any(
                isinstance(m, ErrorMessage) and "sha256" in str(m.message) for m in msgs
            )

        rejected = run("de" * 32)  # a wrong 64-hex digest
        if os.path.exists(installed):
            return VULNERABLE, "tampered package installed despite sha256 mismatch"
        if not rejected:
            return STATIC, "download fizzled before reaching the integrity gate"
        run(good)  # positive control: the matching digest must install
        if not os.path.exists(installed):
            return STATIC, "integrity gate also rejected a matching digest"
        return FIXED, "sha256 mismatch refused before commit; matching digest installs"
    finally:
        if box in nltk.data.path:
            nltk.data.path.remove(box)
        shutil.rmtree(box, ignore_errors=True)
