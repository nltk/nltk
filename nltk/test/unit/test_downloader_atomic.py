import hashlib
import multiprocessing
import os
import shutil
import tempfile
import time
import unittest
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import patch

import nltk.data
import nltk.pathsec
from nltk.downloader import Downloader, Package

BIG_PAYLOAD = b"x" * (1024 * 1024)


def _build_source_zip(source_dir):
    os.makedirs(source_dir, exist_ok=True)
    zip_path = os.path.join(source_dir, "abc.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("abc/dummy.txt", BIG_PAYLOAD)
    return zip_path


def _zip_metadata(zip_path):
    with open(zip_path, "rb") as f:
        data = f.read()
    with zipfile.ZipFile(zip_path, "r") as zf:
        unzipped_size = sum(info.file_size for info in zf.infolist())
    return {
        "size": len(data),
        "md5": hashlib.md5(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "unzipped_size": unzipped_size,
    }


class SlowResponse:
    def __init__(self, wrapped, delay=0.02):
        self._wrapped = wrapped
        self._delay = delay

    def read(self, n=-1):
        data = self._wrapped.read(n)
        if data:
            time.sleep(self._delay)
        return data

    def close(self):
        return self._wrapped.close()

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


def _download_with_file_url(download_dir, pkg, fetch_count, fetch_lock):
    real_pathsec_urlopen = nltk.pathsec.urlopen

    def counting_urlopen(url, *args, **kwargs):
        with fetch_lock:
            fetch_count.value += 1
        wrapped = real_pathsec_urlopen(url, *args, **kwargs)
        return SlowResponse(wrapped, delay=0.02)

    dl = Downloader(download_dir=download_dir)
    with patch("nltk.downloader.urlopen", side_effect=counting_urlopen):
        return dl.download(pkg, quiet=True)


def _collect_debug(download_dir, pkg):
    dl = Downloader(download_dir=download_dir)
    zip_path = os.path.join(download_dir, pkg.filename)
    unzipdir = zip_path[:-4] if zip_path.endswith(".zip") else None

    data = {
        "pkg_filename": pkg.filename,
        "zip_path": zip_path,
        "zip_exists": os.path.exists(zip_path),
        "zip_size": os.path.getsize(zip_path) if os.path.exists(zip_path) else None,
        "unzipdir": unzipdir,
        "unzipdir_exists": os.path.exists(unzipdir) if unzipdir else None,
        "unzipdir_is_dir": os.path.isdir(unzipdir) if unzipdir else None,
        "files": [],
        "total_unzipped_size": 0,
        "expected_size": int(pkg.size),
        "expected_unzipped_size": int(pkg.unzipped_size),
        "expected_md5": pkg.checksum,
        "expected_sha256": getattr(pkg, "sha256_checksum", None),
        "status": dl.status(pkg, download_dir),
    }

    if os.path.exists(zip_path):
        with open(zip_path, "rb") as f:
            content = f.read()
        data["zip_md5"] = hashlib.md5(content).hexdigest()
        data["zip_sha256"] = hashlib.sha256(content).hexdigest()

    if unzipdir and os.path.isdir(unzipdir):
        for root, _dirs, files in os.walk(unzipdir):
            for name in sorted(files):
                path = os.path.join(root, name)
                rel = os.path.relpath(path, unzipdir)
                size = os.path.getsize(path)
                data["files"].append((rel, size))
                data["total_unzipped_size"] += size

    return data


class TestDownloaderAtomic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = tempfile.mkdtemp()

        # Allow strict pathsec access to our temp roots.
        self._old_nltk_data_path = list(nltk.data.path)
        resolved_test_dir = str(Path(self.test_dir).resolve())
        resolved_source_dir = str(Path(self.source_dir).resolve())
        if resolved_test_dir not in nltk.data.path:
            nltk.data.path.append(resolved_test_dir)
        if resolved_source_dir not in nltk.data.path:
            nltk.data.path.append(resolved_source_dir)

        self.source_zip_path = _build_source_zip(self.source_dir)
        meta = _zip_metadata(self.source_zip_path)

        self.pkg = Package(
            id="abc",
            url=Path(self.source_zip_path).resolve().as_uri(),
            subdir="corpora",
            size=meta["size"],
            unzipped_size=meta["unzipped_size"],
            checksum=meta["md5"],
            sha256_checksum=meta["sha256"],
            unzip=True,
        )

    def tearDown(self):
        nltk.data.path[:] = self._old_nltk_data_path
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists(self.source_dir):
            shutil.rmtree(self.source_dir)

    def test_concurrent_downloads_cooperate(self):
        """Verify multiple parallel processes cooperate under ENFORCE=True."""
        num_concurrent = 3
        mp_ctx = multiprocessing.get_context("spawn")

        with mp_ctx.Manager() as manager:
            fetch_count = manager.Value("i", 0)
            fetch_lock = manager.Lock()

            with ProcessPoolExecutor(
                max_workers=num_concurrent, mp_context=mp_ctx
            ) as executor:
                futures = [
                    executor.submit(
                        _download_with_file_url,
                        self.test_dir,
                        self.pkg,
                        fetch_count,
                        fetch_lock,
                    )
                    for _ in range(num_concurrent)
                ]
                results = [f.result() for f in futures]

            debug = _collect_debug(self.test_dir, self.pkg)

            self.assertTrue(
                all(results),
                msg=f"results={results}, fetch_count={fetch_count.value}, debug={debug}",
            )
            self.assertEqual(
                fetch_count.value,
                1,
                msg=f"Expected exactly one fetch, got {fetch_count.value}; debug={debug}",
            )

            zip_path = os.path.join(self.test_dir, self.pkg.filename)
            extracted_file = os.path.join(self.test_dir, "corpora", "abc", "dummy.txt")

            self.assertTrue(os.path.exists(zip_path), msg=f"debug={debug}")
            self.assertTrue(os.path.exists(extracted_file), msg=f"debug={debug}")

            with open(extracted_file, "rb") as f:
                self.assertEqual(f.read(), BIG_PAYLOAD, msg=f"debug={debug}")

            dl = Downloader(download_dir=self.test_dir)
            self.assertEqual(
                dl.status(self.pkg, self.test_dir), dl.INSTALLED, msg=f"debug={debug}"
            )

    def test_md5_mismatch_rejected_before_install(self):
        """Legacy MD5 metadata should be enforced before install/extraction."""

        bad_pkg = Package(
            id="abc",
            url=Path(self.source_zip_path).resolve().as_uri(),
            subdir="corpora",
            size=self.pkg.size,
            unzipped_size=self.pkg.unzipped_size,
            checksum="deadbeefdeadbeefdeadbeefdeadbeef",
            unzip=True,
        )

        dl = Downloader(download_dir=self.test_dir)

        ok = dl.download(
            bad_pkg,
            quiet=True,
            force=True,
            raise_on_error=False,
        )

        extracted_file = os.path.join(
            self.test_dir,
            "corpora",
            "abc",
            "dummy.txt",
        )

        self.assertFalse(ok)
        self.assertFalse(os.path.exists(extracted_file))

    def _make_zip_with_members(self, members):
        """Build a ZIP in srv_dir with given {member_path: content} dict."""
        srv_dir = tempfile.mkdtemp()
        buf = __import__("io").BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
            for path, content in members.items():
                zf.writestr(path, content)
        zb = buf.getvalue()
        zip_path = os.path.join(srv_dir, "evil.zip")
        open(zip_path, "wb").write(zb)
        return srv_dir, zip_path, zb

    def _make_pkg(self, zip_path, zb, pkg_id, subdir, members):
        import hashlib
        from pathlib import Path

        unzipped = sum(len(v.encode()) for v in members.values())
        return Package(
            id=pkg_id,
            url=Path(zip_path).resolve().as_uri(),
            subdir=subdir,
            size=len(zb),
            unzipped_size=unzipped,
            checksum=hashlib.md5(zb).hexdigest(),
            sha256_checksum=hashlib.sha256(zb).hexdigest(),
            unzip=True,
        )

    def test_cross_package_overwrite_blocked(self):
        """Direct cross-package overwrite (CVE-2026-12261 core case).

        evil-corpus declares subdir=corpora but its ZIP contains
        abc/dummy.txt — another package's file.  The install must
        be rejected and the victim file must remain unchanged.
        """
        # Write a sentinel victim file
        victim_dir = os.path.join(self.test_dir, "corpora", "abc")
        os.makedirs(victim_dir, exist_ok=True)
        victim_file = os.path.join(victim_dir, "dummy.txt")
        open(victim_file, "wb").write(b"original")

        members = {"abc/dummy.txt": "poisoned"}
        srv_dir, zip_path, zb = self._make_zip_with_members(members)
        try:
            evil_pkg = self._make_pkg(zip_path, zb, "evil-corpus", "corpora", members)
            dl = Downloader(download_dir=self.test_dir)
            ok = dl.download(evil_pkg, quiet=True, force=True, raise_on_error=False)

            with open(victim_file, "rb") as f:
                content = f.read()

            self.assertFalse(ok, "Download should have been rejected")
            self.assertEqual(
                content, b"original", "Victim file must not be overwritten"
            )
        finally:
            __import__("shutil").rmtree(srv_dir, ignore_errors=True)

    def test_traversal_member_cannot_escape_package_ownership(self):
        """Traversal-like members must not overwrite sibling packages."""

        victim_dir = os.path.join(self.test_dir, "corpora", "abc")
        os.makedirs(victim_dir, exist_ok=True)

        victim_file = os.path.join(victim_dir, "dummy.txt")
        with open(victim_file, "wb") as f:
            f.write(b"original")

        members = {
            "evil-corpus/../abc/dummy.txt": "poisoned",
        }

        srv_dir, zip_path, zb = self._make_zip_with_members(members)

        try:
            evil_pkg = self._make_pkg(
                zip_path,
                zb,
                "evil-corpus",
                "corpora",
                members,
            )

            dl = Downloader(download_dir=self.test_dir)

            ok = dl.download(
                evil_pkg,
                quiet=True,
                force=True,
                raise_on_error=False,
            )

            self.assertFalse(
                ok,
                "Traversal-style member should be rejected",
            )

            with open(victim_file, "rb") as f:
                self.assertEqual(
                    f.read(),
                    b"original",
                    "Traversal member must not overwrite victim package",
                )

            extracted_file = os.path.join(
                self.test_dir,
                "corpora",
                "evil-corpus",
                "abc",
                "dummy.txt",
            )

            self.assertFalse(os.path.exists(extracted_file))

        finally:
            shutil.rmtree(srv_dir, ignore_errors=True)

    def test_missing_unzipdir_is_not_installed_for_packages_that_require_unzip(self):
        dl = Downloader(download_dir=self.test_dir)
        zip_path = os.path.join(self.test_dir, self.pkg.filename)

        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        shutil.copyfile(self.source_zip_path, zip_path)

        self.assertEqual(dl.status(self.pkg, self.test_dir), dl.NOT_INSTALLED)

    def test_missing_unzipdir_is_installed_for_packages_kept_zipped(self):
        dl = Downloader(download_dir=self.test_dir)

        pkg = Package(
            id=self.pkg.id,
            url=self.pkg.url,
            subdir=self.pkg.subdir,
            size=self.pkg.size,
            unzipped_size=self.pkg.unzipped_size,
            checksum=self.pkg.checksum,
            sha256_checksum=self.pkg.sha256_checksum,
            unzip=False,
        )
        zip_path = os.path.join(self.test_dir, pkg.filename)

        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        shutil.copyfile(self.source_zip_path, zip_path)

        self.assertEqual(dl.status(pkg, self.test_dir), dl.INSTALLED)

    def test_stale_zip_exists_unzips_without_redownload(self):
        dl = Downloader(download_dir=self.test_dir)
        zip_path = os.path.join(self.test_dir, self.pkg.filename)
        extracted_file = os.path.join(self.test_dir, "corpora", "abc", "dummy.txt")

        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        shutil.copyfile(self.source_zip_path, zip_path)

        with patch("nltk.downloader.urlopen") as urlopen_mock:
            ok = dl.download(self.pkg, quiet=True)

        self.assertTrue(ok)
        urlopen_mock.assert_not_called()
        self.assertTrue(os.path.exists(extracted_file))
        self.assertEqual(dl.status(self.pkg, self.test_dir), dl.INSTALLED)
