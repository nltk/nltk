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
- **No guessable `/tmp` defaults** → `tempfile.mkdtemp(prefix="nltk_…")` (private
  0700, unpredictable). A class with a save method exposes a lazy, reused
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

### dataset / model loading (data.py + corpus readers)
| Area | Verdict | Test |
|---|---|---|
| data.py `load`/`retrieve`/`find`/`_open`, `FileSystemPathPointer.open` | TODO (agent: dataset-loading — attack absolute/traversal/symlink, with & without ENFORCE) | test_pathsec_sweep_dataset_loading |
| corpus/reader/*.py `open`/`abspath`/XML/CoNLL/pickle loaders | TODO (agent: dataset-loading) | test_pathsec_sweep_dataset_loading |
| CorpusReader.__init__ root | GUARDED (validate_path on root — verified: outside root → PermissionError under ENFORCE) | test_pathsec_sweep_dataset_loading |

### deserialization (pickle / json / np) — RCE surface
| Area | Verdict | Test |
|---|---|---|
| every `pickle.load` / `np.load(allow_pickle)` / `json.load` tree-wide | TODO (agent: deserialization — gadget battery vs GHSA-x99w/4489/rhp5) | test_pathsec_sweep_deserialization |
| picklesec allowlist shared denylist (scipy.io, sklearn.datasets, numpy call-gadgets) | GAP-FIXED | test_pickle_allowlist_security |

### documented exemptions (re-verified — not gaps)
| File | Reason | Test |
|---|---|---|
| app/*.py | Tk `askopenfilename`/`asksaveasfilename` dialogs (human in loop); literal-guarded `wordnet_app` read; operator-CLI logfile | TODO (agent: exempt-recheck) |
| twitter/*.py | by-design `$TWITTER` / `~/twitter-files` credential + developer-supplied output paths | TODO (agent: exempt-recheck) |
| draw/util.py | `print_to_file` — Tk save dialog / user save destination | TODO (agent: exempt-recheck) |
| downloader.py md5/sha256 reads | download-flow paths already gated (795–805 containment + validated write) | TODO (agent: exempt-recheck) |
| __init__.py VERSION | fixed `__file__`-relative resource, import-time | — |

## Test matrix (this PR)

`test_pathsec.py` (core F2 + model save/load) · `test_pickle_allowlist_security.py`
(exact allowlist + gadget battery) · `test_pathsec_sweep_{chunk,classify,parse,
tokenize,sentiment_util,misc}.py` · plus (in flight) `…_tag`, `…_classify_extra`,
`…_misc2`, `…_dataset_loading`, `…_deserialization`, `…_exempt_recheck`.

Every attack test uses a genuinely-outside `$HOME` target (never a temp dir — the
private system temp is an allowed root on macOS) with a negative control, and
exercises **ENFORCE on** (refused) vs **off** (baseline) where relevant.
