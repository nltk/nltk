#!/usr/bin/env python

from hadooplib.mapper import MapperBase

class WordCountMapper(MapperBase):
    """
    count the occurences of each word
    """

    def map(self, key, value):
        """
        for each word in input, output a (word, 1) pair

        @param key: None, no use
        @param value: line from input
        """
        words = value.split()
        for word in words:
            self.outputcollector.collect(word, 1)

if __name__ == "__main__":
    WordCountMapper().call_map()
