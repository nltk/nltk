# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Twitter Package

This package contains classes for retrieving Tweet documents using the
Twitter API.

"""
#try:
    #from twython import Twython, TwythonStreamer
#except ImportError as e:
    #e.msg = """The twitterclient module requires the Twython
    #package. See https://twython.readthedocs.org/ for installation
    #instructions."""
    #raise

from nltk.twitter.util import credsfromfile
from nltk.twitter.twitterclient import Streamer, Query, Twitter, TweetViewer,\
     TweetWriter

# skip doctests from this package
def setup_module(module):
    from nose import SkipTest
    raise SkipTest("nltk.twitter examples are not doctests")


if __name__ == "__main__":
    from twitterclient import Twitter
    tw = Twitter()