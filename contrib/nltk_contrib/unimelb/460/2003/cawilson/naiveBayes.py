#!/usr/local/bin/python

#############################################################
#
# Claire Louise Taylor
#
# 7 October 2003
#
# 
# This only performs disambiguation for one word at a time
#
# The basecase takes the most frequent german 'sense' (or the
# german translation) and tags all occurences of the ambiguous
# word as that sense.
#
# The simpleBaysian class is a classifier that uses naive bayes
# to decide a word's sense using bayes rule.
# When an instance of this class is created the context size N
# is specified. So in training and testing we only look N words
# infront and behind the ambiguous word.
# In the case where we want the whole sentence to be the context
# we set N=-1.
#
#############################################################
from nltk.probability import *
from nltk.tagger import *



class basecase:
    """
    A class for disambiguating words.
    Assigns the most frequent sense of the word
    to all occurrences.

    Gives a base case to compare other results to.

    This class takes the word to disambiguate as a
    parameter when initialising.  So therefore a separate
    class is required for every different word you wish
    to disambiguate.
   
    As the basecase assigns the most frequent sense to all
    occurrences of the word we don't need to remember any
    information about context.
    
    """
    
    def __init__(self,word):
        """
        Set the word we are trying to disambiguate and create a
        frequency distribution that we will use to train and test.
        
        @param word: The word we plan to disambigutate.
        @type word: C{string}
        
        """

        self._word = word
        self._freq_dist = FreqDist()
        
    def train(self,sense_labeled_text):
        """
        Train a base case on this data.
	This involves counting the frequency of each sense as it
	appears in the training data (which is sense_labeled_text

	@param sense_labeled_text: A list of SenseLabeledText instances.
	  Each SenseLabeledText instance consists of the sentence which
	  contains the ambiguous word and the sense of the word.
	  In the case of bilingual corpora the sense is the translation
	  of the word.   
	  
	@type sense_labeled_text: List{SenseLabeledText}
        
        """

        for sentence in sense_labeled_text:
            sent = sentence.type()
	    (sense,) = sent.label()
            self._freq_dist.inc(sense)
	# Record the frequency of the sense.
        

    def sense_tag(self,data):
        """
	Run the testing phase of this disambiguator.
	As this is just a base case every occurrence of the 
	ambiguous word gets assigned the same sense.  This
	sense is the sense that appeared the most often during
	training.

        @param data: A list of untagged data for testing.
        @type data: List{Token}

	@return: Return the list of Tokens with the ambiguous
		words tagged with the most frequent sense.
	@rtype: List{Token}
        
        """
      
        max = self._freq_dist.max()
        # find the sense which occurs most often
        
        res = []
        for i in range(len(data)):
            new_tag = ""
            if data[i].type() == self._word:
                #  We have found an occurence of the ambiguous word
		#  so disambiguate by assigning the most frequent
		#  sense 
                new_tag = max
            res.append(TaggedType(data[i],new_tag))
            
        return res

class simpleBayesian:
    """
    A simple Bayesian which takes N words
    either side of the ambiguous word as the context window.
    -1 = whole sentence.

    The Naive Bayes method uses Bayes Theorem to assign a
    sense for each test sentence.

        P(sense|context) = P(context|sense)P(sense)
                        ---------------------		(1)
                               P(context)
    
    In practice P(context|sense) = P(w_1|sense)*P(w_2|sense)*...*P(w_n|sense) (2)
    where context = [w_1,w_2,...,w_n]	

    So during training a simpleBayesian instance will calculate
    conditional frequencies of a word for a given sense.
    eg P('rate'|'Zinsen').  It also calculates P('Zinsen').

    During training it will try to find the sense, s, such that
    P(s|context) > P(t|context) for all other senses t != s.

    As P(context) is the same each time we calculate P(sense|context)
    for a different context we only have to calculate
    P(context|sense)P(sense) and find the sense such that this is maximised.

    This implementation uses the Witten-Bell Discounting formulas
    to allow for events we haven't seen yet.

    So if P(word|sense) = 0 instead of allowing the whole product in (2)
    to become zero as well we introduce smoothing so that events we haven't
    seen yet become small but non zero and probabilities of events we have
    seen are adjusted accordingly.

    The formulas used are as follows:
	P_i =   C_i 
	      --------   if C_i > 0
	       (N + T)

	P_i =    T
	       --------
		Z*(N + T)  where 
			         N is the number of word tokens (total)
				 T is word tokens seen so far for this sense
				 Z is the number of words with zero count.
				  We estimate this at N - T

    """

    def __init__(self, word, N=-1):
        """
	Initialise a Naive Bayes instance by setting the 
	word we are disambiguating and the size of the context 
	window we wish to use.

        @param word: the word we wish to disambiguate
        @type word: C{string}

        @param N: the number of words before and after which we want to
                  include in the context of this word.
                  The default value is -1 which means all words in the
                  sentence will be used as context
        @type N: C{int}

        """
        self._N = N
        # the window either side of the ambiguous word
        
        self._word = word
        self._freq_dist = ConditionalFreqDist()
        self._sense_freq_dist = FreqDist()  
	# self._freq_dist is a conditional frequency distribution
	# used to record P(word|sense)
	
	# self._sense_freq_dist is a frequency distribution used 
	# to record P(sense)


    def train(self, sense_labeled_text):
        """
	This function trains the Naive Bayes Classifier.
	It takes the training data as sense_labeled_text and updates
	the internal data structures that record probabilities that
	are used in the testing phase.  It records information
	about words in the context window that was specified in the 
	initialisation function.   The training data is passed in 
	as a list of senseLabeledText instances.

	@param sense_labeled_text:  The training data.  A list of
	SenseLabeledText.  Each SenseLabeledText instance contains
	the sentence containing the amiguous word as well as the sense
	for this particular sentence.

	@type sense_labeled_text: List{SenseLabeledText}
        """
	for sentence in sense_labeled_text:

	    sent = sentence.type()
	    (sense,) = sent.label()
	    # we need the probability of each sense for the testing phase.
            self._sense_freq_dist.inc(sense)

	    tokens = sentence.type().text()
	    pos = sentence.type().headIndex()
	    # find the position of the word in the sentence

	    #include each word in the context window in the 
	    # self._freq_dist frequency distribution
            if self._N == -1:
                #all words in the sentence
                start = 0
                end = len(tokens)
            else:
		# take the words around the ambiguous word
		# (at position pos) as the context window
		# so we want N words either side.
		# deal with the cases when taking N words
		# around the ambiguous one means we go
		# over the end of the sentence or off the
		# beginning
                if pos - self._N < 0:
                    start = 0
                else:
                    start = pos - self._N

                if pos + self._N > len(tokens):
                    end = len(tokens)
                else:
                    end = pos + self._N

            # take from [start,pos-1] and [pos+1,end] as
	    # the context window
            for token in tokens[start:pos-1]:
		# for each word in the context window
		# before the ambiguous word
		# include it in the conditional frequency
		# distribution.  This will be used later
		# to calculate Bayes Theorem during testing
                self._freq_dist[sense].inc(token.type().base())

            for token in tokens[pos+1:end]:
		# now do the same for the words after it...
                self._freq_dist[sense].inc(token.type().base())

 	self._prob_dist = ConditionalProbDist(self._freq_dist, MLEProbDist)
        self._sense_prob_dist = MLEProbDist(self._sense_freq_dist)
        #create some probability distributions    
	return 


    def sense_tag(self, test_data):
        """
	This function goes through the test data and assigns a sense
	for each occurence of the ambiguous word by calling the _test
	function.  Every other word is tagged as "" so any accuracy function
	should only count correct tags for the actual ambiguous word
	instead of the tags for all words.

	See the _test function for more information about the method
	used to decide which tag is most correct for each instance
	of the ambiguous word

        @param data: A list of untagged data for testing.
        @type data: List{Token}

	@return: The Test Tokens now having each occurrence of the
		ambiguous word tagged with a sense according to	
		Bayes Theorem.
	@rtype: List{TaggedToken}
        
        """
        self._testdata = test_data
        results = []
        for i in range(len(test_data)):
            new_tag = ""
            if test_data[i].type() == self._word:
                #  We have found an ambiguous word 
               	# so try to disambiguate it 
                new_tag = self._test(i)
            results.append(TaggedType(test_data[i], new_tag))
        return results
        
    def _test(self, pos):
        """
        Use Bayes Theorem and the Witten-Bell Discounting formulas (for
        unseen words) to assign the most probable sense for the ambiguous
        word at position pos using Bayes Theorem.

        Witten-Bell Formulas:
        n = no of word tokens
        t = no of word tokens seen in this context
        z = no of words with zero frequency

        P(word_i) =    t        for c_i = 0   (1)
                     -------        (where c_i is the count of this word)
                     z*(n+t)


        P(word_i) =   c_i       for c_i > 0  (2)
                    ---------
                     (n+t)

        I take n to be the total no of words seen in training.
        t is the number of words seen for the current sense we are looking at.
        As I don't know the number of words with zero frequency I take it as
        n - t

	See the inline documentation at the beginning of this class for 
	Bayes Theorem.

        I actually found that when I _don't_ change P(word_i) for c_i > 0
	(where word_i _has_ been seen) using formula (2) above
	I get approximately 10% better accuracy
	(measured as correct/total_no_of_instances_of_ambiguous_word) than
	when I did adjust the probabilities.  Despite this I have implemented
	the probability adjustments so this method is completely correct. 
	
        
        @param pos: position of the word in self._testdata
        @type pos: C{int}

        @return: The assigned sense for this occurrence
        @rtype: C{string}
        """
            
        context = []
	#initialise a variable to store the context 
        if pos != -1:
            #check to make sure the word is really in the sentence first.
            if self._N == -1:
		# when N = -1 we want the context window to be the whole 
		# sentence.  However as this is just a list of tokens
		# it is not easy to find sentence boundaries,  unless
		# I change how the data is passed in so it is tokenized
		# by sentences first then by words.  This is possible
		# but due to time constraints I decided not to implement this
		# instead I look 20 words before and after the ambiguous
		# word.
	        
                start = pos - 20
                end = pos + 20
		if start < 0:
			start = 0
		if end > len(self._testdata):
			end = len(self._testdata)
		#check to make sure we dont go over the edge of the list
            else:
		# otherwise we have a normal context window of size N
		# so get the start and end positions in the same way 
		# we did during training
                if pos - self._N < 0:
                    start = 0
                else:
                    start = pos - self._N

                if pos + self._N > len(self._testdata):
                    end = len(self._testdata)
                else:
                    end = pos + self._N

            context += self._testdata[start:pos-1]
            context += self._testdata[pos+1:end]
	    # so we now have a context window for this occurence of the word
	    # and we can sense tag it using Bayes Theorem
            
        dict = {}
            # create a dictionary of senses which associates
	    # each sense with P(sense|context) for this context 
	    # When we are finished calculating this for each possible
	    # sense we create a DictionaryProbDist so we can easily find
	    # the maximum and assign the appropriate sense.
            
        n = (float) (self._get_n())
        # see the inline documentation for this function for an explanation
        # of n (as well as t and z below)
        
        for sense in self._sense_prob_dist.samples():
	    # we want to find P(sense|context) for each sense and then
	    # assign the sense with the largest P(sense|context) as
	    # the most likely sense

            t = (float) (self._get_t(sense))
            z = (float) (n - t)
	    # see the inline documentation for this function or class for
	    # an explanation of these variables.  Used for Smoothing
         
            dict[sense] = 1
            # calculate P(sense|context) using Bayes Theorem.
            # see the inline documentation of this class for more information

            for word in context:
                if self._freq_dist[sense].freq(word.type()) == 0.0:
                    # an unseen word so assign a very small probability
                    tempProb = (float) (1/z)*(t/(n+t))
                else:
                    # we have seen this word before but we have to alter
                    # the probability slightly to allow for the unseen words:
                    tempProb = (float)(self._freq_dist[sense].count(
			word.type()))/(float)(n+t)
                dict[sense] *= tempProb
                # each word in the context has its probability multiplied to the
		# overall probability so far.  See the inline documentation
		# for this class for more information.                

            dict[sense] *= self._sense_prob_dist.prob(sense)
            # Bayes Rule says we need to mulitply the result of the above
	    # calculations by the probability of finding this sense.
 
        dict_prob = DictionaryProbDist(dict)
	# make a dictionary Probability distribution based on the information
	# gathered above
        
        assign_sense = dict_prob.max()
        # get the sense with the highest P(sense|context)        
        return assign_sense

    def _get_n(self):
        """
        Find n for the Witten-Bell discounting formulas.
        n = total number of word tokens seen in training.

	@return: The Value for n
	@rtype: C{int}
        """
        total = 0
        for sense in self._sense_prob_dist.samples():
            for s in self._freq_dist[sense].samples():
                total += self._freq_dist[sense].count(s)
        # count the number of word tokens we saw in training    
        return total

    def _get_t(self,sense):
        """
        Find t for the Witten-Bell discounting formulas.
        t = the number of word tokens seen so far in this context
        (or sense)
	
	@param sense: The sense that we wish to find a t value for
	@type sense: C{string}

	@return: The t value defined above and in the inline 
		documentation for this class (and the _test function)
	@rtype: C{int} 
        """

        t = 0
        for word in self._freq_dist[sense].samples():
            t += self._freq_dist[sense].count(word)
	# count the number of word tokens that were seen together with
	# this sense during training
        return t

    


