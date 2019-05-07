# -*- coding: utf-8 -*-
# Natural Language Toolkit
#
# Copyright (C) 2001-2019 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""Language Model Utilities"""

from math import log

NEG_INF = float("-inf")
POS_INF = float("inf")


def log_base2(score):
    """Convenience function for computing logarithms with base 2."""
    if score == 0.0:
        return NEG_INF
    return log(score, 2)
