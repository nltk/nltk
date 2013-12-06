# Natural Language Toolkit: Aligned Sentences
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

class IBMModel1(object):
    """
    This class implements the Expectation Maximization algorithm for
    IBM Model 1. The algorithm runs upon a sentence-aligned parallel
    corpus and generates word alignments in aligned sentence pairs.
    The process is divided into 2 stages:

    - Stage 1: Calculates word-to-word translation probabilities by collecting
      evidence of a English word being the translation of a foreign word from
      the parallel corpus.
    - Stage 2: Generates updated word alignments for the sentence pairs, based
      on the translation probabilities from Stage 1.

        >>> corpus = [AlignedSent(['the', 'house'], ['das', 'Haus']),
        ...           AlignedSent(['the', 'book'], ['das', 'Buch']),
        ...           AlignedSent(['a', 'book'], ['ein', 'Buch'])]
        >>> ibm1 = IBMModel1(corpus)
        >>> print("%.1f" % ibm1.probabilities['book', 'Buch'])
        1.0
        >>> print("%.1f" % ibm1.probabilities['book', 'das'])
        0.0
        >>> print("%.1f" % ibm1.probabilities['book', None])
        0.5

    :param aligned_sents: The parallel text ``corpus.Iterable`` containing
        AlignedSent instances of aligned sentence pairs from the corpus.
    :type aligned_sents: list(AlignedSent)
    :param convergent_threshold: The threshold value of convergence. An
        entry is considered converged if the delta from ``old_t`` to ``new_t``
        is less than this value. The algorithm terminates when all entries
        are converged. This parameter is optional, default is 0.01
    :type convergent_threshold: float
    """

    def __init__(self, aligned_sents, convergent_threshold=1e-2, debug=False):
        self.aligned_sents = aligned_sents
        self.convergent_threshold = convergent_threshold
        # Dictionary of translation probabilities t(e,f).
        self.probabilities = None
        self._train()

    def _train(self):
        """
        Perform Expectation Maximization training to learn
        word-to-word translation probabilities.
        """
        logging.debug("Starting training")

        # Collect up sets of all English and foreign words
        english_words = set()
        foreign_words = set()
        for aligned_sent in self.aligned_sents:
            english_words.update(aligned_sent.words)
            foreign_words.update(aligned_sent.mots)
        # add the NULL token to the foreign word set.
        foreign_words.add(None)
        num_probs = len(english_words) * len(foreign_words)

        # Initialise t(e|f) uniformly
        default_prob = 1.0 / len(english_words)
        t = defaultdict(lambda: default_prob)

        convergent_threshold = self.convergent_threshold
        globally_converged = False
        iteration_count = 0
        while not globally_converged:
            # count(e|f)
            count = defaultdict(float)
            # total(f)
            total = defaultdict(float)

            for aligned_sent in self.aligned_sents:
                s_total = {}
                # Compute normalization
                for e_w in aligned_sent.words:
                    s_total[e_w] = 0.0
                    for f_w in aligned_sent.mots+[None]:
                        s_total[e_w] += t[e_w, f_w]

                # Collect counts
                for e_w in aligned_sent.words:
                    for f_w in aligned_sent.mots+[None]:
                        cnt = t[e_w, f_w] / s_total[e_w]
                        count[e_w, f_w] += cnt
                        total[f_w] += cnt

            # Estimate probabilities
            num_converged = 0
            for f_w in foreign_words:
                for e_w in english_words:
                    new_prob = count[e_w, f_w] / total[f_w]
                    delta = abs(t[e_w, f_w] - new_prob)
                    if delta < convergent_threshold:
                        num_converged += 1
                    t[e_w, f_w] = new_prob

            # Have we converged
            iteration_count += 1
            if num_converged == num_probs:
                globally_converged = True
            logging.debug("%d/%d (%.2f%%) converged" %
                          (num_converged, num_probs, 100.0*num_converged/num_probs))

        self.probabilities = dict(t)

    def aligned(self):
        """
        Return a list of AlignedSents with Alignments calculated using
        IBM-Model 1.
        """

        if self.probabilities is None:
            raise ValueError("No probabilities calculated")

        aligned = []
        # Alignment Learning from t(e|f)
        for aligned_sent in self.aligned_sents:
            alignment = []

            # for every English word
            for j, e_w in enumerate(aligned_sent.words):
                # find the French word that gives maximized t(e|f)
                # NULL token is the initial candidate
                f_max = (self.probabilities[e_w, None], None)
                for i, f_w in enumerate(aligned_sent.mots):
                    f_max = max(f_max, (self.probabilities[e_w, f_w], i))

                # only output alignment with non-NULL mapping
                if f_max[1] is not None:
                    alignment.append((j, f_max[1]))

            # substitute the alignment of AlignedSent with the yielded one
            aligned.append(AlignedSent(aligned_sent.words,
                    aligned_sent.mots,  alignment))

        return aligned
