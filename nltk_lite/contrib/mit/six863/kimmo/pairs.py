class KimmoPair(object):
    """
    Input/Output character pair
    """
    def __init__(self, input_subset, output_subset):
        self._input = input_subset
        self._output = output_subset


    def input(self): return self._input
    def output(self): return self._output


    def __repr__(self):
        sI = self.input()
        sO = self.output()
        s = sI + ':' + sO
        return s

    def __cmp__(self, other):
        if type(self) != type(other): return -1
        return cmp( (self._input, self._output), (other.input(),
        other.output()))

    def __hash__(self):
        return hash( (self._input, self._output) )

    def includes(self, pair, subsets):
        return (self._matches(self.input(), pair.input(), subsets) and
                self._matches(self.output(), pair.output(), subsets))
    
    def matches(self, input, output, subsets, negatedOutputMatch=False):
        if not(self._matches(self.input(), input, subsets)): return False
        m = self._matches(self.output(), output, subsets)
        if negatedOutputMatch: return not(m)
        return m


    def _matches(self, me, terminal, subsets):
        if (me == terminal): return True
        if (me[0] == '~'):
            m = me[1:]
            if (m in subsets):
                return not(terminal in subsets[m])
            else:
                return False
        if (me in subsets):
            return terminal in subsets[me]
        else:
            return False
    
    @staticmethod
    def make(text):
        parts = text.split(':')
        if len(parts) == 1: return KimmoPair(text, text)
        elif len(parts) == 2: return KimmoPair(parts[0], parts[1])
        else: raise ValueError, "Bad format for pair: %s" % text

