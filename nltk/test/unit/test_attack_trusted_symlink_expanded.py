# Natural Language Toolkit: trusted-spawn symlink layout harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Symlinked tool installs at the trusted-spawn chokepoint (CWE-426/427/732).

#3887 made every executed binary go through ``pathsec.spawn_trusted``, whose
resolver refused any ``..`` it met, including one inside a symlink's own text.
That is how the standard package layouts are built: Homebrew's ``bin/dot ->
../Cellar/graphviz/<v>/bin/dot``, the python.org ``bin/python3 ->
../../../Library/...``, a Debian ``circo -> dot`` sibling link, so the merged
PR broke ``dot2img`` on every such Graphviz install (ekaf, #3887 comment
5969235326).

The resolver now follows a link's text as the kernel does (the holding
directory is already resolved, so each ``..`` is its real parent) and judges
the target by the chain it lands in. The trust property is unchanged: NLTK
never executes a file another local user could have planted or swapped. Every
directory on the chain, every link on it and the final file must be owned by
the current user or root and be neither group- nor world-writable; the chain
is bounded (``_MAX_LINK_HOPS``, a loop is refused); the caller's own ``..`` is
still never folded. Real files, real links, real ``chmod``: every standard
layout below runs the tool and returns its real output, every spoof is refused
with the reason naming the check and the path, and the teeth show that
removing each check lets a spoof through.
"""
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

from nltk import pathsec

POSIX = pytest.mark.skipif(
    os.name != "posix", reason="symlinks and the POSIX ownership model"
)

STUB = '#!/bin/sh\ncat >/dev/null\necho "GRAPHVIZ-STUB $*"\n'
GRAPH = "digraph { a -> b }"


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


# --------------------------------------------------------------------------- #
# Layouts: (bin dir to put on PATH, entry to run, real file or None).           #
# --------------------------------------------------------------------------- #


def homebrew(r):
    """``prefix/bin/dot -> ../Cellar/graphviz/15.1.1/bin/dot``; inside the
    Cellar ``circo -> dot`` and ``fdp -> dot``, as ``brew install graphviz``
    lays it out."""
    real = _tool(f"{r}/Cellar/graphviz/15.1.1/bin/dot")
    _ln("dot", f"{r}/Cellar/graphviz/15.1.1/bin/circo")
    _ln("dot", f"{r}/Cellar/graphviz/15.1.1/bin/fdp")
    _ln("../Cellar/graphviz/15.1.1/bin/dot", f"{r}/bin/dot")
    _ln("../Cellar/graphviz/15.1.1/bin/circo", f"{r}/bin/circo")
    return f"{r}/bin", f"{r}/bin/dot", real


def homebrew_sibling_two_hops(r):
    """``prefix/bin/circo -> ../Cellar/.../bin/circo -> dot``."""
    bindir, _, real = homebrew(r)
    return bindir, f"{r}/bin/circo", real


def homebrew_opt_dir_link(r):
    """``prefix/opt/graphviz -> ../Cellar/graphviz/15.1.1`` (a directory link
    with ``..``), then ``bin/dot`` below it."""
    real = _tool(f"{r}/Cellar/graphviz/15.1.1/bin/dot")
    _ln("../Cellar/graphviz/15.1.1", f"{r}/opt/graphviz")
    return f"{r}/opt/graphviz/bin", f"{r}/opt/graphviz/bin/dot", real


def multicall(r):
    """One real binary, ``dot`` / ``neato`` / ``circo`` sibling links to it."""
    real = _tool(f"{r}/usr/bin/graphviz")
    for name in ("dot", "neato", "circo"):
        _ln("graphviz", f"{r}/usr/bin/{name}")
    return f"{r}/usr/bin", f"{r}/usr/bin/dot", real


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
    """``./``, ``//`` and ``/./`` in a link's text are inert."""
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


BENIGN = {
    "homebrew": homebrew,
    "homebrew_sibling_two_hops": homebrew_sibling_two_hops,
    "homebrew_opt_dir_link": homebrew_opt_dir_link,
    "multicall": multicall,
    "chain_two_deep": chain_two_deep,
    "chain_three_deep": chain_three_deep,
    "relative_link": relative_link,
    "absolute_link": absolute_link,
    "alternatives": alternatives,
    "pythonorg_three_up": pythonorg_three_up,
    "overclimb_clamps_at_root": overclimb_clamps_at_root,
    "inert_components": inert_components,
    "chain_at_the_bound": chain_at_the_bound,
    "parent_of_a_writable_dir_is_not_inside_it": parent_of_a_writable_dir_is_not_inside_it,
}


def group_writable_target_dir(r):
    real = _tool(f"{r}/gw/dot")
    os.chmod(f"{r}/gw", 0o775)
    _ln("../gw/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "group-writable", f"{r}/gw"


def world_writable_sticky_target_dir(r):
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


def writable_dir_descended_into_through_dotdot(r):
    """``bin/dot -> ../ww/sub/../dot``: ``ww`` is entered this time, and it is
    world-writable."""
    real = _tool(f"{r}/ww/dot")
    _dir(f"{r}/ww/sub")
    os.chmod(f"{r}/ww", 0o777)
    _ln("../ww/sub/../dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", f"{r}/ww"


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
    "writable_dir_descended_into_through_dotdot": writable_dir_descended_into_through_dotdot,
}


def _run(entry):
    proc = pathsec.spawn_trusted(
        entry,
        ["-Tsvg"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out = proc.communicate(GRAPH.encode())[0].decode()
    return proc, out


def _dot2img(monkeypatch, bindir):
    from nltk.parse import dependencygraph

    monkeypatch.setenv("PATH", bindir)
    return dependencygraph.dot2img(GRAPH, "svg")


# --------------------------------------------------------------------------- #
# Every standard layout runs the tool and returns its real output.             #
# --------------------------------------------------------------------------- #


@POSIX
class TestStandardLayoutsRun:
    @pytest.mark.parametrize("layout", sorted(BENIGN), ids=sorted(BENIGN))
    def test_resolves_to_the_real_file_and_runs_it(self, home, monkeypatch, layout):
        bindir, entry, real = BENIGN[layout](home)
        assert os.path.realpath(entry) != entry  # a link somewhere on the way
        got = pathsec.resolve_trusted_executable(entry)
        assert got is not None and _same(got, real), (layout, got)
        assert not os.path.islink(got)  # the resolved path, never the link
        assert pathsec.untrusted_executable_reason(entry) is None
        proc, out = _run(entry)
        assert _same(proc.args[0], real) and proc.args[0] == got
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg", (layout, out)
        # the OS's own lookup has its own ELOOP limit (32 on macOS, 40 on
        # Linux), so the PATH finder sees the chain at the bound only where the
        # OS follows it; the walker and the spawn above did either way
        if os.path.basename(entry) == "dot" and os.path.isfile(entry):
            assert _dot2img(monkeypatch, bindir).strip() == "GRAPHVIZ-STUB -Tsvg"
        else:
            assert layout in ("homebrew_sibling_two_hops", "chain_at_the_bound")

    def test_ekaf_reproduction_on_the_homebrew_layout(self, home, monkeypatch):
        """The exact two lines from the report, with the Homebrew shape on PATH."""
        bindir, _, _ = homebrew(home)
        monkeypatch.setenv("PATH", bindir)
        from nltk.parse.dependencygraph import dot2img

        assert dot2img(GRAPH).strip() == "GRAPHVIZ-STUB -Tsvg"

    def test_aligned_sent_svg_on_the_homebrew_layout(self, home, monkeypatch):
        from nltk.translate.api import AlignedSent, Alignment

        bindir, _, _ = homebrew(home)
        monkeypatch.setenv("PATH", bindir)
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        assert sent._repr_svg_().strip() == "GRAPHVIZ-STUB -Tsvg"

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
        got = pathsec.resolve_trusted_executable(entry)
        assert _same(got, kernel) and not _same(got, folded)
        assert _same(os.path.realpath(entry), kernel)  # the OS agrees
        joined = os.path.join(f"{home}/holder", "sub/../real")
        assert _same(os.path.normpath(joined), folded)  # what folding gives


# --------------------------------------------------------------------------- #
# Every spoof is refused, with the reason naming the check and the path.       #
# --------------------------------------------------------------------------- #


@POSIX
class TestSpoofLayoutsAreRefused:
    @pytest.mark.parametrize("layout", sorted(SPOOF), ids=sorted(SPOOF))
    def test_refused_with_the_reason(self, home, monkeypatch, layout):
        bindir, entry, real, check, named = SPOOF[layout](home)
        assert pathsec.resolve_trusted_executable(entry) is None, layout
        reason = pathsec.untrusted_executable_reason(entry)
        assert check in reason and named in reason, (layout, reason)
        with pytest.raises(pathsec.TrustError) as excinfo:
            _run(entry)
        message = str(excinfo.value)
        assert message.startswith("refusing to execute untrusted path")
        assert reason in message and "chmod g-w,o-w" in message
        if real is not None and os.path.isfile(entry):
            # the Graphviz entry point surfaces the same reason, and the
            # trusted spawn is its cause
            with pytest.raises(Exception, match="Cannot create image") as excinfo:
                _dot2img(monkeypatch, bindir)
            assert reason in str(excinfo.value)
            assert isinstance(excinfo.value.__cause__, pathsec.TrustError)

    def test_a_link_owned_by_another_user_is_refused(self, home, monkeypatch):
        """Simulated (no root here): ``lstat`` of one link reports a foreign
        uid, at the entry and in the middle of a chain. Its holder is private,
        so this is the link-owner check alone."""
        real = _tool(f"{home}/real/dot")
        mid = _ln("../real/dot", f"{home}/mid/dot")
        entry = _ln("../mid/dot", f"{home}/bin/dot")
        assert _same(pathsec.resolve_trusted_executable(entry), real)
        true_lstat = os.lstat
        foreign = os.geteuid() + 4242

        def _foreign_link(victim):
            def lstat(path, *args, **kwargs):
                st = true_lstat(path, *args, **kwargs)
                if os.fspath(path) == victim:
                    fields = list(st)
                    fields[stat.ST_UID] = foreign
                    st = os.stat_result(tuple(fields))
                return st

            return lstat

        for victim in (entry, mid):
            monkeypatch.setattr(pathsec.os, "lstat", _foreign_link(victim))
            assert pathsec.resolve_trusted_executable(entry) is None, victim
            reason = pathsec.untrusted_executable_reason(entry)
            assert f"symlink {victim!r} is owned by uid {foreign}" in reason
            with pytest.raises(pathsec.TrustError, match="owned by uid"):
                _run(entry)
            monkeypatch.undo()
        assert _same(pathsec.resolve_trusted_executable(entry), real)

    def test_a_climb_into_the_shared_tmp_is_refused(self, home):
        """``bin/dot -> ../../..(to /)/tmp/<dir>/dot``: the sticky ``/tmp``
        on the way is world-writable, so the chain is refused there."""
        tmp = "/tmp"
        if not (os.path.isdir(tmp) and os.stat(tmp).st_mode & stat.S_ISVTX):
            pytest.skip("/tmp is not a sticky world-writable dir here")
        plant = tempfile.mkdtemp(prefix="nltk_symlink_spoof_", dir=tmp)
        try:
            real = _tool(f"{plant}/dot")
            entry = _ln("../" * 40 + real.lstrip("/"), f"{home}/bin/dot")
            assert pathsec.resolve_trusted_executable(entry) is None
            reason = pathsec.untrusted_executable_reason(entry)
            assert "world-writable" in reason and "tmp" in reason
        finally:
            shutil.rmtree(plant, ignore_errors=True)

    def test_the_callers_own_dotdot_is_still_never_folded(self, home):
        """A ``..`` in the target the caller hands over is refused as before,
        even when it folds to a trusted file: an unresolved name before it
        could hide a link, and a configured location is never allowed one."""
        real = _tool(f"{home}/bin/dot")
        spelled = f"{home}/bin/../bin/dot"
        assert _same(os.path.realpath(spelled), real)
        assert pathsec.resolve_trusted_executable(spelled) is None
        assert "'..' component" in pathsec.untrusted_executable_reason(spelled)
        with pytest.raises(pathsec.TrustError, match="'..' component"):
            pathsec.spawn_trusted(spelled, [])
        assert pathsec._resolve_private(spelled) is None
        assert _same(pathsec._resolve_private(spelled, _in_link=True), real)

    def test_relative_and_odd_targets_name_their_reason(self, home):
        real = _tool(f"{home}/bin/dot")
        assert "not absolute" in pathsec.untrusted_executable_reason("bin/dot")
        assert "NUL" in pathsec.untrusted_executable_reason(real + "\x00")
        assert "not a str path" in pathsec.untrusted_executable_reason(7)
        assert "not a str path" in pathsec.untrusted_executable_reason(None)
        missing = f"{home}/nowhere/dot"
        assert "cannot be inspected" in pathsec.untrusted_executable_reason(missing)
        assert pathsec.untrusted_executable_reason(real) is None


# --------------------------------------------------------------------------- #
# Teeth: removing each check lets a spoof through.                             #
# --------------------------------------------------------------------------- #


@POSIX
class TestTeeth:
    def test_without_the_link_owner_check_a_foreign_link_runs(self, home, monkeypatch):
        real = _tool(f"{home}/real/dot")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        true_lstat = os.lstat
        foreign = os.geteuid() + 4242

        def lstat(path, *args, **kwargs):
            st = true_lstat(path, *args, **kwargs)
            if os.fspath(path) == entry:
                fields = list(st)
                fields[stat.ST_UID] = foreign
                st = os.stat_result(tuple(fields))
            return st

        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        assert pathsec.resolve_trusted_executable(entry) is None
        monkeypatch.setattr(pathsec, "_link_owner_problem", lambda path, st: None)
        assert _same(pathsec.resolve_trusted_executable(entry), real)

    def test_without_the_hop_bound_an_overlong_chain_runs(self, home, monkeypatch):
        _, entry, real, _, _ = chain_over_the_bound(home)
        assert pathsec.resolve_trusted_executable(entry) is None
        monkeypatch.setattr(pathsec, "_MAX_LINK_HOPS", 10_000)
        assert _same(pathsec.resolve_trusted_executable(entry), real)

    def test_without_the_directory_check_a_dotdot_into_a_writable_dir_runs(
        self, home, monkeypatch
    ):
        """The directory check is what refuses a ``..`` that lands in a
        writable directory now that the ``..`` itself is followed."""
        _, entry, real, _, _ = group_writable_target_dir(home)
        assert pathsec.resolve_trusted_executable(entry) is None
        monkeypatch.setattr(pathsec, "is_private_dir", lambda path: True)
        assert _same(pathsec.resolve_trusted_executable(entry), real)

    def test_without_the_file_check_a_writable_target_runs(self, home, monkeypatch):
        _, entry, real, _, _ = group_writable_target_file(home)
        assert pathsec.resolve_trusted_executable(entry) is None
        monkeypatch.setattr(pathsec, "_private_stat", lambda st: True)
        assert _same(pathsec.resolve_trusted_executable(entry), real)

    def test_the_spawn_runs_what_the_resolver_returned(self, home, monkeypatch):
        """The reason is a second, diagnostic walk; the spawn executes the one
        path the resolver returned, read once from a path-like."""
        real = _tool(f"{home}/real/dot")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        calls = []
        true_resolve = pathsec.resolve_trusted_executable

        def resolve(target):
            calls.append(target)
            return true_resolve(target)

        monkeypatch.setattr(pathsec, "resolve_trusted_executable", resolve)
        proc, out = _run(Path(entry))
        assert calls == [entry] and proc.args[0] == os.path.realpath(real)
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg"


def test_reason_api_is_available_on_every_platform(tmp_path):
    missing = str(tmp_path / "nowhere" / "dot")
    reason = pathsec.untrusted_executable_reason(missing)
    assert reason and "cannot be inspected" in reason
    assert pathsec.resolve_trusted_executable(missing) is None
    with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
        pathsec.spawn_trusted(missing, [])
