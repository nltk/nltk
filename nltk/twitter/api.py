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

'''
The following is not a general purpose object for dealing with the local timezone
- It assumes that the date passed has been created using datetime(..., tzinfo=Local),
  where Local is an instance of the object LocalTimezoneOffsetWithUTC
- For such un object, it returns the offset with UTC, used for date comparations

Reference: https://docs.python.org/3/library/datetime.html
'''
import time as _time
from datetime import tzinfo, timedelta, datetime

class LocalTimezoneOffsetWithUTC(tzinfo):
    STDOFFSET = timedelta(seconds = -_time.timezone)
    if _time.daylight:
        DSTOFFSET = timedelta(seconds = -_time.altzone)
    else:
        DSTOFFSET = STDOFFSET

    def utcoffset(self, dt):
        return self.DSTOFFSET

Local = LocalTimezoneOffsetWithUTC()

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
            self.date_limit = datetime(*date_limit, tzinfo=Local)

        self.startingup = True
        """A flag to indicate whether this is the first data
        item to be processed in the current round of processing."""
        self.counter = 0

    def handle(self, data):
        """
        Deal appropriately with data returned by the Twitter API
        """
        raise NotImplementedError

    def handle_chunk(self, data_chunk):
        """
        Deal appropriately with a list of elements returned by the Twitter API
        (default implementation should be enough in most cases)
        """
        for item in data_chunk:
            self.handle(item)
