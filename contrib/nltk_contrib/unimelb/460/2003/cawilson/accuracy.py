#!/usr/local/bin/python
#
######################################################################
#
#
# Claire Louise Taylor
#
# 30 October 2003
#
#
# This file contains the functions used to evaluate the wsd methods.
#
######################################################################
from nltk.probability import *
from nltk.tagger import *

def wsdaccuracy(orig, test, word):
    """
    @param orig: the original test data 
    @param orig: List{SenseLabeledText}

    @param test: Our tagged tokens
    @type test: List{TaggedToken}

    @param word: The word we were trying to disambiguate
    @type word: C{string}

    @return: The percentage of the tags we got correct
    @rtype: C{float} 
    
    Test the accuracy of a tagged text, with respect the correct
    tagging.  This accuracy is defined as the percentage of tokens
    tagged correctly.

    Accuracy is only tested on the ambiguous words we disambiguated

    Also, this function doesnot call the sense mapping function and
    so only works if you both tested and trained on data with the 
    same tags
    """
    # go through each of the words in the original data
    # if we find the ambiguous word see if it is tagged correctly
    # if it is increment the correct counter.
    # return the percentage correct
    correct = 0
    count = 0
    offset = 0
    for i in range(len(orig)):
	
	for token in orig[i].type().text():
	    if token.type().base() == word:
                count += 1
		# if the sense tags are the same increment count
		test_tagged_token = test[offset + orig[i].type().headIndex()]
		if orig[i].type().label()[0] == test_tagged_token.tag():
			correct +=1

	# increment the offset for the start of the current sentence
	offset += len(orig[i].type().text())


    # return the percentage of correct tags 
    return float(correct)/count
 


def precision_recall(orig,test,word,alpha=0.5):
    """
    calculate the precision and recall for each sense
    that appears in the test data we tagged.

    This function can only be run on one ambiguous word
    at a time.  

    Precision is defined as follows:
	P = no of times we tagged as this sense and were correct
	   -------------------------------------------------------
	   total no of instances of this sense in the data we tagged

   Recall is defined as:
	R = no of times tagged as this sense and it is correct
	   -------------------------------------------------------
	   total no of instances tagged as this sense in the original 

    
    @param orig: The original test data with the correct sense tags attached
    @type orig: List{SenseLabeledText}

    @param test: The test data after being tagged by a disambiguator.
		 Only the ambiguous word needs to be tagged as all other
		 tags are ignored
    @type test: List{TaggedToken}

    @param word: The ambiguous word
    @type word: C{string}

    @param alpha: The value used to calculate the f-measure.
		 1/(alpha/prec + (1-alpha)/rec)
		 Must be between 0 and 1
    @type alpha: C{float}

    """


    f_sense = FreqDist()

    for i in range(len(orig)):
        for token in orig[i].type().text():
            if token.type().base() == word:
                f_sense.inc(orig[i].type().label()[0])

    # count frequency of each tag in the original data

    f_mytags = FreqDist()
    for r in test:
        if r.base().type() == word:
            f_mytags.inc(r.tag())
    # count the frequency of each tag in the data that has been tagged

    sense_map = match_sense(orig,test,word)
    # since we are using a bilingual corpus we need a way of deciding which
    # translation of the ambiguous word corresponds to which sense in the
    # testing data.  See the match_sense function for more information
    # so sense_map is a dictionary that gives the actual sense (from the
    # senses in the original test data) for each assigned sense

    for sense in f_mytags.samples():
        # for each sense calculate the precision and recall
	
        count = 0
        offset = 0
        correct = 0
        for i in range(len(orig)):
	
            for token in orig[i].type().text():
                if token.type().base() == word:
                    count += 1
		    # if the sense tags are the same
		    test_tagged_token= test[offset + orig[i].type().headIndex()]
                    if test_tagged_token.tag() == sense: #sense_map[sense]:
                        if orig[i].type().label()[0] == sense_map[sense]: 
			    #test_tagged_token.tag():
			    correct +=1
			    # count the number of correct tags for this sense
			    # only

	    # increment the offset for the start of the current sentence
	    offset += len(orig[i].type().text())

	# calculate precision and recall for this sense.
	# and the f measure with alpha = 0.5
	prec = precision(correct,f_mytags.count(sense))

        rec = recall(correct,f_sense.count(sense_map[sense]))

        fmeasure = f_measure(correct,f_mytags.count(sense), \
		f_sense.count(sense_map[sense]))
	# default value for alpha is 0.5
        
	print "\nsense is: ", sense
        print "precision is: ",prec
        print "recall is: ",rec
        print "f measure is: ", fmeasure
	print "\n"

def precision(correct,count):
    """
    Calculate the precision.  Return zero if count is zero to 
    avoid a divide by zero error.

    See precision_recall function for more details of precision

    The definitions below assume that this function is called for each
    sense.

    @param correct:  The number of times an instance of the ambiguous word
		     was tagged as correct (as the sense).
    @type correct: C{int}

    @param count: The total number of times it was assigned as the sense.
    @type count: C{int}

    @return: C{float}
    @rtype: C{float} 
    """
    if count == 0: return 0.0
    else: return float(correct)/float(count)

def recall(correct,count):
    """
    Calculate the recall.  Return zero if count is zero to avoid a divide
    by zero error.

    See precision_recall function for more details of recall.

    The definitions below assume that this function is called for
    each sense.

    @param correct: The number of times a word was tagged as this sense and
		    it is correct.
    @type correct: C{int}

    @param count: Total number of instances of the sense in the test data 
    @type count: C{int}

    @return: The recall value for a sense
    @rtype: C{float}
    """
    if count == 0: return 0.0
    else: return float(correct)/float(count)

        
def f_measure(correct,pcount,rcount,alpha=0.5):
    """
    Calculate the f measure.  Set the default alpha to 0.5

    Return zero if precision or recall is zero to avoid a divide by zero
    error.

    F measure is defined as follows:
    
      f-measure =                        1
                  -----------------------------------------------------
                         alpha                   (1-alpha)
		     ( ---------- )      +   ( ---------------- )
                        precision                   recall
   
    @param correct: The total number of times the sense was tagged correctly
    @type correct: C{int}

    @param pcount: Total number of times it was assigned the sense
    @type pcount: C{int}

    @param rcount: Total number of times it was tagged as this sense 
		   in the test data
    @type rcount: C{int}

    @return: The fmeasure value
    @rtype: C{float}
    """
    prec = precision(correct,pcount)
    rec = recall(correct,rcount)

    if prec == 0 or rec == 0:
        return 0
    else: return 1/(alpha/prec + (1-alpha)/rec)




def match_sense(orig,test,word,alpha=0.5):
    """
    Since this project was designed for use with a bilingual corpus
    the assigned senses will differ from the actual senses in the 
    test data.  So this function attempts to match them up.

    Match the assigned sense to the correct sense based on
    f_measure values.

    So for each assigned sense calculate the precision and recall for
    each actual sense and then take the actual sense as the one with the
    highest f measure.

    Repeat for each sense in test and return a dictionary of
    assigned sense -> actual


    @param orig: The original data complete with original tags
    @type orig: List{SenseLabeledText}

    @param test: The data that has been tagged using a word sense
		  disambiguator
    @type test: List{TaggedToken}

    @param word: The ambigous word we are interested in.  We are only
		 concerned with this word and not any other tags
    @type word: C{string}

    @param alpha: The alpha value used to calculate the f-measure.
		  The default value id 0.5
		  Must be between 0 and 1
    @type alpha: C{float}

    @return: A dictionary mapping the assigned senses (in test) to the
	     actual senses (in orig)
    @rtype: Dictionary{string:string}
    """


    f_sense = FreqDist()

    for i in range(len(orig)):
        for token in orig[i].type().text():
            if token.type().base() == word:
                f_sense.inc(orig[i].type().label()[0])


    f_mytags = FreqDist()
    for r in test:
        if r.base().type() == word:
            f_mytags.inc(r.tag())

    #count the number of times each sense appears in both the original
    # test data and the newly tagged test data

    actualsenses = f_sense.samples()
    senses = []
    for sense in f_mytags.samples():
        senses.append([sense,f_mytags.count(sense)])
    # create a list of senses where each element of the list is a 
    # (sense, count) pair.  These are the assigned tags

    sort(senses)
    # sort the senses so that the most frequent sense gets mapped first

    sense_map = {}
    for sense_count in senses:
        # for each assigned sense
        sense = sense_count[0]
        sense_dict = {}
        for actualsense in actualsenses:
            # for each actual sense calculate f measures
	    # and then assign the one with the highest f measure

            count = 0
            offset = 0
            correct = 0
            for i in range(len(orig)):
	
                for token in orig[i].type().text():
                    if token.type().base() == word:
                        count += 1
                        test_tagged_token = test[offset + \
				orig[i].type().headIndex()]
                        if test_tagged_token.tag() == sense:
                            if orig[i].type().label()[0] == actualsense:
			        correct +=1

		# increment the offset for the start of the current sentence
                offset += len(orig[i].type().text())
	
            sense_dict[actualsense] = f_measure(correct, \
                           f_mytags.count(sense),f_sense.count(actualsense))
        sense_dict_prob = DictionaryProbDist(sense_dict)
	# create a dictionary probability dist so we can easily find the max
        most_likely_sense = sense_dict_prob.max()
        del sense_dict_prob
        del sense_dict
	# delete the dictionary and prob dist.  We had a few problems with 
	# memory usage so delete whatever we can.
            
        actualsenses.remove(most_likely_sense)
	# remove the mapped sense from the list so we dont assign it more than
	# once
        sense_map[sense] = most_likely_sense
	# record the mapping in the dictionary

    # return the dictionary mapping senses.
    print "Senses were mapped as follows"
    print sense_map
    return sense_map


def sort(list):
    """ 
    sort the list.
    Each element of the list is a pair consisting of the sense in position 0
    and the count.  So this function sorts by this count value so the most 
    frequent sense is first

    @param list: A list of pairs of sense and the corresponding count.
		 This function will sort by this count
    @type list: List{List{string,int}}

    @return: The sorted list
    @rtype: List{List{string,int}}
    """
    res = list[:0]
    for j in range(len(list)):
        i = 0
        for y in res:
            if list[j][1] <= y[1]: break
            i += 1
        res = res[:i]+ list[j:j+1] + res[i:]
    return res
