#!/usr/bin/env  python

from hadooplib.mapper import MapperBase
from hadooplib.inputformat import KeyValueInput

class IDFMapper(MapperBase):
    """
    output (word All, 1) for every (word filename, tf) pair

    (word filename, tf) -> (word All, 1)
    """

    def __init__(self):
        MapperBase.__init__(self)
        # use KeyValueInput instead of the default TextLineInput
        self.set_inputformat(KeyValueInput)

    def map(self, key, value):
        """
        output (word All, 1) for every (word filename, tf) pair
        """
        word, filename = key.split()
        # use 'All' to mark the unique occurence
        # of every word in a document
        self.outputcollector.collect(word + " All", 1)

if __name__ == "__main__":
    IDFMapper().call_map()
