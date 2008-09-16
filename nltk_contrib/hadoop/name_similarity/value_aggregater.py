#!/usr/bin/env python

from hadooplib.reducer import ReducerBase
from hadooplib.util import tuple2str

class ValueAggregater(ReducerBase):
    """
    aggregate the values having the same key.

    e.g. (animal, cat)
         (animal, dog)
         (animal, mouse)
         
         -> 
         
         (animal, cat dog mouse)
    """

    def reduce(self, key, values):
        """
        aggregate the values having the same key.
        """
        values_str = tuple2str(tuple(values))
        self.outputcollector.collect(key, values_str)

if __name__ == "__main__":
    ValueAggregater().call_reduce()
