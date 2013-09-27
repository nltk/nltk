# Natural Language Toolkit: Applications package
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interactive NLTK Applications:

chartparser:  Chart Parser
chunkparser:  Regular-Expression Chunk Parser
collocations: Find collocations in text
concordance:  Part-of-speech concordancer
nemo:         Finding (and Replacing) Nemo regular expression tool
rdparser:     Recursive Descent Parser
srparser:     Shift-Reduce Parser
wordnet:      WordNet Browser
"""


# Import Tkinter-based modules if Tkinter is installed
import nltk.compat
try:
    import tkinter
except ImportError:
    import warnings
    warnings.warn("nltk.app package not loaded "
                  "(please install Tkinter library).")
else:
    from .chartparser_app import app as chartparser
    from .chunkparser_app import app as chunkparser
    from .collocations_app import app as collocations
    from .concordance_app import app as concordance
    from .nemo_app import app as nemo
    from .rdparser_app import app as rdparser
    from .srparser_app import app as srparser
    from .wordnet_app import app as wordnet

    try:
        import pylab
    except ImportError:
        import warnings
        warnings.warn("nltk.app.wordfreq not loaded "
                      "(requires the pylab library).")
    else:
        from .wordfreq_app import app as wordfreq

# skip doctests from this package
def setup_module(module):
    from nose import SkipTest
    raise SkipTest("nltk.app examples are not doctests")
