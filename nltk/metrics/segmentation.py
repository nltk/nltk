# Natural Language Toolkit: Text Segmentation Metrics
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         David Doukhan <david.doukhan@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT



"""
Text Segmentation Metrics

1. Windowdiff

Pevzner, L., and Hearst, M., A Critique and Improvement of
  an Evaluation Metric for Text Segmentation,
Computational Linguistics 28, 19-36


2. Generalized Hamming Distance

Bookstein A., Kulyukin V.A., Raita T.
Generalized Hamming Distance
Information Retrieval 5, 2002, pp 353-375

Baseline implementation in C++
http://digital.cs.usu.edu/~vkulyukin/vkweb/software/ghd/ghd.html

Study describing benefits of Generalized Hamming Distance Versus
WindowDiff for evaluating text segmentation tasks
Begsten, Y.  Quel indice pour mesurer l'efficacite en segmentation de textes ?
TALN 2009


3. Pk text segmentation metric

Beeferman D., Berger A., Lafferty J. (1999)
Statistical Models for Text Segmentation
Machine Learning, 34, 177-210
"""

try:
    import numpy
except ImportError:
    pass

def windowdiff(seg1, seg2, k, boundary="1"):
    """
    Compute the windowdiff score for a pair of segmentations.  A
    segmentation is any sequence over a vocabulary of two items
    (e.g. "0", "1"), where the specified boundary value is used to
    mark the edge of a segmentation.

    >>> s1 = "00000010000000001000000"
    >>> s2 = "00000001000000010000000"
    >>> s3 = "00010000000000000001000"
    >>> windowdiff(s1, s1, 3)
    0
    >>> windowdiff(s1, s2, 3)
    4
    >>> windowdiff(s2, s3, 3)
    16

    :param seg1: a segmentation
    :type seg1: str or list
    :param seg2: a segmentation
    :type seg2: str or list
    :param k: window width
    :type k: int
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: int
    """

    if len(seg1) != len(seg2):
        raise ValueError, "Segmentations have unequal length"
    wd = 0
    for i in range(len(seg1) - k):
        wd += abs(seg1[i:i+k+1].count(boundary) - seg2[i:i+k+1].count(boundary))
    return wd



# Generalized Hamming Distance

def _init_mat(nrows, ncols, ins_cost, del_cost):
    mat = numpy.empty((nrows, ncols))
    mat[0, :] = [x * ins_cost for x in xrange(ncols)]
    mat[:, 0] = [x * del_cost for x in xrange(nrows)]
    return mat

def _ghd_aux(mat, rowv, colv, ins_cost, del_cost, shift_cost_coeff):
    for i, rowi in enumerate(rowv):
        for j, colj in enumerate(colv):          
            shift_cost = shift_cost_coeff * abs(rowi - colj) + mat[i, j]
            if rowi == colj:
                # boundaries are at the same location, no transformation required
                tcost = mat[i, j]
            elif rowi > colj:
                # boundary match through a deletion
                tcost = del_cost + mat[i, j + 1]
            else:
                # boundary match through an insertion
                tcost = ins_cost + mat[i + 1, j]
            mat[i + 1, j + 1] = min(tcost, shift_cost)


def ghd(ref, hyp, ins_cost=2.0, del_cost=2.0, shift_cost_coeff=1.0, boundary='1'):
    """
    Compute the Generalized Hamming Distance for a reference and a hypothetical
    segmentation, corresponding to the cost related to the transformation
    of the hypothetical segmentation into the reference segmentation
    through boundary insertion, deletion and shift operations.

    A segmentation is any sequence over a vocabulary of two items
    (e.g. "0", "1"), where the specified boundary value is used to
    mark the edge of a segmentation.

    Recommended parameter values are a shift_cost_coeff of 2.
    Associated with a ins_cost, and del_cost equal to the mean segment
    length in the reference segmentation.

    >>> # Same examples as Kulyukin C++ implementation
    >>> ghd('1100100000', '1100010000', 1.0, 1.0, 0.5)
    0.5
    >>> ghd('1100100000', '1100000001', 1.0, 1.0, 0.5)
    2.0
    >>> ghd('011', '110', 1.0, 1.0, 0.5)
    1.0
    >>> ghd('1', '0', 1.0, 1.0, 0.5)
    1.0
    >>> ghd('111', '000', 1.0, 1.0, 0.5)
    3.0
    >>> ghd('000', '111', 1.0, 2.0, 0.5)
    6.0

    :param ref: the reference segmentation
    :type ref: str or list
    :param hyp: the hypothetical segmentation
    :type hyp: str or list
    :param ins_cost: insertion cost
    :type ins_cost: float
    :param del_cost: deletion cost
    :type del_cost: float
    :param shift_cost_coeff: constant used to compute the cost of a shift.
    shift cost = shift_cost_coeff * |i - j| where i and j are
    the positions indicating the shift
    :type shift_cost_coeff: float
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: float
    """

    ref_idx = [i for (i, val) in enumerate(ref) if val == boundary]
    hyp_idx = [i for (i, val) in enumerate(hyp) if val == boundary]

    nref_bound = len(ref_idx)
    nhyp_bound = len(hyp_idx)

    if nref_bound == 0 and nhyp_bound == 0:
        return 0.0
    elif nref_bound > 0 and nhyp_bound == 0:
        return nref_bound * ins_cost
    elif nref_bound == 0 and nhyp_bound > 0:
        return nhyp_bound * del_cost

    mat = _init_mat(nhyp_bound + 1, nref_bound + 1, ins_cost, del_cost) 
    _ghd_aux(mat, hyp_idx, ref_idx, ins_cost, del_cost, shift_cost_coeff)
    return mat[-1, -1]


# Beeferman's Pk text segmentation evaluation metric

def pk(ref, hyp, k=None, boundary='1'):
    """
    Compute the Pk metric for a pair of segmentations A segmentation
    is any sequence over a vocabulary of two items (e.g. "0", "1"),
    where the specified boundary value is used to mark the edge of a
    segmentation.

    >>> s1 = "00000010000000001000000"
    >>> s2 = "00000001000000010000000"
    >>> s3 = "00010000000000000001000"
    >>> pk(s1, s1, 3)
    0.0
    >>> pk(s1, s2, 3)
    0.095238...
    >>> pk(s2, s3, 3)
    0.190476...

    :param ref: the reference segmentation
    :type ref: str or list
    :param hyp: the segmentation to evaluate
    :type hyp: str or list
    :param k: window size, if None, set to half of the average reference segment length
    :type boundary: str or int or bool
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: float
    """

    if k is None:
        k = int(round(len(ref) / (ref.count(boundary) * 2.)))
    
    n_considered_seg = len(ref) - k + 1
    n_same_ref = 0.0
    n_false_alarm = 0.0
    n_miss = 0.0

    for i in xrange(n_considered_seg):
        bsame_ref_seg = False
        bsame_hyp_seg = False

        if boundary not in ref[(i+1):(i+k)]:
            n_same_ref += 1.0
            bsame_ref_seg = True
        if boundary not in hyp[(i+1):(i+k)]:
            bsame_hyp_seg = True
        
        if bsame_hyp_seg and not bsame_ref_seg:
            n_miss += 1
        if bsame_ref_seg and not bsame_hyp_seg:
            n_false_alarm += 1

    prob_same_ref = n_same_ref / n_considered_seg
    prob_diff_ref = 1 - prob_same_ref
    prob_miss = n_miss / n_considered_seg
    prob_false_alarm = n_false_alarm / n_considered_seg

    return prob_miss * prob_diff_ref + prob_false_alarm * prob_same_ref


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
