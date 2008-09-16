#!/usr/bin/env  python

from hadooplib.mapper import MapperBase
from hadooplib.inputformat import KeyValueInput

class TFIDFMapper1(MapperBase):
    """
    keep only the word in the key field
    remove filename from key and put it into value

    (word filename, number) -> (word, filename number)
    e.g. (dog 1.txt, 1) -> (dog, 1.txt 1)
    """
    def __init__(self):
        MapperBase.__init__(self)
        self.set_inputformat(KeyValueInput)

    def map(self, key, value):
        """
        extract filename from key and put it into value

        @param key: word and filename
        @param value: term frequency
        """
        word, filename = key.split()
        self.outputcollector.collect(word, filename + "," + value)

if __name__ == "__main__":
    TFIDFMapper1().call_map()
