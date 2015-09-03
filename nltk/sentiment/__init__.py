# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Sentiment Analysis Package

"""
try:
    import twython
except ImportError:
    import warnings
    warnings.warn("nltk.sentiment package not loaded "
                  "(please install twython library).")

from nltk.sentiment.sentiment_analyzer import SentimentAnalyzer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
