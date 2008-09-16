#!/usr/bin/env python

from hadooplib.reducer import ReducerBase

class Name2SimiliarName(ReducerBase):
    """
    find the most simliar name for the given name, 
    from the name before and after it

    e.g. (Adam, Ada Adams) -> (Adam, Ada)
    """

    def reduce(self, key, values):
        """
        find the most simliar name for the given name 

        @param key: the given name
        @param values: the name before and after the given name
        """
        li  = values[0].strip().split()

        # solve the boundary case: the name is at the head or at the tail
        if len(li) == 1:
            li.append("")
        before, after = li[0], li[1]

        sim1 = self.similiarity(key, before)
        sim2 = self.similiarity(key, after)

        if sim1 >= sim2:
            self.outputcollector.collect(key, before)
        else:
            self.outputcollector.collect(key, after)

    def similiarity(self, name1, name2):
        """
        compute the similarity between name1 and name2

        e.g. similiarity("Ada", "Adam") = 3
        """

        n = min(len(name1), len(name2))
        for i in range(n):
            if (name1[i] != name2[i]):
                return i + 1
        return n 

if __name__ == "__main__":
    Name2SimiliarName().call_reduce()
