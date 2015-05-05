# Natural Language Toolkit: word embedding package
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

# Import Gensim if installed
try:
    import gensim
except ImportError:
    import warnings
    warnings.warn("gensim package not loaded "
                  "(please install gensim library).")
#else:
