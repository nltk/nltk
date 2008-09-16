#!/usr/bin/env  python

from hadooplib.reducer import ReducerBase
from math import log

class TFIDFReducer1(ReducerBase):
    """
    computing the TF*IDF value for every word

    (word, [filename occurences...]) -> (word, [filename TF*IDF...])
    """

    def reduce(self, key, values):
        """
        computing the TF*IDF value for every word

        @param key: word
        @param values: filename occurences
        """
        idf = 1
        # first compute the IDF value
        for value in values:
            if value[:3] == "All":
                idf = 1.0/(1 + log(int(value.split(',')[1].strip())))
                values.remove(value)
                break

        # then compute TF*IDF value for each word
        value_str = ""
        for value in values:
            file, tf = value.split(',')
            tf = int(tf.strip())
            value_str += " " + file + "," + str(tf*idf) + " "
        self.outputcollector.collect(key, value_str)

if __name__ == "__main__":
    TFIDFReducer1().call_reduce()
