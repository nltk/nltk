# Natural Language Toolkit: trusted-spawn symlink layout harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Symlinked tool installs at the trusted-spawn chokepoint (CWE-426/427/732).

#3887 made every executed binary go through ``pathsec.spawn_trusted``, whose
resolver refuses any ``..`` it meets, including one inside a symlink's own
text. That is how the standard package layouts are built: Homebrew's
``bin/dot -> ../Cellar/graphviz/<v>/bin/dot``, the python.org ``bin/python3 ->
../../../Library/...``, so ``dot2img`` refuses every such Graphviz install
(ekaf, #3887 comment 5969235326).

The default stays that refusal: a ``..`` met anywhere, in the caller's path or
in a link's text, is refused outright with a reason naming it, and nothing is
executed. The one way through is the keyword-only ``follow_link_parents=True``
on the Graphviz entry points (``dot2img``, ``DependencyGraph.to_image``,
``AlignedSent.to_image``), which the user passes explicitly per call; it
reaches ``spawn_trusted`` through the private ``_follow_link_parents`` walk
that resolves a ``..`` inside a link's text the way the kernel does and then
verifies every directory on the resolved chain, every link hop and its owner,
the hop bound and the final regular file. No other tool wrapper has the
keyword. Real files, real links, real ``chmod``, a canary binary that writes a
marker when it runs: every standard layout is refused by default with the
keyword named, runs the canary under the keyword and returns its real output;
every spoof is refused in BOTH modes with the reason naming the check and the
path, never naming the keyword, and the canary never runs; the teeth show
that removing each check lets a named spoof through.
"""
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from nltk import pathsec

POSIX = pytest.mark.skipif(
    os.name != "posix", reason="symlinks and the POSIX ownership model"
)
WINDOWS = pytest.mark.skipif(
    os.name != "nt", reason="NTFS junctions and reparse points need Windows"
)
MODES = ("default", "keyword")

#: The canary: swallows stdin, drops a marker beside the file that ran, echoes.
STUB = '#!/bin/sh\ncat >/dev/null\n: > "$0.ran" 2>/dev/null\necho "GRAPHVIZ-STUB $*"\n'
GRAPH = "digraph { a -> b }"
KEYWORD = "follow_link_parents"
PRIVATE_KEYWORD = "_follow_link_parents"


@pytest.fixture
def home():
    """A private root under $HOME: a private chain on every CI runner, which a
    shared sticky ``/tmp`` is not (the resolver refuses it by design)."""
    root = Path(tempfile.mkdtemp(prefix=".nltk_symlink_layouts_", dir=Path.home()))
    os.chmod(root, 0o700)
    try:
        yield root
    finally:
        for dirpath, dirnames, _ in os.walk(root):
            for name in dirnames:
                try:
                    os.chmod(os.path.join(dirpath, name), 0o700)
                except OSError:
                    pass
        shutil.rmtree(root, ignore_errors=True)


def _tool(path, mode=0o755):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STUB, encoding="utf-8")
    path.chmod(mode)
    return str(path)


def _dir(path, mode=0o755):
    Path(path).mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)
    return str(path)


def _ln(target, link):
    link = Path(link)
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, link)
    return str(link)


def _same(a, b):
    return os.path.realpath(str(a)) == os.path.realpath(str(b))


def _ran(root):
    """Every canary marker under *root*: empty means nothing was executed."""
    return sorted(
        os.path.join(dirpath, name)
        for dirpath, _, names in os.walk(root)
        for name in names
        if name.endswith(".ran")
    )


def _resolve(entry, mode):
    if mode == "keyword":
        return pathsec._resolve_trusted(entry, _follow_link_parents=True)
    return pathsec.resolve_trusted_executable(entry)


def _walk(entry, mode, why):
    """One verification walk, recording its reason in *why* as it happens."""
    return pathsec._resolve_trusted(
        entry, why, _follow_link_parents=(mode == "keyword")
    )


def _reason(entry, mode):
    return pathsec._refusal(entry, _follow_link_parents=(mode == "keyword"))[0]


def _run(entry, mode):
    kw = {PRIVATE_KEYWORD: True} if mode == "keyword" else {}
    proc = pathsec.spawn_trusted(
        entry,
        ["-Tsvg"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kw,
    )
    out = proc.communicate(GRAPH.encode())[0].decode()
    return proc, out


def _dot2img(monkeypatch, bindir, mode):
    from nltk.parse import dependencygraph

    monkeypatch.setenv("PATH", bindir)
    kw = {KEYWORD: True} if mode == "keyword" else {}
    return dependencygraph.dot2img(GRAPH, "svg", **kw)


# --------------------------------------------------------------------------- #
# Layouts: (bin dir to put on PATH, entry to run, real file or None).           #
# --------------------------------------------------------------------------- #


def homebrew(r):
    """Intel Homebrew: ``usr/local/bin/dot -> ../Cellar/graphviz/15.1.1/bin/dot``;
    inside the Cellar ``circo -> dot`` and ``fdp -> dot``, as ``brew install
    graphviz`` lays it out."""
    real = _tool(f"{r}/usr/local/Cellar/graphviz/15.1.1/bin/dot")
    _ln("dot", f"{r}/usr/local/Cellar/graphviz/15.1.1/bin/circo")
    _ln("dot", f"{r}/usr/local/Cellar/graphviz/15.1.1/bin/fdp")
    _ln("../Cellar/graphviz/15.1.1/bin/dot", f"{r}/usr/local/bin/dot")
    _ln("../Cellar/graphviz/15.1.1/bin/circo", f"{r}/usr/local/bin/circo")
    return f"{r}/usr/local/bin", f"{r}/usr/local/bin/dot", real


def homebrew_apple_silicon(r):
    """Apple-silicon Homebrew: the same link under ``opt/homebrew``."""
    real = _tool(f"{r}/opt/homebrew/Cellar/graphviz/15.1.1/bin/dot")
    _ln("dot", f"{r}/opt/homebrew/Cellar/graphviz/15.1.1/bin/circo")
    _ln("../Cellar/graphviz/15.1.1/bin/dot", f"{r}/opt/homebrew/bin/dot")
    _ln("../Cellar/graphviz/15.1.1/bin/circo", f"{r}/opt/homebrew/bin/circo")
    return f"{r}/opt/homebrew/bin", f"{r}/opt/homebrew/bin/dot", real


def homebrew_sibling_two_hops(r):
    """``prefix/bin/circo -> ../Cellar/.../bin/circo -> dot``."""
    bindir, _, real = homebrew(r)
    return bindir, f"{bindir}/circo", real


def homebrew_opt_dir_link(r):
    """``prefix/opt/graphviz -> ../Cellar/graphviz/15.1.1`` (a directory link
    with ``..``), then ``bin/dot`` below it."""
    real = _tool(f"{r}/Cellar/graphviz/15.1.1/bin/dot")
    _ln("../Cellar/graphviz/15.1.1", f"{r}/opt/graphviz")
    return f"{r}/opt/graphviz/bin", f"{r}/opt/graphviz/bin/dot", real


def chain_two_deep(r):
    real = _tool(f"{r}/real/dot")
    _ln(real, f"{r}/lib/dot")
    _ln("../lib/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def chain_three_deep(r):
    real = _tool(f"{r}/d/dot")
    _ln("../d/dot", f"{r}/c/dot")
    _ln("../c/dot", f"{r}/b/dot")
    _ln("../b/dot", f"{r}/a/dot")
    return f"{r}/a", f"{r}/a/dot", real


def relative_link(r):
    real = _tool(f"{r}/real/dot")
    _ln("../real/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def pythonorg_three_up(r):
    """``usr/local/bin/dot -> ../../../Library/Frameworks/GV/bin/dot``."""
    real = _tool(f"{r}/Library/Frameworks/GV/bin/dot")
    _ln("../../../Library/Frameworks/GV/bin/dot", f"{r}/usr/local/bin/dot")
    return f"{r}/usr/local/bin", f"{r}/usr/local/bin/dot", real


def overclimb_clamps_at_root(r):
    """More ``..`` than the depth: the kernel stays at ``/``, so does the walk."""
    real = _tool(f"{r}/real/dot")
    _ln("../" * 40 + real.lstrip("/"), f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def inert_components(r):
    """``./``, ``//`` and ``/./`` runs in a link's text are inert."""
    real = _tool(f"{r}/real/dot")
    _ln("./..//real/./dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def chain_at_the_bound(r):
    real = _tool(f"{r}/real/dot")
    n = pathsec._MAX_LINK_HOPS
    for i in range(n):
        _ln(real if i == 0 else f"../l{i - 1}/dot", f"{r}/l{i}/dot")
    return f"{r}/l{n - 1}", f"{r}/l{n - 1}/dot", real


def parent_of_a_writable_dir_is_not_inside_it(r):
    """``bin/dot -> ../ww/../real/dot``: ``ww/..`` is ``ww``'s parent whatever
    ``ww`` holds, and nothing in ``ww`` is ever descended into or read."""
    real = _tool(f"{r}/real/dot")
    _dir(f"{r}/ww", 0o777)
    _ln("../ww/../real/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def dotdot_landing_on_a_dir_link(r):
    """``bin/dot -> ../lib/dot`` where ``lib -> ../real_lib`` is itself a
    directory link with ``..``: a ``..`` that lands on a link, two climbs."""
    real = _tool(f"{r}/real_lib/dot")
    _ln("../real_lib", f"{r}/pkg/lib")
    _ln("../lib/dot", f"{r}/pkg/bin/dot")
    return f"{r}/pkg/bin", f"{r}/pkg/bin/dot", real


#: Layouts with a ``..`` in some link's text: refused by default, run under
#: the keyword.
CLIMBING = {
    "homebrew": homebrew,
    "homebrew_apple_silicon": homebrew_apple_silicon,
    "homebrew_sibling_two_hops": homebrew_sibling_two_hops,
    "homebrew_opt_dir_link": homebrew_opt_dir_link,
    "chain_two_deep": chain_two_deep,
    "chain_three_deep": chain_three_deep,
    "relative_link": relative_link,
    "pythonorg_three_up": pythonorg_three_up,
    "overclimb_clamps_at_root": overclimb_clamps_at_root,
    "inert_components": inert_components,
    "chain_at_the_bound": chain_at_the_bound,
    "parent_of_a_writable_dir_is_not_inside_it": parent_of_a_writable_dir_is_not_inside_it,
    "dotdot_landing_on_a_dir_link": dotdot_landing_on_a_dir_link,
}


def multicall(r):
    """Debian multi-call: one real binary, ``dot`` / ``neato`` / ``circo``
    sibling links to it, no ``..`` anywhere."""
    real = _tool(f"{r}/usr/bin/graphviz")
    for name in ("dot", "neato", "circo"):
        _ln("graphviz", f"{r}/usr/bin/{name}")
    return f"{r}/usr/bin", f"{r}/usr/bin/dot", real


def absolute_link(r):
    real = _tool(f"{r}/real/dot")
    _ln(real, f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def alternatives(r):
    """Debian alternatives: ``usr/bin/dot -> /etc/alternatives/dot ->
    /usr/bin/dot-real``, absolute at both hops."""
    real = _tool(f"{r}/usr/bin/dot-real")
    _ln(real, f"{r}/etc/alternatives/dot")
    _ln(f"{r}/etc/alternatives/dot", f"{r}/usr/bin/dot")
    return f"{r}/usr/bin", f"{r}/usr/bin/dot", real


def hard_linked_private_binary(r):
    """The real binary also hard-linked from a world-writable directory: the
    inode's owner and mode are what they are wherever it is named, so the
    private path still runs (and the writable path is refused, below)."""
    real = _tool(f"{r}/bin/dot")
    _dir(f"{r}/ww")
    os.link(real, f"{r}/ww/dot")
    os.chmod(f"{r}/ww", 0o777)
    return f"{r}/bin", f"{r}/bin/dot", real


#: Layouts with no ``..`` anywhere: run in both modes.
PLAIN = {
    "multicall": multicall,
    "absolute_link": absolute_link,
    "alternatives": alternatives,
    "hard_linked_private_binary": hard_linked_private_binary,
}


def group_writable_target_dir(r):
    real = _tool(f"{r}/gw/dot")
    os.chmod(f"{r}/gw", 0o775)
    _ln("../gw/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "group-writable", f"{r}/gw"


def world_writable_sticky_target_dir(r):
    """The Linux ``/tmp`` shape on the chain: sticky, world-writable."""
    real = _tool(f"{r}/ww/dot")
    os.chmod(f"{r}/ww", 0o1777)
    _ln("../ww/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", f"{r}/ww"


def world_writable_intermediate_dir(r):
    """``bin/dot -> ../ww/hop``, ``ww`` 0777, ``ww/hop -> ../private/dot``:
    the hop is held in a directory another user could repoint."""
    real = _tool(f"{r}/private/dot")
    _dir(f"{r}/ww")
    _ln("../private/dot", f"{r}/ww/hop")
    os.chmod(f"{r}/ww", 0o777)
    _ln("../ww/hop", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", f"{r}/ww"


def world_writable_holder(r):
    """The link's own directory is world-writable: the link can be swapped."""
    real = _tool(f"{r}/private/dot")
    _dir(f"{r}/ww")
    _ln("../private/dot", f"{r}/ww/dot")
    os.chmod(f"{r}/ww", 0o777)
    return f"{r}/ww", f"{r}/ww/dot", real, "world-writable", f"{r}/ww"


def group_writable_target_file(r):
    real = _tool(f"{r}/real/dot", 0o775)
    _ln("../real/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "group-writable", real


def world_writable_target_file(r):
    real = _tool(f"{r}/real/dot", 0o777)
    _ln("../real/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", real


def symlink_loop(r):
    """A loop made of ``..`` hops: ``bin/dot -> ../x/dot -> ../bin/dot``."""
    _ln("../x/dot", f"{r}/bin/dot")
    _ln("../bin/dot", f"{r}/x/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "longer than", "hops"


def chain_over_the_bound(r):
    real = _tool(f"{r}/real/dot")
    n = pathsec._MAX_LINK_HOPS + 1
    for i in range(n):
        _ln(real if i == 0 else f"../l{i - 1}/dot", f"{r}/l{i}/dot")
    return f"{r}/l{n - 1}", f"{r}/l{n - 1}/dot", real, "longer than", "hops"


def dangling(r):
    _ln("../nowhere/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "cannot be inspected", f"{r}/nowhere"


def link_to_a_directory(r):
    _dir(f"{r}/adir")
    _ln("../adir", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "not a regular file", f"{r}/adir"


def link_to_a_fifo(r):
    _dir(f"{r}/fifo")
    os.mkfifo(f"{r}/fifo/dot")
    _ln("../fifo/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "not a regular file", f"{r}/fifo/dot"


def link_to_a_socket(r):
    _dir(f"{r}/sock")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(f"{r}/sock/dot")
    except OSError as exc:
        pytest.skip(f"cannot bind a unix socket here ({exc})")
    finally:
        sock.close()
    _ln("../sock/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "not a regular file", f"{r}/sock/dot"


def link_to_a_device(r):
    _ln("/dev/null", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "not a regular file", "/dev/null"


def writable_dir_descended_into_through_dotdot(r):
    """``bin/dot -> ../ww/sub/../dot``: ``ww`` is entered this time, and it is
    world-writable."""
    real = _tool(f"{r}/ww/dot")
    _dir(f"{r}/ww/sub")
    os.chmod(f"{r}/ww", 0o777)
    _ln("../ww/sub/../dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", f"{r}/ww"


def climb_above_the_root_into_writable_and_back(r):
    """``priv/bin/dot -> ../../ww/pkg/bin/dot``: the text climbs out of the
    private tree into a world-writable one and back down into it."""
    real = _tool(f"{r}/ww/pkg/bin/dot")
    os.chmod(f"{r}/ww", 0o777)
    _ln("../../ww/pkg/bin/dot", f"{r}/priv/bin/dot")
    return f"{r}/priv/bin", f"{r}/priv/bin/dot", real, "world-writable", f"{r}/ww"


def dotdot_landing_on_a_dir_link_into_writable(r):
    """``pkg/bin/dot -> ../lib/dot`` with ``pkg/lib -> ../ww_lib`` 0777."""
    real = _tool(f"{r}/ww_lib/dot")
    os.chmod(f"{r}/ww_lib", 0o777)
    _ln("../ww_lib", f"{r}/pkg/lib")
    _ln("../lib/dot", f"{r}/pkg/bin/dot")
    return f"{r}/pkg/bin", f"{r}/pkg/bin/dot", real, "world-writable", f"{r}/ww_lib"


def absolute_link_into_writable(r):
    real = _tool(f"{r}/ww/dot")
    os.chmod(f"{r}/ww", 0o777)
    _ln(real, f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", f"{r}/ww"


def hard_link_in_a_writable_dir(r):
    """The writable path of :func:`hard_linked_private_binary`."""
    bindir, entry, real = hard_linked_private_binary(r)
    return f"{r}/ww", f"{r}/ww/dot", real, "world-writable", f"{r}/ww"


def newline_in_link_text(r):
    """A link whose text holds a line break, to a real private file whose
    directory is named with one: the kernel would follow it; the walk refuses
    the control character before interpreting the text."""
    real = _tool(f"{r}/re\nal/dot")
    _ln("../re\nal/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "control character", f"{r}/bin/dot"


def escape_in_link_text(r):
    real = _tool(f"{r}/real/dot")
    _ln("../real/dot\x1b[0m", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "control character", f"{r}/bin/dot"


#: Spoofs with a ``..`` somewhere in the chain, or none: refused in both
#: modes, by the check named.
SPOOF = {
    "group_writable_target_dir": group_writable_target_dir,
    "world_writable_sticky_target_dir": world_writable_sticky_target_dir,
    "world_writable_intermediate_dir": world_writable_intermediate_dir,
    "world_writable_holder": world_writable_holder,
    "group_writable_target_file": group_writable_target_file,
    "world_writable_target_file": world_writable_target_file,
    "symlink_loop": symlink_loop,
    "chain_over_the_bound": chain_over_the_bound,
    "dangling": dangling,
    "link_to_a_directory": link_to_a_directory,
    "link_to_a_fifo": link_to_a_fifo,
    "link_to_a_socket": link_to_a_socket,
    "link_to_a_device": link_to_a_device,
    "writable_dir_descended_into_through_dotdot": writable_dir_descended_into_through_dotdot,
    "climb_above_the_root_into_writable_and_back": climb_above_the_root_into_writable_and_back,
    "dotdot_landing_on_a_dir_link_into_writable": dotdot_landing_on_a_dir_link_into_writable,
    "absolute_link_into_writable": absolute_link_into_writable,
    "hard_link_in_a_writable_dir": hard_link_in_a_writable_dir,
    "newline_in_link_text": newline_in_link_text,
    "escape_in_link_text": escape_in_link_text,
}


def _foreign_lstat(victim, uid):
    """An ``lstat`` that reports *victim* as owned by *uid*."""
    true_lstat = os.lstat

    def lstat(path, *args, **kwargs):
        st = true_lstat(path, *args, **kwargs)
        if os.fspath(path) == victim:
            fields = list(st)
            fields[stat.ST_UID] = uid
            st = os.stat_result(tuple(fields))
        return st

    return lstat


# --------------------------------------------------------------------------- #
# Climbing layouts: refused by default, naming the '..'; run under the keyword. #
# --------------------------------------------------------------------------- #


@POSIX
class TestClimbingLayouts:
    @pytest.mark.parametrize("layout", sorted(CLIMBING), ids=sorted(CLIMBING))
    def test_refused_by_default_naming_the_link_and_its_dotdot(
        self, home, monkeypatch, layout
    ):
        bindir, entry, real = CLIMBING[layout](home)
        assert pathsec.resolve_trusted_executable(entry) is None, layout
        reason = pathsec.untrusted_executable_reason(entry)
        assert "'..' component is not followed by default" in reason, (layout, reason)
        assert "symlink " in reason and "points to" in reason
        with pytest.raises(pathsec.TrustError) as excinfo:
            _run(entry, "default")
        assert excinfo.value.link_parent is True
        assert reason in str(excinfo.value) and "chmod g-w,o-w" in str(excinfo.value)
        if os.path.basename(entry) == "dot" and os.path.isfile(entry):
            # the Graphviz entry point names the keyword and the call
            with pytest.raises(Exception, match="Cannot create image") as excinfo:
                _dot2img(monkeypatch, bindir, "default")
            message = str(excinfo.value)
            assert reason in message and f"dot2img(..., {KEYWORD}=True)" in message
            assert isinstance(excinfo.value.__cause__, pathsec.TrustError)
        assert _ran(home) == [], layout

    @pytest.mark.parametrize("layout", sorted(CLIMBING), ids=sorted(CLIMBING))
    def test_runs_under_the_keyword_by_its_resolved_path(
        self, home, monkeypatch, layout
    ):
        bindir, entry, real = CLIMBING[layout](home)
        assert os.path.realpath(entry) != entry  # a link somewhere on the way
        got = _resolve(entry, "keyword")
        assert got is not None and _same(got, real), (layout, got)
        assert not os.path.islink(got)  # the resolved path, never the link
        assert _reason(entry, "keyword") is None
        proc, out = _run(entry, "keyword")
        assert _same(proc.args[0], real) and proc.args[0] == got
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg", (layout, out)
        assert _ran(home) == [real + ".ran"]
        os.unlink(real + ".ran")
        # the OS's own lookup has its own ELOOP limit (32 on macOS, 40 on
        # Linux), so the PATH finder sees the chain at the bound only where the
        # OS follows it; the walker and the spawn above did either way
        if os.path.basename(entry) == "dot" and os.path.isfile(entry):
            assert (
                _dot2img(monkeypatch, bindir, "keyword").strip()
                == "GRAPHVIZ-STUB -Tsvg"
            )
            assert _ran(home) == [real + ".ran"]
        else:
            assert layout in ("homebrew_sibling_two_hops", "chain_at_the_bound")

    @pytest.mark.parametrize("layout", sorted(PLAIN), ids=sorted(PLAIN))
    @pytest.mark.parametrize("mode", MODES)
    def test_a_layout_without_dotdot_runs_in_both_modes(
        self, home, monkeypatch, layout, mode
    ):
        bindir, entry, real = PLAIN[layout](home)
        got = _resolve(entry, mode)
        assert got is not None and _same(got, real), (layout, mode, got)
        assert not os.path.islink(got) and _reason(entry, mode) is None
        proc, out = _run(entry, mode)
        assert proc.args[0] == got and out.strip() == "GRAPHVIZ-STUB -Tsvg"
        assert _ran(home) == [real + ".ran"]
        os.unlink(real + ".ran")
        assert _dot2img(monkeypatch, bindir, mode).strip() == "GRAPHVIZ-STUB -Tsvg"

    def test_ekaf_reproduction_on_the_homebrew_layout(self, home, monkeypatch):
        """The exact two lines from the report, with the Homebrew shape on
        PATH: refused with the keyword named; the keyword renders."""
        bindir, _, real = homebrew(home)
        monkeypatch.setenv("PATH", bindir)
        from nltk.parse.dependencygraph import dot2img

        with pytest.raises(Exception, match=f"dot2img\\(\\.\\.\\., {KEYWORD}=True\\)"):
            dot2img(GRAPH)
        assert _ran(home) == []
        assert dot2img(GRAPH, follow_link_parents=True).strip() == "GRAPHVIZ-STUB -Tsvg"
        assert _ran(home) == [real + ".ran"]

    def test_the_graph_entry_points_on_the_homebrew_layout(self, home, monkeypatch):
        """``DependencyGraph`` and ``AlignedSent``: the IPython hook takes no
        argument and is refused; ``to_image`` with the keyword renders."""
        from nltk.parse.dependencygraph import DependencyGraph
        from nltk.translate.api import AlignedSent, Alignment

        bindir, _, real = homebrew(home)
        monkeypatch.setenv("PATH", bindir)
        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        for hook in (dg._repr_svg_, sent._repr_svg_, dg.to_image, sent.to_image):
            with pytest.raises(Exception, match="not followed by default") as excinfo:
                hook()
            assert f"{KEYWORD}=True" in str(excinfo.value)
        assert _ran(home) == []
        for method in (dg.to_image, sent.to_image):
            assert method(follow_link_parents=True).strip() == "GRAPHVIZ-STUB -Tsvg"
            assert (
                method("png", follow_link_parents=True).strip()
                == b"GRAPHVIZ-STUB -Tpng"
            )
        assert _ran(home) == [real + ".ran"]

    def test_a_link_before_the_dotdot_is_resolved_first_never_folded(self, home):
        """``holder/dot -> sub/../real`` with ``holder/sub`` a link to another
        private directory: the kernel resolves ``sub`` first, so ``..`` is
        that directory's parent and ``real`` is the file beside it. A lexical
        fold would have run ``holder/real`` instead, a different file."""
        kernel = _tool(f"{home}/other/real")
        folded = _tool(f"{home}/holder/real")
        _dir(f"{home}/other/inner")
        _ln(f"{home}/other/inner", f"{home}/holder/sub")
        entry = _ln("sub/../real", f"{home}/holder/dot")
        assert pathsec.resolve_trusted_executable(entry) is None
        got = _resolve(entry, "keyword")
        assert _same(got, kernel) and not _same(got, folded)
        assert _same(os.path.realpath(entry), kernel)  # the OS agrees
        joined = os.path.join(f"{home}/holder", "sub/../real")
        assert _same(os.path.normpath(joined), folded)  # what folding gives

    @pytest.mark.parametrize(
        "spelling", ["case_fold", "nfd_for_nfc"], ids=["case_fold", "nfd_for_nfc"]
    )
    def test_a_lookalike_component_is_judged_on_the_filesystem(self, home, spelling):
        """``../REAL/dot`` for ``real``, ``cafe`` + combining acute for ``caf``
        + e-acute: on a case- or normalisation-insensitive filesystem (macOS)
        the spelled component names the same verified directory and the
        resolved file is the same inode as the real tool; elsewhere it names
        nothing and is refused. Neither mode runs anything unverified."""
        if spelling == "case_fold":
            real_dir, spelled = "real", "REAL"
        else:
            real_dir, spelled = "caf" + chr(0xE9), "cafe" + chr(0x301)
        real = _tool(f"{home}/{real_dir}/dot")
        entry = _ln(f"../{spelled}/dot", f"{home}/bin/dot")
        assert pathsec.resolve_trusted_executable(entry) is None
        assert "'..' component" in pathsec.untrusted_executable_reason(entry)
        got = _resolve(entry, "keyword")
        if got is None:
            assert "cannot be inspected" in _reason(entry, "keyword")
            with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
                _run(entry, "keyword")
            assert _ran(home) == []
        else:
            assert os.path.samefile(got, real) and not os.path.islink(got)
            assert pathsec.is_private_dir(os.path.dirname(got))
            proc, out = _run(entry, "keyword")
            assert out.strip() == "GRAPHVIZ-STUB -Tsvg"
            assert [os.path.samefile(p[: -len(".ran")], real) for p in _ran(home)] == [
                True
            ]


# --------------------------------------------------------------------------- #
# Every spoof is refused in both modes, with the reason naming the check and   #
# the path, never the keyword, and nothing runs.                               #
# --------------------------------------------------------------------------- #


@POSIX
class TestSpoofLayoutsAreRefused:
    @pytest.mark.parametrize("layout", sorted(SPOOF), ids=sorted(SPOOF))
    @pytest.mark.parametrize("mode", MODES)
    def test_refused_with_the_reason(self, home, monkeypatch, layout, mode):
        bindir, entry, real, check, named = SPOOF[layout](home)
        assert _resolve(entry, mode) is None, (layout, mode)
        reason = _reason(entry, mode)
        assert check in reason and named in reason, (layout, mode, reason)
        with pytest.raises(pathsec.TrustError) as excinfo:
            _run(entry, mode)
        message = str(excinfo.value)
        assert message.startswith("refusing to execute untrusted path")
        assert reason in message and "chmod g-w,o-w" in message
        # the keyword would not help, so it is never suggested
        assert excinfo.value.link_parent is False
        assert KEYWORD not in message
        if real is not None and os.path.isfile(entry):
            # the Graphviz entry point surfaces the same reason, and the
            # trusted spawn is its cause
            with pytest.raises(Exception, match="Cannot create image") as excinfo:
                _dot2img(monkeypatch, bindir, mode)
            assert reason in str(excinfo.value)
            assert KEYWORD not in str(excinfo.value)
            assert isinstance(excinfo.value.__cause__, pathsec.TrustError)
        assert _ran(home) == [], (layout, mode)

    @pytest.mark.parametrize("mode", MODES)
    def test_a_link_owned_by_another_user_is_refused(self, home, monkeypatch, mode):
        """Simulated (no root here): ``lstat`` of one link reports a foreign
        uid, at the entry and in the middle of a chain. Its holder is private,
        so this is the link-owner check alone."""
        real = _tool(f"{home}/real/dot")
        mid = _ln("../real/dot", f"{home}/mid/dot")
        entry = _ln("../mid/dot", f"{home}/bin/dot")
        assert _same(_resolve(entry, "keyword"), real)
        foreign = os.geteuid() + 4242
        for victim in (entry, mid):
            monkeypatch.setattr(pathsec.os, "lstat", _foreign_lstat(victim, foreign))
            assert _resolve(entry, mode) is None, (victim, mode)
            reason = _reason(entry, mode)
            assert f"symlink {victim!r} is owned by uid {foreign}" in reason, mode
            with pytest.raises(pathsec.TrustError, match="owned by uid") as excinfo:
                _run(entry, mode)
            assert KEYWORD not in str(excinfo.value)
            monkeypatch.undo()
        assert _ran(home) == []
        assert _same(_resolve(entry, "keyword"), real)

    @pytest.mark.parametrize("mode", MODES)
    def test_a_root_owned_link_in_a_writable_dir_and_the_reverse(
        self, home, monkeypatch, mode
    ):
        """A link root created in a directory anyone can write: the directory
        refuses it (the link can be swapped). A link another user created in
        a root-owned directory: the link owner refuses it."""
        real = _tool(f"{home}/real/dot")
        _dir(f"{home}/ww")
        entry = _ln("../real/dot", f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        monkeypatch.setattr(pathsec.os, "lstat", _foreign_lstat(entry, 0))
        assert _resolve(entry, mode) is None
        reason = _reason(entry, mode)
        assert "world-writable" in reason and f"{home}/ww" in reason
        monkeypatch.undo()
        os.chmod(f"{home}/ww", 0o755)
        true_stat = os.stat

        def root_dir(path, *args, **kwargs):
            st = true_stat(path, *args, **kwargs)
            if os.fspath(path) == f"{home}/ww":
                fields = list(st)
                fields[stat.ST_UID] = 0
                st = os.stat_result(tuple(fields))
            return st

        monkeypatch.setattr(pathsec.os, "stat", root_dir)
        monkeypatch.setattr(
            pathsec.os, "lstat", _foreign_lstat(entry, os.geteuid() + 4242)
        )
        assert _resolve(entry, mode) is None
        reason = _reason(entry, mode)
        assert f"symlink {entry!r} is owned by uid" in reason
        with pytest.raises(pathsec.TrustError, match="owned by uid"):
            _run(entry, mode)
        assert _ran(home) == []

    @pytest.mark.parametrize("mode", MODES)
    def test_a_climb_into_the_shared_tmp_is_refused(self, home, mode):
        """``bin/dot -> ../../..(to /)/tmp/<dir>/dot``: the sticky ``/tmp``
        on the way is world-writable, so the chain is refused there."""
        tmp = "/tmp"
        if not (os.path.isdir(tmp) and os.stat(tmp).st_mode & stat.S_ISVTX):
            pytest.skip("/tmp is not a sticky world-writable dir here")
        plant = tempfile.mkdtemp(prefix="nltk_symlink_spoof_", dir=tmp)
        try:
            real = _tool(f"{plant}/dot")
            entry = _ln("../" * 40 + real.lstrip("/"), f"{home}/bin/dot")
            assert _resolve(entry, mode) is None
            reason = _reason(entry, mode)
            assert "world-writable" in reason and "tmp" in reason
            with pytest.raises(pathsec.TrustError) as excinfo:
                _run(entry, mode)
            assert KEYWORD not in str(excinfo.value)
            assert not os.path.exists(real + ".ran")
        finally:
            shutil.rmtree(plant, ignore_errors=True)

    @pytest.mark.parametrize("mode", MODES)
    def test_the_callers_own_dotdot_is_never_folded(self, home, mode):
        """A ``..`` in the target the caller hands over is refused in both
        modes, even when it folds to a trusted file and even when it is the
        resolved path of a link: an unresolved name before it could hide a
        link, and a configured location is never allowed one."""
        real = _tool(f"{home}/real/dot")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        resolved = _resolve(entry, "keyword")
        for spelled in (
            f"{home}/bin/../real/dot",
            f"{home}/real/../real/dot",
            os.path.join(os.path.dirname(resolved), os.pardir, "real", "dot"),
        ):
            assert _same(os.path.realpath(spelled), real)
            assert _resolve(spelled, mode) is None, (spelled, mode)
            reason = _reason(spelled, mode)
            assert "'..' component" in reason and "not followed" not in reason
            with pytest.raises(pathsec.TrustError, match="'..' component") as excinfo:
                _run(spelled, mode)
            assert KEYWORD not in str(excinfo.value)
        assert _ran(home) == []

    def test_relative_and_odd_targets_name_their_reason(self, home):
        real = _tool(f"{home}/bin/dot")
        for mode in MODES:
            assert "not absolute" in _reason("bin/dot", mode)
            assert "NUL" in _reason(real + "\x00", mode)
            assert "not a str path" in _reason(7, mode)
            assert "not a str path" in _reason(None, mode)
            missing = f"{home}/nowhere/dot"
            assert "cannot be inspected" in _reason(missing, mode)
            assert _reason(real, mode) is None

    @pytest.mark.parametrize("mode", MODES)
    def test_a_hop_repointed_between_lstat_and_readlink_is_rewalked(
        self, home, monkeypatch, mode
    ):
        """TOCTOU on a middle hop: the link is repointed into a world-writable
        directory after its owner was checked and before its text was read.
        The text actually read is the one walked, from the root, so the
        writable directory it now lands in refuses it; nothing runs."""
        real = _tool(f"{home}/real/dot")
        decoy = _tool(f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        mid = _ln("../real/dot", f"{home}/mid/dot")
        entry = _ln("../mid/dot", f"{home}/bin/dot")
        true_readlink = os.readlink

        def readlink(path, *args, **kwargs):
            if os.fspath(path) == mid and true_readlink(mid) == "../real/dot":
                os.unlink(mid)
                os.symlink("../ww/dot", mid)
            return true_readlink(path, *args, **kwargs)

        monkeypatch.setattr(pathsec.os, "readlink", readlink)
        assert _resolve(entry, mode) is None
        reason = _reason(entry, mode)
        assert "world-writable" in reason and f"{home}/ww" in reason
        with pytest.raises(pathsec.TrustError, match="world-writable"):
            _run(entry, mode)
        assert _ran(home) == [] and os.path.exists(decoy) and os.path.exists(real)

    @pytest.mark.parametrize("mode", MODES)
    def test_a_final_component_swapped_for_a_link_fails_the_open(
        self, home, monkeypatch, mode
    ):
        """TOCTOU on the final file: between the ``lstat`` that saw a regular
        file and the ``open``, the file is replaced by a symlink into a
        world-writable directory. ``O_NOFOLLOW`` refuses the open, so the
        inode judged can only be the one at that path; nothing runs."""
        real = _tool(f"{home}/real/dot")
        decoy = _tool(f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        entry = real if mode == "default" else _ln("../real/dot", f"{home}/bin/dot")
        true_lstat = os.lstat
        seen = []

        def lstat(path, *args, **kwargs):
            st = true_lstat(path, *args, **kwargs)
            if os.fspath(path) == real:
                seen.append(path)
                if len(seen) == 2:  # the resolver's own lstat, after the walk
                    os.unlink(real)
                    os.symlink(decoy, real)
            return st

        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        why = pathsec._Why()
        assert _walk(entry, mode, why) is None
        swapped = len(seen)  # os.path.islink below goes through the patch too
        assert os.path.islink(real) and swapped == 2
        assert "cannot be opened for verification" in "; ".join(why)
        os.unlink(real)
        _tool(real)
        seen.clear()
        # the spawn is refused; its diagnostic walk runs after the swap, so the
        # reason it reports is the link it now finds, into the writable dir
        with pytest.raises(pathsec.TrustError, match="world-writable") as excinfo:
            _run(entry, mode)
        assert f"{home}/ww" in str(excinfo.value) and KEYWORD not in str(excinfo.value)
        assert _ran(home) == []

    @pytest.mark.parametrize("mode", MODES)
    def test_a_final_component_replaced_by_another_file_is_seen(
        self, home, monkeypatch, mode
    ):
        """The same window, the file renamed over by another regular file:
        the inode opened is not the one inspected, and that is the reason."""
        real = _tool(f"{home}/real/dot")
        other = _tool(f"{home}/real/other")
        entry = real if mode == "default" else _ln("../real/dot", f"{home}/bin/dot")
        true_lstat = os.lstat
        seen = []

        def lstat(path, *args, **kwargs):
            st = true_lstat(path, *args, **kwargs)
            if os.fspath(path) == real:
                seen.append(path)
                if len(seen) == 2:
                    os.replace(other, real)
            return st

        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        assert _resolve(entry, mode) is None
        _tool(other)
        seen.clear()
        assert "changed while it was being verified" in _reason(entry, mode)
        assert _ran(home) == []


# --------------------------------------------------------------------------- #
# Teeth: removing each check lets a named spoof through.                       #
# --------------------------------------------------------------------------- #


@POSIX
class TestTeeth:
    def test_without_the_default_dotdot_refusal_the_homebrew_layout_runs(self, home):
        """The only difference between the default walk and the private one is
        the refusal of a ``..`` in a link's text: take it away and Homebrew's
        chain resolves to the real file. The default therefore IS that check."""
        _, entry, real = homebrew(home)
        assert pathsec.resolve_trusted_executable(entry) is None
        assert pathsec._resolve_private(entry) is None
        assert _same(pathsec._resolve_private(entry, _follow_link_parents=True), real)
        assert _same(pathsec._resolve_trusted(entry, _follow_link_parents=True), real)

    @pytest.mark.parametrize("mode", MODES)
    def test_without_the_link_owner_check_a_foreign_link_runs(
        self, home, monkeypatch, mode
    ):
        real = _tool(f"{home}/real/dot")
        entry = _ln(real, f"{home}/bin/dot")
        monkeypatch.setattr(
            pathsec.os, "lstat", _foreign_lstat(entry, os.geteuid() + 4242)
        )
        assert _resolve(entry, mode) is None
        monkeypatch.setattr(pathsec, "_link_owner_problem", lambda path, st: None)
        assert _same(_resolve(entry, mode), real)

    def test_without_the_hop_bound_an_overlong_chain_runs(self, home, monkeypatch):
        _, entry, real, _, _ = chain_over_the_bound(home)
        assert _resolve(entry, "keyword") is None
        monkeypatch.setattr(pathsec, "_MAX_LINK_HOPS", 10_000)
        assert _same(_resolve(entry, "keyword"), real)

    def test_without_the_directory_check_a_dotdot_into_a_writable_dir_runs(
        self, home, monkeypatch
    ):
        """Under the keyword the directory check is what refuses a ``..`` that
        lands in a writable directory."""
        _, entry, real, _, _ = group_writable_target_dir(home)
        assert _resolve(entry, "keyword") is None
        monkeypatch.setattr(pathsec, "is_private_dir", lambda path: True)
        assert _same(_resolve(entry, "keyword"), real)
        # and the default still refuses it, at the '..'
        assert "not followed by default" in pathsec.untrusted_executable_reason(entry)

    def test_without_the_directory_check_a_climb_out_and_back_runs(
        self, home, monkeypatch
    ):
        _, entry, real, _, _ = climb_above_the_root_into_writable_and_back(home)
        assert _resolve(entry, "keyword") is None
        monkeypatch.setattr(pathsec, "is_private_dir", lambda path: True)
        assert _same(_resolve(entry, "keyword"), real)

    @pytest.mark.parametrize("mode", MODES)
    def test_without_the_file_check_a_writable_target_runs(
        self, home, monkeypatch, mode
    ):
        real = _tool(f"{home}/real/dot", 0o775)
        entry = _ln(real, f"{home}/bin/dot")
        assert _resolve(entry, mode) is None
        monkeypatch.setattr(pathsec, "_private_stat", lambda st: True)
        assert _same(_resolve(entry, mode), real)

    def test_without_the_control_character_check_a_newline_link_runs(
        self, home, monkeypatch
    ):
        _, entry, real, _, _ = newline_in_link_text(home)
        assert _resolve(entry, "keyword") is None
        monkeypatch.setattr(pathsec, "_link_text_problem", lambda path, link: None)
        assert _same(_resolve(entry, "keyword"), real)

    @pytest.mark.parametrize("mode", MODES)
    def test_without_the_open_check_a_swapped_final_component_runs(
        self, home, monkeypatch, mode
    ):
        """With the ``O_NOFOLLOW`` open replaced by a path ``stat``, the link
        swapped in as the final component is followed to the decoy, which is
        a private-looking file, and the path returned now names the decoy."""
        real = _tool(f"{home}/real/dot")
        decoy = _tool(f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        entry = real if mode == "default" else _ln("../real/dot", f"{home}/bin/dot")
        true_lstat = os.lstat
        seen = []

        def lstat(path, *args, **kwargs):
            st = true_lstat(path, *args, **kwargs)
            if os.fspath(path) == real:
                seen.append(path)
                if len(seen) == 2:
                    os.unlink(real)
                    os.symlink(decoy, real)
            return st

        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        # either check alone still refuses: the O_NOFOLLOW open (ELOOP), or
        # the inode comparison against what was inspected
        monkeypatch.setattr(pathsec, "_open_verified", lambda real, why: os.stat(real))
        why = pathsec._Why()
        assert _walk(entry, mode, why) is None
        assert "changed while it was being verified" in "; ".join(why)
        os.unlink(real)
        _tool(real)
        seen.clear()
        monkeypatch.undo()
        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        monkeypatch.setattr(pathsec, "_same_inode", lambda a, b: True)
        why = pathsec._Why()
        assert _walk(entry, mode, why) is None
        assert "cannot be opened for verification" in "; ".join(why)
        os.unlink(real)
        _tool(real)
        seen.clear()
        # both gone: the decoy is what the returned path now names
        monkeypatch.setattr(pathsec, "_open_verified", lambda real, why: os.stat(real))
        got = _resolve(entry, mode)
        assert got == real and os.path.realpath(got) == os.path.realpath(decoy)

    def test_the_spawn_runs_what_the_resolver_returned(self, home, monkeypatch):
        """The reason is a second, diagnostic walk; the spawn executes the one
        path the resolver returned, read once from a path-like."""
        real = _tool(f"{home}/real/dot")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        calls = []
        true_resolve = pathsec._resolve_trusted

        def resolve(target, why=None, **kw):
            calls.append((target, kw))
            return true_resolve(target, why, **kw)

        monkeypatch.setattr(pathsec, "_resolve_trusted", resolve)
        proc, out = _run(Path(entry), "keyword")
        assert calls == [(entry, {PRIVATE_KEYWORD: True})]
        assert proc.args[0] == os.path.realpath(real)
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg"


# --------------------------------------------------------------------------- #
# The keyword is a bool, accepted only where documented, and nowhere else.     #
# --------------------------------------------------------------------------- #


class TestKeywordSurface:
    @pytest.mark.parametrize(
        "value",
        [
            "True",
            1,
            1.0,
            object(),
            [True],
            type("Lying", (), {"__bool__": lambda self: True})(),
        ],
        ids=["str", "int", "float", "object", "list", "lying_bool"],
    )
    def test_anything_but_a_bool_is_refused_before_any_lookup(self, value, monkeypatch):
        from nltk.parse.dependencygraph import DependencyGraph, dot2img
        from nltk.translate.api import AlignedSent, Alignment

        monkeypatch.setenv("PATH", "")
        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        with pytest.raises(TypeError, match=KEYWORD):
            dot2img(GRAPH, follow_link_parents=value)
        with pytest.raises(TypeError, match=KEYWORD):
            dg.to_image(follow_link_parents=value)
        with pytest.raises(TypeError, match=KEYWORD):
            sent.to_image(follow_link_parents=value)
        with pytest.raises(TypeError, match=PRIVATE_KEYWORD):
            pathsec.spawn_trusted("/x", [], _follow_link_parents=value)
        with pytest.raises(TypeError, match=PRIVATE_KEYWORD):
            pathsec._resolve_private("/x", _follow_link_parents=value)

    def test_the_keyword_is_keyword_only_everywhere(self):
        from nltk.parse.dependencygraph import DependencyGraph, dot2img
        from nltk.translate.api import AlignedSent, Alignment

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        with pytest.raises(TypeError):
            dot2img(GRAPH, "svg", True)
        with pytest.raises(TypeError):
            dg.to_image("svg", True)
        with pytest.raises(TypeError):
            sent.to_image("svg", True)
        with pytest.raises(TypeError):
            pathsec.spawn_trusted("/x", [], True)
        with pytest.raises(TypeError):
            pathsec._resolve_trusted("/x", None, True)

    def test_the_repr_hooks_take_no_argument_and_use_the_defaults(self, monkeypatch):
        """IPython calls ``_repr_svg_()`` bare; an attribute named like the
        keyword on the instance has no effect; ``dot2img`` sees False."""
        import inspect

        from nltk.parse import dependencygraph
        from nltk.parse.dependencygraph import DependencyGraph
        from nltk.translate.api import AlignedSent, Alignment

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        for hook in (dg._repr_svg_, sent._repr_svg_):
            assert list(inspect.signature(hook).parameters) == []
            with pytest.raises(TypeError):
                hook(follow_link_parents=True)
        seen = []

        def record(dot_string, t="svg", *, follow_link_parents=False):
            seen.append(follow_link_parents)
            return "<svg/>"

        monkeypatch.setattr(dependencygraph, "dot2img", record)
        for obj in (dg, sent):
            setattr(obj, KEYWORD, True)
            setattr(obj, PRIVATE_KEYWORD, True)
            obj.__dict__[KEYWORD] = True
            assert obj._repr_svg_() == "<svg/>"
            assert obj.to_image() == "<svg/>"
        assert seen == [False, False, False, False]
        # the signature defaults are off at every entry point
        for fn in (dependencygraph.DependencyGraph.to_image, AlignedSent.to_image):
            assert inspect.signature(fn).parameters[KEYWORD].default is False
            assert (
                inspect.signature(fn).parameters[KEYWORD].kind
                is inspect.Parameter.KEYWORD_ONLY
            )

    def test_dot2img_forwards_exactly_the_checked_bool(self, monkeypatch):
        from nltk.parse import dependencygraph

        seen = []

        def record(target, args, **kw):
            seen.append(kw.get(PRIVATE_KEYWORD))
            raise pathsec.TrustError("stop")

        monkeypatch.setattr(dependencygraph, "find_binary_absolute", lambda name: "/x")
        monkeypatch.setattr(dependencygraph, "spawn_trusted", record)
        for value in (False, True):
            with pytest.raises(Exception, match="Cannot create image"):
                dependencygraph.dot2img(GRAPH, follow_link_parents=value)
        assert seen == [False, True]

    def test_no_other_wrapper_accepts_the_keyword(self):
        """Every other tool wrapper keeps the default: there is no keyword to
        pass, on any platform."""
        import inspect

        from nltk.internals import config_java, find_binary_absolute, java
        from nltk.tag.hunpos import HunposTagger
        from nltk.inference.prover9 import Prover9Command
        from nltk.classify.megam import config_megam
        from nltk.classify.tadm import config_tadm

        for kw in (KEYWORD, PRIVATE_KEYWORD):
            with pytest.raises(TypeError):
                config_java(**{kw: True})
            with pytest.raises(TypeError):
                find_binary_absolute("prover9", **{kw: True})
            with pytest.raises(TypeError):
                config_megam(**{kw: True})
            with pytest.raises(TypeError):
                config_tadm(**{kw: True})
            for fn in (
                HunposTagger.__init__,
                Prover9Command.__init__,
                java,
                pathsec.resolve_trusted_executable,
                pathsec.untrusted_executable_reason,
            ):
                params = inspect.signature(fn).parameters
                assert kw not in params, fn
                assert not any(p.kind is p.VAR_KEYWORD for p in params.values()), fn

    @POSIX
    def test_a_homebrew_shaped_link_stays_refused_for_every_other_tool(
        self, home, monkeypatch
    ):
        """java, prover9 and hunpos found behind a ``..`` link: the finder
        hands the link over, the default spawn refuses it by name, and the
        error never suggests a keyword they do not have."""
        from nltk.internals import find_binary_absolute

        real = _tool(f"{home}/Cellar/tool/1/bin/tool")
        for name in ("java", "prover9", "hunpos-tag"):
            _ln("../Cellar/tool/1/bin/tool", f"{home}/bin/{name}")
        monkeypatch.setenv("PATH", f"{home}/bin")
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.delenv("JAVAHOME", raising=False)
        for name in ("java", "prover9", "hunpos-tag"):
            found = find_binary_absolute(name, binary_names=[name])
            assert _same(found, f"{home}/bin/{name}")
            with pytest.raises(pathsec.TrustError, match="not followed by default"):
                pathsec.spawn_trusted(found, [])
        assert _ran(home) == [] and os.path.exists(real)


@POSIX
def test_only_the_graphviz_caller_names_the_private_walk():
    """``git grep`` of the private keyword: its definition and threading in
    pathsec, the one Graphviz caller, the CI guard and the tests, nothing else.
    A new wrapper that picked it up would fail here and in the guard."""
    import nltk

    repo = os.path.dirname(os.path.dirname(os.path.abspath(nltk.__file__)))
    allowed = {
        os.path.join("nltk", "pathsec.py"),
        os.path.join("nltk", "parse", "dependencygraph.py"),
        os.path.join("tools", "check_all_spawns_through_pathsec.py"),
    }
    hits = set()
    for top in ("nltk", "tools"):
        for dirpath, _, names in os.walk(os.path.join(repo, top)):
            for name in names:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    if PRIVATE_KEYWORD in fh.read():
                        hits.add(os.path.relpath(path, repo))
    tests = {h for h in hits if h.startswith(os.path.join("nltk", "test"))}
    assert hits - tests == allowed, sorted(hits - tests)
    assert os.path.join("nltk", "translate", "api.py") not in hits


# --------------------------------------------------------------------------- #
# The real Graphviz: nothing stubbed. CI installs it on every runner and sets  #
# NLTK_CI_REQUIRE_GRAPHVIZ so a missing or refused dot fails, never skips.     #
# --------------------------------------------------------------------------- #

PNG = b"\x89PNG\r\n\x1a\n"


def _required():
    return bool(os.environ.get("NLTK_CI_REQUIRE_GRAPHVIZ"))


def _real_dot():
    """The Graphviz ``dot`` on PATH, resolved absolute by the finder."""
    from nltk.internals import find_binary_absolute

    try:
        return find_binary_absolute("dot")
    except LookupError:
        if _required():
            pytest.fail(
                "NLTK_CI_REQUIRE_GRAPHVIZ is set but no Graphviz dot is on PATH"
            )
        pytest.skip("no Graphviz dot on PATH")


def _valid_svg(text):
    """A real rendering of GRAPH: well-formed XML, an svg root, both labels."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(text)
    assert root.tag.endswith("svg") and "</svg>" in text
    labels = {el.text or "" for el in root.iter() if el.tag.endswith("text")}
    # dot2img's GRAPH labels its nodes a and b, DependencyGraph "1 (a)" / "2 (b)"
    assert all(any(name in label for label in labels) for name in "ab"), labels
    return text


def _graph_objects():
    from nltk.parse.dependencygraph import DependencyGraph
    from nltk.translate.api import AlignedSent, Alignment

    dg = DependencyGraph("a N 2\nb V 0")
    sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
    return dg, sent


class TestRealGraphviz:
    def test_the_installed_dot_renders_or_its_refusal_is_caught(self):
        """The dot as installed (apt: a root-owned file; choco: a .exe; brew:
        a ``bin/dot -> ../Cellar/...`` link): a trusted file renders in both
        modes; the Homebrew link is refused by default with the keyword named
        and renders under it; anything else refused is reported with its
        reason in both modes, and in CI that is a failure to fix in the
        workflow (the chain is made private), never a skip."""
        from nltk.parse.dependencygraph import dot2img

        dot = _real_dot()
        reason, link_parent = pathsec._refusal(dot)
        if reason is not None and not link_parent:
            for kw in ({}, {KEYWORD: True}):
                with pytest.raises(Exception, match="Cannot create image") as excinfo:
                    dot2img(GRAPH, **kw)
                assert reason in str(excinfo.value)
                assert isinstance(excinfo.value.__cause__, pathsec.TrustError)
            message = f"the installed dot {dot!r} is refused: {reason}"
            if _required():
                pytest.fail(message)
            pytest.skip(message)
        dg, sent = _graph_objects()
        if link_parent:
            for call in (
                lambda: dot2img(GRAPH),
                dg._repr_svg_,
                sent._repr_svg_,
                dg.to_image,
                sent.to_image,
            ):
                with pytest.raises(Exception, match="Cannot create image") as excinfo:
                    call()
                message = str(excinfo.value)
                assert "not followed by default" in message
                assert f"dot2img(..., {KEYWORD}=True)" in message
                assert excinfo.value.__cause__.link_parent is True
        else:
            _valid_svg(dot2img(GRAPH))
            assert dot2img(GRAPH, "png")[:8] == PNG
            _valid_svg(dg._repr_svg_())
            _valid_svg(sent._repr_svg_())
        _valid_svg(dot2img(GRAPH, follow_link_parents=True))
        assert dot2img(GRAPH, "png", follow_link_parents=True)[:8] == PNG
        _valid_svg(dg.to_image(follow_link_parents=True))
        _valid_svg(sent.to_image(follow_link_parents=True))
        assert dg.to_image("png", follow_link_parents=True)[:8] == PNG
        assert sent.to_image("png", follow_link_parents=True)[:8] == PNG

    @POSIX
    def test_the_installed_dot_behind_a_homebrew_shaped_chain(self, home, monkeypatch):
        """The real binary at the end of a real ``bin/dot -> ../Cellar/
        graphviz/<v>/bin/dot`` chain built here: refused by default with the
        link, its ``..`` and the keyword named, the TrustError as the cause;
        valid SVG and PNG under the keyword, through dot2img and both
        to_image methods; the two-hop sibling link too. The same real binary
        behind a world-writable directory is refused in both modes with that
        reason and without the keyword."""
        from nltk.parse.dependencygraph import dot2img

        dot = _real_dot()
        real = pathsec._resolve_trusted(dot, _follow_link_parents=True)
        if real is None:
            message = f"the installed dot {dot!r} is refused: {_reason(dot, 'keyword')}"
            if _required():
                pytest.fail(message)
            pytest.skip(message)
        cellar = f"{home}/usr/local/Cellar/graphviz/14.1.2/bin"
        _ln(real, f"{cellar}/dot")
        _ln("dot", f"{cellar}/circo")
        _ln("../Cellar/graphviz/14.1.2/bin/dot", f"{home}/usr/local/bin/dot")
        _ln("../Cellar/graphviz/14.1.2/bin/circo", f"{home}/usr/local/bin/circo")
        monkeypatch.setenv("PATH", f"{home}/usr/local/bin")
        dg, sent = _graph_objects()
        for call in (
            lambda: dot2img(GRAPH),
            lambda: dot2img(GRAPH, "png"),
            dg._repr_svg_,
            sent._repr_svg_,
            dg.to_image,
            sent.to_image,
        ):
            with pytest.raises(Exception, match="Cannot create image") as excinfo:
                call()
            message = str(excinfo.value)
            assert f"symlink {home}/usr/local/bin/dot" in message.replace("'", "")
            assert "'../Cellar/graphviz/14.1.2/bin/dot'" in message
            assert "not followed by default" in message
            assert f"dot2img(..., {KEYWORD}=True)" in message
            cause = excinfo.value.__cause__
            assert isinstance(cause, pathsec.TrustError) and cause.link_parent is True
        _valid_svg(dot2img(GRAPH, follow_link_parents=True))
        assert dot2img(GRAPH, "png", follow_link_parents=True)[:8] == PNG
        _valid_svg(dg.to_image(follow_link_parents=True))
        _valid_svg(sent.to_image(follow_link_parents=True))
        assert dg.to_image("png", follow_link_parents=True)[:8] == PNG
        circo = f"{home}/usr/local/bin/circo"
        assert pathsec.resolve_trusted_executable(circo) is None
        proc = pathsec.spawn_trusted(
            circo,
            ["-Tsvg"],
            _follow_link_parents=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert _same(proc.args[0], real)
        _valid_svg(proc.communicate(GRAPH.encode())[0].decode())
        # the same real binary behind a world-writable directory
        _dir(f"{home}/ww")
        _ln(real, f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        _ln("../ww/dot", f"{home}/sbin/dot")
        monkeypatch.setenv("PATH", f"{home}/sbin")
        for kw in ({}, {KEYWORD: True}):
            with pytest.raises(Exception, match="Cannot create image") as excinfo:
                dot2img(GRAPH, **kw)
            message = str(excinfo.value)
            assert "world-writable" in message and f"{home}/ww" in message
            assert KEYWORD not in message
            assert excinfo.value.__cause__.link_parent is False


# --------------------------------------------------------------------------- #
# Windows: junctions and reparse points, best-effort by design, both modes.    #
# --------------------------------------------------------------------------- #


@WINDOWS
class TestWindowsJunctions:
    def _junction(self, target, link):
        proc = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            pytest.skip(f"mklink /J unavailable here: {proc.stderr.strip()}")

    @pytest.mark.parametrize("mode", MODES)
    def test_a_junction_resolves_to_the_regular_file_never_the_junction(
        self, tmp_path, mode
    ):
        real = tmp_path / "real" / "dot.exe"
        real.parent.mkdir()
        real.write_bytes(b"MZ")
        self._junction(tmp_path / "real", tmp_path / "junc")
        entry = str(tmp_path / "junc" / "dot.exe")
        got = _resolve(entry, mode)
        assert got is not None and os.path.isfile(got)
        assert os.path.samefile(got, real)
        assert "junc" not in [part.lower() for part in Path(got).parts]
        assert _reason(entry, mode) is None

    @pytest.mark.parametrize("mode", MODES)
    def test_a_dangling_junction_is_refused_with_the_reason(self, tmp_path, mode):
        (tmp_path / "gone").mkdir()
        self._junction(tmp_path / "gone", tmp_path / "junc")
        os.rmdir(tmp_path / "gone")
        entry = str(tmp_path / "junc" / "dot.exe")
        assert _resolve(entry, mode) is None
        assert "cannot be inspected" in _reason(entry, mode)
        with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
            pathsec.spawn_trusted(entry, [])

    @pytest.mark.parametrize("mode", MODES)
    def test_a_junction_to_a_directory_is_not_a_regular_file(self, tmp_path, mode):
        (tmp_path / "adir").mkdir()
        self._junction(tmp_path / "adir", tmp_path / "junc")
        entry = str(tmp_path / "junc")
        assert _resolve(entry, mode) is None
        assert "not a regular file" in _reason(entry, mode)


def test_reason_api_is_available_on_every_platform(home):
    # under a private chain, so the first reason is the missing file itself,
    # not the shared sticky /tmp that holds pytest's tmp_path on Linux
    missing = str(home / "nowhere" / "dot")
    reason = pathsec.untrusted_executable_reason(missing)
    assert reason and "cannot be inspected" in reason
    assert pathsec.resolve_trusted_executable(missing) is None
    with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
        pathsec.spawn_trusted(missing, [])
