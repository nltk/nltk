# -*- coding: utf-8 -*-


# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#          Edward Loper <edloper@gmail.com>
#          Steven Bird <stevenbird1@gmail.com>
#          Marcus Uneson <marcus.uneson@gmail.com>
# URL: <http://nltk.org/>
# For license information, see  LICENSE.TXT
from __future__ import print_function


# returns a list of errors in string format

def error_list (train_sents, test_sents, radius=2):
    """
    Returns a list of human-readable strings indicating the errors in the
    given tagging of the corpus.

    :param train_sents: The correct tagging of the corpus
    :type train_sents: list(tuple)
    :param test_sents: The tagged corpus
    :type test_sents: list(tuple)
    :param radius: How many tokens on either side of a wrongly-tagged token
        to include in the error string.  For example, if radius=2,
        each error string will show the incorrect token plus two
        tokens on either side.
    :type radius: int
    """
    hdr = (('%25s | %s | %s\n' + '-'*26+'+'+'-'*24+'+'+'-'*26) %
           ('left context', 'word/test->gold'.center(22), 'right context'))
    errors = [hdr]
    for (train_sent, test_sent) in zip(train_sents, test_sents):
        for wordnum, (word, train_pos) in enumerate(train_sent):
            test_pos = test_sent[wordnum][1]
            if train_pos != test_pos:
                left = ' '.join('%s/%s' % w for w in train_sent[:wordnum])
                right = ' '.join('%s/%s' % w for w in train_sent[wordnum+1:])
                mid = '%s/%s->%s' % (word, test_pos, train_pos)
                errors.append('%25s | %s | %s' %
                              (left[-25:], mid.center(22), right[:25]))

    return errors
