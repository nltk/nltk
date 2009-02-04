# Natural Language Toolkit: Applications package
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: __init__.py 7460 2009-01-29 01:06:02Z StevenBird1 $

# Import Tkinter-based modules if Tkinter is installed
try:
    import Tkinter
    from chart import *
    from rdparser import *
    from srparser import *
    from rechunkparser import RegexpChunkDemo
    from concordance import pos_concordance
    from wordnet_browser import wnb
    from nemo import finding_nemo

except ImportError:
    print "Warning: nltk.app package not loaded (please install Tkinter library)."
