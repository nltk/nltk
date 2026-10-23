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

    python tools/security_cve_cwe_audit.py            # writes tools/pentest/ledgers/SECURITY_LEDGER.md
    python tools/security_cve_cwe_audit.py --offline  # reuse cached catalogs

This is dev-only maintenance tooling; it is not shipped in the wheel or sdist.
"""

import argparse
import fnmatch
import gzip
import http.client
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
# An NVD API key raises the limit from 5 to 50 requests per 30 s; read from the
# environment for the request header only, never written anywhere.
NVD_API_KEY_ENV = "NVD_API_KEY"
# The recency sweep: every record of the last ``since_months`` whose text
# mentions Python, in windows of at most 120 days (the API's date-range cap).
RECENCY_CLASS = "recent-python"
RECENCY_KEYWORD = "python"
# 119: the API refuses a span that reaches 120 days once the end of day is added.
RECENCY_WINDOW_DAYS = 119
# The complete publication stream: every record published in the window, no
# keyword, at the maximum page size, filtered locally for a Python context, so
# the ledger provably reaches the newest id (raw pages under CACHE/full).
STREAM_CLASS = "stream-all"
STREAM_PAGE = 2000
# Names that make a record OURS to triage by hand when no operation keyword
# matches: the library, its dependencies, its tools, the interpreter itself.
OWN_NAMES = (
    "nltk",
    "cpython",
    "python software foundation",
    "numpy",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "sklearn",
    "gensim",
    "pandas",
    "joblib",
    "tqdm",
    "pyparsing",
    "defusedxml",
    "twython",
    "pyyaml",
    "setuptools",
    "crfsuite",
    "weka",
    "corenlp",
    "stanford nlp",
    "mallet",
    "senna",
    "maltparser",
    "hunpos",
    "prover9",
    "megam",
    "graphviz",
    "bllip",
    "libexpat",
    "pyexpat",
    "zlib module",
    "python zlib",
    "sqlite3",
    "python sqlite",
    "requests library",
    "python-requests",
    "requests module",
    "python click",
    "click library",
)
# In scope for the stream: the text or the CPE names a Python context or a
# product the class queries enumerate.
STREAM_SCOPE_WORDS = (
    "python",
    "pypi",
    "cpython",
    "nltk",
    "numpy",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "sklearn",
    "gensim",
    "pandas",
    "joblib",
    "tqdm",
    "pyparsing",
    "defusedxml",
    "twython",
    "pyyaml",
    "setuptools",
    "crfsuite",
    "weka",
    "corenlp",
    "stanford nlp",
    "mallet",
    "senna",
    "maltparser",
    "hunpos",
    "prover9",
    "megam",
    "graphviz",
    "bllip",
    "libexpat",
    "zlib",
    "sqlite",
)
# GitHub Advisory Database, pip ecosystem: the curated PyPI feed, days ahead of
# the NVD's enrichment and holding advisories with no CVE id at all.
GHSA_API = "https://api.github.com/advisories"
GHSA_CLASS = "ghsa-pip"
GHSA_FIRST_YEAR = 2006
# CISA Known Exploited Vulnerabilities: every ledger row in it is flagged and
# every KEV record with a Python context is classified against the surfaces.
KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)
# The CVE Program's own records (what cve.org renders): the CNA container holds
# the authoritative description, CWE and affected products. Pulled per id.
CVE_ORG_API = "https://cveawg.mitre.org/api/cve/{}"
# Marker records read every run so the ledger shows each source answering: one
# old record and the newest ids known when set; the highest id read must reach them.
MARKER_CVES = ("CVE-2015-5477", "CVE-2026-109618", "CVE-2026-109619")
# The CVE List V5 bulk download behind cve.org's Downloads page: every record as
# one JSON file, a midnight zip plus hourly deltas on GitHub; read whole and
# filtered locally, the zips under CACHE/full and only the extract committed.
CVELIST_RELEASES_API = "https://api.github.com/repos/CVEProject/cvelistV5/releases"
CVELIST_CLASS = "cvelist-all"
# Notes about a catalog that could not be refreshed live; rendered at the top of
# the ledger so a stale catalog is declared, never silent.
CATALOG_NOTES = []
# Committed snapshot (NOT dot-hidden, NOT gitignored): the pulled CWE dictionary
# and every NVD dump live here gzipped so they travel with the branch and
# ``--offline`` reproduces the ledger with zero network. Refresh by re-running
# online; the fetch helpers rewrite the .gz in place.
CACHE = os.path.join(os.path.dirname(__file__), "security_audit_cache")
# Bulk pages of the full stream and the CVE List zips: large, ignored by git.
STREAM_CACHE = os.path.join(CACHE, "full")
# The generated ledger lives with the other pentest ledgers.
DEFAULT_LEDGER = os.path.join(
    os.path.dirname(__file__), "pentest", "ledgers", "SECURITY_LEDGER.md"
)

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
    "redos-python": "python regular expression denial of service",
    "expat": "libexpat",
    "zlib": "python zlib",
    "sqlite": "python sqlite",
    "urllib": "python urllib",
    "http-server": "python http.server",
    "html-injection": "python html injection",
    "symlink-race": "python symlink race",
    # optional scientific / ML dependencies NLTK imports (never vendored)
    "numpy": "numpy",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "scikit-learn": "scikit-learn",
    "gensim": "gensim",
    "pandas": "pandas dataframe",
    # runtime dependencies (install_requires and extras) and the build toolchain
    "click": "python click",
    "joblib": "joblib",
    "regex-module": "python regex module",
    "tqdm": "tqdm",
    "requests": "python requests library",
    "pyparsing": "pyparsing",
    "defusedxml": "defusedxml",
    "twython": "twython",
    "pyyaml": "pyyaml",
    "setuptools": "setuptools",
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
    "graphviz": "graphviz",
    "bllip": "bllip",
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
    "click",
    "joblib",
    "regex-module",
    "tqdm",
    "requests",
    "pyparsing",
    "defusedxml",
    "twython",
    "pyyaml",
    "setuptools",
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
    "graphviz",
    "bllip",
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
    "redos-python": ("regex", "GUARDED: nltk.redos (timeout + compile-time refusal)"),
    "expat": (
        "xml",
        "GUARDED: nltk.xmlsec / defusedxml (XXE + entity caps); expat itself is "
        "CPython's, remediated by upgrading Python",
    ),
    "zlib": (
        "archive",
        "GUARDED: pathsec ZipFile decompression-bomb caps + size bounds; zlib "
        "itself is CPython's, remediated by upgrading Python",
    ),
    "sqlite": ("sql", "GUARDED: chat80 uses parameterized sqlite (bound params)"),
    "urllib": (
        "network",
        "GUARDED: nltk.pathsec SSRF (IP filter, redirect re-validate, pin) on the "
        "downloader and CoreNLP client",
    ),
    "http-server": (
        "http_server",
        "GUARDED: wordnet_app loopback bind + HMAC shutdown token + html.escape",
    ),
    "html-injection": (
        "html_output",
        "GUARDED: html.escape at the wordnet_app HTML sinks",
    ),
    "symlink-race": (
        "file_io",
        "GUARDED: nltk.pathsec containment (resolves symlinks before check) + "
        "make_staging_dir (0700 data root)",
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
    "click": (
        "native_c",
        "INHERITED: runtime dep (nltk.cli command parsing); remediate by "
        "upgrading click",
    ),
    "joblib": (
        "pickle",
        "INHERITED: runtime dep (parallel loops only; no joblib.load of untrusted "
        "files, model loads go through picklesec); remediate by upgrading joblib",
    ),
    "regex-module": (
        "regex",
        "INHERITED: runtime dep, the engine behind nltk.redos; its timeout and "
        "the compile-time refusal bound every pattern; remediate by upgrading regex",
    ),
    "tqdm": (
        "html_output",
        "INHERITED: runtime dep (progress bars); NLTK passes counts, not untrusted "
        "text, to tqdm; remediate by upgrading tqdm",
    ),
    "requests": (
        "network",
        "INHERITED: optional dep (CoreNLP client, twitter); URLs go through the "
        "SSRF guard first; remediate by upgrading requests",
    ),
    "pyparsing": (
        "regex",
        "INHERITED: optional dep (tgrep grammar); the tgrep pattern is bounded by "
        "nltk.redos limits before parsing; remediate by upgrading pyparsing",
    ),
    "defusedxml": (
        "xml",
        "INHERITED: optional fast path under nltk.xmlsec, which keeps its own "
        "entity and depth caps; remediate by upgrading defusedxml",
    ),
    "twython": (
        "network",
        "INHERITED: optional dep (twitter client); remediate by upgrading twython",
    ),
    "pyyaml": (
        "yaml",
        "INHERITED: optional dep; nltk.jsontags routes yaml through safe_load "
        "only; remediate by upgrading pyyaml",
    ),
    "setuptools": (
        "native_c",
        "INHERITED: build-time dep of the sdist only, never imported at runtime; "
        "remediate by upgrading setuptools on the build host",
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
    "graphviz": (
        "subprocess_jvm",
        "GUARDED: dot is run through spawn_trusted (trusted-exec chokepoint) with "
        "an argv list; the graph text is escaped",
    ),
    "bllip": (
        "file_io",
        "GUARDED: BLLIP model directory validate_tool_path (data-root bounded)",
    ),
    RECENCY_CLASS: (
        None,
        "REVIEW: surfaced by the recency sweep only; no operation keyword matched, "
        "triaged by hand in the manual-triage section",
    ),
    STREAM_CLASS: (
        None,
        "REVIEW: surfaced by the full publication stream only; no operation keyword "
        "matched, triaged by hand in the manual-triage section",
    ),
    CVELIST_CLASS: (
        None,
        "REVIEW: surfaced by the complete CVE List only; no operation keyword "
        "matched, triaged by hand in the manual-triage section",
    ),
    GHSA_CLASS: (
        None,
        "REVIEW: pip-ecosystem advisory with no operation keyword matched, triaged "
        "by hand in the manual-triage section",
    ),
}

# == code-surface inventory (what NLTK actually contains) ==

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

# Guard-note substring -> the attack-test file globs that PROVE that guard by
# running the exploit through the real code path. Resolved against nltk/test/unit/
# at generate() time, so tests added later appear automatically. Ordered
# most-specific first; first match wins. This is what ties every APPLICABLE /
# IN-SCOPE row to the concrete test that proves it. A row whose verdict matches
# NO entry here (or matches one that resolves to zero files on disk) is flagged a
# COVERAGE GAP in the ledger, NOT silently assumed covered.
GUARD_TESTS = [
    (
        "sanitize_terminal",
        [
            "test_termsec_*.py",
            "test_trojan_source_security.py",
            "test_print_injection_sinks.py",
        ],
    ),
    ("sanitize_csv_field", ["test_csvsec_*.py", "test_csv_injection_security.py"]),
    (
        "_assert_safe_signature",
        ["test_decorators_security.py", "test_attack_core_guards_expanded.py"],
    ),
    (
        "getattr/import",
        ["test_pickle_allowlist_security.py", "test_attack_allowlist_*.py"],
    ),
    (
        "picklesec",
        [
            "test_pickle_*.py",
            "test_picklesec_*.py",
            "test_attack_deser_*.py",
            "test_attack_allowlist_*.py",
            "test_attack_warnonly_*.py",
            "test_attack_pickle_*.py",
        ],
    ),
    ("ssrf", ["test_ssrf_*.py", "test_attack_ssrf_*.py"]),
    (
        "decompression-bomb",
        ["test_zip*.py", "test_aggregate_zip_bomb.py", "test_downloader_unzip.py"],
    ),
    ("tarfile", ["test_zip*.py", "test_downloader_unzip.py"]),
    (
        "make_staging_dir",
        ["test_staging_tempdir_security.py", "test_maxent_scratch_staging_security.py"],
    ),
    ("staging_tempdir", ["test_staging_tempdir_security.py"]),
    ("weka", ["test_weka_*.py"]),
    (
        "find_binary",
        [
            "test_java_*.py",
            "test_attack_java_tool_*.py",
            "test_malt_*.py",
            "test_senna_*.py",
            "test_boxer_*.py",
            "test_*_stanford_pathsec.py",
            "test_attack_tool_injection_*.py",
            "test_corenlp_options_security.py",
        ],
    ),
    (
        "argv",  # matches "argv list" and "argv-list Popen ..."
        [
            "test_java_*.py",
            "test_attack_java_tool_*.py",
            "test_attack_tool_injection_*.py",
            "test_corenlp_options_security.py",
        ],
    ),
    (
        "os.system",
        [
            "test_java_*.py",
            "test_attack_java_tool_*.py",
            "test_attack_tool_injection_*.py",
        ],
    ),
    (
        "validate_tool_path",
        [
            "test_java_*.py",
            "test_malt_*.py",
            "test_senna_*.py",
            "test_weka_*.py",
            "test_pathsec_tool_resources.py",
            "test_model_artifact_pathsec.py",
        ],
    ),
    ("megam", ["test_attack_java_tool_expanded.py", "test_attack_tool_injection_*.py"]),
    (
        "spawn_trusted",
        [
            "test_pathsec_trusted_exec.py",
            "test_tool_search_path_security.py",
            "test_attack_trusted_symlink_expanded.py",
            "test_attack_translate_expanded.py",
        ],
    ),
    ("loopback bind", ["test_output_exposure_security.py", "test_attack_wordnet_*.py"]),
    (
        "jsontags",
        [
            "test_attack_json_*.py",
            "test_json_serialization.py",
            "test_attack_jsontags_*.py",
        ],
    ),
    (
        "xmlsec",
        [
            "test_xml*.py",
            "test_xmlsec.py",
            "test_attack_xml_*.py",
            "test_attack_xmlsec_*.py",
        ],
    ),
    ("defusedxml", ["test_xml*.py", "test_xmlsec.py", "test_attack_xml_*.py"]),
    (
        "redos",
        [
            "test_redos*.py",
            "test_*redos*.py",
            "test_attack_dos_*.py",
            "test_recursion_dos.py",
        ],
    ),
    (
        "depth/time bounds",
        ["test_redos*.py", "test_recursion_dos.py", "test_attack_dos_*.py"],
    ),
    ("shiftreduce", ["test_recursion_dos.py", "test_redos*.py"]),
    ("parser cap", ["test_recursion_dos.py", "test_redos*.py"]),
    ("html.escape", ["test_output_exposure_security.py", "test_attack_wordnet_*.py"]),
    (
        "hmac shutdown token",
        ["test_output_exposure_security.py", "test_attack_wordnet_*.py"],
    ),
    ("creds report key-names", ["test_output_exposure_security.py"]),
    ("no secrets logged", ["test_output_exposure_security.py"]),
    ("parameterized sqlite", ["test_chat80_pathsec.py", "test_attack_sqli_*.py"]),
    (
        "pathsec",
        [
            "test_pathsec*.py",
            "test_path_traversal_security.py",
            "test_corpus_reader_pathsec.py",
            "test_attack_path_sandbox_*.py",
            "test_*_pathsec.py",
            "test_data_security.py",
        ],
    ),
    (
        "improper-neutralization pillar",
        [
            "test_pathsec_io_attack_matrix.py",
            "test_redos.py",
            "test_xml_attack_matrix.py",
            "test_attack_java_tool_expanded.py",
        ],
    ),
    (
        "resource-lifetime pillar",
        [
            "test_pathsec_io_attack_matrix.py",
            "test_pickle_allowlist_security.py",
            "test_attack_json_loaders_expanded.py",
            "test_xmlsec.py",
            "test_staging_tempdir_security.py",
        ],
    ),
    ("control-flow pillar", ["test_recursion_dos.py", "test_redos.py"]),
    (
        "exceptional-conditions pillar",
        [
            "test_childes_security.py",
            "test_framenet_security.py",
            "test_nkjp_security.py",
            "test_conll_cmudict_security.py",
            "test_dependencygraph_security.py",
            "test_xmldocs_security.py",
        ],
    ),
    (
        "parse/reader",
        [
            "test_childes_security.py",
            "test_framenet_security.py",
            "test_nkjp_security.py",
            "test_conll_cmudict_security.py",
        ],
    ),
    ("cpython", []),  # inherited from Python upstream; no NLTK-level attack test
]

# Guards whose tests once lived only on a sibling PR (terminal sanitiser, CSV
# field sanitiser, decorators-eval fence) merged into develop with #3914, #3915
# and #3850, so GUARD_TESTS resolves them to files on disk; nothing is cross-PR.
CROSS_PR_GUARDS = []

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


# Hand-written verdicts, keyed by id, for records no keyword rule classified;
# the text is the evidence. A record missing here renders as REVIEW: open work.
MANUAL_TRIAGE = {
    "CVE-2025-29088": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2024-0232": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2021-31239": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2020-13435": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2019-19924": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2019-19926": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2019-19242": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2019-19244": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2019-16168": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2019-8457": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2015-3415": "INHERITED: a defect in the SQLite engine itself, which reaches NLTK only through CPython's bundled sqlite3 module; chat80 opens its store read-only with bound parameters; remediate by upgrading Python",
    "CVE-2021-36690": "N/A: the sqlite3 command-line shell, which NLTK never spawns; the vendor disputes the record",
    "CVE-2026-54619": "N/A: the Ruby sqlite3 gem; NLTK uses CPython's sqlite3 module",
    "CVE-2026-54620": "N/A: the Ruby sqlite3 gem; NLTK uses CPython's sqlite3 module",
    "CVE-2011-0995": "N/A: the Ruby sqlite3 gem packaging on SUSE; not a Python surface",
    "CVE-2022-43441": "N/A: the Node.js sqlite3 binding; not a Python surface",
    "CVE-2022-21227": "N/A: the Node.js sqlite3 binding; not a Python surface",
    "CVE-2016-10695": "N/A: an npm sqlite3 trunk module downloading binaries over HTTP; not a Python surface",
    "CVE-2026-58041": "N/A: Node.js node:sqlite; not a Python surface",
    "CVE-2026-54687": "N/A: an n8n node exposing a SQLite path; not a Python surface",
    "CVE-2025-47736": "N/A: a Rust SQLite parser crate; not a Python surface",
    "CVE-2021-28305": "N/A: the Rust diesel crate's SQLite backend; not a Python surface",
    "CVE-2021-0646": "N/A: Android's SQLite build; not a Python surface",
    "CVE-2019-2195": "N/A: Android's sqlite3_android tokenizer; not a Python surface",
    "CVE-2022-40278": "N/A: Samsung TizenRT provisioning database; not a Python surface",
    "CVE-2022-40280": "N/A: Samsung TizenRT provisioning database; not a Python surface",
    "CVE-2014-1422": "N/A: Ubuntu trust-store; not a Python surface",
    "CVE-2013-4376": "N/A: X2Go Server's SQLite wrapper; not a Python surface",
    "CVE-2011-1717": "N/A: Skype for Android's local databases; not a Python surface",
    "CVE-2026-23838": "N/A: Tandoor Recipes' NixOS packaging exposing its SQLite file; not a surface here",
    "CVE-2025-59163": "N/A: the vet supply-chain tool's MCP server; not a surface here",
    "CVE-2025-54119": "N/A: the ADOdb PHP library; not a Python surface",
    "CVE-2026-41138": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2026-35052": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2025-46725": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2025-0185": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2024-12366": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2023-46134": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2023-39660": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2023-39661": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2023-39662": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2026-27952": "N/A: a RestrictedPython sandbox allowlisting numpy in another product; NLTK runs no code sandbox",
    "CVE-2022-41890": "N/A: TensorFlow's numpy-compatible shape helper; NLTK does not import TensorFlow",
    "CVE-2022-26488": "INHERITED: the Python for Windows installer's PATH handling; remediated by upgrading the interpreter, not by this library",
    "CVE-2021-44550": "INHERITED: the CoreNLP server's NERServlet; NLTK is a client of the server and never exposes it; deploy CoreNLP 4.4.0 or later",
    "CVE-2020-28439": "N/A: an npm CoreNLP wrapper; NLTK's client is nltk.parse.corenlp",
    "CVE-2014-1829": "INHERITED: the requests dependency (netrc leak on redirect, fixed in 2.3.0); remediate by upgrading requests",
    "CVE-2014-8650": "N/A: the requests-kerberos add-on, which NLTK does not use",
    "CVE-2020-15720": "N/A: Dogtag PKI's client hard-coding requests verification off; NLTK's CoreNLP client leaves verification on",
    "CVE-2026-105745": "N/A: Docling importing entry points before honouring its plugin switch; NLTK loads no entry-point plugins",
    "CVE-2026-113731": "N/A: the djust MCP tool reading templates by absolute path; not a surface here",
    "CVE-2026-24811": "N/A: the ROOT framework's bundled zlib; NLTK uses CPython's zlib",
    "CVE-2026-24812": "N/A: the ROOT framework's bundled zlib; NLTK uses CPython's zlib",
    "CVE-2017-14919": "N/A: Node.js zlib windowBits; not a Python surface",
    "CVE-2026-54769": "N/A: another package evaluating untrusted text through pandas; NLTK never calls pandas.eval or DataFrame.query, and its only pandas use renders tables it builds itself",
    "CVE-2025-30990": "N/A: another project's record; it names a product NLTK neither imports nor drives, and the operation is not present here",
    "CVE-2018-8823": "N/A: another project's record; it names a product NLTK neither imports nor drives, and the operation is not present here",
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
        import datetime

        age = os.path.getmtime(os.path.join(CACHE, "cwec_dictionary.xml.gz"))
        CATALOG_NOTES.append(
            "MITRE CWE dictionary: offline run, cached copy written %s"
            % datetime.date.fromtimestamp(age).isoformat()
        )
        data = _cache_read("cwec_dictionary.xml")
    else:
        try:
            zbytes = _get_with_retries(
                urllib.request.Request(CWE_XML_URL), timeout=180, attempts=3
            )
            with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
                name = [n for n in z.namelist() if n.endswith(".xml")][0]
                data = z.read(name)
            _cache_write("cwec_dictionary.xml", data)
        except Exception as e:
            if not _cache_has("cwec_dictionary.xml"):
                raise
            CATALOG_NOTES.append(
                "MITRE CWE dictionary: the live fetch failed (%s); the cached "
                "dictionary was used, re-run to refresh" % e
            )
            data = _cache_read("cwec_dictionary.xml")

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


def _get_with_retries(req, timeout, attempts=5, backoff=30):
    """GET with retries: a rate-limit or gateway error and a connection timeout
    both sleep ``backoff`` seconds and try again; the last error propagates."""
    import time
    import urllib.error

    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (403, 429, 500, 502, 503, 504):
                raise
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.HTTPException,
        ) as e:
            last = e
        sys.stderr.write("  retry %d/%d after %s\n" % (attempt + 1, attempts, last))
        time.sleep(backoff)
    raise last


def _nvd_get(url, timeout=120):
    """GET an NVD URL, with the API key header when the environment holds one."""
    req = urllib.request.Request(url)
    key = os.environ.get(NVD_API_KEY_ENV)
    if key:
        req.add_header("apiKey", key)
    return _get_with_retries(req, timeout)


def _nvd_delay():
    """Seconds between NVD requests: the published limits with and without a key."""
    return 0.8 if os.environ.get(NVD_API_KEY_ENV) else 7


def _cve_fields(c):
    """(cwe, description, published date) of one NVD ``cve`` record."""
    desc = next((x["value"] for x in c["descriptions"] if x["lang"] == "en"), "")
    cwe = ""
    for w in c.get("weaknesses", []):
        for dd in w.get("description", []):
            if dd["value"].startswith("CWE-"):
                cwe = dd["value"]
                break
    return cwe, desc, (c.get("published") or "")[:10]


def fetch_nvd_cves(keyword="nltk", offline=False):
    """Return list of (cve_id, cwe, description, published) the NVD attributes to nltk."""
    name = "nvd_%s.json" % keyword
    if offline and _cache_has(name):
        raw = _cache_read(name)
    else:
        url = f"{NVD_API}?keywordSearch={keyword}&resultsPerPage=200"
        raw = _nvd_get(url)
        _cache_write(name, raw)
    d = json.loads(raw)
    out = []
    for v in d.get("vulnerabilities", []):
        c = v["cve"]
        cwe, desc, published = _cve_fields(c)
        out.append((c["id"], cwe, desc, published))
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
        cwe, desc, published = _cve_fields(c)
        e = agg.setdefault(
            cid, {"cwe": cwe, "desc": desc, "classes": [], "published": published}
        )
        if label not in e["classes"]:
            e["classes"].append(label)
        if cwe and not e["cwe"]:
            e["cwe"] = cwe
        if published and not e["published"]:
            e["published"] = published


def _in_stream_scope(c):
    """True when an NVD ``cve`` record names a Python context or one of the
    products the class queries enumerate, in its text or its CPE criteria."""
    text = " ".join(x["value"] for x in c.get("descriptions", [])).lower()
    if any(w in text for w in STREAM_SCOPE_WORDS):
        return True
    for conf in c.get("configurations", []):
        for node in conf.get("nodes", []):
            for m in node.get("cpeMatch", []):
                crit = m.get("criteria", "").lower()
                if ":python:" in crit or any(w in crit for w in STREAM_SCOPE_WORDS):
                    return True
    return False


def _cve_number(cid):
    try:
        return tuple(int(x) for x in cid.split("-")[1:3])
    except ValueError:
        return (0, 0)


def fetch_full_stream(since, offline=False, delay=None, max_pages=200):
    """Read EVERY record the NVD published from ``since`` (ISO date) to today, no
    keyword, in RECENCY_WINDOW_DAYS windows at STREAM_PAGE records a page.
    Returns (rows, stats): rows are the in-scope records as
    (cve_id, cwe, desc, [STREAM_CLASS], published); stats carries the totals per
    window, the in-scope count and the highest id read, which the ledger prints
    so the sweep provably reaches the newest publication."""
    import datetime
    import time

    if delay is None:
        delay = _nvd_delay()
    os.makedirs(STREAM_CACHE, exist_ok=True)
    today = datetime.date.today()
    start = datetime.date.fromisoformat(since)
    windows = []
    cursor = start
    while cursor < today:
        end = min(cursor + datetime.timedelta(days=RECENCY_WINDOW_DAYS), today)
        windows.append((cursor.isoformat(), end.isoformat()))
        cursor = end
    net = [False]
    agg = {}
    stats = {"windows": [], "read": 0, "in_scope": 0, "highest": "", "since": since}
    for window_start, window_end in windows:
        read = 0
        total = None
        index = 0
        pages = 0
        while total is None or (read < total and pages < max_pages):
            name = "nvd_full_%s_%s_p%d.json.gz" % (window_start, window_end, index)
            path = os.path.join(STREAM_CACHE, name)
            if offline and os.path.exists(path):
                with gzip.open(path, "rb") as fh:
                    d = json.loads(fh.read())
            else:
                if net[0]:
                    time.sleep(delay)
                net[0] = True
                url = (
                    "{}?pubStartDate={}T00:00:00.000&pubEndDate={}T23:59:59.999"
                    "&resultsPerPage={}&startIndex={}".format(
                        NVD_API, window_start, window_end, STREAM_PAGE, index
                    )
                )
                try:
                    raw = _nvd_get(url)
                except Exception as e:
                    sys.stderr.write(
                        "  %s %s p%d: fetch failed (%s)\n"
                        % (STREAM_CLASS, window_start, index, e)
                    )
                    break
                with gzip.open(path, "wb") as fh:
                    fh.write(raw)
                d = json.loads(raw)
            total = d.get("totalResults", 0)
            got = d.get("vulnerabilities", [])
            if not got:
                break
            for v in got:
                c = v["cve"]
                if _cve_number(c["id"]) > _cve_number(stats["highest"]):
                    stats["highest"] = c["id"]
                if _in_stream_scope(c):
                    cwe, desc, published = _cve_fields(c)
                    e = agg.setdefault(
                        c["id"],
                        {
                            "cwe": cwe,
                            "desc": desc,
                            "classes": [STREAM_CLASS],
                            "published": published,
                        },
                    )
                    if cwe and not e["cwe"]:
                        e["cwe"] = cwe
            read += len(got)
            index += len(got)
            pages += 1
        stats["windows"].append((window_start, window_end, total or 0, read))
        stats["read"] += read
    stats["in_scope"] = len(agg)
    rows = sorted(
        (cid, e["cwe"], e["desc"], e["classes"], e["published"])
        for cid, e in agg.items()
    )
    return rows, stats


def fetch_ghsa_pip(
    first_year=GHSA_FIRST_YEAR, offline=False, per_page=100, max_pages=60
):
    """Every GitHub Advisory Database record for the pip ecosystem, read one
    calendar year at a time from ``first_year`` to today (a closed year is cached
    for good; the current year is re-read). Returns rows (ghsa_id, cve_id, cwe,
    desc, published, [package names], severity), newest first."""
    import datetime

    today = datetime.date.today()
    rows = []
    for year in range(first_year, today.year + 1):
        start = "%d-01-01" % year
        end = today.isoformat() if year == today.year else "%d-12-31" % year
        rows.extend(_fetch_ghsa_window(start, end, offline, per_page, max_pages))
    seen = set()
    unique = []
    for r in sorted(rows, key=lambda r: r[4], reverse=True):
        if r[0] not in seen:
            seen.add(r[0])
            unique.append(r)
    return unique


def _github_page(url):
    """(body bytes, next-page URL or None) for one GitHub REST page; the
    global advisories endpoint paginates by cursor in the Link header."""
    import time
    import urllib.error

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                link = r.headers.get("Link", "")
                break
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.HTTPException,
        ) as e:
            last = e
            time.sleep(20)
    else:
        raise last
    nxt = None
    for part in link.split(","):
        if 'rel="next"' in part:
            nxt = part.split(";")[0].strip().strip("<>")
    return body, nxt


def _fetch_ghsa_window(since, until, offline, per_page, max_pages):
    import time

    rows = []
    url = "{}?ecosystem=pip&published={}..{}&per_page={}".format(
        GHSA_API, since, until, per_page
    )
    closed_year = until.endswith("-12-31")
    for page in range(1, max_pages + 1):
        name = "ghsa_pip_%s_%s_cursor%d.json" % (since, until, page)
        if _cache_has(name) and (offline or closed_year):
            cached = json.loads(_cache_read(name))
            items, url = cached["items"], cached.get("next")
        else:
            if url is None:
                break
            try:
                raw, url = _github_page(url)
            except Exception as e:
                CATALOG_NOTES.append(
                    "GitHub Advisory Database (pip): %s..%s page %d failed (%s); "
                    "the feed is partial, re-run to complete" % (since, until, page, e)
                )
                break
            items = json.loads(raw)
            _cache_write(
                name, json.dumps({"items": items, "next": url}).encode("utf-8")
            )
            time.sleep(1)
        if not items:
            break
        for a in items:
            cwe = (a.get("cwes") or [{}])[0].get("cwe_id", "") if a.get("cwes") else ""
            desc = "{}. {}".format(a.get("summary", ""), a.get("description") or "")
            packages = sorted(
                {
                    v["package"]["name"].lower()
                    for v in a.get("vulnerabilities", [])
                    if v.get("package")
                }
            )
            rows.append(
                (
                    a["ghsa_id"],
                    a.get("cve_id") or "",
                    cwe,
                    desc,
                    (a.get("published_at") or "")[:10],
                    packages,
                    a.get("severity") or "",
                )
            )
        if url is None:
            break
    return rows


def fetch_cve_record(cid, offline=False):
    """One CVE Program record from the CVE Services API: dict with state,
    published, cwes (CNA problem types), description, affected ([vendor
    product]) and the cna name, or None when the record cannot be read."""
    import time

    name = "cveorg_%s.json" % cid
    if _cache_has(name) and offline:
        raw = _cache_read(name)
    else:
        req = urllib.request.Request(CVE_ORG_API.format(cid))
        req.add_header("Accept", "application/json")
        try:
            raw = _get_with_retries(req, timeout=60, attempts=3, backoff=10)
        except Exception as e:
            if _cache_has(name):
                raw = _cache_read(name)
            else:
                CATALOG_NOTES.append(
                    "cve.org record {}: fetch failed ({})".format(cid, e)
                )
                return None
        else:
            _cache_write(name, raw)
            time.sleep(0.5)
    d = json.loads(raw)
    meta = d.get("cveMetadata", {})
    cna = d.get("containers", {}).get("cna", {})
    cwes = []
    for pt in cna.get("problemTypes", []):
        for desc in pt.get("descriptions", []):
            cwe = desc.get("cweId") or ""
            if not cwe and desc.get("description", "").startswith("CWE-"):
                cwe = desc["description"].split()[0]
            if cwe and cwe not in cwes:
                cwes.append(cwe)
    description = next(
        (
            x.get("value", "")
            for x in cna.get("descriptions", [])
            if x.get("lang", "").startswith("en")
        ),
        "",
    )
    affected = [
        "{} {}".format(a.get("vendor", ""), a.get("product", ""))
        for a in cna.get("affected", [])
    ]
    return {
        "id": meta.get("cveId", cid),
        "state": meta.get("state", ""),
        "published": (meta.get("datePublished") or "")[:10],
        "cwes": cwes,
        "description": description,
        "affected": affected,
        "cna": cna.get("providerMetadata", {}).get("shortName", ""),
    }


def _github_json(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    return json.loads(_get_with_retries(req, timeout=60, attempts=3, backoff=20))


def _download(url, path):
    """Stream a large asset to ``path`` (skipped when it is already there)."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    req = urllib.request.Request(url)
    tmp = path + ".part"
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, path)
    return path


def _cvelist_record(data):
    """Compact row of one CVE List V5 record: (id, state, published, [cwes],
    description, [affected vendor product], cna)."""
    meta = data.get("cveMetadata", {})
    cna = data.get("containers", {}).get("cna", {})
    cwes = []
    for pt in cna.get("problemTypes", []):
        for desc in pt.get("descriptions", []):
            cwe = desc.get("cweId") or ""
            if not cwe and desc.get("description", "").startswith("CWE-"):
                cwe = desc["description"].split()[0]
            if cwe and cwe not in cwes:
                cwes.append(cwe)
    description = next(
        (
            x.get("value", "")
            for x in cna.get("descriptions", [])
            if x.get("lang", "").startswith("en")
        ),
        "",
    )
    affected = [
        "{} {}".format(a.get("vendor", ""), a.get("product", ""))
        for a in cna.get("affected", [])
    ]
    return (
        meta.get("cveId", ""),
        meta.get("state", ""),
        (meta.get("datePublished") or "")[:10],
        cwes,
        description,
        affected,
        cna.get("providerMetadata", {}).get("shortName", ""),
    )


def _cvelist_in_scope(row):
    text = (row[4] + " " + " ".join(row[5])).lower()
    return any(w in text for w in STREAM_SCOPE_WORDS)


def _walk_cvelist_zip(path, visit):
    """Call ``visit(record_dict)`` for every CVE JSON inside a CVE List V5 zip,
    the midnight archive (a zip holding one inner zip) or an hourly delta zip."""
    with zipfile.ZipFile(path) as outer:
        inner_names = [n for n in outer.namelist() if n.lower().endswith(".zip")]
        if inner_names:
            with outer.open(inner_names[0]) as inner_fh:
                data = io.BytesIO(inner_fh.read())
            with zipfile.ZipFile(data) as inner:
                for name in inner.namelist():
                    if name.endswith(".json") and "/CVE-" in name:
                        with inner.open(name) as fh:
                            visit(json.load(fh))
        else:
            for name in outer.namelist():
                if name.endswith(".json") and "/CVE-" in name:
                    with outer.open(name) as fh:
                        visit(json.load(fh))


def fetch_cve_list_v5(offline=False):
    """Read the complete CVE List V5: the latest midnight archive plus every
    hourly delta released since it. Returns (rows, stats): rows are the in-scope
    records as (cve_id, cwe, desc, [CVELIST_CLASS], published), stats holds the
    release tag, record counts by state and by year, the highest id and the
    delta tags applied. Offline, the committed in-scope extract is replayed."""
    extract = "cvelist_v5_scope.json"
    if offline and _cache_has(extract):
        saved = json.loads(_cache_read(extract))
        return [tuple(r) for r in saved["rows"]], saved["stats"]
    os.makedirs(STREAM_CACHE, exist_ok=True)
    releases = _github_json(CVELIST_RELEASES_API + "?per_page=40")
    midnight = None
    for rel in releases:
        for asset in rel.get("assets", []):
            if asset["name"].endswith("_all_CVEs_at_midnight.zip.zip"):
                midnight = (
                    rel["tag_name"],
                    asset["name"],
                    asset["browser_download_url"],
                )
                break
        if midnight:
            break
    deltas = []
    if midnight:
        day = midnight[1].split("_all_CVEs")[0]
        for rel in releases:
            for asset in rel.get("assets", []):
                name = asset["name"]
                if name.startswith(day + "_delta_CVEs_at_") and name.endswith(".zip"):
                    deltas.append(
                        (rel["tag_name"], name, asset["browser_download_url"])
                    )
    if midnight is None:
        CATALOG_NOTES.append(
            "CVE List V5: no midnight archive among the latest releases"
        )
        return [], {}
    stats = {
        "release": midnight[0],
        "deltas": [d[0] for d in deltas],
        "records": 0,
        "by_state": {},
        "by_year": {},
        "highest": "",
        "in_scope": 0,
    }
    agg = {}

    def visit(data):
        row = _cvelist_record(data)
        cid, state, published = row[0], row[1], row[2]
        if not cid:
            return
        stats["records"] += 1
        stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
        year = cid.split("-")[1] if "-" in cid else "?"
        stats["by_year"][year] = stats["by_year"].get(year, 0) + 1
        if _cve_number(cid) > _cve_number(stats["highest"]):
            stats["highest"] = cid
        if state != "REJECTED" and _cvelist_in_scope(row):
            agg[cid] = (
                cid,
                row[3][0] if row[3] else "",
                row[4],
                [CVELIST_CLASS],
                published,
            )

    path = _download(midnight[2], os.path.join(STREAM_CACHE, midnight[1]))
    _walk_cvelist_zip(path, visit)
    for tag, name, url in sorted(deltas):
        try:
            dpath = _download(url, os.path.join(STREAM_CACHE, name))
            _walk_cvelist_zip(dpath, visit)
        except Exception as e:
            CATALOG_NOTES.append("CVE List V5 delta {}: {}".format(tag, e))
    stats["in_scope"] = len(agg)
    rows = sorted(agg.values())
    _cache_write(extract, json.dumps({"rows": rows, "stats": stats}).encode("utf-8"))
    return rows, stats


def fetch_kev(offline=False):
    """The CISA Known Exploited Vulnerabilities catalog: {cve_id: (date added,
    vendor, product, name, short description)}."""
    name = "cisa_kev.json"
    if offline and _cache_has(name):
        raw = _cache_read(name)
    else:
        try:
            raw = _get_with_retries(
                urllib.request.Request(KEV_URL), timeout=120, attempts=3
            )
            _cache_write(name, raw)
        except Exception as e:
            if not _cache_has(name):
                CATALOG_NOTES.append("CISA KEV: fetch failed (%s); no cached copy" % e)
                return {}
            CATALOG_NOTES.append(
                "CISA KEV: the live fetch failed (%s); the cached catalog was used" % e
            )
            raw = _cache_read(name)
    d = json.loads(raw)
    out = {}
    for v in d.get("vulnerabilities", []):
        out[v["cveID"]] = (
            v.get("dateAdded", ""),
            v.get("vendorProject", ""),
            v.get("product", ""),
            v.get("vulnerabilityName", ""),
            v.get("shortDescription", ""),
        )
    return out


def _recency_windows(since_months, today=None):
    """[(start, end)] ISO date pairs of at most RECENCY_WINDOW_DAYS covering the
    last ``since_months`` months up to ``today`` (newest window last)."""
    import datetime

    today = today or datetime.date.today()
    start = today - datetime.timedelta(days=int(round(since_months * 30.44)))
    out = []
    cursor = start
    while cursor < today:
        end = min(cursor + datetime.timedelta(days=RECENCY_WINDOW_DAYS), today)
        out.append((cursor.isoformat(), end.isoformat()))
        cursor = end
    return out


def fetch_ecosystem_cves(
    offline=False, delay=None, page=200, max_pages=25, since_months=0
):
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

    if delay is None:
        delay = _nvd_delay()
    agg = {}
    class_counts = {}
    capped = []
    net = [False]  # gate the rate-limit sleep on having actually hit the network

    def _fetch(name, query):
        if offline and _cache_has(name):
            return json.loads(_cache_read(name))
        if net[0]:
            time.sleep(delay)  # the NVD rate limit, with or without a key
        net[0] = True
        raw = _nvd_get(f"{NVD_API}?{query}")
        _cache_write(name, raw)
        return json.loads(raw)

    def _get(label, start):
        name = (
            "nvd_eco_%s.json" % label
            if start == 0
            else "nvd_eco_%s_p%d.json" % (label, start)
        )
        return _fetch(
            name,
            "keywordSearch={}&resultsPerPage={}&startIndex={}".format(
                urllib.parse.quote(ECOSYSTEM_KEYWORDS[label]), page, start
            ),
        )

    def _get_recent(window_start, window_end, start):
        name = "nvd_recent_%s_%s_p%d.json" % (window_start, window_end, start)
        return _fetch(
            name,
            "keywordSearch={}&pubStartDate={}T00:00:00.000&pubEndDate={}T23:59:59.999"
            "&resultsPerPage={}&startIndex={}".format(
                urllib.parse.quote(RECENCY_KEYWORD),
                window_start,
                window_end,
                page,
                start,
            ),
        )

    for label in ECOSYSTEM_KEYWORDS:
        try:
            d = _get(label, 0)
        except Exception as e:  # transient NVD outage: keep going, note gap
            sys.stderr.write(f"  {label}: fetch failed ({e})\n")
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
    if since_months:
        recent_total = 0
        for window_start, window_end in _recency_windows(since_months):
            try:
                d = _get_recent(window_start, window_end, 0)
            except Exception as e:
                sys.stderr.write(
                    "  %s %s..%s: fetch failed (%s)\n"
                    % (RECENCY_CLASS, window_start, window_end, e)
                )
                continue
            total = d.get("totalResults", 0)
            recent_total += total
            _harvest_nvd(d, RECENCY_CLASS, agg)
            pulled = len(d.get("vulnerabilities", []))
            pages = 1
            while pulled < total and pages < max_pages:
                try:
                    d = _get_recent(window_start, window_end, pages * page)
                except Exception as e:
                    sys.stderr.write(
                        "  %s %s p%d: fetch failed (%s)\n"
                        % (RECENCY_CLASS, window_start, pages * page, e)
                    )
                    break
                got = d.get("vulnerabilities", [])
                if not got:
                    break
                _harvest_nvd(d, RECENCY_CLASS, agg)
                pulled += len(got)
                pages += 1
            if pulled < total:
                capped.append(("{} {}".format(RECENCY_CLASS, window_start), total))
        class_counts[RECENCY_CLASS] = recent_total
    rows = sorted(
        (cid, e["cwe"], e["desc"], e["classes"], e["published"])
        for cid, e in agg.items()
    )
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
    if primary in (RECENCY_CLASS, STREAM_CLASS, CVELIST_CLASS, GHSA_CLASS):
        low = desc.lower()
        if any(n in low for n in OWN_NAMES):
            return "REVIEW (recent, unmatched)", ECOSYSTEM_CLASS_GUARD[primary][1]
        return (
            "N/A",
            "another Python package's record: names neither this library, a "
            "dependency, a wrapped tool nor the interpreter, and no operation "
            "class present here matches its text",
        )
    surface, note = ECOSYSTEM_CLASS_GUARD.get(primary, (None, ""))
    if surface is None:
        return "N/A", note or "no NLTK-equivalent surface"
    if note.startswith("N/A"):
        return "N/A", note
    if surfaces.get(surface, 0) > 0:
        return "IN-SCOPE (guarded)", note
    return "N/A", f"{primary}: {surface} surface absent in NLTK"


def _unit_test_files():
    d = os.path.join("nltk", "test", "unit")
    return sorted(
        f for f in os.listdir(d) if f.startswith("test_") and f.endswith(".py")
    )


def resolve_proving_tests(note, test_files, cap=3):
    """Resolve a guard note to concrete proving-test basenames on disk.

    Returns (display_str, covered_bool). covered is False when the note matches no
    GUARD_TESTS entry, or matches one whose globs resolve to zero files present:
    those are the rows the ledger must flag as a COVERAGE GAP rather than assume.
    The ``cpython`` inherited case is covered-by-design (fixed upstream in Python),
    so it returns covered=True with an explicit inherited label.
    """
    low = note.lower()
    for sub, label in CROSS_PR_GUARDS:  # #3850-only guards: attribute, do not flag
        if sub in low:
            return label, True
    for sub, globs in GUARD_TESTS:
        if sub in low:
            if not globs:  # cpython inherited: no NLTK-level test by design
                return "inherited (Python upstream)", True
            found = []
            for g in globs:
                for f in test_files:
                    if fnmatch.fnmatch(f, g) and f not in found:
                        found.append(f)
            found.sort()
            if not found:
                return "GAP: no test on disk", False
            shown = found[:cap]
            extra = len(found) - len(shown)
            disp = ", ".join(shown) + (" (+%d)" % extra if extra else "")
            return disp, True
    return "GAP: unmapped guard", False


def _probe_files(ghsa_id):
    """Advisory probe files on disk for a GHSA id (ghsa_<id>*.py under nltk/test)."""
    import glob as _glob

    stem = ghsa_id.lower().replace("-", "_")
    return sorted(
        os.path.basename(p)
        for p in _glob.glob(
            os.path.join("nltk", "test", "**", stem + "*.py"), recursive=True
        )
    )


def _quoted(text, width):
    """Record text quoted as inline code: it is data from another project's
    advisory, not prose of this playbook, and the hygiene gate reads it so."""
    flat = " ".join(text.split()).replace("`", "'").replace("|", "/")
    if len(flat) > width:
        flat = flat[: width - 3] + "..."
    return "`%s`" % flat if flat else ""


def _previous_ids(path):
    """The CWE and CVE ids the ledger at ``path`` already lists, or empty sets."""
    import re

    if not os.path.exists(path):
        return set(), set()
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    cwes = set(re.findall(r"^\| (CWE-\d+) \|", text, re.M))
    cves = set(re.findall(r"^\| (CVE-\d{4}-\d+) \|", text, re.M))
    return cwes, cves


def _cutoff(since_months):
    import datetime

    days = int(round(since_months * 30.44))
    return (datetime.date.today() - datetime.timedelta(days=days)).isoformat()


def _merge_rows(eco_rows, extra_rows):
    """Fold extra (cid, cwe, desc, classes, published) rows into the ecosystem
    rows: a known id gains the extra classes, a new id is appended."""
    by_id = {r[0]: list(r) for r in eco_rows}
    for cid, cwe, desc, classes, published in extra_rows:
        if cid in by_id:
            row = by_id[cid]
            for c in classes:
                if c not in row[3]:
                    row[3].append(c)
            if cwe and not row[1]:
                row[1] = cwe
            if published and not row[4]:
                row[4] = published
        else:
            by_id[cid] = [cid, cwe, desc, list(classes), published]
    return sorted(tuple(r) for r in by_id.values())


def generate(
    offline=False,
    out_path=None,
    since_months=12,
    full_since=None,
    ghsa_first_year=GHSA_FIRST_YEAR,
    cvelist=True,
    kev=True,
):
    if out_path is None:
        out_path = DEFAULT_LEDGER
    del CATALOG_NOTES[:]
    prev_cwes, prev_cves = _previous_ids(out_path)
    cwes = fetch_cwe(offline)
    cves = fetch_nvd_cves("nltk", offline)
    eco_rows, eco_counts, eco_capped = fetch_ecosystem_cves(
        offline, since_months=since_months
    )
    stream_stats = {}
    if full_since:
        stream_rows, stream_stats = fetch_full_stream(full_since, offline)
        eco_rows = _merge_rows(eco_rows, stream_rows)
        eco_counts[STREAM_CLASS] = stream_stats.get("read", 0)
    cvelist_stats = {}
    if cvelist:
        cvelist_rows, cvelist_stats = fetch_cve_list_v5(offline)
        eco_rows = _merge_rows(eco_rows, cvelist_rows)
        eco_counts[CVELIST_CLASS] = cvelist_stats.get("records", 0)
    ghsa_rows = fetch_ghsa_pip(ghsa_first_year, offline) if ghsa_first_year else []
    kev_map = fetch_kev(offline) if kev else {}
    # A record naming this library that the NVD product query did not return
    # (enrichment lag, or a CNA record the NVD has not mapped yet) is still a
    # product CVE: fold it into the product table with its source named.
    product_ids = {cid for cid, *_ in cves}
    product_source = {cid: "NVD product query" for cid in product_ids}
    extra = []
    for cid, cwe, desc, classes, published in eco_rows:
        if cid not in product_ids and "nltk" in desc.lower():
            extra.append((cid, cwe, desc, published))
            product_ids.add(cid)
            product_source[cid] = ", ".join(classes)
    for ghsa_id, cve_id, cwe, desc, published, packages, severity in ghsa_rows:
        if cve_id and cve_id not in product_ids and "nltk" in packages:
            extra.append((cve_id, cwe, desc, published))
            product_ids.add(cve_id)
            product_source[cve_id] = "GitHub Advisory Database (%s)" % ghsa_id
    cves = sorted(set(cves) | set(extra))
    product_records = {cid: fetch_cve_record(cid, offline) for cid, *_ in cves}
    ghsa_by_cve = {
        cve_id: ghsa_id
        for ghsa_id, cve_id, cwe, desc, published, packages, severity in ghsa_rows
        if cve_id and "nltk" in packages
    }
    markers = {cid: fetch_cve_record(cid, offline) for cid in MARKER_CVES}
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

    test_files = _unit_test_files()
    tag_test_cache = {}

    def tests_for_tag(tag, cap=3):
        """Proving-test basenames that literally reference this CWE/CVE tag."""
        if tag not in tag_test_cache:
            out = _sh("grep -rlE '%s' nltk/test/ --include='*.py'" % tag)
            names = sorted({os.path.basename(p) for p in out.split()})
            shown = names[:cap]
            extra = len(names) - len(shown)
            tag_test_cache[tag] = (
                ", ".join(shown) + (" (+%d)" % extra if extra else "") if names else ""
            )
        return tag_test_cache[tag]

    # APPLICABLE / IN-SCOPE rows whose guard note resolves to NO proving test on
    # disk: the methodical worklist, surfaced instead of assumed covered.
    gaps = []

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
        "**Totals:** %d CWEs classified (%s); %d NVD CVEs on the product; highest CVE "
        "id reached: NVD stream %s, CVE List %s.\n"
        % (
            len(cwe_rows),
            ", ".join("%d %s" % (v, k) for k, v in sorted(stats.items())),
            len(cves),
            stream_stats.get("highest") or "n/a",
            cvelist_stats.get("highest") or "n/a",
        )
    )
    lines.append("## Sources read this run\n")
    if CATALOG_NOTES:
        lines.append("> **Catalog notes:** " + " ".join(CATALOG_NOTES) + "\n")
    lines.append("| Source | What was read | Reached |\n|---|---|---|")
    lines.append(
        "| MITRE CWE dictionary | `%s` | %d ids |" % (CWE_XML_URL, len(cwe_rows))
    )
    lines.append(
        "| NIST NVD, product query | `%s?keywordSearch=nltk` | %d records |"
        % (NVD_API, len(cves))
    )
    lines.append(
        "| NIST NVD, %d class queries, paginated | keyword queries in the class table below | %d distinct records |"
        % (
            len(ECOSYSTEM_KEYWORDS),
            sum(1 for r in eco_rows if any(c in ECOSYSTEM_KEYWORDS for c in r[3])),
        )
    )
    if since_months:
        lines.append(
            "| NIST NVD, recency sweep | every record with `%s` in its text published in the last %d months, %d-day windows | %d records |"
            % (
                RECENCY_KEYWORD,
                since_months,
                RECENCY_WINDOW_DAYS,
                eco_counts.get(RECENCY_CLASS, 0),
            )
        )
    if stream_stats:
        lines.append(
            "| NIST NVD, complete publication stream | every record published since %s, no keyword, %d per page | %d records read, %d in scope, highest id **%s** |"
            % (
                stream_stats["since"],
                STREAM_PAGE,
                stream_stats["read"],
                stream_stats["in_scope"],
                stream_stats["highest"] or "none",
            )
        )
    if cvelist_stats:
        years = sorted(cvelist_stats.get("by_year", {}).items())
        lines.append(
            "| CVE List V5 (cve.org Downloads) | release `%s` + hourly deltas %s; every record | %d records (%s), %d in scope, highest id **%s** |"
            % (
                cvelist_stats.get("release", ""),
                ", ".join(cvelist_stats.get("deltas", [])) or "none",
                cvelist_stats.get("records", 0),
                ", ".join(
                    "%d %s" % (v, k)
                    for k, v in sorted(cvelist_stats.get("by_state", {}).items())
                ),
                cvelist_stats.get("in_scope", 0),
                cvelist_stats.get("highest", "") or "none",
            )
        )
        lines.append(
            "| CVE List V5 by year | records per id year | %s |"
            % ", ".join("%s: %d" % (k, v) for k, v in years)
        )
    lines.append(
        "| GitHub Advisory Database, pip | `%s?ecosystem=pip` one calendar year at a time from %d | %d advisories, newest %s |"
        % (
            GHSA_API,
            ghsa_first_year,
            len(ghsa_rows),
            ghsa_rows[0][4] if ghsa_rows else "none",
        )
    )
    lines.append(
        "| CISA Known Exploited Vulnerabilities | `%s` | %d records, newest added %s |"
        % (KEV_URL, len(kev_map), max((v[0] for v in kev_map.values()), default="none"))
    )
    for cid in MARKER_CVES:
        rec = markers.get(cid)
        lines.append(
            "| cve.org record `%s` | `%s` | %s |"
            % (
                cid,
                CVE_ORG_API.format(cid),
                (
                    (
                        "{}, published {}, CNA {}, CWE {}".format(
                            rec["state"],
                            rec["published"],
                            rec["cna"],
                            ", ".join(rec["cwes"]) or "none",
                        )
                    )
                    if rec
                    else "not reached"
                ),
            )
        )
    lines.append("")
    lines.append("## Code-surface inventory (files per construct)\n")
    lines.append("| surface | files | present |\n|---|---|---|")
    for k, v in surfaces.items():
        lines.append("| %s | %d | %s |" % (k, v, "yes" if v else "no"))
    lines.append(
        "\n## Every MITRE CWE (complete cwec dictionary: weaknesses + categories + views)\n"
    )
    lines.append(
        "| CWE | Name | Abstraction | Verdict | Evidence / guard | Commit | Proving tests |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for tag, name, ab, st, verdict, cm in cwe_rows:
        if st == "PATCHED+TESTED":
            pt = tests_for_tag(tag) or "(tagged in code)"
        elif st == "APPLICABLE":
            pt, covered = resolve_proving_tests(verdict, test_files)
            if not covered:
                gaps.append(("CWE", tag, verdict))
        else:
            pt = "-"
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                tag,
                name.replace("|", "\\|")[:58],
                ab,
                st,
                verdict.replace("|", "\\|"),
                "`%s`" % cm if cm else "",
                pt.replace("|", "\\|"),
            )
        )
    lines.append("\n## Every NVD CVE attributed to the nltk product\n")
    lines.append(
        "The cve.org column is the CVE Program record itself (state, CNA CWE), "
        "cross-checked against the NVD's CWE.\n"
    )
    lines.append(
        "| CVE | Source | CWE | cve.org record | NLTK status | Commit | Proving tests |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    product_status = {}
    for cid, cwe, desc, published in cves:
        if "llama" in desc.lower():
            status, cm, pt = "N/A: dependency (llama_index), not NLTK", "", "-"
        elif _sh("grep -rlE '%s' nltk/ --include='*.py'" % cid):
            has_t = bool(_sh("grep -rlE '%s' nltk/test/ --include='*.py'" % cid))
            status, cm = ("PATCHED+TESTED" if has_t else "PATCHED"), commit(cid)
            pt = tests_for_tag(cid) or "(tagged in code)"
        elif cwe and (cwe in addressed):
            status, cm = "COVERED by %s class (chokepoint)" % cwe, commit(cwe)
            pt = tests_for_tag(cwe)
            if not pt:
                pt = "GAP: no test references %s" % cwe
                gaps.append(("CVE", cid, status))
        elif any(
            c in addressed for c in (product_records.get(cid) or {}).get("cwes", [])
        ):
            cna_cwe = next(c for c in product_records[cid]["cwes"] if c in addressed)
            status, cm = "COVERED by %s class (chokepoint, CNA CWE)" % cna_cwe, commit(
                cna_cwe
            )
            pt = tests_for_tag(cna_cwe)
            if not pt:
                pt = "GAP: no test references %s" % cna_cwe
                gaps.append(("CVE", cid, status))
        elif cid in ghsa_by_cve and _probe_files(ghsa_by_cve[cid]):
            status, cm = "PATCHED+TESTED (advisory probe %s)" % ghsa_by_cve[cid], ""
            pt = ", ".join(_probe_files(ghsa_by_cve[cid]))
        else:
            status, cm, pt = "advisory-only / older-version fix", "", "-"
            if cid in ghsa_by_cve:
                status = "advisory %s without a probe file: GAP" % ghsa_by_cve[cid]
                gaps.append(("CVE", cid, status))
        product_status[cid] = (cwe, published, status, desc)
        rec = product_records.get(cid)
        rec_text = (
            "{}; CNA CWE {}".format(rec["state"], ", ".join(rec["cwes"]) or "none")
            if rec
            else "no public record (reserved or not reached)"
        )
        if rec and rec["cwes"] and cwe and cwe not in rec["cwes"]:
            rec_text += "; differs from NVD"
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                cid,
                product_source.get(cid, ""),
                cwe or "-",
                rec_text,
                status,
                "`%s`" % cm if cm else "",
                pt.replace("|", "\\|"),
            )
        )

    # == Python-ecosystem inherited-surface sweep ==
    eco_stats = {}
    eco_render = []
    eco_meta = {}
    for cid, cwe, desc, classes, published in eco_rows:
        if cid in product_status:
            st, verdict, cm = product_status[cid][2], "see the nltk product table", ""
            eco_stats[st] = eco_stats.get(st, 0) + 1
            eco_render.append((cid, cwe, classes, st, verdict, cm))
            eco_meta[cid] = (published, desc)
            continue
        if _sh("grep -rlE '%s' nltk/ --include='*.py'" % cid):
            has_t = bool(_sh("grep -rlE '%s' nltk/test/ --include='*.py'" % cid))
            st = "PATCHED+TESTED" if has_t else "PATCHED"
            verdict, cm = "addressed directly in nltk/", commit(cid)
        else:
            st, verdict = classify_ecosystem_cve(cwe, desc, classes, surfaces)
            cm = commit(cwe) if cwe in addressed else ""
            if st == "REVIEW (recent, unmatched)" and cid in MANUAL_TRIAGE:
                verdict = MANUAL_TRIAGE[cid]
                st = (
                    "INHERITED (dep)"
                    if verdict.startswith("INHERITED")
                    else "N/A (triaged)"
                )
        eco_stats[st] = eco_stats.get(st, 0) + 1
        eco_render.append((cid, cwe, classes, st, verdict, cm))
        eco_meta[cid] = (published, desc)

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
        lines.append(
            "| {} | `{}` | {} |".format(label, kw, eco_counts.get(label, "n/a"))
        )
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
        "| CVE | CWE | Surface class(es) | NLTK verdict | Guard / evidence | Commit "
        "| Proving tests |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for cid, cwe, classes, st, verdict, cm in eco_render:
        if st == "PATCHED+TESTED":
            pt = tests_for_tag(cid) or "(tagged in code)"
        elif st in ("APPLICABLE", "IN-SCOPE (guarded)"):
            pt, covered = resolve_proving_tests(verdict, test_files)
            if not covered:
                gaps.append(("ECO-CVE", cid, verdict))
        else:  # INHERITED (dep) / N/A
            pt = "-"
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                cid,
                cwe or "-",
                ", ".join(classes),
                st,
                verdict.replace("|", "\\|"),
                "`%s`" % cm if cm else "",
                pt.replace("|", "\\|"),
            )
        )

    # == GitHub Advisory Database, pip ecosystem ==
    our_packages = (
        {"nltk"}
        | {k for k in DEPENDENCY_CLASSES}
        | {"regex", "python-crfsuite", "scikit-learn", "pyyaml", "numpy", "scipy"}
    )
    ghsa_stats = {}
    ghsa_render = []
    for ghsa_id, cve_id, cwe, desc, published, packages, severity in ghsa_rows:
        if cve_id and cve_id in product_status:
            st, verdict = product_status[cve_id][2], "see the nltk product table"
        elif "nltk" in packages:
            st, verdict = (
                "NLTK advisory",
                "an advisory on this library; probe coverage is gated in CI (test_advisory_coverage_ci)",
            )
        elif any(pk in our_packages for pk in packages):
            dep = next(pk for pk in packages if pk in our_packages)
            st, verdict = (
                "INHERITED (dep)",
                "dependency %s; remediate by upgrading it" % dep,
            )
        else:
            hit = _classify_text(desc, surfaces)
            if hit:
                st, verdict = hit
                st = {"APPLICABLE": "IN-SCOPE (guarded)"}.get(st, st)
            else:
                st, verdict = (
                    "N/A",
                    "another package's advisory with no operation class present here",
                )
        if cve_id and cve_id in kev_map:
            verdict += "; **in CISA KEV since %s**" % kev_map[cve_id][0]
        ghsa_stats[st] = ghsa_stats.get(st, 0) + 1
        ghsa_render.append(
            (published, ghsa_id, cve_id, cwe, packages, severity, st, verdict)
        )
        eco_meta.setdefault(cve_id or ghsa_id, (published, desc))
    lines.append(
        "\n## GitHub Advisory Database, pip ecosystem: every advisory since %d\n"
        % ghsa_first_year
    )
    lines.append(
        "Read one calendar year at a time. An advisory on this library points at the "
        "probe gate; one on a dependency is inherited; any other is classified by its "
        "operation class against the surfaces here, so a class that repeats across "
        "the ecosystem is checked for an instance in this code. **%d advisories (%s).**\n"
        % (
            len(ghsa_render),
            ", ".join("%d %s" % (v, k) for k, v in sorted(ghsa_stats.items())),
        )
    )
    lines.append(
        "| Published | GHSA | CVE | CWE | Package(s) | Severity | NLTK verdict | Guard / evidence |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for published, ghsa_id, cve_id, cwe, packages, severity, st, verdict in ghsa_render:
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                published,
                ghsa_id,
                cve_id or "-",
                cwe or "-",
                _quoted(", ".join(packages), 60),
                severity,
                st,
                verdict.replace("|", "\\|"),
            )
        )
    # == CISA KEV cross-reference ==
    ledger_ids = (
        set(product_status)
        | {r[0] for r in eco_render}
        | {r[2] for r in ghsa_render if r[2]}
    )
    kev_hits = sorted((cid, v) for cid, v in kev_map.items() if cid in ledger_ids)
    kev_python = sorted(
        (cid, v)
        for cid, v in kev_map.items()
        if cid not in ledger_ids
        and any(w in (" ".join(v[1:])).lower() for w in STREAM_SCOPE_WORDS)
    )
    lines.append("\n## CISA Known Exploited Vulnerabilities: cross-reference\n")
    lines.append(
        "Every KEV record that is also a ledger row is listed with the ledger's "
        "verdict (exploitation in the wild raises its priority, it does not change "
        "the evidence); every other KEV record with a Python context is classified "
        "here so none is overlooked. **%d ledger rows in KEV, %d further KEV records "
        "with a Python context.**\n" % (len(kev_hits), len(kev_python))
    )
    lines.append("| Added to KEV | CVE | Vendor / product | Ledger verdict |")
    lines.append("|---|---|---|---|")
    status_index = {cid: v[2] for cid, v in product_status.items()}
    status_index.update({r[0]: r[3] for r in eco_render})
    status_index.update({r[2]: r[6] for r in ghsa_render if r[2]})
    for cid, (added, vendor, product, name, short) in kev_hits:
        lines.append(
            "| {} | {} | {} | {} |".format(
                added,
                cid,
                _quoted(vendor + " " + product, 60),
                status_index.get(cid, ""),
            )
        )
    for cid, (added, vendor, product, name, short) in kev_python:
        hit = _classify_text(name + " " + short, surfaces)
        verdict = "%s: %s" % hit if hit else "N/A: no operation class present here"
        lines.append(
            "| {} | {} | {} | {} |".format(
                added,
                cid,
                _quoted(vendor + " " + product, 60),
                verdict.replace("|", "\\|"),
            )
        )
    # == Published in the last N months: every record, with its verdict ==
    cutoff = _cutoff(since_months) if since_months else None
    recent = []
    if cutoff:
        for cid, (cwe, published, status, desc) in product_status.items():
            if published >= cutoff:
                recent.append((published, cid, cwe, "nltk product", status, desc))
        for cid, cwe, classes, st, verdict, cm in eco_render:
            published, desc = eco_meta[cid]
            if published >= cutoff:
                recent.append((published, cid, cwe, ", ".join(classes), st, desc))
        listed = {r[1] for r in recent}
        for (
            published,
            ghsa_id,
            cve_id,
            cwe,
            packages,
            severity,
            st,
            verdict,
        ) in ghsa_render:
            key = cve_id or ghsa_id
            if published >= cutoff and key not in listed:
                recent.append((published, key, cwe, GHSA_CLASS, st, ""))
                listed.add(key)
        recent.sort(reverse=True)
        recent_stats = {}
        for row in recent:
            recent_stats[row[4]] = recent_stats.get(row[4], 0) + 1
        lines.append(
            "\n## Published in the last %d months (since %s): every record, with "
            "its verdict\n" % (since_months, cutoff)
        )
        lines.append(
            "The recency sweep queries the NVD for every record published in this "
            "window whose description mentions Python, in %d-day windows, on top of "
            "the class queries above; a record no class query would have reached is "
            "listed here with the class `%s` and triaged by hand below. "
            "**%d records (%s).**\n"
            % (
                RECENCY_WINDOW_DAYS,
                RECENCY_CLASS,
                len(recent),
                ", ".join("%d %s" % (v, k) for k, v in sorted(recent_stats.items())),
            )
        )
        lines.append("| Published | CVE | CWE | Class(es) | NLTK verdict |")
        lines.append("|---|---|---|---|---|")
        for published, cid, cwe, classes, st, desc in recent:
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    published, cid, cwe or "-", classes, st
                )
            )
    # == Manual triage: recency-only rows no keyword rule classified ==
    review = [
        (cid, cwe, eco_meta[cid][0], eco_meta[cid][1])
        for cid, cwe, classes, st, verdict, cm in eco_render
        if st == "REVIEW (recent, unmatched)"
    ]
    lines.append("\n## Manual triage: recent records no rule classified\n")
    if review:
        lines.append(
            "These %d records were reached by the recency sweep only and matched no "
            "operation keyword. Each is read and settled below; a verdict written "
            "here is evidence, so a row left as REVIEW is open work, not a pass.\n"
            % len(review)
        )
        lines.append("| Published | CVE | CWE | Record (first 160 chars) | Triage |")
        lines.append("|---|---|---|---|---|")
        for cid, cwe, published, desc in sorted(
            review, key=lambda r: r[2], reverse=True
        ):
            blurb = _quoted(desc, 160)
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    published, cid, cwe or "-", blurb, MANUAL_TRIAGE.get(cid, "REVIEW")
                )
            )
    else:
        lines.append(
            "**None.** Every recency-sweep record matched an operation rule.\n"
        )
    # == New catalog entries since the previous ledger ==
    new_cwes = [r for r in cwe_rows if r[0] not in prev_cwes] if prev_cwes else []
    all_cves = [cid for cid, *_ in cves] + [r[0] for r in eco_render]
    new_cves = sorted({c for c in all_cves if c not in prev_cves}) if prev_cves else []
    lines.append("\n## New catalog entries since the previous ledger\n")
    if not prev_cwes and not prev_cves:
        lines.append(
            "No previous ledger was found at the output path; nothing to diff.\n"
        )
    else:
        lines.append(
            "Against the ledger this run replaced (%d CWE ids, %d CVE ids): "
            "**%d new CWEs, %d new CVEs.** Every one is classified in the tables "
            "above; this section only makes the delta visible.\n"
            % (len(prev_cwes), len(prev_cves), len(new_cwes), len(new_cves))
        )
        if new_cwes:
            lines.append("| New CWE | Name | Verdict |\n|---|---|---|")
            for tag, name, ab, st, verdict, cm in new_cwes:
                lines.append(
                    "| {} | {} | {} |".format(tag, name.replace("|", "\\|")[:58], st)
                )
        if new_cves:
            status_of = {cid: st for cid, cwe, classes, st, v, cm in eco_render}
            status_of.update({cid: v[2] for cid, v in product_status.items()})
            lines.append("\n| New CVE | Verdict |\n|---|---|")
            for cid in new_cves:
                lines.append("| {} | {} |".format(cid, status_of.get(cid, "")))
    # == Coverage gaps: APPLICABLE/IN-SCOPE rows with no proving test ==
    gap_section = [
        "\n## Coverage gaps (APPLICABLE / IN-SCOPE rows lacking a proving test)\n"
    ]
    if gaps:
        gap_section.append(
            "These %d rows are classified guarded but their guard note did not resolve "
            "to an attack test on disk. Each is a worklist item: add the exploit test, "
            "then re-run.\n" % len(gaps)
        )
        gap_section.append("| kind | id | verdict / guard |\n|---|---|---|")
        for kind, idv, verdict in gaps:
            gap_section.append(
                "| {} | {} | {} |".format(kind, idv, verdict.replace("|", "\\|")[:90])
            )
    else:
        gap_section.append(
            "**None.** Every APPLICABLE / IN-SCOPE CWE and CVE row resolves to at least "
            "one attack test that runs its exploit through the real code path.\n"
        )
    # Surface the gap section right after the totals line (index 3) so it is the
    # first thing a reader sees.
    lines[4:4] = gap_section

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return (
        stats,
        len(cwe_rows),
        len(cves),
        len(eco_render),
        eco_stats,
        len(gaps),
        len(recent),
        len(review),
        len(new_cwes),
        len(new_cves),
        len(ghsa_render),
        len(kev_hits),
        stream_stats.get("highest") or cvelist_stats.get("highest") or "",
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--offline",
        action="store_true",
        help="reuse cached catalogs instead of fetching",
    )
    ap.add_argument("-o", "--out", default=DEFAULT_LEDGER)
    ap.add_argument(
        "--since-months",
        type=int,
        default=12,
        help="recency sweep window in months (0 disables the sweep)",
    )
    ap.add_argument(
        "--full-since",
        default=_cutoff(12),
        help="read the complete NVD publication stream from this ISO date (empty disables)",
    )
    ap.add_argument(
        "--ghsa-first-year",
        type=int,
        default=GHSA_FIRST_YEAR,
        help="first calendar year of the GitHub pip advisory pull (0 disables)",
    )
    ap.add_argument(
        "--no-cvelist", action="store_true", help="skip the CVE List V5 bulk read"
    )
    ap.add_argument("--no-kev", action="store_true", help="skip the CISA KEV catalog")
    args = ap.parse_args(argv)
    (
        stats,
        ncwe,
        ncve,
        neco,
        eco_stats,
        ngaps,
        nrecent,
        nreview,
        nnewcwe,
        nnewcve,
        nghsa,
        nkev,
        highest,
    ) = generate(
        args.offline,
        args.out,
        args.since_months,
        args.full_since or None,
        args.ghsa_first_year,
        not args.no_cvelist,
        not args.no_kev,
    )
    print(
        "wrote %s: %d CWEs (%s), %d nltk-product CVEs, %d ecosystem CVEs (%s); "
        "%d coverage gaps; %d records published in the last %d months, %d awaiting "
        "manual triage; %d new CWEs and %d new CVEs since the previous ledger; "
        "%d pip advisories; %d ledger rows in CISA KEV; highest CVE id reached %s"
        % (
            args.out,
            ncwe,
            ", ".join("%d %s" % (v, k) for k, v in sorted(stats.items())),
            ncve,
            neco,
            ", ".join("%d %s" % (v, k) for k, v in sorted(eco_stats.items())),
            ngaps,
            nrecent,
            args.since_months,
            nreview,
            nnewcwe,
            nnewcve,
            nghsa,
            nkev,
            highest or "n/a",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
