# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter API
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
This module provides an interface for TweetHandlers, and support for timezone
handling.
"""

from datetime import tzinfo, timedelta, datetime
import time as _time


class LocalTimezoneOffsetWithUTC(tzinfo):
    """
    This is not intended to be a general purpose class for dealing with the
    local timezone. In particular:

    * it assumes that the date passed has been created using
      `datetime(..., tzinfo=Local)`, where `Local` is an instance of
      the object `LocalTimezoneOffsetWithUTC`;
    * for such an object, it returns the offset with UTC, used for date comparisons.

    Reference: https://docs.python.org/3/library/datetime.html
    """
    STDOFFSET = timedelta(seconds=-_time.timezone)

    if _time.daylight:
        DSTOFFSET = timedelta(seconds=-_time.altzone)
    else:
        DSTOFFSET = STDOFFSET

    def utcoffset(self, dt):
        """
        Access the relevant time offset.
        """
        return self.DSTOFFSET

LOCAL = LocalTimezoneOffsetWithUTC()

class BasicTweetHandler(object):
    """
    Minimum implementation of TweetHandler
    Counts the number of tweets and decides when the client shoud stop
    fetching tweets
    """
    def __init__(self, limit=20):
        self.limit = limit
        self.counter = 0
        
        """A flag to indicate that to the client to stop for
        a functional clause (e.g. date limit)"""
        self.do_stop = False

    def do_continue(self):
        """
        Returns false if the client should stop fetching tweets
        """
        return self.counter < self.limit and not self.do_stop

class TweetHandlerI(BasicTweetHandler):
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
        BasicTweetHandler.__init__(self, limit)

        self.date_limit = date_limit
        if date_limit is not None:
            self.date_limit = datetime(*date_limit, tzinfo=LOCAL)

        self.startingup = True

    def handle(self, data):
        """
        Deal appropriately with data returned by the Twitter API
        """
        raise NotImplementedError

    def on_finish(self):
        """
        Actions when the tweet limit has been reached
        """
        raise NotImplementedError
        