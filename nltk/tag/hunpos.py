# Natural Language Toolkit: Interface to the HunPos POS-tagger
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
#         Dávid Márk Nemeskey <nemeskeyd@gmail.com> (modifications)
#         Attila Zséder <zseder@gmail.com> (modifications)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the HunPos open-source POS-tagger.
"""

import os
from subprocess import PIPE

from nltk.internals import find_binary, find_file
from nltk.pathsec import TrustError, spawn_trusted, validate_tool_path
from nltk.tag.api import TaggerI

_hunpos_url = "https://code.google.com/p/hunpos/"

_hunpos_charset = "ISO-8859-1"
"""The default encoding used by hunpos: ISO-8859-1."""


class HunposTagger(TaggerI):
    """
    A class for pos tagging with HunPos. The input is the paths to:
     - a model trained on training data
     - (optionally) the path to the hunpos-tag binary
     - (optionally) the encoding of the training data (default: ISO-8859-1)

    Check whether the required "hunpos-tag" binary is available:

        >>> from nltk.test.setup_fixt import check_binary
        >>> check_binary('hunpos-tag')

    Example:
        >>> from nltk.tag import HunposTagger
        >>> ht = HunposTagger('en_wsj.model')
        >>> ht.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'), ('of', 'IN'), ('an', 'DT'), ('unladen', 'NN'), ('swallow', 'VB'), ('?', '.')]
        >>> ht.close()

    This class communicates with the hunpos-tag binary via pipes. When the
    tagger object is no longer needed, the close() method should be called to
    free system resources. The class supports the context manager interface; if
    used in a with statement, the close() method is invoked automatically:

        >>> with HunposTagger('en_wsj.model') as ht:
        ...     ht.tag('What is the airspeed of an unladen swallow ?'.split())
        ...
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'), ('of', 'IN'), ('an', 'DT'), ('unladen', 'NN'), ('swallow', 'VB'), ('?', '.')]
    """

    def __init__(
        self, path_to_model, path_to_bin=None, encoding=_hunpos_charset, verbose=False
    ):
        """
        Starts the hunpos-tag executable and establishes a connection with it.

        :param path_to_model: The model file.
        :param path_to_bin: The hunpos-tag binary.
        :param encoding: The encoding used by the model. Unicode tokens
            passed to the tag() and tag_sents() methods are converted to
            this charset when they are sent to hunpos-tag.
            The default is ISO-8859-1 (Latin-1).

            This parameter is ignored for str tokens, which are sent as-is.
            The caller must ensure that tokens are encoded in the right charset.
        """
        self._closed = True
        hunpos_paths = [
            "/usr/bin",
            "/usr/local/bin",
            "/opt/local/bin",
            "/Applications/bin",
            "~/bin",
            "~/Applications/bin",
        ]
        hunpos_paths = list(map(os.path.expanduser, hunpos_paths))

        self._hunpos_bin = find_binary(
            "hunpos-tag",
            path_to_bin,
            env_vars=("HUNPOS_TAGGER",),
            searchpath=hunpos_paths,
            url=_hunpos_url,
            verbose=verbose,
        )

        self._hunpos_model = find_file(
            path_to_model, env_vars=("HUNPOS_TAGGER",), verbose=verbose
        )
        self._encoding = encoding
        # ``self._hunpos_model`` (from find_file) becomes argv to the hunpos-tag
        # subprocess pathsec.open cannot wrap; bound it before spawning (GHSA-8mgp-746c-j5xp).
        validate_tool_path(self._hunpos_model, context="HunposTagger.__init__")
        # Route through the trusted-exec chokepoint: verify the hunpos-tag binary
        # is on a path no other local user can swap, refuse a shell, and scrub the
        # loader environment before exec (CWE-426/427/732).
        try:
            self._hunpos = spawn_trusted(
                self._hunpos_bin,
                [self._hunpos_model],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
            )
        except TrustError as e:
            raise LookupError(
                f"Refusing to run the HunPos tagger {self._hunpos_bin!r}: it is "
                "not on a trusted path. Install HunPos where only you (or root) "
                f"can write ({e})."
            ) from e
        self._closed = False

    def __del__(self):
        self.close()

    def close(self):
        """Closes the pipe to the hunpos executable."""
        if not self._closed:
            self._hunpos.communicate()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def tag(self, tokens):
        """Tags a single sentence: a list of words.
        The tokens should not contain any newline characters.
        """
        for token in tokens:
            raw = token if isinstance(token, bytes) else token.encode(self._encoding)
            # Not an assert (python -O strips those): a control char in a token
            # injects an extra line into the tagger's line-oriented stdin or
            # truncates the token, desynchronising every tag that follows.
            if any(b < 0x20 and b != 0x09 for b in raw):
                raise ValueError(
                    "hunpos tokens must not contain newline, NUL or other control "
                    "characters"
                )
            self._hunpos.stdin.write(raw + b"\n")
        # We write a final empty line to tell hunpos that the sentence is finished:
        self._hunpos.stdin.write(b"\n")
        self._hunpos.stdin.flush()

        tagged_tokens = []
        for token in tokens:
            tagged = self._hunpos.stdout.readline().strip().split(b"\t")
            tag = tagged[1] if len(tagged) > 1 else None
            tagged_tokens.append((token, tag))
        # We have to read (and dismiss) the final empty line:
        self._hunpos.stdout.readline()

        return tagged_tokens
