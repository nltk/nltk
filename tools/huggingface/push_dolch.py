"""Push Dolch sight word list to nltk-data-hub/dolch.

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

Also removes old dolch configs from nltk-data-hub/words (now hosted here).
Also uploads updated nltk-data-hub/words README removing dolch/swadesh sections.

Usage:
    python push_dolch.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/dolch"
WORDS_REPO_ID = "nltk-data-hub/words"
SPLIT = "dolch"

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
ALL_DOLCH_CONFIGS = ["dolch"] + [f"dolch-{pos}" for pos in POS_CONFIGS]

README_DOLCH = """\
---
configs:
- config_name: dolch
  data_files:
  - split: dolch
    path: data/dolch/dolch.parquet
- config_name: dolch-adjectives
  data_files:
  - split: dolch
    path: data/dolch-adjectives/dolch.parquet
- config_name: dolch-nouns
  data_files:
  - split: dolch
    path: data/dolch-nouns/dolch.parquet
- config_name: dolch-verbs
  data_files:
  - split: dolch
    path: data/dolch-verbs/dolch.parquet
- config_name: dolch-adverbs
  data_files:
  - split: dolch
    path: data/dolch-adverbs/dolch.parquet
- config_name: dolch-prepositions
  data_files:
  - split: dolch
    path: data/dolch-prepositions/dolch.parquet
- config_name: dolch-pronouns
  data_files:
  - split: dolch
    path: data/dolch-pronouns/dolch.parquet
- config_name: dolch-conjunctions
  data_files:
  - split: dolch
    path: data/dolch-conjunctions/dolch.parquet
license: other
task_categories:
- token-classification
pretty_name: NLTK Dolch Sight Word List
---

# NLTK Dolch Sight Word List

The 315 Dolch sight words (Dolch 1936), grouped by part of speech, distributed
via [NLTK](https://www.nltk.org/).

## Configs

| Config | Words | Schema |
|---|---|---|
| `dolch` | 315 | `word, pos` |
| `dolch-adjectives` | 46 | `word` |
| `dolch-nouns` | 95 | `word` |
| `dolch-verbs` | 92 | `word` |
| `dolch-adverbs` | 34 | `word` |
| `dolch-prepositions` | 16 | `word` |
| `dolch-pronouns` | 26 | `word` |
| `dolch-conjunctions` | 6 | `word` |

## Schema

**`dolch`** — combined list with part-of-speech

| Column | Type | Description |
|---|---|---|
| `word` | string | The sight word |
| `pos` | string | Part of speech (adjectives, nouns, verbs, …) |

**`dolch-*`** — word only

| Column | Type | Description |
|---|---|---|
| `word` | string | The sight word |

## Usage

```python
from datasets import load_dataset

ds = load_dataset("nltk-data-hub/dolch", "dolch")         # all 315, with pos
ds = load_dataset("nltk-data-hub/dolch", "dolch-verbs")   # verbs only
```

## Via NLTK

```python
import nltk
nltk.download("words", hf=True)

nltk.corpus.words.words("dolch")             # 315 Dolch sight words
nltk.corpus.words.words("dolch-verbs")       # 92 verbs
nltk.corpus.words.words("dolch-nouns")       # 95 nouns
```

## License

Public domain — Dolch (1936), published work now in the public domain.

## Citation

```bibtex
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

# Cleaned-up words README — dolch and swadesh configs removed; See Also added
README_WORDS = """\
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
license: cc-by-4.0
task_categories:
- text-classification
- token-classification
pretty_name: NLTK Word Lists
---

# NLTK Word Lists

English word lists from [NLTK](https://www.nltk.org/),
the [New General Service List Project](https://www.newgeneralservicelist.com/),
and [Bing Liu's Opinion Lexicon](http://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html).

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

## See Also

These related word list datasets are also accessible via `nltk.corpus.words.words()`:

| Dataset | Contents | NLTK access |
|---|---|---|
| [nltk-data-hub/dolch](https://huggingface.co/datasets/nltk-data-hub/dolch) | 315 Dolch sight words, 8 POS configs | `words.words("dolch")`, `words.words("dolch-verbs")`, … |
| [nltk-data-hub/swadesh](https://huggingface.co/datasets/nltk-data-hub/swadesh) | 207 Swadesh concepts × 24 languages | `words.words("swadesh-en")`, `words.words("swadesh-de")`, … |

## Schemas

**`en`, `en-basic`, `opinion-positive`, `opinion-negative`** — word only

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

ds = load_dataset("nltk-data-hub/words", "ngsl")
ds = load_dataset("nltk-data-hub/words", "nawl")
ds = load_dataset("nltk-data-hub/words", "opinion-positive")
ds = load_dataset("nltk-data-hub/words", "opinion-negative")
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
nltk.corpus.words.words("en")                # 235,886 words
nltk.corpus.words.words("en-basic")          # Ogden 850
# Routed to nltk-data-hub/dolch:
nltk.corpus.words.words("dolch")             # 315 Dolch sight words
nltk.corpus.words.words("dolch-verbs")       # 92 Dolch verbs
# Routed to nltk-data-hub/swadesh:
nltk.corpus.words.words("swadesh-en")        # 207 English Swadesh words
nltk.corpus.words.words("swadesh-de")        # 207 German Swadesh words
```

## Licenses

- `en`, `en-basic`: distributed as part of the NLTK corpus data package.
- `ngsl`, `toeic`, `nawl`, `bsl`: © Browne, Culligan & Phillips, licensed under
  [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- `opinion-positive`, `opinion-negative`: © Bing Liu, licensed under
  [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).

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
  doi       = {10.7820/vli.v03.2.browne}
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
  booktitle = {Proceedings of KDD-2004},
  year      = {2004},
  url       = {http://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html}
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
    rows = []
    for pos in POS_CONFIGS:
        words = _read_words(os.path.join(CORPUS_DIR, pos))
        rows.extend({"word": w, "pos": pos} for w in words)
    df_all = pd.DataFrame(rows)
    _write(df_all, outdir, "dolch")
    counts["dolch"] = len(df_all)
    print(f"  dolch: {len(df_all):,} words (combined)")

    for pos in POS_CONFIGS:
        words = _read_words(os.path.join(CORPUS_DIR, pos))
        df = pd.DataFrame({"word": words})
        cfg = f"dolch-{pos}"
        _write(df, outdir, cfg)
        counts[cfg] = len(words)
        print(f"  {cfg}: {len(words):,} words")

    return counts


def cleanup_words_repo(api):
    """Delete old dolch configs from nltk-data-hub/words."""
    print(f"\nCleaning up old dolch configs from {WORDS_REPO_ID}...")
    for cfg in ALL_DOLCH_CONFIGS:
        path = f"data/{cfg}/words.parquet"
        try:
            api.delete_file(
                path_in_repo=path,
                repo_id=WORDS_REPO_ID,
                repo_type="dataset",
            )
            print(f"  deleted {path}")
        except Exception as e:
            print(f"  skip {path} ({e})")


def update_words_readme(api, outdir):
    """Upload cleaned-up words README (no dolch/swadesh YAML configs)."""
    print(f"\nUpdating README on {WORDS_REPO_ID}...")
    readme_path = os.path.join(outdir, "words_README.md")
    with open(readme_path, "w") as f:
        f.write(README_WORDS)
    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=WORDS_REPO_ID,
        repo_type="dataset",
    )
    print("  done")


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
        f.write(README_DOLCH)

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print(f"Uploading to {REPO_ID}...")
    for cfg in ALL_DOLCH_CONFIGS:
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

    cleanup_words_repo(api)
    update_words_readme(api, outdir)

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
