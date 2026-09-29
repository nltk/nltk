"""Run as the unprivileged runtime user of the #3928 image: the archives root
installed are closed to this account, the extracted files are what it reads,
and every entry point the reporter's application would use works."""

import os
import stat
import sys

root = "/usr/local/lib/nltk_data"
zips = [
    os.path.join(root, "corpora", name)
    for name in ("wordnet.zip", "omw-1.4.zip", "omw-2.0.zip")
]
for path in zips:
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600, (path, oct(mode))
    assert not os.access(path, os.R_OK), path + " is readable by the runtime user"
assert os.access(os.path.join(root, "corpora", "wordnet", "data.noun"), os.R_OK)

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer

assert WordNetLemmatizer().lemmatize("bearings") == "bearing"
assert "the" in stopwords.words("english")
assert wordnet.synset("dog.n.01").definition()
assert "cane" in wordnet.synset("dog.n.01").lemma_names("ita")  # omw-2.0
# The startup idiom, pointed at the shared root: judged installed by the
# extracted files without touching the network or the private archive.
for package in ("wordnet", "omw-1.4", "omw-2.0", "stopwords"):
    assert nltk.download(package, download_dir=root, quiet=True), package
print(
    "root-installed data serves",
    os.environ.get("USER") or os.getuid(),
    "through the extracted files",
)
sys.exit(0)
