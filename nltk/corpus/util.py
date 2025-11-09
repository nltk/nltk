# Natural Language Toolkit: Corpus Reader Utility Functions
#
# Copyright (C) 2001-2025 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# ----------------------------------------------------------------------
# Lazy Corpus Loader
# ----------------------------------------------------------------------
#
# Unload design notes:
# Older implementations tried to "void" a loaded corpus instance with
#     self.__class__ = None
# which is unsafe: CPython expects __class__ to remain a valid type
# object. Assigning None can corrupt interpreter state and cause segfaults.
#
# The current approach restores the object to a *fresh* LazyCorpusLoader
# proxy, allowing a future reload while dropping references to the loaded
# corpus for GC. If a permanently inert unload is desired, a different
# flag‑based pattern could be introduced separately.
# ----------------------------------------------------------------------

import gc
import re
import types

import nltk

TRY_ZIPFILE_FIRST = False


class LazyCorpusLoader:
    """
    Lazily stands in for an actual corpus reader until first access.

    On first attribute access, the loader locates the corpus root,
    instantiates the designated reader class, and mutates its own
    __dict__ and __class__ to become that reader.

    If the corpus is not found, a LookupError with installation
    guidance is raised.

    :param name: Corpus name (path fragment under nltk_data/<subdir>).
    :param reader_cls: CorpusReader subclass to instantiate.
    :param nltk_data_subdir: Optional override for data subdirectory (default 'corpora').
    :param *args, **kwargs: Forwarded to reader_cls.
    """

    def __init__(self, name, reader_cls, *args, **kwargs):
        from nltk.corpus.reader.api import CorpusReader

        assert issubclass(reader_cls, CorpusReader)
        self.__name = self.__name__ = name
        self.__reader_cls = reader_cls
        if "nltk_data_subdir" in kwargs:
            self.subdir = kwargs.pop("nltk_data_subdir")
        else:
            self.subdir = "corpora"
        self.__args = args
        self.__kwargs = kwargs

    def __load(self):
        # Resolve root directory, trying normal then zip (or reversed if configured).
        zip_name = re.sub(r"(([^/]+)(/.*)?)", r"\2.zip/\1/", self.__name)
        if TRY_ZIPFILE_FIRST:
            try:
                root = nltk.data.find(f"{self.subdir}/{zip_name}")
            except LookupError as e:
                try:
                    root = nltk.data.find(f"{self.subdir}/{self.__name}")
                except LookupError:
                    raise e
        else:
            try:
                root = nltk.data.find(f"{self.subdir}/{self.__name}")
            except LookupError as e:
                try:
                    root = nltk.data.find(f"{self.subdir}/{zip_name}")
                except LookupError:
                    raise e

        corpus = self.__reader_cls(root, *self.__args, **self.__kwargs)

        # Preserve construction args for future reload after unload.
        args, kwargs = self.__args, self.__kwargs
        name, reader_cls = self.__name, self.__reader_cls

        # Adopt corpus identity.
        self.__dict__ = corpus.__dict__
        self.__class__ = corpus.__class__

        def _unload(self):
            # Rebuild a pristine lazy proxy; drop old corpus references.
            lazy_reader = LazyCorpusLoader(name, reader_cls, *args, **kwargs)
            self.__dict__.clear()
            self.__dict__.update(lazy_reader.__dict__)
            self.__class__ = lazy_reader.__class__
            self._unloaded = True  # Diagnostic/optional.
            gc.collect()

        # Directly bind method without helper.
        self._unload = types.MethodType(_unload, self)

    def __getattr__(self, attr):
        """
        Trigger loading on first missing attribute access.

        From Python 3.9+ we no longer need legacy inspect workarounds.
        To avoid surprising loads during introspection, do not load on
        dunder attribute lookups (e.g., '__bases__', '__wrapped__').
        """
        if attr.startswith("__") and attr.endswith("__"):
            # Avoid loading on introspection-related dunder names.
            raise AttributeError(
                f"{type(self).__name__} object has no attribute {attr!r}"
            )

        self.__load()
        # After loading, our class is now the real corpus reader; delegate.
        return getattr(self, attr)

    def __repr__(self):
        return "<{} in {!r} (not loaded yet)>".format(
            self.__reader_cls.__name__,
            ".../corpora/" + self.__name,
        )

    def _unload(self):
        # Placeholder only active if load failed and rebound did not occur.
        pass
