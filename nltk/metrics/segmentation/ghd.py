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



def ghd(seg1, seg2, ins_cost=2., del_cost=2., shift_cost_coeff=1., boundary='1'):
    """
    Compute the Generalized Hamming Distance for a pair of segmentations
    A segmentation is any sequence over a vocabulary
    of two items (e.g. "0", "1"),
    where the specified boundary value is used
    to mark the edge of a segmentation

    :param seg1: a segmentation
    :type seg1: str or list
    :param seg2: a segmentation
    :type seg2: str or list
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

    # get boundaries positions
    rvec = _fill_bit_pos_vec(seg1, boundary)
    cvec = _fill_bit_pos_vec(seg2, boundary)
    nrows = len(rvec)
    ncols = len(cvec)

    if nrows == 0 and ncols == 0:
        # no boundaries in both segmentations
        return 0.
    elif nrows > 0 and ncols == 0:
        # if there are no boundaries in seg1
        # return the cost of the insertions
        return (nrows) * ins_cost
    elif nrows == 0 and ncols > 0:
        # if there are no boundaries in seg2
        # return the cost of deletions
        return (ncols) * del_cost
        
    # both segmentations contain boundary symbols
    mat = _init_mat(nrows + 1, ncols + 1, ins_cost, del_cost) 
    _compute_ghd_aux(mat, rvec, cvec, ins_cost, del_cost, shift_cost_coeff)
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
    for seg1, seg2, ins_cost, del_cost, shift_cost_coeff in tests:
        ret = ghd(seg1, seg2, ins_cost, del_cost, shift_cost_coeff)
        print pat % (seg1, seg2, ins_cost, del_cost, shift_cost_coeff, ret)
