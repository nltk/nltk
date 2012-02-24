# Natural Language Toolkit: Beeferman's Pk text segmentation evaluation metric
#
# Copyright (C) 2001-2012 NLTK Project
# Author: David Doukhan <david.doukhan@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT



"""
Implementation of Pk text segmentation evaluation metric

Beeferman D., Berger A., Lafferty J.
Statistical Models for Text Segmentation
Machile Learning, 34(1-3): 177-210 (1999)
"""

def Pk(ref, hyp, k=None, boundary='1'):
    """
    Compute the Pk metric for a pair of segmentations
    A segmentation is any sequence over a vocabulary
    of two items (e.g. "0", "1"),
    where the specified boundary value is used
    to mark the edge of a segmentation

    :param ref: the reference segmentation
    :type ref: str or list
    :param hyp: the segmentation to evaluate
    :type hyp: str or list
    :param k: window size. if set to None: window size is half of the average reference segment length
    :type boundary: str or int or bool
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: float
    """

    if k is None:
        k = int(round(len(ref) / (ref.count(boundary) * 2.)))
    
    n_considered_seg = len(ref) - k + 1
    n_same_ref = 0.
    n_false_alarm = 0.
    n_miss = 0.

    for i in xrange(n_considered_seg):
        bsame_ref_seg = False
        bsame_hyp_seg = False

        if boundary not in ref[(i+1):(i+k)]:
            n_same_ref += 1.
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


def demo():
    s1 = "00000010000000001000000"
    s2 = "00000001000000010000000"
    s3 = "00010000000000000001000"
    print "s1:", s1
    print "s2:", s2
    print "s3:", s3

    print "Pk(s1, s1, 3) = ", Pk(s1, s1, 3)
    print "Pk(s1, s2, 3) = ", Pk(s1, s2, 3)
    print "Pk(s2, s3, 3) = ", Pk(s2, s3, 3)
