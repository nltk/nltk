# Natural Language Toolkit: Treebank Tagged Tokenizer
#
# Copyright (C) 2004 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Single tokenizer class for loading part-of-speech tagged data from the Penn
Treebank. This extends the L{TaggedTokenizer} to support the additional markup
present in these files.

@group Tokenizers: TreebankTaggedTokenizer
"""

from nltk.tagger import TaggedTokenReader
import re

