#!/usr/local/bin/python

#############################################################
#
# Claire Louise Taylor
#
# 25 October 2003
#
# 
# A Bagger Class
# Use multiple samples of the training data to train instances
# of a naive Bayes wsd.  Assign the sense that gets predicted
# the most often.
# 
#
#############################################################
from nltk.probability import *
from nltk.tagger import *
import random
from naiveBayes import simpleBayesian

class bagger:
    """
    This class implements a bagger.
    The main idea of a bagger is that the amount of training data
    is limited and so we try to overcome this problem by reusing
    the same training data to train several of the same classifiers.

    This works as follows:
    The bagger 'replaces' a certain number of training instances
    with copies of othere training instances.  It does this t
    times (t being the parameter passed in to __init__.  see its
    inline documentation for more details), producing t dependent
    training sets.  t classifiers are then trained on these data sets.
    Since each of the data sets has copies of some of the instances
    the classifier will be slightly biased.
    For the testing phase each instance of the ambiguous word is 
    assigned a sense by looking at which sense each of the t classifiers
    predicts.  The most frequently predicted sense becomes the assigned
    sense for this instance.

    We found by doing this that the bagging method does not add much to
    the performance of the system but we decided to leave it as part of 
    the system as it is interesting anyway.
    
    """

    def __init__(self,t,replacement,N,word):
        """
        Create an instance of the bagger class.
        The input values define how the bagger class will train and test

	@param t: The number of models used to train and test with.
		  The bagger will create t naive Bayes classifers each
		  trained on a different (but dependent) data set.
	@type t: C{int}

	@param replacement: The number of training data instances that will
			    be replaced with copies of other instances for
			    each of the t data sets
	@type replacement: C{int}

	@param N: The context window for the Naive Bayes Classifer.
		  Each of the t models will have the same context window
	@type N: C{int}

	@param word: The ambiguous word we wish to disambiguate
	@type word: C{string}

        """
        if t == 0:
            t = 1 
	    # don't allow 0 or we will have problems
            
        self._t = t
        self._replacement = replacement
        self._N = N
        self._word = word
	# fairly straight forward.  Just remember these values for later use.

    def train(self,sense_labeled_text):
        """
        Train t Naive Bayes Classifiers (each with context window
	self._N).  For each classifier create a different data set
	by taking the original training data and replacing 
	self._replacement training instances with copies of other
	training instances.
	
	Store the trained classifiers in self._models for later use in
	testing

	@param sense_labeled_text: The training data we wish to train
				   the t models on
	@type sense_labeled_text: List{SenseLabeledText}	

        """
        self._models = []
        sample = []
        for i in range(self._t):
            # take a different sample of data
            del sample
	    # we had a problem with memory usage.
	    # so I delete it every time to make sure the memory is free-ed
	    # a bit redundant for the first time through the loop but oh-well

            sample = []
            sample = sense_labeled_text

            # delete self._replacement instances
            for j in range(self._replacement):
                t = sample.pop(random.randint(0,len(sample)-1))

            # now insert the same number of instances (copies of
            # the existing samples
            for j in range(self._replacement):
                sample.append(sample[random.randint(0,len(sample)-1)])
                                    
            
            self._models.append(simpleBayesian(self._word,self._N))
            self._models[-1].train(sample)
	    # create a new simpleBayesian instance and train it on this
	    # sample of the data set

        # so we have now trained t different naive Bayes models on
        # different samples of the training data.
        # so we can test and assign the most frequent sense


    def sense_tag(self,test_data):
        """
	Run the testing phase.
	For each instance of the ambiguous word we ask each of the
	self._t classifiers to predict a sense for this occurrence
	and then assign the most frequently predicted sense.

	@param test_data: The test data containing untagged instances
			  of the ambiguous word.
	@type test_data: List{Token}

	@return: The sense tagged data
	@rtype: List{TaggedToken}	
	
        """

        for i in range(self._t):
            self._models[i]._testdata = test_data
	    # make sure we assign each one the test data
	    # this is normally done using the sense_tag function
	    # of the simpleBayesian class but we don't want to call
	    # that this time as we only want to get the senses 
	    # one word at a time.
	    # So instead we call the _test function which returns
	    # the predicted sense.  See naiveBayes.py for more
	    # information


        results = []
        
        for i in range(len(test_data)):
            new_tag = ""
            senses = FreqDist()
            if test_data[i].type() == self._word:
                #  run each model on this and store the result.
                # then assign the most frequent sense.
                for model in range(self._t):
                    senses.inc(self._models[model]._test(i))
                
                
                new_tag = senses.max()
            del senses    
	    # again - memory problems so delete to be on the safe side!
            results.append(TaggedType(test_data[i], new_tag))
	    # add the tagged word to the end of the list
	# return the resulting tagged tokens
        return results

