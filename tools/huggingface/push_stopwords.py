"""Push NLTK stopwords to nltk-data-hub/stopwords on HuggingFace.

One config per language, one parquet file per language.
The HF dataset viewer shows each language as a separate tab.

Usage:
    python push_stopwords.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/stopwords"

# BCP-47 codes for NLTK language names
LANG_CODES = {
    "albanian": "sq",
    "arabic": "ar",
    "azerbaijani": "az",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "catalan": "ca",
    "chinese": "zh",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "greek": "el",
    "hebrew": "he",
    "hinglish": "hi",
    "hungarian": "hu",
    "indonesian": "id",
    "italian": "it",
    "kazakh": "kk",
    "nepali": "ne",
    "norwegian": "no",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "slovene": "sl",
    "spanish": "es",
    "swedish": "sv",
    "tajik": "tg",
    "tamil": "ta",
    "turkish": "tr",
    "uzbek": "uz",
}

README_TEMPLATE = """\
---
language:
{lang_yaml}
configs:
{configs_yaml}
license: other
task_categories:
- text-classification
- token-classification
pretty_name: NLTK Stopwords
---

# NLTK Stopwords

Stopword lists from [NLTK](https://www.nltk.org/), covering {n_langs} languages.

Each language is a separate config. Each row is one stopword.

## Usage

```python
from datasets import load_dataset

# Load one language
ds = load_dataset("nltk-data-hub/stopwords", "portuguese")
words = ds["stopwords"]["word"]

# Load all languages
for lang in {lang_list_repr}:
    ds = load_dataset("nltk-data-hub/stopwords", lang)
    print(lang, ds["stopwords"].num_rows)
```

## Schema

| Column | Type | Description |
|---|---|---|
| `word` | `string` | The stopword |

## Languages and word counts

| Language | BCP-47 | Count |
|---|---|---|
{lang_stats}

## Source

Originally distributed as part of `nltk.download('stopwords')`.
Converted to Parquet for use with the HuggingFace `datasets` library.

## Citation

```bibtex
@book{nltk,
  author    = {Bird, Steven and Klein, Ewan and Loper, Edward},
  title     = {Natural Language Processing with Python},
  publisher = {O'Reilly Media},
  year      = {2009},
  url       = {https://www.nltk.org/}
}
```
"""


def build_per_language(outdir):
    """Write one parquet file per language under outdir/<lang>/stopwords.parquet."""
    from nltk.corpus import stopwords as sw

    langs = sorted(sw.fileids())
    counts = {}
    for lang in langs:
        words = sw.words(lang)
        df = pd.DataFrame({"word": words})
        lang_dir = os.path.join(outdir, lang)
        os.makedirs(lang_dir, exist_ok=True)
        df.to_parquet(os.path.join(lang_dir, "stopwords.parquet"), index=False)
        counts[lang] = len(words)
        print(f"  {lang}: {len(words)} words")

    return langs, counts


def build_readme(langs, counts):
    lang_yaml = "\n".join(f"- {LANG_CODES.get(l, l)}" for l in langs)

    configs_yaml = "\n".join(
        f"- config_name: {lang}\n"
        f"  data_files:\n"
        f"  - split: stopwords\n"
        f"    path: data/{lang}/stopwords.parquet"
        for lang in langs
    )

    lang_stats = "\n".join(
        f"| {lang} | {LANG_CODES.get(lang, '?')} | {counts[lang]:,} |" for lang in langs
    )

    lang_list_repr = repr(langs)

    return (
        README_TEMPLATE.replace("{lang_yaml}", lang_yaml)
        .replace("{configs_yaml}", configs_yaml)
        .replace("{n_langs}", str(len(langs)))
        .replace("{lang_list_repr}", lang_list_repr)
        .replace("{lang_stats}", lang_stats)
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_stopwords.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_stopwords_v2"
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    print("Building per-language parquet files...")
    langs, counts = build_per_language(os.path.join(outdir, "data"))
    print(f"  {len(langs)} languages, {sum(counts.values()):,} total words")

    print("Building README.md...")
    readme = build_readme(langs, counts)
    readme_path = os.path.join(outdir, "README.md")
    open(readme_path, "w").write(readme)

    # Create / ensure repo exists
    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    # Delete old flat parquet if present
    print("Removing old flat data/stopwords.parquet...")
    try:
        api.delete_file(
            path_in_repo="data/stopwords.parquet",
            repo_id=REPO_ID,
            repo_type="dataset",
        )
    except Exception:
        pass  # didn't exist, fine

    # Upload all per-language parquets
    print("Uploading per-language parquet files...")
    for lang in langs:
        local_path = os.path.join(outdir, "data", lang, "stopwords.parquet")
        api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=f"data/{lang}/stopwords.parquet",
            repo_id=REPO_ID,
            repo_type="dataset",
        )
        print(f"  uploaded {lang}")

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
