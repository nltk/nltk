__doc__ = '''
433-460 Human Language Technology Project

Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
Student number: 119004

A Hidden Markov Model implementation, derived from the Java HMM implementation
in jahmm.

The HMM implementation in NLTK is not sufficient for our purposes, since it does
not support HMMs with continuous probability distribution outputs. While not
absolutely necessary for speech recognition (for example, techniques such as
Vector Quantization can be used to make the problem a discrete one),
continuous probability distributions perform much better empirically than
discrete approaches.

I do not claim any particular originality for this code -- it is effectively a
direct port of the necessary features from the Java code in jahmm to Python.
Interestingly the resulting code is much shorter =)

Only the forward/scaled forward algorithms are implemented since they are all
we need for this particular application.
'''

import math
from Numeric import *
from LinearAlgebra import *

class UnimplementedException:
    '''UnimplementedException is an exception thrown when an abstract method is
       called.'''
    pass

class Hmm:
    '''A Hidden Markov Model class

    '''

    def __init__(self, nStates, opdfFactory):
        '''Hmm constructor

        Build a Hidden Markov Model with nStates states, with uniform
        a[][] and pi[] values, using the opdfFactory to build the probability
        distribution functions associated with each state.
        '''

        if nStates <= 0:
            raise "Invalid nStates passed to Hmm constructor"

        self.pi = [1.0 / float(nStates)] * nStates
        self.opdfs = [opdfFactory.produce() for i in range(nStates)]

        self.a = [[1.0 / float(nStates)] * nStates] * nStates


    # Data accessor functions
    def nStates(self):
        return len(self.pi)

    def getPi(self, i):
        return self.pi[i]

    def setPi(self, i, pi):
        self.pi[i] = pi

    def getOpdf(self, state):
        return self.opdfs[state]

    def setOpdf(self, state, opdf):
        self.opdfs[state] = opdf

    def getAij(self, i, j):
        return self.a[i][j]

    def setAij(self, i, j, v):
        self.a[i][j] = v

    def probability(self, oseq):
        '''Given an observation sequence return its probability using the
           Forward algorithm.'''
        return ForwardCalculator(oseq, self).probability()

    def lnprobability(self, oseq):
        '''Given an observation sequence return its Napierian/Natural log
        probability, using the Scaled Forward algorithm (see pp365--368 of
        Rabiner and Juang 'Fundamentals of Speech Recognition').

        Scaling is used to avoid numeric underflow due to the extremely small
        probabilities involved in the calculation.
        '''
        return ForwardScaledCalculator(oseq, self).lnprobability()
        

class ForwardCalculator:
    def __init__(self, oseq, hmm):
        self.compute_alpha(hmm, oseq)
        self.compute_probability(oseq)

    def probability(self):
        return self.prob

    def compute_alpha_init(self, hmm, oseq):
        self.alpha = [[0.0 for i in range(hmm.nStates())]
            for j in range(len(oseq))]
        for i in range(hmm.nStates()):
            self.alpha[0][i] = hmm.getPi(i) * hmm.getOpdf(i).probability(oseq[0])
        #print self.alpha[0]

    def compute_alpha_step(self, hmm, oseq, t, j):
        sum = 0.0
        for i in range(hmm.nStates()):
            sum = sum + self.alpha[t-1][i] * hmm.getAij(i, j)
        self.alpha[t][j] = sum * hmm.getOpdf(j).probability(oseq[t])
        #print (t,j,sum,self.alpha[t])

    def compute_alpha(self, hmm, oseq):
        self.compute_alpha_init(hmm, oseq)

        for t in range(1,len(oseq)):
            for j in range(hmm.nStates()):
                self.compute_alpha_step(hmm, oseq, t, j)

    def compute_probability(self, oseq):
        self.prob = 0.0
        for a in self.alpha[-1]:
            self.prob = self.prob + a
        

class ForwardScaledCalculator(ForwardCalculator):
    def __init__(self, oseq, hmm):
        self.cFactors = [0.] * len(oseq)
        self.compute_alpha(hmm, oseq)
        self.compute_probability(oseq)

    def scale(self, t):
        #sum = 0.0
        sum = 1e-300
        for i in range(len(self.alpha[t])):
            sum = sum + self.alpha[t][i]
        #print sum
        #print self.alpha[t]

        self.cFactors[t] = sum
        for i in range(len(self.alpha[t])):
            self.alpha[t][i] = self.alpha[t][i] / sum
        #print self.alpha[t]
            

    def compute_alpha(self, hmm, oseq):
        self.compute_alpha_init(hmm, oseq)
        self.scale(0)

        for t in range(1,len(oseq)):
            for j in range(hmm.nStates()):
                self.compute_alpha_step(hmm, oseq, t, j)
            self.scale(t)

    def compute_probability(self, oseq):
        self.lnprob = 0.0
        for t in range(len(oseq)):
            self.lnprob = self.lnprob + math.log(self.cFactors[t])

        self.prob = math.exp(self.lnprob)

    def lnprobability(self):
        return self.lnprob



class OpdfFactory:
    '''Abstract factory class for an Observation Probability Distribution
    Function object.'''

    def __init__(self):
        raise UnimplementedException()

    def produce(self):
        '''Create a new observation probability distribution function'''    
        raise UnimplementedException()

class Opdf:
    '''Abstract class implementing a probability distribution function'''
   
    def __init__(self):
        raise UnimplementedException()

    def probability(self, observation):
        '''Given an observation, return its probability'''
        raise UnimplementedException()

# ---------- Integer probability distributions -----------------
class OpdfInteger(Opdf):
    def __init__(self, probabilities):
        self.probabilities = probabilities

    def probability(self, obs):
        return self.probabilities[obs]

    def setProbabilities(self, probs):
        self.probabilities = probs

    def getProbabilities(self):
        return self.probabilites


class OpdfIntegerFactory(OpdfFactory):
    def __init__(self, nEntries):
        self.nEntries = nEntries

    def produce(self):
        return OpdfInteger([1.0 / self.nEntries] * self.nEntries)

# --------- Multi-Gaussian probability distributions -------------

class MultiGaussianDistribution:
    '''A class representing a multi-variable Gaussian probability distribution.

    Such a distribution is characterised by a mean vector and a covariance
    matrix.
    '''

    def __init__(self, dimension, mean = None, covar = None):
        if mean is None:
            mean = array([0.0] * dimension)
        if covar is None:
            covar = array([[0.0] * dimension] * dimension)

        self.dimension = dimension
        self.mean = array([mean])
        self.covar = array(covar)

    def probability(self, obs):
        '''Calculate the probability of an observation vector under this
        probability distribution. This is simply a direct implementation
        of the formula for a multi-variable Gaussian distribution.
        '''
        v = array([obs]) - self.mean
        exparg = matrixmultiply(v,
            matrixmultiply(inverse(self.covar), transpose(v))
        )[0][0] * -0.5

        return (math.exp(exparg) /
            (math.pow(2.0 * math.pi, float(self.dimension) / 2.0) *
             math.pow(determinant(self.covar), 0.5)))
        
    def setCovar(self, covar):
        self.covar = array(covar)

    def setMean(self, mean):
        self.mean = array([mean])

    def setDimension(self, dimension):
        self.dimension = dimension

class OpdfMultiGaussian(Opdf):
    def __init__(self, dimension, mean = None, covar = None):
        self.mg = MultiGaussianDistribution(dimension, mean, covar)

    def probability(self, obs):
        return self.mg.probability(obs)

        
class OpdfMultiGaussianFactory(OpdfFactory):
    def __init__(self, dimension, mean = None, covar = None):
        self.dimension = dimension
        self.mean = mean
        self.covar = covar

    def produce(self):
        return OpdfMultiGaussian(self.dimension, self.mean, self.covar)
