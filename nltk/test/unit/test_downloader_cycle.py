# nltk/test/unit/test_downloader_cycle.py
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nltk


class TestDownloaderCycle(unittest.TestCase):
    """Test that Downloader._update_index handles cyclic collection references safely."""

    def _run_index_test(self, xml, expected_packages, timeout=5):
        """
        Write xml to a temp file, run Downloader.packages() in a subprocess,
        and assert it returns within timeout and collects the expected packages.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml)
            path = f.name

        try:
            uri = Path(path).as_uri()

            # Build a script that runs the test and prints results
            script = f"""
import sys
import nltk
from nltk.downloader import Downloader

# Disable pathsec for file:// tests
nltk.pathsec.ENFORCE = False

dl = Downloader(server_index_url={repr(uri)})
packages = dl.packages()
# Print package IDs as a comma-separated list
print(','.join(p.id for p in packages))
"""
            # Set PYTHONPATH so the subprocess can find nltk
            env = os.environ.copy()
            # Add the current working directory (root of nltk source) to PYTHONPATH
            cwd = os.getcwd()
            env["PYTHONPATH"] = cwd + os.pathsep + env.get("PYTHONPATH", "")

            # Run the script in a subprocess with a timeout
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            self.assertEqual(
                result.returncode,
                0,
                f"Subprocess failed with exit code {result.returncode}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}",
            )

            output_packages = (
                result.stdout.strip().split(",") if result.stdout.strip() else []
            )
            self.assertEqual(
                output_packages,
                expected_packages,
                f"Expected packages {expected_packages}, got {output_packages}",
            )

        except subprocess.TimeoutExpired:
            self.fail(f"Index test timed out after {timeout} seconds (infinite loop?)")
        finally:
            os.unlink(path)

    def test_acyclic_index(self):
        """Control: a normal index should complete normally."""
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
        self._run_index_test(xml, expected_packages=["p1"], timeout=5)

    def test_self_referential_index(self):
        """A self-referential collection should complete without hanging."""
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
        self._run_index_test(xml, expected_packages=["p1"], timeout=5)

    def test_mutual_referential_index(self):
        """Two collections referencing each other should complete without hanging."""
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
        self._run_index_test(xml, expected_packages=["p1"], timeout=5)


if __name__ == "__main__":
    unittest.main()
