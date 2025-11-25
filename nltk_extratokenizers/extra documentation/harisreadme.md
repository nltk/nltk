Verifying NLTK Entry-Point Data Loading and nltk-punkt Package
This README explains how to verify that:


Your custom NLTK clone (this repo) is being used.


The nltk-punkt pip package is installed and exposes all required data via nltk_data entry points.


The patched nltk.data.find() correctly loads multiple NLTK datasets from pip, not via nltk.download().


These tests work on Windows, Linux, and macOS, but the paths here use Windows examples.

0. Assumptions
These instructions assume:


You are inside this repo:
C:\...\ENGG4450_labs\NLTK\nltk_Group1_ENGG4450


You installed this NLTK clone in editable mode:
pip install -e .



You installed your custom NLTK data package:
cd nltk_punkt
pip install --force-reinstall dist\nltk_punkt-0.1.0-*.whl
cd ..



You are using the same Python environment for all steps.



1. Verify Your Local NLTK Clone Is Used
Open PowerShell in the repo root and run:
python

Then inside Python:
import nltk, inspect
import nltk.data as nd

print("nltk imported from:", nltk.__file__)
print("data.py imported from:", inspect.getfile(nd))

✔ Expected
Both paths should point inside this repo, for example:
...\nltk_Group1_ENGG4450\nltk\__init__.py
...\nltk_Group1_ENGG4450\nltk\data.py

If they point to site-packages\nltk, reinstall the clone:
pip install -e .


2. Verify the nltk-punkt Package Is Installed
Exit Python (exit()), then run:
python -m pip show nltk-punkt

✔ Expected
You should see:
Name: nltk-punkt
Version: 0.1.0
Location: ...\site-packages

If not installed, run:
cd nltk_punkt
python -m pip install --force-reinstall dist\nltk_punkt-0.1.0-*.whl
cd ..


3. Confirm the nltk_data Entry Points
Start Python:
python

Run:
import importlib.metadata as m

print("nltk_data entry points:")
for ep in m.entry_points(group="nltk_data"):
    print(" ", ep)

✔ Expected
You should see these entries (or more):
EntryPoint(name='punkt', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='averaged_perceptron_tagger', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='stopwords', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='wordnet', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='omw-1.4', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='snowball_data', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='names', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='brown', value='nltk_punkt.data', group='nltk_data')
EntryPoint(name='movie_reviews', value='nltk_punkt.data', group='nltk_data')

If punkt is missing, the wheel wasn’t built correctly.

4. Verify That find() Resolves Resources From the Wheel
Still in Python:
from nltk.data import find

print("Punkt:", find("tokenizers/punkt/english.pickle"))
print("Tagger:", find("taggers/averaged_perceptron_tagger/averaged_perceptron_tagger.pickle"))
print("Stopwords:", find("corpora/stopwords"))
print("WordNet:", find("corpora/wordnet"))
print("OMW:", find("corpora/omw-1.4"))
print("Snowball:", find("snowball_data"))
print("Names:", find("corpora/names"))
print("Brown:", find("corpora/brown"))
print("Movie Reviews:", find("corpora/movie_reviews"))

✔ Expected
Each one returns a FileSystemPathPointer.
To inspect the actual file location:
p = find("tokenizers/punkt/english.pickle")
print("Punkt actual file:", p._path)

You should see something like:
...\site-packages\nltk_punkt\data\tokenizers\punkt\english.pickle

If NLTK returns a path such as:
C:\Users\<username>\AppData\Roaming\nltk_data\...

→ you still have local data installed. Either delete ~/nltk_data/ or temporarily rename it.

5. Test Real NLTK Functionality (All Should Work Without Downloads)
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords, wordnet as wn, names, brown, movie_reviews
from nltk import pos_tag

# Punkt tokenizer
print("Sentences:", sent_tokenize("Hello world. This is a test. Another sentence here."))

# Stopwords
print("Stopwords sample:", stopwords.words("english")[:10])

# WordNet
print("WordNet synsets for 'dog':", wn.synsets("dog")[:3])

# Names corpus
print("Names sample:", names.words()[:10])

# Brown corpus
print("Brown categories:", brown.categories()[:5])

# Movie reviews
print("Movie review file count:", len(movie_reviews.fileids()))

# POS tagger
print("POS tag sample:", pos_tag(word_tokenize("Hello, how are you today?")))

✔ Expected
All of these must work without nltk.download().
If any LookupError occurs, that dataset is either:


missing from the wheel, or


being overridden by a local nltk_data folder.



6. Final Checklist (All Must Be ✔)
CheckResultNLTK imports from this repo✔nltk-punkt (0.1.0) installed✔Entry points list all 9 data packages✔find() resolves to nltk_punkt/data✔Tokenizer works✔Tagger works✔Stopwords work✔WordNet & OMW work✔Brown + movie_reviews work✔
If all boxes are checked, your fix for Issue #3413 is fully implemented.

If you want, I can also generate a unit test script (test_pip_data_loading.py) that your teammates can run automatically.