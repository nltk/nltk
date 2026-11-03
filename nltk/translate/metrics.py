# Natural Language Toolkit: Translation metrics
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
The machine translation metrics as objects, set up once and then scoring a
corpus or a sentence (see nltk.translate.api.MetricI)::

    >>> from nltk.translate.metrics import BLEU
    >>> refs = [['the cat sat on the red mat today'.split()]]
    >>> hyps = ['the cat sat on the mat today'.split()]
    >>> round(BLEU(mode="sacrebleu").corpus_score(refs, hyps), 4)
    0.613

The functions (corpus_bleu, sentence_nist and so on) remain, and give the
scores of the "nltk" mode. The error rates TER and WER are lower for better
translations; the other metrics are higher.

    >>> from nltk.translate.metrics import TER
    >>> TER().corpus_score(refs, hyps)
    0.125
"""

from nltk.translate.bleu_score import BLEU
from nltk.translate.chrf_score import CHRF
from nltk.translate.gleu_score import GLEU
from nltk.translate.lepor import LEPOR
from nltk.translate.meteor_score import METEOR
from nltk.translate.nist_score import NIST
from nltk.translate.ribes_score import RIBES
from nltk.translate.rouge_score import ROUGE
from nltk.translate.ter_score import TER
from nltk.translate.wer_score import WER


def alignment_error_rate(reference, hypothesis, possible=None):
    """
    Return the Alignment Error Rate (AER) of an alignment
    with respect to a "gold standard" reference alignment.
    Return an error rate between 0.0 (perfect alignment) and 1.0 (no
    alignment).

        >>> from nltk.translate import Alignment
        >>> ref = Alignment([(0, 0), (1, 1), (2, 2)])
        >>> test = Alignment([(0, 0), (1, 2), (2, 1)])
        >>> alignment_error_rate(ref, test) # doctest: +ELLIPSIS
        0.6666666666666667

    :type reference: Alignment
    :param reference: A gold standard alignment (sure alignments)
    :type hypothesis: Alignment
    :param hypothesis: A hypothesis alignment (aka. candidate alignments)
    :type possible: Alignment or None
    :param possible: A gold standard reference of possible alignments
        (defaults to *reference* if None)
    :rtype: float or None
    """

    if possible is None:
        possible = reference
    else:
        assert reference.issubset(possible)  # sanity check

    return 1.0 - (len(hypothesis & reference) + len(hypothesis & possible)) / float(
        len(hypothesis) + len(reference)
    )
