"""Offline gate over the per-advisory security probes.

Runs every probe and fails on any VULNERABLE. The negative controls break one
guard in-process and assert the probe flips to VULNERABLE, so a probe cannot
pass by never reaching the sink.
"""

import gc
import importlib
import json
import os
import pathlib
import pkgutil
import re
import shutil
import tempfile
import warnings
from collections import Counter

from nltk.test.unit import security_probes as probes
from nltk.test.unit import test_advisory_coverage_ci as covci
from nltk.test.unit.security_probes import _base


def test_each_ghsa_module_registers_exactly_one_probe():
    """Every ghsa_*.py module registers exactly one probe, and vice versa.

    No hard-coded count: discover the modules the way __init__ does and require
    a 1:1 mapping. Catches a module that failed to register (partial import), a
    forgotten @probe, a typo'd id, or a double registration -- and self-updates
    as advisories are added.
    """
    ghsa_modules = {
        f"{probes.__name__}.{module.name}"
        for module in pkgutil.iter_modules(probes.__path__)
        if module.name.startswith("ghsa_")
    }
    assert ghsa_modules, "no ghsa_* probe modules discovered -- package broken?"

    registered = Counter(fn.__module__ for fn in probes.PROBES.values())
    missing = ghsa_modules - set(registered)
    extra = set(registered) - ghsa_modules
    duplicated = {mod: n for mod, n in registered.items() if n > 1}

    assert not missing, f"ghsa_* modules with no registered probe: {sorted(missing)}"
    assert not extra, f"probes registered outside a ghsa_* module: {sorted(extra)}"
    assert not duplicated, f"modules registering more than one probe: {duplicated}"
    assert len(probes.PROBES) == len(ghsa_modules)


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


def test_model_artifact_probe_has_teeth():
    """Turn containment off and the probe must escape the sandbox.

    The payload has to genuinely reach the sink: a traversal that lands on a
    non-existent path errors out and would score FIXED no matter what the guards
    do, which is how this probe used to pass with every guard disabled.
    """
    import nltk.data
    import nltk.pathsec as pathsec

    probe = probes.PROBES["GHSA-8mgp-746c-j5xp"]
    reject, enforce = nltk.data._reject_unsafe_no_protocol, pathsec.ENFORCE
    try:
        nltk.data._reject_unsafe_no_protocol = lambda url: None
        pathsec.ENFORCE = False
        assert probe()[0] == probes.VULNERABLE
    finally:
        nltk.data._reject_unsafe_no_protocol, pathsec.ENFORCE = reject, enforce
    assert probe()[0] == probes.FIXED


def test_model_artifact_probe_covers_every_api_the_advisory_names():
    """The probe must drive the APIs the advisory lists, not only the loader.

    The advisory names six model-artifact entry points. A probe that exercises
    ``nltk.data.load`` alone reports FIXED while any one of them regresses, which
    is the failure this list pins shut.
    """
    from nltk.test.unit.security_probes import ghsa_8mgp_746c_j5xp as mod

    labels = {label for label, _ in mod._attempts(str(pathlib.Path.home()))}
    for named in (
        "TransitionParser.train",
        "TransitionParser.parse",
        "AveragedPerceptron.save",
        "AveragedPerceptron.load",
        "PerceptronTagger.save_to_json",
        "save_maxent_params",
    ):
        assert named in labels, f"advisory API {named} is not probed"


def test_perceptron_bare_open_probe_has_teeth():
    """Restore the advisory's own bug and the probe must flip to VULNERABLE.

    ``AveragedPerceptron.save``/``load`` used ``builtins.open`` on a caller path.
    Putting that back is the exact regression this probe exists to catch, so it
    must not stay FIXED through it.
    """
    import json as _json

    from nltk.tag.perceptron import AveragedPerceptron

    probe = probes.PROBES["GHSA-8mgp-746c-j5xp"]
    saved, loaded = AveragedPerceptron.save, AveragedPerceptron.load

    def bare_save(self, path):
        with open(path, "w") as fout:
            return _json.dump(self.weights, fout)

    def bare_load(self, path):
        with open(path) as fin:
            self.weights = _json.load(fin)

    try:
        AveragedPerceptron.save, AveragedPerceptron.load = bare_save, bare_load
        assert probe()[0] == probes.VULNERABLE
    finally:
        AveragedPerceptron.save, AveragedPerceptron.load = saved, loaded
    assert probe()[0] == probes.FIXED


def test_perceptron_save_to_json_validation_has_teeth():
    """Restore the tagger's pre-fix destination handling and it must escape again.

    Both of its guards go: the sandbox check on ``loc``, and (on the Windows
    branch, where there is no pinned dir_fd to write through) the sandboxed
    per-file open. Neutering only one leaves the other holding, which is the
    point of having both -- and is why this control has to remove the pair.
    """
    import builtins

    import nltk.pathsec as pathsec
    import nltk.tag.perceptron as perceptron

    probe = probes.PROBES["GHSA-8mgp-746c-j5xp"]
    validate, opener = perceptron.validate_path, perceptron.pathsec_open
    try:
        perceptron.validate_path = lambda *args, **kwargs: None
        perceptron.pathsec_open = lambda path, mode="r", **kwargs: builtins.open(
            path, mode
        )
        assert probe()[0] == probes.VULNERABLE
    finally:
        perceptron.validate_path, perceptron.pathsec_open = validate, opener
    assert probe()[0] == probes.FIXED
    assert perceptron.validate_path is pathsec.validate_path
    assert perceptron.pathsec_open is pathsec.open


def test_perceptron_load_does_not_widen_the_sandbox():
    """A caller-supplied model dir must never become an allowed root.

    ``load_from_json`` used to append a private caller directory to
    ``nltk.data.path``, which turns the containment check off for that path (and
    every later read under it) process-wide.
    """
    import nltk.data
    from nltk.tag.perceptron import PerceptronTagger

    before = list(nltk.data.path)
    outside = pathlib.Path(
        tempfile.mkdtemp(prefix=".nltk_widen_", dir=str(pathlib.Path.home()))
    )
    try:
        (outside / "averaged_perceptron_tagger_xx.weights.json").write_text("{}")
        try:
            PerceptronTagger(load=False).load_from_json(lang="xx", loc=str(outside))
        except Exception:
            pass
        assert list(nltk.data.path) == before, "caller dir was added to nltk.data.path"
    finally:
        nltk.data.path[:] = before
        shutil.rmtree(outside, ignore_errors=True)


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


def test_proxy_ssrf_probe_has_teeth():
    """Neuter the proxied-fetch refusal; the probe must report VULNERABLE.

    Guards against a false FIXED where the fetch merely fails downstream (the
    fake proxy is unreachable) instead of being refused by the guard.
    """
    import nltk.pathsec as pathsec

    probe = probes.PROBES["GHSA-6ww7-3frv-cqxh"]
    original = pathsec._reject_unpinnable_proxied_fetch
    try:
        pathsec._reject_unpinnable_proxied_fetch = lambda url: None
        assert probe()[0] == probes.VULNERABLE
    finally:
        pathsec._reject_unpinnable_proxied_fetch = original
    assert probe()[0] == probes.FIXED


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


def test_xss_probe_has_teeth():
    """Neuter html.escape in the wordnet app; the reflected <script> must be
    caught as VULNERABLE, proving the probe reaches the response sink."""
    from nltk.data import find

    try:
        find("corpora/wordnet.zip")
    except LookupError:
        import pytest

        pytest.skip("wordnet corpus unavailable")

    import nltk.app.wordnet_app as wa

    probe = probes.PROBES["GHSA-gfwx-w7gr-fvh7"]
    real = wa.html.escape
    try:
        wa.html.escape = lambda s, quote=True: s  # identity: no escaping
        assert probe()[0] == probes.VULNERABLE
    finally:
        wa.html.escape = real
    assert probe()[0] == probes.FIXED


def test_hardlink_write_probe_has_teeth():
    """Replace the hardened opener with a bare open; the symlink/hardlink write
    escape must be caught as VULNERABLE."""
    import builtins

    import nltk.pathsec as pathsec

    if os.name != "posix":
        import pytest

        pytest.skip("hardened write path is POSIX-only")

    probe = probes.PROBES["GHSA-f794-5jv7-7672"]
    real = pathsec._hardened_open
    try:
        pathsec._hardened_open = (
            lambda raw, mode, context, required_root, **kw: builtins.open(
                raw, mode, **kw
            )
        )
        assert probe()[0] == probes.VULNERABLE
    finally:
        pathsec._hardened_open = real
    assert probe()[0] == probes.FIXED


def test_shutdown_token_probe_has_teeth():
    """Bypass the per-process shutdown-token check; a token-less shutdown request
    must be caught as VULNERABLE (it would reach os._exit)."""
    import nltk.app.wordnet_app as wa

    probe = probes.PROBES["GHSA-jm6w-m3j8-898g"]
    real = wa.MyServerHandler._shutdown_authorized
    try:
        wa.MyServerHandler._shutdown_authorized = lambda self: True
        assert probe()[0] == probes.VULNERABLE
    finally:
        wa.MyServerHandler._shutdown_authorized = real
    assert probe()[0] == probes.FIXED


def test_graphviz_search_probe_has_teeth():
    """Make find_binary hand back the bare CWD name; the probe must flag the
    planted ./dot as VULNERABLE."""
    import nltk.internals as internals

    probe = probes.PROBES["GHSA-6hwm-xvph-95vm"]
    real = internals.find_binary
    try:
        internals.find_binary = lambda name, *a, **k: name  # returns the CWD hit
        assert probe()[0] == probes.VULNERABLE
    finally:
        internals.find_binary = real
    assert probe()[0] == probes.FIXED


class TestProbeDiscoveryIsolation:
    """The probe package discovers and imports only from its own directory.

    __init__ populates PROBES by iterating ``pkgutil.iter_modules(__path__)`` and
    importing each ``ghsa_*`` module by fully-qualified name. These attacks prove
    that discovery cannot be redirected to attacker-controlled code planted on
    ``sys.path`` or in the CWD -- the trust boundary is write access to the
    installed package directory itself, which is already full compromise.
    """

    @staticmethod
    def _plant(dirpath, name, marker):
        """Write a ghsa_*.py that drops ``marker`` when imported (proves exec)."""
        os.makedirs(dirpath, exist_ok=True)
        (pathlib.Path(dirpath) / f"{name}.py").write_text(
            f"import pathlib; pathlib.Path({str(marker)!r}).write_text('x')\n"
        )

    def test_attacker_module_on_syspath_is_not_imported(self, tmp_path, monkeypatch):
        marker = tmp_path / "pwned"
        attacker = tmp_path / "attacker_dir"
        self._plant(str(attacker), "ghsa_attacker_aaaa_bbbb", marker)
        monkeypatch.syspath_prepend(str(attacker))

        importlib.reload(probes)

        assert not marker.exists(), "a ghsa_* module on sys.path was executed"
        assert "GHSA-attacker-aaaa-bbbb" not in probes.PROBES

    def test_cwd_planted_module_is_not_imported(self, tmp_path, monkeypatch):
        marker = tmp_path / "pwned"
        self._plant(str(tmp_path), "ghsa_cwd_cccc_dddd", marker)
        self._plant(str(tmp_path), "advisories", marker)  # the old bare-name vector
        monkeypatch.chdir(tmp_path)

        importlib.reload(probes)

        assert not marker.exists(), "a ghsa_*/advisories module in the CWD was executed"

    def test_discovery_scans_only_the_package_directory(self):
        discovered = {m.name for m in pkgutil.iter_modules(probes.__path__)}
        on_disk = {p.stem for p in pathlib.Path(probes.__path__[0]).glob("*.py")}
        assert (
            discovered <= on_disk
        ), "discovery listed a module outside the package dir"

    def test_all_imports_are_qualified_under_the_package(self, monkeypatch):
        issued = []
        real_import = importlib.import_module

        def spy(name, *args, **kwargs):
            issued.append(name)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", spy)
        importlib.reload(probes)

        prefix = probes.__name__ + "."
        unqualified = [n for n in issued if not n.startswith(prefix)]
        assert (
            not unqualified
        ), f"imports not under the package namespace: {unqualified}"


class TestReadSource:
    """``_base.read_source`` reads a module's source without leaking the FD.

    It used a bare ``open(module.__file__).read()`` that left the descriptor for
    the garbage collector. ``Path.read_text`` closes it eagerly. (The reader only
    ever takes hardcoded ``nltk.*`` literals from the probes -- no untrusted
    input reaches it -- so the only defect to fix is the leak.)
    """

    def test_reads_real_nltk_source(self):
        assert "class Downloader" in _base.read_source("nltk.downloader")

    def test_no_descriptor_leak_under_repeated_reads(self):
        # A bare open().read() leaves the file object for the GC to close, which
        # emits a ResourceWarning. Promote it to an error and force collection:
        # Path.read_text closes eagerly, so the loop stays silent.
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            for _ in range(200):
                _base.read_source("nltk.downloader")
            gc.collect()


class _FakeResp:
    """Minimal stand-in for a urllib response: a body plus a Link header."""

    def __init__(self, payload, link=None):
        self._body = json.dumps(payload).encode()
        self.headers = {"Link": link} if link else {}

    def read(self, size=-1):
        return self._body if size < 0 else self._body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _serve(pages, monkeypatch):
    """Route urlopen to ``pages`` (url -> _FakeResp), offline."""

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        if url not in pages:
            raise AssertionError(f"unexpected url requested: {url}")
        return pages[url]

    monkeypatch.setattr(covci.urllib.request, "urlopen", fake_urlopen)


class TestAdvisoryPagination:
    """The coverage fetch must not silently stop at GitHub's 100-per-page cap.

    A single un-paginated request drops advisories past 100, so a real coverage
    gap in that tail would pass unnoticed. These offline tests drive the Link
    header logic with a fake urlopen -- no network.
    """

    def test_next_url_parses_on_origin_rel_next(self):
        nxt = covci._API_ORIGIN + "?per_page=100&page=2"
        last = covci._API_ORIGIN + "?per_page=100&page=9"
        header = f'<{nxt}>; rel="next", <{last}>; rel="last"'
        assert covci._next_url(header) == nxt

    def test_next_url_absent_or_off_origin_is_none(self):
        last = covci._API_ORIGIN + "?per_page=100&page=9"
        assert covci._next_url(f'<{last}>; rel="last"') is None  # no rel=next
        assert covci._next_url('<https://evil.example/x?page=2>; rel="next"') is None
        assert covci._next_url(None) is None
        assert covci._next_url("") is None

    def test_single_page_unchanged(self, monkeypatch):
        _serve({covci._API: _FakeResp([{"ghsa_id": "A"}])}, monkeypatch)
        assert [a["ghsa_id"] for a in covci._fetch_advisories()] == ["A"]

    def test_follows_pagination_and_concatenates(self, monkeypatch):
        page2 = covci._API_ORIGIN + "?per_page=100&page=2"
        _serve(
            {
                covci._API: _FakeResp(
                    [{"ghsa_id": "A"}], link=f'<{page2}>; rel="next"'
                ),
                page2: _FakeResp([{"ghsa_id": "B"}]),
            },
            monkeypatch,
        )
        assert [a["ghsa_id"] for a in covci._fetch_advisories()] == ["A", "B"]

    def test_off_origin_next_is_not_followed(self, monkeypatch):
        # An off-origin next link stops pagination -- the evil URL is never
        # fetched (_serve raises on any unexpected url), so we get page 1 only.
        evil = "https://evil.example.com/repos/nltk/nltk?page=2"
        _serve(
            {covci._API: _FakeResp([{"ghsa_id": "A"}], link=f'<{evil}>; rel="next"')},
            monkeypatch,
        )
        assert [a["ghsa_id"] for a in covci._fetch_advisories()] == ["A"]

    def test_page_cap_returns_none_not_partial(self, monkeypatch):
        # Every page advertises another on-origin next -> the cap is hit. The
        # list is not provably complete, so skip (None), never under-report.
        forever = covci._API_ORIGIN + "?per_page=100&page=2"

        def fake_urlopen(request, timeout=None):
            return _FakeResp([{"ghsa_id": "X"}], link=f'<{forever}>; rel="next"')

        monkeypatch.setattr(covci.urllib.request, "urlopen", fake_urlopen)
        assert covci._fetch_advisories() is None

    def test_fetch_error_returns_none(self, monkeypatch):
        def boom(request, timeout=None):
            raise OSError("network down")

        monkeypatch.setattr(covci.urllib.request, "urlopen", boom)
        assert covci._fetch_advisories() is None

    def test_oversized_body_returns_none(self, monkeypatch):
        # A body past the byte cap is refused (json never buffers it whole),
        # so the fetch is not trusted -> None -> skip.
        monkeypatch.setattr(covci, "_MAX_BYTES", 8)
        _serve({covci._API: _FakeResp([{"ghsa_id": "AAAAAAAAAA"}])}, monkeypatch)
        assert covci._fetch_advisories() is None


def test_dns_rebinding_probe_has_teeth():
    """Neuter the SSRF IP filter; the rebound link-local connect must be caught as
    VULNERABLE. The _resolve_hostname lru_cache is cleared so the restored run does
    not false-fail on stale sequencing."""
    import nltk.pathsec as pathsec

    probe = probes.PROBES["GHSA-3gqm-fcw5-w839"]
    real = pathsec._ip_is_forbidden
    try:
        pathsec._resolve_hostname.cache_clear()
        pathsec._ip_is_forbidden = lambda ip: False  # nothing is forbidden
        assert probe()[0] == probes.VULNERABLE
    finally:
        pathsec._ip_is_forbidden = real
        pathsec._resolve_hostname.cache_clear()
    assert probe()[0] == probes.FIXED


def test_ssrf_ip_filter_probe_has_teeth():
    """Allow every IP; all the loopback/metadata/mapped targets must pass the filter
    and the probe must flip to VULNERABLE."""
    import nltk.pathsec as pathsec

    probe = probes.PROBES["GHSA-qvv7-cg9c-w4x3"]
    real = pathsec._ip_is_forbidden
    try:
        pathsec._ip_is_forbidden = lambda ip: False
        assert probe()[0] == probes.VULNERABLE
    finally:
        pathsec._ip_is_forbidden = real
    assert probe()[0] == probes.FIXED


def test_dotted_name_probe_has_teeth():
    """Restore stock find_class (which walks dotted names at proto>=4); the dotted
    global must then be reconstructed and the probe flip to VULNERABLE."""
    import pickle

    from nltk.picklesec import AllowlistUnpickler

    probe = probes.PROBES["GHSA-4489-j4f3-2g8q"]
    real = AllowlistUnpickler.find_class
    try:
        AllowlistUnpickler.find_class = pickle.Unpickler.find_class
        assert probe()[0] == probes.VULNERABLE
    finally:
        AllowlistUnpickler.find_class = real
    assert probe()[0] == probes.FIXED


def test_pickle_denylist_fires_under_broad_allow():
    """Defense in depth: os.system is refused by the module denylist even when a
    caller mistakenly names 'os' in allowed_modules (not merely by an empty allow)."""
    import io
    import pickle

    import pytest

    from nltk.picklesec import allowlisted_pickle_load

    payload = b"cos\nsystem\n(t R."  # GLOBAL os.system, empty-tuple REDUCE
    with pytest.raises(pickle.UnpicklingError, match="denied module"):
        allowlisted_pickle_load(io.BytesIO(payload), allowed_modules=("os",))


def test_cyclic_index_probe_reports_a_hang_as_vulnerable():
    """The advisory's regression manifests as an infinite loop, i.e. a subprocess
    that never returns. Simulate that: a hanging cyclic run with a healthy acyclic
    control must be VULNERABLE, and only a control that also hangs is STATIC."""
    module = importlib.import_module(
        "nltk.test.unit.security_probes.ghsa_pcm8_fqjx_rvx8"
    )
    probe = probes.PROBES["GHSA-pcm8-fqjx-rvx8"]
    real = module._resolve
    try:
        module._resolve = lambda shape, timeout=30: (
            ("ok", "p1") if shape == "acyclic" else ("hang", "timed out")
        )
        assert probe()[0] == probes.VULNERABLE
        # an overloaded host (control hangs too) must NOT be called a regression
        module._resolve = lambda shape, timeout=30: ("hang", "timed out")
        assert probe()[0] == probes.STATIC
    finally:
        module._resolve = real
    assert probe()[0] == probes.FIXED


def test_jvm_option_filter_probe_has_teeth(monkeypatch):
    """Neuter only the options filter; java()'s classpath and cmd guards stay live,
    so a flip to VULNERABLE proves the probe scores this filter and not a neighbour."""
    from nltk import internals

    probe = probes.PROBES["GHSA-m4rf-3fr8-xwx3"]
    assert probe()[0] == probes.FIXED

    monkeypatch.setattr(internals, "_validate_java_options", lambda opts: None)
    status, evidence = probe()
    assert status == probes.VULNERABLE, evidence
    # proof of injection is the command line that was about to run, not a count
    assert "-Xbootclasspath" in evidence

    monkeypatch.undo()
    assert probe()[0] == probes.FIXED
