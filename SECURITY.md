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
