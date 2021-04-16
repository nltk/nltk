# Natural Language Toolkit: SVM-based classifier
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Leon Derczynski <leon@dcs.shef.ac.uk>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
nltk.classify.svm was deprecated. For classification based
on support vector machines SVMs use nltk.classify.scikitlearn
(or `scikit-learn <http://scikit-learn.org>`_ directly).
"""


class SvmClassifier(object):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(__doc__)
