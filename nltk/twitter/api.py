# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter API
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Provides an interface for TweetHandlers.
"""
import datetime
from nltk.compat import UTC

class TweetHandlerI(object):
    """
    Interface class whose subclasses should implement a handle method that
    Twitter clients can delegate to.
    """
    def __init__(self, limit=20, date_limit=None):
        """
        :param int limit: The number of data items to process in the current round of\
        processing.

        :param tuple date_limit: The date at which to stop collecting new\
        data. This should be entered as a tuple which can serve as the\
        argument to `datetime.datetime`. E.g. `data_limit=(2015, 4, 1, 12,\
        40)` for 12:30 pm on April 1 2015.

        """
        self.limit = limit
        self.date_limit = date_limit
        if date_limit is not None:
            self.date_limit = datetime.datetime(*date_limit, tzinfo=UTC)

        self.startingup = True
        """A flag to indicate whether this is the first data
        item to be processed in the current round of processing."""
        self.counter = 0

    def handle(self, data):
        """
        Deal appropriately with data returned by the Twitter API
        """
        raise NotImplementedError
