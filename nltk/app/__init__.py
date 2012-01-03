# Natural Language Toolkit: Applications package
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: __init__.py 7460 2009-01-29 01:06:02Z StevenBird1 $

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
try:
    import Tkinter
except ImportError:
    import warnings
    warnings.warn("nltk.app package not loaded "
                  "(please install Tkinter library).")
else:
    from chartparser_app import app as chartparser
    from chunkparser_app import app as chunkparser
    from collocations_app import app as collocations
    from concordance_app import app as concordance
    from nemo_app import app as nemo
    from rdparser_app import app as rdparser
    from srparser_app import app as srparser
    from wordnet_app import app as wordnet

    try:
        import pylab
    except ImportError:
        import warnings
        warnings.warn("nltk.app.wordfreq not loaded "
                      "(requires the pylab library).")
    else:
        from wordfreq_app import app as wordfreq
