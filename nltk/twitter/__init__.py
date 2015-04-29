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
    from twython import Twython, TwythonStreamer
except ImportError as err:
    import textwrap
    MSG = """The NLTK twitterclient module requires the Twython package. See\
    https://twython.readthedocs.org/ for installation instructions."""
    err.msg = textwrap.fill(MSG)
    raise

from nltk.twitter.util import credsfromfile
from nltk.twitter.twitterclient import Streamer, Query, Twitter, TweetViewer,\
     TweetWriter
