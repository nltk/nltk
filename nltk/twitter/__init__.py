# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Twitter Package

This package contains classes for retrieving Tweet documents using the
Twitter API.

"""
try:
    import twython
except ImportError:
    import warnings
    warnings.warn("nltk.twitter package not loaded "
                  "(please install twython library).")

from nltk.twitter.util import Authenticate, credsfromfile, json2csv
from nltk.twitter.twitterclient import Streamer, Query, Twitter,\
     TweetViewer, TweetWriter
