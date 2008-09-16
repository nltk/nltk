#!/usr/bin/env python

from hadooplib.inputformat import KeyValueInput
from hadooplib.mapper import MapperBase
from hadooplib.util import tuple2str

class Name2Names(MapperBase):
    """
    map a name to the name before and after it

    e.g. (A, Ada Adam Adams) -> (Adam, Ada Adams)
    """

    def __init__(self):
        MapperBase.__init__(self)
        self.set_inputformat(KeyValueInput)

    def map(self, key, value):
        """
        map a name to the name before and after it

        @param key: the first character of a name
        @param value: all the names start with the key
        """
        namelist = value.strip().split()
        namelist.insert(0, '')
        namelist.append('')
        n = len(namelist)
        for i in range(1, n - 1):
            self.outputcollector.collect(namelist[i], \
                    tuple2str((namelist[i-1] ,namelist[i+1])))
    
if __name__ == "__main__":
    Name2Names().call_map()
