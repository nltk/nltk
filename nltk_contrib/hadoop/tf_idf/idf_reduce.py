#!/usr/bin/env  python

from hadooplib.reducer import ReducerBase

class IDFReducer(ReducerBase):

    def reduce(self, key, values):
        sum  = 0
        try:
            for value in values:
                sum += int(value) 
            self.outputcollector.collect(key, sum)
        except ValueError:
            #count was not a number, so silently discard this item
            pass

if __name__ == "__main__":
    IDFReducer().call_reduce()
