# Output entry-point exploit ledger (terminal + CSV write surface)

Companion to `SECURITY_LEDGER.md` for the output side of the codebase: every
parameter channel of every print/write entry point introduced by the
`nltk.termsec` / `nltk.csvsec` slice (PR #3914) and the sinks it feeds
(PR #3915 and the remaining #3889 slices), checked methodically for known and
unknown exploit classes.

**Automatic re-verification:** `python tools/security_output_audit.py` runs
both passes on demand: an AST inventory of every output sink in the package
(bare vs routed) and a live exploit battery that fires every attack class
below at the real sanitisers (skipped with a notice while the modules are
absent). Its leak detectors are independently derived and self-tested, and
the battery is mutation-verified: neutering either sanitiser in memory makes
probes report LEAK.

Audit method (2026-09-23 sweep): enumerate every parameter channel of every
entry point; for each, name the exploit candidate, probe it EMPIRICALLY
(exploit first, then fix), and record the pinning test. Statuses:
**DEFENDED** (guard + harness pin), **FAIL-CLOSED** (stdlib raises before
harm; pinned where practical), **BY DESIGN** (documented, deliberate),
**PENDING** (future slice).

## Findings of the 2026-09-23 sweep (both were live bypasses, both fixed + pinned in #3914)

1. **QUOTE_NONE structural bypass** (SafeCsvWriter/SafeCsvDictWriter fmtparams
   channel): with `quoting=csv.QUOTE_NONE, escapechar="\\"`, a sanitized
   default-mode cell `"x\n=SUM(A1)"` was written with its PHYSICAL newline in
   the stream (backslash first, newline after), forging a row whose first cell
   is a live formula lead. Fix: `_refuse_unquoted_structure` checks the MERGED
   dialect (fmtparams alone is smuggle-able via a dialect object) and raises
   ValueError at construction unless `single_line=True` (cell data then cannot
   emit a physical newline). Pins: `TestQuoteNoneStructuralGuard`
   (test_csvsec_writer.py). Mutation-verified: neutering the guard in-memory
   leaks the forged row.

2. **Lying str-subclass materialisation bypass**: `str(text)` is NOT a
   materialisation guarantee. A subclass `__str__` returning `self` hands the
   scan an attacker-defined object; `char in allowed` consults the yielded
   char's `__hash__`/reflected `__eq__`, so a 1-char subclass whose buffer is
   ESC but which claims to equal TAB was KEPT and joined into a plain-str
   output containing a live escape (confirmed empirically). Fix: after
   `str(text)`, any str subclass is re-materialised through the unbound
   `str.__str__(text)` C slot, which copies the REAL buffer, consults nothing
   attacker-definable and preserves lone surrogates for the escape pass. The
   single site in `sanitize_terminal` covers `csvsec` too (its cell pipeline
   funnels every value through `sanitize_terminal`). Pins:
   `TestLyingStrSubclassLaundering` (test_termsec_attack_matrix.py).

## A. `sanitize_terminal(text, *, single_line=False)`

| Channel | Exploit candidate | Status | Pin |
|---|---|---|---|
| text: C0/DEL/C1 bytes | CWE-150 live controls | DEFENDED | test_every_dangerous_control_byte_is_escaped |
| text: ESC/CSI/OSC sequences | clear/title/hyperlink/backspace/CR spoof | DEFENDED | test_control_sequences_are_neutralised |
| text: bidi overrides | CVE-2021-42574 Trojan Source | DEFENDED | OVERRIDE_ATTACKS (always escaped) |
| text: unbalanced embeddings/isolates | crossing/LIFO abuse | DEFENDED | MALFORMED_ATTACKS + _bidi_is_balanced |
| text: default ignorables/plane-14/musical/nonchars | invisible smuggle | DEFENDED | UCD-diffed matrix (kept-allowlist ZWJ/VS/FVS/CGJ) |
| text: lone surrogates | UnicodeEncodeError DoS on print | DEFENDED | test_safe_print_does_not_crash_on_lone_surrogate |
| text: huge int object | CVE-2020-10735 render bomb | DEFENDED | TestNumericBombs (unbound int.bit_length, 333k bits) |
| text: `__str__` raising | error-path leak | FAIL-CLOSED | raises before output |
| text: `__str__` returning str SUBCLASS | finding 2 above | DEFENDED | TestLyingStrSubclassLaundering |
| text: subclass fake-clean `__iter__` | hide buffer from scan | DEFENDED | test_fake_clean_iterator_cannot_hide_the_buffer |
| single_line=False keeps \t\n | newline forges a LINE (not row) | BY DESIGN | callers printing one-line values pass single_line=True (#3915 wiring) |
| single_line=True | \t \n escaped, superset strictness | DEFENDED | TestSingleLineMode |
| output identity | returning original object | DEFENDED | always joined; type-is-str pinned |
| idempotence | double-escape corruption | DEFENDED | TestSanitizeIsIdempotent |

## B. `safe_print(*values, sep, end, file, flush, single_line)`

| Channel | Exploit candidate | Status | Pin |
|---|---|---|---|
| values | all of section A | DEFENDED | test_safe_print_sanitises + single_line class |
| sep/end str (incl lying subclass) | smuggle live sequence | DEFENDED | test_safe_print_sanitises_sep_and_end (+ A materialisation) |
| sep/end None | default kept | DEFENDED | test_safe_print_sep_none_keeps_default |
| sep/end non-str object | bypass sanitize | FAIL-CLOSED | print() raises TypeError |
| file= | caller's own sink | BY DESIGN | destination is caller trust, values still sanitized |
| unknown kwargs | smuggle channel | FAIL-CLOSED | print() rejects |

## C. `sanitize_csv_field(value, *, single_line=False)`

| Channel | Exploit candidate | Status | Pin |
|---|---|---|---|
| leads `= + - @ % \| ＝ ＋ － ＠` | CWE-1236 incl CVE-2022-28481, fullwidth | DEFENDED | TestResearchDrivenLeads |
| whitespace-padded lead (tab/NBSP/ideographic) | padded-lead bypass class | DEFENDED | test_whitespace_padded_lead_defused |
| BOM-led formula | ignorable-then-lead | DEFENDED | escaped by A, then lead defused |
| `==SUM(A1)` | strip-once bypass class | DEFENDED | test_double_equals_stays_defused (prefix, never strip) |
| genuine numbers incl `-1,234.56` | overblocking | DEFENDED | TestGroupedNumbers (charset admits no function/DDE) |
| numeric-lead length cap | parse-time burn | DEFENDED | 10_000 cap, TestNumericLeadLengthCap |
| exact int/float/bool/None | type preserved, no smuggle | DEFENDED | exact-type test (`type(value) in`, defeats lying int subclass) |
| lying numeric subclass | isinstance evasion | DEFENDED | EvilInt/Sub/Boom sweep |
| int bomb | render burn | DEFENDED | TestNumericBombs |
| Fraction(-1,2) "-1/2" | lead-shaped non-number | DEFENDED (fail-closed apostrophe) | test_negative_fraction_lead_fails_closed |
| complex/bytes/datetime/Path/Decimal/numpy | per-type gaps | DEFENDED | TestTypeSweepOnePipelineNoBranches |
| mid-cell text | data mangling (pipe rewrite bug class) | BY DESIGN | never rewritten; lead defusal only |

## D. `SafeCsvWriter(fileobj, dialect="excel", *, single_line, **fmtparams)`

| Channel | Exploit candidate | Status | Pin |
|---|---|---|---|
| quoting=QUOTE_NONE (fmtparams OR dialect) | finding 1 above | DEFENDED | TestQuoteNoneStructuralGuard |
| QUOTE_NONE + single_line=True | none: \n escaped in-cell | ALLOWED | test_single_line_legitimises_quote_none |
| QUOTE_MINIMAL/ALL/NONNUMERIC/NOTNULL/STRINGS | newline containment | SAFE | strings always quoted; test_other_quoting_modes_unaffected |
| doublequote=False, no escapechar | quote breakout | FAIL-CLOSED | csv module raises on first quotechar |
| quotechar=None with quoting on | structural off | FAIL-CLOSED | csv module TypeError |
| exotic lineterminator/delimiter | containment change | SAFE | QUOTE_MINIMAL quotes on \r\n regardless |
| writerow(generator) raising mid-row | partial poisoned row | DEFENDED | test_row_iterable_raising_midway_writes_nothing |
| fileobj | caller's sink | BY DESIGN | cells sanitized regardless of destination |

## E. `SafeCsvDictWriter(..., restval, extrasaction, ...)`

| Channel | Exploit candidate | Status | Pin |
|---|---|---|---|
| fieldnames | crafted header = crafted first row | DEFENDED | writeheader sanitizes; TestSafeCsvDictWriter |
| restval | hostile default cell | DEFENDED | test_restval_is_defused |
| extrasaction="ignore" | smuggled extra keys | DEFENDED | test_extrasaction_ignore_passthrough |
| extrasaction="raise" | n/a | FAIL-CLOSED | ValueError on extras |
| row dict keys | lookup vs written mismatch | BY DESIGN | keys ORIGINAL for lookup, values sanitized |
| quoting=QUOTE_NONE | finding 1 | DEFENDED | test_dict_writer_refuses_quote_none |

## F. Library-wide sinks (remaining #3889 slices)

| Sink | Plan | Status |
|---|---|---|
| 1407 print sites / 121 files | #3915 routes through safe_print (stub until #3914 merges) | PR OPEN |
| downloader package-id/index prints | sanitize_terminal wiring, single_line for ids | PENDING |
| twitter json2csv writers | csvsec wiring + .ref fixture updates | PENDING |
| Text/ConcordanceIndex display | via #3915 routing | PR OPEN |
| decorators eval (CWE-95) | eval-avoidance rewrite | PENDING |
| jsontags giant int | follow-up after the int-bomb chokepoint | PENDING |
| CI `no-unsafe-print` guard | forbid bare print on untrusted values | PENDING |

## Standing verdicts (re-litigate only with new evidence)

- `float()` parsing is LINEAR for every input shape (STRTOD_DIGLIM=40 in
  CPython dtoa.c), measured empirically at 1M digits across adversarial
  shapes; the numeric-cell length cap is kept belt-and-braces regardless.
- Guards consult NOTHING attacker-definable: exact-type checks plus unbound C
  slots (`int.bit_length(v)`, `str.__str__(v)`); never instance lookups,
  never regex (the ansi-regex CVE-2021-3807 lesson: a sanitizer must not be a
  DoS vector itself).
- Escape-to-visible (`\xNN` style) matches the cat -v / GNU ls / git
  precedent; the apostrophe prefix is CWE-1236's own remediation (a TAB
  prefix was itself Symfony's CVE-2021-41270).
