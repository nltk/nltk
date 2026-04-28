"""Push NLTK names corpus to nltk-data-hub/names on HuggingFace.

One config per gender (female, male), one parquet file per config.

Usage:
    python push_names.py <hf_token>
"""

import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/names"
SPLIT = "names"
CONFIGS = ["female", "male"]

README_TEMPLATE = """\
---
configs:
{configs_yaml}
license: other
task_categories:
- text-classification
pretty_name: NLTK Names Corpus
---

# NLTK Names Corpus

Name lists from [NLTK](https://www.nltk.org/), split by gender.

Each gender is a separate config. Each row is one name.

## Usage

```python
from datasets import load_dataset

ds = load_dataset("nltk-data-hub/names", "female")
names = ds["names"]["name"]
```

## Schema

| Column | Type | Description |
|---|---|---|
| `name` | `string` | The name |

## Configs

| Config | Count |
|---|---|
{config_stats}

## Source

Originally distributed as part of `nltk.download('names')`.
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


def build_per_config(outdir):
    from nltk.corpus import names as names_corpus

    counts = {}
    for cfg in CONFIGS:
        words = names_corpus.words(cfg + ".txt")
        df = pd.DataFrame({"name": words})
        cfg_dir = os.path.join(outdir, cfg)
        os.makedirs(cfg_dir, exist_ok=True)
        df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)
        counts[cfg] = len(words)
        print(f"  {cfg}: {len(words)} names")
    return counts


def build_readme(counts):
    configs_yaml = "\n".join(
        f"- config_name: {cfg}\n"
        f"  data_files:\n"
        f"  - split: {SPLIT}\n"
        f"    path: data/{cfg}/{SPLIT}.parquet"
        for cfg in CONFIGS
    )
    config_stats = "\n".join(f"| {cfg} | {counts[cfg]:,} |" for cfg in CONFIGS)
    return README_TEMPLATE.replace("{configs_yaml}", configs_yaml).replace(
        "{config_stats}", config_stats
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python push_names.py <hf_token>")
        sys.exit(1)

    token = sys.argv[1]
    api = HfApi(token=token)

    outdir = "/tmp/nltk_names"
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    print("Building per-config parquet files...")
    counts = build_per_config(os.path.join(outdir, "data"))
    total = sum(counts.values())
    print(f"  {len(CONFIGS)} configs, {total:,} total names")

    print("Building README.md...")
    readme = build_readme(counts)
    readme_path = os.path.join(outdir, "README.md")
    open(readme_path, "w").write(readme)

    print(f"\nCreating repo {REPO_ID}...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)

    print("Uploading per-config parquet files...")
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
