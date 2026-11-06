# Natural Language Toolkit: Translation Edit Rate
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Translation edit rate (TER) implementation."""

import math

from nltk.metrics.distance import _check_distance_input_len
from nltk.translate.api import MetricI, _refuse_smoothing


def sentence_ter(references, hypothesis, *, on_empty="raise"):
    """
    Calculate the translation edit rate (TER) of a hypothesis from

    Matthew Snover, Bonnie Dorr, Richard Schwartz, Linnea Micciulla and John
    Makhoul. 2006. A Study of Translation Edit Rate with Targeted Human
    Annotation. In Proceedings of AMTA.
    https://aclanthology.org/2006.amta-papers.25.pdf

    TER is the number of edits that turn the hypothesis into a reference,
    divided by the average length of the references. Besides substituting,
    deleting and inserting a word, an edit can shift a phrase of the
    hypothesis to another place, at the cost of one edit however far and
    however long: a translation with its phrases in the wrong order is not
    punished once for every word of them, as WER punishes it. It is an
    error rate, so lower is better.

    Finding the fewest such edits is too hard to do exactly, so TER is what
    tercom, the program of Snover et al., finds: it shifts greedily, the
    shift that removes the most other edits first, while one helps.

    "on the mat" comes first in the hypothesis: one shift moves it to the
    end, and nothing else is wrong.

        >>> reference = 'the cat sat on the mat'.split()
        >>> hypothesis = 'on the mat the cat sat'.split()
        >>> round(sentence_ter([reference], hypothesis), 4)
        0.1667

    Of several references the hypothesis takes the one with the fewest
    edits, divided by the average length of all of them, as tercom does.

    :param references: the references of the hypothesis
    :type references: list(list(str))
    :param hypothesis: a hypothesis
    :type hypothesis: list(str)
    :param on_empty: "raise" (the default) or "zero", for a hypothesis
        without references
    :type on_empty: str
    :rtype: float
    """
    return TER(on_empty=on_empty).sentence_score(references, hypothesis)


def corpus_ter(list_of_references, hypotheses, *, on_empty="raise"):
    """
    Calculate the TER of a corpus: the edits of all hypotheses divided by the
    average reference lengths of all of them, as tercom's "Total TER".

        >>> refs = [['the cat sat on the mat'.split()], ['thank you'.split()]]
        >>> hyps = ['on the mat the cat sat'.split(), 'thanks you'.split()]
        >>> round(corpus_ter(refs, hyps), 4)
        0.25

    :param list_of_references: the references of each hypothesis
    :type list_of_references: list(list(list(str)))
    :param hypotheses: the hypotheses
    :type hypotheses: list(list(str))
    :param on_empty: "raise" (the default) or "zero", for an empty corpus or a
        hypothesis without references
    :type on_empty: str
    :rtype: float
    """
    return TER(on_empty=on_empty).corpus_score(list_of_references, hypotheses)


class TER(MetricI):
    """
    TER in two modes, which search for shifts differently and so can find
    different numbers of edits on long or scrambled sentences. ``"nltk"`` is
    corpus_ter() and sentence_ter(): tercom's search (tercom 0.7.25, and the
    0.8.0 of github.com/jhclark/tercom), with its beam of edit costs 20
    wide, shifts of up to 10 words and 50 positions, the longest shifts
    tried first. ``"sacrebleu"`` is sacrebleu 2.6.0's TER, a port of tercom
    that keeps 25 positions around the diagonal of the edit distance matrix
    instead, ranks the shifts its own way and stops after 1000 of them.

        >>> from nltk.translate.ter_score import TER
        >>> reference = 'the cat sat on the mat'.split()
        >>> hypothesis = 'on the mat the cat sat'.split()
        >>> round(TER().sentence_score([reference], hypothesis), 4)
        0.1667
        >>> round(TER(mode="sacrebleu").sentence_score([reference], hypothesis), 4)
        0.1667

    Both compare the tokens as they are given. tercom lowercases unless it
    is run with -s, and sacrebleu unless TER(case_sensitive=True); with -N
    and normalized=True they tokenize too. A corpus without reference words
    raises ValueError in the nltk mode, where tercom divides by zero, and
    scores 1.0 (or 0.0 without edits) in the sacrebleu mode, as sacrebleu.

    :param mode: "nltk" or "sacrebleu"
    :param smoothing: "none" only (see MetricI)
    :param on_empty: "raise" or "zero", see MetricI
    """

    modes = ("nltk", "sacrebleu")

    def __init__(self, *, smoothing=None, mode="nltk", on_empty="raise"):
        super().__init__(mode, on_empty)
        _refuse_smoothing(self, smoothing, "counts edits, not matches")

    def _corpus_score(self, list_of_references, hypotheses):
        count = _tercom_edits if self.mode == "nltk" else _sacrebleu_edits
        edits = words = 0
        for references, hypothesis in zip(list_of_references, hypotheses):
            # the fewest edits, the first reference of those on a tie
            edits += min(count(hypothesis, reference) for reference in references)
            words += sum(len(reference) for reference in references) / len(references)
        if words > 0:
            return edits / words
        if self.mode == "sacrebleu":
            return 1.0 if edits > 0 else 0.0
        raise ValueError(
            "TER divides by the reference length, and the references have no words"
        )


# tercom's limits (TerScorer.java)
_TERCOM_BEAM_WIDTH = 20
_TERCOM_MAX_SHIFT_SIZE = 10
_TERCOM_MAX_SHIFT_DIST = 50


def _tercom_edits(hypothesis, reference):
    """
    The edits tercom counts: shift while a shift does not add edits, then the
    substitutions, insertions and deletions of the shifted hypothesis.
    """
    if not hypothesis or not reference:
        return len(hypothesis) + len(reference)
    _check_distance_input_len(hypothesis, reference, "TER")
    phrases = _tercom_phrases(hypothesis, reference)
    edits, path = _tercom_edit_distance(hypothesis, reference)
    shifts = 0
    while True:
        best = _tercom_best_shift(hypothesis, reference, phrases, edits, path)
        if best is None:
            return edits + shifts
        hypothesis, edits, path = best
        shifts += 1


def _tercom_phrases(hypothesis, reference):
    """
    BuildWordMatches: where each phrase of the reference starts, for the
    phrases of up to 11 words that are all words of the hypothesis.
    """
    hyp_words = set(hypothesis)
    in_hyp = [word in hyp_words for word in reference]
    phrases = {}
    for start in range(len(reference)):
        end = start
        while (
            end < len(reference)
            and end - start <= _TERCOM_MAX_SHIFT_SIZE
            and in_hyp[end]
        ):
            phrases.setdefault(tuple(reference[start : end + 1]), []).append(start)
            end += 1
    return phrases


def _tercom_edit_distance(hypothesis, reference):
    """
    MinEditDist: the fewest substitutions, insertions and deletions in
    tercom's beam, and their path (" " match, "S", "I", "D"). A cell more
    than the beam width above the best cell of the previous hypothesis
    word is not extended, except for the last word.
    """
    n_ref, n_hyp = len(reference), len(hypothesis)
    # cost[j][i]: the column of hypothesis position j, row i of the reference
    cost = [[-1] * (n_ref + 1) for _ in range(n_hyp + 1)]
    back = [[None] * (n_ref + 1) for _ in range(n_hyp + 1)]
    cost[0][0] = 0
    current_best = math.inf
    current_first_good, cur_last_good = 0, 0
    for j in range(n_hyp + 1):
        last_best, current_best = current_best, math.inf
        first_good, current_first_good = current_first_good, -1
        last_good, cur_last_good = cur_last_good, -1
        column, back_column = cost[j], back[j]
        last = j == n_hyp
        if not last:
            following, back_following = cost[j + 1], back[j + 1]
            word, limit = hypothesis[j], last_best + _TERCOM_BEAM_WIDTH
        i = first_good
        # a deletion that reaches past last_good extends this column
        while i <= n_ref and i <= last_good:
            score = column[i]
            if score < 0 or (not last and score > limit):
                i += 1
                continue
            if current_first_good == -1:
                current_first_good = i
            if not last and i < n_ref:
                if reference[i] == word:
                    if following[i + 1] < 0 or score < following[i + 1]:
                        following[i + 1], back_following[i + 1] = score, " "
                    if score < current_best:
                        current_best = score
                elif following[i + 1] < 0 or score + 1 < following[i + 1]:
                    following[i + 1], back_following[i + 1] = score + 1, "S"
                    if score + 1 < current_best:
                        current_best = score + 1
            cur_last_good = i + 1
            if not last and (following[i] < 0 or following[i] > score + 1):
                following[i], back_following[i] = score + 1, "I"
            if i < n_ref and (column[i + 1] < 0 or column[i + 1] > score + 1):
                column[i + 1], back_column[i + 1] = score + 1, "D"
                if i >= last_good:
                    last_good = i + 1
            i += 1
    path, i, j = [], n_ref, n_hyp
    while i > 0 or j > 0:
        step = back[j][i]
        path.append(step)
        if step in (" ", "S"):
            i, j = i - 1, j - 1
        elif step == "D":
            i -= 1
        elif step == "I":
            j -= 1
        else:
            raise RuntimeError("tercom's beam lost the edit path")
    return cost[n_hyp][n_ref], path[::-1]


def _tercom_best_shift(hypothesis, reference, phrases, edits, path):
    """
    CalcBestShift: of the shifts GatherAllPossShifts allows, longest first,
    the one that leaves the fewest edits, if it removes at least as many
    edits as it costs; stop at a length whose shifts cannot do better. The
    new hypothesis, its edits and path, or None.
    """
    hyp_err, ref_err, ref_align = _tercom_errors(path, len(hypothesis), len(reference))
    shifts = _tercom_shifts(hypothesis, phrases, hyp_err, ref_err, ref_align)
    best = None
    best_cost, best_edits = 0, edits
    for length in range(len(shifts) - 1, -1, -1):
        # a shift of length + 1 words fixes at most 2 * (length + 1) edits
        max_fix = 2 * (length + 1)
        for shift in [None] + shifts[length]:
            fix = edits - (best_cost + best_edits)
            if fix > max_fix or (best_cost != 0 and fix == max_fix):
                return best
            if shift is None:
                continue
            shifted = _tercom_perform_shift(hypothesis, *shift)
            new_edits, new_path = _tercom_edit_distance(shifted, reference)
            gain = (best_edits + best_cost) - (new_edits + 1)
            if gain > 0 or (best_cost == 0 and gain == 0):
                best = shifted, new_edits, new_path
                best_cost, best_edits = 1, new_edits
    return best


def _tercom_errors(path, n_hyp, n_ref):
    """
    FindAlignErr: which hypothesis and reference words the path gets wrong,
    and the hypothesis position each reference word is aligned to.
    """
    hyp_err, ref_err, ref_align = [False] * n_hyp, [False] * n_ref, [0] * n_ref
    h = r = -1
    for step in path:
        if step in (" ", "S", "I"):
            h += 1
            hyp_err[h] = step != " "
        if step in (" ", "S", "D"):
            r += 1
            ref_err[r] = step != " "
            ref_align[r] = h
    return hyp_err, ref_err, ref_align


def _tercom_shifts(hypothesis, phrases, hyp_err, ref_err, ref_align):
    """
    GatherAllPossShifts: (start, end, new location) of each shift of a
    hypothesis phrase that the reference has too, that has a wrong word, and
    whose place in the reference has a wrong word, by phrase length.
    """
    shifts = [[] for _ in range(_TERCOM_MAX_SHIFT_SIZE + 1)]
    for start, word in enumerate(hypothesis):
        if not any(
            start != ref_align[m]
            and ref_align[m] - start <= _TERCOM_MAX_SHIFT_DIST
            and start - ref_align[m] - 1 <= _TERCOM_MAX_SHIFT_DIST
            for m in phrases.get((word,), ())
        ):
            continue
        end, ok = start, True
        while ok and end < len(hypothesis) and end < start + _TERCOM_MAX_SHIFT_SIZE:
            phrase = tuple(hypothesis[start : end + 1])
            ok = phrase in phrases and not any(hyp_err[start : end + 1])
            for move_to in phrases.get(phrase, ()) if not ok else ():
                align = ref_align[move_to]
                if (
                    align == start
                    or start <= align <= end
                    or align - start > _TERCOM_MAX_SHIFT_DIST
                    or start - align > _TERCOM_MAX_SHIFT_DIST
                ):
                    continue
                ok = True
                if not any(ref_err[move_to : move_to + end - start + 1]):
                    continue
                for offset in range(-1, end - start + 1):
                    if offset == -1 and move_to == 0:
                        shifts[end - start].append((start, end, -1))
                    elif start != ref_align[move_to + offset] and (
                        offset == 0 or ref_align[move_to + offset] != align
                    ):
                        shifts[end - start].append(
                            (start, end, ref_align[move_to + offset])
                        )
            end += 1
    return shifts


def _tercom_perform_shift(words, start, end, new_loc):
    """PerformShift: move words[start:end + 1] to after position new_loc."""
    if new_loc == -1:
        return words[start : end + 1] + words[:start] + words[end + 1 :]
    if new_loc < start:
        return (
            words[: new_loc + 1]
            + words[start : end + 1]
            + words[new_loc + 1 : start]
            + words[end + 1 :]
        )
    if new_loc > end:
        return (
            words[:start]
            + words[end + 1 : new_loc + 1]
            + words[start : end + 1]
            + words[new_loc + 1 :]
        )
    # moving inside itself
    k = end + new_loc - start
    return (
        words[:start] + words[end + 1 : k + 1] + words[start : end + 1] + words[k + 1 :]
    )


# sacrebleu's limits (lib_ter.py)
_SACREBLEU_BEAM_WIDTH = 25
_SACREBLEU_MAX_SHIFT_SIZE = 10
_SACREBLEU_MAX_SHIFT_DIST = 50
_SACREBLEU_MAX_SHIFT_CANDIDATES = 1000
_SACREBLEU_MAX_CACHE_SIZE = 10000


def _sacrebleu_edits(hypothesis, reference):
    """
    The edits sacrebleu 2.6.0 counts (translation_edit_rate in lib_ter.py):
    shift while a shift removes more than one edit, until 1000 shifts have
    been tried, then the edit distance of the shifted hypothesis.
    """
    if not reference:
        return len(hypothesis)
    _check_distance_input_len(hypothesis, reference, "TER")
    distance = _SacrebleuEditDistance(reference)
    shifts = checked = 0
    while True:
        gain, shifted, checked = _sacrebleu_shift(
            hypothesis, reference, distance, checked
        )
        if checked >= _SACREBLEU_MAX_SHIFT_CANDIDATES or gain <= 0:
            return shifts + distance(hypothesis)[0]
        shifts += 1
        hypothesis = shifted


def _sacrebleu_shift(hypothesis, reference, distance, checked):
    """
    sacrebleu's _shift: of the shifts of hypothesis phrases the reference
    has, the one that removes the most edits, then the longest, earliest and
    earliest placed; its gain, the shifted hypothesis, and the count of
    shifts tried.
    """
    edits, trace = distance(hypothesis)
    # the trace rewrites the hypothesis into the reference: flip it to align
    trace = trace.translate(str.maketrans("id", "di"))
    align, ref_err, hyp_err = _sacrebleu_alignment(trace)
    best = None
    for start_h, start_r, length in _sacrebleu_pairs(hypothesis, reference):
        if not any(hyp_err[start_h : start_h + length]):
            continue
        if not any(ref_err[start_r : start_r + length]):
            continue
        if start_h <= align[start_r] < start_h + length:
            continue
        previous = -1
        for offset in range(-1, length):
            if start_r + offset == -1:
                target = 0
            elif start_r + offset in align:
                target = align[start_r + offset] + 1
            else:
                break
            if target == previous:
                continue
            previous = target
            shifted = _sacrebleu_perform_shift(hypothesis, start_h, length, target)
            candidate = (
                edits - distance(shifted)[0],
                length,
                -start_h,
                -target,
                shifted,
            )
            checked += 1
            if not best or candidate > best:
                best = candidate
        if checked >= _SACREBLEU_MAX_SHIFT_CANDIDATES:
            break
    if not best:
        return 0, hypothesis, checked
    return best[0], best[4], checked


def _sacrebleu_pairs(hypothesis, reference):
    """sacrebleu's _find_shifted_pairs: (hyp start, ref start, length) of shared phrases."""
    for start_h in range(len(hypothesis)):
        for start_r in range(len(reference)):
            if abs(start_r - start_h) > _SACREBLEU_MAX_SHIFT_DIST:
                continue
            length = 0
            while (
                hypothesis[start_h + length] == reference[start_r + length]
                and length < _SACREBLEU_MAX_SHIFT_SIZE
            ):
                length += 1
                yield start_h, start_r, length
                if (
                    len(hypothesis) == start_h + length
                    or len(reference) == start_r + length
                ):
                    break


def _sacrebleu_alignment(trace):
    """sacrebleu's trace_to_alignment: reference to hypothesis positions, and the errors."""
    h = r = -1
    hyp_err, ref_err, align = [], [], {}
    for step in trace:
        if step in " si":
            h += 1
            hyp_err.append(step != " ")
        if step in " sd":
            r += 1
            ref_err.append(step != " ")
            align[r] = h
    return align, ref_err, hyp_err


def _sacrebleu_perform_shift(words, start, length, target):
    """sacrebleu's _perform_shift: move words[start:start + length] before target."""
    if target < start:
        return (
            words[:target]
            + words[start : start + length]
            + words[target:start]
            + words[start + length :]
        )
    if target > start + length:
        return (
            words[:start]
            + words[start + length : target]
            + words[start : start + length]
            + words[target:]
        )
    return (
        words[:start]
        + words[start + length : length + target]
        + words[start : start + length]
        + words[length + target :]
    )


class _SacrebleuEditDistance:
    """
    sacrebleu's BeamEditDistance: the edit distance to one reference of the
    hypotheses that shifting makes, all of one length, in a beam around the
    diagonal, the rows of shared hypothesis prefixes computed once.
    """

    def __init__(self, reference):
        self.reference = reference
        self.first_row = [(j, "i") for j in range(len(reference) + 1)]
        self.empty_row = [(math.inf, "x")] * (len(reference) + 1)
        self.cache, self.cache_size = {}, 0

    def __call__(self, hypothesis):
        node, rows = self.cache, [self.first_row]
        for word in hypothesis:
            if word not in node:
                break
            node, row = node[word]
            rows.append(row)
        start = len(rows) - 1
        rows = rows + [list(self.empty_row) for _ in range(len(hypothesis) - start)]
        n_ref = len(self.reference)
        ratio = n_ref / len(hypothesis) if hypothesis else 1
        # very different lengths need a wider beam to overlap the previous row
        beam = (
            math.ceil(ratio / 2 + _SACREBLEU_BEAM_WIDTH)
            if _SACREBLEU_BEAM_WIDTH < ratio / 2
            else _SACREBLEU_BEAM_WIDTH
        )
        for i in range(start + 1, len(hypothesis) + 1):
            diagonal = math.floor(i * ratio)
            low, high = max(0, diagonal - beam), min(n_ref + 1, diagonal + beam)
            if i == len(hypothesis):
                high = n_ref + 1
            row, above, word = rows[i], rows[i - 1], hypothesis[i - 1]
            for j in range(low, high):
                if j == 0:
                    row[0] = (above[0][0] + 1, "d")
                    continue
                # on a tie: no change or substitution, then deletion, then insertion
                best = row[j]
                if word == self.reference[j - 1]:
                    if best[0] > above[j - 1][0]:
                        best = (above[j - 1][0], " ")
                elif best[0] > above[j - 1][0] + 1:
                    best = (above[j - 1][0] + 1, "s")
                if best[0] > above[j][0] + 1:
                    best = (above[j][0] + 1, "d")
                if best[0] > row[j - 1][0] + 1:
                    best = (row[j - 1][0] + 1, "i")
                row[j] = best
        trace, i, j = "", len(hypothesis), n_ref
        while i > 0 or j > 0:
            step = rows[i][j][1]
            trace = step + trace
            if step in " s":
                i, j = i - 1, j - 1
            elif step == "i":
                j -= 1
            elif step == "d":
                i -= 1
            else:
                raise RuntimeError("sacrebleu's beam lost the edit path")
        self._remember(hypothesis, rows[start + 1 :], start)
        return rows[-1][-1][0], trace

    def _remember(self, hypothesis, rows, start):
        if self.cache_size >= _SACREBLEU_MAX_CACHE_SIZE:
            return
        node = self.cache
        for word in hypothesis[:start]:
            node = node[word][0]
        for word, row in zip(hypothesis[start:], rows):
            if word not in node:
                node[word] = ({}, tuple(row))
                self.cache_size += 1
            node = node[word][0]
