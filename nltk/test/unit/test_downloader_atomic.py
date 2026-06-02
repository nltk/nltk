import hashlib
import io
import multiprocessing
import os
import shutil
import tempfile
import threading
import time
import unittest
import zipfile
from concurrent.futures import ProcessPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer

from nltk.downloader import Downloader, Package

# 1. Dynamically generate a valid, minimal ZIP file in memory
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zf:
    zf.writestr("abc/dummy.txt", b"real zip payload")
ZIP_BYTES = zip_buffer.getvalue()
ZIP_SIZE = len(ZIP_BYTES)
ZIP_MD5 = hashlib.md5(ZIP_BYTES).hexdigest()


# Create a custom server class to safely track requests
class TrackingServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_count = 0


class TrackingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.request_count += 1

        # Artificial delay to guarantee multiple processes hit the lock logic
        # while the file is actively downloading.
        time.sleep(0.1)

        self.send_response(200)
        self.send_header("Content-type", "application/zip")
        self.send_header("Content-Length", str(ZIP_SIZE))
        self.end_headers()
        self.wfile.write(ZIP_BYTES)

    def log_message(self, format, *args):
        pass  # Suppress console logging during the test run


class TestDownloaderAtomic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start a local server on a random open port
        cls.server = TrackingServer(("127.0.0.1", 0), TrackingHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.server.request_count = 0  # Reset count for each test

        self.pkg = Package(
            id="abc",
            url=f"http://127.0.0.1:{self.port}/abc.zip",
            size=ZIP_SIZE,
            unzipped_size=16,  # Length of b"real zip payload"
            filename="abc.zip",
            checksum=ZIP_MD5,
            unzip=True,
        )

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_concurrent_downloads_cooperate(self):
        """Verify multiple parallel processes result in exactly ONE network request."""
        dl = Downloader(download_dir=self.test_dir)
        num_concurrent = 3

        # Use 'spawn' to prevent deadlocks from forking a process that already has running threads
        mp_ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=num_concurrent, mp_context=mp_ctx
        ) as executor:
            futures = [
                executor.submit(dl.download, self.pkg, quiet=True)
                for _ in range(num_concurrent)
            ]
            results = [f.result() for f in futures]

        # All processes should report success
        self.assertTrue(all(results))

        # PROOF 1: The local server should have only received 1 request
        self.assertEqual(self.server.request_count, 1)

        # PROOF 2: The zip file exists and is valid
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "abc.zip")))

        # PROOF 3: NLTK successfully unzipped the file without throwing BadZipFile
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "abc", "dummy.txt")))
