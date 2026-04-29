"""Download geographic wordlist sources to wordlists/geo/.

Sources:
  1. GeoNames cities15000     — CC-BY 4.0
  2. UN M49                   — public domain
  3. ISO 3166-2 subdivisions  — Apache 2.0
  4. Natural Earth 10m places — public domain
  5. CLDR territory names     — Unicode License (~30 major langs)
  6. Wikidata countries/caps  — CC0
  7. OSM capitals (Overpass)  — ODbL

Run:
    python download_geo.py
"""

import io
import json
import os
import time
import zipfile

import requests

BASE = os.path.expanduser("~/nltk_data/geo")

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

WIKIDATA_SPARQL = """\
SELECT ?country ?countryLabel ?capital ?capitalLabel ?demonym ?demonymLabel WHERE {
  ?country wdt:P31 wd:Q6256 .
  OPTIONAL { ?country wdt:P36 ?capital . }
  OPTIONAL { ?country wdt:P1549 ?demonym . FILTER(LANG(?demonym) = "en") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
ORDER BY ?countryLabel
"""

OVERPASS_QUERY = """\
[out:json][timeout:90];
node["capital"="yes"]["name"];
out tags 500;
"""


def _mkdir(path):
    os.makedirs(path, exist_ok=True)
    return path


def _get(url, **kwargs):
    resp = requests.get(url, timeout=60, **kwargs)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# 1. GeoNames cities15000
# ---------------------------------------------------------------------------

def download_geonames():
    out_dir = _mkdir(os.path.join(BASE, "geonames"))
    out_file = os.path.join(out_dir, "cities15000.txt")
    if os.path.exists(out_file):
        print(f"  [skip] {out_file} already exists")
        return

    print("  Downloading GeoNames cities15000.zip …")
    resp = _get("https://download.geonames.org/export/dump/cities15000.zip")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        with zf.open("cities15000.txt") as src, open(out_file, "wb") as dst:
            dst.write(src.read())
    size = os.path.getsize(out_file)
    print(f"  → {out_file} ({size:,} bytes)")


# ---------------------------------------------------------------------------
# 2. UN M49
# ---------------------------------------------------------------------------

def download_un_m49():
    out_dir = _mkdir(os.path.join(BASE, "un_m49"))
    out_file = os.path.join(out_dir, "all.csv")
    if os.path.exists(out_file):
        print(f"  [skip] {out_file} already exists")
        return

    url = (
        "https://raw.githubusercontent.com/lukes/"
        "ISO-3166-Countries-with-Regional-Codes/master/all/all.csv"
    )
    print("  Downloading UN M49 …")
    resp = _get(url)
    with open(out_file, "wb") as f:
        f.write(resp.content)
    lines = resp.text.count("\n")
    print(f"  → {out_file} ({lines} rows)")


# ---------------------------------------------------------------------------
# 3. ISO 3166-2 subdivisions
# ---------------------------------------------------------------------------

def download_iso3166_2():
    out_dir = _mkdir(os.path.join(BASE, "iso3166_2"))
    out_file = os.path.join(out_dir, "subdivisions.csv")
    if os.path.exists(out_file):
        print(f"  [skip] {out_file} already exists")
        return

    url = (
        "https://raw.githubusercontent.com/ipregistry/iso3166/"
        "main/subdivisions.csv"
    )
    print("  Downloading ISO 3166-2 subdivisions …")
    resp = _get(url)
    with open(out_file, "wb") as f:
        f.write(resp.content)
    lines = resp.text.count("\n")
    print(f"  → {out_file} ({lines} rows)")


# ---------------------------------------------------------------------------
# 4. Natural Earth 10m populated places
# ---------------------------------------------------------------------------

def download_natural_earth():
    out_dir = _mkdir(os.path.join(BASE, "natural_earth"))
    out_file = os.path.join(out_dir, "ne_10m_populated_places.geojson")
    if os.path.exists(out_file):
        print(f"  [skip] {out_file} already exists")
        return

    # Use the ZIP from the GitHub releases (smaller than raw GeoJSON in the repo)
    url = (
        "https://naciscdn.org/naturalearth/10m/cultural/"
        "ne_10m_populated_places.zip"
    )
    print("  Downloading Natural Earth 10m populated places …")
    try:
        resp = _get(url)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            shp_file = next((n for n in names if n.endswith(".shp")), None)
            if shp_file:
                # Save all shapefile components
                for name in names:
                    zf.extract(name, out_dir)
                print(f"  → {out_dir}/ (shapefile, {len(names)} files)")
                return
    except Exception as e:
        print(f"  naciscdn failed ({e}), trying GitHub GeoJSON …")

    # Fallback: direct GeoJSON from GitHub (large but reliable)
    url2 = (
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson/ne_10m_populated_places.geojson"
    )
    resp = _get(url2, stream=True)
    written = 0
    with open(out_file, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            written += len(chunk)
    print(f"  → {out_file} ({written:,} bytes)")


# ---------------------------------------------------------------------------
# 5. CLDR territory names (~30 major languages)
# ---------------------------------------------------------------------------

def download_cldr():
    out_dir = _mkdir(os.path.join(BASE, "cldr"))
    base_url = (
        "https://raw.githubusercontent.com/unicode-org/cldr-json/main/"
        "cldr-json/cldr-localenames-full/main/{lang}/territories.json"
    )
    ok = 0
    skip = 0
    for lang in CLDR_LANGS:
        out_file = os.path.join(out_dir, f"territories_{lang}.json")
        if os.path.exists(out_file):
            skip += 1
            continue
        url = base_url.format(lang=lang)
        try:
            resp = _get(url)
            with open(out_file, "wb") as f:
                f.write(resp.content)
            ok += 1
            time.sleep(0.05)  # be polite to GitHub raw
        except requests.HTTPError as e:
            print(f"  [warn] CLDR {lang}: {e}")
    if skip:
        print(f"  [skip] {skip} CLDR files already downloaded")
    print(f"  → {out_dir}/ ({ok} new files, {len(CLDR_LANGS)} total langs)")


# ---------------------------------------------------------------------------
# 6. Wikidata SPARQL — countries, capitals, demonyms
# ---------------------------------------------------------------------------

def download_wikidata():
    out_dir = _mkdir(os.path.join(BASE, "wikidata"))
    out_file = os.path.join(out_dir, "countries.csv")
    if os.path.exists(out_file):
        print(f"  [skip] {out_file} already exists")
        return

    print("  Querying Wikidata SPARQL …")
    resp = requests.get(
        "https://query.wikidata.org/sparql",
        params={"query": WIKIDATA_SPARQL},
        headers={
            "Accept": "text/csv",
            "User-Agent": "nltk-gazetteer-builder/1.0 (https://nltk.org)",
        },
        timeout=120,
    )
    resp.raise_for_status()
    with open(out_file, "wb") as f:
        f.write(resp.content)
    lines = resp.text.count("\n")
    print(f"  → {out_file} ({lines} rows)")


# ---------------------------------------------------------------------------
# 7. OpenStreetMap capitals via Overpass
# ---------------------------------------------------------------------------

def download_osm():
    out_dir = _mkdir(os.path.join(BASE, "osm"))
    out_file = os.path.join(out_dir, "capitals.json")
    if os.path.exists(out_file):
        print(f"  [skip] {out_file} already exists")
        return

    print("  Querying OSM Overpass API …")
    resp = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": OVERPASS_QUERY},
        headers={"User-Agent": "nltk-gazetteer-builder/1.0 (https://nltk.org)"},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n = len(data.get("elements", []))
    print(f"  → {out_file} ({n} elements)")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    import argparse

    global BASE
    parser = argparse.ArgumentParser(
        description="Download geographic source files for push_gazetteers_*.py"
    )
    parser.add_argument(
        "--geo-dir",
        default=BASE,
        help=f"Output directory (default: {BASE})",
    )
    args = parser.parse_args()
    BASE = os.path.expanduser(args.geo_dir)

    print(f"Output base: {BASE}\n")

    print("[1/7] GeoNames cities15000")
    download_geonames()

    print("\n[2/7] UN M49")
    download_un_m49()

    print("\n[3/7] ISO 3166-2 subdivisions")
    download_iso3166_2()

    print("\n[4/7] Natural Earth 10m populated places")
    download_natural_earth()

    print("\n[5/7] CLDR territory names")
    download_cldr()

    print("\n[6/7] Wikidata countries / capitals / demonyms")
    download_wikidata()

    print("\n[7/7] OSM capitals (Overpass)")
    download_osm()

    print("\nDone.")


if __name__ == "__main__":
    main()
