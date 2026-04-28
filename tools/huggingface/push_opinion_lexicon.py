"""Push opinion_lexicon configs to nltk-data-hub/words.

Configs pushed:
  opinion-positive  — 2,006 positive opinion words (Hu & Liu)
  opinion-negative  — 4,783 negative opinion words (Hu & Liu)

Schema: word (string only — one word per row, alphabetical order)
License: CC BY 4.0
Source: Bing Liu, http://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html

Usage:
    python push_opinion_lexicon.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/words"
SPLIT = "words"

CORPUS_DIR = os.path.expanduser("~/nltk_data/corpora/opinion_lexicon")
CONFIGS = {
    "opinion-positive": "positive-words.txt",
    "opinion-negative": "negative-words.txt",
}

# Updated README for nltk-data-hub/words including all 8 configs
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

## Schemas

**`en`, `en-basic`, `opinion-positive`, `opinion-negative`** — simple word column only

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

# Academic / Business English supplements
ds = load_dataset("nltk-data-hub/words", "nawl")
ds = load_dataset("nltk-data-hub/words", "bsl")

# TOEIC exam vocabulary
ds = load_dataset("nltk-data-hub/words", "toeic")

# Sentiment / opinion word lists
ds = load_dataset("nltk-data-hub/words", "opinion-positive")
ds = load_dataset("nltk-data-hub/words", "opinion-negative")

# Ogden Basic English 850 / full word list
ds = load_dataset("nltk-data-hub/words", "en-basic")
ds = load_dataset("nltk-data-hub/words", "en")
```

## Via NLTK

```python
import nltk
nltk.download("words", hf=True)

nltk.corpus.words.words("ngsl")             # 2,809 words, frequency order
nltk.corpus.words.words("nawl")             # 963 academic words
nltk.corpus.words.words("bsl")              # 1,744 business words
nltk.corpus.words.words("toeic")            # 1,250 TOEIC words
nltk.corpus.words.words("opinion-positive") # 2,006 positive opinion words
nltk.corpus.words.words("opinion-negative") # 4,783 negative opinion words
nltk.corpus.words.words("en")               # 235,886 words
nltk.corpus.words.words("en-basic")         # Ogden 850
```

## Licenses

- `en`, `en-basic`: distributed as part of the NLTK corpus data package.
- `ngsl`, `toeic`, `nawl`, `bsl`: © Browne, Culligan & Phillips, licensed under
  [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
- `opinion-positive`, `opinion-negative`: © Bing Liu, licensed under
  [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).

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
```
"""


def _read_word_file(path):
    words = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            words.append(line)
    return words


def build_configs(outdir):
    counts = {}
    for cfg, filename in CONFIGS.items():
        path = os.path.join(CORPUS_DIR, filename)
        words = _read_word_file(path)
        df = pd.DataFrame({"word": words})
        cfg_dir = os.path.join(outdir, cfg)
        os.makedirs(cfg_dir, exist_ok=True)
        df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
        counts[cfg] = len(words)
        print(f"  {cfg}: {len(words):,} words")
    return counts


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_opinion_lexicon.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_opinion_lexicon"
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    print("Building opinion lexicon parquets...")
    counts = build_configs(os.path.join(outdir, "data"))
    print(f"  {len(counts)} configs, {sum(counts.values()):,} total words")

    readme_path = os.path.join(outdir, "README.md")
    with open(readme_path, "w") as f:
        f.write(README)

    print(f"\nUploading to {REPO_ID}...")
    for cfg in CONFIGS:
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
