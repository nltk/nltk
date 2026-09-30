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

# The st_nlink hardlink guard lives in pathsec's POSIX-only hardened open, so a
# hardlink to an out-of-root inode is only refused on POSIX (a symlink is refused
# everywhere: validate_path resolves it and rejects by containment).
posix_only = pytest.mark.skipif(
    os.name != "posix", reason="st_nlink hardlink guard is POSIX-only (pathsec)"
)

# A valid NKJP sample modelled on the TEI4NKJP examples: a TEI with the nkjp:
# namespace, pretty-printed one element per line (as the real files are, and as
# XML_Tool's line-based stripper expects). Text = pangram "Zażółć gęślą jaźń."
_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<teiHeader xmlns:nkjp="http://www.nkjp.pl/ns/1.0">
 <fileDesc><sourceDesc><bibl><title>{title}</title></bibl></sourceDesc></fileDesc>
</teiHeader>
"""
# Token offsets into the pangram: Zażółć 0-5, gęślą 7-11, jaźń 13-16, "." 17.
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
# ann_segmentation carries a real <choice> of <nkjp:paren> variants (an ambiguous
# segmentation): XML_Tool strips <choice>/<nkjp:paren> and remove_choice keeps the
# first, so the over-segmentation (7,2) of "gęślą" is dropped for the whole (7,5).
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


# Functional: the legitimate UTF-8 flow must work (this is the #2416 fix).
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


# Security: fileid-level containment (refused in add_root before any read).
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
    """A NUL or newline in a fileid must be refused, not read from disk. NUL is
    caught by validate_path's marked guard (a PermissionError, which is an
    OSError); a newline is a valid POSIX name char so it falls through to a
    file-not-found OSError, and is an invalid name on Windows (also OSError)."""
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


# Security: corpus-file-level guards inside XML_Tool (the binary pathsec read).
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


@posix_only
def test_nkjp_refuses_hardlinked_corpus_file(tmp_path):
    """A corpus file that is a hardlink to an out-of-root inode has no symlink to
    resolve, so only the st_nlink>1 check in the POSIX hardened open catches it;
    on Windows pathsec falls back to a plain open with no such check."""
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


# Security: XML_Tool scratch teardown cannot become arbitrary deletion.
def _xml_tool(root, filename="text.xml"):
    from nltk.corpus.reader.nkjp import XML_Tool

    return XML_Tool(str(root / "sample") + os.sep, filename)


def test_nkjp_reads_do_not_delete_corpus_files(tmp_path):
    """Reading (and its teardown) must leave every source file on disk."""
    root = _build_corpus(tmp_path)
    reader = _reader(root)
    reader.header()
    reader.raw()
    reader.words()
    reader.sents()
    for name in (
        "header.xml",
        "text.xml",
        "ann_segmentation.xml",
        "ann_morphosyntax.xml",
    ):
        assert (root / "sample" / name).exists()


def test_teardown_removes_only_its_own_scratch_file(tmp_path):
    """Cleanup deletes the one temp file, not staging_tempdir() itself or any
    sibling in it (the single-file os.remove, not a directory-tree rmtree)."""
    tool = _xml_tool(_build_corpus(tmp_path))
    scratch = tool.build_preprocessed_file()
    assert os.path.exists(scratch)
    sibling = os.path.join(os.path.dirname(scratch), "other-reader.keep")
    open(sibling, "w").close()
    try:
        tool.remove_preprocessed_file()
        assert not os.path.exists(scratch)  # our file is gone
        assert os.path.exists(sibling)  # a co-tenant file is untouched
    finally:
        os.remove(sibling)


def test_teardown_is_idempotent_and_safe_before_build(tmp_path):
    """Removing twice, and removing before any file was written, must not raise."""
    tool = _xml_tool(_build_corpus(tmp_path))
    tool.remove_preprocessed_file()  # nothing written yet
    tool.build_preprocessed_file()
    tool.remove_preprocessed_file()
    tool.remove_preprocessed_file()  # already gone


def test_teardown_does_not_delete_through_a_symlink(tmp_path):
    """Cleanup must leave an unowned symlink and its target untouched. write_file
    is never caller-derived (defence-in-depth), but even if it were a symlink to a
    victim, the ownership guard skips it, and os.remove would only unlink the link,
    never the target's contents, so the teardown primitive stays safe."""
    victim = tmp_path / "victim.txt"
    victim.write_text("KEEP")
    link = tmp_path / "scratch_link"
    try:
        os.symlink(victim, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    tool = _xml_tool(_build_corpus(tmp_path))
    tool.write_file = str(link)
    tool.remove_preprocessed_file()
    assert link.is_symlink()
    assert victim.exists() and victim.read_text() == "KEEP"


def test_teardown_refuses_to_delete_a_directory(tmp_path):
    """Cleanup must leave an unowned directory and its contents untouched. Even if
    write_file pointed at a directory, the ownership guard skips it, and os.remove
    refuses a directory anyway (never nuking a tree), so no rmtree-style mass
    deletion is reachable."""
    victim_dir = tmp_path / "victim_dir"
    victim_dir.mkdir()
    (victim_dir / "keep.txt").write_text("KEEP")
    tool = _xml_tool(_build_corpus(tmp_path))
    tool.write_file = str(victim_dir)
    tool.remove_preprocessed_file()
    assert victim_dir.exists() and (victim_dir / "keep.txt").exists()


@pytest.mark.parametrize("failure", ["decode", "write", "destination"])
def test_preprocessing_closes_streams_before_cleanup(tmp_path, monkeypatch, failure):
    from nltk import pathsec

    root = _build_corpus(tmp_path)
    if failure == "decode":
        (root / "sample" / "text.xml").write_bytes(b"\xff")
    tool = _xml_tool(root)
    streams = []
    real_open = pathsec.open
    real_remove = os.remove

    def tracked_open(path, mode, **kwargs):
        if mode == "xb" and failure == "destination":
            raise PermissionError("destination refused")
        stream = real_open(path, mode, **kwargs)
        streams.append(stream)
        if mode == "xb" and failure == "write":

            def fail_write(data):
                raise OSError("write failed")

            monkeypatch.setattr(stream, "write", fail_write)
        return stream

    def checked_remove(path):
        assert all(stream.closed for stream in streams)
        return real_remove(path)

    monkeypatch.setattr(pathsec, "open", tracked_open)
    monkeypatch.setattr(os, "remove", checked_remove)
    error = UnicodeDecodeError if failure == "decode" else OSError
    with pytest.raises(error):
        tool.build_preprocessed_file()
    assert streams and all(stream.closed for stream in streams)
    assert not os.path.exists(tool.write_file)


@pytest.mark.parametrize("cleanup_before_build", [False, True])
def test_preprocessing_preserves_existing_scratch_file(tmp_path, cleanup_before_build):
    tool = _xml_tool(_build_corpus(tmp_path))
    with open(tool.write_file, "wb") as stream:
        stream.write(b"another reader's data")
    try:
        if cleanup_before_build:
            tool.remove_preprocessed_file()
        with pytest.raises(FileExistsError):
            tool.build_preprocessed_file()
        tool.remove_preprocessed_file()
        with open(tool.write_file, "rb") as stream:
            assert stream.read() == b"another reader's data"
    finally:
        os.remove(tool.write_file)


def _scratch_files():
    from nltk.data import staging_tempdir

    return sorted(f for f in os.listdir(staging_tempdir()) if f.startswith("nkjp-"))


@pytest.mark.parametrize("method", ["raw", "words", "sents"])
def test_view_constructor_failure_removes_the_scratch_copy(
    tmp_path, monkeypatch, method
):
    """The scratch copy exists as soon as build_preprocessed_file() returns, and
    XMLCorpusView.__init__ then reads it (encoding detection, size). A failure
    there used to leave the copy in the staging dir for the life of the process,
    because only handle_query() cleaned up; a 250 KB first line that makes the
    encoding-detection regex hit its time limit is a real trigger."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    def broken(self, fileid):
        raise OSError("encoding detection failed")

    monkeypatch.setattr(XMLCorpusView, "_detect_encoding", broken)
    reader = _reader(_build_corpus(tmp_path))
    with pytest.raises(OSError, match="encoding detection failed"):
        getattr(reader, method)()
    assert _scratch_files() == []


def test_handle_query_error_keeps_its_type_and_removes_the_scratch(tmp_path):
    """A parse error while reading the scratch copy must surface as the parser's
    own error, not a bare Exception, and the copy must be gone afterwards."""
    root = _build_corpus(tmp_path)
    (root / "sample" / "text.xml").write_text(
        '<?xml version="1.0"?><TEI><text><body><div><ab xml:id="ab_1">open',
        encoding="utf-8",
    )
    with pytest.raises(Exception) as exc:
        _reader(root).raw()
    assert type(exc.value) is not Exception, type(exc.value)
    assert _scratch_files() == []


@pytest.mark.parametrize("variant", ["bom", "crlf", "bom+crlf", "no-final-newline"])
def test_bom_and_crlf_text_reads_the_same_words(tmp_path, variant):
    """Byte-exact preprocessing: a UTF-8 BOM and CR LF line ends are legitimate
    and must survive the line-based strip unchanged."""
    text = _TEXT
    if "crlf" in variant:
        text = text.replace("\n", "\r\n")
    if "bom" in variant:
        text = "\ufeff" + text
    if variant == "no-final-newline":
        text = text.rstrip("\n")
    root = _build_corpus(tmp_path)
    (root / "sample" / "text.xml").write_text(text, encoding="utf-8")
    reader = _reader(root)
    assert reader.raw() == ["Zażółć gęślą jaźń."]
    assert reader.words() == ["Zażółć", "gęślą", "jaźń"]


@pytest.mark.parametrize("bomb", ["billion-laughs", "external-entity"])
def test_entity_bombs_in_text_xml_are_refused_without_expansion(tmp_path, bomb):
    """The scratch copy is parsed through the same guarded XML route as every
    corpus file: an entity declaration is refused (CWE-776/611), nothing is
    expanded or read from outside, and no scratch copy is left behind."""
    if bomb == "billion-laughs":
        entities = '<!ENTITY lol "lol">' + "".join(
            '<!ENTITY lol%d "%s">' % (i, "&lol%d;" % (i - 1) * 10) for i in range(2, 9)
        )
        body = "&lol8;"
    else:
        entities = '<!ENTITY xxe SYSTEM "file:///etc/passwd">'
        body = "&xxe;"
    root = _build_corpus(tmp_path)
    (root / "sample" / "text.xml").write_text(
        '<?xml version="1.0"?><!DOCTYPE t [%s]>' % entities
        + '<TEI><text><body><div><ab xml:id="ab_1">%s</ab></div></body></text></TEI>'
        % body,
        encoding="utf-8",
    )
    with pytest.raises(Exception) as exc:
        _reader(root).raw()
    assert "root:" not in str(exc.value) and "lol" * 100 not in str(exc.value)
    assert _scratch_files() == []


def test_concurrent_reads_leave_no_scratch_files(tmp_path):
    """Eight threads reading the same sample at once: every read succeeds (the
    names are unique per instance) and the staging dir ends empty."""
    import threading

    reader = _reader(_build_corpus(tmp_path))
    errors = []

    def work():
        try:
            for _ in range(3):
                assert reader.raw() == ["Zażółć gęślą jaźń."]
                assert reader.words() == ["Zażółć", "gęślą", "jaźń"]
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert _scratch_files() == []


@pytest.mark.parametrize("plant", ["symlink", "directory"])
def test_a_plant_at_the_scratch_name_is_refused_and_untouched(tmp_path, plant):
    """ "xb" is O_CREAT|O_EXCL behind pathsec: a symlink or a directory already
    at the scratch name is refused, never followed, written or removed."""
    victim = tmp_path / "victim.txt"
    victim.write_text("KEEP")
    tool = _xml_tool(_build_corpus(tmp_path))
    if plant == "symlink":
        try:
            os.symlink(victim, tool.write_file)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported on this platform")
    else:
        os.mkdir(tool.write_file)
    try:
        with pytest.raises((OSError, ValueError)):
            tool.build_preprocessed_file()
        tool.remove_preprocessed_file()
        assert os.path.lexists(tool.write_file)
        assert victim.read_text() == "KEEP"
    finally:
        if plant == "symlink":
            os.unlink(tool.write_file)
        else:
            os.rmdir(tool.write_file)


@posix_only
def test_scratch_dir_is_reallocated_once_it_stops_being_private(tmp_path):
    """A staging dir that has become group/world-writable is squattable
    (CWE-377): staging_tempdir() must hand out a fresh 0700 dir and the reader
    must keep working through it."""
    import stat

    from nltk.data import staging_tempdir

    reader = _reader(_build_corpus(tmp_path))
    reader.raw()
    old = staging_tempdir()
    os.chmod(old, 0o777)
    try:
        new = staging_tempdir()
        assert new != old and stat.S_IMODE(os.stat(new).st_mode) == 0o700
        assert reader.raw() == ["Zażółć gęślą jaźń."]
        assert (
            os.path.dirname(_xml_tool(_build_corpus(tmp_path / "b")).write_file) == new
        )
    finally:
        os.chmod(old, 0o700)


@pytest.mark.parametrize("method", ["raw", "words", "sents"])
def test_handle_query_closes_the_stream_before_cleanup(tmp_path, monkeypatch, method):
    """Windows refuses to remove an open file and remove_preprocessed_file()
    tolerates that refusal, so a read that fails while the view's stream is still
    open left the scratch copy behind there (seen on the Windows CI cell): every
    exit must close the stream first. Checked at the os.remove call itself."""
    from nltk.corpus.reader.nkjp import NKJPCorpus_Text_View
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    views = []

    def failing_read_block(self, stream, tagspec=None, elt_handler=None):
        views.append(self)
        raise ValueError("parse failed while the stream is open")

    real_remove = os.remove

    def checked_remove(path):
        assert all(view._stream is None for view in views), path
        return real_remove(path)

    monkeypatch.setattr(XMLCorpusView, "read_block", failing_read_block)
    monkeypatch.setattr(NKJPCorpus_Text_View, "read_block", failing_read_block)
    monkeypatch.setattr(os, "remove", checked_remove)
    with pytest.raises(ValueError, match="stream is open"):
        getattr(_reader(_build_corpus(tmp_path)), method)()
    assert views and all(view._stream is None for view in views)
    assert _scratch_files() == []
