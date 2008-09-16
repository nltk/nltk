#!/usr/bin/env  python

from hadooplib.mapper import MapperBase

class TFMapper(MapperBase):
    """
    get the filename (one filename per line), 
    open the file and count the term frequency.
    """

    def map(self, key, value):
        """
        output (word filename, 1) for every word in files

        @param key: None
        @param value: filename
        """
        filename = value.strip()
        if len(filename) == 0:
            return
        file = open(filename, 'r')
        for line in file:
            words = line.strip().split()
            for word in words:
                self.outputcollector.collect(word + " " + filename, 1)

if __name__ == "__main__":
    TFMapper().call_map()
