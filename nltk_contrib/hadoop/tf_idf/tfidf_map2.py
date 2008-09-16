#!/usr/bin/env  python

from hadooplib.mapper import MapperBase
from hadooplib.inputformat import KeyValueInput

class TFIDFMapper2(MapperBase):
    """
    sort TF*IDF value by filename

    (word, [filename TF*IDF...]) -> (filename TF*IDF, word)
    """

    def __init__(self):
        MapperBase.__init__(self)
        self.set_inputformat(KeyValueInput)
    
    def map(self, key, value):
        """
        do some content swapping and extraction on key and value

        @param key: word
        @param value: filename TF*IDF
        """
        elements  = value.split()
        for e in elements:
            e = e.replace(',', ' ')
            self.outputcollector.collect(e, key)
    
if __name__ == "__main__":
    TFIDFMapper2().call_map()
