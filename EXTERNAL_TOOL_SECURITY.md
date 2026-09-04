# Securing NLTK's external-tool wrappers

Several NLTK modules shell out to a third-party executable (a native binary or a
JVM tool). Running an external program from a library is a well-known source of
vulnerabilities — untrusted search paths (CWE-426/427), loader injection
(CWE-88/426), and argument/CRLF injection (CWE-88/93). This document describes
the **layered guards** every such wrapper should apply and the **shared
primitives** in `nltk.pathsec` / `nltk.internals` that implement them, so a new
wrapper can be hardened by composition rather than re-inventing the checks.

The design principle is: **treat "run an external tool" as a single
security-critical primitive that is owned and audited once, not a
`subprocess.Popen` call sprinkled across the codebase.** The chokepoints are
`nltk.pathsec.spawn_trusted` (native binaries) and `nltk.internals.java` (JVM
tools).

## The seven layers

| # | Layer | What it stops | CWE | Primitive |
|---|-------|---------------|-----|-----------|
| 1 | **Resolve, don't search untrusted** | A planted `./tool` (CWD) or a `PATH`/relative match run in place of the real binary | 426/427 | `nltk.internals.find_binary_iter` (refuses CWD-relative matches; requires a trusted absolute location) |
| 2 | **Unswappable binary** | Another local user swapping the binary because it, or an ancestor directory, is group/world-writable | 426/732 | `pathsec.resolve_trusted_executable` (walks every directory from `/` to the target, following symlink hops; each must be owned by us/root and not group/world-writable) |
| 3 | **No shell, absolute exec** | The command being re-interpreted by a shell | 78/88 | `pathsec.spawn_trusted` (`Popen([real, *args], executable=real)`, refuses `shell=True`) |
| 4 | **Scrub the environment** | `LD_PRELOAD`/`DYLD_*`/`PYTHONPATH`/`GCONV_PATH`/… hijacking the child; a poisoned or empty `PATH` (empty is searched as the CWD) | 88/426 | `pathsec.safe_env` (deny-by-default whitelist; `PATH` locked to a no-command sentinel) |
| 5 | **Bound the arguments** | An attacker-controlled value injected as a `-option` or an out-of-sandbox file path | 88/22 | `pathsec.validate_tool_path`, `pathsec.validate_model_resource`; a per-tool allowlist for option tokens (e.g. Senna's `SUPPORTED_OPERATIONS`) |
| 6 | **Sanitize line-oriented I/O** | A CR/LF smuggling an extra input line into a line-oriented protocol | 93 | reject `\n`/`\r` in tokens fed to the tool (see Senna, REPP) |
| 7 | **Control the CWD** | A tool that loads a plugin/config from `.` | 426 | pass a safe `cwd=` to `spawn_trusted` (only when the tool reads the CWD) |

`spawn_trusted` bundles layers 1–4 (it calls `resolve_trusted_executable` and
`safe_env` for you); the wrapper supplies layers 5–7 for its own arguments and
I/O.

## Trust policy: strict everywhere

`spawn_trusted` **refuses** (raises `TrustError`) any binary whose path is not
owned by us/root on a non-writable chain, and **fails closed on Windows** (POSIX
mode bits do not describe who can write a Windows path, and NLTK does not assume
`win32security`).

Operator consequence: a tool installed in a **group/world-writable directory is
refused**. Notably this includes Homebrew's `/usr/local/bin` (`drwxrwxr-x`) and
many `pipx`/`~/tools` locations. Install external tools where **only you or root
can write** (e.g. `/usr/local/bin` owned `root:wheel 0755`, `/opt/<tool>`, or a
`0700` directory under your home), or point the wrapper's environment variable
(`SENNA`, `MEGAM`, `HUNPOS_TAGGER`, …) at such a location. Each wrapper surfaces
a refusal as a clear error naming the untrusted path.

## Per-wrapper status

| Wrapper | Module | Entry point | Guards | Notes |
|---------|--------|-------------|--------|-------|
| Senna | `classify/senna.py` | `tag_sents` | 1,2,3,4,5,6 | Reference implementation; 7 is N/A (reads only `-path` + stdin). PR #3858 |
| REPP | `tokenize/repp.py` | `_execute` | 1,2,3,4 | Scratch input already staged via `make_staging_dir` |
| TADM | `classify/tadm.py` | `call_tadm` | 1,2,3,4 | |
| MEGAM | `classify/megam.py` | `call_megam` | 1,2,3,4 | Low-level escape hatch; args pass through as literal argv (5 is the caller's) |
| Prover9 / Mace | `inference/prover9.py` | `Prover9Parent._call` | 1,2,3,4 | Shared `_call` covers both provers |
| Boxer / C&C | `sem/boxer.py` | `Boxer._call` | 1,2,3,4 | |
| Graphviz `dot` | `translate/api.py` | `AlignedSent._repr_svg_` | 1,2,3,4 | Strict policy refuses a Homebrew-`/usr/local/bin` `dot`; see trust policy |
| HunPos | `tag/hunpos.py` | `HunposTagger.__init__` | 1,3,5 | **Partial** — has `validate_tool_path` (5) + no-shell (3); routing through `spawn_trusted` (2,4) is deferred pending a rework of its shared guard-test framework |
| Stanford / Malt / CoreNLP / Weka | `parse/*`, `tag/stanford.py`, `classify/weka.py` | via `internals.java` | 1,3,4,5 | JVM tools: `find_binary` locates `java`, `_java_child_env` scrubs the environment, `validate_model_resource`/`validate_tool_path` bound the jar/model. Exec-trust (2) of the `java` binary itself is not yet routed through `resolve_trusted_executable` |

Layer 1 (`find_binary_iter`'s CWD-relative refusal) already applies uniformly to
**every** wrapper above, independent of the exec chokepoint.

## Standardizing a new native-binary wrapper

Replace a bare `subprocess.Popen(cmd, **kw)` where `cmd = [binary] + args`:

```python
from nltk.pathsec import TrustError, spawn_trusted

try:
    p = spawn_trusted(cmd[0], cmd[1:], **kw)   # layers 1-4
except TrustError as e:
    raise LookupError(
        f"Refusing to run {cmd[0]!r}: it is not on a trusted path. Install it "
        f"where only you (or root) can write ({e})."
    ) from e
stdout, stderr = p.communicate(...)
```

Then add the wrapper-specific guards:

- **Layer 5** — bound any caller-controlled option to an allowlist (see Senna's
  `SUPPORTED_OPERATIONS` check) and bound file-path arguments with
  `validate_tool_path` / `validate_model_resource`.
- **Layer 6** — if the tool consumes a line-oriented stream, reject `\n`/`\r`
  in the tokens.
- **Layer 7** — pass `cwd=` a trusted directory only if the tool loads anything
  from the current directory.

### Testing (real, not mocked)

Mirror the pattern in `test_repp_security.py` / `test_tadm_security.py`:

1. **Refusal test** — build the binary in a **world-writable** directory and
   assert the wrapper raises before running (real `chmod`, no mock).
2. **Trusted control** — stage the binary under a **private data root** with
   `nltk.data.make_staging_dir(cleanup=True)` (never `/tmp`, which the strict
   resolver refuses) and assert the spawn is reached with a resolved, absolute
   `argv[0]` and no shell.

Because the check runs *before* `Popen`, a test that builds its binary in
`tmp_path` (which is `/tmp` on Linux) will be refused; stage under
`make_staging_dir` instead. When spying on the spawn, patch the shared
`subprocess.Popen` (which `pathsec` uses), not `<wrapper>.Popen` — the wrapper no
longer imports `Popen` directly.
