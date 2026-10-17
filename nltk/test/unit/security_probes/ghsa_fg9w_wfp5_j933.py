"""GHSA-fg9w-wfp5-j933 [medium]: BllipParser hands caller model paths to the
bllipparser C extension without a pathsec check (CWE-22 / CWE-73 / CWE-400)."""

import os
import tempfile

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe


class _SpyExtension:
    """Records the paths the bllipparser C extension would open natively."""

    last = None

    def __init__(self):
        type(self).last = self
        self.parser_model = None
        self.reranker = None

    def load_parser_model(self, model_dir, **kw):
        self.parser_model = model_dir

    def load_reranker_model(self, features_filename, weights_filename, **kw):
        self.reranker = (features_filename, weights_filename)


def _unified_shim(model_dir):
    parser = os.path.join(model_dir, "parser")
    return (parser if os.path.exists(parser) else model_dir, None, None)


def _malt_learn_mode_model():
    """Second-pass sibling sink: ``MaltParser.generate_malt_command`` in ``learn``
    mode builds the ``-c`` the JVM WRITES the ``.mco`` to. An outside-root model
    must be refused while the command is built, before any JVM runs. No tool is
    needed: the command builder is a pure function driven on a fabricated
    instance, so this is deterministic on every platform."""
    import nltk.parse.malt as malt

    outside = tempfile.mkdtemp(prefix=".nltk_fg9w_malt_", dir=os.path.expanduser("~"))
    try:
        mp = malt.MaltParser.__new__(malt.MaltParser)
        mp.model = os.path.join(outside, "evil.mco")
        mp._working_dir = outside
        try:
            cmd = mp.generate_malt_command(
                os.path.join(outside, "train.conll"), mode="learn"
            )
        except Exception as exc:
            if is_security_rejection(exc):
                return FIXED, "outside-root learn-mode model refused before the JVM"
            return STATIC, f"non-security failure {type(exc).__name__}: {exc}"
        if any(mp.model in str(tok) or "evil.mco" in str(tok) for tok in cmd):
            return VULNERABLE, f"learn-mode command built with outside model {cmd!r}"
        return FIXED, "no outside-root model reached the command"
    finally:
        import shutil

        shutil.rmtree(outside, ignore_errors=True)


def _repp_config_dir_with_a_planted_link():
    """Third-pass sibling sink: a directory an external tool READS natively
    (REPP's config tree, like SENNA's data dir and C&C's models). A symlink
    planted inside it must be refused while the command is built, before any
    binary runs; no tool is needed, the command builder is a pure function."""
    import shutil

    from nltk.tokenize import repp as repp_mod

    if not hasattr(os, "symlink"):
        return STATIC, "no symlinks on this platform"
    base = tempfile.mkdtemp(prefix=".nltk_fg9w_repp_", dir=os.path.expanduser("~"))
    try:
        tree = os.path.join(base, "repp")
        os.makedirs(os.path.join(tree, "src"))
        os.makedirs(os.path.join(tree, "erg"))
        for name in ("src/repp", "erg/repp.set"):
            with open(
                os.path.join(tree, name), "wb"
            ):  # sandboxed-open ok: probe fixture under ~
                pass
        victim = os.path.join(base, "victim.set")
        with open(victim, "w") as handle:  # sandboxed-open ok: probe fixture under ~
            handle.write("outside")
        try:
            os.symlink(victim, os.path.join(tree, "erg", "planted.set"))
        except OSError as exc:
            return STATIC, f"cannot plant a symlink here: {exc}"
        tokenizer = repp_mod.ReppTokenizer.__new__(repp_mod.ReppTokenizer)
        tokenizer.repp_dir = tree
        tokenizer.encoding = "utf8"
        try:
            cmd = tokenizer.generate_repp_command(os.path.join(base, "in.txt"))
        except Exception as exc:
            if is_security_rejection(exc):
                return (
                    FIXED,
                    "config tree with a planted symlink refused before the binary",
                )
            return STATIC, f"non-security failure {type(exc).__name__}: {exc}"
        if any(tree in str(tok) for tok in cmd):
            return (
                VULNERABLE,
                f"command built over a tree holding a planted link {cmd!r}",
            )
        return FIXED, "no tampered tree reached the command"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _senna_data_dir_with_a_planted_link():
    """Third-pass sibling sink: SENNA's ``-path`` data directory, read natively
    by the binary. A symlink planted inside it must be refused before the
    spawn; the spawn is intercepted so no binary is needed, only a file with
    the binary's name so the wrapper constructs."""
    import shutil
    from platform import architecture, system

    from nltk.classify import senna as senna_mod

    if not hasattr(os, "symlink"):
        return STATIC, "no symlinks on this platform"
    base = tempfile.mkdtemp(prefix=".nltk_fg9w_senna_", dir=os.path.expanduser("~"))
    saved_spawn = senna_mod.spawn_trusted
    seen = []

    def fake_spawn(executable, args, **kwargs):
        seen.append(list(args))
        raise RuntimeError("probe: spawn intercepted")

    try:
        tool = os.path.join(base, "senna")
        os.mkdir(tool)
        os_name = system()
        if os_name == "Linux":
            name = "senna-linux64" if architecture()[0] == "64bit" else "senna-linux32"
        elif os_name == "Windows":
            name = "senna-win32.exe"
        elif os_name == "Darwin":
            name = "senna-osx"
        else:
            name = "senna"
        binary = os.path.join(tool, name)
        with open(binary, "wb"):  # sandboxed-open ok: probe fixture under ~
            pass
        os.chmod(binary, 0o755)
        victim = os.path.join(base, "victim.dat")
        with open(victim, "w") as handle:  # sandboxed-open ok: probe fixture under ~
            handle.write("outside")
        try:
            os.symlink(victim, os.path.join(tool, "planted.dat"))
        except OSError as exc:
            return STATIC, f"cannot plant a symlink here: {exc}"
        senna_mod.spawn_trusted = fake_spawn
        try:
            senna_mod.Senna(tool, ["pos"]).tag_sents([["the"]])
        except Exception as exc:
            if is_security_rejection(exc):
                if seen:
                    return VULNERABLE, "refused but the spawn got the data dir"
                return FIXED, "data dir with a planted symlink refused before the spawn"
            if seen:
                return VULNERABLE, f"spawned with the tampered data dir {seen[0]!r}"
            return STATIC, f"non-security failure {type(exc).__name__}: {exc}"
        if seen:
            return VULNERABLE, f"spawned with the tampered data dir {seen[0]!r}"
        return FIXED, "no tampered data dir reached the spawn"
    finally:
        senna_mod.spawn_trusted = saved_spawn
        shutil.rmtree(base, ignore_errors=True)


def _candc_models_with_a_planted_link():
    """Third-pass sibling sink: the C&C ``--models`` tree Boxer hands the
    parser, read natively. A symlink planted inside it must be refused before
    the call; the call is intercepted so no binary is needed."""
    import shutil

    from nltk.sem import boxer as boxer_mod

    if not hasattr(os, "symlink"):
        return STATIC, "no symlinks on this platform"
    base = tempfile.mkdtemp(prefix=".nltk_fg9w_candc_", dir=os.path.expanduser("~"))
    saved_call = boxer_mod.Boxer._call
    saved_env = os.environ.pop("CANDC", None)
    seen = []

    def fake_call(self, input_str, binary, args, verbose=False):
        seen.append(list(args))
        raise RuntimeError("probe: call intercepted")

    try:
        tool = os.path.join(base, "candc")
        os.makedirs(os.path.join(tool, "bin"))
        os.makedirs(os.path.join(tool, "models", "boxer"))
        for name in ("candc", "boxer"):
            binary = os.path.join(tool, "bin", name)
            with open(binary, "wb"):  # sandboxed-open ok: probe fixture under ~
                pass
            os.chmod(binary, 0o755)
        with open(
            os.path.join(tool, "models", "boxer", "super"), "w"
        ):  # sandboxed-open ok: probe fixture under ~
            pass
        victim = os.path.join(base, "victim.dat")
        with open(victim, "w") as handle:  # sandboxed-open ok: probe fixture under ~
            handle.write("outside")
        try:
            os.symlink(victim, os.path.join(tool, "models", "boxer", "planted"))
        except OSError as exc:
            return STATIC, f"cannot plant a symlink here: {exc}"
        boxer_mod.Boxer._call = fake_call
        try:
            boxer_mod.Boxer(bin_dir=os.path.join(tool, "bin"))._call_candc(
                [["the dog barks ."]], ["1"], question=False
            )
        except Exception as exc:
            if is_security_rejection(exc):
                if seen:
                    return VULNERABLE, "refused but the call got the models tree"
                return (
                    FIXED,
                    "models tree with a planted symlink refused before the call",
                )
            if seen:
                return VULNERABLE, f"called with the tampered models tree {seen[0]!r}"
            return STATIC, f"non-security failure {type(exc).__name__}: {exc}"
        if seen:
            return VULNERABLE, f"called with the tampered models tree {seen[0]!r}"
        return FIXED, "no tampered models tree reached the call"
    finally:
        boxer_mod.Boxer._call = saved_call
        if saved_env is not None:
            os.environ["CANDC"] = saved_env
        shutil.rmtree(base, ignore_errors=True)


@probe("GHSA-fg9w-wfp5-j933")
def _bllip_model_paths():
    """``BllipParser(parser_model=<outside-root>)`` must be refused before the
    extension opens the file; the sibling MaltParser learn-mode model sink
    (second pass) must be refused before its JVM writes the ``.mco``.

    The real extension rarely builds, so a spy stands in for it and records what
    ``load_parser_model`` would have opened: the guard being present means an
    outside-root model is security-refused and the spy never sees it (FIXED);
    with the guard removed the spy records the escaping path (VULNERABLE). An
    out-of-root *directory* is the attack target because ``parser_model`` names a
    model directory; the advisory's ``/etc/passwd`` file form is refused the same
    way (not a directory AND outside the roots). The verdict is the combined
    worst case over both sinks.
    """
    import nltk.parse.bllip as bllip

    outside = tempfile.mkdtemp(
        prefix=".nltk_fg9w_outside_", dir=os.path.expanduser("~")
    )
    model = os.path.join(outside, "parser")
    os.makedirs(model, exist_ok=True)
    with open(os.path.join(model, "pSgT.txt"), "wb") as handle:
        handle.write(b"model data")

    _ABSENT = object()
    saved = {
        name: getattr(bllip, name, _ABSENT)
        for name in (
            "RerankingParser",
            "get_unified_model_parameters",
            "_ensure_bllip_import_or_error",
        )
    }
    _SpyExtension.last = None
    bllip.RerankingParser = _SpyExtension
    bllip.get_unified_model_parameters = _unified_shim
    bllip._ensure_bllip_import_or_error = lambda: None
    try:
        try:
            bllip.BllipParser(parser_model=model)
        except Exception as exc:
            if is_security_rejection(exc):
                if _SpyExtension.last is not None and _SpyExtension.last.parser_model:
                    bllip_result = (
                        VULNERABLE,
                        "refused but the extension got the path",
                    )
                else:
                    bllip_result = (
                        FIXED,
                        "outside-root parser_model refused before the extension",
                    )
            else:
                bllip_result = (STATIC, f"non-security failure {type(exc).__name__}")
        else:
            if (
                _SpyExtension.last is not None
                and _SpyExtension.last.parser_model == model
            ):
                bllip_result = (VULNERABLE, f"extension opened out-of-root {model!r}")
            else:
                bllip_result = (FIXED, "no outside-root path reached the extension")
    finally:
        for name, value in saved.items():
            if value is _ABSENT:
                if hasattr(bllip, name):
                    delattr(bllip, name)
            else:
                setattr(bllip, name, value)
        import shutil

        shutil.rmtree(outside, ignore_errors=True)

    malt_result = _malt_learn_mode_model()
    repp_result = _repp_config_dir_with_a_planted_link()
    senna_result = _senna_data_dir_with_a_planted_link()
    candc_result = _candc_models_with_a_planted_link()
    results = [bllip_result, malt_result, repp_result, senna_result, candc_result]
    for status, detail in results:
        if status == VULNERABLE:
            return VULNERABLE, detail
    if all(status == STATIC for status, _ in results):
        return STATIC, bllip_result[1]
    detail = "; ".join(f"{s.lower()}: {d}" for s, d in results)
    return FIXED, detail
