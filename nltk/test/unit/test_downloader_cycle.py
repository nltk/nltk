import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nltk


class TestDownloaderCycle(unittest.TestCase):
    def _run_index_test(self, xml, expected_packages, timeout=5):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml)
            path = f.name
        try:
            uri = Path(path).as_uri()
            # Build script without leading indentation
            script_lines = [
                "import sys",
                "import nltk",
                "from nltk.downloader import Downloader",
                "nltk.pathsec.ENFORCE = False",
                f"dl = Downloader(server_index_url={repr(uri)})",
                "packages = dl.packages()",
                "print(','.join(p.id for p in packages))",
            ]
            script = "\n".join(script_lines)
            env = os.environ.copy()
            # Derive import root from nltk.__file__
            nltk_root = os.path.dirname(os.path.dirname(os.path.dirname(nltk.__file__)))
            env["PYTHONPATH"] = nltk_root + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            self.assertEqual(
                result.returncode, 0, f"Subprocess failed: {result.stderr}"
            )
            output = result.stdout.strip().split(",") if result.stdout.strip() else []
            self.assertEqual(output, expected_packages)
        except subprocess.TimeoutExpired:
            self.fail(f"Test timed out after {timeout}s")
        finally:
            os.unlink(path)

    def test_acyclic_index(self):
        xml = """<?xml version="1.0"?>
<index>
  <packages>
    <package id="p1" name="Sample" subdir="corpora/p1"
             url="http://example.invalid/p1.zip" unzip="0" size="0" unzipped_size="0"/>
  </packages>
  <collections>
    <collection id="a" name="Acyclic">
      <item ref="p1"/>
    </collection>
  </collections>
</index>"""
        self._run_index_test(xml, ["p1"])

    def test_self_referential_index(self):
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
        self._run_index_test(xml, ["p1"])

    def test_mutual_referential_index(self):
        xml = """<?xml version="1.0"?>
<index>
  <packages>
    <package id="p1" name="Sample" subdir="corpora/p1"
             url="http://example.invalid/p1.zip" unzip="0" size="0" unzipped_size="0"/>
  </packages>
  <collections>
    <collection id="a" name="A">
      <item ref="b"/>
      <item ref="p1"/>
    </collection>
    <collection id="b" name="B">
      <item ref="a"/>
    </collection>
  </collections>
</index>"""
        self._run_index_test(xml, ["p1"])
