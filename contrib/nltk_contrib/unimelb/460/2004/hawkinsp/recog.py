#!/usr/bin/python

__doc__ = '''433-460 Human Language Technology Project
Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
Student number: 119004

'''

import sys, string, getopt
from Numeric import array
import hmm, mfcc, vecquant, vector
import continuous_data

words = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09",
         "en", "er", "go", "hp", "no", "rb", "rp", "sp", "st", "ys"]

NUM_STATES = 6
NUM_DIMENSIONS = 12

class UnimplementedException:
    pass

class Recogniser:
    def __init__(self):
        raise UnimplementedException()

    def recognise(self, obs):
        best = None
        best_item = None
        for i in range(len(self.words)):
            pr = self.hmms[i].lnprobability(obs)
            print (i,pr)
            if best is None or pr > best:
                best = pr
                best_item = i

        return (best_item, best)


class ContinuousRecogniser(Recogniser):
    def __init__(self, words):
        self.words = words
        self.hmms = [None] * len(self.words)
        for w in range(len(self.words)):
            self.hmms[w] = hmm.Hmm(
                NUM_STATES,
                hmm.OpdfMultiGaussianFactory(NUM_DIMENSIONS)
            )
            self.hmms[w].a = continuous_data.A[w]
            self.hmms[w].pi = continuous_data.Pi[w]
            for s in range(NUM_STATES):
                self.hmms[w].opdfs[s].mg.setMean(continuous_data.mean[w][s])
                self.hmms[w].opdfs[s].mg.setCovar(continuous_data.covar[w][s])


        
class QuantizedRecogniser(Recogniser):
    def __init__(self, words, codebook):
        self.words = words
        self.hmms = [None] * len(self.words)

        # Read in the codebook
        cbf = open(codebook)
        inp = cbf.readline()

        self.ncbvecs = int(inp)
        self.codebook = []
        for i in range(self.ncbvecs):
            inp = cbf.readline()
            self.codebook.append(
                vector.Vector(array(map(lambda x: float(x), string.split(inp))))
            )

        # Build the HMMs
        for w in range(len(self.words)):
            self.hmms[w] = hmm.Hmm(
                NUM_STATES,
                hmm.OpdfIntegerFactory(self.ncbvecs)
            )
            self.hmms[w].a = quantized_data.A[w]
            self.hmms[w].pi = quantized_data.Pi[w]
            for s in range(NUM_STATES):
                self.hmms[w].opdfs[s].setProbabilities(quantized_data.prob[w][s])

    def recognise(self, obs):
        qobs = map(lambda x:
            vecquant.closest_codeword(self.codebook, vector.Vector(array(x))),
            obs)
        return Recogniser.recognise(self, qobs)

def usage():
    print '''recog.py [-q <codebook size>]

If the optional '-q XX' argument is passed, vector quantization will be used.
The HMM specification from qXX_data.py and the codebook from codeXX.txt will
be used for the recognition and quantization, respectively.

If '-q' is not passed, continuous density HMMs from continuous_data.py will
be used instead.
'''


# Parse the command line arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "q:", ["quantize="])
except getopt.GetoptError:
    usage()
    sys.exit(1)

codebook_size = None
for o, a in opts:
    if o in ("-q", "--quantize"):
        codebook_size = a

# Create either a continuous or quantized recogniser, depending on the
# arguments
recog = None
if codebook_size is None:
    recog = ContinuousRecogniser(words)
else:
    if codebook_size == "4":
        import q4_data as quantized_data
    elif codebook_size == "8":
        import q8_data as quantized_data
    elif codebook_size == "16":
        import q16_data as quantized_data
    elif codebook_size == "32":
        import q32_data as quantized_data
    elif codebook_size == "64":
        import q64_data as quantized_data
    elif codebook_size == "128":
        import q128_data as quantized_data

    codebook="code%s.txt" % (codebook_size, )
    recog = QuantizedRecogniser(words, codebook)



# Process the input files
for a in args:
    obs = mfcc.extractfeatures(a)
    (best_item, best) = recog.recognise(obs)
    print "Input file %s is most probably a '%s' with log probability %.2f" % (
        a, words[best_item], best
    )
