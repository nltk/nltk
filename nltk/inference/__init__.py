# Natural Language Toolkit: Inference
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#         
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for theorem proving and model building.
"""

from api import *
from mace import *
from prover9 import *
from resolution import *
from tableau import *
from discourse import *

__all__ = [
    # inference tools
    'Prover9', 'Prover9Command',
    'TableauProver', 'TableauProverCommand', 
    'ResolutionProver', 'ResolutionProverCommand',
    'Mace', 'MaceCommand',
    'ParallelProverBuilder', 'ParallelProverBuilderCommand',
    
    # discourse
    'ReadingCommand', 'CfgReadingCommand', 'DrtGlueReadingCommand', 'DiscourseTester'
    ]
