# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter API
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Provides an interface for TweetHandlers.
"""

class TweetHandlerI(object):
    """
    Interface class whose subclasses should implement a handle method that
    Twitter clients can delegate to.
    """
    def __init__(self, limit=20):
        """
        :param limit: number of data items to process in the current round of
        processing

        :param startingup: flag to indicate whether this is the first data
        item to be processed in the current round of processing.

        :param counter: keep track of number of data items processed

        """
        self.limit = limit
        self.startingup = True
        self.counter = 0

    def handle(self, data):
        """
        Deal appropriately with data returned by the Twitter API
        """
        raise NotImplementedError
