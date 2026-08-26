"""GHSA-8mgp-746c-j5xp [high] -- Model-artifact APIs bypass pathsec and touch files outside allowed roots"""

import contextlib
import io
import json
import os
import pathlib
import shutil
import tempfile

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe

#: The canary an escaping read must hand back, and an escaping write must leave
#: on disk outside the allowed roots.
CANARY = "GHSA-8MGP-CANARY"

#: ``lang`` for the throwaway tagger, so a probe run can never collide with a
#: real ``averaged_perceptron_tagger_eng`` model.
LANG = "probe8mgp"


@contextlib.contextmanager
def _outside_dir():
    """A writable directory that is genuinely OUTSIDE every allowed pathsec root.

    Not ``tempfile.mkdtemp()``: a *private* per-user system temp dir is itself an
    allowed root on macOS/Windows, so an attack target staged there would be
    correctly permitted and the probe would prove nothing. ``$HOME`` is not a
    root (only ``~/nltk_data`` is), so a directory made there is a real escape
    target. Yields ``None`` when it turns out to be inside a root anyway (an
    operator may have put ``$HOME`` on ``nltk.data.path``), so the caller can
    report STATIC instead of a bogus result.

    Containment is compared against the allowed roots directly, never by calling
    ``validate_path``: that answers "would this be refused", which is False once
    ``ENFORCE`` is off, so the negative control would lose its escape target at
    exactly the moment it needs one.
    """
    from nltk import pathsec

    path = pathlib.Path(
        tempfile.mkdtemp(prefix=".nltk_probe8mgp_", dir=str(pathlib.Path.home()))
    )
    try:
        resolved = path.resolve()
        inside = any(
            resolved == root or resolved.is_relative_to(root)
            for root in pathsec._get_allowed_roots()
        )
        yield None if inside else path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _weights_files(loc, lang):
    """Write the three json files ``PerceptronTagger.load_from_json`` reads.

    Written with the stdlib writer on purpose: this is the *attacker's* plant,
    staged outside the sandbox before the attack runs, not NLTK doing I/O.
    """
    payload = {
        "weights": {CANARY: {"NN": 1.0}},
        "tagdict": {},
        "classes": ["NN"],
    }
    os.makedirs(loc, mode=0o700, exist_ok=True)
    for attr, value in payload.items():
        target = os.path.join(loc, f"averaged_perceptron_tagger_{lang}.{attr}.json")
        pathlib.Path(target).write_text(json.dumps(value), encoding="utf-8")


def _attempts(outside):
    """(label, callable) for every API the advisory names, read and write.

    Each callable must either be security-refused or leave evidence: a read
    returns something containing ``CANARY``, a write returns the paths it
    created outside the root. Returning a falsy value means "ran, escaped
    nothing".
    """
    from nltk.parse.transitionparser import TransitionParser
    from nltk.tag.perceptron import AveragedPerceptron, PerceptronTagger

    def _tagger():
        tagger = PerceptronTagger(load=False)
        tagger.model.weights = {CANARY: {"NN": 1.0}}
        tagger.tagdict = {}
        tagger.classes = {"NN"}
        return tagger

    def perceptron_load():
        target = os.path.join(outside, "weights.json")
        pathlib.Path(target).write_text(
            json.dumps({CANARY: {"NN": 1.0}}), encoding="utf-8"
        )
        model = AveragedPerceptron()
        model.load(target)
        return repr(model.weights)

    def perceptron_save():
        target = os.path.join(outside, "saved.json")
        AveragedPerceptron({CANARY: {"NN": 1.0}}).save(target)
        return pathlib.Path(target).read_text(encoding="utf-8")

    def perceptron_save_symlink():
        """A symlink inside a root pointing out of it must not carry the write."""
        victim = os.path.join(outside, "victim.json")
        pathlib.Path(victim).write_text("untouched", encoding="utf-8")
        root = tempfile.mkdtemp(prefix="nltk_probe8mgp_root_")
        link = os.path.join(root, "link.json")
        try:
            os.symlink(victim, link)
        except OSError:
            shutil.rmtree(root, ignore_errors=True)
            return None
        try:
            AveragedPerceptron({CANARY: {"NN": 1.0}}).save(link)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        return pathlib.Path(victim).read_text(encoding="utf-8")

    def tagger_save_to_json():
        loc = os.path.join(outside, "tagger_save")
        _tagger().save_to_json(lang=LANG, loc=loc)
        return CANARY + " " + repr(sorted(os.listdir(loc)))

    def tagger_load_from_json():
        loc = os.path.join(outside, "tagger_load")
        _weights_files(loc, LANG)
        tagger = PerceptronTagger(load=False)
        tagger.load_from_json(lang=LANG, loc=loc)
        return repr(tagger.model.weights)

    def tagger_ctor_loc():
        loc = os.path.join(outside, "tagger_ctor")
        _weights_files(loc, LANG)
        return repr(PerceptronTagger(load=True, lang=LANG, loc=loc).model.weights)

    def transition_parse():
        target = os.path.join(outside, "model.pickle")
        pathlib.Path(target).write_bytes(b"\x80\x04N.")
        TransitionParser("arc-standard").parse([], target)
        return CANARY + " read " + target

    def maxent_save():
        import numpy

        from nltk.classify.maxent import save_maxent_params

        loc = os.path.join(outside, "maxent_out")
        save_maxent_params(
            numpy.array([1.0]), {("a", "b"): 0}, ["L"], {"alwayson": 0}, tab_dir=loc
        )
        return CANARY + " " + repr(sorted(os.listdir(loc)))

    def transition_train():
        target = os.path.join(outside, "trained.pickle")
        TransitionParser("arc-standard").train([], target, verbose=False)
        return CANARY + " wrote " + target

    def crf_train():
        """A native (pycrfsuite) writer given a caller path."""
        from nltk.tag.crf import CRFTagger

        target = os.path.join(outside, "model.crf")
        CRFTagger().train(
            [[("the", "DT"), ("dog", "NN")], [("a", "DT"), ("cat", "NN")]], target
        )
        return CANARY + " wrote " + target if os.path.exists(target) else None

    def crf_load():
        from nltk.tag.crf import CRFTagger

        target = os.path.join(outside, "planted.crf")
        pathlib.Path(target).write_bytes(b"not-a-real-model")
        CRFTagger().set_model_file(target)
        return CANARY + " opened " + target

    def data_load_urls():
        """The generic loader underneath the model APIs, in several path forms."""
        import nltk.data

        target = os.path.join(outside, "resource.txt")
        pathlib.Path(target).write_text(CANARY, encoding="utf-8")
        forms = [
            target,
            "nltk:" + target,
            "file://" + target,
            target + "\x00.cfg",
            os.path.join(tempfile.gettempdir(), "..", "..", "etc", "passwd"),
            "/etc/passwd",
        ]
        seen = []
        for form in forms:
            with contextlib.suppress(Exception):
                # cache=False: nltk.data.load memoises by URL, so a read that
                # succeeded in an earlier run would be replayed here and
                # reported as a leak that is not there.
                seen.append(str(nltk.data.load(form, format="raw", cache=False)))
        return " ".join(seen)

    return [
        ("AveragedPerceptron.load", perceptron_load),
        ("AveragedPerceptron.save", perceptron_save),
        ("AveragedPerceptron.save/symlink", perceptron_save_symlink),
        ("PerceptronTagger.save_to_json", tagger_save_to_json),
        ("PerceptronTagger.load_from_json", tagger_load_from_json),
        ("PerceptronTagger(loc=...)", tagger_ctor_loc),
        ("TransitionParser.parse", transition_parse),
        ("TransitionParser.train", transition_train),
        ("save_maxent_params", maxent_save),
        ("CRFTagger.train", crf_train),
        ("CRFTagger.set_model_file", crf_load),
        ("nltk.data.load", data_load_urls),
    ]


@probe("GHSA-8mgp-746c-j5xp")
def _model_artifact_apis():
    """Every model-artifact API the advisory names must refuse an outside-root path.

    The advisory is about ``TransitionParser.train``/``parse``,
    ``AveragedPerceptron.save``/``load``, ``PerceptronTagger.save_to_json`` and
    ``save_maxent_params`` treating a caller path as a plain filename, so the
    probe drives those APIs, not only the generic loader underneath them: a
    regression in any one of them is invisible to a probe that exercises
    ``nltk.data.load`` alone.

    A leak is evidence, not merely "the call returned": a read must hand back the
    canary and a write must land outside the allowed roots. A refusal only counts
    when it is security-marked, so an incidental ImportError/FileNotFoundError is
    never scored as a defence.
    """
    with _outside_dir() as outside:
        if outside is None:
            return STATIC, "$HOME is inside an allowed root here; no escape target"
        reached, notes = False, []
        for label, run in _attempts(str(outside)):
            try:
                # Several of these APIs print progress; a probe reports through
                # its return value, so keep the harness output clean.
                with contextlib.redirect_stdout(io.StringIO()):
                    result = run()
            except Exception as exc:
                if is_security_rejection(exc):
                    reached = True
                    notes.append(f"{label}=blocked")
                else:
                    notes.append(f"{label}=unreached({type(exc).__name__})")
                continue
            if result and CANARY in str(result):
                return VULNERABLE, f"{label} escaped the sandbox: {str(result)[:120]}"
            notes.append(f"{label}=no-escape")
        detail = "; ".join(notes)
        if reached:
            return FIXED, detail
        return STATIC, "attack never reached a security check: " + detail
