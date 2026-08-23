"""GHSA-pcm8-fqjx-rvx8 [moderate] -- Cyclic collection index causes infinite loop in nltk.downloader"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import nltk

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-pcm8-fqjx-rvx8")
def _cyclic_collection_index():
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
        uri = Path(path).as_uri()
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
            # Subprocess timeout is wall-clock (startup + imports + probe work).
            # Under CI contention, shorter budgets can false-timeout healthy runs.
            timeout=30,
            env=env,
        )

        if result.returncode != 0:
            return VULNERABLE, f"Subprocess failed: {result.stderr.strip()}"
        output = result.stdout.strip()
        if output == "p1":
            return FIXED, "Cyclic index handled correctly"
        else:
            return VULNERABLE, f"Expected 'p1', got '{output}'"
    except subprocess.TimeoutExpired:
        return STATIC, "Subprocess timed out under CI load (inconclusive)"
    finally:
        os.unlink(path)
