# Natural Language Toolkit: trusted-spawn symlink layout harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Symlinked tool installs at the trusted-spawn chokepoint (CWE-426/427/732).

#3887 made every executed binary go through ``pathsec.spawn_trusted``, whose
resolver refused any ``..`` it met, including one inside a symlink's own
text. That is how the standard package layouts are built: Homebrew's
``bin/dot -> ../Cellar/graphviz/<v>/bin/dot``, Debian's ``/usr/bin/dot ->
../sbin/libgvc6-config-update``, the python.org ``bin/python3 ->
../../../Library/...``, so ``dot2img`` refused every such Graphviz install
(ekaf, #3887 comment 5969235326).

This harness pins what the trusted spawn does with each layout now: a ``..``
inside a link's own text is folded the way the kernel folds it, to the real
parent of the directory already resolved, and the layout runs its real file
under the name it was invoked by; a ``..`` the caller typed is refused.
Real files, real links, real ``chmod``, a canary binary that writes a marker
when it runs: every climbing and plain layout resolves to the kernel's own
``realpath`` and runs the canary once, at the real file; every spoof is
refused by its own check, with the reason naming that check and the path,
and the canary never runs; the teeth show that removing each check lets a
named spoof through.
"""
import os
import shutil
import socket
import stat
import subprocess
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
#: The walks a parametrized test runs: the default walk is the only one.
MODES = ("default",)

#: The canary: swallows stdin, drops a marker beside the file that ran, echoes.
STUB = '#!/bin/sh\ncat >/dev/null\n: > "$0.ran" 2>/dev/null\necho "GRAPHVIZ-STUB $*"\n'
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


def _ran(root):
    """Every canary marker under *root*: empty means nothing was executed."""
    return sorted(
        os.path.join(dirpath, name)
        for dirpath, _, names in os.walk(root)
        for name in names
        if name.endswith(".ran")
    )


def _resolve(entry):
    return pathsec.resolve_trusted_executable(entry)


def _walk(entry, why):
    """One verification walk, recording its reason in *why* as it happens."""
    return pathsec._resolve_trusted(entry, why)


def _reason(entry):
    return pathsec.untrusted_executable_reason(entry)


def _runs(home, entry, real):
    """*entry* resolves to the kernel's own ``realpath``, which is *real* and
    not a link, and the spawn runs the canary once, at *real*, under the name
    *entry* was invoked by."""
    got = _resolve(entry)
    assert got == os.path.realpath(entry) and _same(got, real), (entry, got)
    assert not os.path.islink(got) and _reason(entry) is None, entry
    proc, out = _run(entry)
    assert proc.args[0] == entry and out.strip() == "GRAPHVIZ-STUB -Tsvg", entry
    assert _ran(home) == [real + ".ran"], entry
    os.unlink(real + ".ran")
    return got


def _refused(home, entry, check, named):
    """*entry* is refused by the walk and the spawn, the reason naming *check*
    and *named*, and nothing runs."""
    assert _resolve(entry) is None, entry
    reason = _reason(entry)
    assert check in reason and named in reason, (entry, reason)
    with pytest.raises(pathsec.TrustError) as excinfo:
        _run(entry)
    assert reason in str(excinfo.value), entry
    assert _ran(home) == [], entry
    return reason


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


# =========================================================================== #
# Layouts: (bin dir to put on PATH, entry to run, real file or None).           #
# =========================================================================== #


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
    """More ``..`` than the depth: the kernel stays at ``/``."""
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


def absolute_text_with_dotdot(r):
    """``bin/dot -> <r>/opt/../etc/dot``: an absolute text with a ``..`` in
    it, the ``/opt/../etc/x`` shape, folded at ``opt``'s real parent."""
    real = _tool(f"{r}/etc/dot")
    _dir(f"{r}/opt")
    _ln(f"{r}/opt/../etc/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def dotdot_after_a_mid_path_dir_link(r):
    """The caller's ``pkg/lib/dot`` passes ``pkg/lib -> <r>/other/inner``, a
    directory link in the middle of the path; ``dot`` there is a link to
    ``../real``. The kernel applies that ``..`` to the link target's parent,
    ``other``; the lexical parent ``pkg/real`` holds a decoy that never runs."""
    real = _tool(f"{r}/other/real")
    _tool(f"{r}/pkg/real")
    _dir(f"{r}/other/inner")
    _ln(f"{r}/other/inner", f"{r}/pkg/lib")
    _ln("../real", f"{r}/other/inner/dot")
    return f"{r}/pkg/lib", f"{r}/pkg/lib/dot", real


def dot_and_slash_runs_mixed(r):
    """``./``, ``//`` and ``..`` interleaved, stepping in and out of ``bin``."""
    real = _tool(f"{r}/real/dot")
    _ln(".//..//.//bin/./..//real//./dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real


def _hops_last_climbing(r, n):
    """*n* links: the innermost (followed last) climbs with ``..`` to the real
    file, every other one names the next absolutely."""
    real = _tool(f"{r}/real/dot")
    _ln("../real/dot", f"{r}/l0/dot")
    for i in range(1, n):
        _ln(f"{r}/l{i - 1}/dot", f"{r}/l{i}/dot")
    return f"{r}/l{n - 1}", f"{r}/l{n - 1}/dot", real


def forty_hops_the_last_climbing(r):
    return _hops_last_climbing(r, pathsec._MAX_LINK_HOPS)


#: Layouts with a ``..`` in some link's text: folded as the kernel folds it,
#: they resolve to the kernel's ``realpath`` and run.
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
    "absolute_text_with_dotdot": absolute_text_with_dotdot,
    "dotdot_after_a_mid_path_dir_link": dotdot_after_a_mid_path_dir_link,
    "dot_and_slash_runs_mixed": dot_and_slash_runs_mixed,
    "forty_hops_the_last_climbing": forty_hops_the_last_climbing,
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


#: Layouts with no ``..`` anywhere: they run.
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


def forty_one_hops_the_last_climbing(r):
    bindir, entry, real = _hops_last_climbing(r, pathsec._MAX_LINK_HOPS + 1)
    return bindir, entry, real, "longer than", "hops"


def absolute_text_with_dotdot_into_writable(r):
    """``bin/dot -> <r>/opt/../ww/dot``, ``ww`` 0777."""
    real = _tool(f"{r}/ww/dot")
    os.chmod(f"{r}/ww", 0o777)
    _dir(f"{r}/opt")
    _ln(f"{r}/opt/../ww/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", real, "world-writable", f"{r}/ww"


def dotdot_after_a_dir_link_lands_on_a_writable_file(r):
    """``holder/dot -> sub/../tool`` with ``holder/sub -> <r>/other/inner``:
    the kernel's ``tool`` is ``other/tool``, group-writable; the lexical fold
    names ``holder/tool``, a private decoy that would pass every check."""
    real = _tool(f"{r}/other/tool", 0o775)
    _tool(f"{r}/holder/tool")
    _dir(f"{r}/other/inner")
    _ln(f"{r}/other/inner", f"{r}/holder/sub")
    _ln("sub/../tool", f"{r}/holder/dot")
    return f"{r}/holder", f"{r}/holder/dot", real, "group-writable", f"{r}/other/tool"


def dotdot_after_a_mid_path_dir_link_into_writable(r):
    """The caller's ``pkg/lib/dot`` passes ``pkg/lib -> <r>/other/inner``;
    ``dot`` there is ``../ww/dot``, which the kernel reads as ``other/ww/dot``,
    ``other/ww`` 0777. The lexical ``pkg/ww/dot`` is a private decoy."""
    real = _tool(f"{r}/other/ww/dot")
    os.chmod(f"{r}/other/ww", 0o777)
    _tool(f"{r}/pkg/ww/dot")
    _dir(f"{r}/other/inner")
    _ln(f"{r}/other/inner", f"{r}/pkg/lib")
    _ln("../ww/dot", f"{r}/other/inner/dot")
    return f"{r}/pkg/lib", f"{r}/pkg/lib/dot", real, "world-writable", f"{r}/other/ww"


def dangling_component_before_a_dotdot(r):
    """``bin/dot -> ../ghost/../real/dot`` with no ``ghost``: the kernel stops
    at ``ghost`` (ENOENT), and so does the walk."""
    _tool(f"{r}/real/dot")
    _ln("../ghost/../real/dot", f"{r}/bin/dot")
    return f"{r}/bin", f"{r}/bin/dot", None, "cannot be inspected", f"{r}/ghost"


#: Spoofs, each planting the check named by its last two fields: refused by
#: that check, the reason naming it and the path.
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
    "forty_one_hops_the_last_climbing": forty_one_hops_the_last_climbing,
    "absolute_text_with_dotdot_into_writable": absolute_text_with_dotdot_into_writable,
    "dotdot_after_a_dir_link_lands_on_a_writable_file": dotdot_after_a_dir_link_lands_on_a_writable_file,
    "dotdot_after_a_mid_path_dir_link_into_writable": dotdot_after_a_mid_path_dir_link_into_writable,
    "dangling_component_before_a_dotdot": dangling_component_before_a_dotdot,
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


# =========================================================================== #
# Climbing layouts: a link's '..' folded as the kernel does; they run.        #
# =========================================================================== #


@POSIX
class TestClimbingLayouts:
    @pytest.mark.parametrize("layout", sorted(CLIMBING), ids=sorted(CLIMBING))
    def test_runs_under_the_default_by_its_resolved_path(
        self, home, monkeypatch, layout
    ):
        bindir, entry, real = CLIMBING[layout](home)
        assert os.path.realpath(entry) != entry  # a link somewhere on the way
        got = _resolve(entry)
        # the kernel's own realpath, the real file, never a link
        assert got == os.path.realpath(entry) and _same(got, real), (layout, got)
        assert not os.path.islink(got) and _reason(entry) is None
        # the OS's own lookup has its own ELOOP limit (32 on macOS, 40 on
        # Linux): where it follows the chain, it reaches the same inode
        if os.path.exists(entry):
            assert os.path.samefile(entry, got), layout
        else:
            assert layout in ("chain_at_the_bound", "forty_hops_the_last_climbing")
        proc, out = _run(entry)
        # argv[0] is the invoked path, as the kernel passes it; the inode run is real
        assert proc.args[0] == entry and _same(proc.args[0], real)
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg", (layout, out)
        assert _ran(home) == [real + ".ran"]
        os.unlink(real + ".ran")
        # the PATH finder sees the chain only where the OS follows it; the
        # walk and the spawn above did either way
        if os.path.basename(entry) == "dot" and os.path.isfile(entry):
            assert _dot2img(monkeypatch, bindir).strip() == "GRAPHVIZ-STUB -Tsvg"
            assert _ran(home) == [real + ".ran"]
        else:
            assert layout in (
                "homebrew_sibling_two_hops",
                "chain_at_the_bound",
                "forty_hops_the_last_climbing",
            )

    @pytest.mark.parametrize("layout", sorted(PLAIN), ids=sorted(PLAIN))
    @pytest.mark.parametrize("mode", MODES)
    def test_a_layout_without_dotdot_runs_by_its_resolved_path(
        self, home, monkeypatch, layout, mode
    ):
        bindir, entry, real = PLAIN[layout](home)
        got = _resolve(entry)
        assert got is not None and _same(got, real), (layout, mode, got)
        assert got == os.path.realpath(entry), (layout, mode, got)
        assert not os.path.islink(got) and _reason(entry) is None
        proc, out = _run(entry)
        assert proc.args[0] == entry and out.strip() == "GRAPHVIZ-STUB -Tsvg"
        assert _ran(home) == [real + ".ran"]
        os.unlink(real + ".ran")
        assert _dot2img(monkeypatch, bindir).strip() == "GRAPHVIZ-STUB -Tsvg"

    def test_ekaf_reproduction_on_the_homebrew_layout(self, home, monkeypatch):
        """The call from the report, with the Homebrew shape on PATH: it
        renders, the real file run once under the invoked name."""
        bindir, entry, real = homebrew(home)
        monkeypatch.setenv("PATH", bindir)
        from nltk.parse.dependencygraph import dot2img

        assert dot2img(GRAPH).strip() == "GRAPHVIZ-STUB -Tsvg"
        assert _ran(home) == [real + ".ran"]

    def test_the_display_hooks_on_the_homebrew_layout(self, home, monkeypatch):
        """``DependencyGraph._repr_svg_`` (through dot2img) and
        ``AlignedSent._repr_svg_`` (its own trusted spawn) both run the real
        file behind the Homebrew link."""
        from nltk.parse.dependencygraph import DependencyGraph
        from nltk.translate.api import AlignedSent, Alignment

        bindir, entry, real = homebrew(home)
        monkeypatch.setenv("PATH", bindir)
        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        for hook in (dg._repr_svg_, sent._repr_svg_):
            assert hook().strip() == "GRAPHVIZ-STUB -Tsvg", hook
            assert _ran(home) == [real + ".ran"], hook
            os.unlink(real + ".ran")

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
        joined = os.path.join(f"{home}/holder", "sub/../real")
        assert _same(os.path.normpath(joined), folded)  # what folding gives
        got = _runs(home, entry, kernel)
        assert os.path.samefile(entry, got) and not _same(got, folded)

    @pytest.mark.parametrize(
        "spelling", ["case_fold", "nfd_for_nfc"], ids=["case_fold", "nfd_for_nfc"]
    )
    def test_a_lookalike_component_is_judged_on_the_filesystem(self, home, spelling):
        """``../REAL/dot`` for ``real``, ``cafe`` + combining acute for ``caf``
        + e-acute: on a case- or normalisation-insensitive filesystem (macOS)
        the spelled component names the same verified directory and the
        resolved file is the same inode as the real tool; elsewhere it names
        nothing and is refused. Nothing unverified runs either way."""
        if spelling == "case_fold":
            real_dir, spelled = "real", "REAL"
        else:
            real_dir, spelled = "caf" + chr(0xE9), "cafe" + chr(0x301)
        real = _tool(f"{home}/{real_dir}/dot")
        entry = _ln(f"../{spelled}/dot", f"{home}/bin/dot")
        got = _resolve(entry)
        if got is None:
            assert not os.path.exists(entry)  # the kernel finds nothing either
            assert "cannot be inspected" in _reason(entry)
            with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
                _run(entry)
            assert _ran(home) == []
        else:
            assert os.path.samefile(got, real) and not os.path.islink(got)
            assert os.path.samefile(entry, got)  # the kernel agrees
            assert pathsec.is_private_dir(os.path.dirname(got))
            proc, out = _run(entry)
            assert proc.args[0] == entry and out.strip() == "GRAPHVIZ-STUB -Tsvg"
            ran = _ran(home)
            assert len(ran) == 1 and os.path.samefile(ran[0][: -len(".ran")], real)

    def test_a_homebrew_shaped_link_runs_for_every_tool(self, home, monkeypatch):
        """java, prover9 and hunpos found behind a ``..`` link: the finder
        hands the link over and the spawn runs the real file under the name
        the finder returned, as for dot."""
        from nltk.internals import find_binary_absolute

        real = _tool(f"{home}/Cellar/tool/1/bin/tool")
        for name in ("java", "prover9", "hunpos-tag"):
            _ln("../Cellar/tool/1/bin/tool", f"{home}/bin/{name}")
        monkeypatch.setenv("PATH", f"{home}/bin")
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.delenv("JAVAHOME", raising=False)
        for name in ("java", "prover9", "hunpos-tag"):
            found = find_binary_absolute(name, binary_names=[name])
            assert found == f"{home}/bin/{name}"
            _runs(home, found, real)


# =========================================================================== #
# Spoofs: refused with the reason naming the check and the path; none runs.   #
# =========================================================================== #


@POSIX
class TestSpoofLayoutsAreRefused:
    @pytest.mark.parametrize("layout", sorted(SPOOF), ids=sorted(SPOOF))
    @pytest.mark.parametrize("mode", MODES)
    def test_refused_with_the_reason(self, home, monkeypatch, layout, mode):
        bindir, entry, real, check, named = SPOOF[layout](home)
        assert _resolve(entry) is None, (layout, mode)
        reason = _reason(entry)
        # refused by the check the layout plants, never by a '..' as such
        assert check in reason and named in reason, (layout, mode, reason)
        assert "'..'" not in reason, (layout, mode, reason)
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
        assert _ran(home) == [], (layout, mode)

    @pytest.mark.parametrize("shape", ["absolute", "climbing"])
    def test_a_link_owned_by_another_user_is_refused(self, home, monkeypatch, shape):
        """Simulated (no root here): ``lstat`` of one link reports a foreign
        uid, at the entry and in the middle of a chain of absolute links or of
        ``..`` links. Its holder is private, so this is the link-owner check
        alone."""
        real = _tool(f"{home}/real/dot")
        if shape == "absolute":
            mid = _ln(real, f"{home}/mid/dot")
            entry = _ln(mid, f"{home}/bin/dot")
        else:
            mid = _ln("../real/dot", f"{home}/mid/dot")
            entry = _ln("../mid/dot", f"{home}/bin/dot")
        mode = shape
        assert _same(_resolve(entry), real)
        foreign = os.geteuid() + 4242
        for victim in (entry, mid):
            monkeypatch.setattr(pathsec.os, "lstat", _foreign_lstat(victim, foreign))
            assert _resolve(entry) is None, (victim, mode)
            reason = _reason(entry)
            assert f"symlink {victim!r} is owned by uid {foreign}" in reason, mode
            with pytest.raises(pathsec.TrustError, match="owned by uid"):
                _run(entry)
            monkeypatch.undo()
        assert _ran(home) == []
        assert _same(_resolve(entry), real)

    @pytest.mark.parametrize("mode", MODES)
    def test_a_foreign_link_is_refused_before_its_text_is_read(
        self, home, monkeypatch, mode
    ):
        """A link another user owns whose text climbs with ``..``: the owner
        is judged on ``lstat`` before ``readlink``, so the reason is the
        owner, and the text is never read."""
        _tool(f"{home}/real/dot")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        foreign = os.geteuid() + 4242
        monkeypatch.setattr(pathsec.os, "lstat", _foreign_lstat(entry, foreign))
        true_readlink = os.readlink
        read = []

        def readlink(path, *args, **kwargs):
            read.append(os.fspath(path))
            return true_readlink(path, *args, **kwargs)

        monkeypatch.setattr(pathsec.os, "readlink", readlink)
        reason = _reason(entry)
        assert reason.startswith(f"symlink {entry!r} is owned by uid {foreign}")
        assert read == [], mode
        assert _ran(home) == []

    @pytest.mark.parametrize("mode", MODES)
    def test_a_root_owned_link_in_a_writable_dir_and_the_reverse(
        self, home, monkeypatch, mode
    ):
        """A link root created in a directory anyone can write: the directory
        refuses it (the link can be swapped). A link another user created in
        a root-owned directory: the link owner refuses it."""
        _tool(f"{home}/real/dot")
        _dir(f"{home}/ww")
        entry = _ln("../real/dot", f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        monkeypatch.setattr(pathsec.os, "lstat", _foreign_lstat(entry, 0))
        assert _resolve(entry) is None
        reason = _reason(entry)
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
        assert _resolve(entry) is None
        reason = _reason(entry)
        assert f"symlink {entry!r} is owned by uid" in reason, mode
        with pytest.raises(pathsec.TrustError, match="owned by uid"):
            _run(entry)
        assert _ran(home) == []
        # the control: root's link in that root-owned private directory runs
        monkeypatch.setattr(pathsec.os, "lstat", _foreign_lstat(entry, 0))
        assert _resolve(entry) == os.path.realpath(entry), mode
        _runs(home, entry, f"{home}/real/dot")

    @pytest.mark.parametrize("mode", MODES)
    def test_a_link_into_the_shared_tmp_is_refused(self, home, mode):
        """``bin/dot`` pointing into a directory planted in the sticky
        ``/tmp``, by a climb with ``..`` past the root or by an absolute
        text: both are refused at ``/tmp``, which is world-writable."""
        tmp = "/tmp"
        if not (os.path.isdir(tmp) and os.stat(tmp).st_mode & stat.S_ISVTX):
            pytest.skip("/tmp is not a sticky world-writable dir here")
        plant = tempfile.mkdtemp(prefix="nltk_symlink_spoof_", dir=tmp)
        try:
            real = _tool(f"{plant}/dot")
            climbing = _ln("../" * 40 + real.lstrip("/"), f"{home}/bin/dot")
            absolute = _ln(real, f"{home}/abs/dot")
            for entry in (climbing, absolute):
                assert os.path.samefile(entry, real)  # the kernel follows it
                assert _resolve(entry) is None, (entry, mode)
                reason = _reason(entry)
                assert "world-writable" in reason and "tmp" in reason, mode
                with pytest.raises(pathsec.TrustError, match="world-writable"):
                    _run(entry)
            assert not os.path.exists(real + ".ran")
        finally:
            shutil.rmtree(plant, ignore_errors=True)

    @pytest.mark.parametrize("mode", MODES)
    def test_the_callers_own_dotdot_is_never_folded(self, home, mode):
        """A ``..`` in the target the caller hands over is refused, even when
        it folds to a trusted file and even when it is the resolved path of a
        link: an unresolved name before it could hide a link, and a
        configured location is never allowed one."""
        real = _tool(f"{home}/real/dot")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        resolved = _resolve(entry)
        assert resolved == os.path.realpath(entry) and _same(resolved, real)
        # a '..' after a link to a directory in the middle of the path: the
        # kernel would take that link target's parent; the walk refuses it
        _dir(f"{home}/other/inner")
        kernel = _tool(f"{home}/other/real/dot")
        _ln(f"{home}/other/inner", f"{home}/holder/sub")
        after_a_link = f"{home}/holder/sub/../real/dot"
        assert _same(os.path.realpath(after_a_link), kernel)
        assert _resolve(after_a_link) is None
        assert _reason(after_a_link) == f"{after_a_link!r} contains a '..' component"
        with pytest.raises(pathsec.TrustError, match="'..' component"):
            _run(after_a_link)
        for spelled in (
            f"{home}/bin/../real/dot",
            f"{home}/real/../real/dot",
            os.path.join(os.path.dirname(resolved), os.pardir, "real", "dot"),
        ):
            assert _same(os.path.realpath(spelled), real)
            assert _resolve(spelled) is None, (spelled, mode)
            assert _reason(spelled) == f"{spelled!r} contains a '..' component"
            with pytest.raises(pathsec.TrustError, match="'..' component"):
                _run(spelled)
        assert _ran(home) == []

    def test_a_fold_onto_a_root_owned_boundary_judges_each_child(
        self, home, monkeypatch
    ):
        """A mount-like boundary, simulated: ``mnt`` reported as owned by root
        (``stat`` says uid 0) and private, holding a group-writable ``gw`` and
        a private ``ok``. ``mnt/pkg/bin/dot -> ../../gw/dot`` folds onto
        ``mnt`` and is refused at ``gw``; ``mnt/pkg/bin/ok -> ../../ok/dot``
        runs."""
        mnt = _dir(f"{home}/mnt")
        bad = _tool(f"{mnt}/gw/dot")
        os.chmod(f"{mnt}/gw", 0o775)
        good = _tool(f"{mnt}/ok/dot")
        refused = _ln("../../gw/dot", f"{mnt}/pkg/bin/dot")
        runs = _ln("../../ok/dot", f"{mnt}/pkg/bin/ok")
        true_stat = os.stat

        def root_mnt(path, *args, **kwargs):
            st = true_stat(path, *args, **kwargs)
            if os.fspath(path) == mnt:
                fields = list(st)
                fields[stat.ST_UID] = 0
                st = os.stat_result(tuple(fields))
            return st

        monkeypatch.setattr(pathsec.os, "stat", root_mnt)
        assert pathsec._private_dir_problem(mnt) is None and os.stat(mnt).st_uid == 0
        _refused(home, refused, "group-writable", f"{mnt}/gw")
        _runs(home, runs, good)
        assert not os.path.exists(bad + ".ran")

    def test_a_hop_retargeted_between_readlink_and_the_descent_is_rewalked(
        self, home, monkeypatch
    ):
        """TOCTOU after the text is read: ``bin/dot -> ../pkg/dot`` is read,
        then, before the walk descends, ``pkg`` is swapped for a link into a
        world-writable directory holding a decoy. The descent ``lstat``s each
        component afresh, meets the new link and refuses ``ww``."""
        _tool(f"{home}/pkg/dot")
        decoy = _tool(f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        entry = _ln("../pkg/dot", f"{home}/bin/dot")
        true_readlink = os.readlink
        swapped = []

        def readlink(path, *args, **kwargs):
            text = true_readlink(path, *args, **kwargs)
            if os.fspath(path) == entry and not swapped:
                os.rename(f"{home}/pkg", f"{home}/pkg.orig")
                os.symlink(f"{home}/ww", f"{home}/pkg")
                swapped.append(text)
            return text

        monkeypatch.setattr(pathsec.os, "readlink", readlink)
        why = pathsec._Why()
        assert _walk(entry, why) is None and swapped == ["../pkg/dot"]
        reason = "; ".join(why)
        assert "world-writable" in reason and f"{home}/ww" in reason
        monkeypatch.undo()
        with pytest.raises(pathsec.TrustError, match="world-writable"):
            _run(entry)
        assert _ran(home) == [] and os.path.exists(decoy)
        assert os.path.isfile(f"{home}/pkg.orig/dot") and os.path.islink(f"{home}/pkg")

    @pytest.mark.parametrize("swap", ["link", "rename"])
    def test_a_climbing_entrys_final_file_swapped_is_refused(
        self, home, monkeypatch, swap
    ):
        """The final-component swap behind a ``..`` link: ``bin/dot ->
        ../real/dot``, and between the ``lstat`` that saw a regular file and
        the ``open``, ``real/dot`` becomes a link to a decoy in a
        world-writable directory (``O_NOFOLLOW`` refuses the open) or is
        renamed over by another file (the inode check refuses it)."""
        real = _tool(f"{home}/real/dot")
        decoy = _tool(f"{home}/ww/dot")
        other = _tool(f"{home}/real/other")
        os.chmod(f"{home}/ww", 0o777)
        entry = _ln("../real/dot", f"{home}/bin/dot")
        true_lstat = os.lstat
        seen = []

        def lstat(path, *args, **kwargs):
            st = true_lstat(path, *args, **kwargs)
            if os.fspath(path) == real:
                seen.append(path)
                if len(seen) == 2:  # the resolver's own lstat, after the walk
                    if swap == "link":
                        os.unlink(real)
                        os.symlink(decoy, real)
                    else:
                        os.replace(other, real)
            return st

        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        why = pathsec._Why()
        assert _walk(entry, why) is None and len(seen) == 2
        expected = {
            "link": "cannot be opened for verification",
            "rename": "changed while it was being verified",
        }[swap]
        assert expected in "; ".join(why) and real in "; ".join(why), swap
        monkeypatch.undo()
        assert _ran(home) == []

    def test_a_nul_in_link_text_is_refused_as_a_control_character(
        self, home, monkeypatch
    ):
        """No filesystem stores a NUL in a link's text (``symlink`` refuses
        it), so a ``readlink`` returning one is simulated: the walk refuses it
        by the control-character check, naming the link. The newline twin is
        a real link (``newline_in_link_text``)."""
        _tool(f"{home}/real/dot")
        with pytest.raises(ValueError):
            os.symlink("../real\x00/dot", f"{home}/bin/nul")
        entry = _ln("../real/dot", f"{home}/bin/dot")
        true_readlink = os.readlink

        def readlink(path, *args, **kwargs):
            text = true_readlink(path, *args, **kwargs)
            if os.fspath(path) == entry:
                text = text.replace("/dot", "\x00/dot")
            return text

        monkeypatch.setattr(pathsec.os, "readlink", readlink)
        reason = _refused(home, entry, "control character", entry)
        assert "\\x00" in reason

    def test_a_lying_str_subclass_target_is_read_once(self, home):
        """A ``str`` subclass whose methods all name a decoy in a
        world-writable directory: its real characters, a ``..`` link to the
        private tool, are what is checked and run, and argv[0] is a plain
        ``str`` of them."""
        real = _tool(f"{home}/real/dot")
        decoy = _tool(f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        entry = _ln("../real/dot", f"{home}/bin/dot")

        class Liar(str):
            def __fspath__(self):
                return decoy

            def __str__(self):
                return decoy

            def split(self, *args, **kwargs):
                return decoy.split(*args, **kwargs)

            def startswith(self, *args, **kwargs):
                return True

            def __contains__(self, item):
                return False

            def __eq__(self, other):
                return True

            __hash__ = str.__hash__

        proc, out = _run(Liar(entry))
        assert type(proc.args[0]) is str and str.__eq__(proc.args[0], entry)
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg"
        assert _ran(home) == [real + ".ran"] and not os.path.exists(decoy + ".ran")

    def test_a_path_like_that_flips_is_read_once(self, home):
        """A path-like naming the ``..`` link on its first read and a decoy in
        a world-writable directory on every later one: read once, the link
        runs; the decoy first is refused, whatever follows."""
        real = _tool(f"{home}/real/dot")
        decoy = _tool(f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        entry = _ln("../real/dot", f"{home}/bin/dot")

        class Flip(os.PathLike):
            def __init__(self, *answers):
                self.answers, self.calls = answers, 0

            def __fspath__(self):
                self.calls += 1
                return self.answers[min(self.calls, len(self.answers)) - 1]

        flip = Flip(entry, decoy)
        proc, out = _run(flip)
        assert flip.calls == 1 and proc.args[0] == entry
        assert _ran(home) == [real + ".ran"]
        os.unlink(real + ".ran")
        flip = Flip(decoy, entry)
        with pytest.raises(pathsec.TrustError, match="world-writable"):
            _run(flip)
        assert flip.calls == 1 and _ran(home) == []

    def test_relative_and_odd_targets_name_their_reason(self, home):
        real = _tool(f"{home}/bin/dot")
        assert "not absolute" in _reason("bin/dot")
        assert "NUL" in _reason(real + "\x00")
        assert "not a str path" in _reason(7)
        assert "not a str path" in _reason(None)
        missing = f"{home}/nowhere/dot"
        assert "cannot be inspected" in _reason(missing)
        assert _reason(real) is None

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
        mid = _ln(real, f"{home}/mid/dot")
        entry = _ln(mid, f"{home}/bin/dot")
        true_readlink = os.readlink

        def readlink(path, *args, **kwargs):
            if os.fspath(path) == mid and true_readlink(mid) == real:
                os.unlink(mid)
                os.symlink(decoy, mid)
            return true_readlink(path, *args, **kwargs)

        monkeypatch.setattr(pathsec.os, "readlink", readlink)
        assert _resolve(entry) is None
        reason = _reason(entry)
        assert "world-writable" in reason and f"{home}/ww" in reason, mode
        with pytest.raises(pathsec.TrustError, match="world-writable"):
            _run(entry)
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
        entry = real
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
        assert _walk(entry, why) is None
        swapped = len(seen)  # os.path.islink below goes through the patch too
        assert os.path.islink(real) and swapped == 2
        assert "cannot be opened for verification" in "; ".join(why), mode
        os.unlink(real)
        _tool(real)
        seen.clear()
        # the spawn is refused; its diagnostic walk runs after the swap, so the
        # reason it reports is the link it now finds, into the writable dir
        with pytest.raises(pathsec.TrustError, match="world-writable") as excinfo:
            _run(entry)
        assert f"{home}/ww" in str(excinfo.value)
        assert _ran(home) == []

    @pytest.mark.parametrize("mode", MODES)
    def test_a_final_component_replaced_by_another_file_is_seen(
        self, home, monkeypatch, mode
    ):
        """The same window, the file renamed over by another regular file:
        the inode opened is not the one inspected, and that is the reason."""
        real = _tool(f"{home}/real/dot")
        other = _tool(f"{home}/real/other")
        entry = real
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
        assert _resolve(entry) is None
        _tool(other)
        seen.clear()
        assert "changed while it was being verified" in _reason(entry), mode
        assert _ran(home) == []


# =========================================================================== #
# Teeth: removing each check lets a named spoof through.                       #
# =========================================================================== #


@POSIX
class TestTeeth:
    @pytest.mark.parametrize("shape", ["absolute", "climbing"])
    def test_without_the_link_owner_check_a_foreign_link_runs(
        self, home, monkeypatch, shape
    ):
        real = _tool(f"{home}/real/dot")
        text = real if shape == "absolute" else "../real/dot"
        entry = _ln(text, f"{home}/bin/dot")
        monkeypatch.setattr(
            pathsec.os, "lstat", _foreign_lstat(entry, os.geteuid() + 4242)
        )
        assert _resolve(entry) is None, shape
        assert "owned by uid" in _reason(entry), shape
        monkeypatch.setattr(pathsec, "_link_owner_problem", lambda path, st: None)
        assert _resolve(entry) == os.path.realpath(real), shape

    def test_without_the_hop_bound_an_overlong_chain_runs(self, home, monkeypatch):
        """Absolute links, no ``..``, so the bound alone refuses the chain one
        hop over it; the chain exactly at it resolves."""
        real = _tool(f"{home}/real/dot")
        hops = [real]
        for i in range(pathsec._MAX_LINK_HOPS + 1):
            hops.append(_ln(hops[-1], f"{home}/l{i}/dot"))
        at_the_bound, over_it = hops[-2], hops[-1]
        assert _same(_resolve(at_the_bound), real)
        assert _resolve(over_it) is None
        assert "longer than" in _reason(over_it)
        monkeypatch.setattr(pathsec, "_MAX_LINK_HOPS", 10_000)
        assert _same(_resolve(over_it), real)

    @pytest.mark.parametrize(
        "layout", ["chain_over_the_bound", "forty_one_hops_the_last_climbing"]
    )
    def test_without_the_hop_bound_a_climbing_chain_over_it_runs(
        self, home, monkeypatch, layout
    ):
        _, entry, real, check, _ = SPOOF[layout](home)
        assert _resolve(entry) is None and check in _reason(entry)
        monkeypatch.setattr(pathsec, "_MAX_LINK_HOPS", 10_000)
        assert _resolve(entry) == os.path.realpath(real), layout

    @pytest.mark.parametrize(
        "layout",
        [
            "absolute_link_into_writable",
            "hard_link_in_a_writable_dir",
            "group_writable_target_dir",
            "world_writable_sticky_target_dir",
            "world_writable_intermediate_dir",
            "writable_dir_descended_into_through_dotdot",
            "climb_above_the_root_into_writable_and_back",
            "dotdot_landing_on_a_dir_link_into_writable",
            "absolute_text_with_dotdot_into_writable",
            "dotdot_after_a_mid_path_dir_link_into_writable",
        ],
    )
    def test_without_the_directory_check_a_writable_dir_runs(
        self, home, monkeypatch, layout
    ):
        _, entry, real, check, _ = SPOOF[layout](home)
        assert _resolve(entry) is None
        assert check in _reason(entry)
        monkeypatch.setattr(pathsec, "is_private_dir", lambda path: True)
        got = _resolve(entry)  # the hard link is its own name for the one inode
        assert got is not None and os.path.samefile(got, real), layout

    @pytest.mark.parametrize(
        "layout",
        [
            "group_writable_target_file",
            "world_writable_target_file",
            "dotdot_after_a_dir_link_lands_on_a_writable_file",
        ],
    )
    def test_without_the_file_check_a_writable_target_runs(
        self, home, monkeypatch, layout
    ):
        _, entry, real, check, _ = SPOOF[layout](home)
        assert _resolve(entry) is None and check in _reason(entry), layout
        monkeypatch.setattr(pathsec, "_private_stat", lambda st: True)
        assert _resolve(entry) == os.path.realpath(real), layout

    @pytest.mark.parametrize("shape", ["absolute", "climbing"])
    def test_without_the_control_character_check_a_newline_link_runs(
        self, home, monkeypatch, shape
    ):
        """A link whose text holds a line break, to a real private file in a
        directory named with one: absolute, or the ``newline_in_link_text``
        spoof, which climbs with ``..``."""
        if shape == "absolute":
            real = _tool(f"{home}/re\nal/dot")
            entry = _ln(real, f"{home}/bin/dot")
        else:
            _, entry, real, _, _ = newline_in_link_text(home)
        assert _resolve(entry) is None
        assert "control character" in _reason(entry)
        monkeypatch.setattr(pathsec, "_link_text_problem", lambda path, link: None)
        assert _resolve(entry) == os.path.realpath(real), shape

    def test_with_a_lexical_fold_the_dir_link_spoof_runs_its_decoy(
        self, home, monkeypatch
    ):
        """The fold steps to the real parent of the resolved directory: fold
        a link's text lexically instead and ``holder/dot -> sub/../tool``
        names ``holder/tool``, the private decoy, while the kernel's
        ``other/tool`` is the group-writable file that refuses it."""
        _, entry, real, check, named = dotdot_after_a_dir_link_lands_on_a_writable_file(
            home
        )
        assert _resolve(entry) is None and named in _reason(entry)
        true_walk = pathsec._resolve_private

        def lexical(path, _hops=0, why=None, _link=None):
            if _link is not None:
                path = os.path.normpath(path)
            return true_walk(path, _hops, why=why, _link=_link)

        monkeypatch.setattr(pathsec, "_resolve_private", lexical)
        got = _resolve(entry)
        assert got == f"{home}/holder/tool" and not _same(got, real)

    def test_without_the_callers_dotdot_refusal_a_typed_dotdot_runs(
        self, home, monkeypatch
    ):
        """Treat the caller's own ``..`` as a link's and the typed
        ``holder/sub/../real/dot`` (``sub`` a directory link) resolves; the
        refusal is the one thing that stops it."""
        _dir(f"{home}/other/inner")
        kernel = _tool(f"{home}/other/real/dot")
        _ln(f"{home}/other/inner", f"{home}/holder/sub")
        typed = f"{home}/holder/sub/../real/dot"
        assert _resolve(typed) is None and "'..' component" in _reason(typed)
        true_walk = pathsec._resolve_private

        def as_a_link(path, _hops=0, why=None, _link=None):
            return true_walk(path, _hops, why=why, _link=_link or ("typed", path))

        monkeypatch.setattr(pathsec, "_resolve_private", as_a_link)
        assert _resolve(typed) == os.path.realpath(kernel)

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
        entry = real
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
        assert _walk(entry, why) is None
        assert "changed while it was being verified" in "; ".join(why), mode
        os.unlink(real)
        _tool(real)
        seen.clear()
        monkeypatch.undo()
        monkeypatch.setattr(pathsec.os, "lstat", lstat)
        monkeypatch.setattr(pathsec, "_same_inode", lambda a, b: True)
        why = pathsec._Why()
        assert _walk(entry, why) is None
        assert "cannot be opened for verification" in "; ".join(why), mode
        os.unlink(real)
        _tool(real)
        seen.clear()
        # both gone: the decoy is what the returned path now names
        monkeypatch.setattr(pathsec, "_open_verified", lambda real, why: os.stat(real))
        got = _resolve(entry)
        assert got == real and os.path.realpath(got) == os.path.realpath(decoy)

    def test_the_spawn_runs_what_the_resolver_returned(self, home, monkeypatch):
        """The reason is a second, diagnostic walk on a refusal only; the
        spawn walks once and executes the one path the resolver returned,
        read once from a path-like."""
        real = _tool(f"{home}/real/dot")
        entry = _ln(real, f"{home}/bin/dot")
        calls = []
        true_resolve = pathsec._resolve_trusted

        def resolve(target, why=None):
            calls.append(target)
            return true_resolve(target, why)

        monkeypatch.setattr(pathsec, "_resolve_trusted", resolve)
        proc, out = _run(Path(entry))
        assert calls == [entry]
        assert proc.args[0] == entry  # the invoked path, read once
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg"


# =========================================================================== #
# What reaches execve: argv[0] as invoked, the verified inode as executable.   #
# =========================================================================== #


@POSIX
class TestInvokedName:
    """What reaches ``execve``: the inode run is the verified resolved file
    (``executable=``), argv[0] is the verified path the caller invoked. A
    multi-call binary dispatches on argv[0] (Debian's ``/usr/bin/dot`` is a
    link to ``libgvc6-config-update``), so the resolved path there would make
    dot refuse to run; a shell stub cannot see argv[0], so these tests pin
    what is passed at the ``Popen`` call."""

    @staticmethod
    def _capture(monkeypatch):
        seen = {}
        true_popen = subprocess.Popen

        def popen(args, **kw):
            seen["args"], seen["executable"] = list(args), kw.get("executable")
            return true_popen(args, **kw)

        monkeypatch.setattr(pathsec.subprocess, "Popen", popen)
        return seen

    @pytest.mark.parametrize("layout", sorted(PLAIN), ids=sorted(PLAIN))
    def test_a_linked_tool_runs_its_target_under_the_invoked_name(
        self, home, monkeypatch, layout
    ):
        bindir, entry, real = PLAIN[layout](home)
        seen = self._capture(monkeypatch)
        proc, out = _run(entry)
        assert seen["args"] == [entry, "-Tsvg"]
        assert _same(seen["executable"], real)
        assert not os.path.islink(seen["executable"])
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg"

    @pytest.mark.parametrize("layout", sorted(CLIMBING), ids=sorted(CLIMBING))
    def test_a_climbing_link_runs_its_target_under_the_invoked_name(
        self, home, monkeypatch, layout
    ):
        bindir, entry, real = CLIMBING[layout](home)
        seen = self._capture(monkeypatch)
        proc, out = _run(entry)
        assert seen["args"] == [entry, "-Tsvg"]
        assert seen["executable"] == os.path.realpath(entry)
        assert _same(seen["executable"], real)
        assert not os.path.islink(seen["executable"])
        assert out.strip() == "GRAPHVIZ-STUB -Tsvg"

    @pytest.mark.parametrize("mode", MODES)
    def test_a_debian_multicall_link_keeps_its_own_name(self, home, monkeypatch, mode):
        """``dot``, ``neato`` and ``circo`` are links to one binary; each runs
        the shared inode under its own name, which is what tells the binary
        which program to be."""
        bindir, entry, real = multicall(home)
        for name in ("dot", "neato", "circo"):
            seen = self._capture(monkeypatch)
            proc, out = _run(f"{bindir}/{name}")
            assert seen["args"][0] == f"{bindir}/{name}", (mode, name, seen)
            assert _same(seen["executable"], real)
            assert out.strip() == "GRAPHVIZ-STUB -Tsvg"

    @pytest.mark.parametrize("mode", MODES)
    def test_a_path_like_is_invoked_by_its_text_read_once(
        self, home, monkeypatch, mode
    ):
        real = _tool(f"{home}/real/dot")
        entry = _ln(real, f"{home}/bin/dot")  # absolute link, no '..'
        seen = self._capture(monkeypatch)
        _run(Path(entry))
        assert seen["args"][0] == entry and _same(seen["executable"], real), mode


# =========================================================================== #
# The real Graphviz, nothing stubbed (CI sets NLTK_CI_REQUIRE_GRAPHVIZ).      #
# =========================================================================== #

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


def _entry_points():
    """Every way NLTK runs dot: dot2img (svg and png) and both display hooks."""
    from nltk.parse.dependencygraph import DependencyGraph, dot2img
    from nltk.translate.api import AlignedSent, Alignment

    dg = DependencyGraph("a N 2\nb V 0")
    sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
    return {
        "dot2img svg": lambda: dot2img(GRAPH),
        "dot2img png": lambda: dot2img(GRAPH, "png"),
        "DependencyGraph._repr_svg_": dg._repr_svg_,
        "AlignedSent._repr_svg_": sent._repr_svg_,
    }


def _capture_spawns(monkeypatch):
    """Record the argv and ``executable=`` of every trusted spawn."""
    seen = []
    true_popen = subprocess.Popen

    def popen(args, **kw):
        seen.append((list(args), kw.get("executable")))
        return true_popen(args, **kw)

    monkeypatch.setattr(pathsec.subprocess, "Popen", popen)
    return seen


def _all_render(dot, real, monkeypatch):
    """Every entry point renders well-formed SVG (and PNG through dot2img)
    with the installed *dot* as argv[0] and its resolved *real* run."""
    seen = _capture_spawns(monkeypatch)
    calls = _entry_points()
    _valid_svg(calls["dot2img svg"]())
    assert calls["dot2img png"]()[:8] == PNG
    _valid_svg(calls["DependencyGraph._repr_svg_"]())
    _valid_svg(calls["AlignedSent._repr_svg_"]())
    assert [(args[0], exe) for args, exe in seen] == [(dot, real)] * 4, seen
    monkeypatch.undo()


def _all_refused(reason):
    """Every entry point raises with *reason* in its message, the TrustError
    as its cause."""
    for name, call in _entry_points().items():
        with pytest.raises(Exception) as excinfo:
            call()
        assert reason in str(excinfo.value), (name, str(excinfo.value))
        assert isinstance(excinfo.value.__cause__, pathsec.TrustError), name


class TestRealGraphviz:
    def test_the_installed_dot_renders_under_its_invoked_name(self, monkeypatch):
        """The dot as installed, nothing stubbed: apt's multi-call
        ``/usr/bin/dot -> ../sbin/libgvc6-config-update``, Homebrew's
        ``bin/dot -> ../Cellar/graphviz/<v>/bin/dot`` (its chain made private,
        as CI does) and choco's plain ``dot.exe`` each render well-formed SVG
        and PNG through dot2img and both display hooks, run by the resolved
        file with argv[0] the path the finder returned. apt's binary is dot
        only under that name: run by its own name it refuses to lay out a
        graph, so this is the live proof of the argv[0] contract. A refusal
        fails in CI."""
        dot = _real_dot()
        reason = pathsec.untrusted_executable_reason(dot)
        if reason is not None:
            _all_refused(reason)
            message = f"the installed dot {dot!r} is refused: {reason}"
            if _required():
                pytest.fail(message)
            pytest.skip(message)
        real = pathsec.resolve_trusted_executable(dot)
        if os.name == "posix":
            assert real == os.path.realpath(dot) and not os.path.islink(real)
        _all_render(dot, real, monkeypatch)
        if os.path.splitext(os.path.basename(real))[0].lower() != "dot":
            # a multi-call binary named otherwise (apt's libgvc6-config-update):
            # invoked by its resolved path, it is not dot and renders nothing
            proc = pathsec.spawn_trusted(
                real,
                ["-Tsvg"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = proc.communicate(GRAPH.encode())
            assert proc.args[0] == real and b"<svg" not in out, (out, err)
            assert proc.returncode != 0, (out, err)

    @POSIX
    def test_the_installed_dot_behind_a_homebrew_shaped_chain(self, home, monkeypatch):
        """The real binary, by its resolved path, at the end of a real
        ``bin/dot -> ../Cellar/graphviz/<v>/bin/dot`` chain built here: it
        renders through every entry point with argv[0] the link invoked, and
        the two-hop ``bin/circo`` renders under the name ``circo``. The same
        binary behind a world-writable directory is refused with that
        reason."""
        dot = _real_dot()
        real = pathsec.resolve_trusted_executable(dot)
        if real is None:
            message = f"the installed dot {dot!r} is refused: {_reason(dot)}"
            if _required():
                pytest.fail(message)
            pytest.skip(message)
        cellar = f"{home}/usr/local/Cellar/graphviz/14.1.2/bin"
        _ln(real, f"{cellar}/dot")
        _ln("dot", f"{cellar}/circo")
        brew = _ln("../Cellar/graphviz/14.1.2/bin/dot", f"{home}/usr/local/bin/dot")
        circo = _ln(
            "../Cellar/graphviz/14.1.2/bin/circo", f"{home}/usr/local/bin/circo"
        )
        monkeypatch.setenv("PATH", f"{home}/usr/local/bin")
        assert pathsec.untrusted_executable_reason(brew) is None
        assert pathsec.resolve_trusted_executable(brew) == real
        _all_render(brew, real, monkeypatch)
        monkeypatch.setenv("PATH", f"{home}/usr/local/bin")
        seen = _capture_spawns(monkeypatch)
        proc = pathsec.spawn_trusted(
            circo,
            ["-Tsvg"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _valid_svg(proc.communicate(GRAPH.encode())[0].decode())
        assert seen == [([circo, "-Tsvg"], real)]
        monkeypatch.undo()
        # the same real binary behind a world-writable directory
        _dir(f"{home}/ww")
        _ln(real, f"{home}/ww/dot")
        os.chmod(f"{home}/ww", 0o777)
        _ln("../ww/dot", f"{home}/sbin/dot")
        monkeypatch.setenv("PATH", f"{home}/sbin")
        reason = pathsec.untrusted_executable_reason(f"{home}/sbin/dot")
        assert "world-writable" in reason and f"{home}/ww" in reason
        _all_refused(reason)


# =========================================================================== #
# Windows: junctions and reparse points, best-effort by design.                #
# =========================================================================== #


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
        got = _resolve(entry)
        assert got is not None and os.path.isfile(got), mode
        assert os.path.samefile(got, real)
        assert "junc" not in [part.lower() for part in Path(got).parts]
        assert _reason(entry) is None

    @pytest.mark.parametrize("mode", MODES)
    def test_a_dangling_junction_is_refused_with_the_reason(self, tmp_path, mode):
        (tmp_path / "gone").mkdir()
        self._junction(tmp_path / "gone", tmp_path / "junc")
        os.rmdir(tmp_path / "gone")
        entry = str(tmp_path / "junc" / "dot.exe")
        assert _resolve(entry) is None, mode
        assert "cannot be inspected" in _reason(entry)
        with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
            pathsec.spawn_trusted(entry, [])

    @pytest.mark.parametrize("mode", MODES)
    def test_a_junction_to_a_directory_is_not_a_regular_file(self, tmp_path, mode):
        (tmp_path / "adir").mkdir()
        self._junction(tmp_path / "adir", tmp_path / "junc")
        entry = str(tmp_path / "junc")
        assert _resolve(entry) is None, mode
        assert "not a regular file" in _reason(entry)


def test_reason_api_is_available_on_every_platform(home):
    # under a private chain, so the first reason is the missing file itself,
    # not the shared sticky /tmp that holds pytest's tmp_path on Linux
    missing = str(home / "nowhere" / "dot")
    reason = pathsec.untrusted_executable_reason(missing)
    assert reason and "cannot be inspected" in reason
    assert pathsec.resolve_trusted_executable(missing) is None
    with pytest.raises(pathsec.TrustError, match="cannot be inspected"):
        pathsec.spawn_trusted(missing, [])
