"""GHSA-cc5r-64rf-75hg [high] : Untrusted search path in the tool config entry
points (prover9/mace4, megam, tadm, java, hunpos) allows local code execution
via a relative binary location (CWE-426, CWE-427)"""

import os
import pathlib
import shutil
import stat
import tempfile

from ._base import FIXED, VULNERABLE, probe, register_data_root

_TOOL_ENV = ("PROVER9", "MEGAM", "TADM", "JAVAHOME", "JAVA_HOME", "HUNPOS_TAGGER")


class _Spawned(Exception):
    """Raised in place of the hunpos spawn, carrying the binary it was given."""


class _LyingStr(str):
    """A location whose string methods lie. ``posixpath.isabs`` asks
    ``startswith``; ``ntpath.isabs`` slices and replaces first; a NUL check asks
    ``in``. Every one of them is answered with a lie."""

    def startswith(self, *args, **kwargs):
        return True

    def replace(self, *args, **kwargs):
        return self

    def __getitem__(self, key):
        return self

    def __contains__(self, item):
        return False


def _plant(directory, relpath):
    path = os.path.join(directory, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\necho PWNED\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


def _relative_forms(name, box):
    forms = [
        ".",
        "./",
        "./" + name,
        "sub/" + name,
        "sub",
        "sub/",
        "./sub/../" + name,
        "../" + os.path.basename(box) + "/" + name,
    ]
    if os.name == "nt":
        forms += [
            ".\\" + name,
            "sub\\" + name,
            "..\\" + os.path.basename(box) + "\\" + name,
        ]
    return forms


def _odd_forms(name):
    """Relative locations that are not plain strings, or carry a NUL byte."""
    relative = "./" + name
    return [
        _LyingStr(relative),
        _LyingStr(relative + chr(0)),
        pathlib.Path(relative),
        relative.encode(),
        relative + chr(0),
    ]


def _inside(path, box):
    return os.path.realpath(str(path)).startswith(os.path.realpath(box) + os.sep)


def _scrubbed_path(directory):
    """A PATH holding nothing but ``which``, which find_file_iter shells out to."""
    real_which = shutil.which("which")
    if os.name == "posix" and real_which:
        os.symlink(real_which, os.path.join(directory, "which"))
    return directory


def _entry_points(legit):
    """(label, binary name, configure(location) -> resolved binary path)."""
    import nltk.tag.hunpos as hunpos_module
    from nltk import internals
    from nltk.classify import megam, tadm
    from nltk.inference.mace import Mace
    from nltk.inference.prover9 import Prover9

    def prover9(location):
        tool = Prover9()
        tool.config_prover9(location)
        return tool._prover9_bin

    def mace(location):
        tool = Mace()
        tool.config_prover9(location)
        return tool._prover9_bin

    def megam_config(location):
        megam.config_megam(location)
        return megam._megam_bin

    def tadm_config(location):
        tadm.config_tadm(location)
        return tadm._tadm_bin

    def java_config(location):
        internals.config_java(location)
        return internals._java_bin

    model = os.path.join(legit, "en_wsj.model")

    def hunpos_tagger(location):
        # the constructor spawns the binary it resolved; capture that instead
        def _record(target, *args, **kwargs):
            raise _Spawned(target)

        saved = hunpos_module.spawn_trusted
        hunpos_module.spawn_trusted = _record
        try:
            hunpos_module.HunposTagger(model, path_to_bin=location)
        except _Spawned as spawned:
            return spawned.args[0]
        finally:
            hunpos_module.spawn_trusted = saved
        raise AssertionError("HunposTagger returned without spawning")

    return [
        ("config_prover9", "prover9", prover9),
        ("Mace.config_prover9", "prover9", mace),
        ("config_megam", "megam", megam_config),
        ("config_tadm", "tadm", tadm_config),
        ("config_java", "java", java_config),
        ("HunposTagger", "hunpos-tag", hunpos_tagger),
    ]


def _leak(label, form, resolved, box, expected=None):
    """The VULNERABLE verdict for a resolution, or None if it is acceptable."""
    if _inside(resolved, box):
        return f"{label}({form!r}) took the CWD-relative binary {resolved!r}"
    if expected is None:
        return (
            f"{label}({form!r}) resolved {resolved!r} with no trusted location "
            "configured"
        )
    if os.path.realpath(str(resolved)) != expected:
        return (
            f"{label}({form!r}) resolved {resolved!r} instead of the configured "
            f"install {expected!r}"
        )
    return None


@probe("GHSA-cc5r-64rf-75hg")
def _relative_binary_location():
    """Plant decoy binaries in a temporary CWD and configure each tool with every
    relative location form (including non-str, NUL-bearing and lying-string
    forms), first with no tool reachable through the environment (only the
    decoys can match: each form must be refused), then with a trusted absolute
    install configured through the tool's env var (each form must either be
    refused or resolve to that install, never to a decoy), then with the env
    var itself pointing through ``..`` at the decoy directory (the same rule).

    Before the fix these entry points forwarded the location to ``find_binary``,
    which honours an explicit relative path, so the tool's spawn would have run
    the planted file. They now resolve through ``find_binary_absolute``. The
    probe checks WHICH binary was chosen, not merely whether the call raised: on
    a machine with a real install configured, a relative form resolving to that
    install is the correct outcome, not a leak.
    """
    from nltk import internals
    from nltk.classify import megam, tadm

    # both under $HOME: hunpos validates its model as private and in-sandbox
    # (a shared temp dir is neither), and the '..' env-var phase needs the decoy
    # directory to be a sibling of the install
    home = os.path.expanduser("~")
    box = tempfile.mkdtemp(prefix=".nltk_cc5r_box_", dir=home)
    legit = tempfile.mkdtemp(prefix=".nltk_cc5r_legit_", dir=home)
    empty = os.path.join(legit, "empty")
    os.makedirs(empty)
    scrubbed = _scrubbed_path(empty)
    tools = _entry_points(legit)
    for name in {name for _, name, _ in tools}:
        _plant(box, name)
        _plant(box, os.path.join("sub", name))
        _plant(legit, name)
    with open(os.path.join(legit, "en_wsj.model"), "w", encoding="utf-8") as fh:
        fh.write("stub\n")
    saved_env = {var: os.environ.get(var) for var in _TOOL_ENV + ("PATH",)}
    saved_bins = (megam._megam_bin, tadm._tadm_bin, internals._java_bin)
    undo_root = register_data_root(legit)
    old_cwd = os.getcwd()
    refused = 0
    try:
        os.chdir(box)
        # phase 1: nothing but the CWD decoys can match
        for var in _TOOL_ENV:
            os.environ.pop(var, None)
        os.environ["PATH"] = scrubbed
        for label, name, configure in tools:
            for form in _relative_forms(name, box) + _odd_forms(name):
                try:
                    resolved = configure(form)
                except LookupError:
                    refused += 1
                    continue
                return VULNERABLE, _leak(label, form, resolved, box)
        # phase 2: a trusted absolute install is configured; the decoys must
        # never shadow it
        for var in _TOOL_ENV:
            os.environ[var] = legit
        for label, name, configure in tools:
            expected = os.path.realpath(os.path.join(legit, name))
            for form in _relative_forms(name, box):
                try:
                    resolved = configure(form)
                except LookupError:
                    refused += 1
                    continue
                verdict = _leak(label, form, resolved, box, expected)
                if verdict:
                    return VULNERABLE, verdict
        # phase 3: the env var itself climbs through '..' into the decoy
        # directory; a location joined onto it must not land there either
        through = os.path.join(legit, os.pardir, os.path.basename(box))
        for var in _TOOL_ENV:
            os.environ[var] = through
        for label, name, configure in tools:
            for form in _relative_forms(name, box):
                try:
                    resolved = configure(form)
                except LookupError:
                    refused += 1
                    continue
                if _inside(resolved, box):
                    return (
                        VULNERABLE,
                        f"{label}({form!r}) with the env var set to {through!r} "
                        f"took the decoy {resolved!r}",
                    )
        return (
            FIXED,
            f"{refused} relative locations refused across {len(tools)} entry "
            "points; with an install configured every form resolved to it and "
            "never to a CWD decoy",
        )
    finally:
        os.chdir(old_cwd)
        for var, value in saved_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        megam._megam_bin, tadm._tadm_bin, internals._java_bin = saved_bins
        undo_root()
        shutil.rmtree(box, ignore_errors=True)
        shutil.rmtree(legit, ignore_errors=True)
