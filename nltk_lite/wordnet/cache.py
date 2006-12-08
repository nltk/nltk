# Natural Language Toolkit: Wordnet Interface: Cache Module
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Some kind of cache is necessary since Sense -> Synset references are
# stored by key, and it's nice not to have to cons a new copy of a
# Synset that's been paged in each time a Sense's synset is retrieved.
# Ideally, we'd use a weak dict, but there aren't any.  A strong dict
# reintroduces the problem that eliminating the Sense <-> Synset
# circularity was intended to resolve: every entity ever seen is
# preserved forever, making operations that iterate over the entire
# database prohibitive.
#
# The LRUCache approximates a weak dict in the case where temporal
# locality is good.

from nltk_lite.wordnet import *

class _LRUCache:
    """
    A cache of values such that least recently used element is flushed when
    the cache fills.
    
    Private fields
    --------------
    entities
      a dict from key -> (value, timestamp)
    history
      is a dict from timestamp -> key
    nextTimeStamp
      is the timestamp to use with the next value that's added.
    oldestTimeStamp
      The timestamp of the oldest element (the next one to remove),
      or slightly lower than that.
    
      This lets us retrieve the key given the timestamp, and the
      timestamp given the key. (Also the value given either one.)
      That's necessary so that we can reorder the history given a key,
      and also manipulate the values dict given a timestamp.  #
    
      I haven't tried changing history to a List. An earlier
      implementation of history as a List was slower than what's here,
      but the two implementations aren't directly comparable.
    """

    def __init__(this, capacity):
        this.capacity = capacity
        this.clear()
    
    def clear(this):
        this.values = {}
        this.history = {}
        this.oldestTimestamp = 0
        this.nextTimestamp = 1
    
    def removeOldestEntry(this):

        while this.oldestTimestamp < this.nextTimestamp:

            if this.history.get(this.oldestTimestamp):
                key = this.history[this.oldestTimestamp]
                del this.history[this.oldestTimestamp]
                del this.values[key]
                return

            this.oldestTimestamp = this.oldestTimestamp + 1
    
    def setCapacity(this, capacity):

        if capacity == 0: this.clear()

        else:
            this.capacity = capacity

            while len(this.values) > this.capacity:
                this.removeOldestEntry()    
    
    def get(this, key, loadfn=None):
        value = None

        if this.values:
            pair = this.values.get(key)

            if pair:
                (value, timestamp) = pair
                del this.history[timestamp]

        if value == None:
            value = loadfn and loadfn()

        if this.values != None:
            timestamp = this.nextTimestamp
            this.nextTimestamp = this.nextTimestamp + 1
            this.values[key] = (value, timestamp)
            this.history[timestamp] = key

            if len(this.values) > this.capacity:
                this.removeOldestEntry()

        return value

class _NullCache:
    """
    A NullCache implements the Cache interface (the interface that
    LRUCache implements), but doesn't store any values.
    """

    def clear():
        pass
    
    def get(this, key, loadfn=None):
        return loadfn and loadfn()

DEFAULT_CACHE_CAPACITY = 1000
entityCache = _LRUCache(DEFAULT_CACHE_CAPACITY)

def disableCache():
    """Disable the entity cache."""
    _entityCache = _NullCache()

def enableCache():
    """Enable the entity cache."""
    if not isinstance(_entityCache, LRUCache):
        _entityCache = _LRUCache(DEFAULT_CACHE_CAPACITY)

def clearCache():
    """Clear the entity cache."""
    _entityCache.clear()

def setCacheCapacity(capacity=DEFAULT_CACHE_CAPACITY):
    """Set the capacity of the entity cache."""
    enableCache()
    _entityCache.setCapacity(capacity)

setCacheSize = setCacheCapacity # for compatability with version 1.0

def buildIndexFiles():

    for dict in Dictionaries:
        dict._buildIndexCacheFile()

