# Natural Language Toolkit: XML attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""XML entity attacks against ``nltk.xmlsec``, the parser the readers use.

Several corpus readers parse XML that a user supplies, so the classic entity
attacks all apply: file disclosure through an external entity, exponential
expansion, and an external DTD that turns the parser into an SSRF client.

The external-DTD case is checked against a REAL listening socket rather than by
reading the parsed text. A document whose DTD was fetched still parses to the
same text, so text alone cannot tell "ignored" from "fetched and discarded", and
the second of those is a live outbound request.
"""

import os
import shutil
import socket
import tempfile
import threading

import pytest

import nltk.data
from nltk import pathsec

xmlsec = pytest.importorskip("nltk.xmlsec")

_XXE = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
)
_BILLION = (
    '<?xml version="1.0"?><!DOCTYPE l ['
    '<!ENTITY a "aa">'
    '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
    '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
    '<!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">'
    '<!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">'
    "]><l>&e;</l>"
)
_PARAM = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE r [<!ENTITY % p SYSTEM "file:///etc/passwd">%p;]><r/>'
)


@pytest.fixture
def sandbox_root(monkeypatch):
    root = tempfile.mkdtemp(prefix="nltk_sandbox_root_")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write(root, document):
    path = os.path.join(root, "doc.xml")
    with pathsec.open(path, "w", context="test", encoding="utf-8") as handle:
        handle.write(document)
    return path


@pytest.mark.parametrize(
    "document, label",
    [
        (_XXE, "external entity"),
        (_BILLION, "billion laughs"),
        (_PARAM, "parameter entity"),
    ],
    ids=["xxe", "billion-laughs", "param-entity"],
)
def test_entity_attacks_are_refused(sandbox_root, document, label):
    path = _write(sandbox_root, document)
    with pytest.raises(Exception) as excinfo:
        tree = xmlsec.parse(path)
        text = "".join(tree.getroot().itertext())
        assert "root:" not in text, f"{label} disclosed /etc/passwd"
    assert "Forbidden" in type(excinfo.value).__name__ or "Entit" in str(excinfo.value)


def test_an_external_dtd_is_not_fetched(sandbox_root):
    """SSRF check against a real socket.

    The document parses either way, so the only honest test is whether anything
    connected.
    """
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(4)
    port = listener.getsockname()[1]
    connections = []

    def accept_one():
        try:
            connection, _ = listener.accept()
            connections.append(connection.recv(64))
            connection.close()
        except Exception:
            pass

    thread = threading.Thread(target=accept_one, daemon=True)
    thread.start()
    path = _write(
        sandbox_root,
        f'<?xml version="1.0"?><!DOCTYPE r SYSTEM '
        f'"http://127.0.0.1:{port}/evil.dtd"><r>x</r>',
    )
    try:
        xmlsec.parse(path)
    except Exception:
        pass
    thread.join(timeout=5)
    listener.close()
    assert connections == [], "the parser fetched the external DTD (SSRF)"


def test_ordinary_xml_still_parses(sandbox_root):
    """Over-block control: the readers depend on this working."""
    path = _write(sandbox_root, "<r><a>hi</a></r>")
    assert xmlsec.parse(path).getroot().find("a").text == "hi"
