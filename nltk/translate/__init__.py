# -*- coding: utf-8 -*-
# Natural Language Toolkit: Machine Translation
#
# Copyright (C) 2001-2017 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>, Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Experimental features for machine translation.
These interfaces are prone to change.
"""

from nltk.translate.api import AlignedSent, Alignment, PhraseTable
from nltk.translate.bleu_score import sentence_bleu as bleu
from nltk.translate.ibm1 import IBMModel1
from nltk.translate.ibm2 import IBMModel2
from nltk.translate.ibm3 import IBMModel3
from nltk.translate.ibm4 import IBMModel4
from nltk.translate.ibm5 import IBMModel5
from nltk.translate.ibm_model import IBMModel
from nltk.translate.metrics import alignment_error_rate
from nltk.translate.ribes_score import sentence_ribes as ribes
from nltk.translate.stack_decoder import StackDecoder

