"""GHSA-pcm8-fqjx-rvx8 [moderate] -- Cyclic collection index causes infinite loop in nltk.downloader"""

import os
import tempfile
import threading
from pathlib import Path

import nltk
from nltk.downloader import Downloader

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-pcm8-fqjx-rvx8")
def _cyclic_collection_index():
    # Create a self-referential index
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
        # Disable pathsec for file:// access in the probe
        original_enforce = nltk.pathsec.ENFORCE
        nltk.pathsec.ENFORCE = False

        # Use pathlib to get a proper file:// URI (works on Windows)
        uri = Path(path).as_uri()
        dl = Downloader(server_index_url=uri)

        # Run packages() with a timeout to detect hangs
        result = []
        exception = []
        done = threading.Event()

        def target():
            try:
                result.append(dl.packages())
            except Exception as e:
                exception.append(e)
            finally:
                done.set()

        t = threading.Thread(target=target)
        t.daemon = True
        t.start()
        completed = done.wait(timeout=10)

        nltk.pathsec.ENFORCE = original_enforce

        if not completed:
            return VULNERABLE, "Downloader.packages() hung (infinite loop)"
        elif exception:
            return VULNERABLE, f"Downloader.packages() raised: {exception[0]}"
        else:
            packages = result[0] if result else []
            if any(p.id == "p1" for p in packages):
                return FIXED, "Cyclic index handled correctly, packages returned"
            else:
                return VULNERABLE, "Expected package 'p1' not found"
    finally:
        os.unlink(path)
