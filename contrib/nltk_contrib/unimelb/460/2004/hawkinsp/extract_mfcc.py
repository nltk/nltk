#!/usr/bin/python

__doc__ = '''
433-460 Human Language Technology Project
Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
Student Number: 119004

MFCC feature extraction utility.

Given a list of .WAV file arguments, derive Mel Frequency Cepstral Coefficients
and output the results to standard output.

The input .WAV files must be in 11025hz 16-bit signed mono format. No checking
of this is done by the sample reading code, so ensure that your input is
in the correct format.
'''

import sys, getopt, string
from Numeric import array
import mfcc, vecquant, vector

def usage():
    print """mfcc_extract.py [-j] [ -q <codebook> ] <input file names>
    
The optional '-q' argument should be passed if the output vectors should be
quantized according to a codebook.
"""

# Parse the command line arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "q:j", ["quantize="])
except getopt.GetoptError:
    usage()
    sys.exit(1)

codebook_file = None
for o, a in opts:
    if o in ("-q", "--quantize"):
        codebook_file = a

# Read in the codebook if necessary
codebook = []
if codebook_file is not None:
    cbf = open(codebook_file)
    inp = cbf.readline()

    ncbvecs = int(inp)
    for i in range(ncbvecs):
        inp = cbf.readline()
        codebook.append(
            vector.Vector(array(map(lambda x: float(x), string.split(inp))))
        )
 

# Process the input files
for a in args:
    # Extract the MFCC features
    features = mfcc.extractfeatures(a)

    # Print out either the features themselves or their quantized versions
    for vec in features:
        if codebook_file is None:
            sys.stdout.write("[ ")
            for x in vec:
                sys.stdout.write("%.2f " % (x,))
            sys.stdout.write("] ; ")

        else:
            sys.stdout.write("%d ; " % (
                vecquant.closest_codeword(codebook, vector.Vector(array(vec))),
                )
            )
    sys.stdout.write("\n")
            
