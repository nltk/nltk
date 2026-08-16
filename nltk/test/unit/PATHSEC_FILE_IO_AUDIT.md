# NLTK file-I/O security audit (GHSA-8mgp-746c-j5xp)

Living checklist of **every** file-I/O sink in NLTK — `open`, `codecs.open`,
`pickle.load`/`dump`, `json.load`/`dump`, `numpy.load`/`save`, model/dataset
save/load, and binary reads — and its containment status against the pathsec
sandbox. Work through it top to bottom; **extend it whenever a new sink is
found**. Do not delete a row — mark it.

## Conventions applied

- **`pathsec.open`** for direct reads/writes of a caller/dataset path (validates
  against the allowed data roots, closes the symlink-swap TOCTOU on write).
- **`validate_path(path, context=…)`** immediately before a path handed to a
  C-extension / JVM / sqlite3 / shelve / matplotlib that `pathsec.open` can't wrap.
- **No guessable `/tmp` defaults** → `pathsec.make_staging_dir(prefix="nltk_…")`
  (private 0700, unpredictable, and registered so its writes pass the sandbox even
  on Linux, where the shared `/tmp` root is untrusted and would otherwise refuse
  our own staging dir). A class with a save method exposes a lazy, reused
  **`save_dir`** property; a module save function returns its dir, annotated `-> str`.
- **`allowlisted_pickle_load`** (exact-globals allowlist) for every untrusted
  pickle; **no** `np.load(allow_pickle=True)` on a caller path.
- Pathsec imports are **hoisted** to module top level.

## Status legend

`GUARDED` routed through pathsec · `EXEMPT` human-in-loop GUI / by-design creds /
fixed packaged resource / subprocess-or-internal-tempfile · `GAP-FIXED` was a real
gap, now closed · `TODO` under audit.

## Checklist

### chunk
| File | Sink | Verdict | Test |
|---|---|---|---|
| chunk/named_entity.py | `Maxent_NE_Chunker.save_params` (+ private `save_dir`) | GAP-FIXED (mkdtemp default, validate before mkdir, returns dir) | test_pathsec_sweep_chunk |
| chunk/named_entity.py | `load_ace_file` reads | GUARDED (pathsec_open) | test_pathsec_sweep_chunk |
| chunk/named_entity.py | deprecated build_model pickle (docstring, dead) | GAP-FIXED (mkdtemp, no /tmp) | — |

### classify
| File | Sink | Verdict | Test |
|---|---|---|---|
| classify/maxent.py | `save_maxent_params` | GAP-FIXED (mkdtemp default, validate, returns dir) | test_pathsec_sweep_classify |
| classify/maxent.py | `load_maxent_params` | GUARDED (open_datafile) | — |
| classify/maxent.py | megam/tadm trainfile/weightfile | EXEMPT (internal mkstemp) | — |
| classify/weka.py | `ARFF_Formatter.write` | GUARDED (pathsec_open) | test_pathsec_sweep_classify |
| classify/weka.py | `__main__` demo /tmp/name.model | GAP-FIXED (mkdtemp) | — |
| classify/{megam,tadm,senna,decisiontree,rte_classify,textcat}.py | model/data I/O | EXEMPT / NO GAP (streams, subprocess pipes, internal mkstemp, fixed corpus resources) | — |

### parse
| File | Sink | Verdict | Test |
|---|---|---|---|
| parse/transitionparser.py | `train` pickle write | GUARDED (pathsec_open) | test_pathsec_sweep_parse |
| parse/transitionparser.py | `parse` pickle read | GUARDED (pathsec_open + **exact-allowlist** unpickler) | test_pickle_allowlist_security |
| parse/malt.py | reads | EXEMPT (internal NamedTemporaryFile / subprocess / PathPointer) | test_pathsec_sweep_parse |
| parse/featurechart.py | `run_profile` `/tmp/profile.out` (profiling helper) | GAP-FIXED (mkdtemp) | — |
| parse/dependencygraph.py | demo `savefig("tree.png")` (fixed CWD name) | GAP-FIXED (mkdtemp) | — |

### tag
| File | Sink | Verdict | Test |
|---|---|---|---|
| tag/perceptron.py | `AveragedPerceptron.save`/`load` | GUARDED (pathsec_open) | test_pathsec |
| tag/perceptron.py | `PerceptronTagger.save_to_json` | GUARDED (validate loc; O_NOFOLLOW dir-fd) | test_pathsec |
| tag/perceptron.py | `load_from_json` | GUARDED (open_datafile) | — |
| tag/crf.py | `set_model_file` / `train` (pycrfsuite native open/write) | GAP-FIXED (validate_path before native hand-off) | test_pathsec_sweep_tag |
| tag/stanford.py | `tag_sents` model path → JVM `-model` | GAP-FIXED (validate_path before java()) | test_pathsec_sweep_tag |
| tag/hunpos.py | `__init__` model path → subprocess argv | GAP-FIXED (validate_path before Popen) | test_pathsec_sweep_tag |
| tag/{senna,brill,sequential,tnt,hmm,mapping}.py | — | NO GAP (in-memory / fixed resource / subprocess) | — |

### tokenize
| File | Sink | Verdict | Test |
|---|---|---|---|
| tokenize/punkt.py | `save_punkt_params` | GAP-FIXED (mkdtemp default, validate, returns dir) | test_pathsec_sweep_tokenize |
| tokenize/punkt.py | `PunktTokenizer.save_params` (+ private `save_dir`) | GAP-FIXED (no /tmp/<lang>) | test_pathsec_sweep_tokenize |
| tokenize/punkt.py | `PunktSentenceTokenizer.dump` | GAP-FIXED (private mkdtemp, not /tmp/punkt.new) | test_pathsec_sweep_tokenize |
| tokenize/punkt.py | `load_punkt_params` | GUARDED (open_datafile) | — |
| tokenize/stanford_segmenter.py | `_sha256sum` read | GUARDED (pathsec_open) | test_pathsec_sweep_tokenize |

### sentiment
| File | Sink | Verdict | Test |
|---|---|---|---|
| sentiment/sentiment_analyzer.py | `save_file` | GUARDED (pathsec_open) | test_pathsec_sweep_chunk |
| sentiment/util.py | `output_markdown`/`json2csv_preprocess`/`parse_tweets_set` (codecs.open) | GUARDED (pathsec_open) | test_pathsec_sweep_sentiment_util |

### sem / tbl / metrics / stem / translate / misc / help
| File | Sink | Verdict | Test |
|---|---|---|---|
| sem/chat80.py | `sqlite3.connect`/`shelve.open`/`label_indivs` | GUARDED (validate_path / pathsec_open) | test_pathsec_sweep_misc |
| tbl/demo.py | pickle write/read, error_output, savefig | GUARDED (pathsec_open / validate_path) | test_pathsec_sweep_misc |
| metrics/agreement.py | `__main__` `-f` read | GUARDED (pathsec_open) | test_pathsec_sweep_misc |
| help.py | `json.load` tagset help | TODO (agent: misc) | test_pathsec_sweep_misc2 |
| stem/, translate/, misc/ | model/data I/O | TODO (agent: misc) | test_pathsec_sweep_misc2 |

### security modules
| File | Sink | Verdict | Test |
|---|---|---|---|
| xmlsec.py | `parse(source)` filename | GUARDED (validate_path; covers defusedxml + fallback) | test_pathsec_sweep_infra |
| pathsec.py | `validate_path` URL-scheme bypass (F2) | GAP-FIXED (anchored-regex reject) | test_pathsec (TestUrlSchemePathBypass) |
| pathsec.py | save default refused on Linux (shared `/tmp` not an allowed root) | GAP-FIXED (`make_staging_dir` registers NLTK's own private 0700 dir; unregistered temp dirs stay refused) | test_pathsec (TestPrivateStagingRegistry) |

### dataset / model loading (data.py + corpus readers) — ATTACKED, no leak
| Load path | Attacks refused | Verdict |
|---|---|---|
| `data.find` | absolute-outside, `../` traversal, `%2f`-encoded traversal | CONTAINED (`_UNSAFE_NO_PROTOCOL_RE` + `_assert_no_encoded_bypass`) |
| `data.load('file://…')` | absolute-outside read | CONTAINED (`_open`→`_secure_open`→`validate_path`) |
| `data.retrieve` | symlink-at-destination **write** escape | CONTAINED (O_NOFOLLOW; target never written) |
| `FileSystemPathPointer.open` / `Gzip…` | absolute-outside, in-root symlink→outside | CONTAINED (validate_path resolves symlink) |
| `StreamBackedCorpusView._open` | bare outside fileid | CONTAINED (`_secure_open`) |
| `CorpusReader.open` / `.__init__` | traversal, absolute, in-root symlink, out-of-sandbox root | CONTAINED (lexical + scoped `required_root` + root validate) |
| WordList/Plaintext/XML/PanLex(sqlite3) readers | symlink escape, bare-string, db symlink | CONTAINED (inherited open / pathsec_open / validate_path) |
| bespoke loaders (crubadan, framenet, toolbox, propbank, nombank, nkjp, bcp47, childes, bnc, semcor, lin, ipipan, pl196x) | read-through | CONTAINED (PathPointer sandbox or validate_path(required_root)) |

19-test attack matrix (absolute/traversal/symlink + negative controls) in
test_pathsec_sweep_dataset_loading.py. No source change needed — already contained.

### deserialization (pickle / json / np) — RCE surface — AUDITED, no gap
| Site | Routing | Verdict |
|---|---|---|
| transitionparser.parse | `allowlisted_pickle_load` (exact globals) + pathsec_open | SAFE |
| data.py `restricted_pickle_load` (dataset .pickle) | `RestrictedUnpickler` (blocks ALL globals) | SAFE |
| wordnet_app `Reference.decode` (untrusted base64 over HTTP) | `RestrictedUnpickler` + shape check | SAFE |
| punkt `punkt_pickle_load` | `allowlisted_pickle_load` (punkt globals) | SAFE |
| all json.load/json.loads (help, data, perceptron, twitter, corpus) | pathsec-guarded file open / string parse (not RCE) | SAFE |
| `np.load`/`numpy.load`/`allow_pickle=True` | **none exist in the tree** | SAFE (n/a) |
| chartparser GUI pickle · tbl/demo cache | warn-only `pickle_load` — interactive / dev-demo, not untrusted dataset | documented residual |
| picklesec shared denylist (scipy.io, sklearn.datasets, numpy call-gadgets, LowLevelCallable) | GAP-FIXED | test_pickle_allowlist_security |

Gadget battery (os.system, subprocess, eval/exec/import, scipy.io.mmwrite, sklearn.datasets.fetch_openml, numpy.load/apply_along_axis, dotted-name sklearn.os.system, live `__reduce__`→os.system) **refused at every site**; legit SVC/Punkt/wordnet/dict loads still succeed. 96 tests in test_pathsec_sweep_deserialization.py.

### documented exemptions (re-verified adversarially — NOT gaps)
| File | Reason | Test |
|---|---|---|
| app/*.py | EXEMPT ✓ every open traced to a Tk `askopenfilename`/`asksaveasfilename` dialog (human in loop); `wordnet_app:138` guarded by exact-literal `if usp == "…Database Info.html"`; `:257` operator-CLI logfile | — |
| twitter/*.py | EXEMPT ✓ by-design `$TWITTER`/`credentials*.txt` reads; output paths are operator ctor params (`subdir`/`fprefix`), no untrusted string reaches them | — |
| draw/util.py | EXEMPT ✓ `print_to_file` filename only from `asksaveasfilename`; no programmatic caller | — |
| downloader.py md5/sha256 reads | EXEMPT ✓ `info.filename` neutralized+validated in constructor (subdir/id/ext all reject `..`/sep); no metadata-steered read; write path is O_NOFOLLOW + `os.replace` | — |
| __init__.py VERSION | fixed `__file__`-relative resource, import-time | — |

## Test matrix (this PR)

`test_pathsec.py` (core F2 + model save/load) · `test_pickle_allowlist_security.py`
(exact allowlist + gadget battery) · `test_pathsec_sweep_{chunk,classify,parse,
tokenize,sentiment_util,misc}.py` · plus (in flight) `…_tag`, `…_classify_extra`,
`…_misc2`, `…_dataset_loading`, `…_deserialization`, `…_exempt_recheck`.

Every attack test uses a genuinely-outside `$HOME` target (never a temp dir — the
private system temp is an allowed root on macOS) with a negative control, and
exercises **ENFORCE on** (refused) vs **off** (baseline) where relevant.
