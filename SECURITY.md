# Security Policy

## Reporting a Vulnerability

Please report security issues to `nltk.team@gmail.com`

## Security Hardening

NLTK includes a centralized I/O security module (`nltk.pathsec`) that
validates file paths, network URLs, and zip archives.

As of NLTK 3.10.0, strict enforcement is enabled by default
(`ENFORCE=True`). In normal operation, NLTK applies the stricter
`pathsec` policy unless a caller explicitly opts out.

Under enforcement, unauthorized file access, SSRF attempts, and zip-slip
style path escapes raise exceptions (typically `PermissionError`) instead of emitting warnings.

### Resource-loading security model

NLTK's resource-loading protections are designed to reduce common risks
when NLTK is used with untrusted input or in shared environments such as
web applications, services, notebooks, CI/CD systems, and multi-tenant
pipelines.

In particular, the current policy reduces the risk of:

- **Arbitrary local file access through NLTK resource loading** by
  requiring filesystem access to remain within allowed NLTK data
  directories.
- **SSRF to non-public destinations** by resolving network targets and
  blocking loopback, private, link-local, and multicast addresses.
- **Redirect-based bypasses** by re-validating redirects at each hop.
- **Zip-slip attacks** by validating extraction targets before writing
  files.

These protections apply to NLTK's own resource-loading paths and URL
handling. They are not a general operating-system sandbox, and they do
not prevent all unsafe behavior an application might perform outside
NLTK.

### Local file access

`file:` URLs are not a general-purpose mechanism for loading arbitrary
local files.

With strict enforcement enabled (`ENFORCE=True`), file-backed resources
must resolve inside allowed NLTK data directories. By default these
directories are derived from:

1. `nltk.data.path` (configurable at runtime)
2. `NLTK_DATA` environment variable
3. Standard locations (`~/nltk_data`, `/usr/share/nltk_data`, etc.)
4. The system temp directory

If you use a custom resource directory, explicitly add it to
`nltk.data.path`:

```python
import nltk
nltk.data.path.append('/my/custom/data')
```

Then load resources by NLTK resource path rather than relying on access
to arbitrary filesystem locations.

### Current Working Directory (CWD) access

Implicit access to the current working directory is not allowed under
strict enforcement (`ENFORCE=True`) unless that directory has been
explicitly added to `nltk.data.path`.

If you intentionally want to trust the current directory, authorize it
explicitly:

```python
import nltk
nltk.data.path.append('.')
```

This makes the trust decision explicit and avoids surprising behavior in
server-side or shared execution environments.

### Module import hijacking (CWE-426)

NLTK uses lazy (inline) imports for optional dependencies such as
`numpy`, `joblib`, and `tqdm`. Like any Python code, these imports are
resolved through `sys.path`.

By default, Python prepends a path to `sys.path` at interpreter startup:
for `python script.py` it is the script's directory, and for
`python -m module`, `python -c ...`, or the REPL it is the current
working directory. If you run Python from an untrusted or
world-writable directory, an attacker who can place a malicious
`numpy.py`, `joblib.py`, or `tqdm.py` there can have it imported instead
of the real dependency, leading to arbitrary code execution.

This is an **interpreter-level** search-path issue (CWE-426), not
specific to NLTK. It cannot be reliably fixed from within a library:
by the time `import nltk` runs, `sys.path` is already built and other
modules may already have been imported against the unsafe entry. Deciding
whether the current directory should be on `sys.path` is the host
application's prerogative, and Python provides a direct way to make that
choice.

#### Recommended mitigation

Start Python so the unsafe path is never added in the first place. On
Python 3.11+:

```bash
python -P your_script.py
# or, per invocation:
PYTHONSAFEPATH=1 python your_script.py
```

`-P` / `PYTHONSAFEPATH` omit the auto-prepended script/CWD entry from
`sys.path` at startup, before any import runs. This applies to *all*
imports in the process, not just NLTK's, and is the mitigation CPython
itself recommends for untrusted working directories.

#### Enabling it conveniently

For a one-off command, prefix the invocation:

```bash
PYTHONSAFEPATH=1 python your_script.py
```

To apply it to every Python process you launch, export the environment
variable from your shell profile (e.g. `~/.bashrc`, `~/.zshrc`, or
`~/.profile`):

```bash
export PYTHONSAFEPATH=1
```

Because it is an environment variable, it is inherited by scripts,
subprocesses, virtual-environment interpreters, cron jobs, and most
tools that launch Python — which the command-line `-P` flag is not. This
is the most reliable "set once" option.

> **Note:** exporting `PYTHONSAFEPATH=1` changes behavior for *all* your
> Python programs. A few programs legitimately rely on importing modules
> from the current working directory (for example, running a script that
> imports a sibling file). If you hit an unexpected `ModuleNotFoundError`
> after enabling it, that program needs the CWD on `sys.path` and should
> be run without the flag, or its directory added to `PYTHONPATH`
> explicitly.

A shell alias such as `alias python='python -P'` is possible but **not
recommended as a security control**: aliases apply only to interactive
shells and only to the exact command name `python`. They do not cover
shebang scripts, `python3`/`py`/venv interpreters, IDEs, notebook
kernels, or subprocesses, so they can leave gaps. Prefer the exported
environment variable.

#### Enabling it in CI

Setting `PYTHONSAFEPATH=1` in continuous integration keeps the test suite
running under the same policy recommended above. Set it once in the job
environment so every Python step, and any subprocesses they spawn,
inherit it. This is not a substitute for CI isolation: in CI the working
directory is the checked-out repository itself, so if that code is
untrusted (for example, a fork pull request) the real protection comes
from the CI platform running it with restricted permissions and no
secrets, not from `-P`.

NLTK's own CI runs with `PYTHONSAFEPATH=1` and the test suite includes
`test_safe_path_blocks_cwd_import`, which fails if the policy is not in
effect.

#### Limitations

`-P` / `PYTHONSAFEPATH` removes only the *automatic, implicit* prepending
of the script/CWD directory at interpreter startup. It does **not**
prevent code that runs later — the host application, a dependency, or
test tooling such as `pytest` — from deliberately re-adding the current
directory, e.g.:

```python
import sys
sys.path.insert(0, "")  # CWD is searchable again
```

It is therefore a strong, sensible default rather than an irreversible
sandbox. Its value is that the CWD is no longer searched *silently and by
default*; re-adding it afterward is an explicit act by code you already
trust to run in your process. NLTK does not attempt to enforce this from
within the library, because doing so would mean mutating the host
application's global `sys.path` — which is both easily undone and poor
library etiquette.

### Network URL validation

NLTK permits network resource loading only for `http:` and `https:`
URLs.

Before a request is made, NLTK validates the resolved destination and
blocks requests to:

- loopback addresses
- private RFC1918 ranges
- link-local addresses
- multicast addresses

Redirects are re-validated at each hop, so a public URL cannot bypass
the policy by redirecting to a blocked destination.

In practice, ordinary public URLs continue to work, while destinations
such as `127.0.0.1`, `10.0.0.0/8`, and `169.254.169.254` are rejected.

### What is protected

- **Path traversal**: file access is validated against allowed NLTK
  data directories (`nltk.data.path`, `NLTK_DATA`, and standard system
  locations).
- **SSRF prevention**: `urlopen` resolves hostnames via DNS and blocks
  requests to loopback, private, link-local, and multicast IP ranges,
  including obfuscated forms where applicable.
- **Zip-slip protection**: zip extraction validates that member paths
  stay within the target directory.
- **Pickle safety**: `nltk.data.load()` uses `RestrictedUnpickler`
  which blocks all class/function globals. Other pickle loading uses
  `pickle_load()` which emits a security warning.

### Note on symlinks

NLTK's corpus readers perform lexical path containment checks when
joining file paths. These checks do not resolve symlinks. If your threat
model includes attackers who can place symlinks inside trusted NLTK data
directories, keep strict enforcement enabled so paths are fully resolved
and validated.
