"""Functional and path-security tests for NKJPCorpusReader.

The NKJP views build file paths from the caller-supplied ``fileids`` and read
the corpus files (``text.xml``/``ann_segmentation.xml``/``ann_morphosyntax.xml``)
through ``XML_Tool``, which pre-strips the ``nkjp:`` namespace so ``XMLCorpusView``
can parse substrings.  Two properties are tested here:

* Functional: ``header()``/``raw()``/``words()``/``sents()`` round-trip real UTF-8
  Polish text through the reader.  These exercise the ``XML_Tool`` preprocess step
  (a binary pathsec read + a binary pathsec write of the namespace-stripped copy);
  the original code wrote ``str`` to a binary tempfile and raised ``TypeError`` on
  every non-header read (issue #2416), which no security test caught because they
  only drove ``header()`` (which bypasses ``XML_Tool``) and traversal (which is
  refused in ``add_root`` before ``XML_Tool`` runs).

* Security (CWE-22/59): a ``..`` sequence, an absolute path, a NUL/newline, or an
  in-root symlink/hardlink in ``fileids`` or on a corpus file must not escape the
  corpus root.  The containment check is symlink-aware (``nltk.pathsec`` resolves
  the path and refuses to follow a final-component symlink with ``O_NOFOLLOW``), so
  ``os.path.abspath`` is not enough to fool it.

Paths are built with ``os.sep``/``os.path.join``/``os.pardir`` so the tests behave
identically on POSIX and Windows.  The malicious cases must *raise*, never return
out-of-root content.
"""

import os

import pytest

from nltk.corpus.reader.nkjp import NKJPCorpusReader

# A valid, reasonable NKJP sample modelled on the TEI4NKJP examples: a teiCorpus
# TEI with the nkjp: namespace, pretty-printed one element per line (as the real
# files are, and as XML_Tool's line-based stripper expects).  ann_segmentation
# carries a real <choice> of <nkjp:paren> variants (an ambiguous segmentation);
# XML_Tool strips <choice>/<nkjp:paren> and remove_choice keeps the first
# alternative, so the over-segmentation (7,2) of "gęślą" is dropped for (7,5).
# The text is the Polish pangram "Zażółć gęślą jaźń." (offsets: 0-5 / 7-11 / 13-16
# / 17 for the full stop), so every read mode has a deterministic expected value.
_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<teiHeader xmlns:nkjp="http://www.nkjp.pl/ns/1.0">
 <fileDesc><sourceDesc><bibl><title>{title}</title></bibl></sourceDesc></fileDesc>
</teiHeader>
"""
_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns:nkjp="http://www.nkjp.pl/ns/1.0">
 <text>
  <body>
   <div>
    <ab xml:id="ab_1">Zażółć gęślą jaźń.</ab>
   </div>
  </body>
 </text>
</TEI>
"""
_SEGMENTATION = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns:nkjp="http://www.nkjp.pl/ns/1.0">
 <text>
  <body>
   <p>
    <s>
     <seg corresp="text.xml#string-range(ab_1,0,6)"/>
     <choice>
      <nkjp:paren>
       <seg corresp="text.xml#string-range(ab_1,7,5)"/>
      </nkjp:paren>
      <nkjp:paren>
       <seg corresp="text.xml#string-range(ab_1,7,2)"/>
      </nkjp:paren>
     </choice>
     <seg corresp="text.xml#string-range(ab_1,13,4)"/>
     <seg corresp="text.xml#string-range(ab_1,17,1)"/>
    </s>
   </p>
  </body>
 </text>
</TEI>
"""
_MORPHOSYNTAX = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns:nkjp="http://www.nkjp.pl/ns/1.0">
 <text>
  <body>
   <p>
    <s>
     <seg><fs type="morph"><f name="orth"><string>Zażółć</string></f></fs></seg>
     <seg><fs type="morph"><f name="orth"><string>gęślą</string></f></fs></seg>
     <seg><fs type="morph"><f name="orth"><string>jaźń</string></f></fs></seg>
    </s>
   </p>
  </body>
 </text>
</TEI>
"""


def _build_corpus(tmp_path, title="IN-ROOT"):
    """Write the four NKJP files for a single sample under ``<tmp>/corpus/sample``."""
    root = tmp_path / "corpus"
    sample = root / "sample"
    sample.mkdir(parents=True)
    (sample / "header.xml").write_text(_HEADER.format(title=title), encoding="utf-8")
    (sample / "text.xml").write_text(_TEXT, encoding="utf-8")
    (sample / "ann_segmentation.xml").write_text(_SEGMENTATION, encoding="utf-8")
    (sample / "ann_morphosyntax.xml").write_text(_MORPHOSYNTAX, encoding="utf-8")
    return root


def _reader(root):
    # The trailing separator is added with os.sep, so the root keeps the shape
    # the reader is normally given without hard-coding a POSIX "/".
    return NKJPCorpusReader(root=str(root) + os.sep, fileids="sample")


# =========================================================================== #
# Functional: the legitimate UTF-8 flow must work (this is the #2416 fix).
# =========================================================================== #
def test_nkjp_header(tmp_path):
    reader = _reader(_build_corpus(tmp_path, title="Przykład"))
    out = reader.header()
    assert out and out[0]["title"] == "Przykład"


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("raw", ["Zażółć gęślą jaźń."]),
        ("words", ["Zażółć", "gęślą", "jaźń"]),
        ("sents", ["Zażółć gęślą jaźń."]),
    ],
)
def test_nkjp_reads_utf8_text(tmp_path, method, expected):
    """raw/words/sents must decode Polish text and preserve it, exercising the
    binary pathsec read + write in XML_Tool (the path the tempfile bug broke)."""
    reader = _reader(_build_corpus(tmp_path))
    assert getattr(reader, method)() == expected


# =========================================================================== #
# Security: fileid-level containment (refused in add_root before any read).
# =========================================================================== #
def test_nkjp_header_rejects_traversal_fileid(tmp_path):
    """A ../ traversal in fileids must be rejected, not read from disk."""
    root = _build_corpus(tmp_path)
    secret = tmp_path / "outside"
    secret.mkdir()
    (secret / "header.xml").write_text(_HEADER.format(title="SECRET"), encoding="utf-8")

    reader = _reader(root)
    evil = os.path.join(str(root), os.pardir, "outside") + os.sep
    with pytest.raises(ValueError):
        reader.header(fileids=[evil])


def test_nkjp_words_rejects_traversal_fileid(tmp_path):
    """All NKJP read modes funnel through add_root(); words() must reject too."""
    root = _build_corpus(tmp_path)
    reader = _reader(root)
    evil = os.path.join(str(root), os.pardir, "outside") + os.sep
    with pytest.raises(ValueError):
        reader.words(fileids=[evil])


def test_nkjp_rejects_absolute_path_fileid(tmp_path):
    """An absolute fileid pointing outside the root must be refused."""
    root = _build_corpus(tmp_path)
    reader = _reader(root)
    outside = str(tmp_path / "outside") + os.sep
    with pytest.raises(ValueError):
        reader.header(fileids=[outside])


@pytest.mark.parametrize("bad", ["sample\x00", "sample\nheader", "sample\r"])
def test_nkjp_rejects_control_char_fileid(tmp_path, bad):
    """A NUL or newline in a fileid must be refused (CWE-22 / line injection)."""
    root = _build_corpus(tmp_path)
    reader = _reader(root)
    with pytest.raises((ValueError, OSError)):
        reader.header(fileids=[bad])


def test_nkjp_header_rejects_inroot_symlink_escape(tmp_path):
    """A directory symlink *inside* the root that points outside must be rejected.

    This is the case ``os.path.abspath`` cannot catch: the candidate path is
    lexically in-root, so only resolving the symlink reveals that it escapes.
    """
    root = _build_corpus(tmp_path)
    secret = tmp_path / "outside"
    secret.mkdir()
    (secret / "header.xml").write_text(_HEADER.format(title="SECRET"), encoding="utf-8")

    link = root / "evil"
    try:
        os.symlink(secret, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    reader = _reader(root)
    evil = str(link) + os.sep
    with pytest.raises(ValueError):
        reader.header(fileids=[evil])


# =========================================================================== #
# Security: corpus-file-level guards inside XML_Tool (the binary pathsec read).
# =========================================================================== #
@pytest.mark.parametrize(
    ("victim", "method"),
    [("text.xml", "raw"), ("ann_morphosyntax.xml", "words")],
)
def test_nkjp_refuses_symlinked_corpus_file(tmp_path, victim, method):
    """A corpus file replaced by a symlink pointing outside the root must not be
    followed: pathsec resolves it (ValueError) or O_NOFOLLOW refuses it
    (PermissionError). The out-of-root secret must never be returned."""
    root = _build_corpus(tmp_path)
    secret = tmp_path / "secret.xml"
    secret.write_text(
        "<TEI><text><body><div><ab>TOP SECRET</ab></div></body></text></TEI>"
    )

    target = root / "sample" / victim
    target.unlink()
    try:
        os.symlink(secret, target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    reader = _reader(root)
    with pytest.raises((ValueError, PermissionError, OSError)) as exc:
        getattr(reader, method)()
    assert "SECRET" not in str(exc.value)


def test_nkjp_refuses_hardlinked_corpus_file(tmp_path):
    """A corpus file that is a hardlink to an out-of-root inode has no symlink to
    resolve, so only the st_nlink>1 check in the hardened open catches it."""
    root = _build_corpus(tmp_path)
    secret = tmp_path / "secret.xml"
    secret.write_text(
        "<TEI><text><body><div><ab>TOP SECRET</ab></div></body></text></TEI>"
    )

    target = root / "sample" / "text.xml"
    target.unlink()
    try:
        os.link(secret, target)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("hardlinks not supported on this platform")

    reader = _reader(root)
    with pytest.raises((ValueError, PermissionError, OSError)) as exc:
        reader.raw()
    assert "SECRET" not in str(exc.value)


def test_nkjp_non_utf8_source_fails_closed(tmp_path):
    """A corpus file that is not valid UTF-8 must raise (fail closed), not decode
    into silent mojibake; the explicit UTF-8 decode is what enforces this."""
    root = _build_corpus(tmp_path)
    # 0xF3 0xB3 are the ISO-8859-2 bytes for "ó³"; 0xF3 starts a 4-byte UTF-8
    # sequence that 0xB3 then 'w' do not complete, so this is not valid UTF-8.
    (root / "sample" / "text.xml").write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<TEI><text><body><div><ab xml:id="ab_1">z\xf3\xb3w</ab></div></body></text></TEI>\n'
    )
    reader = _reader(root)
    with pytest.raises(UnicodeDecodeError):
        reader.raw()
