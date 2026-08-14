# Advisory verification probes

One `ghsa_<id>.py` module per published NLTK security advisory. Each runs the
attack the advisory describes and reports what the tree does now — an advisory
says a version *was* vulnerable; a probe checks the tree *is* fixed, on every
commit, and a silent regression looks exactly like a shipped fix without one.

    python -m nltk.test.unit.security_probes    # print the report

## Tests

- `test_advisory_probes.py` — offline, every run. Runs all probes (none may be
  VULNERABLE) plus negative controls that break each guard in-process and
  assert the probe flips to VULNERABLE, so a probe cannot pass by never
  reaching the sink.
- `test_advisory_coverage_ci.py` — CI only (`NLTK_ADVISORY_CI=1`). Pulls the
  live published list from GitHub and fails if a new advisory has no probe.

## Statuses

`FIXED` attack ran, tree defended · `VULNERABLE` attack worked · `STATIC` guard
confirmed in source but attack not executed (needs a network peer / real
download / running JVM) · `BENIGN` audited, never exploitable, pinned.

`STATIC` is distinct from `FIXED` on purpose: a grep is not an exploit attempt.

## Result on develop

38 probes: 31 FIXED, 7 STATIC, 0 VULNERABLE. The three top-severity claims all
describe states that no longer exist — the pickle allowlist rejects dangerous
globals under an allowlisted parent (GHSA-x99w), `TransitionParser` uses
`allowlisted_pickle_load` (GHSA-rhp5), and `pathsec.ENFORCE` is `True` so
`/etc/passwd` raises `PermissionError` (GHSA-p3m8).

## Design

Inside `nltk/test/unit` so the coverage test imports it as a normal sibling —
no computed outside path, no `sys.path` injection (in an installed tree that
reaches `site-packages`). No advisory JSON is committed; the live list is
fetched only in the isolated CI job. STATIC probes locate NLTK source via each
module's own `__file__`.

## Findings (not code changes)

- Twelve published advisories, one critical (GHSA-x99w), have no
  `patched_versions` in their metadata, so pip-audit / Dependabot cannot tell
  users which release is safe.
- `validate_network_url()` fails open on DNS failure, but a simulated rebind is
  still blocked by `pathsec.urlopen`, which re-resolves through a pinned check —
  not exploitable. (The first version of that probe tested the helper alone and
  wrongly reported VULNERABLE; reachability is what makes a finding.)
