"""Build and push the unified 'all' config for nltk-data-hub/gazetteers.

Collects every name from all gazetteer sources, tags each entry with a
category, deduplicates by (word, category), and uploads a single parquet
as the 'all' config.

Schema:
  word      (string) — the gazetteer entry
  category  (string) — one of:
              country     sovereign nations and territories
              city        all populated places (cities, towns, capitals)
              region      all geographic regions — from US states and Canadian
                          provinces to continents and macro-regions
              nationality     nationality adjectives
              other       entries that don't fit the above (e.g. abbreviations)

Access:
  from datasets import load_dataset
  ds = load_dataset("nltk-data-hub/gazetteers", "all")
  df = ds["gazetteers"].to_pandas()   # word, category columns

  # Via NLTK (returns JSON strings, one per line):
  import json, nltk
  entries = [json.loads(w) for w in nltk.corpus.gazetteers.words("all")]

Prerequisite:
    Run download_geo.py first to fetch the geographic source files:
        python download_geo.py [--geo-dir ~/nltk_data/geo]

Usage:
    python push_gazetteers_all.py <hf_token> [--geo-dir <path>]

    --geo-dir   Directory containing the geo/ subdirectories produced by
                download_geo.py. Default: ~/nltk_data/geo
"""

import csv
import json
import os
import shutil
import sys

import pandas as pd
from huggingface_hub import HfApi

REPO_ID = "nltk-data-hub/gazetteers"
SPLIT = "gazetteers"
CONFIG = "all"

NLTK_CORPUS = os.path.expanduser("~/nltk_data/corpora/gazetteers")
_DEFAULT_GEO_DIR = os.path.expanduser("~/nltk_data/geo")
GEO_DIR = _DEFAULT_GEO_DIR  # overridden in main() via --geo-dir

# ---------------------------------------------------------------------------
# ISO 3166-2 → unified category
# City-like entries → city; everything else → region
# ---------------------------------------------------------------------------

_ISO_CITY = {
    "CITY", "METROPOLITAN CITY", "CITY WITH COUNTY RIGHTS",
    "SPECIAL ADMINISTRATIVE CITY", "METROPOLITAN ADMINISTRATION",
    "CAPITAL CITY", "CAPITAL", "CAPITAL DISTRICT",
    "CAPITAL TERRITORY", "FEDERAL CAPITAL TERRITORY",
}


def _iso_category(raw):
    raw = raw.strip().upper()
    return "city" if raw in _ISO_CITY else "region"


# ---------------------------------------------------------------------------
# Source readers — each yields (word, category) tuples
# ---------------------------------------------------------------------------

def _nltk_file(filename, category):
    path = os.path.join(NLTK_CORPUS, filename)
    with open(path, encoding="latin-1") as f:
        for line in f:
            word = line.strip()
            if word and not word.startswith(";"):
                yield (word, category)


def _source_original():
    yield from _nltk_file("countries.txt", "country")
    yield from _nltk_file("isocountries.txt", "country")
    yield from _nltk_file("nationalities.txt", "nationality")
    yield from _nltk_file("caprovinces.txt", "region")
    yield from _nltk_file("mexstates.txt", "region")
    yield from _nltk_file("usstates.txt", "region")
    yield from _nltk_file("usstateabbrev.txt", "other")
    yield from _nltk_file("uscities.txt", "city")


def _source_worldcities():
    path = os.path.join(GEO_DIR, "geonames", "cities15000.txt")
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 15:
                name = parts[1].strip()
                if name:
                    yield (name, "city")


def _source_un_m49():
    path = os.path.join(GEO_DIR, "un_m49", "all.csv")
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("name", "").strip()
            if name:
                yield (name, "country")


def _source_iso3166_2():
    path = os.path.join(GEO_DIR, "iso3166_2", "subdivisions.csv")
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("subdivision_name", "").strip()
            raw_cat = row.get("category", "").strip()
            if name:
                yield (name, _iso_category(raw_cat))


def _source_cldr_en():
    path = os.path.join(GEO_DIR, "cldr", "territories_en.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    territories = d["main"]["en"]["localeDisplayNames"]["territories"]
    for code, name in territories.items():
        name = name.strip()
        if not name:
            continue
        if code.isdigit():
            # UN numeric = continent / macro-region
            yield (name, "region")
        else:
            # ISO 3166-1 alpha-2 = country/territory
            yield (name, "country")


def _source_wikidata():
    path = os.path.join(GEO_DIR, "wikidata", "countries.csv")
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            country = row.get("countryLabel", "").strip()
            capital = row.get("capitalLabel", "").strip()
            nationality = row.get("demonymLabel", "").strip()
            if country and not country.startswith("http"):
                yield (country, "country")
            if capital and not capital.startswith("http"):
                yield (capital, "city")
            if nationality and not nationality.startswith("http"):
                yield (nationality, "nationality")


def _source_osm_capitals():
    path = os.path.join(GEO_DIR, "osm", "capitals.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for el in data.get("elements", []):
        name = el.get("tags", {}).get("name", "").strip()
        if name:
            yield (name, "city")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

CATEGORY_ORDER = ["country", "city", "region", "nationality", "other"]


def build_all():
    seen = set()  # (word, category) pairs
    rows = []

    sources = [
        ("nltk-original", _source_original()),
        ("geonames", _source_worldcities()),
        ("un-m49", _source_un_m49()),
        ("iso3166-2", _source_iso3166_2()),
        ("cldr-en", _source_cldr_en()),
        ("wikidata", _source_wikidata()),
        ("osm", _source_osm_capitals()),
    ]

    for src_name, gen in sources:
        src_count = 0
        for word, category in gen:
            key = (word.lower(), category)
            if key not in seen:
                seen.add(key)
                rows.append({"word": word, "category": category})
            src_count += 1
        print(f"  {src_name}: processed {src_count:,} entries")

    df = pd.DataFrame(rows, columns=["word", "category"])

    # Sort by category order then word
    cat_rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    df["_rank"] = df["category"].map(lambda c: cat_rank.get(c, 99))
    df = df.sort_values(["_rank", "word"], key=lambda s: s.str.lower() if s.dtype == object else s)
    df = df.drop(columns=["_rank"]).reset_index(drop=True)

    print(f"\n  Total unique (word, category) pairs: {len(df):,}")
    print("  Category breakdown:")
    for cat, n in df["category"].value_counts().sort_index().items():
        print(f"    {cat:<15} {n:>7,}")

    return df


# ---------------------------------------------------------------------------
# README updater — adds the 'all' config entry to existing README
# ---------------------------------------------------------------------------

def _all_config_yaml():
    return (
        f"- config_name: {CONFIG}\n"
        f"  data_files:\n"
        f"  - split: {SPLIT}\n"
        f"    path: data/{CONFIG}/{SPLIT}.parquet"
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("hf_token")
    parser.add_argument(
        "--geo-dir",
        default=_DEFAULT_GEO_DIR,
        help="Directory with geo/ subdirs from download_geo.py (default: ~/nltk_data/geo)",
    )
    args = parser.parse_args()

    global GEO_DIR
    GEO_DIR = os.path.expanduser(args.geo_dir)
    if not os.path.isdir(GEO_DIR):
        print(f"Error: --geo-dir {GEO_DIR!r} does not exist.")
        print("Run download_geo.py first to fetch the geographic source files.")
        sys.exit(1)

    token = args.hf_token
    api = HfApi(token=token)

    print("Building unified 'all' gazetteer...")
    df = build_all()

    # Write parquet
    outdir = f"/tmp/nltk_gazetteers_all/data/{CONFIG}"
    if os.path.exists("/tmp/nltk_gazetteers_all"):
        shutil.rmtree("/tmp/nltk_gazetteers_all")
    os.makedirs(outdir)

    parquet_path = os.path.join(outdir, f"{SPLIT}.parquet")
    df.to_parquet(parquet_path, index=False)
    size = os.path.getsize(parquet_path)
    print(f"\n  Written: {parquet_path} ({size:,} bytes)")

    print(f"\nUploading to {REPO_ID} config '{CONFIG}'...")
    api.upload_file(
        path_or_fileobj=parquet_path,
        path_in_repo=f"data/{CONFIG}/{SPLIT}.parquet",
        repo_id=REPO_ID,
        repo_type="dataset",
    )

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")
    print(f"\nUsage:")
    print(f"  from datasets import load_dataset")
    print(f"  ds = load_dataset('{REPO_ID}', '{CONFIG}')")
    print(f"  df = ds['{SPLIT}'].to_pandas()")


if __name__ == "__main__":
    main()
