# Security Policy

## Reporting a Vulnerability

Please report security issues to `nltk.team@gmail.com`

## Security Hardening

NLTK includes a centralized I/O security module (`nltk.pathsec`) that
validates file paths, network URLs, and zip archives. During the initial
transition phase, it operates by default in **warn-only mode**, to avoid
breaking existing workflows. In a later release, it will be switched to
enforce the stricter security policy by default.

### Enabling strict enforcement

If you are running NLTK in a security-sensitive environment (web
applications, multi-tenant pipelines, CI/CD systems, or any context
where untrusted input may reach NLTK), you should enable strict
enforcement:

```python
import nltk.pathsec
nltk.pathsec.ENFORCE = True
```

With `ENFORCE = True`, unauthorized file access, SSRF attempts, and
zip-slip attacks will raise `PermissionError` instead of emitting
warnings.


### Current Working Directory (CWD) Access

To maintain a "zero-friction" experience for students and researchers,
NLTK permits access to resources located in the process's current
working directory by default.

* **Standard Mode (`ENFORCE=False`):** Accessing data in the CWD is
permitted but triggers a `RuntimeWarning` to alert users that this
behavior may be insecure in shared or server-side environments.

* **Strict Mode (`ENFORCE=True`):** Implicit CWD access is **disabled**.
To authorize the local directory in strict mode, users must explicitly
append it to the search path:
  ```python
  import nltk
  nltk.data.path.append('.')
  ```


### What is protected

- **Path traversal**: file access is validated against allowed NLTK
  data directories (`nltk.data.path`, `NLTK_DATA` environment
  variable, and standard system locations).
- **SSRF prevention**: `urlopen` resolves hostnames via DNS and blocks
  requests to loopback, private, link-local, and multicast IP ranges,
  including obfuscated forms (e.g. decimal IP notation).
- **Zip-slip protection**: zip extraction validates that member paths
  stay within the target directory.
- **Pickle safety**: `nltk.data.load()` uses `RestrictedUnpickler`
  which blocks all class/function globals. Other pickle loading uses
  `pickle_load()` which emits a security warning.

### Configuring allowed data paths

NLTK determines allowed data directories from:

1. `nltk.data.path` (configurable at runtime)
2. `NLTK_DATA` environment variable
3. Standard locations (`~/nltk_data`, `/usr/share/nltk_data`, etc.)
4. System temp directory

If you use a custom data location, add it to `nltk.data.path`:

```python
import nltk
nltk.data.path.append('/my/custom/data')
```

### Note on symlinks

NLTK's corpus readers perform lexical path containment checks when
joining file paths. These checks do not resolve symlinks. If your
threat model includes attackers who can place symlinks inside your
NLTK data directories, enable `ENFORCE = True` for full path
resolution and validation.
