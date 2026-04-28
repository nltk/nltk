"""Push NLTK words corpus + NGSL + TOEIC Service List to nltk-data-hub/words.

Configs pushed:
  en          — full NLTK English word list (~235K words)
  en-basic    — Ogden Basic English 850 (1930)
  ngsl        — New General Service List 1.2 (Browne et al. 2013), 2809 words, CC-BY-SA 4.0
  toeic       — TOEIC Service List 1.2 (Browne & Culligan 2016), 1250 words, CC-BY-SA 4.0

NGSL and TOEIC parquets include frequency metadata columns:
  word, rank, sfi, freq_per_million

Usage:
    python push_words.py <hf_token>
"""

import io
import os
import shutil
import sys

import pandas as pd
import requests
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/words"
SPLIT = "words"

# Direct download URLs (Squarespace-hosted, CC-BY-SA 4.0)
NGSL_URL = (
    "https://static1.squarespace.com/static/64336926d7c6bb38965fdf3b"
    "/t/644e0be4ad7bae3d45b9e62a/1682836452194/NGSL_1.2_stats.csv"
)
TSL_URL = (
    "https://static1.squarespace.com/static/64336926d7c6bb38965fdf3b"
    "/t/643c876e097db81d6db2722c/1681688430425/TSL_1.2_stats.csv"
)

README = """\
---
configs:
- config_name: en
  data_files:
  - split: words
    path: data/en/words.parquet
- config_name: en-basic
  data_files:
  - split: words
    path: data/en-basic/words.parquet
- config_name: ngsl
  data_files:
  - split: words
    path: data/ngsl/words.parquet
- config_name: toeic
  data_files:
  - split: words
    path: data/toeic/words.parquet
license: cc-by-sa-4.0
task_categories:
- text-classification
- token-classification
pretty_name: NLTK Word Lists
---

# NLTK Word Lists

English word lists from [NLTK](https://www.nltk.org/) and the
[New General Service List Project](https://www.newgeneralservicelist.com/).

## Configs

| Config | Words | Schema | License | Source |
|---|---|---|---|---|
| `en` | 235,886 | `word` | NLTK (other) | NLTK words corpus |
| `en-basic` | 850 | `word` | Public domain | Ogden Basic English (1930) |
| `ngsl` | 2,809 | `word, rank, sfi, freq_per_million` | CC-BY-SA 4.0 | New General Service List 1.2 |
| `toeic` | 1,250 | `word, rank, sfi, freq_per_million` | CC-BY-SA 4.0 | TOEIC Service List 1.2 |

## Schemas

**`en` and `en-basic`**

| Column | Type | Description |
|---|---|---|
| `word` | string | The word |

**`ngsl` and `toeic`**

| Column | Type | Description |
|---|---|---|
| `word` | string | Headword / lemma |
| `rank` | int | Frequency rank (1 = most frequent) |
| `sfi` | float | Standard Frequency Index |
| `freq_per_million` | float | Adjusted frequency per million words |

## Usage

```python
from datasets import load_dataset

# Full English word list
ds = load_dataset("nltk-data-hub/words", "en")

# Ogden Basic English 850
ds = load_dataset("nltk-data-hub/words", "en-basic")

# New General Service List (2,809 most frequent words in general English)
ds = load_dataset("nltk-data-hub/words", "ngsl")
ngsl_words = ds["words"]["word"]

# TOEIC Service List (1,250 words for TOEIC / business English)
ds = load_dataset("nltk-data-hub/words", "toeic")
toeic_words = ds["words"]["word"]

# Sort NGSL by frequency rank
import pandas as pd
df = ds["words"].to_pandas().sort_values("rank")
```

## Via NLTK (after nltk.download)

```python
import nltk
nltk.download("words", hf=True)

nltk.corpus.words.words("ngsl")    # list of 2,809 words
nltk.corpus.words.words("toeic")   # list of 1,250 words
nltk.corpus.words.words("en")      # list of 235,886 words
nltk.corpus.words.words("en-basic")  # Ogden 850
```

## Licenses

- `en`, `en-basic`: distributed as part of the NLTK corpus data package.
- `ngsl`, `toeic`: © Browne, Culligan & Phillips, licensed under
  [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).

## Citations

```bibtex
@book{nltk,
  author    = {Bird, Steven and Klein, Ewan and Loper, Edward},
  title     = {Natural Language Processing with Python},
  publisher = {O'Reilly Media},
  year      = {2009},
  url       = {https://www.nltk.org/}
}

@misc{ngsl,
  author    = {Browne, Charles and Culligan, Brent and Phillips, Joseph},
  title     = {New General Service List 1.2},
  year      = {2013},
  url       = {https://www.newgeneralservicelist.com/}
}

@misc{tsl,
  author    = {Browne, Charles and Culligan, Brent},
  title     = {TOEIC Service List 1.2},
  year      = {2016},
  url       = {https://www.newgeneralservicelist.com/toeic-service-list}
}
```
"""


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_en_configs(outdir):
    from nltk.corpus import words as words_corpus

    counts = {}
    for cfg in ["en", "en-basic"]:
        word_list = words_corpus.words(cfg)
        df = pd.DataFrame({"word": word_list})
        cfg_dir = os.path.join(outdir, cfg)
        os.makedirs(cfg_dir, exist_ok=True)
        df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
        counts[cfg] = len(word_list)
        print(f"  {cfg}: {len(word_list):,} words")
    return counts


def build_ngsl_config(outdir):
    print("  Downloading NGSL 1.2 stats CSV...")
    resp = requests.get(NGSL_URL, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    # Normalise column names: Lemma, SFI Rank, SFI, Adjusted Frequency per Million (U)
    df = df.rename(
        columns={
            "Lemma": "word",
            "SFI Rank": "rank",
            "SFI": "sfi",
            df.columns[-1]: "freq_per_million",  # long name varies slightly
        }
    )[["word", "rank", "sfi", "freq_per_million"]]
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype("Int64")
    df = df.sort_values("rank").reset_index(drop=True)
    cfg_dir = os.path.join(outdir, "ngsl")
    os.makedirs(cfg_dir, exist_ok=True)
    df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
    print(f"  ngsl: {len(df):,} words")
    return len(df)


def build_toeic_config(outdir):
    print("  Downloading TSL 1.2 stats CSV...")
    resp = requests.get(TSL_URL, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    # Normalise column names: Word, TSL Rank, SFI, U
    df = df.rename(
        columns={
            "Word": "word",
            "TSL Rank": "rank",
            "SFI": "sfi",
            "U": "freq_per_million",
        }
    )[["word", "rank", "sfi", "freq_per_million"]]
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype("Int64")
    df = df.sort_values("rank").reset_index(drop=True)
    cfg_dir = os.path.join(outdir, "toeic")
    os.makedirs(cfg_dir, exist_ok=True)
    df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
    print(f"  toeic: {len(df):,} words")
    return len(df)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_words.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_words"
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    print("Building word list parquets...")
    counts = build_en_configs(os.path.join(outdir, "data"))
    counts["ngsl"] = build_ngsl_config(os.path.join(outdir, "data"))
    counts["toeic"] = build_toeic_config(os.path.join(outdir, "data"))
    print(f"  4 configs, {sum(counts.values()):,} total entries")

    readme_path = os.path.join(outdir, "README.md")
    with open(readme_path, "w") as f:
        f.write(README)

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print("Uploading parquet files...")
    for cfg in ["en", "en-basic", "ngsl", "toeic"]:
        local_path = os.path.join(outdir, "data", cfg, f"{SPLIT}.parquet")
        api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=f"data/{cfg}/{SPLIT}.parquet",
            repo_id=REPO_ID,
            repo_type="dataset",
        )
        print(f"  uploaded {cfg}")

    print("Uploading README.md...")
    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=REPO_ID,
        repo_type="dataset",
    )

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
