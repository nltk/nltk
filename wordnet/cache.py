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

DEFAULT_CACHE_CAPACITY = 1000

class _LRUCache:
    """
    A cache of values such that least recently used element is flushed when
    the cache fills.

    This lets us retrieve the key given the timestamp, and the
    timestamp given the key. (Also the value given either one.)
    That's necessary so that we can reorder the history given a key,
    and also manipulate the values dict given a timestamp. 
    
    I haven't tried changing history to a List. An earlier
    implementation of history as a List was slower than what's here,
    but the two implementations aren't directly comparable.

    @type  entities: C{dict}
    @param entities: A dict from key -> (value, timestamp)

    @type  history: C{dict}
    @param history: A dict from timestamp -> key

    @type  nextTimeStamp: C{int}
    @param nextTimeStamp: Timestamp to use with the next value that's added.

    @type  oldestTimeStamp: C{int}
    @param oldestTimeStamp: Timestamp of the oldest element (the next one to
        remove), or slightly lower than that.
    """

    def __init__(self, capacity):
        """
        Initialize a new cache

        @type  capacity: int
        @param capacity: Size of the cache (number of Sense -> Synset mappings)
        """
        self.capacity = capacity
        self.clear()
    
    def clear(self):
        """
        Flush the cache
        """
        self.values = {}
        self.history = {}
        self.oldestTimestamp = 0
        self.nextTimestamp = 1
    
    def removeOldestEntry(self):
        """
        Remove the oldest entry from the cache.
        """
        while self.oldestTimestamp < self.nextTimestamp:

            if self.history.get(self.oldestTimestamp):
                key = self.history[self.oldestTimestamp]
                del self.history[self.oldestTimestamp]
                del self.values[key]
                return

            self.oldestTimestamp = self.oldestTimestamp + 1
    
    def setCapacity(self, capacity):
        """
        Set the capacity of the cache.

        @type  capacity: int
        @param capacity: new size of the cache
        """
        if capacity == 0: self.clear()

        else:
            self.capacity = capacity

            while len(self.values) > self.capacity:
                self.removeOldestEntry()    
    
    def get(self, key, loadfn=None):
        """
        Get an item from the cache.

        @type  key: unknown
        @param key: identifier of a cache entry

        @type  loadfn: function reference
        @param loadfn: a function used to load the cached entry

	@return: a cached item
        """
        value = None

        if self.values:
            pair = self.values.get(key)

            if pair:
                (value, timestamp) = pair
                del self.history[timestamp]

        if value == None:
            value = loadfn and loadfn()

        if self.values != None:
            timestamp = self.nextTimestamp
            self.nextTimestamp = self.nextTimestamp + 1
            self.values[key] = (value, timestamp)
            self.history[timestamp] = key

            if len(self.values) > self.capacity:
                self.removeOldestEntry()

        return value

class _NullCache:
    """
    A NullCache implements the Cache interface (the interface that
    LRUCache implements), but doesn't store any values.
    """

    def clear():
        pass
    
    def get(self, key, loadfn=None):
        return loadfn and loadfn()

def disableCache():
    """Disable the entity cache."""
    entityCache = _NullCache()

def enableCache():
    """Enable the entity cache."""
    if not isinstance(entityCache, LRUCache):
        entityCache = _LRUCache(DEFAULT_CACHE_CAPACITY)

def clearCache():
    """Clear the entity cache."""
    entityCache.clear()

def setCacheCapacity(capacity=DEFAULT_CACHE_CAPACITY):
    """
    Set the capacity of the entity cache.

    @type  capacity: int
    @param capacity: new size of the cache.
    """
    enableCache()
    entityCache.setCapacity(capacity)

def buildIndexFiles():

    for dict in Dictionaries:
        dict._buildIndexCacheFile()

# Create a default cache
entityCache = _LRUCache(DEFAULT_CACHE_CAPACITY)
