"""
Tests for XML Entity Expansion (XXE) protection in nltk.downloader.

Verifies that defusedxml blocks Billion Laughs (XML bomb) payloads
when parsing the package index from a remote URL.
"""

import io
import unittest
from unittest.mock import patch

from defusedxml import EntitiesForbidden

from nltk.downloader import Downloader

# Billion Laughs payload: ~1KB input expands to ~3GB in memory
BILLION_LAUGHS_XML = """\
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
  <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
  <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
  <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
  <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<root>&lol9;</root>
"""


class TestDownloaderXXE(unittest.TestCase):
    """Verify that the downloader rejects XML bomb payloads."""

    def test_billion_laughs_blocked(self):
        """defusedxml must reject entity expansion in index XML."""
        downloader = Downloader()
        xml_bytes = BILLION_LAUGHS_XML.encode("utf-8")

        with patch("nltk.downloader.urlopen", return_value=io.BytesIO(xml_bytes)):
            with self.assertRaises(EntitiesForbidden):
                downloader._update_index(url="http://example.com/malicious.xml")

    def test_valid_xml_parses(self):
        """Normal XML index should parse without error."""
        valid_xml = """\
<?xml version="1.0"?>
<nltk_data>
  <packages>
    <package id="test_pkg" name="Test" subdir="corpora"
             url="http://example.com/test.zip" size="1024"
             unzipped_size="2048" checksum="abc123"/>
  </packages>
  <collections>
    <collection id="test_col" name="Test Collection">
      <item ref="test_pkg"/>
    </collection>
  </collections>
</nltk_data>
"""
        downloader = Downloader()
        xml_bytes = valid_xml.encode("utf-8")

        with patch("nltk.downloader.urlopen", return_value=io.BytesIO(xml_bytes)):
            downloader._update_index(url="http://example.com/valid.xml")
            self.assertIn("test_pkg", downloader._packages)


if __name__ == "__main__":
    unittest.main()
