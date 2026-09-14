# CLAUDE.md

Companion to [AGENTS.md](AGENTS.md) for Claude Code and other Claude-based agents. AGENTS.md is the baseline for every automated contributor — read it first. This file does not replace it; it adds the Claude Code workflow and the reasoning behind each rule. Where the two overlap, AGENTS.md governs scope and this file governs how to execute a change safely.

NLTK is a mature, educational library in maintenance mode. Optimize for a reviewer's time, not your own throughput.

## 1. Vet before you build (never work in silos)

A GitHub issue is a report, not a mandate.

* A singleton issue with no maintainer or contributor engagement is not a signal to fix. It may be unpatched on purpose.
* Read every comment on the issue and cross-reference related issues before forming a plan.
* If you believe an unvetted issue is worth doing, audit the relevant modules and their tests, propose your approach on the issue, and wait for maintainer consensus. Do not open a speculative PR.
* A human must be in the loop before any PR is opened.

## 2. Faithful before optimized

* Correct, human-readable, canonical code beats clever or fast code. NLTK exists to teach.
* Keep an implementation faithful to its cited paper or reference algorithm. If you have a non-canonical improvement, put it behind a user-facing toggle; never silently replace the faithful (even if flawed) implementation.
* Verify your change actually matches the cited algorithm and the surrounding conventions, not just what looks plausible to an LLM.

## 3. Security is a chokepoint, not an afterthought

Anything that opens, reads, writes, loads, saves, prints, parses, or spawns MUST route through the library's guards:

* `pathsec` — filesystem and network paths (containment, symlink/traversal, zip members).
* `picklesec` — pickle loading (allowlist unpickler).
* `jsontags` — JSON parsing (tagged, depth-bounded loader).
* `termsec` — terminal and CSV output (control, ANSI, bidi, and formula neutralisation).
* `redos` — every regular expression (compile and match time bounded).

Never call a bare `open` / `pickle.load` / `json.load` / `print` / `re` on untrusted data.

When your change touches that surface, the bar rises. Run this audit on the paths you touch:

> Read the security modules and their tests. Make sure no CWE/CVE exploit leaks through after your change. Expand the attack corpus for the surface you touched, add every plausible candidate (benign or not) to the harness, fix, and retest so no advisory exploit leaks. Then confirm the affected functionality still works: do not just mock it — load the modules, and for a third-party tool compile or run the real tool and cross-check its output.

Scope discipline (per AGENTS.md): attack the surface your change touches thoroughly, but do not refactor unrelated security modules or expand the audit across the whole codebase.

Three rules this project has paid for in real bugs:

* **Reject a threat vector; do not coerce it.** A lying `str` subclass can override `startswith`/`split`/`lower`/`__iter__` to validate as a benign flag while its real characters reach an argv or JVM sink. Hard-reject anything that is not an exact `str` (`type(x) is not str`) rather than normalising it, because a caller may discard the validated return and forward the original.
* **Bound recursion on untrusted input.** A deeply nested parser or traversal input (tree, logic, CCG, toolbox, dependency graph, tgrep, XML) must raise a controlled `ValueError` or domain exception at a documented `MAX_*_DEPTH`, never an uncaught `RecursionError`.
* **Do not run a bare executable.** A tool wrapper must accept only an absolute binary path; an explicit relative path resolves against the current working directory and can execute a planted binary.

## 4. Testing and CI

* Ordinary fixes get one focused test (see AGENTS.md). A security fix additionally gets a regression test that runs the real attack and asserts the *specific* bounded exception — a broad `except Exception` hides real bugs (a `NameError` can masquerade as "handled").
* Do not mock what you can run. For a third-party tool (CoreNLP, Stanford, Malt, Prover9, and so on) start the real binary and cross-check its output; a mock only proves the wrapper's plumbing, not that the tool works.
* Run the suite for the modules you touched locally, then watch CI after opening the PR. NLTK CI is cross-platform (Linux, macOS, Windows; Python 3.10 to 3.14) — a change can pass on one leg and fail on another.
* Never relax a test's criteria to make CI green. If a timing or DoS test flakes, fix the *measurement* (for example, take the minimum of several runs to remove scheduler noise); do not loosen the threshold, because the loosened bound is exactly what lets a real regression through. A transient single-runner flake is re-run, not edited.
* Use `python3.13` (not a bare `python3`) and the repo's pinned formatters; a newer local formatter reformats differently and reds pre-commit.

## 5. Git and pull requests

* One logical change per PR. No mass, cosmetic, or reformatting-only PRs.
* Stage explicit paths; never `git add -A` (it sweeps scratch files into the PR).
* Iterate with follow-up commits and a plain push; do not force-push a branch that is under review.
* Compare branches with `git worktree`, not a bare `git stash`.
* Do not open or push a PR without a human in the loop. Maintainer decisions are final — accept a rejection and close the loop; do not argue or generate a lengthy defense.
* Do not post PR or issue comments on the human's behalf unless they have asked for that specific comment.

## 6. Transparency

When an agentic tool produced the change, note the tool, the task, and the model in the PR description so it can be traced. Redact private context and raw chain-of-thought — a concise summary, not the reasoning log.
