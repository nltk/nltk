# NLTK advisory verification — 2026-08

Every published security advisory for `nltk/nltk`, re-verified against the
working tree rather than taken on trust.

    python -m nltk.test.unit.security_probes             # probe every advisory
    NLTK_ADVISORY_CI=1 pytest .../test_advisory_coverage_ci.py  # CI gap check
    python -m nltk.test.unit.security_probes             # print the report

Offline gate: `nltk/test/unit/test_advisory_probes.py` (runs the probes + negative controls). CI-only gap gate: `test_advisory_coverage_ci.py` (pulls the live list from GitHub).

## Why probes rather than reading advisories

An advisory records that some version *was* vulnerable. It does not say the
current tree is fixed, and — this is the part that matters — a fix that
silently regresses looks exactly like a fix that shipped. Reading 37 advisories
by hand answers the question once. A probe answers it on every commit.

## Result

    published advisories:  37
      live probe, defended: 30
      source inspection:     7   (weaker evidence, see below)
      VULNERABLE:            0
      no probe:              0

    closed advisories:     21   (withdrawn or duplicate; not probed)

All three top-severity claims describe states that no longer exist:

| Advisory | Claim | Verified now |
|---|---|---|
| GHSA-x99w (critical) | pickle allowlist trusts whole module namespaces | dangerous globals rejected even under an allowlisted parent |
| GHSA-rhp5 (critical) | `TransitionParser` uses unrestricted `pickle_load` | routes through `allowlisted_pickle_load` |
| GHSA-p3m8 (high) | `pathsec.ENFORCE` defaults to `False` | `ENFORCE = True`; `/etc/passwd` → `PermissionError` |

## Evidence strength is labelled, not blurred

Seven probes report **STATIC**: they confirm the guard is present in the source
but do not execute the attack, because a safe reproduction needs a network
peer, a real download, or a running JVM. That is weaker evidence than FIXED and
is reported as such — a grep is not an exploit attempt, and a report that
presents one as the other is worse than no report.

STATIC today: GHSA-469j, GHSA-5wp5, GHSA-6ww7, GHSA-f794 (downloader),
GHSA-jm6w, GHSA-gfwx (wordnet_app), GHSA-6hwm (graphviz). Each is an upgrade
candidate.

## Findings

### 1. Twelve published advisories record no patched version

Including the critical **GHSA-x99w**. Downstream tooling — pip-audit,
Dependabot, GitHub's own alerts — reads `patched_versions` to decide whether an
installation is affected. With the field empty, users on a fixed release can
still be told they are vulnerable, and users on a vulnerable one may not be
warned at all.

    GHSA-x99w-6fgc-pmfw  critical    GHSA-3gq4-3j92-5w49  high
    GHSA-6ww7-3frv-cqxh  high        GHSA-8mgp-746c-j5xp  high
    GHSA-m4rf-3fr8-xwx3  high        GHSA-cw6x-m8jw-qmrh  medium
    GHSA-ff5c-cp5c-9wjf  medium      GHSA-ww6m-cw3f-q94g  medium
    GHSA-6hwm-xvph-95vm  low         GHSA-8mpw-7fpc-4gqj  low
    GHSA-97qj-x29f-37w7  low         GHSA-vp2x-qp44-57v7  low

This is metadata on GitHub, not a code change, but it is the finding with the
most direct effect on users.

### 2. `validate_network_url()` fails open on DNS failure — not exploitable

`_resolve_hostname` returns `[]` on `OSError`, so the validation loop in
`validate_network_url` iterates zero times and the function returns clean. The
fail-open **GHSA-3gqm** describes is real as a property of that function.

It is not, however, the reachable boundary. Simulating an actual rebind —
NXDOMAIN during validation, then `169.254.169.254` at connect time —
`pathsec.urlopen` blocks it, because the connection re-resolves through
`_resolve_and_validate_host`, which pins the numeric address and validates
every record.

Recorded because the first version of this probe called `validate_network_url`
alone and reported VULNERABLE. That measured a helper, not an attack. **What
decides exposure is whether the reachable API can be made to connect to a
forbidden address.** The probe now simulates the rebind end to end.

Still worth hardening: `validate_network_url` should not be used as a
standalone gate by callers who do not follow up with a pinned connection.

### 3. Three backlog items were wrong

Re-verified rather than trusted, and each had drifted:

- **pathsec shared temp dir — already fixed.** Gated on `is_private_dir()`,
  with a comment citing CWE-377/378 and excluding world-writable `/tmp`.
- **NKJP "world-readable temp file" — not world-readable.**
  `NamedTemporaryFile` creates at `0600`, and the file *is* removed via
  `remove_preprocessed_file()`.
- **TextTiling `eval()` — not exploitable.** An allowlist five lines above
  restricts `window` to five literal strings. Worth replacing with `getattr`
  as a code smell; not a vulnerability, and should not be described as one.

### 4. Genuinely open, low severity

- **`twython`** — the `twitter` extra pins an unmaintained package; last
  release 2021-07-16.
- **11 modules import `defusedxml` directly** rather than through
  `nltk/xmlsec.py`, so the hardening policy lives in eleven places.
- **`read_str`** (`nltk/internals.py:455`) calls bare `eval()` on a
  regex-matched slice. The regexes constrain it to a string literal, so this is
  a hardening candidate (`ast.literal_eval`) rather than a live hole — but it
  has not been proven equivalent, so it stays on the list.

## Lessons

1. **Probe the reachable API, not the helper.** The one false VULNERABLE in
   this sweep came from testing an internal function in isolation. Reachability
   is what separates a finding from a footnote.
2. **Label evidence strength.** Some checks execute the attack; some read the
   source. Collapsing both into "FIXED" makes the report untrustworthy exactly
   where it matters.
3. **A probe that crashes is not a pass.** The CI gate treats a probe raising
   an unexpected exception as a failure, because "the test errored" and "the
   code is safe" are not the same claim.
4. **Fail on unprobed advisories, not just failing ones.** Advisories are filed
   continuously; without that gate, coverage decays silently while the suite
   stays green.
5. **Verify a backlog before working it.** Three of eight pending items had
   already been fixed or were mis-stated. Recalled findings describe the tree
   as it was, not as it is.
