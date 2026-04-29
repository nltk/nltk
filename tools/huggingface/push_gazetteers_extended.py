"""Push extended geographic gazetteers to nltk-data-hub/gazetteers.

Adds 7 new configs on top of the original 8 (countries, isocountries, etc.):

  worldcities    — 33,602 cities ≥15k pop (GeoNames, CC-BY 4.0)
                   schema: name, ascii_name, country_code, population,
                           latitude, longitude, timezone
  un-m49         — 249 countries with UN M49 regional codes (public domain)
                   schema: name, alpha2, alpha3, m49_code, region, sub_region
  iso3166-2      — 6,260 country subdivisions (Apache 2.0)
                   schema: name, code, country_code, category
  cldr-{lang}    — 73 configs × ~316 territory names in each language
                   schema: code, name   (territory CLDR code + localised name)
                   Unicode License
  wikidata-countries — countries with capitals and demonyms (CC0)
                   schema: name, capital, demonym
  osm-capitals   — 209 OSM capital city nodes (ODbL)
                   schema: name, country_code, latitude, longitude

Natural Earth shapefile is skipped (requires geopandas/pyshp).

All configs keep `name` as the primary gazetteer string column.

Prerequisite:
    Run download_geo.py first to fetch the geographic source files:
        python download_geo.py [--geo-dir ~/nltk_data/geo]

Usage:
    python push_gazetteers_extended.py <hf_token> [--geo-dir <path>]

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
_DEFAULT_GEO_DIR = os.path.expanduser("~/nltk_data/geo")
GEO_DIR = _DEFAULT_GEO_DIR  # overridden in main() via --geo-dir

# ---------------------------------------------------------------------------
# Original 8 configs (names only, for README reference)
# ---------------------------------------------------------------------------

ORIGINAL_CONFIGS = [
    ("countries", "289 country names", "GFDL (Wikipedia)"),
    ("isocountries", "234 ISO country names", "public domain"),
    ("nationalities", "200 nationality adjectives", "public domain"),
    ("caprovinces", "14 Canadian provinces", "—"),
    ("mexstates", "32 Mexican states", "—"),
    ("usstates", "52 US states", "—"),
    ("usstateabbrev", "137 US state abbreviations", "—"),
    ("uscities", "255 US cities 100k+ population", "GFDL (Wikipedia)"),
]

# ---------------------------------------------------------------------------
# CLDR languages
# ---------------------------------------------------------------------------

CLDR_LANGS = [
    "af", "ar", "az", "be", "bg", "bn", "bs", "ca", "cs", "cy",
    "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fil",
    "fr", "ga", "gl", "gu", "he", "hi", "hr", "hu", "hy", "id",
    "is", "it", "ja", "ka", "kk", "km", "kn", "ko", "lt", "lv",
    "mk", "ml", "mn", "mr", "ms", "my", "nb", "ne", "nl", "or",
    "pa", "pl", "pt", "ro", "ru", "si", "sk", "sl", "sq", "sr",
    "sv", "sw", "ta", "te", "th", "tk", "tr", "uk", "ur", "uz",
    "vi", "zh", "zu",
]

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _parquet(df, outdir, cfg):
    cfg_dir = os.path.join(outdir, cfg)
    os.makedirs(cfg_dir, exist_ok=True)
    df.to_parquet(os.path.join(cfg_dir, f"{SPLIT}.parquet"), index=False)


def build_worldcities(outdir):
    path = os.path.join(GEO_DIR, "geonames", "cities15000.txt")
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 19:
                continue
            name = parts[1].strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "ascii_name": parts[2].strip(),
                "country_code": parts[8].strip(),
                "population": int(parts[14]) if parts[14].strip() else 0,
                "latitude": float(parts[4]) if parts[4].strip() else None,
                "longitude": float(parts[5]) if parts[5].strip() else None,
                "timezone": parts[17].strip(),
            })
    df = pd.DataFrame(rows, columns=[
        "name", "ascii_name", "country_code",
        "population", "latitude", "longitude", "timezone",
    ])
    _parquet(df, outdir, "worldcities")
    print(f"  worldcities: {len(df):,} rows")
    return len(df)


def build_un_m49(outdir):
    path = os.path.join(GEO_DIR, "un_m49", "all.csv")
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "alpha2": row.get("alpha-2", "").strip(),
                "alpha3": row.get("alpha-3", "").strip(),
                "m49_code": row.get("country-code", "").strip(),
                "region": row.get("region", "").strip(),
                "sub_region": row.get("sub-region", "").strip(),
            })
    df = pd.DataFrame(rows, columns=[
        "name", "alpha2", "alpha3", "m49_code", "region", "sub_region",
    ])
    _parquet(df, outdir, "un-m49")
    print(f"  un-m49: {len(df):,} rows")
    return len(df)


def build_iso3166_2(outdir):
    path = os.path.join(GEO_DIR, "iso3166_2", "subdivisions.csv")
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("subdivision_name", "").strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "code": row.get("subdivision_code_iso3166-2", "").strip(),
                "country_code": row.get("country_code_alpha2", "").strip(),
                "category": row.get("category", "").strip(),
            })
    df = pd.DataFrame(rows, columns=["name", "code", "country_code", "category"])
    _parquet(df, outdir, "iso3166-2")
    print(f"  iso3166-2: {len(df):,} rows")
    return len(df)


def build_cldr(outdir):
    cldr_dir = os.path.join(GEO_DIR, "cldr")
    total = 0
    for lang in CLDR_LANGS:
        path = os.path.join(cldr_dir, f"territories_{lang}.json")
        if not os.path.exists(path):
            print(f"  [skip] cldr-{lang}: file not found")
            continue
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        try:
            territories = d["main"][lang]["localeDisplayNames"]["territories"]
        except KeyError:
            print(f"  [skip] cldr-{lang}: unexpected JSON structure")
            continue
        rows = [
            {"code": code, "name": label.strip()}
            for code, label in territories.items()
            if label.strip()
        ]
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=["code", "name"])
        cfg = f"cldr-{lang}"
        _parquet(df, outdir, cfg)
        total += len(df)
    print(f"  cldr-* ({len(CLDR_LANGS)} langs): {total:,} total rows")
    return total


def build_wikidata_countries(outdir):
    path = os.path.join(GEO_DIR, "wikidata", "countries.csv")
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("countryLabel", "").strip()
            if not name or name.startswith("http"):
                continue
            rows.append({
                "name": name,
                "capital": row.get("capitalLabel", "").strip(),
                "demonym": row.get("demonymLabel", "").strip(),
            })
    df = pd.DataFrame(rows, columns=["name", "capital", "demonym"])
    _parquet(df, outdir, "wikidata-countries")
    print(f"  wikidata-countries: {len(df):,} rows")
    return len(df)


def build_osm_capitals(outdir):
    path = os.path.join(GEO_DIR, "osm", "capitals.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue
        rows.append({
            "name": name,
            "country_code": tags.get("is_in:country_code", tags.get("addr:country", "")).strip(),
            "latitude": el.get("lat"),
            "longitude": el.get("lon"),
        })
    df = pd.DataFrame(rows, columns=["name", "country_code", "latitude", "longitude"])
    _parquet(df, outdir, "osm-capitals")
    print(f"  osm-capitals: {len(df):,} rows")
    return len(df)


# ---------------------------------------------------------------------------
# README builder
# ---------------------------------------------------------------------------

def _config_yaml_entry(cfg):
    return (
        f"- config_name: {cfg}\n"
        f"  data_files:\n"
        f"  - split: {SPLIT}\n"
        f"    path: data/{cfg}/{SPLIT}.parquet"
    )


def build_readme(counts):
    # YAML: original 8 + new configs
    original_cfgs = [c for c, _, _ in ORIGINAL_CONFIGS]
    new_cfgs = [
        "worldcities", "un-m49", "iso3166-2",
        *[f"cldr-{lang}" for lang in CLDR_LANGS],
        "wikidata-countries", "osm-capitals",
    ]
    all_cfgs = original_cfgs + new_cfgs
    yaml_block = "\n".join(_config_yaml_entry(c) for c in all_cfgs)

    # Table rows for original configs
    orig_rows = "\n".join(
        f"| `{cfg}` | {desc} | {lic} |"
        for cfg, desc, lic in ORIGINAL_CONFIGS
    )

    # Table rows for new configs
    cldr_row = f"| `cldr-{{lang}}` | Territory names in 73 languages | Unicode License |"
    new_rows = f"""\
| `worldcities` | {counts.get('worldcities', '?'):,} cities ≥15k population | CC-BY 4.0 (GeoNames) |
| `un-m49` | {counts.get('un-m49', '?')} countries with UN M49 regional codes | public domain |
| `iso3166-2` | {counts.get('iso3166-2', '?'):,} country subdivisions (states, provinces, …) | Apache 2.0 |
{cldr_row}
| `wikidata-countries` | {counts.get('wikidata-countries', '?')} countries with capital and demonym | CC0 (Wikidata) |
| `osm-capitals` | {counts.get('osm-capitals', '?')} capital cities (OSM, ODbL) | ODbL |"""

    return f"""\
---
configs:
{yaml_block}
license: gfdl
task_categories:
- token-classification
pretty_name: NLTK Gazetteers (Extended)
---

# NLTK Gazetteers (Extended)

Geographic and demographic word lists, extended from the original
[NLTK](https://www.nltk.org/) gazetteers corpus.

Each config is one list; each row is one entry.

## Original configs (NLTK gazetteers corpus)

| Config | Description | License |
|---|---|---|
{orig_rows}

**Schema:** `name` (string) — one entry per row.

## Extended configs (new sources)

| Config | Description | License |
|---|---|---|
{new_rows}

### Schema by config

| Config | Columns |
|---|---|
| `worldcities` | `name, ascii_name, country_code, population, latitude, longitude, timezone` |
| `un-m49` | `name, alpha2, alpha3, m49_code, region, sub_region` |
| `iso3166-2` | `name, code, country_code, category` |
| `cldr-{{lang}}` | `code, name` |
| `wikidata-countries` | `name, capital, demonym` |
| `osm-capitals` | `name, country_code, latitude, longitude` |

All configs include `name` as the primary gazetteer string.

## CLDR language codes

73 configs: {', '.join(f'`cldr-{lang}`' for lang in CLDR_LANGS[:20])}, … and {len(CLDR_LANGS) - 20} more.

## Usage

```python
from datasets import load_dataset

# World cities (with country, population, coords)
ds = load_dataset("nltk-data-hub/gazetteers", "worldcities")
cities = ds["gazetteers"].to_pandas()

# Territory names in French
ds = load_dataset("nltk-data-hub/gazetteers", "cldr-fr")
territories = ds["gazetteers"]["name"]

# Countries with capitals and demonyms
ds = load_dataset("nltk-data-hub/gazetteers", "wikidata-countries")
df = ds["gazetteers"].to_pandas()
```

## Via NLTK

```python
import nltk
nltk.download("gazetteers")

nltk.corpus.gazetteers.words("countries.txt")
nltk.corpus.gazetteers.words("uscities.txt")
```

## License

- Original configs: GFDL (Wikipedia-derived) / public domain
- `worldcities`: CC-BY 4.0 — [GeoNames](https://www.geonames.org/)
- `un-m49`: public domain — UN Statistics Division
- `iso3166-2`: Apache 2.0 — [ipregistry/iso3166](https://github.com/ipregistry/iso3166)
- `cldr-*`: Unicode License — [CLDR](https://cldr.unicode.org/)
- `wikidata-countries`: CC0 — [Wikidata](https://www.wikidata.org/)
- `osm-capitals`: ODbL — [OpenStreetMap](https://www.openstreetmap.org/)
"""


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

    outdir = "/tmp/nltk_gazetteers_ext/data"
    if os.path.exists("/tmp/nltk_gazetteers_ext"):
        shutil.rmtree("/tmp/nltk_gazetteers_ext")
    os.makedirs(outdir)

    print("Building extended gazetteer parquets...")
    counts = {}
    counts["worldcities"] = build_worldcities(outdir)
    counts["un-m49"] = build_un_m49(outdir)
    counts["iso3166-2"] = build_iso3166_2(outdir)
    build_cldr(outdir)
    counts["wikidata-countries"] = build_wikidata_countries(outdir)
    counts["osm-capitals"] = build_osm_capitals(outdir)

    # Per-lang CLDR counts not tracked individually — sum from files
    counts["cldr"] = sum(
        1 for f in os.listdir(outdir) if f.startswith("cldr-")
    )
    print(f"\n  Total new configs: {len(counts)} groups")

    readme_path = "/tmp/nltk_gazetteers_ext/README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(build_readme(counts))

    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path="/tmp/nltk_gazetteers_ext",
        repo_id=REPO_ID,
        repo_type="dataset",
    )

    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
