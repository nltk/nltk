#!/usr/bin/env  python

from hadooplib.reducer import ReducerBase

class TFReducer(ReducerBase):
    """
    sum the occurences of every word
    """

    def reduce(self, key, values):
        """
        @param key: word
        @param values: list of partial sum
        """
        sum  = 0
        try:
            for value in values:
                sum += int(value) 
            self.outputcollector.collect(key, sum)
        except ValueError:
            #value was not a number, so silently discard this item
            pass

if __name__ == "__main__":
    TFReducer().call_reduce()
