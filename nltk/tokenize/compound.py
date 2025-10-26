#
# Natural Language Toolkit: WordNet-based compound splitter
#
# Copyright (C) 2001-2025 NLTK Project
# Author: Danial Changez
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT
#

"""Compound word splitting utilities.

This module provides a compound splitter that uses a vocabulary
built from WordNet lemma names. It can decompose concatenated tokens such as
``crossregionswitch`` into words like ``cross region switch``.

The implementation is intentionally conservative (it will always keep the
original token as a fall-back) and it scores candidate splits using WordNet lemma frequencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Mapping, Tuple

__all__ = ["split_compound", "WordNetCompoundSplitter", "build_wordnet_vocab"]

# Cache for WordNet-derived vocabularies
_WORDNET_VOCAB_CACHE: Dict[int, Dict[str, float]] = {}


def build_wordnet_vocab(min_len: int = 2) -> Dict[str, float]:
    """Return a mapping from words to their splitting cost.

    The cost is based on lemma frequency counts: ``-log(count + 1)``. Words that
    appear more frequently in WordNet therefore have lower costs and are more
    likely to be selected as part of a split.

    Parameters
    ----------
    min_len : int
        Minimum length of lemma names to consider. Very short words (e.g.
        single characters) are ignored to reduce noise.

    Returns
    -------
    dict
        Mapping of lower-cased words to cost values.

    Raises
    ------
    LookupError
        If the WordNet corpus has not been downloaded.
    """

    if min_len in _WORDNET_VOCAB_CACHE:
        return _WORDNET_VOCAB_CACHE[min_len]

    counts: Dict[str, int] = {}
    from nltk.corpus import wordnet as wn
    try:
        for synset in wn.all_synsets():
            for lemma in synset.lemmas():
                name = lemma.name()
                if "_" in name:
                    # Skip multi-word lemma names; we only want atomic words.
                    continue
                name = name.lower()
                if len(name) < min_len:
                    continue
                counts[name] = counts.get(name, 0) + max(lemma.count(), 1)
    except LookupError as err:
        raise LookupError(
            "WordNet corpus not found. Please run nltk.download('wordnet')."
        ) from err

    # Convert counts to costs. Add a small constant penalty to discourage
    # overly long words when counts tie.
    total = sum(counts.values())
    smoothing = 1.0
    vocab = {
        word: -math.log((count + smoothing) / (total + smoothing * len(counts)))
        for word, count in counts.items()
    }
    _WORDNET_VOCAB_CACHE[min_len] = vocab
    return vocab


@dataclass
class WordNetCompoundSplitter:
    """Split concatenated words using a WordNet-derived vocabulary.

    Parameters
    ----------
    vocab : mapping, optional
        Mapping from lower-cased words to cost values (lower is better). If
        ``None`` (default) a vocabulary derived from WordNet lemma names is used.
    split_penalty : float
        Penalty added for every additional segment beyond the first. Larger
        values result in fewer splits.
    unknown_penalty : float
        Cost assigned when falling back to the unsplit token.
    min_segment_len : int
        Minimum segment length to consider when splitting. Defaults to 2 to
        avoid splitting into single characters.
    """

    vocab: Mapping[str, float] | None = None
    # Slightly lower than 1.5 so genuine triple splits remain affordable while
    # still discouraging gratuitous decompositions.
    split_penalty: float = 1.45
    unknown_penalty: float = 30.0
    min_segment_len: int = 2
    short_segment_penalty: float = 4.5
    min_component_length: int = 5

    def __post_init__(self) -> None:
        if self.vocab is None:
            self.vocab = build_wordnet_vocab(min_len=self.min_segment_len)
        else:
            # Make a copy so we can rely on consistent behaviour even if
            # the caller mutates the original mapping after instantiation.
            self.vocab = dict(self.vocab)

        assert self.vocab is not None  # for type checkers
        self._max_segment_len = max((len(word) for word in self.vocab), default=0)

    def split(self, word: str) -> List[str]:
        """Split *word* into a sequence of components.

        The original *word* is preserved when no beneficial decomposition can be
        found.
        """

        if not word:
            return [word]

        lower_word = word.lower()
        n = len(word)
        vocab = self.vocab
        assert vocab is not None

        if lower_word in vocab:
            return [word]

        @lru_cache(maxsize=None)
        def solve(index: int) -> Tuple[float, List[str]]:
            if index >= n:
                return (0.0, [])

            best_cost: float | None = None
            best_segments: List[str] | None = None

            limit = min(n, index + self._max_segment_len)
            for end in range(index + self.min_segment_len, limit + 1):
                segment = lower_word[index:end]
                cost = vocab.get(segment)
                if cost is None:
                    continue
                segment_len = end - index
                if segment_len <= 2:
                    length_cost = self.short_segment_penalty
                elif segment_len == 3:
                    length_cost = self.short_segment_penalty * 0.5
                else:
                    length_cost = 0.0

                remainder_cost, remainder_segments = solve(end)
                total_cost = cost + length_cost + remainder_cost
                if remainder_segments:
                    total_cost += self.split_penalty

                if (
                    best_cost is None
                    or total_cost < best_cost
                    or (
                        math.isclose(total_cost, best_cost)
                        and len(remainder_segments) + 1 < len(best_segments or [])
                    )
                ):
                    best_cost = total_cost
                    best_segments = [word[index:end], *remainder_segments]

            if best_segments is None:
                return (self.unknown_penalty, [word[index:]])

            assert best_cost is not None
            if best_cost >= self.unknown_penalty:
                return (self.unknown_penalty, [word[index:]])

            return best_cost, best_segments

        _, segments = solve(0)
        if len(segments) > 1 and max(len(seg) for seg in segments) < self.min_component_length:
            return [word]
        return segments


def split_compound(word: str, splitter: WordNetCompoundSplitter | None = None) -> List[str]:
    """Convenience wrapper for :class:`WordNetCompoundSplitter`."""

    if splitter is None:
        splitter = WordNetCompoundSplitter()
    return splitter.split(word)
