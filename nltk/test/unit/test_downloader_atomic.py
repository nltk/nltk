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
