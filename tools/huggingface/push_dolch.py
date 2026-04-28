"""Push Dolch sight word list to nltk-data-hub/words.

Configs pushed:
  dolch              — all 315 sight words combined (word, pos columns)
  dolch-adjectives   — 46 words
  dolch-nouns        — 95 words
  dolch-verbs        — 92 words
  dolch-adverbs      — 34 words
  dolch-prepositions — 16 words
  dolch-pronouns     — 26 words
  dolch-conjunctions — 6 words

Source: Dolch, E. W. (1936). A basic sight vocabulary. The Elementary School
        Journal, 36(6), 456–460.
License: Public domain (1936 publication)

Usage:
    python push_dolch.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/words"
SPLIT = "words"

CORPUS_DIR = os.path.expanduser("~/nltk_data/corpora/dolch")
POS_CONFIGS = [
    "adjectives",
    "nouns",
    "verbs",
    "adverbs",
    "prepositions",
    "pronouns",
    "conjunctions",
]

# Full README for nltk-data-hub/words with all configs
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
- config_name: opinion-positive
  data_files:
  - split: words
    path: data/opinion-positive/words.parquet
- config_name: opinion-negative
  data_files:
  - split: words
    path: data/opinion-negative/words.parquet
- config_name: dolch
  data_files:
  - split: words
    path: data/dolch/words.parquet
- config_name: dolch-adjectives
  data_files:
  - split: words
    path: data/dolch-adjectives/words.parquet
- config_name: dolch-nouns
  data_files:
  - split: words
    path: data/dolch-nouns/words.parquet
- config_name: dolch-verbs
  data_files:
  - split: words
    path: data/dolch-verbs/words.parquet
- config_name: dolch-adverbs
  data_files:
  - split: words
    path: data/dolch-adverbs/words.parquet
- config_name: dolch-prepositions
  data_files:
  - split: words
    path: data/dolch-prepositions/words.parquet
- config_name: dolch-pronouns
  data_files:
  - split: words
    path: data/dolch-pronouns/words.parquet
- config_name: dolch-conjunctions
  data_files:
  - split: words
    path: data/dolch-conjunctions/words.parquet
license: cc-by-4.0
task_categories:
- text-classification
- token-classification
pretty_name: NLTK Word Lists
---

# NLTK Word Lists

English word lists from [NLTK](https://www.nltk.org/),
the [New General Service List Project](https://www.newgeneralservicelist.com/),
[Bing Liu's Opinion Lexicon](http://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html),
and the [Dolch sight word list](https://en.wikipedia.org/wiki/Dolch_word_list).

## Configs

| Config | Words | Schema | License | Source |
|---|---|---|---|---|
| `en` | 235,886 | `word` | NLTK (other) | NLTK words corpus |
| `en-basic` | 850 | `word` | Public domain | Ogden Basic English (1930) |
| `ngsl` | 2,809 | `word, rank, sfi, freq_per_million` | CC-BY-SA 4.0 | New General Service List 1.2 |
| `toeic` | 1,250 | `word, rank, sfi, freq_per_million` | CC-BY-SA 4.0 | TOEIC Service List 1.2 |
| `nawl` | 963 | `word, rank, band, sfi, freq_per_million` | CC-BY-SA 4.0 | New Academic Word List 1.2 |
| `bsl` | 1,744 | `word, rank, band, sfi, freq_per_million` | CC-BY-SA 4.0 | Business Service List 1.2 |
| `opinion-positive` | 2,006 | `word` | CC-BY 4.0 | Hu & Liu Opinion Lexicon |
| `opinion-negative` | 4,783 | `word` | CC-BY 4.0 | Hu & Liu Opinion Lexicon |
| `dolch` | 315 | `word, pos` | Public domain | Dolch (1936) sight words |
| `dolch-adjectives` | 46 | `word` | Public domain | Dolch (1936) |
| `dolch-nouns` | 95 | `word` | Public domain | Dolch (1936) |
| `dolch-verbs` | 92 | `word` | Public domain | Dolch (1936) |
| `dolch-adverbs` | 34 | `word` | Public domain | Dolch (1936) |
| `dolch-prepositions` | 16 | `word` | Public domain | Dolch (1936) |
| `dolch-pronouns` | 26 | `word` | Public domain | Dolch (1936) |
| `dolch-conjunctions` | 6 | `word` | Public domain | Dolch (1936) |

## Schemas

**`en`, `en-basic`, `opinion-positive`, `opinion-negative`, `dolch-*`** — word only

| Column | Type | Description |
|---|---|---|
| `word` | string | The word |

**`dolch`** — combined list with part-of-speech

| Column | Type | Description |
|---|---|---|
| `word` | string | The sight word |
| `pos` | string | Part of speech (adjectives, nouns, verbs, …) |

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

# Academic / Business English supplements
ds = load_dataset("nltk-data-hub/words", "nawl")
ds = load_dataset("nltk-data-hub/words", "bsl")

# TOEIC exam vocabulary
ds = load_dataset("nltk-data-hub/words", "toeic")

# Sentiment / opinion word lists
ds = load_dataset("nltk-data-hub/words", "opinion-positive")
ds = load_dataset("nltk-data-hub/words", "opinion-negative")

# Dolch sight words
ds = load_dataset("nltk-data-hub/words", "dolch")          # all 315, with pos column
ds = load_dataset("nltk-data-hub/words", "dolch-verbs")    # verbs only

# Ogden Basic English 850 / full word list
ds = load_dataset("nltk-data-hub/words", "en-basic")
ds = load_dataset("nltk-data-hub/words", "en")
```

## Via NLTK

```python
import nltk
nltk.download("words", hf=True)

nltk.corpus.words.words("ngsl")              # 2,809 words, frequency order
nltk.corpus.words.words("nawl")              # 963 academic words
nltk.corpus.words.words("bsl")               # 1,744 business words
nltk.corpus.words.words("toeic")             # 1,250 TOEIC words
nltk.corpus.words.words("opinion-positive")  # 2,006 positive opinion words
nltk.corpus.words.words("opinion-negative")  # 4,783 negative opinion words
nltk.corpus.words.words("dolch")             # 315 Dolch sight words (word column only)
nltk.corpus.words.words("dolch-verbs")       # 92 Dolch verbs
nltk.corpus.words.words("en")                # 235,886 words
nltk.corpus.words.words("en-basic")          # Ogden 850
```

## Licenses

- `en`, `en-basic`: distributed as part of the NLTK corpus data package.
- `ngsl`, `toeic`, `nawl`, `bsl`: © Browne, Culligan & Phillips, licensed under
  [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
- `opinion-positive`, `opinion-negative`: © Bing Liu, licensed under
  [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
- `dolch`, `dolch-*`: public domain (Dolch 1936, published work now in public domain).

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

@inproceedings{opinion_lexicon,
  author    = {Hu, Minqing and Liu, Bing},
  title     = {Mining and Summarizing Customer Reviews},
  booktitle = {Proceedings of the ACM SIGKDD International Conference on
               Knowledge Discovery and Data Mining (KDD-2004)},
  year      = {2004},
  address   = {Seattle, Washington, USA},
  url       = {http://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html}
}

@article{dolch,
  author  = {Dolch, Edward William},
  title   = {A Basic Sight Vocabulary},
  journal = {The Elementary School Journal},
  volume  = {36},
  number  = {6},
  pages   = {456--460},
  year    = {1936},
  doi     = {10.1086/457353}
}
```
"""


def _read_words(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _write(df, outdir, cfg):
    cfg_dir = os.path.join(outdir, cfg)
    os.makedirs(cfg_dir, exist_ok=True)
    df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)


def build_configs(outdir):
    counts = {}

    # Combined dolch config (word + pos)
    rows = []
    for pos in POS_CONFIGS:
        words = _read_words(os.path.join(CORPUS_DIR, pos))
        rows.extend({"word": w, "pos": pos} for w in words)
    df_all = pd.DataFrame(rows)
    _write(df_all, outdir, "dolch")
    counts["dolch"] = len(df_all)
    print(f"  dolch: {len(df_all):,} words (combined)")

    # Per-POS configs (word only)
    for pos in POS_CONFIGS:
        words = _read_words(os.path.join(CORPUS_DIR, pos))
        df = pd.DataFrame({"word": words})
        cfg = f"dolch-{pos}"
        _write(df, outdir, cfg)
        counts[cfg] = len(words)
        print(f"  {cfg}: {len(words):,} words")

    return counts


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_dolch.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_dolch"
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    print("Building Dolch parquets...")
    counts = build_configs(os.path.join(outdir, "data"))
    print(f"  {len(counts)} configs, {counts['dolch']:,} unique words")

    readme_path = os.path.join(outdir, "README.md")
    with open(readme_path, "w") as f:
        f.write(README)

    print(f"\nUploading to {REPO_ID}...")
    all_configs = ["dolch"] + [f"dolch-{pos}" for pos in POS_CONFIGS]
    for cfg in all_configs:
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
