# Natural Language Toolkit: Generalized Hamming Distance for evaluating text segmentation
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

def _init_tableau(nrows, ncols, ci, cd):
    tab = numpy.empty((nrows, ncols))
    tab[0, :] = [x * ci for x in xrange(ncols)]
    tab[:, 0] = [x * cd for x in xrange(nrows)]
    return tab

def _fill_bit_pos_vec(bitv, boundary):
    """Returns the indices of bitv containing the given boundary value"""
    return [i for (i, val) in enumerate(bitv) if val == boundary]

def _compute_ghd_aux(tab, rowv, colv, ci, cd, a):
    for i, ri in enumerate(rowv):
        for j, cj in enumerate(colv):
            shiftCost = a * abs(ri - cj) + tab[i, j]
            if ri > cj:
                delCost = cd + tab[i, j + 1]
                # compute the minimum cost
                if delCost < shiftCost:
                    minCost = delCost
                else:
                    minCost = shiftCost
            elif ri < cj:
                insCost = ci + tab[i + 1, j]
                # compute the minimum cost
                if insCost < shiftCost:
                    minCost = insCost
                else:
                    minCost = shiftCost
            else:
                minCost = tab[i, j]
            tab[i + 1, j + 1] = minCost



def ghd(seg1, seg2, ci=2., cd=2., a=1., boundary='1'):
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
    :param ci: insertion cost
    :type ci: float
    :param cd: deletion cost
    :type cd: float
    :param a: constant used to compute the cost of a shift. shift cost = a * |i - j| where i and j are the positions indicating the shift
    :type a: float
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: float
    """

    # build the bite-site for the target.
    rvec = _fill_bit_pos_vec(seg1, boundary)
    nrows = len(rvec)
    # build the bite-site for the source.
    cvec = _fill_bit_pos_vec(seg2, boundary)
    ncols = len(cvec)

    if nrows == 0 and ncols == 0:
        return 0.
    elif nrows > 0 and ncols == 0:
        # if there are no bits in the target,
        # return the cost of the insertions.
        return (nrows) * ci
    elif nrows == 0 and ncols > 0:
        return (ncols) * cd
        
    # both nrows > 0 and ncols > 0
    tab = _init_tableau(nrows + 1, ncols + 1, ci, cd) 
    _compute_ghd_aux(tab, rvec, cvec, ci, cd, a)
    return tab[-1, -1]


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

    # ref results: .5, 2, 1, 1, 3, 6
    for seg1, seg2, ci, cd, a in tests:
        ret = ghd(seg1, seg2, ci, cd, a)
        print 'ghd(\'%s\', \'%s\', %.1f, %.1f, %.1f) = %.1f' % (seg1, seg2, ci, cd, a, ret)
