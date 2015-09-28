# -*- coding: utf-8 -*-
# Natural Language Toolkit: Machine Translation
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>, Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Experimental features for machine translation.
These interfaces are prone to change.
"""

from nltk.align.api import AlignedSent, Alignment
from nltk.align.ibm_model import IBMModel
from nltk.align.ibm1 import IBMModel1
from nltk.align.ibm2 import IBMModel2
from nltk.align.ibm3 import IBMModel3
from nltk.align.ibm4 import IBMModel4
from nltk.align.ibm5 import IBMModel5
from nltk.align.bleu_score import bleu
from nltk.translate.stack_decoder import StackDecoder
from nltk.translate.phrase_table import PhraseTable
