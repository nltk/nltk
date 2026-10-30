# Natural Language Toolkit: downloader package-attribute traversal
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A malicious download index must not write outside the download directory.

CVE-2026-33236: the ``subdir`` and ``id`` attributes in the remote index.xml
were joined into the install path (``os.path.join(subdir, id + ext)``). A
``subdir`` of ``../../../../tmp`` or an ``id`` of ``../../evil`` escaped the
download dir. Both are validated at Package construction now; this pins that a
crafted index cannot build an escaping filename.

The ``subdir`` check rejects absoluteness under posix and windows rules and a
bare drive prefix, because Python 3.13's ``ntpath.isabs`` no longer treats a
rooted ``/tmp`` as absolute and ``os.path.isabs`` sees no drive on posix.
"""

import os

import pytest

from nltk.downloader import Package

_REQUIRED = dict(url="http://example/x.zip", size=1, unzipped_size=1, checksum="a")


@pytest.mark.parametrize(
    "attributes",
    [
        {"id": "x", "subdir": "../../../../tmp"},
        {"id": "x", "subdir": "/tmp"},
        {"id": "x", "subdir": "..\\..\\tmp"},
        {"id": "x", "subdir": "C:\\evil"},
        {"id": "../../../../tmp/evil", "subdir": "corpora"},
        {"id": "/tmp/evil", "subdir": "corpora"},
        {"id": "..\\..\\..\\tmp\\evil", "subdir": "corpora"},
        {"id": "ok\x00/../evil", "subdir": "corpora"},
        {"id": "a/b", "subdir": "corpora"},
    ],
    ids=[
        "subdir-traversal",
        "subdir-absolute",
        "subdir-backslash",
        "subdir-drive",
        "id-traversal",
        "id-absolute",
        "id-backslash",
        "id-nul",
        "id-with-slash",
    ],
)
def test_malicious_package_attributes_are_refused(attributes):
    with pytest.raises((PermissionError, ValueError)):
        Package(**_REQUIRED, **attributes)


def test_a_benign_package_builds_a_contained_filename():
    """Over-block control, and the shape a real index uses."""
    package = Package(id="punkt", subdir="tokenizers", **_REQUIRED)
    assert package.filename == os.path.join("tokenizers", "punkt.zip")
    # the join with any download dir stays inside it
    download_dir = os.path.join("home", "user", "nltk_data")
    full = os.path.normpath(os.path.join(download_dir, package.filename))
    assert full.startswith(os.path.normpath(download_dir))
