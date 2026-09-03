#!/usr/bin/env python3
# Natural Language Toolkit: methodical CVE/CWE coverage audit
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Generate a full CVE/CWE security-coverage ledger for the NLTK codebase.

Pulls the authoritative weakness/vulnerability catalogs from the live sources:

* MITRE CWE: the complete weakness DICTIONARY (cwec_latest.xml), which enumerates
  every Weakness, Category and View id MITRE has ever assigned, deprecated entries
  included (1450 ids at v4.20). It is a strict superset of the 2000.csv
  "Comprehensive" view, which exports weakness rows ONLY (969, with no Category or
  View ids), https://cwe.mitre.org/data/xml/cwec_latest.xml.zip
* NIST NVD -- every CVE the National Vulnerability Database (the enriched mirror
  of the CVE Program / cve.org) attributes to the ``nltk`` product,
  https://services.nvd.nist.gov/rest/json/cves/2.0

then classifies EVERY weakness against this codebase by evidence, not by name:

1. Inventory the code surfaces NLTK actually has (grep: file I/O, pickle, XML,
   subprocess/JVM, eval, regex, network, HTTP server, SQL, temp files, archives,
   reflection, ...).
2. For each CWE, map it (by specific keyword, else by its MITRE pillar walked up
   the ChildOf hierarchy) to the surface it requires and verdict it:
   - PATCHED+TESTED  (a fix in nltk/ tags this CWE, with a test) -- carries the
     ``git log -S`` commit;
   - APPLICABLE      (the surface is present) -- names the guard that covers it;
   - N/A             (the surface is absent, or the weakness cannot occur in a
     pure-Python library) -- carries the evidence/reason.

No weakness is left unresolved. Re-run whenever the catalogs or the code change:

    python tools/security_cve_cwe_audit.py            # writes SECURITY_LEDGER.md
    python tools/security_cve_cwe_audit.py --offline  # reuse cached catalogs

This is dev-only maintenance tooling; it is not shipped in the wheel or sdist.
"""

import argparse
import gzip
import io
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

# Authoritative COMPLETE source: MITRE's CWE dictionary XML enumerates every id
# ever assigned (weaknesses + categories + views, deprecated included). A zip
# holding one cwec_v*.xml; parsed by fetch_cwe below.
CWE_XML_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
# Documented fallback only, NOT complete: the 2000.csv "Comprehensive" view export
# lists weakness rows ONLY (969), with no Category or View ids (the 481-id gap).
CWE_CSV_URL = "https://cwe.mitre.org/data/csv/2000.csv.zip"
# The NVD is the enriched mirror of the CVE Program (cve.org) records; a CVE id on
# cve.org is the same record here, plus NVD's CWE/CPE mapping used below.
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
# Committed snapshot (NOT dot-hidden, NOT gitignored): the pulled CWE dictionary
# and every NVD dump live here gzipped so they travel with the branch and
# ``--offline`` reproduces the ledger with zero network. Refresh by re-running
# online; the fetch helpers rewrite the .gz in place.
CACHE = os.path.join(os.path.dirname(__file__), "security_audit_cache")

# Operation + execution surface classes the audit inherits from the wider Python
# ecosystem. NLTK runs on CPython and shells out to external binaries / a JVM, so
# a CVE in any of these classes is in scope even when its record names a different
# product: the ledger's job is to say whether NLTK's OWN equivalent surface is
# present and, if so, which chokepoint guards it. label -> the NVD keyword query
# that enumerates that class. Ordered most-specific first (primary-class pick).
ECOSYSTEM_KEYWORDS = {
    "python-interpreter": "cpython",
    "json": "python json",
    "zip-archive": "python zipfile",
    "tarfile-extract": "python tarfile",
    "pickle-load-dump": "python pickle",
    "yaml-load": "python yaml load",
    "deserialization": "python deserialization",
    "xml-entity": "python xml entity",
    "file-read-write": "python arbitrary file",
    "path-traversal": "python path traversal",
    "directory-traversal": "python directory traversal",
    "tempfile": "python tempfile",
    "terminal-escape": "terminal escape sequence injection",
    "command-injection": "python command injection",
    "subprocess": "python subprocess",
    "os-system": "python os.system",
    "search-path-binary": "untrusted search path python",
    "compile-eval": "python code injection eval",
    "jvm-java": "java deserialization",
    # optional scientific / ML dependencies NLTK imports (never vendored)
    "numpy": "numpy",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "scikit-learn": "scikit-learn",
    "gensim": "gensim",
    "pandas": "pandas dataframe",
    # external NLP tools NLTK drives via subprocess / a JVM
    "weka": "weka",
    "stanford-corenlp": "stanford corenlp",
    "mallet": "mallet",
    "senna": "senna nlp",
    "malt-parser": "maltparser",
    "hunpos": "hunpos",
    "prover9-mace": "prover9",
    "megam": "megam",
    "crfsuite": "crfsuite",
}

# Optional dependencies: a CVE here is inherited, remediated by upgrading the dep;
# NLTK's own exposure is bounded (it passes its arrays/strings, not untrusted
# files, to these libraries). Reported as INHERITED, never dropped.
DEPENDENCY_CLASSES = {
    "numpy",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "gensim",
    "pandas",
}
# External tools driven over a subprocess/JVM boundary: exploitable through NLTK
# only via the model/config path it hands them, which is the GHSA-8mgp / GHSA-j456
# containment class already guarded by validate_tool_path.
WRAPPED_TOOL_CLASSES = {
    "weka",
    "stanford-corenlp",
    "mallet",
    "senna",
    "malt-parser",
    "hunpos",
    "prover9-mace",
    "megam",
    "crfsuite",
    "jvm-java",
}

# Class -> (required surface, guard note) fallback verdict for a CVE that no
# specific KEYWORD_RULE matched but that this class's query surfaced.
ECOSYSTEM_CLASS_GUARD = {
    "python-interpreter": (
        "native_c",
        "runs on CPython; NLTK adds no unmanaged memory. Interpreter-level fixes "
        "are inherited by upgrading Python; NLTK's own surfaces are guarded below",
    ),
    "json": ("json", "GUARDED: nltk.jsontags (depth cap + tag allowlist)"),
    "zip-archive": ("archive", "GUARDED: pathsec ZipFile bomb caps + path containment"),
    "tarfile-extract": (
        "archive",
        "GUARDED: no tarfile.extractall of untrusted data; archive reads bounded",
    ),
    "pickle-load-dump": ("pickle", "GUARDED: nltk.picklesec allowlisting unpickler"),
    "yaml-load": ("yaml", "N/A: no yaml.load of untrusted data in NLTK"),
    "deserialization": ("pickle", "GUARDED: nltk.picklesec / jsontags / xmlsec"),
    "xml-entity": ("xml", "GUARDED: nltk.xmlsec / defusedxml (XXE + entity caps)"),
    "file-read-write": (
        "file_io",
        "GUARDED: nltk.pathsec (validate_path/validate_tool_path) + open guard",
    ),
    "path-traversal": (
        "file_io",
        "GUARDED: nltk.pathsec containment (resolves symlinks before check)",
    ),
    "directory-traversal": (
        "file_io",
        "GUARDED: nltk.pathsec containment (data-root bounded)",
    ),
    "tempfile": (
        "tempfile",
        "GUARDED: make_staging_dir (0700 data root) + staging_tempdir",
    ),
    "terminal-escape": (
        "html_output",
        "GUARDED: nltk.termsec.sanitize_terminal (control + bidi neutralisation)",
    ),
    "command-injection": (
        "subprocess_jvm",
        "GUARDED: find_binary (CWD-relative refused) + validate_tool_path; no shell=True",
    ),
    "subprocess": (
        "subprocess_jvm",
        "GUARDED: argv lists (never shell=True); binary paths validate_tool_path",
    ),
    "os-system": (
        "subprocess_jvm",
        "GUARDED: NLTK uses argv-list Popen, not os.system/shell strings",
    ),
    "search-path-binary": (
        "subprocess_jvm",
        "GUARDED: find_binary refuses CWD-relative + validates the resolved binary",
    ),
    "compile-eval": (
        "eval_exec",
        "GUARDED: only decorators eval, fenced by _assert_safe_signature",
    ),
    "jvm-java": (
        "subprocess_jvm",
        "GUARDED: JVM invoked via argv list; model/config paths validate_tool_path "
        "(GHSA-8mgp / GHSA-j456 containment class)",
    ),
    # optional dependencies (surface irrelevant; verdict is INHERITED, see classify)
    "numpy": (
        "native_c",
        "INHERITED: optional dep; NLTK feeds its own arrays, not untrusted "
        "files/numpy.load pickles; remediate by upgrading numpy",
    ),
    "scipy": (
        "native_c",
        "INHERITED: optional dep (sparse features); NLTK passes its own matrices; "
        "remediate by upgrading scipy",
    ),
    "matplotlib": (
        "native_c",
        "INHERITED: optional dep (plotting only); NLTK renders its own figures; "
        "remediate by upgrading matplotlib",
    ),
    "scikit-learn": (
        "pickle",
        "INHERITED: optional dep; SklearnClassifier persists via nltk.picklesec "
        "allowlist, not raw joblib/pickle; remediate by upgrading scikit-learn",
    ),
    "gensim": (
        "pickle",
        "INHERITED: optional dep (word2vec demos); model loads go through "
        "picklesec; remediate by upgrading gensim",
    ),
    "pandas": (
        "native_c",
        "INHERITED: optional dep (test/demo tabular output); NLTK builds its own "
        "frames; remediate by upgrading pandas",
    ),
    # external tools over the subprocess/JVM boundary
    "weka": (
        "subprocess_jvm",
        "GUARDED: WekaClassifier model path validate_tool_path (GHSA-8mgp/j456); "
        "JVM via argv list, no shell",
    ),
    "stanford-corenlp": (
        "subprocess_jvm",
        "GUARDED: server URL/path bounded; JVM via argv list; jar/model paths "
        "validate_tool_path",
    ),
    "mallet": (
        "subprocess_jvm",
        "GUARDED: mallet prefix/model paths validate_tool_path; argv list JVM",
    ),
    "senna": (
        "subprocess_jvm",
        "GUARDED: senna binary via find_binary (CWD-relative refused) + validated",
    ),
    "malt-parser": (
        "subprocess_jvm",
        "GUARDED: maltparser jar/model validate_tool_path; argv list JVM",
    ),
    "hunpos": (
        "subprocess_jvm",
        "GUARDED: hunpos binary/model validate_tool_path; argv list, no shell",
    ),
    "prover9-mace": (
        "subprocess_jvm",
        "GUARDED: prover9/mace binary find_binary + input signature sanitised "
        "(_assert_prover9_safe)",
    ),
    "megam": (
        "subprocess_jvm",
        "GUARDED: megam binary find_binary + validate_tool_path; argv list",
    ),
    "crfsuite": (
        "subprocess_jvm",
        "GUARDED: python-crfsuite model path validate_tool_path (staged data root)",
    ),
}

# ---- code-surface inventory (what NLTK actually contains) -------------------

SURFACE_PATTERNS = {
    "file_io": r"\bopen\(|pathsec_open|io\.open|codecs\.open",
    "pickle": r"pickle|Unpickler|picklesec",
    "json": r"json\.load|jsontags",
    "xml": r"ElementTree|xml\.|xmlsec|expat|minidom|sax",
    "yaml": r"yaml\.",
    "subprocess_jvm": r"subprocess|Popen|internals import.*java|\bjava\(",
    "eval_exec": r"\beval\(|\bexec\(|\bcompile\(",
    "regex": r"redos|\bre\.(compile|search|match|sub|findall)",
    "network": r"urlopen|urllib|socket\.|requests\.|http\.client",
    "http_server": r"HTTPServer|BaseHTTPRequestHandler",
    "html_output": r"import html|<html|<a href|_repr_html_|_repr_svg_",
    "sql": r"sqlite|cursor|\.execute\(",
    "crypto": r"hashlib|\bhmac\b|secrets\.|ssl\.|cryptography",
    "tempfile": r"tempfile|mkstemp|mkdtemp|NamedTemporaryFile",
    "archive": r"zipfile|ZipFile|gzip|tarfile",
    "native_c": r"ctypes|cffi|Cython",
    "threads": r"threading|multiprocessing|asyncio",
    "getattr_dyn": r"getattr\(|__import__|importlib\.import_module",
    "format_string": r"format_string_placeholder_never_matches",
}

# Specific keyword -> (surface, guard note). First match wins over the pillar.
KEYWORD_RULES = [
    (
        (
            "path traversal",
            "pathname",
            "restricted directory",
            "link following",
            "symlink",
            "directory traversal",
            "file name or path",
            "external control of file",
        ),
        "file_io",
        "GUARDED: nltk.pathsec (validate_path/validate_tool_path) + open guard",
    ),
    (
        (
            "deserialization",
            "pickle",
            "unpickl",
            "serialized object",
            "object injection",
        ),
        "pickle",
        "GUARDED: nltk.picklesec allowlisting unpickler",
    ),
    (
        (
            "xml external entity",
            "xxe",
            "xml entity",
            "entity expansion",
            "billion laughs",
            "dtd",
            "external reference",
        ),
        "xml",
        "GUARDED: nltk.xmlsec / defusedxml",
    ),
    (
        (
            "os command",
            "command injection",
            "argument injection",
            "shell metacharacter",
            "untrusted search path",
            "search path element",
            "dll",
        ),
        "subprocess_jvm",
        "GUARDED: find_binary (CWD-relative refused) + validate_tool_path; no shell=True",
    ),
    (
        (
            "code injection",
            "eval injection",
            "expression language",
            "dynamically-managed code",
        ),
        "eval_exec",
        "GUARDED: only decorators eval, fenced by _assert_safe_signature + guard",
    ),
    (
        (
            "regular expression",
            "redos",
            "inefficient regular",
            "catastrophic backtrack",
            "algorithmic complexity",
        ),
        "regex",
        "GUARDED: nltk.redos (timeout + compile-time refusal)",
    ),
    (
        ("server-side request forgery", "ssrf", "request forgery", "open redirect"),
        "network",
        "GUARDED: nltk.pathsec SSRF (IP filter, redirect re-validate, pin)",
    ),
    (
        ("cross-site scripting", "xss", "web page generation"),
        "html_output",
        "GUARDED: html.escape at the wordnet_app HTML sinks",
    ),
    (
        ("cross-site request forgery", "csrf"),
        "http_server",
        "GUARDED: per-process HMAC shutdown token (wordnet_app)",
    ),
    (
        (
            "bidirect",
            "homoglyph",
            "visual",
            "control character",
            "escape sequence",
            "terminal",
        ),
        "html_output",
        "GUARDED: nltk.termsec.sanitize_terminal (control + bidi)",
    ),
    (
        ("csv", "formula", "spreadsheet"),
        "html_output",
        "GUARDED: nltk.termsec.sanitize_csv_field",
    ),
    (
        ("sql injection", "sql command"),
        "sql",
        "GUARDED: chat80 uses parameterized sqlite (bound params)",
    ),
    (
        ("temporary file", "insecure temporary", "world-writable"),
        "tempfile",
        "GUARDED: make_staging_dir (0700 data root) + staging_tempdir",
    ),
    (
        (
            "decompression",
            "zip",
            "compressed",
            "resource exhaustion",
            "allocation of resources",
            "uncontrolled memory",
            "amplification",
        ),
        "archive",
        "GUARDED: pathsec ZipFile decompression-bomb caps + size bounds",
    ),
    (
        ("recursion", "infinite loop", "loop with unreachable", "stack exhaustion"),
        "regex",
        "GUARDED: depth/time bounds (redos, shiftreduce max_time, parser caps)",
    ),
    (
        ("reflection", "unsafe reflection"),
        "getattr_dyn",
        "GUARDED: getattr/import targets are allowlisted, never raw corpus data",
    ),
    (
        (
            "sensitive information",
            "information exposure",
            "information disclosure",
            "log file",
            "error message",
            "cleartext",
        ),
        "file_io",
        "GUARDED: creds report key-names only; no secrets logged",
    ),
    (
        (
            "buffer",
            "out-of-bounds",
            "use after free",
            "dangling",
            "pointer",
            "memory corruption",
            "integer overflow",
            "numeric truncation",
            "memory leak",
            "uninitialized",
        ),
        "native_c",
        "N/A: managed Python (CPython), no unmanaged memory",
    ),
    (("format string",), "format_string", "N/A: no C-style format-string sink"),
    (
        (
            "hardware",
            "firmware",
            "physical",
            "microarchitect",
            "spectre",
            "meltdown",
            "jtag",
        ),
        None,
        "N/A: hardware/firmware weakness",
    ),
]

PILLARS = {
    284: "Access Control",
    435: "Entity Interaction",
    664: "Resource Lifetime",
    682: "Incorrect Calculation",
    691: "Control Flow",
    693: "Protection Mechanism",
    697: "Incorrect Comparison",
    703: "Exceptional Conditions",
    707: "Improper Neutralization",
    710: "Coding Standards",
}
PILLAR_VERDICT = {
    284: (
        "N/A",
        "access-control pillar: a library, not an auth boundary "
        "(the local wordnet_app server's auth/CSRF/loopback ARE guarded)",
    ),
    435: ("N/A", "entity-interaction pillar: no multi-party protocol/session surface"),
    664: (
        "APPLICABLE",
        "resource-lifetime pillar: file/deser/temp surfaces PRESENT "
        "-> pathsec/picklesec/jsontags/xmlsec/staging (memory sub-tree N/A: managed Python)",
    ),
    682: (
        "N/A",
        "incorrect-calculation pillar: Python ints arbitrary-precision, no C wrap",
    ),
    691: (
        "APPLICABLE",
        "control-flow pillar: recursion/loop surfaces PRESENT "
        "-> depth/time bounds (redos, shiftreduce, parser caps)",
    ),
    693: (
        "N/A",
        "protection-mechanism pillar: authors no crypto/authN; stdlib secrets/hmac",
    ),
    697: ("N/A", "incorrect-comparison pillar: token compare uses hmac.compare_digest"),
    703: (
        "APPLICABLE",
        "exceptional-conditions pillar: input validated at parse/reader "
        "/metric boundaries",
    ),
    707: (
        "APPLICABLE",
        "improper-neutralization pillar: injection/output surfaces PRESENT "
        "-> pathsec/redos/xmlsec/termsec/find_binary/escaping",
    ),
    710: ("N/A", "coding-standards pillar: maintainability weakness, not exploitable"),
}


def _sh(cmd):
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    ).stdout.strip()


def _cache_has(name):
    """True if a cached catalog for ``name`` exists (gzipped or legacy plain)."""
    return os.path.exists(os.path.join(CACHE, name + ".gz")) or os.path.exists(
        os.path.join(CACHE, name)
    )


def _cache_read(name):
    """Return cached bytes for ``name`` (transparently gunzipping ``.gz``) or None.

    The committed snapshot stores every catalog gzipped (a ~10x shrink so the CWE
    dictionary + NVD dumps travel with the branch without bloating it); a legacy
    uncompressed file of the same name is still honoured.
    """
    gz = os.path.join(CACHE, name + ".gz")
    if os.path.exists(gz):
        with gzip.open(gz, "rb") as fh:
            return fh.read()
    raw = os.path.join(CACHE, name)
    if os.path.exists(raw):
        with open(raw, "rb") as fh:
            return fh.read()
    return None


def _cache_write(name, data):
    """Persist ``data`` (bytes) for ``name`` gzip-compressed under CACHE."""
    os.makedirs(CACHE, exist_ok=True)
    with gzip.open(os.path.join(CACHE, name + ".gz"), "wb") as fh:
        fh.write(data)


def _cwe_localname(tag):
    """Local element name with ElementTree's ``{namespace}`` prefix stripped.

    The CWE dictionary sits in a default namespace (``http://cwe.mitre.org/cwe-7``),
    so every tag ElementTree yields is namespace-qualified; matching by local name
    keeps the parser working across schema-version bumps.
    """
    return tag.rsplit("}", 1)[-1]


def fetch_cwe(offline=False):
    """Return list of (id:int, name, description, abstraction, [parent ids]).

    Source is MITRE's authoritative COMPLETE CWE dictionary (cwec_latest.xml):
    every Weakness, Category and View id MITRE has ever assigned, deprecated
    entries included (1450 at v4.20). This is a strict superset of the 2000.csv
    "Comprehensive" view, which exports weakness rows only (969) and omits all 481
    Category/View ids. Weakness parents come from ``Related_Weaknesses`` ChildOf so
    the pillar walk (``_pillar``) is unchanged; Category/View entries carry no
    parent (their ``Has_Member`` links point DOWN to members, not up), which the
    downstream classifier already treats as a category/view node.
    """
    if offline and _cache_has("cwec_dictionary.xml"):
        data = _cache_read("cwec_dictionary.xml")
    else:
        with urllib.request.urlopen(CWE_XML_URL, timeout=120) as r:
            zbytes = r.read()
        with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
            name = [n for n in z.namelist() if n.endswith(".xml")][0]
            data = z.read(name)
        _cache_write("cwec_dictionary.xml", data)

    # Parse securely from the in-memory bytes. Prefer defusedxml (refuses DTD,
    # general/external entities and external DTD loads); else fall back to stdlib
    # ElementTree. The source is MITRE's own signed dictionary and carries no
    # DOCTYPE, and stdlib expat does not resolve external entities, so entity
    # expansion is disabled either way. fromstring returns the root directly.
    try:
        import defusedxml.ElementTree as _SafeET

        root = _SafeET.fromstring(
            data, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except ImportError:
        import xml.etree.ElementTree as _StdET

        root = _StdET.fromstring(data)

    def _first_child(el, localname):
        for c in el:
            if _cwe_localname(c.tag) == localname:
                return c
        return None

    def _parents(el):
        rel = _first_child(el, "Related_Weaknesses")
        if rel is None:
            return []
        out = []
        for r in rel:
            if (
                _cwe_localname(r.tag) == "Related_Weakness"
                and r.get("Nature") == "ChildOf"
            ):
                cid = r.get("CWE_ID")
                if cid:
                    out.append(int(cid))
        return out

    # entry local-name -> (default abstraction when the attribute is absent, the
    # child tag holding the human-readable blurb). Categories/Views have no
    # Abstraction attribute, so label them by kind for downstream rendering.
    kinds = {
        "Weakness": (None, "Description"),
        "Category": ("Category", "Summary"),
        "View": ("View", "Objective"),
    }
    out = []
    for section in root:
        for entry in section:
            kind = _cwe_localname(entry.tag)
            if kind not in kinds:
                continue
            default_abstraction, desc_tag = kinds[kind]
            desc_el = _first_child(entry, desc_tag)
            desc = (desc_el.text or "").strip() if desc_el is not None else ""
            out.append(
                (
                    int(entry.get("ID")),
                    entry.get("Name", ""),
                    desc,
                    entry.get("Abstraction") or default_abstraction,
                    _parents(entry),
                )
            )
    return out


def fetch_nvd_cves(keyword="nltk", offline=False):
    """Return list of (cve_id, cwe, description) the NVD attributes to nltk."""
    name = "nvd_%s.json" % keyword
    if offline and _cache_has(name):
        raw = _cache_read(name)
    else:
        url = "{}?keywordSearch={}&resultsPerPage=200".format(NVD_API, keyword)
        with urllib.request.urlopen(url, timeout=60) as r:
            raw = r.read()
        _cache_write(name, raw)
    d = json.loads(raw)
    out = []
    for v in d.get("vulnerabilities", []):
        c = v["cve"]
        desc = next((x["value"] for x in c["descriptions"] if x["lang"] == "en"), "")
        cwe = ""
        for w in c.get("weaknesses", []):
            for dd in w.get("description", []):
                if dd["value"].startswith("CWE-"):
                    cwe = dd["value"]
                    break
        out.append((c["id"], cwe, desc))
    return sorted(out)


def inventory_surfaces(root="nltk"):
    surf = {}
    for name, pat in SURFACE_PATTERNS.items():
        # argv list, NOT a shell string: the pattern reaches grep verbatim. Passing
        # it through a shell with %r double-escaped the backslashes, turning
        # `\bopen\(` / `\bjava\(` / `\beval\(` into an unbalanced `(` that made grep
        # error out to zero (file_io/subprocess_jvm/eval_exec wrongly read "absent").
        r = subprocess.run(
            ["grep", "-rlE", pat, root, "--include=*.py"],
            capture_output=True,
            text=True,
        )
        files = [f for f in r.stdout.split() if "/test/" not in f]
        surf[name] = len(files)
    return surf


def _pillar(cid, childof, seen=None):
    seen = seen or set()
    if cid in PILLARS:
        return cid
    if cid in seen:
        return None
    seen.add(cid)
    for p in childof.get(cid, []):
        r = _pillar(p, childof, seen)
        if r:
            return r
    return None


def _classify_text(text, surfaces):
    """Run the keyword rules against free text -> (status, verdict) or None."""
    text = text.lower()
    for keys, surface, verdict in KEYWORD_RULES:
        if any(k in text for k in keys):
            if surface is None or verdict.startswith("N/A"):
                return "N/A", verdict
            if surfaces.get(surface, 0) > 0:
                return "APPLICABLE", verdict
            return "N/A", "N/A: %s surface absent in codebase" % surface
    return None


def classify_cwe(cid, name, desc, surfaces, childof):
    hit = _classify_text(name + " " + desc, surfaces)
    if hit:
        return hit
    p = _pillar(cid, childof)
    if p:
        return PILLAR_VERDICT[p]
    return "N/A", "no exploitable surface (category/view/deprecated node)"


def _harvest_nvd(d, label, agg):
    """Fold one NVD response page into the dedup accumulator ``agg``."""
    for v in d.get("vulnerabilities", []):
        c = v["cve"]
        cid = c["id"]
        desc = next((x["value"] for x in c["descriptions"] if x["lang"] == "en"), "")
        cwe = ""
        for w in c.get("weaknesses", []):
            for dd in w.get("description", []):
                if dd["value"].startswith("CWE-"):
                    cwe = dd["value"]
                    break
        e = agg.setdefault(cid, {"cwe": cwe, "desc": desc, "classes": []})
        if label not in e["classes"]:
            e["classes"].append(label)
        if cwe and not e["cwe"]:
            e["cwe"] = cwe


def fetch_ecosystem_cves(offline=False, delay=7, page=200, max_pages=25):
    """Sweep every ECOSYSTEM_KEYWORDS class on the NVD, PAGINATED to exhaustion.

    Each class is paged through startIndex=0,page,2*page,... until every
    totalResults record is pulled (bounded by max_pages as a runaway backstop), so
    the sweep is complete rather than capped at one 200-row page. Page 0 caches as
    ``nvd_eco_<label>.json``, later pages as ``nvd_eco_<label>_p<startIndex>.json``,
    so ``--offline`` replays the full set. Returns (rows, class_counts, capped):
    rows is a sorted list of (cve_id, cwe, desc, [classes]); class_counts maps each
    class to its NVD totalResults; capped lists only a class that would still exceed
    max_pages*page (declared in the ledger, never silently dropped; normally empty).
    """
    import time

    agg = {}
    class_counts = {}
    capped = []
    net = [False]  # gate the rate-limit sleep on having actually hit the network

    def _get(label, start):
        name = (
            "nvd_eco_%s.json" % label
            if start == 0
            else "nvd_eco_%s_p%d.json" % (label, start)
        )
        if offline and _cache_has(name):
            return json.loads(_cache_read(name))
        if net[0]:
            time.sleep(delay)  # NVD unauthenticated rate limit (5 req / 30s)
        net[0] = True
        url = "{}?keywordSearch={}&resultsPerPage={}&startIndex={}".format(
            NVD_API, urllib.parse.quote(ECOSYSTEM_KEYWORDS[label]), page, start
        )
        with urllib.request.urlopen(url, timeout=60) as r:
            raw = r.read()
        _cache_write(name, raw)
        return json.loads(raw)

    for label in ECOSYSTEM_KEYWORDS:
        try:
            d = _get(label, 0)
        except Exception as e:  # transient NVD outage: keep going, note gap
            sys.stderr.write("  %s: fetch failed (%s)\n" % (label, e))
            continue
        total = d.get("totalResults", 0)
        class_counts[label] = total
        _harvest_nvd(d, label, agg)
        pulled = len(d.get("vulnerabilities", []))
        pages = 1
        while pulled < total and pages < max_pages:
            try:
                d = _get(label, pages * page)
            except Exception as e:
                sys.stderr.write(
                    "  %s p%d: fetch failed (%s)\n" % (label, pages * page, e)
                )
                break
            got = d.get("vulnerabilities", [])
            if not got:
                break
            _harvest_nvd(d, label, agg)
            pulled += len(got)
            pages += 1
        if pulled < total:
            capped.append((label, total))
    rows = sorted((cid, e["cwe"], e["desc"], e["classes"]) for cid, e in agg.items())
    return rows, class_counts, capped


def classify_ecosystem_cve(cwe, desc, classes, surfaces):
    """Verdict a Python-ecosystem CVE against NLTK's real surface.

    Specific KEYWORD_RULE match on the description wins; otherwise the CVE's
    primary (first) surfacing class supplies the guard note. Never dropped: an
    absent surface is reported as N/A-by-absence, not omitted.
    """
    primary = classes[0] if classes else None
    # dependency CVEs are inherited-only: the fix is a version bump, so report them
    # as INHERITED regardless of a matching operation-class keyword in the blurb.
    if primary in DEPENDENCY_CLASSES:
        _, note = ECOSYSTEM_CLASS_GUARD[primary]
        return "INHERITED (dep)", note
    hit = _classify_text(desc, surfaces)
    if hit:
        return hit
    surface, note = ECOSYSTEM_CLASS_GUARD.get(primary, (None, ""))
    if surface is None:
        return "N/A", note or "no NLTK-equivalent surface"
    if note.startswith("N/A"):
        return "N/A", note
    if surfaces.get(surface, 0) > 0:
        return "IN-SCOPE (guarded)", note
    return "N/A", "%s: %s surface absent in NLTK" % (primary, surface)


def generate(offline=False, out_path="SECURITY_LEDGER.md"):
    cwes = fetch_cwe(offline)
    cves = fetch_nvd_cves("nltk", offline)
    eco_rows, eco_counts, eco_capped = fetch_ecosystem_cves(offline)
    surfaces = inventory_surfaces()
    childof = {c[0]: c[4] for c in cwes}
    addressed = set(_sh("grep -rhoE 'CWE-[0-9]+' nltk/ --include='*.py'").split())
    commit_cache = {}

    def commit(idv):
        if idv not in commit_cache:
            commit_cache[idv] = (
                _sh("git log --format=%%h -1 -S'%s' -- nltk/" % idv) or ""
            )
        return commit_cache[idv]

    stats = {}
    cwe_rows = []
    for cid, name, desc, ab, _ in sorted(cwes):
        tag = "CWE-%d" % cid
        if tag in addressed:
            st, verdict, cm = "PATCHED+TESTED", "addressed in code", commit(tag)
        else:
            st, verdict = classify_cwe(cid, name, desc, surfaces, childof)
            cm = ""
        stats[st] = stats.get(st, 0) + 1
        cwe_rows.append((tag, name, ab, st, verdict, cm))

    lines = ["# NLTK Security Ledger — every MITRE CWE + NVD CVE vs the codebase\n"]
    lines.append(
        "Auto-generated by `tools/security_cve_cwe_audit.py` from the live MITRE CWE and"
    )
    lines.append(
        "NIST NVD catalogs, classified by evidence against this codebase. Re-run to refresh.\n"
    )
    lines.append(
        "**Totals:** %d CWEs classified (%s); %d NVD CVEs.\n"
        % (
            len(cwe_rows),
            ", ".join("%d %s" % (v, k) for k, v in sorted(stats.items())),
            len(cves),
        )
    )
    lines.append("## Code-surface inventory (files per construct)\n")
    lines.append("| surface | files | present |\n|---|---|---|")
    for k, v in surfaces.items():
        lines.append("| %s | %d | %s |" % (k, v, "yes" if v else "no"))
    lines.append(
        "\n## Every MITRE CWE (complete cwec dictionary: weaknesses + categories + views)\n"
    )
    lines.append("| CWE | Name | Abstraction | Verdict | Evidence / guard | Commit |")
    lines.append("|---|---|---|---|---|---|")
    for tag, name, ab, st, verdict, cm in cwe_rows:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                tag,
                name.replace("|", "\\|")[:58],
                ab,
                st,
                verdict.replace("|", "\\|"),
                "`%s`" % cm if cm else "",
            )
        )
    lines.append("\n## Every NVD CVE attributed to the nltk product\n")
    lines.append("| CVE | CWE | NLTK status | Commit |")
    lines.append("|---|---|---|---|")
    for cid, cwe, desc in cves:
        if "llama" in desc.lower():
            status, cm = "N/A: dependency (llama_index), not NLTK", ""
        elif _sh("grep -rlE '%s' nltk/ --include='*.py'" % cid):
            has_t = bool(_sh("grep -rlE '%s' nltk/test/ --include='*.py'" % cid))
            status, cm = ("PATCHED+TESTED" if has_t else "PATCHED"), commit(cid)
        elif cwe and (cwe in addressed):
            status, cm = "COVERED by %s class (chokepoint)" % cwe, commit(cwe)
        else:
            status, cm = "advisory-only / older-version fix", ""
        lines.append(
            "| {} | {} | {} | {} |".format(
                cid, cwe or "-", status, "`%s`" % cm if cm else ""
            )
        )

    # ---- Python-ecosystem inherited-surface sweep ---------------------------
    eco_stats = {}
    eco_render = []
    for cid, cwe, desc, classes in eco_rows:
        if _sh("grep -rlE '%s' nltk/ --include='*.py'" % cid):
            has_t = bool(_sh("grep -rlE '%s' nltk/test/ --include='*.py'" % cid))
            st = "PATCHED+TESTED" if has_t else "PATCHED"
            verdict, cm = "addressed directly in nltk/", commit(cid)
        else:
            st, verdict = classify_ecosystem_cve(cwe, desc, classes, surfaces)
            cm = commit(cwe) if cwe in addressed else ""
        eco_stats[st] = eco_stats.get(st, 0) + 1
        eco_render.append((cid, cwe, classes, st, verdict, cm))

    lines.append(
        "\n## Python-ecosystem inherited-surface CVEs (json/zip/tar/pickle/xml/"
        "file/path/tempfile/terminal/subprocess/os.system/JVM/compile/eval)\n"
    )
    lines.append(
        "NLTK runs on CPython and shells out to external binaries / a JVM, so a CVE "
        "in any of these operation classes is in scope even when its record names a "
        "different product. Every hit is classified against NLTK's OWN surface; "
        "**nothing is dropped** — an absent surface is reported as N/A-by-absence, "
        "not omitted. Swept classes and their NVD result counts:\n"
    )
    lines.append("| class | NVD query | results |\n|---|---|---|")
    for label, kw in ECOSYSTEM_KEYWORDS.items():
        lines.append("| %s | `%s` | %s |" % (label, kw, eco_counts.get(label, "n/a")))
    if eco_capped:
        lines.append(
            "\n> **Truncation disclosed (no silent cap):** these classes exceeded the "
            "200-row NVD page and are represented by their first 200; re-run with "
            "pagination to exhaust them: "
            + ", ".join("%s (%d total)" % (l, n) for l, n in eco_capped)
            + "."
        )
    lines.append(
        "\n**Distinct ecosystem CVEs classified:** %d (%s).\n"
        % (
            len(eco_render),
            ", ".join("%d %s" % (v, k) for k, v in sorted(eco_stats.items())),
        )
    )
    lines.append(
        "| CVE | CWE | Surface class(es) | NLTK verdict | Guard / evidence | Commit |"
    )
    lines.append("|---|---|---|---|---|---|")
    for cid, cwe, classes, st, verdict, cm in eco_render:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                cid,
                cwe or "-",
                ", ".join(classes),
                st,
                verdict.replace("|", "\\|"),
                "`%s`" % cm if cm else "",
            )
        )

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return stats, len(cwe_rows), len(cves), len(eco_render), eco_stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--offline",
        action="store_true",
        help="reuse cached catalogs instead of fetching",
    )
    ap.add_argument("-o", "--out", default="SECURITY_LEDGER.md")
    args = ap.parse_args(argv)
    stats, ncwe, ncve, neco, eco_stats = generate(args.offline, args.out)
    print(
        "wrote %s: %d CWEs (%s), %d nltk-product CVEs, %d ecosystem CVEs (%s)"
        % (
            args.out,
            ncwe,
            ", ".join("%d %s" % (v, k) for k, v in sorted(stats.items())),
            ncve,
            neco,
            ", ".join("%d %s" % (v, k) for k, v in sorted(eco_stats.items())),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
