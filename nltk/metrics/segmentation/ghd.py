# Natural Language Toolkit: Generalized Hamming Distance
#
# Copyright (C) 2001-2012 NLTK Project
# Author: David Doukhan <david.doukhan@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Implementation of Generalized Hamming Distance as a text segmentation metric

Bookstein A., Kulyukin V.A., Raita T.
Generalized Hamming Distance
Information Retrieval 5, 2002, pp 353-375

Baseline implementation in C++
http://digital.cs.usu.edu/~vkulyukin/vkweb/software/ghd/ghd.html

Study describing benefits of Generalized Hamming Distance Versus
WindowDiff for evaluating text segmentation tasks
Begsten, Y.  Quel indice pour mesurer l'efficacite en segmentation de textes ?
TALN 2009
"""

import numpy

def _init_mat(nrows, ncols, ins_cost, del_cost):
    mat = numpy.empty((nrows, ncols))
    mat[0, :] = [x * ins_cost for x in xrange(ncols)]
    mat[:, 0] = [x * del_cost for x in xrange(nrows)]
    return mat

def _fill_bit_pos_vec(bitv, boundary):
    """Returns the indices of bitv containing the given boundary value"""
    return [i for (i, val) in enumerate(bitv) if val == boundary]

def _compute_ghd_aux(mat, rowv, colv, ins_cost, del_cost, shift_cost_coeff):
    for i, rowi in enumerate(rowv):
        for j, colj in enumerate(colv):          
            shift_cost = shift_cost_coeff * abs(rowi - colj) + mat[i, j]
            if rowi == colj:
                # boundaries are at the same location
                # no transformation is required to match them
                tcost = mat[i, j]
            elif rowi > colj:
                # boundary match through a deletion
                tcost = del_cost + mat[i, j + 1]
            else:
                # boundary match through an insertion
                tcost = ins_cost + mat[i + 1, j]
            # keep minimal cost between intertion, deletion, or shift
            mat[i + 1, j + 1] = min(tcost, shift_cost)



def ghd(ref_seg, hyp_seg, ins_cost=2., del_cost=2., shift_cost_coeff=1., boundary='1'):
    """
    Compute the Generalized Hamming Distance for a reference and an hypothetic
    segmentation, corresponding to the cost related to the transformation
    of the hypothetical segmentation into the reference segmentation
    through boundary insert, delete and shift operations

    A segmentation is any sequence over a vocabulary
    of two items (e.g. "0", "1"),
    where the specified boundary value is used
    to mark the edge of a segmentation

    Recommended parameter values are a shift_cost_coeff of 2.
    Associated with a ins_cost, and del_cost equal to the mean segment
    length in the reference segmentation
 
    :param ref_seg: the reference segmentation
    :type ref_seg: str or list
    :param hyp_seg: the hypothetical segmentation
    :type hyp_seg: str or list
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

    # reference segmentation boundaries indices
    ref_bound_idx = _fill_bit_pos_vec(ref_seg, boundary)
    # number of segments in reference segmentation
    nref_bound = len(ref_bound_idx)

    # hypothetical segmentation boundaries indices
    hyp_bound_idx = _fill_bit_pos_vec(hyp_seg, boundary)
    # number of segments in reference segmentation
    nhyp_bound = len(hyp_bound_idx)

    if nref_bound == 0 and nhyp_bound == 0:
        # no boundaries in both segmentations
        return 0.
    elif nref_bound > 0 and nhyp_bound == 0:
        # if there are no boundaries in hypothetical segmentation
        # return the cost of the insertions
        return nref_bound * ins_cost
    elif nref_bound == 0 and nhyp_bound > 0:
        # if there are no boundaries in reference segmentation
        # return the cost of deletions
        return nhyp_bound * del_cost

    # both segmentations contain boundary symbols
    mat = _init_mat(nhyp_bound + 1, nref_bound + 1, ins_cost, del_cost) 
    _compute_ghd_aux(mat, hyp_bound_idx, ref_bound_idx, ins_cost, del_cost, shift_cost_coeff)
    return mat[-1, -1]


def demo():
    """
    Same examples than those of Kulyukin C++ implementation
    """  
    tests = [
        ('1100100000', '1100010000', 1., 1., .5),
        ('1100100000', '1100000001', 1., 1., .5),
        ('011', '110', 1., 1., .5),
        ('1', '0', 1., 1., .5),
        ('111', '000', 1., 1., .5),
        # Note that the cost of deletion is 2.0, hence the value of
        # 6.0.
        ('000', '111', 1., 2., .5)
        ]

    pat = 'ghd(\'%s\', \'%s\', %.1f, %.1f, %.1f) = %.1f'
    for ref_seg, hyp_seg, ins_cost, del_cost, shift_cost_coeff in tests:
        ret = ghd(ref_seg, hyp_seg, ins_cost, del_cost, shift_cost_coeff)
        print pat % (ref_seg, hyp_seg, ins_cost, del_cost, shift_cost_coeff, ret)
