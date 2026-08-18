# nltk/test/unit/test_downloader_cycle.py
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

import nltk
from nltk.downloader import Downloader


class TestDownloaderCycle(unittest.TestCase):
    def setUp(self):
        # Disable pathsec to avoid file:// permission issues
        self.orig_enforce = nltk.pathsec.ENFORCE
        nltk.pathsec.ENFORCE = False

    def tearDown(self):
        nltk.pathsec.ENFORCE = self.orig_enforce

    def _run_with_timeout(self, func, timeout=2):
        """
        Run func in a thread; return (completed, result, exception).
        If completed is False, the thread timed out.
        If exception is not None, the thread raised that exception.
        """
        result = []
        exc = []

        def target():
            try:
                result.append(func())
            except Exception as e:
                exc.append(e)

        t = threading.Thread(target=target)
        t.daemon = True
        t.start()
        t.join(timeout)

        if t.is_alive():
            return False, None, None
        if exc:
            return True, None, exc[0]
        return True, result[0] if result else None, None

    def test_cyclic_index_does_not_hang(self):
        # Create a temporary index with a self-referential collection
        xml = """<?xml version="1.0"?>
<index>
  <packages>
    <package id="p1" name="Sample" subdir="corpora/p1"
             url="http://example.invalid/p1.zip" unzip="0" size="0" unzipped_size="0"/>
  </packages>
  <collections>
    <collection id="a" name="Cyclic">
      <item ref="a"/>
      <item ref="p1"/>
    </collection>
  </collections>
</index>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml)
            path = f.name

        try:
            # Use pathlib to get a proper file:// URI (works on Windows with drive letters)
            uri = Path(path).as_uri()
            dl = Downloader(server_index_url=uri)

            completed, packages, exc = self._run_with_timeout(
                lambda: dl.packages(), timeout=5
            )

            self.assertTrue(completed, "Cyclic index caused a hang (timeout)")
            self.assertIsNone(exc, f"Unexpected exception: {exc}")
            self.assertIsNotNone(packages, "dl.packages() returned None")
            self.assertEqual(
                [p.id for p in packages], ["p1"], "Expected package p1 to be collected"
            )
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
