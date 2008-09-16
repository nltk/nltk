#!/usr/bin/env python

from hadooplib.reducer import ReducerBase
from hadooplib.util import *
from nltk.tag.hmm import _log_add, _NINF
from numpy import *
import sys


class EM_Reducer(ReducerBase):
    """
    combine local hmm parameters to estimate a global parameter
    """

    def reduce(self, key, values):
        """
        combine local hmm parameters to estimate a global parameter

        @param key: 'parameters' const string, not used in program
        @param values: various parameter quantity
        """
        A_numer = B_numer = A_denom = B_denom = None
        N = M = 0
        logprob = 0

        states  = []
        symbols = []
        pi = {}
        pi_printed = False

        for value in values:
            # identifier identify different parameter type
            identifier = value.split()[0]
            if identifier == "states":
                if not states:
                    states = value.split()[1:]
            elif identifier == "symbols":
                if not symbols:
                    symbols = value.split()[1:]
            elif identifier == "Pi":
                state, prob = value.split()[1:]
                pi[state] = float(prob)
            else:
                # extract quantities from value
                name, i, j, value, lpk, row, col = str2tuple(value)
                row = int (row)
                col = int (col)
                i = int(i)
                j = int(j)
                value = float(value)
                lpk = float(lpk)
                logprob += lpk

                # add these sums to the global A and B values
                if name == "A":
                    if A_numer is None:
                        A_numer = ones((row, col), float64) * _NINF
                        N = row
                    A_numer[i, j] = _log_add(A_numer[i, j],
                            value - lpk)
                elif name == "B":
                    if B_numer is None:
                        B_numer = ones((row, col), float64) * _NINF
                        M = col
                    B_numer[i, j] = _log_add(B_numer[i, j],
                            value - lpk)
                elif name == "A_denom":
                    if A_denom is None:
                        A_denom = ones(col, float64) * _NINF
                    A_denom[j] = _log_add(A_denom[j], value - lpk)
                elif name == "B_denom":
                    if B_denom is None:
                        B_denom = ones(col, float64) * _NINF
                    B_denom[j] = _log_add(B_denom[j], value - lpk)

        # output the global hmm parameter
        for e in pi:
            self.outputcollector.collect("Pi", tuple2str((e, pi[e])))

        for i in range(N):
            for j in range(N):
                self.outputcollector.collect("A", tuple2str((states[i], \
                        states[j], 2 ** (A_numer[i, j] - A_denom[i]))))


        for i in range(N):
            for j in range(M):
                self.outputcollector.collect("B", tuple2str((states[i], \
                        symbols[j], 2 ** (B_numer[i, j] - B_denom[i]))))

        self.outputcollector.collect("loglikelihood", logprob)


if __name__ == "__main__":
    EM_Reducer().call_reduce()
