"""Test that the NLTK downloader is protected against XML entity expansion attacks.

This test verifies that parsing a malicious XML index file with recursive entity
definitions (Billion Laughs / XML bomb) does not cause excessive memory consumption
or denial of service.
"""

import io
import unittest.mock

import pytest
from defusedxml.common import EntitiesForbidden

from nltk.downloader import Downloader


# Billion Laughs payload - exponential entity expansion
BILLION_LAUGHS_XML = b"""\
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<nltk_data>&lol4;</nltk_data>
"""


def test_downloader_rejects_xml_entity_expansion():
    """Verify that the downloader rejects XML with entity expansion (Billion Laughs)."""
    d = Downloader()

    with unittest.mock.patch("nltk.downloader.urlopen") as mock_urlopen:
        mock_urlopen.return_value = io.BytesIO(BILLION_LAUGHS_XML)
        with pytest.raises(EntitiesForbidden):
            d._update_index()
