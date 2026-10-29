# Porting the 3.10 line to Python 2.7

The converters that produced the py27-security branch, kept so the port can
be repeated on a newer 3.10 tree. Run them with Python 3.13 from the branch
root; `import_sweep27.py` runs with the 2.7 interpreter.

- `defstring.py`: f-strings to `str.format`, comments preserved, control
  characters written as escapes.
- `py2pass.py`: `--basic` (annotations, raise-from, yield-from, bare super,
  future header, numeric underscores), `--deco` (keyword-only parameters kept
  keyword-only through `nltk.compat.keyword_only`), `--vararg` (keyword-only
  parameters after `*args` popped from the keyword dict).
- `reescape.py`: re-escapes raw control characters inside string literals.
- `port_file.py`: every pass in order for one file, then the mechanical
  rewrites (six.moves, backports, `nltk.compat` names).
- `port_missing.py`: ports every 3.10 module the tree imports but lacks.
- `import_sweep27.py`: imports every module on 2.7 and groups the failures.

Source of truth for the hand rules: the project notes in the audit record
`PY27_BACKPORT_20261023.md` (not in the tree).
