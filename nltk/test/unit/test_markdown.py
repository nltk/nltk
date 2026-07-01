"""Regression tests for the quadratic-time DoS in NLTK's Markdown corpus reader
(``nltk.corpus.reader.markdown.CategorizedMarkdownCorpusReader.blockquote_reader``
and the identical ``list_reader``) -- CWE-407.

Both readers located each top-level block by calling ``tokens.index(...)`` twice
per block over the full flat token list produced for the whole document -- an
O(n) scan per block, i.e. O(n^2) when the document is made of many top-level
blockquotes/lists. The public ``blockquotes()``/``lists()`` entry points reach
these readers, so extracting blockquotes/lists from untrusted Markdown could be
driven into seconds-to-minutes of CPU with a small crafted document. Each block's
open/close index is now found with linear scans of the token list; ordinary
corpora read identically.
"""

import multiprocessing
import os
import sys
import traceback

import pytest

from nltk.corpus.reader.markdown import CategorizedMarkdownCorpusReader, List


def setup_module():
    pytest.importorskip("markdown_it")
    pytest.importorskip("mdit_plain")
    pytest.importorskip("mdit_py_plugins")


_DOC = """\
> first quote
> second line

Some paragraph.

> another quote
>
> > nested quote inside

- item a
- item b

1. one
2. two

> last quote

* bullet x
  - nested bullet
* bullet y
"""


def _reader(tmp_path, text, name="doc.md"):
    (tmp_path / name).write_text(text, encoding="utf-8")
    return CategorizedMarkdownCorpusReader(
        str(tmp_path), r".*\.md", cat_pattern=r"(.*)\.md"
    )


def test_blockquotes_reading_preserved(tmp_path):
    """blockquotes() returns the same top-level blocks (nested content included)."""
    r = _reader(tmp_path, _DOC)
    assert [b.content for b in r.blockquotes()] == [
        "first quote\nsecond line",
        "another quote\n\nnested quote inside",
        "last quote",
    ]


def test_lists_reading_preserved(tmp_path):
    """lists() returns the same top-level lists with their items and ordering."""
    r = _reader(tmp_path, _DOC)
    assert list(r.lists()) == [
        List(is_ordered=False, items=["item a", "item b"]),
        List(is_ordered=True, items=["one", "two"]),
        List(is_ordered=False, items=["bullet x", "nested bullet", "bullet y"]),
    ]


def _blockquotes_worker(root):
    """Read blockquotes() from a crafted corpus; exit 0 on success, 3 on error.

    On error the traceback is printed (and stderr flushed, since ``os._exit``
    skips normal shutdown) before exiting so a failure here is diagnosable in CI
    -- the parent process only sees the numeric exit code.
    """
    try:
        reader = CategorizedMarkdownCorpusReader(
            root, r".*\.md", cat_pattern=r"(.*)\.md"
        )
        list(reader.blockquotes())
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(3)


def test_blockquotes_is_linear_not_quadratic(tmp_path):
    """A document of many top-level blockquotes must not blow up quadratically.

    Run in a spawned process with a hard deadline: the single-pass reader returns
    quickly, while the previous tokens.index()-per-block version is O(n^2) and
    needs well over a minute at this size, so a regression is terminated and fails
    the test instead of pinning a core for the rest of the suite.
    """
    (tmp_path / "doc.md").write_text(
        "\n\n".join("> a" for _ in range(50_000)) + "\n", encoding="utf-8"
    )
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_blockquotes_worker, args=(str(tmp_path),))
    proc.start()
    proc.join(30)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        raise AssertionError(
            "blockquotes() did not finish in time: quadratic scan regressed"
        )
    assert proc.exitcode == 0, f"worker failed (exit {proc.exitcode})"
