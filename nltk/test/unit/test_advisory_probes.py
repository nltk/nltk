"""Offline gate over the per-advisory security probes.

Runs every probe and fails on any VULNERABLE. The negative controls break one
guard in-process and assert the probe flips to VULNERABLE, so a probe cannot
pass by never reaching the sink.
"""

import importlib
import re

from nltk.test.unit import security_probes as probes


def test_probes_are_registered():
    assert len(probes.PROBES) >= 37


def test_no_advisory_is_vulnerable():
    problems = []
    for ghsa in sorted(probes.PROBES):
        try:
            status, evidence = probes.PROBES[ghsa]()
        except Exception as exc:  # a crashing probe is not a pass
            problems.append("%s ERROR %s: %s" % (ghsa, type(exc).__name__, exc))
        else:
            if status == probes.VULNERABLE:
                problems.append("%s VULNERABLE: %s" % (ghsa, evidence))
    assert not problems, "\n  ".join([""] + problems)


def test_probe_ids_are_wellformed():
    bad = [g for g in probes.PROBES if not re.fullmatch(r"GHSA(-[a-z0-9]{4}){3}", g)]
    assert not bad, bad


# --- negative controls: prove the probes have teeth ---------------------------


def test_pathsec_enforce_probe_has_teeth():
    import nltk.pathsec as pathsec

    probe = probes.PROBES["GHSA-p3m8-78j2-g5p3"]
    original = pathsec.ENFORCE
    try:
        pathsec.ENFORCE = False
        assert probe()[0] == probes.VULNERABLE
    finally:
        pathsec.ENFORCE = original
    assert probe()[0] == probes.FIXED


def test_pickle_allowlist_probe_has_teeth():
    from nltk.picklesec import AllowlistUnpickler

    probe = probes.PROBES["GHSA-x99w-6fgc-pmfw"]
    original = AllowlistUnpickler.find_class
    try:
        AllowlistUnpickler.find_class = lambda self, module, name: __import__(
            module, fromlist=[name.split(".")[0]]
        )
        assert probe()[0] == probes.VULNERABLE
    finally:
        AllowlistUnpickler.find_class = original
    assert probe()[0] == probes.FIXED


def test_redos_probe_has_teeth():
    # A real (a+)+$ blow-up would run for minutes (the probe times, does not
    # interrupt), so sleep just past a lowered budget instead.
    import time

    import nltk.text as text_module

    module = importlib.import_module("nltk.test.unit.security_probes.ghsa_rrv8_h7p8_rx55")
    probe = probes.PROBES["GHSA-rrv8-h7p8-rx55"]
    original_findall, original_budget = text_module.Text.findall, module.DOS_BUDGET
    try:
        module.DOS_BUDGET = 0.3
        text_module.Text.findall = lambda self, regexp: time.sleep(0.6)
        assert probe()[0] == probes.VULNERABLE
    finally:
        text_module.Text.findall = original_findall
        module.DOS_BUDGET = original_budget
    assert probe()[0] == probes.FIXED


def test_escape_probe_has_teeth():
    # Guards the corpus-reader family: a reader that reads the outside-root file
    # must be caught, so a no-leak result cannot come from failing at
    # construction instead of defending the read.
    from nltk.test.unit.security_probes._base import escape_probe

    leaky = lambda box: open(box.secret, encoding="utf-8").read()
    assert escape_probe([("leaky", leaky)])[0] == probes.VULNERABLE

    def guarded(box):
        raise PermissionError("outside root")

    assert escape_probe([("guarded", guarded)])[0] == probes.FIXED


def test_traversal_probe_has_teeth(monkeypatch):
    import nltk.data

    probe = probes.PROBES["GHSA-m42h-3232-vpv3"]
    monkeypatch.setattr(nltk.data, "load", lambda *a, **k: "root:x:0:0:/root")
    assert probe()[0] == probes.VULNERABLE
