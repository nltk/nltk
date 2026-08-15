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
            problems.append(f"{ghsa} ERROR {type(exc).__name__}: {exc}")
        else:
            if status == probes.VULNERABLE:
                problems.append(f"{ghsa} VULNERABLE: {evidence}")
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

    module = importlib.import_module(
        "nltk.test.unit.security_probes.ghsa_rrv8_h7p8_rx55"
    )
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
    # Guards the corpus-reader family. A reader that returns the outside-root
    # file must be caught as VULNERABLE; a security rejection is FIXED; an
    # incidental failure that never reached a guard is STATIC, not a pass.
    from nltk.test.unit.security_probes import _base

    if not _base.OUTSIDE_TARGET:
        import pytest

        pytest.skip("no outside-root target on this platform")

    leaky = lambda box: open(box.target, encoding="utf-8").read()
    assert _base.escape_probe([("leaky", leaky)])[0] == probes.VULNERABLE

    def blocked(box):
        raise PermissionError("Security Violation: outside root")

    assert _base.escape_probe([("blocked", blocked)])[0] == probes.FIXED

    def incidental(box):
        raise FileNotFoundError("no such file")

    assert _base.escape_probe([("incidental", incidental)])[0] == probes.STATIC


def test_traversal_probe_has_teeth(monkeypatch):
    import nltk.data

    # Inject a target so the control runs where /etc/passwd is absent (Windows);
    # the module imports OUTSIDE_TARGET/CANARY by value, so patch them there.
    module = importlib.import_module(
        "nltk.test.unit.security_probes.ghsa_m42h_3232_vpv3"
    )
    monkeypatch.setattr(module, "OUTSIDE_TARGET", "/etc/passwd", raising=False)
    monkeypatch.setattr(module, "OUTSIDE_CANARY", "root:", raising=False)
    monkeypatch.setattr(nltk.data, "load", lambda *a, **k: "root:x:0:0:/root")
    assert probes.PROBES["GHSA-m42h-3232-vpv3"]()[0] == probes.VULNERABLE


def test_escape_probes_reach_the_sink():
    """With enforcement off, the file-read probes must actually leak the file.

    This is the proof the corpus-reader attacks reach the guarded read rather
    than fizzling before it: flip pathsec.ENFORCE off and the ENFORCE-gated
    probes read /etc/passwd -> VULNERABLE; on, they block -> FIXED.
    """
    import nltk.pathsec as pathsec
    from nltk.test.unit.security_probes import _base

    if not _base.OUTSIDE_TARGET:
        import pytest

        pytest.skip("no outside-root target on this platform")

    original = pathsec.ENFORCE
    for ghsa in ("GHSA-x5ph-mj9p-rfr8", "GHSA-72r2-7mfr-5xr9"):
        probe = probes.PROBES[ghsa]
        try:
            pathsec.ENFORCE = False
            assert probe()[0] == probes.VULNERABLE, "%s never reached the read" % ghsa
        finally:
            pathsec.ENFORCE = original
        assert probe()[0] == probes.FIXED
