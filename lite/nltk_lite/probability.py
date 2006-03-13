# Natural Language Toolkit: Probability and Statistics
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Trevor Cohn <tacohn@cs.mu.oz.au> (additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes for representing and processing probabilistic information.

The L{FreqDist} class is used to encode X{frequency distributions},
which count the number of times that each outcome of an experiment
occurs.

The L{ProbDistI} class defines a standard interface for X{probability
distributions}, which encode the probability of each outcome for an
experiment.  There are two types of probability distribution:

  - X{derived probability distributions} are created from frequency
    distributions.  They attempt to model the probability distribution
    that generated the frequency distribution.
  - X{analytic probability distributions} are created directly from
    parameters (such as variance).

The L{ConditionalFreqDist} class and L{ConditionalProbDistI} interface
are used to encode conditional distributions.  Conditional probability
distributions can be derived or analytic; but currently the only
implementation of the C{ConditionalProbDistI} interface is
L{ConditionalProbDist}, a derived distribution.

"""

import types, math, numarray

##//////////////////////////////////////////////////////
##  Frequency Distributions
##//////////////////////////////////////////////////////

class FreqDist(object):
    """
    A frequency distribution for the outcomes of an experiment.  A
    frequency distribution records the number of times each outcome of
    an experiment has occured.  For example, a frequency distribution
    could be used to record the frequency of each word type in a
    document.  Formally, a frequency distribution can be defined as a
    function mapping from each sample to the number of times that
    sample occured as an outcome.

    Frequency distributions are generally constructed by running a
    number of experiments, and incrementing the count for a sample
    every time it is an outcome of an experiment.  For example, the
    following code will produce a frequency distribution that encodes
    how often each word occurs in a text:
    
        >>> fdist = FreqDist()
        >>> for word in tokenize.whitespace(sent):
        ...    fdist.inc(word)
    """
    def __init__(self):
        """
        Construct a new empty, C{FreqDist}.  In particular, the count
        for every sample is zero.
        """
        self._count = {}
        self._N = 0
        self._Nr_cache = None
        self._max_cache = None

    def inc(self, sample, count=1):
        """
        Increment this C{FreqDist}'s count for the given
        sample.
        
        @param sample: The sample whose count should be incremented.
        @type sample: any
        @param count: The amount to increment the sample's count by.
        @type count: C{int}
        @rtype: None
        @raise NotImplementedError: If C{sample} is not a
               supported sample type.
        """
        if count == 0: return
        
        self._N += count
        self._count[sample] = self._count.get(sample,0) + count

        # Invalidate the Nr cache and max cache.
        self._Nr_cache = None
        self._max_cache = None

    def N(self):
        """
        @return: The total number of sample outcomes that have been
          recorded by this C{FreqDist}.  For the number of unique 
          sample values (or bins) with counts greater than zero, use
          C{FreqDist.B()}.
        @rtype: C{int}
        """
        return self._N

    def B(self):
        """
        @return: The total number of sample values (or X{bins}) that
            have counts greater than zero.  For the total
            number of sample outcomes recorded, use C{FreqDist.N()}.
        @rtype: C{int}
        """
        return len(self._count)

    def samples(self):
        """
        @return: A list of all samples that have been recorded as
            outcomes by this frequency distribution.  Use C{count()}
            to determine the count for each sample.
        @rtype: C{list}
        """
        return self._count.keys()

    def Nr(self, r, bins=None):
        """
        @return: The number of samples with count r.
        @rtype: C{int}
        @type r: C{int}
        @param r: A sample count.
        @type bins: C{int}
        @param bins: The number of possible sample outcomes.  C{bins}
            is used to calculate Nr(0).  In particular, Nr(0) is
            C{bins-self.B()}.  If C{bins} is not specified, it
            defaults to C{self.B()} (so Nr(0) will be 0).
        """
        if r < 0: raise IndexError, 'FreqDist.Nr(): r must be non-negative'
        
        # Special case for Nr(0):
        if r == 0:
            if bins is None: return 0
            else: return bins-self.B()
        
        # We have to search the entire distribution to find Nr.  Since
        # this is an expensive operation, and is likely to be used
        # repeatedly, cache the results.
        if self._Nr_cache is None:
            self._cache_Nr_values()
            
        if r >= len(self._Nr_cache): return 0
        return self._Nr_cache[r]

    def _cache_Nr_values(self):
        Nr = [0]
        for sample in self.samples():
            c = self._count.get(sample, 0)
            if c >= len(Nr):
                Nr += [0]*(c+1-len(Nr))
            Nr[c] += 1
        self._Nr_cache = Nr

    def count(self, sample):
        """
        Return the count of a given sample.  The count of a sample is
        defined as the number of times that sample outcome was
        recorded by this C{FreqDist}.  Counts are non-negative
        integers.
        
        @return: The count of a given sample.
        @rtype: C{int}
        @param sample: the sample whose count
               should be returned.
        @type sample: any.
        """
        return self._count.get(sample, 0)

    def freq(self, sample):
        """
        Return the frequency of a given sample.  The frequency of a
        sample is defined as the count of that sample divided by the
        total number of sample outcomes that have been recorded by
        this C{FreqDist}.  The count of a sample is defined as the
        number of times that sample outcome was recorded by this
        C{FreqDist}.  Frequencies are always real numbers in the range
        [0, 1].
        
        @return: The frequency of a given sample.
        @rtype: float
        @param sample: the sample whose frequency
               should be returned.
        @type sample: any
        """
        if self._N is 0: return 0
        return float(self._count.get(sample, 0)) / self._N

    def max(self):
        """
        Return the sample with the greatest number of outcomes in this
        frequency distribution.  If two or more samples have the same
        number of outcomes, return one of them; which sample is
        returned is undefined.  If no outcomes have occured in this
        frequency distribution, return C{None}.

        @return: The sample with the maximum number of outcomes in this
                frequency distribution.
        @rtype: any or C{None}
        """
        if self._max_cache is None:
            best_sample = None
            best_count = -1
            for sample in self._count.keys():
                if self._count[sample] > best_count:
                    best_sample = sample
                    best_count = self._count[sample]
            self._max_cache = best_sample
        return self._max_cache

    def sorted_samples(self):
        """
        Return the samples sorted in decreasing order of frequency.  Instances
        with the same count will be arbitrarily ordered.  Instances with a
        count of zero will be omitted. This method is C{O(N^2)}, where C{N} is
        the number of samples, but will complete in a shorter time on average.

        @return: The set of samples in sorted order.
        @rtype: sequence of any
        """
        items = [(-count,sample) for (sample,count) in self._count.items()]
        items.sort()
        return [sample for (neg_count,sample) in items]

    def __repr__(self):
        """
        @return: A string representation of this C{FreqDist}.
        @rtype: string
        """
        return '<FreqDist with %d samples>' % self.N()
    
    def __str__(self):
        """
        @return: A string representation of this C{FreqDist}.
        @rtype: string
        """
        samples = self.sorted_samples()
        items = ['%r: %r' % (s, self._count[s]) for s in samples]
        return '<FreqDist: %s>' % ', '.join(items)

    def __contains__(self, sample):
        """
        @return: True if the given sample occurs one or more times in
            this frequency distribution.
        @rtype: C{boolean}
        @param sample: The sample to search for.
        @type sample: any
        """
        return self._count.has_key(sample)

##//////////////////////////////////////////////////////
##  Probability Distributions
##//////////////////////////////////////////////////////

class ProbDistI(object):
    """
    A probability distribution for the outcomes of an experiment.  A
    probability distribution specifies how likely it is that an
    experiment will have any given outcome.  For example, a
    probability distribution could be used to predict the probability
    that a token in a document will have a given type.  Formally, a
    probability distribution can be defined as a function mapping from
    samples to nonnegative real numbers, such that the sum of every
    number in the function's range is 1.0.  C{ProbDist}s are often
    used to model the probability distribution of the experiment used
    to generate a frequency distribution.
    """
    def __init__(self):
        if self.__class__ == ProbDistI:
            raise AssertionError, "Interfaces can't be instantiated"
        
    def prob(self, sample):
        """
        @return: the probability for a given sample.  Probabilities
            are always real numbers in the range [0, 1].
        @rtype: float
        @param sample: The sample whose probability
               should be returned.
        @type sample: any
        """
        raise AssertionError()

    def logprob(self, sample):
        """
        @return: the natural logarithm of the probability for a given
            sample.  Log probabilities range from negitive infinity to
            zero.
        @rtype: float
        @param sample: The sample whose probability
               should be returned.
        @type sample: any
        """
        # Default definition, in terms of prob()
        p = self.prob(sample)
        if p == 0:
            # Use some approximation to infinity.  What this does
            # depends on your system's float implementation.
            return -1e1000
        else:
            return math.log(p)

    def max(self):
        """
        @return: the sample with the greatest probability.  If two or
            more samples have the same probability, return one of them;
            which sample is returned is undefined.
        @rtype: any
        """
        raise AssertionError()
    
    def samples(self):
        """
        @return: A list of all samples that have nonzero
            probabilities.  Use C{prob} to find the probability of
            each sample.
        @rtype: C{list}
        """
        raise AssertionError()

class UniformProbDist(ProbDistI):
    """
    A probability distribution that assigns equal probability to each
    sample in a given set; and a zero probability to all other
    samples.
    """
    def __init__(self, samples):
        """
        Construct a new uniform probability distribution, that assigns
        equal probability to each sample in C{samples}.

        @param samples: The samples that should be given uniform
            probability.
        @type samples: C{list}
        @raise ValueError: If C{samples} is empty.
        """
        if len(samples) == 0:
            raise ValueError('A Uniform probability distribution must '+
                             'have at least one sample.')
        self._sampleset = set(samples)
        self._prob = 1.0/len(self._sampleset)
        self._samples = list(self._sampleset)

    def prob(self, sample):
        if sample in self._sampleset: return self._prob
        else: return 0
    def max(self): return self._samples[0]
    def samples(self): return self._samples
    def __repr__(self):
        return '<UniformProbDist with %d samples>' % len(self._sampleset)

class DictionaryProbDist(ProbDistI):
    """
    A probability distribution whose probabilities are directly
    specified by a given dictionary.  The given dictionary maps
    samples to probabilities.
    """
    def __init__(self, prob_dict=None, log=False, normalize=False):
        """
        Construct a new probability distribution from the given
        dictionary, which maps values to probabilities (or to log
        probabilities, if C{log} is true).  If C{normalize} is
        true, then the probability values are scaled by a constant
        factor such that they sum to 1.
        """
        self._prob_dict = prob_dict.copy()
        self._log = log

        # Normalize the distribution, if requested.
        if normalize:
            if log:
                value_sum = sum_logs(self._prob_dict.values())
                if value_sum <= -1e1000:
                    logp = math.log(1.0/len(prob_dict.keys()))
                    for x in prob_dict.keys():
                        self._prob_dict[x] = logp
                else:
                    for (x, p) in self._prob_dict.items():
                        self._prob_dict[x] -= value_sum
            else:
                value_sum = sum(self._prob_dict.values())
                if value_sum == 0:
                    p = 1.0/len(prob_dict.keys())
                    for x in prob_dict.keys():
                        self._prob_dict[x] = p
                else:
                    norm_factor = 1.0/value_sum
                    for (x, p) in self._prob_dict.items():
                        self._prob_dict[x] *= norm_factor
                    
    def prob(self, sample):
        if self._log:
            if sample not in self._prob_dict: return 0
            else: return math.exp(self._prob_dict[sample])
        else:
            return self._prob_dict.get(sample, 0)

    def logprob(self, sample):
        if self._log:
            return self._prob_dict.get(sample, 1e-1000)
        else:
            if sample not in self._prob_dict: return 1e-1000
            else: return math.log(self._prob_dict[sample])

    def max(self):
        if not hasattr(self, '_max'):
            self._max = max([(p,v) for (v,p) in self._prob_dict.items()])[1]
        return self._max
    def samples(self):
        return self._prob_dict.keys()
    def __repr__(self):
        return '<ProbDist with %d samples>' % len(self._prob_dict)
        
class MLEProbDist(ProbDistI):
    """
    The maximum likelihood estimate for the probability distribution
    of the experiment used to generate a frequency distribution.  The
    X{maximum likelihood estimate} approximates the probability of
    each sample as the frequency of that sample in the frequency
    distribution.
    """
    def __init__(self, freqdist):
        """
        Use the maximum likelihood estimate to create a probability
        distribution for the experiment used to generate C{freqdist}.

        @type freqdist: C{FreqDist}
        @param freqdist: The frequency distribution that the
            probability estimates should be based on.
        """
        if freqdist.N() == 0:
            raise ValueError('An MLE probability distribution must '+
                             'have at least one sample.')
        
        self._freqdist = freqdist
        
    def freqdist(self):
        """
        @return: The frequency distribution that this probability
            distribution is based on.
        @rtype: C{FreqDist}
        """        
        return self._freqdist
    
    def prob(self, sample):
        return self._freqdist.freq(sample)
    
    def max(self):
        return self._freqdist.max()
    
    def samples(self):
        return self._freqdist.samples()
    
    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<MLEProbDist based on %d samples>' % self._freqdist.N()

class LidstoneProbDist(ProbDistI):
    """
    The Lidstone estimate for the probability distribution of the
    experiment used to generate a frequency distribution.  The
    C{Lidstone estimate} is paramaterized by a real number M{gamma},
    which typically ranges from 0 to 1.  The X{Lidstone estimate}
    approximates the probability of a sample with count M{c} from an
    experiment with M{N} outcomes and M{B} bins as
    M{(c+gamma)/(N+B*gamma)}.  This is equivalant to adding
    M{gamma} to the count for each bin, and taking the maximum
    likelihood estimate of the resulting frequency distribution.
    """
    def __init__(self, freqdist, gamma, bins=None):
        """
        Use the Lidstone estimate to create a probability distribution
        for the experiment used to generate C{freqdist}.

        @type freqdist: C{FreqDist}
        @param freqdist: The frequency distribution that the
            probability estimates should be based on.
        @type gamma: C{float}
        @param gamma: A real number used to paramaterize the
            estimate.  The Lidstone estimate is equivalant to adding
            M{gamma} to the count for each bin, and taking the
            maximum likelihood estimate of the resulting frequency
            distribution.
        @type bins: C{int}
        @param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            C{bins} is not specified, it defaults to C{freqdist.B()}.
        """
        if (bins == 0) or (bins is None and freqdist.N() == 0):
            name = self.__class__.__name__[:-8]
            raise ValueError('A %s probability distribution ' % name +
                             'must have at least one bin.')
        if (bins is not None) and (bins < freqdist.B()):
            name = self.__class__.__name__[:-8]
            raise ValueError('\nThe number of bins in a %s must be ' % name +
                             'greater than or equal to\nthe number of '+
                             'bins in the FreqDist used to create it.')
        
        self._freqdist = freqdist
        self._gamma = float(gamma)
        self._N = self._freqdist.N()

        if bins is None: bins = freqdist.B()
        self._bins = bins
        
    def freqdist(self):
        """
        @return: The frequency distribution that this probability
            distribution is based on.
        @rtype: C{FreqDist}
        """        
        return self._freqdist
    
    def prob(self, sample):
        c = self._freqdist.count(sample)
        return (c + self._gamma) / (self._N + self._bins * self._gamma)
    
    def max(self):
        # For Lidstone distributions, probability is monotonic with
        # frequency, so the most probable sample is the one that
        # occurs most frequently.
        return self._freqdist.max()
    
    def samples(self):
        return self._freqdist.samples()

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<LidstoneProbDist based on %d samples>' % self._freqdist.N()

class LaplaceProbDist(LidstoneProbDist):
    """
    The Laplace estimate for the probability distribution of the
    experiment used to generate a frequency distribution.  The
    X{Lidstone estimate} approximates the probability of a sample with
    count M{c} from an experiment with M{N} outcomes and M{B} bins as
    M{(c+1)/(N+B)}.  This is equivalant to adding one to the count for
    each bin, and taking the maximum likelihood estimate of the
    resulting frequency distribution.
    """    
    def __init__(self, freqdist, bins=None):
        """
        Use the Laplace estimate to create a probability distribution
        for the experiment used to generate C{freqdist}.

        @type freqdist: C{FreqDist}
        @param freqdist: The frequency distribution that the
            probability estimates should be based on.
        @type bins: C{int}
        @param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            C{bins} is not specified, it defaults to C{freqdist.B()}.
        """
        LidstoneProbDist.__init__(self, freqdist, 1, bins)
        
    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<LaplaceProbDist based on %d samples>' % self._freqdist.N()
        
class ELEProbDist(LidstoneProbDist):
    """
    The expected likelihood estimate for the probability distribution
    of the experiment used to generate a frequency distribution.  The
    X{expected likelihood estimate} approximates the probability of a
    sample with count M{c} from an experiment with M{N} outcomes and
    M{B} bins as M{(c+0.5)/(N+B/2)}.  This is equivalant to adding 0.5
    to the count for each bin, and taking the maximum likelihood
    estimate of the resulting frequency distribution.
    """    
    def __init__(self, freqdist, bins=None):
        """
        Use the expected likelihood estimate to create a probability
        distribution for the experiment used to generate C{freqdist}.

        @type freqdist: C{FreqDist}
        @param freqdist: The frequency distribution that the
            probability estimates should be based on.
        @type bins: C{int}
        @param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            C{bins} is not specified, it defaults to C{freqdist.B()}.
        """
        LidstoneProbDist.__init__(self, freqdist, 0.5, bins)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<ELEProbDist based on %d samples>' % self._freqdist.N()

class HeldoutProbDist(ProbDistI):
    """
    The heldout estimate for the probability distribution of the
    experiment used to generate two frequency distributions.  These
    two frequency distributions are called the "heldout frequency
    distribution" and the "base frequency distribution."  The
    X{heldout estimate} uses uses the X{heldout frequency
    distribution} to predict the probability of each sample, given its
    frequency in the X{base frequency distribution}.

    In particular, the heldout estimate approximates the probability
    for a sample that occurs M{r} times in the base distribution as
    the average frequency in the heldout distribution of all samples
    that occur M{r} times in the base distribution.

    This average frequency is M{Tr[r]/(Nr[r]*N)}, where:
        - M{Tr[r]} is the total count in the heldout distribution for
          all samples that occur M{r} times in the base
          distribution. 
        - M{Nr[r]} is the number of samples that occur M{r} times in
          the base distribution.
        - M{N} is the number of outcomes recorded by the heldout
          frequency distribution. 

    In order to increase the efficiency of the C{prob} member
    function, M{Tr[r]/(Nr[r]*N)} is precomputed for each value of M{r}
    when the C{HeldoutProbDist} is created.

    @type _estimate: C{list} of C{float}
    @ivar _estimate: A list mapping from M{r}, the number of
        times that a sample occurs in the base distribution, to the
        probability estimate for that sample.  C{_estimate[M{r}]} is
        calculated by finding the average frequency in the heldout
        distribution of all samples that occur M{r} times in the base
        distribution.  In particular, C{_estimate[M{r}]} =
        M{Tr[r]/(Nr[r]*N)}.
    @type _max_r: C{int}
    @ivar _max_r: The maximum number of times that any sample occurs
       in the base distribution.  C{_max_r} is used to decide how
       large C{_estimate} must be.
    """
    def __init__(self, base_fdist, heldout_fdist, bins=None):
        """
        Use the heldout estimate to create a probability distribution
        for the experiment used to generate C{base_fdist} and
        C{heldout_fdist}.

        @type base_fdist: C{FreqDist}
        @param base_fdist: The base frequency distribution.
        @type heldout_fdist: C{FreqDist}
        @param heldout_fdist: The heldout frequency distribution.
        @type bins: C{int}
        @param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            C{bins} is not specified, it defaults to C{freqdist.B()}.
        """
        
        self._base_fdist = base_fdist
        self._heldout_fdist = heldout_fdist

        # The max number of times any sample occurs in base_fdist.
        self._max_r = base_fdist.count(base_fdist.max())

        # Calculate Tr, Nr, and N.
        Tr = self._calculate_Tr()
        Nr = [base_fdist.Nr(r, bins) for r in range(self._max_r+1)]
        N = heldout_fdist.N()

        # Use Tr, Nr, and N to compute the probability estimate for
        # each value of r.
        self._estimate = self._calculate_estimate(Tr, Nr, N)

    def _calculate_Tr(self):
        """
        @return: the list M{Tr}, where M{Tr[r]} is the total count in
            C{heldout_fdist} for all samples that occur M{r}
            times in C{base_fdist}.
        @rtype: C{list} of C{float}
        """
        Tr = [0.0] * (self._max_r+1)
        for sample in self._heldout_fdist.samples():
            r = self._base_fdist.count(sample)
            Tr[r] += self._heldout_fdist.count(sample)
        return Tr

    def _calculate_estimate(self, Tr, Nr, N):
        """
        @return: the list M{estimate}, where M{estimate[r]} is the
            probability estimate for any sample that occurs M{r} times
            in the base frequency distribution.  In particular,
            M{estimate[r]} is M{Tr[r]/(N[r]*N)}.  In the special case
            that M{N[r]=0}, M{estimate[r]} will never be used; so we
            define M{estimate[r]=None} for those cases.
        @rtype: C{list} of C{float}
        @type Tr: C{list} of C{float}
        @param Tr: the list M{Tr}, where M{Tr[r]} is the total count in
            the heldout distribution for all samples that occur M{r}
            times in base distribution.
        @type Nr: C{list} of C{float}
        @param Nr: The list M{Nr}, where M{Nr[r]} is the number of
            samples that occur M{r} times in the base distribution.
        @type N: C{int}
        @param N: The total number of outcomes recorded by the heldout
            frequency distribution. 
        """
        estimate = []
        for r in range(self._max_r+1):
            if Nr[r] == 0: estimate.append(None)
            else: estimate.append(Tr[r]/(Nr[r]*N))
        return estimate

    def base_fdist(self):
        """
        @return: The base frequency distribution that this probability
            distribution is based on.
        @rtype: C{FreqDist}
        """        
        return self._base_fdist
    
    def heldout_fdist(self):
        """
        @return: The heldout frequency distribution that this
            probability distribution is based on.
        @rtype: C{FreqDist}
        """        
        return self._heldout_fdist
    
    def prob(self, sample):
        # Use our precomputed probability estimate.
        r = self._base_fdist.count(sample)
        return self._estimate[r]

    def max(self):
        # Note: the Heldout estimation is *not* necessarily monotonic;
        # so this implementation is currently broken.  However, it
        # should give the right answer *most* of the time. :)
        return self._base_fdist.max()

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        s = '<HeldoutProbDist: %d base samples; %d heldout samples>'
        return s % (self._base_fdist.N(), self._heldout_fdist.N())

class CrossValidationProbDist(ProbDistI):
    """
    The cross-validation estimate for the probability distribution of
    the experiment used to generate a set of frequency distribution.
    The X{cross-validation estimate} for the probability of a sample
    is found by averaging the held-out estimates for the sample in
    each pair of frequency distributions.
    """
    def __init__(self, freqdists, bins):
        """
        Use the cross-validation estimate to create a probability
        distribution for the experiment used to generate
        C{freqdists}.

        @type freqdists: C{list} of C{FreqDist}
        @param freqdists: A list of the frequency distributions
            generated by the experiment.
        @type bins: C{int}
        @param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            C{bins} is not specified, it defaults to C{freqdist.B()}.
        """
        self._freqdists = freqdists

        # Create a heldout probability distribution for each pair of
        # frequency distributions in freqdists.
        self._heldout_probdists = []
        for fdist1 in freqdists:
            for fdist2 in freqdists:
                if fdist1 is not fdist2:
                    probdist = HeldoutProbDist(fdist1, fdist2, bins)
                    self._heldout_probdists.append(probdist)

    def freqdists(self):
        """
        @rtype: C{list} of C{FreqDist}
        @return: The list of frequency distributions that this
            C{ProbDist} is based on.
        """
        return self._freqdists

    def prob(self, sample):
        # Find the average probability estimate returned by each
        # heldout distribution.
        prob = 0.0
        for heldout_probdist in self._heldout_probdists:
            prob += heldout_probdist.prob(sample)
        return prob/len(self._heldout_probdists)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<CrossValidationProbDist: %d-way>' % len(self._freqdists)

class WittenBellProbDist(ProbDistI):
    """
    The Witten-Bell estimate of a probability distribution. This distribution
    allocates uniform probability mass to as yet unseen events by using the
    number of events that have only been seen once. The probability mass
    reserved for unseen events is equal to:

        - M{T / (N + T)}

    where M{T} is the number of observed event types and M{N} is the total
    number of observed events. This equates to the maximum likelihood estimate
    of a new type event occuring. The remaining probability mass is discounted
    such that all probability estimates sum to one, yielding:

        - M{p = T / Z (N + T)}, if count = 0
        - M{p = c / (N + T)}, otherwise
    """

    def __init__(self, freqdist, bins=None):
        """
        Creates a distribution of Witten-Bell probability estimates.  This
        distribution allocates uniform probability mass to as yet unseen
        events by using the number of events that have only been seen once.
        The probability mass reserved for unseen events is equal to:

            - M{T / (N + T)}

        where M{T} is the number of observed event types and M{N} is the total
        number of observed events. This equates to the maximum likelihood
        estimate of a new type event occuring. The remaining probability mass
        is discounted such that all probability estimates sum to one,
        yielding:

            - M{p = T / Z (N + T)}, if count = 0
            - M{p = c / (N + T)}, otherwise

        The parameters M{T} and M{N} are taken from the C{freqdist} parameter
        (the C{B()} and C{N()} values). The normalising factor M{Z} is
        calculated using these values along with the C{bins} parameter.

        @param freqdist:    The frequency counts upon which to base the
                            estimation.
        @type  freqdist:    C{FreqDist}
        @param bins:        The number of possible event types. This must be
                            at least as large as the number of bins in the
                            C{freqdist}. If C{None}, then it's assumed to be
                            equal to that of the C{freqdist}
        @type  bins:        C{Int}
        """
        assert bins == None or bins >= freqdist.B(),\
            'Bins parameter must not be less than freqdist.B()'
        if bins == None:
            bins = freqdist.B()
        self._freqdist = freqdist
        self._T = self._freqdist.B()
        self._Z = bins - self._freqdist.B()
        self._N = self._freqdist.N()

    def prob(self, sample):
        # inherit docs from ProbDistI
        c = self._freqdist.count(sample)
        if c == 0:
            return self._T / float(self._Z * (self._N + self._T))
        else:
            return c / float(self._N + self._T)

    def max(self):
        return self._freqdist.max()
    
    def samples(self):
        return self._freqdist.samples()

    def freqdist(self):
        return self._freqdist

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<WittenBellProbDist based on %d samples>' % self._freqdist.N()

class GoodTuringProbDist(ProbDistI):
    """
    The Good-Turing estimate of a probability distribution. This method
    calculates the probability mass to assign to events with zero or low
    counts based on the number of events with higher counts. It does so by
    using the smoothed count M{c*}:

        - M{c* = (c + 1) N(c + 1) / N(c)}

    where M{c} is the original count, M{N(i)} is the number of event types
    observed with count M{i}. These smoothed counts are then normalised to
    yield a probability distribution.
    """
    # TODO - add a cut-off parameter, above which the counts are unmodified
    # (see J&M p216)

    def __init__(self, freqdist, bins):
        """
        Creates a Good-Turing probability distribution estimate.  This method
        calculates the probability mass to assign to events with zero or low
        counts based on the number of events with higher counts. It does so by
        using the smoothed count M{c*}:

            - M{c* = (c + 1) N(c + 1) / N(c)}

        where M{c} is the original count, M{N(i)} is the number of event types
        observed with count M{i}. These smoothed counts are then normalised to
        yield a probability distribution.

        The C{bins} parameter allows C{N(0)} to be estimated.

        @param freqdist:    The frequency counts upon which to base the
                            estimation.
        @type  freqdist:    C{FreqDist}
        @param bins:        The number of possible event types. This must be
                            at least as large as the number of bins in the
                            C{freqdist}. If C{None}, then it's taken to be
                            equal to C{freqdist.B()}.
        @type  bins:        C{Int}
        """
        assert bins == None or bins >= freqdist.B(),\
            'Bins parameter must not be less than freqdist.B()'
        if bins == None:
            bins = freqdist.B()
        self._freqdist = freqdist
        self._bins = bins

    def prob(self, sample):
        # inherit docs from FreqDist
        c = self._freqdist.count(sample)
        nc = self._freqdist.Nr(c, self._bins)
        ncn = self._freqdist.Nr(c + 1, self._bins)
        return float(c + 1) * ncn / (nc * self._freqdist.N())

    def max(self):
        return self._freqdist.max()
    
    def samples(self):
        return self._freqdist.samples()

    def freqdist(self):
        return self._freqdist

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ProbDist}.
        """
        return '<GoodTuringProbDist based on %d samples>' % self._freqdist.N()

class MutableProbDist(ProbDistI):
    """
    An mutable probdist where the probabilities may be easily modified. This
    simply copies an existing probdist, storing the probability values in a
    mutable dictionary and providing an update method.
    """

    def __init__(self, prob_dist, samples, store_logs=True):
        """
        Creates the mutable probdist based on the given prob_dist and using
        the list of samples given. These values are stored as log
        probabilities if the store_logs flag is set.

        @param prob_dist: the distribution from which to garner the
            probabilities
        @type prob_dist: ProbDist
        @param samples: the complete set of samples
        @type samples: sequence of any
        @param store_logs: whether to store the probabilities as logarithms
        @type store_logs: bool
        """
        self._samples = samples
        self._sample_dict = dict([(samples[i], i) for i in range(len(samples))])
        self._data = numarray.zeros(len(samples), numarray.Float64)
        for i in range(len(samples)):
            if store_logs:
                self._data[i] = prob_dist.logprob(samples[i])
            else:
                self._data[i] = prob_dist.prob(samples[i])
        self._logs = store_logs

    def samples(self):
        # inherit documentation
        return self._samples

    def prob(self, sample):
        # inherit documentation
        i = self._sample_dict.get(sample)
        if i != None:
            if self._logs:
                return exp(self._data[i])
            else:
                return self._data[i]
        else:
            return 0.0

    def logprob(self, sample):
        # inherit documentation
        i = self._sample_dict.get(sample)
        if i != None:
            if self._logs:
                return self._data[i]
            else:
                return log(self._data[i])
        else:
            return float('-inf')

    def update(self, sample, prob, log=True):
        """
        Update the probability for the given sample. This may cause the object
        to stop being the valid probability distribution - the user must
        ensure that they update the sample probabilities such that all samples
        have probabilities between 0 and 1 and that all probabilities sum to
        one.

        @param sample: the sample for which to update the probability
        @type sample: C{any}
        @param prob: the new probability
        @type prob: C{float}
        @param log: is the probability already logged
        @type log: C{bool}
        """
        i = self._sample_dict.get(sample)
        assert i != None
        if self._logs:
            if log: self._data[i] = prob
            else:   self._data[i] = log(prob)
        else:
            if log: self._data[i] = exp(prob)
            else:   self._data[i] = prob

##//////////////////////////////////////////////////////
##  Probability Distribution Operations
##//////////////////////////////////////////////////////

def log_likelihood(test_pdist, actual_pdist):
    # Is this right?
    return sum([actual_pdist.prob(s) * math.log(test_pdist.prob(s))
                for s in actual_pdist.samples()])

##//////////////////////////////////////////////////////
##  Conditional Distributions
##//////////////////////////////////////////////////////

class ConditionalFreqDist(object):
    """
    A collection of frequency distributions for a single experiment
    run under different conditions.  Conditional frequency
    distributions are used to record the number of times each sample
    occured, given the condition under which the experiment was run.
    For example, a conditional frequency distribution could be used to
    record the frequency of each word type in a document, given the
    length of the word type.  Formally, a conditional frequency
    distribution can be defined as a function that maps from each
    condition to the C{FreqDist} for the experiment under that
    condition.

    The frequency distribution for each condition is accessed using
    the indexing operator:

        >>> cfdist[3]
        <FreqDist with 73 outcomes>
        >>> cfdist[3].freq('the')
        0.4
        >>> cfdist[3].count('dog')
        2

    When the indexing operator is used to access the frequency
    distribution for a condition that has not been accessed before,
    C{ConditionalFreqDist} creates a new empty C{FreqDist} for that
    condition.

    Conditional frequency distributions are typically constructed by
    repeatedly running an experiment under a variety of conditions,
    and incrementing the sample outcome counts for the appropriate
    conditions.  For example, the following code will produce a
    conditional frequency distribution that encodes how often each
    word type occurs, given the length of that word type:

        >>> cfdist = ConditionalFreqDist()
        >>> for word in tokenize.whitespace(sent):
        ...     condition = len(word)
        ...     cfdist[condition].inc(word)
    """
    def __init__(self):
        """
        Construct a new empty conditional frequency distribution.  In
        particular, the count for every sample, under every condition,
        is zero.
        """
        self._fdists = {}

    def __getitem__(self, condition):
        """
        Return the frequency distribution that encodes the frequency
        of each sample outcome, given that the experiment was run
        under the given condition.  If the frequency distribution for
        the given condition has not been accessed before, then this
        will create a new empty C{FreqDist} for that condition.
        
        @return: The frequency distribution that encodes the frequency
            of each sample outcome, given that the experiment was run
            under the given condition.
        @rtype: C{FreqDist}

        @param condition: The condition under which the experiment was
            run.
        @type condition: any
        """
        # Create the conditioned freq dist, if it doesn't exist
        if not self._fdists.has_key(condition):
            self._fdists[condition] = FreqDist()
            
        return self._fdists[condition]

    def conditions(self):
        """
        @return: A list of the conditions that have been accessed for
            this C{ConditionalFreqDist}.  Use the indexing operator to
            access the frequency distribution for a given condition.
            Note that the frequency distributions for some conditions
            may contain zero sample outcomes.
        @rtype: C{list}
        """
        return self._fdists.keys()

    def __repr__(self):
        """
        @return: A string representation of this
            C{ConditionalFreqDist}.
        @rtype: C{string}
        """
        n = len(self._fdists)
        return '<ConditionalFreqDist with %d conditions>' % n

class ConditionalProbDistI(object):
    """
    A collection of probability distributions for a single experiment
    run under different conditions.  Conditional probability
    distributions are used to estimate the likelihood of each sample,
    given the condition under which the experiment was run.  For
    example, a conditional probability distribution could be used to
    estimate the probability of each word type in a document, given
    the length of the word type.  Formally, a conditional probability
    distribution can be defined as a function that maps from each
    condition to the C{ProbDist} for the experiment under that
    condition.
    """
    def __init__(self):
        raise AssertionError, 'ConditionalProbDistI is an interface'
    
    def __getitem__(self, condition):
        """
        @return: The probability distribution for the experiment run
            under the given condition.
        @rtype: C{ProbDistI}
        @param condition: The condition whose probability distribution
            should be returned.
        @type condition: any
        """
        raise AssertionError

    def conditions(self):
        """
        @return: A list of the conditions that are represented by
            this C{ConditionalProbDist}.  Use the indexing operator to
            access the probability distribution for a given condition.
        @rtype: C{list}
        """
        raise AssertionError

# For now, this is the only implementation of ConditionalProbDistI;
# but we would want a different implementation if we wanted to build a
# conditional probability distribution analytically (e.g., a gaussian
# distribution), rather than basing it on an underlying frequency
# distribution.
class ConditionalProbDist(ConditionalProbDistI):
    """
    A conditional probability distribution modelling the experiments
    that were used to generate a conditional frequency distribution.
    A C{ConditoinalProbDist} is constructed from a
    C{ConditionalFreqDist} and a X{C{ProbDist} factory}:

      - The B{C{ConditionalFreqDist}} specifies the frequency
        distribution for each condition.
      - The B{C{ProbDist} factory} is a function that takes a
        condition's frequency distribution, and returns its
        probability distribution.  A C{ProbDist} class's name (such as
        C{MLEProbDist} or C{HeldoutProbDist}) can be used to specify
        that class's constructor.

    The first argument to the C{ProbDist} factory is the frequency
    distribution that it should model; and the remaining arguments are
    specified by the C{factory_args} parameter to the
    C{ConditionalProbDist} constructor.  For example, the following
    code constructs a C{ConditionalProbDist}, where the probability
    distribution for each condition is an C{ELEProbDist} with 10 bins:

        >>> cpdist = ConditionalProbDist(cfdist, ELEProbDist, 10)
        >>> print cpdist['run'].max()
        'NN'
        >>> print cpdist['run'].prob('NN')
        0.0813
    """
    def __init__(self, cfdist, probdist_factory,
                 supply_condition=False, *factory_args):
        """
        Construct a new conditional probability distribution, based on
        the given conditional frequency distribution and C{ProbDist}
        factory.

        @type cfdist: L{ConditionalFreqDist}
        @param cfdist: The C{ConditionalFreqDist} specifying the
            frequency distribution for each condition.
        @type probdist_factory: C{class} or C{function}
        @param probdist_factory: The function or class that maps
            a condition's frequency distribution to its probability
            distribution.  The function is called with the frequency
            distribution as its first argument, the condition as its
            second argument (only if C{supply_condition=True}), and
            C{factory_args} as its remaining arguments.
        @type supply_condition: C{bool}
        @param supply_condition: If true, then pass the condition as
            the second argument to C{probdist_factory}.
        @type factory_args: (any)
        @param factory_args: Extra arguments for C{probdist_factory}.
            These arguments are usually used to specify extra
            properties for the probability distributions of individual
            conditions, such as the number of bins they contain.
        """
        self._probdist_factory = probdist_factory
        self._cfdist = cfdist
        self._supply_condition = supply_condition
        self._factory_args = factory_args
        
        self._pdists = {}
        for c in cfdist.conditions():
            if supply_condition:
                pdist = probdist_factory(cfdist[c], c, *factory_args)
            else:
                pdist = probdist_factory(cfdist[c], *factory_args)
            self._pdists[c] = pdist

    def __getitem__(self, condition):
        if not self._pdists.has_key(condition):
            # If it's a condition we haven't seen, create a new prob
            # dist from the empty freq dist.  Typically, this will
            # give a uniform prob dist.
            pdist = self._probdist_factory(FreqDist(), *self._factory_args)
            self._pdists[condition] = pdist
            
        return self._pdists[condition]

    def conditions(self):
        return self._pdists.keys()

    def __repr__(self):
        """
        @return: A string representation of this
            C{ConditionalProbDist}.
        @rtype: C{string}
        """
        n = len(self._pdists)
        return '<ConditionalProbDist with %d conditions>' % n

class DictionaryConditionalProbDist(ConditionalProbDistI):
    """
    An alternative ConditionalProbDist that simply wraps a dictionary of
    ProbDists rather than creating these from FreqDists.
    """

    def __init__(self, probdist_dict):
        """
        @param probdist_dict: a dictionary containing the probdists indexed
            by the conditions
        @type probdist_dict: dict any -> probdist
        """
        self._dict = probdist_dict

    def __getitem__(self, condition):
        # inherit documentation
        # this will cause an exception for unseen conditions
        return self._dict[condition]

    def conditions(self):
        # inherit documentation
        return self._dict.keys()

##//////////////////////////////////////////////////////
## Adding in log-space.
##//////////////////////////////////////////////////////

# If the difference is bigger than this, then just take the bigger one:
_ADD_LOGS_MAX_DIFF = math.log(1e-30)

def add_logs(logx, logy):
    """
    Given two numbers C{logx}=M{log(x)} and C{logy}=M{log(y)}, return
    M{log(x+y)}.  Conceptually, this is the same as returning
    M{log(exp(C{logx})+exp(C{logy}))}, but the actual implementation
    avoids overflow errors that could result from direct computation.
    """
    if (logx < logy + _ADD_LOGS_MAX_DIFF):
        return logy
    if (logy < logx + _ADD_LOGS_MAX_DIFF):
        return logx
    base = min(logx, logy)
    return base + math.log(math.exp(logx-base) + math.exp(logy-base))

def sum_logs(logs):
    if len(logs) == 0:
        # Use some approximation to infinity.  What this does
        # depends on your system's float implementation.
        return -1e1000
    else:
        return reduce(add_logs, logs[1:], logs[0])

##//////////////////////////////////////////////////////
##  Probabilistic Mix-in
##//////////////////////////////////////////////////////

class ProbabilisticMixIn(object):
    """
    A mix-in class to associate probabilities with other classes
    (trees, rules, etc.).  To use the C{ProbabilisticMixIn} class,
    define a new class that derives from an existing class and from
    ProbabilisticMixIn.  You will need to define a new constructor for
    the new class, which explicitly calls the constructors of both its
    parent classes.  For example:

        >>> class A:
        ...     def __init__(self, x, y): self.data = (x,y)
        ... 
        >>> class ProbabilisticA(A, ProbabilisticMixIn):
        ...     def __init__(self, x, y, **prob_kwarg):
        ...         A.__init__(self, x, y)
        ...         ProbabilisticMixIn.__init__(self, **prob_kwarg)

    See the documentation for the ProbabilisticMixIn
    L{constructor<__init__>} for information about the arguments it
    expects.

    You should generally also redefine the string representation
    methods, the comparison methods, and the hashing method.
    """
    def __init__(self, **kwargs):
        """
        Initialize this object's probability.  This initializer should
        be called by subclass constructors.  C{prob} should generally be
        the first argument for those constructors.

        @kwparam prob: The probability associated with the object.
        @type prob: C{float}
        @kwparam logprob: The log of the probability associated with
            the object.
        @type logrpob: C{float}
        """
        if 'prob' in kwargs:
            if 'logprob' in kwargs:
                raise TypeError('Must specify either prob or logprob '
                                '(not both)')
            else:
                ProbabilisticMixIn.set_prob(self, kwargs['prob'])
        elif 'logprob' in kwargs:
            ProbabilisticMixIn.set_logprob(self, kwargs['logprob'])
        else:
            self.__prob = self.__logprob = None
            
    def set_prob(self, prob):
        """
        Set the probability associated with this object to C{prob}.
        @param prob: The new probability
        @type prob: C{float}
        """
        self.__prob = prob
        self.__logprob = None

    def set_logprob(self, logprob):
        """
        Set the log probability associated with this object to
        C{logprob}.  I.e., set the probability associated with this
        object to C{exp(logprob)}.
        @param logprob: The new log probability
        @type logprob: C{float}
        """
        self.__logprob = prob
        self.__prob = None

    def prob(self):
        """
        @return: The probability associated with this object.
        @rtype: C{float}
        """
        if self.__prob is None:
            if self.__logprob is None: return None
            self.__prob = math.exp(self.__logprob)
        return self.__prob

    def logprob(self):
        """
        @return: C{log(p)}, where C{p} is the probability associated
        with this object.
        
        @rtype: C{float}
        """
        if self.__logprob is None:
            if self.__prob is None: return None
            self.__logprob = math.log(self.__prob)
        return self.__logprob

class ImmutableProbabilisticMixIn(ProbabilisticMixIn):
    def set_prob(self, prob):
        raise ValueError, '%s is immutable' % self.__class__.__name__
    def set_logprob(self, prob):
        raise ValueError, '%s is immutable' % self.__class__.__name__

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _create_rand_fdist(numsamples, numoutcomes):
    """
    Create a new frequency distribution, with random samples.  The
    samples are numbers from 1 to C{numsamples}, and are generated by
    summing two numbers, each of which has a uniform distribution.
    """
    import random
    from math import sqrt
    fdist = FreqDist()
    for x in range(numoutcomes):
        y = (random.randint(1, (1+numsamples)/2) +
             random.randint(0, numsamples/2))
        fdist.inc(y)
    return fdist

def _create_sum_pdist(numsamples):
    """
    Return the true probability distribution for the experiment
    C{_create_rand_fdist(numsamples, x)}.
    """
    fdist = FreqDist()
    for x in range(1, (1+numsamples)/2+1):
        for y in range(0, numsamples/2+1):
            fdist.inc(x+y)
    return MLEProbDist(fdist)

def demo(numsamples=6, numoutcomes=500):
    """
    A demonstration of frequency distributions and probability
    distributions.  This demonstration creates three frequency
    distributions with, and uses them to sample a random process with
    C{numsamples} samples.  Each frequency distribution is sampled
    C{numoutcomes} times.  These three frequency distributions are
    then used to build six probability distributions.  Finally, the
    probability estimates of these distributions are compared to the
    actual probability of each sample.

    @type numsamples: C{int}
    @param numsamples: The number of samples to use in each demo
        frequency distributions.
    @type numoutcomes: C{int}
    @param numoutcomes: The total number of outcomes for each
        demo frequency distribution.  These outcomes are divided into
        C{numsamples} bins.
    @rtype: C{None}
    """

    # Randomly sample a stochastic process three times.
    fdist1 = _create_rand_fdist(numsamples, numoutcomes)
    fdist2 = _create_rand_fdist(numsamples, numoutcomes)
    fdist3 = _create_rand_fdist(numsamples, numoutcomes)

    # Use our samples to create probability distributions.
    pdists = [
        MLEProbDist(fdist1),
        LidstoneProbDist(fdist1, 0.5, numsamples),
        HeldoutProbDist(fdist1, fdist2, numsamples),
        HeldoutProbDist(fdist2, fdist1, numsamples),
        CrossValidationProbDist([fdist1, fdist2, fdist3], numsamples),
        _create_sum_pdist(numsamples),
        ]

    # Find the probability of each sample.
    vals = []
    for n in range(1,numsamples+1):
        vals.append(tuple([n, fdist1.freq(n)] +
                          [pdist.prob(n) for pdist in pdists]))

    # Print the results in a formatted table.
    print ('%d samples (1-%d); %d outcomes were sampled for each FreqDist' %
           (numsamples, numsamples, numoutcomes))
    print '='*9*(len(pdists)+2)
    FORMATSTR = '      FreqDist '+ '%8s '*(len(pdists)-1) + '|  Actual'
    print FORMATSTR % tuple([`pdist`[1:9] for pdist in pdists[:-1]])
    print '-'*9*(len(pdists)+2)
    FORMATSTR = '%3d   %8.6f ' + '%8.6f '*(len(pdists)-1) + '| %8.6f'
    for val in vals:
        print FORMATSTR % val
    
    # Print the totals for each column (should all be 1.0)
    zvals = zip(*vals)
    def sum(lst): return reduce(lambda x,y:x+y, lst, 0)
    sums = [sum(val) for val in zvals[1:]]
    print '-'*9*(len(pdists)+2)
    FORMATSTR = 'Total ' + '%8.6f '*(len(pdists)) + '| %8.6f'
    print  FORMATSTR % tuple(sums)
    print '='*9*(len(pdists)+2)
    
    # Display the distributions themselves, if they're short enough.
    if len(`str(fdist1)`) < 70:
        print '  fdist1:', str(fdist1)
        print '  fdist2:', str(fdist2)
        print '  fdist3:', str(fdist3)
    print

if __name__ == '__main__':
    demo(6, 10)
    demo(5, 5000)
