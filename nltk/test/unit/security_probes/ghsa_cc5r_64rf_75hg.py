"""GHSA-cc5r-64rf-75hg [high] : Untrusted search path in the tool config entry
points (prover9/mace4, megam, tadm, java, hunpos) allows local code execution
via a relative binary location (CWE-426, CWE-427)"""

import os
import pathlib
import shlex
import shutil
import stat
import tempfile

from ._base import FIXED, VULNERABLE, probe, register_data_root

_TOOL_ENV = (
    "PROVER9",
    "MEGAM",
    "TADM",
    "JAVAHOME",
    "JAVA_HOME",
    "HUNPOS_TAGGER",
    "SENNA",
    "CANDC",
    "REPP_TOKENIZER",
)


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


def _plant(directory, relpath, marker=None):
    """An executable decoy; given a *marker* file it also appends its own path
    there when it runs, so a launch is visible even if the caller discards
    the decoy's output or errors on it afterwards."""
    path = os.path.join(directory, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = ""
    if marker is not None:
        record = f"printf '%s\\n' {shlex.quote(path)} >> {shlex.quote(marker)}\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\n" + record + "echo PWNED\n")
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
    real, root = os.path.realpath(str(path)), os.path.realpath(box)
    return real == root or real.startswith(root + os.sep)


def _scrubbed_path(directory):
    """A PATH holding nothing but ``which``, which find_file_iter shells out to."""
    real_which = shutil.which("which")
    if os.name == "posix" and real_which:
        os.symlink(real_which, os.path.join(directory, "which"))
    return directory


def _entry_points(legit):
    """(label, binary name, configure(location) -> resolved binary path, plant)
    where plant(directory) puts that tool's files into a directory."""
    import nltk.tag.hunpos as hunpos_module
    from nltk import internals
    from nltk.classify import megam, tadm
    from nltk.classify.senna import Senna
    from nltk.inference.mace import Mace
    from nltk.inference.prover9 import Prover9
    from nltk.sem.boxer import Boxer
    from nltk.tokenize.repp import ReppTokenizer

    def plant_binary(name):
        return lambda directory: _plant(directory, name)

    senna_name = os.path.basename(Senna.executable(None, "x"))

    def senna_config(location):
        tool = Senna(location, ["pos"])
        return tool.executable(tool._path)

    def boxer_config(location):
        return Boxer(bin_dir=location)._candc_bin

    def plant_boxer(directory):
        _plant(directory, "candc")
        _plant(directory, "boxer")

    def repp_config(location):
        return os.path.join(ReppTokenizer(location).repp_dir, "src", "repp")

    def plant_repp(directory):
        _plant(directory, os.path.join("src", "repp"))
        os.makedirs(os.path.join(directory, "erg"), exist_ok=True)
        with open(
            os.path.join(directory, "erg", "repp.set"), "w", encoding="utf-8"
        ) as fh:
            fh.write("")

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

    # (label, name, configure, plant, search): search() is the lookup a tool
    # makes with NO location given (env var, searchpath and PATH only)
    return [
        (
            "config_prover9",
            "prover9",
            prover9,
            plant_binary("prover9"),
            lambda: Prover9()._find_binary("prover9"),
        ),
        (
            "Mace.config_prover9",
            "prover9",
            mace,
            plant_binary("prover9"),
            lambda: Mace()._find_binary("prover9"),
        ),
        (
            "config_megam",
            "megam",
            megam_config,
            plant_binary("megam"),
            lambda: megam_config(None),
        ),
        (
            "config_tadm",
            "tadm",
            tadm_config,
            plant_binary("tadm"),
            lambda: tadm_config(None),
        ),
        (
            "config_java",
            "java",
            java_config,
            plant_binary("java"),
            lambda: java_config(None),
        ),
        (
            "HunposTagger",
            "hunpos-tag",
            hunpos_tagger,
            plant_binary("hunpos-tag"),
            lambda: hunpos_tagger(None),
        ),
        (
            "Senna",
            senna_name,
            senna_config,
            plant_binary(senna_name),
            lambda: senna_config(None),
        ),
        ("Boxer", "candc", boxer_config, plant_boxer, lambda: boxer_config(None)),
        ("ReppTokenizer", "repp", repp_config, plant_repp, lambda: repp_config(None)),
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


_SINK_NAMES = ("prover9", "mace4", "prooftrans", "interpformat")


def _plant_sinks(box, marker):
    """The binaries the prover9/mace4 sinks would run, planted as recording
    decoys in the CWD and in a subdirectory of it."""
    for name in _SINK_NAMES:
        _plant(box, name, marker)
        _plant(os.path.join(box, "sub"), name, marker)


def _sink_phase(box, marker):
    """Phase 6, the advisory's sink itself. Prover9 and Mace are configured
    with each relative form and then RUN (``prove()`` and ``build_model()``,
    the calls that would have spawned the configured binary), with nothing
    reachable through the environment. Returns (VULNERABLE evidence or None,
    refusals). Judged by the marker the decoys write when they run and by the
    binary the tool holds afterwards, never by whether a call raised: on a host
    with a real install on the default search list the install runs instead.
    """
    from nltk.inference.mace import Mace, MaceCommand
    from nltk.inference.prover9 import Prover9, Prover9Command
    from nltk.sem import Expression

    goal = Expression.fromstring("mortal(socrates)")
    assumptions = [
        Expression.fromstring("man(socrates)"),
        Expression.fromstring("all x.(man(x) -> mortal(x))"),
    ]
    sinks = (
        (
            "Prover9",
            "prove",
            Prover9,
            lambda tool: Prover9Command(goal, assumptions, prover=tool).prove(),
            ("_prover9_bin",),
        ),
        (
            "Mace",
            "build_model",
            Mace,
            lambda tool: MaceCommand(
                goal, assumptions, model_builder=tool
            ).build_model(),
            ("_prover9_bin", "_mace4_bin"),
        ),
    )
    if os.path.exists(marker):
        os.remove(marker)
    refused = 0
    for label, sink, cls, run, held in sinks:
        for form in _relative_forms("prover9", box):
            tool = cls()
            try:
                tool.config_prover9(form)
            except LookupError:
                refused += 1
            try:
                run(tool)
            except LookupError:
                refused += 1
            except Exception:
                # anything else is only acceptable once we know nothing ran
                if not os.path.exists(marker):
                    raise
            where = f"{label}.{sink}() after config_prover9({form!r})"
            if os.path.exists(marker):
                with open(marker, encoding="utf-8") as fh:
                    ran = fh.read().split()
                return f"{where} executed the CWD decoy {ran[-1]!r}", refused
            for attr in held:
                chosen = getattr(tool, attr, None)
                if chosen is None:
                    continue
                if not os.path.isabs(chosen) or _inside(chosen, box):
                    return f"{where} held the CWD decoy {chosen!r}", refused
    return None, refused


def _sink_alone():
    """The sink phase by itself, in a CWD of recording decoys under $HOME with
    nothing reachable through the environment; (status, evidence) like the
    probe. The teeth tests use it because the probe's earlier phases would
    flip first under the same neutering."""
    home = os.path.expanduser("~")
    box = tempfile.mkdtemp(prefix=".nltk_cc5r_sink_", dir=home)
    empty = tempfile.mkdtemp(prefix=".nltk_cc5r_path_", dir=home)
    marker = os.path.join(empty, "ran")
    _plant_sinks(box, marker)
    saved_env = {var: os.environ.get(var) for var in _TOOL_ENV + ("PATH",)}
    old_cwd = os.getcwd()
    try:
        for var in _TOOL_ENV:
            os.environ.pop(var, None)
        os.environ["PATH"] = _scrubbed_path(empty)
        os.chdir(box)
        verdict, refused = _sink_phase(box, marker)
        if verdict:
            return VULNERABLE, verdict
        return (
            FIXED,
            f"{refused} refusals; the prover9/mace4 sinks never held or executed a decoy",
        )
    finally:
        os.chdir(old_cwd)
        for var, value in saved_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        shutil.rmtree(box, ignore_errors=True)
        shutil.rmtree(empty, ignore_errors=True)


@probe("GHSA-cc5r-64rf-75hg")
def _relative_binary_location():
    """Plant decoy binaries in a temporary CWD and configure each tool with every
    relative location form (including non-str, NUL-bearing and lying-string
    forms), first with no tool reachable through the environment (only the
    decoys can match: each form must be refused), then with a trusted absolute
    install configured through the tool's env var (each form must either be
    refused or resolve to that install, never to a decoy), then with the env
    var itself pointing through ``..`` at the decoy directory (the same rule),
    then with PATH pointing through ``..`` at the decoy directory and no
    location given (a PATH walk must not take the decoy either), then
    (POSIX) with the install made world-writable: java() must refuse to launch
    it even though config_java() accepted its location, and finally the
    advisory's sink: Prover9 and Mace configured with each relative form and
    then run, judged by the marker the decoys write when they execute.

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
    marker = os.path.join(legit, "ran")  # written only by the phase-6 decoys
    tools = _entry_points(legit)
    for _, _, _, plant, _ in tools:
        plant(box)
        plant(os.path.join(box, "sub"))
        plant(legit)
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
        for label, name, configure, _, _ in tools:
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
        for label, name, configure, _, _ in tools:
            expected = os.path.realpath(
                os.path.join(legit, "src", "repp")
                if name == "repp"
                else os.path.join(legit, name)
            )
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
        for label, name, configure, _, _ in tools:
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
        # phase 4: PATH itself climbs through '..' into the decoy directory; a
        # lookup with no location given walks PATH and must refuse the decoy
        # behind that absolute prefix (never resolve inside the box)
        for var in _TOOL_ENV:
            os.environ.pop(var, None)
        os.environ["PATH"] = through
        internals._java_bin = None
        for label, _, _, _, search in tools:
            try:
                resolved = search()
            except LookupError:
                refused += 1
                continue
            if resolved is None or _inside(resolved, box):
                return (
                    VULNERABLE,
                    f"{label} with PATH set to {through!r} took the decoy "
                    f"{resolved!r}",
                )
        os.environ["PATH"] = scrubbed
        # phase 5 (POSIX): an install that is absolute but that any local user
        # can rewrite (the GitHub Ubuntu image's chmod 777 JVM tree) is refused
        # when java() launches it, whatever config_java() accepted
        if os.name == "posix":
            for var in _TOOL_ENV:
                os.environ.pop(var, None)
            os.environ["JAVA_HOME"] = legit
            internals._java_bin = None
            internals.config_java()
            os.chmod(legit, 0o777)
            try:
                launched = internals.java(["Main"], stdout="pipe", stderr="pipe")
            except LookupError:
                launched = None
                refused += 1
            finally:
                os.chmod(legit, 0o700)
            if launched is not None:
                return (
                    VULNERABLE,
                    f"java() launched {internals._java_bin!r} out of the "
                    f"world-writable directory {legit!r}: {launched[0]!r}",
                )
        # phase 6: the advisory's sink. Prover9 and Mace are configured with
        # each relative form and then run; the decoys record when they execute
        for var in _TOOL_ENV:
            os.environ.pop(var, None)
        os.environ["PATH"] = scrubbed
        internals._java_bin = None
        _plant_sinks(box, marker)
        verdict, sunk = _sink_phase(box, marker)
        if verdict:
            return VULNERABLE, verdict
        refused += sunk
        return (
            FIXED,
            f"{refused} relative locations refused across {len(tools)} entry "
            "points; with an install configured every form resolved to it and "
            "never to a CWD decoy, a PATH climbing into the decoy directory was "
            "refused, a world-writable install was refused at launch, and the "
            "prover9/mace4 sinks never held or executed a decoy",
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
