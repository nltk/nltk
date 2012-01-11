# Natural Language Toolkit: Inference
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for theorem proving and model building.
"""

from api import ParallelProverBuilder, ParallelProverBuilderCommand
from mace import Mace, MaceCommand
from prover9 import Prover9, Prover9Command
from resolution import ResolutionProver, ResolutionProverCommand
from tableau import TableauProver, TableauProverCommand
from discourse import (ReadingCommand, CfgReadingCommand,
                       DrtGlueReadingCommand, DiscourseTester)
