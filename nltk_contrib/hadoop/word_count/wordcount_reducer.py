#!/usr/bin/env python

from hadooplib.reducer import ReducerBase

class WordCountReducer(ReducerBase):
    """
    count the occurences of each word
    """

    def reduce(self, key, values):
        """
        for each word, accmulate all the partial sum

        @param key: word
        @param values: list of partical sum
        """
        sum  = 0
        try:
            for value in values:
                sum += int(value) 
            self.outputcollector.collect(key, sum)
        except ValueError:
            #count was not a number, so silently discard this item
            pass

if __name__ == "__main__":
    WordCountReducer().call_reduce()
