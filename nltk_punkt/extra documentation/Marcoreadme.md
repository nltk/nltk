# Verifying Your NLTK Entry-Point Extension and `nltk-punkt` Package

This README explains how to verify that your custom NLTK installation and the `nltk-punkt` pip package are working correctly. These instructions assume:

* You have cloned and modified the NLTK repository (`nltk_Group1_ENGG4450/`).
* You applied the entry-point patch to `nltk/data.py`.
* You built and installed the `nltk-punkt` wheel.
* You installed your local NLTK clone in editable mode.

Follow all steps below to confirm that your implementation works end-to-end.

---

# 1. Verify Your Local NLTK Clone Is Being Used

Open **PowerShell** and run:

```powershell
python
```

At the `>>>` prompt, type:

```python
import nltk, inspect
import nltk.data as nd

print("nltk imported from:", nltk.__file__)
print("data.py imported from:", inspect.getfile(nd))
```

### ✔ Expected output

Both paths MUST point inside:

```
...nltk_Group1_ENGG4450/nltk/
```

### ✘ If they point to `site-packages/nltk`:

You must reinstall your clone:

```powershell
pip install -e .
```

Run the check again.

---

# 2. Verify the Entry Point Is Registered

Inside Python (`>>>`):

```python
import importlib.metadata as m

for ep in m.entry_points():
    if ep.group == "nltk_data":
        print("FOUND entry point:", ep)
```

### ✔ Expected output

```
FOUND entry point: EntryPoint(name='punkt', value='nltk_punkt.data', group='nltk_data')
```

If nothing prints, reinstall your `nltk-punkt` wheel:

```powershell
cd nltk_punkt/dist
pip install --force-reinstall .\nltk_punkt-0.1.0-py3-none-any.whl
```

---

# 3. Verify Your Patched `find()` Detects the pip Resource

In Python:

```python
import nltk
print(nltk.data.find("tokenizers/punkt/english.pickle"))
```

### ✔ Expected output

A path like:

```
...nltk_punkt/data
```

This means NLTK is loading tokenizers from your pip package.

### ✘ Incorrect output

```
AppData\Roaming\nltk_data\tokenizers\punkt\english.pickle
```

This means the patch is not being executed.

---

# 4. Verify Punkt Works Without `nltk.download()`

Run:

```python
from nltk.tokenize import PunktSentenceTokenizer

tok = PunktSentenceTokenizer()
print(tok.tokenize("Hello world. This is a test. Another sentence here."))
```

### ✔ Expected output

A list of tokenized sentences:

```
['Hello world.', 'This is a test.', 'Another sentence here.']
```

This confirms:

* Punkt loaded from your **pip package**, not from `nltk_data`.
* Your entry-point-based lookup is fully functional.

---

# 5. Full Verification Checklist

| Check                                                  | Result |
| ------------------------------------------------------ | ------ |
| Local NLTK clone is active (`nltk imported from` path) | ✔      |
| Entry point appears under `nltk_data` group            | ✔      |
| `find()` returns path inside `nltk_punkt/data`         | ✔      |
| Punkt works without calling `nltk.download()`          | ✔      |

When all four checks pass, your implementation of Issue #3413 is confirmed working.

---

# 6. What Will Persist Between Sessions?

You **do not** need to redo steps after closing VS Code as long as:

* You use the same Python interpreter.
* You keep the patched `nltk/data.py`.
* You do not uninstall Python.
* Your `nltk-punkt` package remains installed.

Everything else is permanent.

---

If you need help creating test cases for Assignment 4, ask and I will generate complete unit tests for validating this behavior automatically.
