# Security policy for the 3.4 maintenance line

This branch is the Python 2.7 maintenance line of NLTK. Release 3.4.5
(August 2019) was the last NLTK that ran on Python 2.7; releases 3.5 and
later dropped Python 2 and, because 3.5 carries no `Requires-Python`
metadata, a plain `pip install nltk` on Python 2.7 resolves to 3.5 and
fails on import. Users on 2.7 therefore pin 3.4.5, which predates every
security fix of the 3.10 line.

Release 3.4.6 applies the vulnerability classes fixed in the 3.10 line to
this code, in place, with one regression test per class
(`nltk/test/unit/test_security_backport.py`, run on Python 2.7 and 3).

## What is fixed

- **Deserialisation (CWE-502).** `nltk.data.load` rebuilds a pickle only
  from NLTK's own resource classes and a few containers; YAML goes through
  the safe loader; every loaded body is bounded. The same restricted
  unpickler is used by the corpus pickle view, the transition parser, the
  tbl and chart-parser demos, and the wordnet browser no longer puts a
  pickle in its links.
- **Path traversal and links (CWE-22, CWE-59, CWE-73).** `nltk.data.find`
  and `FileSystemPathPointer.join` refuse a name that leaves its data root
  once links are resolved. Paths handed to external tools (Weka,
  MaltParser, the transition parser, BLLIP, the tbl demo) may not step
  upward, be a link, or be a hardlinked write target.
- **Downloads (CWE-494, CWE-918, CWE-400; CVE-2026-12261).** The
  downloader fetches over http(s) only, verifies the indexed size and
  checksum before an archive takes the package's name, validates every
  member (Zip-Slip, NUL bytes, planted links, package ownership) before
  extraction, and refuses an archive declaring more than 8 GiB unzipped.
- **Code injection (CWE-94, CWE-74, CWE-78).** The string reader decodes a
  literal instead of evaluating it; TextTiling, the collocations demo and
  the semantics demo look names up instead of `eval`/`exec`; decorator
  signatures are fenced before their eval (CVE-2026-14727); Prover9 input
  refuses list directives (CVE-2026-14709); Boxer no longer runs a shell.
- **Untrusted search path and arguments (CWE-426, CWE-88).** Every spawned
  binary (java, prover9, mace4, candc, boxer, megam, tadm, dot,
  ghostscript, senna, hunpos, repp, MaltParser) must sit where only this
  account or root can write; a bare name in the working directory is not a
  tool; JVM options come from an allowlist (CVE-2026-12841); the Stanford
  parser's model jar is last on the classpath (CVE-2026-14582).
- **Resource exhaustion (CWE-770, CWE-407, CWE-1333, CWE-674).** Bounds or
  linear algorithms for the confusion matrix (CVE-2026-12839), valuation
  parsing and model checking (CVE-2026-12890, CVE-2026-12840), anaphora
  resolution (CVE-2026-12873), parse-tree extraction (CVE-2026-12886),
  variable renaming (CVE-2026-12919), string distances (CVE-2026-12926),
  ngram counting (CVE-2026-12928), METEOR (CVE-2026-12929), Cistem
  (CVE-2026-12868), the Hungarian stemmer (CVE-2026-14597), alignments
  (CVE-2026-12837), Chomsky normal form and the CCG lexicon parser.
- **XML (CWE-776, CWE-611).** Every XML document is parsed by a parser
  that refuses entity declarations and external references and bounds the
  tree (defusedxml when installed).
- **Web, CSV, temp files (CWE-79, CWE-306, CWE-284, CWE-1236, CWE-377).**
  The wordnet browser binds to the loopback interface, needs a per-process
  token to shut down and escapes request text; CSV exports neutralise
  formula leads; the tree renderer and the named-entity trainer use
  private temporary directories.

## What is not fixed, and cannot be

Python 2.7 is end of life. Its interpreter, `ssl`, `expat`, `zlib` and
`sqlite3` carry unpatched vulnerabilities that no change in NLTK can close.
This release makes NLTK's own input handling safe on 2.7; it does not make
a Python 2.7 system safe. Use NLTK 3.10.4 or newer on a current Python
wherever that is possible, and keep Python 2.7 out of sandboxes that run
untrusted code.

Deliberately not carried over from the 3.10 line, because they are either
defence in depth or require its guard framework: the sandboxing of corpus
reader roots to the data directories, terminal-escape sanitisation of
printed output, and wall-clock timeouts on regular-expression matching
(the pathological patterns themselves are rewritten here).

## Reporting

Report a vulnerability in this line the same way as for current NLTK:
through the project's GitHub security advisories.
