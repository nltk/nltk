"""Push Crúbadán n-gram corpus to nltk-data-hub/crubadan.

Configs pushed:
  table          — language metadata: crubadan_code, iso639_3, language_name
  {lang_code}    — 449 per-language configs (trigram, count), sorted by desc count

Source: An Crúbadán web crawler, Kevin Scannell (2010)
        http://borel.slu.edu/crubadan/
License: GPL v3

Usage:
    python push_crubadan.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/crubadan"
SPLIT = "crubadan"
CORPUS_DIR = os.path.expanduser("~/nltk_data/corpora/crubadan")


def load_table():
    rows = []
    with open(os.path.join(CORPUS_DIR, "table.txt"), encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                rows.append(
                    {
                        "crubadan_code": parts[0],
                        "iso639_3": parts[1],
                        "language_name": parts[2],
                    }
                )
    return pd.DataFrame(rows)


def load_ngrams(code):
    path = os.path.join(CORPUS_DIR, f"{code}-3grams.txt")
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                try:
                    rows.append({"count": int(parts[0]), "trigram": parts[1]})
                except ValueError:
                    continue
    df = pd.DataFrame(rows, columns=["count", "trigram"])
    df["count"] = df["count"].astype("int64")
    return df.sort_values("count", ascending=False).reset_index(drop=True)


def build_configs(outdir, codes, df_table):
    # table config
    table_dir = os.path.join(outdir, "table")
    os.makedirs(table_dir, exist_ok=True)
    df_table.to_parquet(os.path.join(table_dir, f"{SPLIT}.parquet"), index=False)
    print(f"  table: {len(df_table)} languages")

    # per-language configs
    for i, code in enumerate(codes, 1):
        df = load_ngrams(code)
        cfg_dir = os.path.join(outdir, code)
        os.makedirs(cfg_dir, exist_ok=True)
        df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
        if i % 50 == 0 or i == len(codes):
            print(f"  {i}/{len(codes)} languages built")


def build_readme(codes, df_table):
    # YAML frontmatter — table config first, then all language configs
    table_yaml = (
        "- config_name: table\n"
        "  data_files:\n"
        f"  - split: {SPLIT}\n"
        f"    path: data/table/{SPLIT}.parquet"
    )
    lang_yaml = "\n".join(
        f"- config_name: {code}\n"
        f"  data_files:\n"
        f"  - split: {SPLIT}\n"
        f"    path: data/{code}/{SPLIT}.parquet"
        for code in codes
    )

    # sample table for README
    sample_rows = "\n".join(
        f"| `{row.crubadan_code}` | `{row.iso639_3}` | {row.language_name} |"
        for row in df_table.head(10).itertuples()
    )

    return f"""\
---
configs:
{table_yaml}
{lang_yaml}
license: gpl-3.0
task_categories:
- text-classification
- token-classification
pretty_name: NLTK Crúbadán Language ID Corpus
---

# NLTK Crúbadán Language ID Corpus

Character 3-gram frequency tables for **{len(codes)} writing systems**, collected
by Kevin Scannell's [An Crúbadán](http://borel.slu.edu/crubadan/) web crawler (2010).
Distributed via [NLTK](https://www.nltk.org/).

Trigrams use `<` (word start) and `>` (word end) as boundary markers.

## Configs

| Config | Description | Schema |
|---|---|---|
| `table` | Language metadata | `crubadan_code, iso639_3, language_name` |
| `{{lang_code}}` | Per-language trigrams | `count, trigram` |

All {len(codes)} language codes: {', '.join(f'`{c}`' for c in codes[:20])}, … (and {len(codes)-20} more)

## Schema

**`table`**

| Column | Type | Description |
|---|---|---|
| `crubadan_code` | string | Internal Crúbadán writing-system code |
| `iso639_3` | string | ISO 639-3 language code |
| `language_name` | string | English language name |

**`{{lang_code}}`** — one config per writing system

| Column | Type | Description |
|---|---|---|
| `count` | int64 | Frequency of trigram in crawled text |
| `trigram` | string | 3-character sequence (`<`/`>` = word boundaries) |

Rows are sorted by descending count (most frequent first).

## Sample languages

| Code | ISO 639-3 | Language |
|---|---|---|
{sample_rows}

## Usage

```python
from datasets import load_dataset

# Language metadata
meta = load_dataset("nltk-data-hub/crubadan", "table")
df = meta["crubadan"].to_pandas()

# Trigrams for a specific language
ds = load_dataset("nltk-data-hub/crubadan", "af")   # Afrikaans
trigrams = ds["crubadan"].to_pandas()               # count, trigram columns
```

## Via NLTK

```python
import nltk
nltk.download("crubadan")

reader = nltk.corpus.crubadan
reader.lang_codes()          # list all 449 codes
reader.trigrams("af")        # Afrikaans trigrams
reader.iso_lang_code("af")   # → 'afr'
reader.lang_name("af")       # → 'Afrikaans'
```

## License

GPL v3 — © 2010 Kevin P. Scannell.
See [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html).

## Citation

```bibtex
@inproceedings{{crubadan,
  author    = {{Scannell, Kevin P.}},
  title     = {{The Crúbadán Project: Corpus building for under-resourced languages}},
  booktitle = {{Building and Exploring Web Corpora: Proceedings of the 3rd Web as Corpus Workshop}},
  year      = {{2007}},
  pages     = {{5--15}},
  url       = {{http://borel.slu.edu/crubadan/}}
}}
```
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_crubadan.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    # collect language codes in table order
    df_table = load_table()
    codes = list(df_table["crubadan_code"])

    outdir = "/tmp/nltk_crubadan/data"
    if os.path.exists("/tmp/nltk_crubadan"):
        shutil.rmtree("/tmp/nltk_crubadan")
    os.makedirs(outdir)

    print(f"Building parquets for {len(codes)} languages + table...")
    build_configs(outdir, codes, df_table)

    readme_path = "/tmp/nltk_crubadan/README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(build_readme(codes, df_table))

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print("Uploading (folder batch)...")
    api.upload_folder(
        folder_path="/tmp/nltk_crubadan",
        repo_id=REPO_ID,
        repo_type="dataset",
    )

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
