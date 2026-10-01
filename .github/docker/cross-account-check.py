"""Run as the unprivileged runtime user of the #3928 image: the archives root
installed are closed to this account, the extracted files are what it reads,
every entry point the reporter's application would use works, and the trust
decision holds against what this account can actually do to the shared root
and to a root of its own (the other-owner cases a single-account test host
cannot stage: here root's files really are another account's)."""

import os
import stat
import sys
import warnings

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
import nltk.data
from nltk import downloader, pathsec
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer

assert WordNetLemmatizer().lemmatize("bearings") == "bearing"
assert "the" in stopwords.words("english")
assert wordnet.synset("dog.n.01").definition()
assert "cane" in wordnet.synset("dog.n.01").lemma_names("ita")  # omw-2.0
# omw-1.4, which the reporter installs, read through its own reader
from nltk.corpus.reader import CorpusReader
from nltk.corpus.reader.wordnet import WordNetCorpusReader
from nltk.corpus.util import LazyCorpusLoader

omw14 = LazyCorpusLoader(
    "omw-1.4", CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"
)
assert len(omw14.fileids()) == 31, omw14.fileids()
wn14 = WordNetCorpusReader(nltk.data.find("corpora/wordnet"), omw14)
assert "cane" in wn14.synset("dog.n.01").lemma_names("ita")  # omw-1.4
# The startup idiom, pointed at the shared root: judged installed by the
# extracted files without touching the network or the private archive.
for package in ("wordnet", "omw-1.4", "omw-2.0", "stopwords"):
    assert nltk.download(package, download_dir=root, quiet=True), package

# ---------------------------------------------------------------------------
# The trust decision, attacked as this account.
# ---------------------------------------------------------------------------
assert os.geteuid() != 0 and pathsec.ENFORCE
corpora = os.path.join(root, "corpora")
wn_dir = os.path.join(corpora, "wordnet")
noun = os.path.join(wn_dir, "data.noun")
# 1. root's files are trusted for what they are: owned by root, private
st = os.stat(noun)
assert st.st_uid == 0 and not st.st_mode & (stat.S_IWGRP | stat.S_IWOTH), oct(
    st.st_mode
)
assert pathsec.is_private_dir(wn_dir) and pathsec.is_private_dir(corpora)
assert isinstance(nltk.data.find("corpora/wordnet"), nltk.data.FileSystemPathPointer)
assert nltk.data.find("corpora/wordnet/data.noun").open().read(2)
# 2. this account cannot plant, replace or rename anything at the shared root
for attempt in (
    lambda: open(noun, "ab"),
    lambda: open(os.path.join(wn_dir, "planted.txt"), "wb"),
    lambda: os.mkdir(os.path.join(corpora, "planted")),
    lambda: os.symlink("/etc/passwd", os.path.join(corpora, "planted.zip")),
    lambda: os.rename(wn_dir, os.path.join(corpora, "wordnet.old")),
    lambda: os.link(noun, os.path.join(corpora, "data.noun")),
    lambda: os.chmod(wn_dir, 0o777),
    lambda: os.remove(zips[0]),
):
    try:
        attempt()
    except PermissionError:
        pass
    else:
        raise AssertionError("the runtime account changed the shared root")
# 3. a root of this account's own, searched first: links to root's private
#    archive or to a file this account cannot read serve nothing
own = os.path.expanduser("~/nltk_data")
os.makedirs(os.path.join(own, "corpora", "wordnet"), mode=0o755, exist_ok=True)
os.symlink(zips[0], os.path.join(own, "corpora", "wordnet.zip"))
os.symlink("/etc/shadow", os.path.join(own, "corpora", "wordnet", "data.noun"))
try:
    os.link(zips[0], os.path.join(own, "corpora", "linked.zip"))
except PermissionError:
    pass  # protected hardlinks: the usual Linux setting
nltk.data.path[:] = [own, root]
pathsec._ALLOWED_ROOTS_CACHE = None
for name in ("corpora/wordnet/data.noun", "corpora/wordnet.zip/wordnet/data.noun"):
    try:
        nltk.data.find(name).open().read(2)
    except (PermissionError, LookupError):
        pass
    else:
        raise AssertionError(name + " was served through this account's links")
try:
    nltk.data.find("corpora/linked.zip/wordnet/data.noun").open().read(2)
except (PermissionError, LookupError, OSError):
    pass
else:
    raise AssertionError("a hardlink to the private archive served it")
# 4. a root of this account's own that other accounts can write to is refused
#    with the warning, and the shared root after it still serves
own_open = os.path.expanduser("~/open_root")
os.makedirs(os.path.join(own_open, "corpora", "wordnet"), exist_ok=True)
with open(os.path.join(own_open, "corpora", "wordnet", "data.noun"), "wb") as fh:
    fh.write(b"PLANTED")
os.chmod(own_open, 0o777)
nltk.data.path[:] = [own_open, root]
pathsec._ALLOWED_ROOTS_CACHE = None
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    found = nltk.data.find("corpora/wordnet/data.noun")
assert found.path.startswith(root), found.path
assert any("writable by, or owned by" in str(w.message) for w in caught)
# 5. the shared install is judged installed from its extracted files alone
nltk.data.path[:] = [root]
pathsec._ALLOWED_ROOTS_CACHE = None
d = downloader.Downloader(download_dir=root)
for package in ("wordnet", "omw-1.4", "omw-2.0", "stopwords"):
    assert d.status(package) == d.INSTALLED, (package, d.status(package))
print(
    "root-installed data serves",
    os.environ.get("USER") or os.getuid(),
    "through the extracted files; the shared root resisted the runtime account",
)
sys.exit(0)
