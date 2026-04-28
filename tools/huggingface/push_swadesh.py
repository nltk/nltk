"""Push Swadesh word lists to nltk-data-hub/swadesh.

Configs pushed (one per language, 207 concepts each):
  swadesh-be  Belarusian      swadesh-bg  Bulgarian
  swadesh-bs  Bosnian         swadesh-ca  Catalan
  swadesh-cs  Czech           swadesh-cu  Church Slavonic
  swadesh-de  German          swadesh-en  English
  swadesh-es  Spanish         swadesh-fr  French
  swadesh-hr  Croatian        swadesh-it  Italian
  swadesh-la  Latin           swadesh-mk  Macedonian
  swadesh-nl  Dutch           swadesh-pl  Polish
  swadesh-pt  Portuguese      swadesh-ro  Romanian
  swadesh-ru  Russian         swadesh-sk  Slovak
  swadesh-sl  Slovenian       swadesh-sr  Serbian
  swadesh-sw  Swahili         swadesh-uk  Ukrainian

Schema: concept_index (1-207), word (entry as in source; may contain alternatives)
Source: Wiktionary Appendix:Swadesh_list (via NLTK)
License: CC-BY-SA 3.0

Also removes old swadesh-* configs from nltk-data-hub/words (now hosted here).

Usage:
    python push_swadesh.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/swadesh"
WORDS_REPO_ID = "nltk-data-hub/words"
SPLIT = "swadesh"

CORPUS_DIR = os.path.expanduser("~/nltk_data/corpora/swadesh")

LANG_NAMES = {
    "be": "Belarusian",
    "bg": "Bulgarian",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cs": "Czech",
    "cu": "Church Slavonic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hr": "Croatian",
    "it": "Italian",
    "la": "Latin",
    "mk": "Macedonian",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "sw": "Swahili",
    "uk": "Ukrainian",
}

LANGS = sorted(LANG_NAMES)

_CONFIG_YAML = "\n".join(
    f"- config_name: swadesh-{lang}\n"
    f"  data_files:\n"
    f"  - split: {SPLIT}\n"
    f"    path: data/swadesh-{lang}/{SPLIT}.parquet"
    for lang in LANGS
)

README = f"""\
---
configs:
{_CONFIG_YAML}
license: cc-by-sa-3.0
task_categories:
- token-classification
pretty_name: NLTK Swadesh Word Lists
---

# NLTK Swadesh Word Lists

Basic vocabulary lists for 24 languages, derived from the
[Wiktionary Swadesh list appendix](https://en.wiktionary.org/wiki/Appendix:Swadesh_list)
and distributed via [NLTK](https://www.nltk.org/).

Each config is one language; each row is one of the 207 Swadesh concepts.

## Languages

| Config | Language | Concepts |
|---|---|---|
{"".join(f"| `swadesh-{lang}` | {LANG_NAMES[lang]} | {207 if lang != 'cu' else 174} |{chr(10)}" for lang in LANGS)}

## Schema

| Column | Type | Description |
|---|---|---|
| `concept_index` | int | Swadesh list position (1–207) |
| `word` | string | Word/phrase in that language (may contain alternatives) |

## Usage

```python
from datasets import load_dataset

ds = load_dataset("nltk-data-hub/swadesh", "swadesh-en")
words = ds["swadesh"]["word"]
```

## Via NLTK

```python
import nltk
nltk.download("words", hf=True)

nltk.corpus.words.words("swadesh-en")  # English Swadesh list
nltk.corpus.words.words("swadesh-de")  # German Swadesh list
nltk.corpus.words.words("swadesh-ru")  # Russian Swadesh list
```

## License

Derived from [Wiktionary](https://en.wiktionary.org/wiki/Appendix:Swadesh_list),
licensed under [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).

## Citation

```bibtex
@misc{{swadesh,
  author = {{Swadesh, Morris}},
  title  = {{Swadesh Word Lists}},
  note   = {{Via Wiktionary Appendix:Swadesh\\_list, CC-BY-SA 3.0}},
  url    = {{https://en.wiktionary.org/wiki/Appendix:Swadesh_list}}
}}
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
    for lang in LANGS:
        path = os.path.join(CORPUS_DIR, lang)
        words = _read_words(path)
        df = pd.DataFrame({"concept_index": range(1, len(words) + 1), "word": words})
        cfg = f"swadesh-{lang}"
        _write(df, outdir, cfg)
        counts[cfg] = len(words)
        print(f"  {cfg} ({LANG_NAMES[lang]}): {len(words)} concepts")
    return counts


def cleanup_words_repo(api):
    """Delete old swadesh-* configs from nltk-data-hub/words."""
    print(f"\nCleaning up old swadesh configs from {WORDS_REPO_ID}...")
    for lang in LANGS:
        path = f"data/swadesh-{lang}/words.parquet"
        try:
            api.delete_file(
                path_in_repo=path,
                repo_id=WORDS_REPO_ID,
                repo_type="dataset",
            )
            print(f"  deleted {path}")
        except Exception as e:
            print(f"  skip {path} ({e})")


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_swadesh.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_swadesh"
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    print("Building Swadesh parquets...")
    counts = build_configs(os.path.join(outdir, "data"))
    print(f"  {len(counts)} configs built")

    readme_path = os.path.join(outdir, "README.md")
    with open(readme_path, "w") as f:
        f.write(README)

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print(f"Uploading to {REPO_ID}...")
    for cfg in [f"swadesh-{lang}" for lang in LANGS]:
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

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
