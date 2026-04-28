"""Push NLTK gazetteers corpus to nltk-data-hub/gazetteers.

Configs pushed (one per file):
  countries      — 289 country names (GFDL, Wikipedia)
  isocountries   — 234 ISO country names (public domain)
  nationalities  — 200 nationality adjectives (public domain)
  caprovinces    — 14 Canadian provinces
  mexstates      — 32 Mexican states
  usstates       — 52 US states
  usstateabbrev  — 137 US state abbreviations
  uscities       — 255 US cities with 100k+ population (GFDL, Wikipedia)

Schema: name (string) — one entry per row.
License: GFDL (Wikipedia-derived files) / public domain

Usage:
    python push_gazetteers.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/gazetteers"
SPLIT = "gazetteers"
CORPUS_DIR = os.path.expanduser("~/nltk_data/corpora/gazetteers")

CONFIGS = [
    "countries",
    "isocountries",
    "nationalities",
    "caprovinces",
    "mexstates",
    "usstates",
    "usstateabbrev",
    "uscities",
]

README = """\
---
configs:
- config_name: countries
  data_files:
  - split: gazetteers
    path: data/countries/gazetteers.parquet
- config_name: isocountries
  data_files:
  - split: gazetteers
    path: data/isocountries/gazetteers.parquet
- config_name: nationalities
  data_files:
  - split: gazetteers
    path: data/nationalities/gazetteers.parquet
- config_name: caprovinces
  data_files:
  - split: gazetteers
    path: data/caprovinces/gazetteers.parquet
- config_name: mexstates
  data_files:
  - split: gazetteers
    path: data/mexstates/gazetteers.parquet
- config_name: usstates
  data_files:
  - split: gazetteers
    path: data/usstates/gazetteers.parquet
- config_name: usstateabbrev
  data_files:
  - split: gazetteers
    path: data/usstateabbrev/gazetteers.parquet
- config_name: uscities
  data_files:
  - split: gazetteers
    path: data/uscities/gazetteers.parquet
license: gfdl
task_categories:
- token-classification
pretty_name: NLTK Gazetteers
---

# NLTK Gazetteers

Geographic and demographic word lists from [NLTK](https://www.nltk.org/).
Each config is one list; each row is one entry.

## Configs

| Config | Entries | Description | License |
|---|---|---|---|
| `countries` | 289 | Country names | GFDL (Wikipedia) |
| `isocountries` | 234 | ISO country names | Public domain |
| `nationalities` | 200 | Nationality adjectives | Public domain |
| `caprovinces` | 14 | Canadian provinces | — |
| `mexstates` | 32 | Mexican states | — |
| `usstates` | 52 | US states | — |
| `usstateabbrev` | 137 | US state abbreviations | — |
| `uscities` | 255 | US cities 100k+ population | GFDL (Wikipedia) |

## Schema

| Column | Type | Description |
|---|---|---|
| `name` | string | The gazetteer entry |

## Usage

```python
from datasets import load_dataset

ds = load_dataset("nltk-data-hub/gazetteers", "countries")
countries = ds["gazetteers"]["name"]
```

## Via NLTK

```python
import nltk
nltk.download("gazetteers")

nltk.corpus.gazetteers.words("countries.txt")
nltk.corpus.gazetteers.words("uscities.txt")
```

## License

- `countries.txt`, `uscities.txt`: GNU Free Documentation License (GFDL),
  derived from Wikipedia.
- `isocountries.txt`, `nationalities.txt`: public domain.
"""


def _read(filename):
    path = os.path.join(CORPUS_DIR, filename)
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return [line.strip() for line in f if line.strip()]
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {filename}")


def build_configs(outdir):
    counts = {}
    for cfg in CONFIGS:
        entries = _read(f"{cfg}.txt")
        df = pd.DataFrame({"name": entries})
        cfg_dir = os.path.join(outdir, cfg)
        os.makedirs(cfg_dir, exist_ok=True)
        df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
        counts[cfg] = len(entries)
        print(f"  {cfg}: {len(entries):,} entries")
    return counts


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_gazetteers.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_gazetteers/data"
    if os.path.exists("/tmp/nltk_gazetteers"):
        shutil.rmtree("/tmp/nltk_gazetteers")
    os.makedirs(outdir)

    print("Building gazetteers parquets...")
    counts = build_configs(outdir)
    print(f"  {len(counts)} configs, {sum(counts.values()):,} total entries")

    readme_path = "/tmp/nltk_gazetteers/README.md"
    with open(readme_path, "w") as f:
        f.write(README)

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print("Uploading...")
    api.upload_folder(
        folder_path="/tmp/nltk_gazetteers",
        repo_id=REPO_ID,
        repo_type="dataset",
    )

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
