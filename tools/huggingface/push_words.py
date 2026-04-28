"""Push NLTK words corpus + NGSL family to nltk-data-hub/words.

Configs pushed:
  en        — full NLTK English word list (~235K words)
  en-basic  — Ogden Basic English 850 (1930)
  ngsl      — New General Service List 1.2 (Browne et al. 2013), 2,809 words, CC-BY-SA 4.0
  toeic     — TOEIC Service List 1.2 (Browne & Culligan 2016), 1,250 words, CC-BY-SA 4.0
  nawl      — New Academic Word List 1.2 (Browne et al. 2013), 963 words, CC-BY-SA 4.0
  bsl       — Business Service List 1.2 (Browne & Culligan 2016), 1,744 words, CC-BY-SA 4.0

NGSL-family parquets (ngsl, toeic, nawl, bsl) include frequency metadata:
  word, rank, band, sfi, freq_per_million
  (band = pedagogical grouping level; absent from ngsl/toeic which pre-date the column)

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

# Direct Squarespace URLs — CC-BY-SA 4.0
NGSL_URL = (
    "https://static1.squarespace.com/static/64336926d7c6bb38965fdf3b"
    "/t/644e0be4ad7bae3d45b9e62a/1682836452194/NGSL_1.2_stats.csv"
)
TSL_URL = (
    "https://static1.squarespace.com/static/64336926d7c6bb38965fdf3b"
    "/t/643c876e097db81d6db2722c/1681688430425/TSL_1.2_stats.csv"
)
NAWL_URL = (
    "https://static1.squarespace.com/static/64336926d7c6bb38965fdf3b"
    "/t/644e0cc3e22fd95fbef5d060/1682836675261/NAWL_1.2_stats.csv"
)
BSL_URL = (
    "https://static1.squarespace.com/static/64336926d7c6bb38965fdf3b"
    "/t/644518e36de39033442a5aa9/1682249955219/BSL_1.20_stats.csv"
)

ALL_CONFIGS = ["en", "en-basic", "ngsl", "toeic", "nawl", "bsl"]

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
- config_name: nawl
  data_files:
  - split: words
    path: data/nawl/words.parquet
- config_name: bsl
  data_files:
  - split: words
    path: data/bsl/words.parquet
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
| `nawl` | 963 | `word, rank, band, sfi, freq_per_million` | CC-BY-SA 4.0 | New Academic Word List 1.2 |
| `bsl` | 1,744 | `word, rank, band, sfi, freq_per_million` | CC-BY-SA 4.0 | Business Service List 1.2 |

## Schemas

**`en` and `en-basic`** — simple word column only

| Column | Type | Description |
|---|---|---|
| `word` | string | The word |

**`ngsl` and `toeic`** — frequency metadata, no band

| Column | Type | Description |
|---|---|---|
| `word` | string | Headword / lemma |
| `rank` | int | Frequency rank (1 = most frequent) |
| `sfi` | float | Standard Frequency Index |
| `freq_per_million` | float | Adjusted frequency per million words |

**`nawl` and `bsl`** — frequency metadata + pedagogical band

| Column | Type | Description |
|---|---|---|
| `word` | string | Headword / lemma |
| `rank` | int | Frequency rank within this list |
| `band` | int | Pedagogical band grouping (lower = more frequent) |
| `sfi` | float | Standard Frequency Index |
| `freq_per_million` | float | Adjusted frequency per million words |

## Usage

```python
from datasets import load_dataset

# General English frequency list
ds = load_dataset("nltk-data-hub/words", "ngsl")

# Academic English supplement
ds = load_dataset("nltk-data-hub/words", "nawl")
nawl_words = ds["words"]["word"]          # sorted by frequency rank

# Business English supplement
ds = load_dataset("nltk-data-hub/words", "bsl")

# TOEIC exam vocabulary
ds = load_dataset("nltk-data-hub/words", "toeic")

# Ogden Basic English 850 / full word list
ds = load_dataset("nltk-data-hub/words", "en-basic")
ds = load_dataset("nltk-data-hub/words", "en")
```

## Via NLTK

```python
import nltk
nltk.download("words", hf=True)

nltk.corpus.words.words("ngsl")     # 2,809 words, frequency order
nltk.corpus.words.words("nawl")     # 963 academic words
nltk.corpus.words.words("bsl")      # 1,744 business words
nltk.corpus.words.words("toeic")    # 1,250 TOEIC words
nltk.corpus.words.words("en")       # 235,886 words
nltk.corpus.words.words("en-basic") # Ogden 850
```

## Licenses

- `en`, `en-basic`: distributed as part of the NLTK corpus data package.
- `ngsl`, `toeic`, `nawl`, `bsl`: © Browne, Culligan & Phillips, licensed under
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

@article{ngsl,
  author    = {Browne, Charles},
  title     = {A New General Service List: The Better Mousetrap We've Been Looking For?},
  journal   = {Vocabulary Learning and Instruction},
  volume    = {3},
  number    = {2},
  pages     = {1--10},
  year      = {2014},
  doi       = {10.7820/vli.v03.2.browne},
  url       = {https://www.newgeneralservicelist.com/}
}

@misc{nawl,
  author    = {Browne, Charles and Culligan, Brent and Phillips, Joseph},
  title     = {New Academic Word List 1.2},
  year      = {2013},
  url       = {https://www.newgeneralservicelist.com/nawl-new-academic-word-list}
}

@misc{tsl,
  author    = {Browne, Charles and Culligan, Brent},
  title     = {TOEIC Service List 1.2},
  year      = {2016},
  url       = {https://www.newgeneralservicelist.com/toeic-service-list}
}

@misc{bsl,
  author    = {Browne, Charles and Culligan, Brent},
  title     = {Business Service List 1.2},
  year      = {2016},
  url       = {https://www.newgeneralservicelist.com/business-service-list}
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


def _fetch_csv(url):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(resp.content), encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode CSV from {url}")


def build_ngsl_config(outdir):
    print("  Downloading NGSL 1.2...")
    df = _fetch_csv(NGSL_URL)
    df = df.rename(
        columns={
            "Lemma": "word",
            "SFI Rank": "rank",
            "SFI": "sfi",
            df.columns[-1]: "freq_per_million",
        }
    )[["word", "rank", "sfi", "freq_per_million"]]
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype("Int64")
    df = df.sort_values("rank").reset_index(drop=True)
    _write(df, outdir, "ngsl")
    return len(df)


def build_toeic_config(outdir):
    print("  Downloading TSL 1.2...")
    df = _fetch_csv(TSL_URL)
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
    _write(df, outdir, "toeic")
    return len(df)


def build_nawl_config(outdir):
    print("  Downloading NAWL 1.2...")
    df = _fetch_csv(NAWL_URL)
    df = df.rename(
        columns={
            "Word": "word",
            "Rank": "rank",
            "Band": "band",
            "SFI": "sfi",
            "U": "freq_per_million",
        }
    )[["word", "rank", "band", "sfi", "freq_per_million"]]
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype("Int64")
    df["band"] = pd.to_numeric(df["band"], errors="coerce").astype("Int64")
    df = df.sort_values("rank").reset_index(drop=True)
    _write(df, outdir, "nawl")
    return len(df)


def build_bsl_config(outdir):
    print("  Downloading BSL 1.2...")
    df = _fetch_csv(BSL_URL)
    # BSL has trailing empty columns — keep only the first 5
    df = df.iloc[:, :5]
    df.columns = ["word", "rank", "band", "sfi", "freq_per_million"]
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype("Int64")
    df["band"] = pd.to_numeric(df["band"], errors="coerce").astype("Int64")
    df = df.sort_values("rank").reset_index(drop=True)
    _write(df, outdir, "bsl")
    return len(df)


def _write(df, outdir, cfg):
    cfg_dir = os.path.join(outdir, cfg)
    os.makedirs(cfg_dir, exist_ok=True)
    df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
    print(f"  {cfg}: {len(df):,} words")


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
    counts["nawl"] = build_nawl_config(os.path.join(outdir, "data"))
    counts["bsl"] = build_bsl_config(os.path.join(outdir, "data"))
    print(f"  {len(counts)} configs, {sum(counts.values()):,} total entries")

    readme_path = os.path.join(outdir, "README.md")
    with open(readme_path, "w") as f:
        f.write(README)

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print("Uploading parquet files...")
    for cfg in ALL_CONFIGS:
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
