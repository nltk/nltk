# Natural Language Toolkit: HuggingFace dataset integration
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
HuggingFace datasets integration for NLTK.

Provides a PathPointer subclass that reads directly from the HuggingFace
datasets cache, and a ``download()`` function that populates that cache.

Usage::

    import nltk
    nltk.download('stopwords', hf=True)            # download to HF cache
    nltk.corpus.stopwords.words('portuguese')      # HF fallback if not in ~/nltk_data
    nltk.corpus.stopwords.words('portuguese', hf=True)  # HF cache directly

Registry schema
---------------
Each entry in ``REGISTRY`` must declare:

``repo`` (str)
    HuggingFace dataset repo id, e.g. ``"nltk-data-hub/stopwords"``.

``split`` (str)
    HF split name to load, e.g. ``"stopwords"``, ``"train"``.

``structure`` (str)
    How the corpus is organised on HF:

    ``"multi_config"``
        One HF config per NLTK fileid.  No assumption about what that
        dimension represents (language, category, author, etc.).
        ``fileid`` → config name.

    ``"flat"``
        Single config, flat table.  A ``fileid_column`` value is used
        to select rows for a given fileid.

    ``"single"``
        Single config, no sub-selection.  The whole split is the corpus.

``content_type`` (str)
    How rows are serialised to the byte/text stream NLTK readers expect:

    ``"word_list"``
        Each row is one entry; ``text_column`` holds the string.
        Serialised as one entry per line.

    ``"raw_text"``
        Rows have a ``text_column`` with full document text.  When a
        fileid is given, rows are filtered by ``fileid_column``.
        Serialised as the raw text string.

    (Add new types here as more corpora are onboarded.)

``cache_probe`` (str)
    A single parquet path inside the repo used to detect whether the
    corpus has already been downloaded locally.  No network request is
    made; ``huggingface_hub.try_to_load_from_cache`` inspects the local
    filesystem only.

Optional keys (required by certain content types):

``text_column``    column that holds the main text / word value.
``fileid_column``  column that identifies which NLTK fileid a row belongs to.
``label_column``   column for classification labels (future use).
"""

import io

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY = {
    "stopwords": {
        "repo": "nltk-data-hub/stopwords",
        "split": "stopwords",
        "structure": "multi_config",
        "content_type": "word_list",
        "text_column": "word",
        "cache_probe": "data/english/stopwords.parquet",
    },
}


# ---------------------------------------------------------------------------
# Cache detection (no network)
# ---------------------------------------------------------------------------


def _is_cached(corpus_id):
    """Return True if the corpus parquet exists in the local HF datasets cache."""
    info = REGISTRY.get(corpus_id)
    if info is None:
        return False
    try:
        from huggingface_hub import try_to_load_from_cache

        result = try_to_load_from_cache(
            repo_id=info["repo"],
            filename=info["cache_probe"],
            repo_type="dataset",
        )
        return result is not None and result != "no_connection"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Content serialisation
# ---------------------------------------------------------------------------


def _serialise(ds, info, fileid=None):
    """
    Convert an HF dataset ``ds`` to the byte/text content that an NLTK
    corpus reader would find in a plain file.

    :param ds: ``datasets.Dataset`` already filtered/selected for this corpus.
    :param info: REGISTRY entry for the corpus.
    :param fileid: the NLTK fileid being requested (used by some types).
    :returns: str — file content as NLTK expects it.
    """
    content_type = info.get("content_type", "raw_text")

    if content_type == "word_list":
        return "\n".join(ds[info["text_column"]])

    if content_type == "raw_text":
        col = info["text_column"]
        texts = ds[col]
        return "\n".join(texts) if len(texts) > 1 else (texts[0] if texts else "")

    raise NotImplementedError(
        f"content_type={content_type!r} is not implemented. "
        "Add a handler in nltk.huggingface.dataset._serialise()."
    )


def _load_hf_dataset(info, fileid=None):
    """
    Load the appropriate HF dataset slice for *fileid*, respecting structure.

    :param info: REGISTRY entry.
    :param fileid: NLTK fileid (may be None for single-structure corpora).
    :returns: ``datasets.Dataset``.
    """
    from datasets import load_dataset

    structure = info.get("structure", "single")

    if structure == "multi_config":
        if fileid is None:
            raise ValueError(
                "fileid is required for multi_config corpora. "
                "Pass the config name (e.g. a language or category)."
            )
        return load_dataset(info["repo"], fileid, split=info["split"])

    if structure == "flat":
        ds = load_dataset(info["repo"], split=info["split"])
        if fileid is not None:
            col = info["fileid_column"]
            ds = ds.filter(lambda row: row[col] == fileid)
        return ds

    # single
    return load_dataset(info["repo"], split=info["split"])


# ---------------------------------------------------------------------------
# HFDatasetPathPointer
# ---------------------------------------------------------------------------


class HFDatasetPathPointer:
    """
    A ``PathPointer``-compatible object backed by a HuggingFace dataset
    stored in the local HF datasets cache (~/.cache/huggingface/datasets/).

    Satisfies the NLTK PathPointer interface (``open`` / ``file_size`` /
    ``join``) so that existing corpus readers work unchanged after
    ``nltk.download(..., hf=True)``.
    """

    def __init__(self, corpus_id, fileid=None):
        self.corpus_id = corpus_id
        self.fileid = fileid

    # -- PathPointer interface -----------------------------------------------

    def open(self, encoding=None):
        """Return a stream of file content as NLTK corpus readers expect."""
        info = REGISTRY[self.corpus_id]
        ds = _load_hf_dataset(info, fileid=self.fileid)
        content = _serialise(ds, info, fileid=self.fileid)
        if encoding:
            return io.StringIO(content)
        return io.BytesIO(content.encode("utf-8"))

    def file_size(self):
        return 0

    def join(self, fileid):
        return HFDatasetPathPointer(self.corpus_id, fileid)

    # -- fileids (duck-typed by find_corpus_fileids) -------------------------

    def fileids(self):
        """Return sorted list of fileids available for this corpus."""
        info = REGISTRY.get(self.corpus_id)
        if info is None or not _is_cached(self.corpus_id):
            return []
        structure = info.get("structure", "single")
        try:
            if structure == "multi_config":
                from datasets import get_dataset_config_names

                return sorted(get_dataset_config_names(info["repo"]))
            if structure == "flat":
                from datasets import load_dataset

                ds = load_dataset(info["repo"], split=info["split"])
                return sorted(ds.unique(info["fileid_column"]))
            return [info["split"]]  # single
        except Exception:
            return []

    # -- repr / path ---------------------------------------------------------

    @property
    def path(self):
        repo = REGISTRY.get(self.corpus_id, {}).get("repo", self.corpus_id)
        return f"hf://{repo}"

    def __str__(self):
        return f"{self.path}/{self.fileid}" if self.fileid else self.path

    def __repr__(self):
        return f"HFDatasetPathPointer({self.corpus_id!r}, {self.fileid!r})"


# Register as virtual subclass of PathPointer — avoids circular import at load
def _register_path_pointer():
    try:
        from nltk.data import PathPointer

        PathPointer.register(HFDatasetPathPointer)
    except Exception:
        pass


_register_path_pointer()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def download(corpus_id, token=None, quiet=False):
    """
    Download an NLTK corpus from HuggingFace into the HF datasets cache
    (``~/.cache/huggingface/datasets/``).

    :param corpus_id: NLTK corpus id, e.g. ``'stopwords'``.
    :param token: optional HuggingFace API token for private repos.
    :param quiet: suppress progress output.
    :raises ValueError: if *corpus_id* is not in the HF registry.
    """
    info = REGISTRY.get(corpus_id)
    if info is None:
        raise ValueError(
            f"Corpus {corpus_id!r} is not available on HuggingFace.\n"
            f"Available: {sorted(REGISTRY)}"
        )

    from datasets import load_dataset

    kwargs = {"token": token} if token else {}
    structure = info.get("structure", "single")

    if structure == "multi_config":
        from datasets import get_dataset_config_names

        configs = get_dataset_config_names(info["repo"])
        result = {
            cfg: load_dataset(info["repo"], cfg, split=info["split"], **kwargs)
            for cfg in configs
        }
        if not quiet:
            total = sum(len(d) for d in result.values())
            print(
                f"[nltk_hf] '{corpus_id}' downloaded from {info['repo']} "
                f"({len(configs)} configs, {total:,} rows)"
            )
        return result

    else:  # flat or single
        ds = load_dataset(info["repo"], split=info["split"], **kwargs)
        if not quiet:
            print(
                f"[nltk_hf] '{corpus_id}' downloaded from {info['repo']} "
                f"({len(ds):,} rows)"
            )
        return ds


def load_data(corpus_id, fileid=None):
    """
    Load data for *corpus_id* directly from the HF datasets cache and return
    it as a string in the format NLTK corpus readers expect.

    :param corpus_id: NLTK corpus id, e.g. ``'stopwords'``.
    :param fileid: sub-resource identifier (config name, category, fileid, …).
    :returns: str.
    :raises LookupError: if the corpus is not in the registry or not cached.
    """
    info = REGISTRY.get(corpus_id)
    if info is None:
        raise LookupError(
            f"Corpus {corpus_id!r} is not in the HuggingFace NLTK registry."
        )
    if not _is_cached(corpus_id):
        raise LookupError(
            f"Corpus {corpus_id!r} not found in HF datasets cache. "
            f"Run: nltk.download({corpus_id!r}, hf=True)"
        )
    ds = _load_hf_dataset(info, fileid=fileid)
    return _serialise(ds, info, fileid=fileid)
