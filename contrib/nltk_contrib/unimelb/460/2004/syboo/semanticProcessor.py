#! /usr/bin/env python

# Subject: 433-460
# Authors: syboo, aboxhall, jcwyang
# Date: October 2004
# Description:
# 	transform a sentence into first order predicate logic

import string
from nltk.tokenizer import *
from myMain import *
from nltk.tokenizer import WhitespaceTokenizer

class processor:
    def __init__(self,string):
        self.string = string
	# variables symbols that will be used in the first order predicate logic
	# representation of the sentence
	# Need to have it as gobal and pop one from the list whenever 
	# a variable is needed to ensure that the variables are
	# always unique
	self.varSymbols = ['N','M','T','S','U','V','C','B','A','W','Z','Y','X']
   
    # Tokenize the semantic representation into word by word
    # ignoring the brackets and commas.
    # Pass to process_sem() to get the first order predicate logic 
    def parser_tokenizer(self,string):
        text = string
        regexp = r'(\w+)|(\d+)|((\+|\-)\w+)|(\?ans)'
        text_token = Token(TEXT=text)
        tokenizer = RegexpTokenizer(regexp,SUBTOKENS='WORDS')
        tokenizer.tokenize(text_token)
        array = text_token['WORDS']
	return array

    def convert_to_predicate_logic(self, array):
	i=0 
        while(i < len(array)):
            word = array[i]['TEXT']
            if(word=="sem"):
                 sem = self.process_sem(i+1,array)
                 print sem.predicate
                 i = sem.index
            i = i+1    
        print "" 

    # change the semantic to first order logic
    def process_sem(self,index,array):
	negative = ""

	# is it a question
        if(array[1]['TEXT'] == "+question"):
            status = "yes"
	else:
	    status = "no"

        while(index < len(array)):    
            curr = array[index]['TEXT']
	    
            #skip over the keyword of the predicate
	    if(curr == "predicate"):
                index=index+1
                continue
	    # get the object
            elif(curr == "object"):
                semObject = self.get_object(index+1,array)
                index = semObject.index
	    # is it negative 
	    elif(string.find(curr, "true") != -1):
		if (curr == "-true"):
		    negative = "\+"
	    # get the verb
            elif(curr == 'verb'):
                semVerb = self.get_next_word(index,array)
                index = index+1
            # get the subject
	    elif(curr == 'subject'):
	        semSubject = self.get_subject(index+1, array)
                index = semSubject.index
                break
            index= index+1
	
	# form the predicate
	predicate = self.form_predicate(semObject, semVerb, semSubject, negative)
	predicate = "question(" + status + "), " + predicate

        # create the dataClass based on the predicate
        sem = semClass(index+1, predicate)
        return sem

    # form the predicate with the object, verb, subject and negative status
    def form_predicate(self, semObject, semVerb, semSubject, negative):
	    predicate = ""
	    i = 0
	    # form the relations with multiple subjects and/or objects
	    # eg "this restaurant serves pizza and noodles" 
	    # => serve(X,Y), serve(X,Z), equal(X,'restaurant'),
	    #    equal(Y,'pizza'), equal(Z,'noodles')
	    # Or "noodlebar and chinabar serve pizza"
	    # => serve(X,Y),serve(Z,Y),equal(X,'noodlebar'),
	    #    equal(Z,'chinabar'),equal(Y,'pizza')
	    while(i < len(semObject.variable)):
		j = 0
		while(j < len(semSubject.variable)):
		    predicate = predicate + negative + semVerb + "(" + (semSubject.variable)[j] + ", " + (semObject.variable)[i] + "), "
		    j = j + 1
		i = i + 1

            predicate = predicate + semSubject.predicate

	    if (semObject.predicate != ""):
                predicate = predicate +", "+ semObject.predicate
            

	    return predicate
    
    # extract the semantic representation
    # the output that we get from invoking main() is the entire parse tree.
    # However, we are only interested in the semantic matrix part, which is
    # the S[] part. Function extractString() uses regExpTokenizer to
    # extract the part that we are interested in.
    def extractString(self):
        toBeExtracted = self.string
        toBeExtracted = str(toBeExtracted)
        text_token = Token(TEXT=toBeExtracted)
	 # inside the [] are the possible entries
        regexp=r'(S\[(\w|\s|\d|\+|\-|\,|\'|\[|\=|\]|\?)+\])'
        
        tokenizer = RegexpTokenizer(regexp,SUBTOKENS='WORDS')
        tokenizer.tokenize(text_token)

        processText = text_token['WORDS']
        
	# only get the first semantic representation which is 
	# the complete semantic representation for the sentence
        extracted = str(processText[0]['TEXT'])
        return extracted
    
    # get the object, eg X serves Y, Y is the object of the sentence.
    def get_object(self,i,array):
        curr = array[i]['TEXT']

	# if the object is the amount (price), for sentences like 
	# "a pizza costs five dollars" 
        if(curr=='amt'):
            amt = self.get_next_word(i,array)
            i = i+2
            unit = self.get_next_word(i,array)
            i = i+1
            var = list.pop(self.varSymbols)
            object="equal("+var+", "+ amt +"_"+unit+")"
	    semObject = semClass(i,object,[var])
	# if "object" is followed by a "predicate", then we have 
        # a sentential complement sentence, like
	# "I think this restaurant serves pizza"
        elif(curr=='predicate'):
            semTemp=self.process_sem(i+1,array)
            tempObjStr="(" + semTemp.predicate + ")"
            semObject= semClass(semTemp.index, "", [tempObjStr])

        # this is the conjunction case like,
	# "this restaurant serves pizza and noodles".
	# This case will have to get multiple nouns
	elif(curr=='+and'):
            semObject=self.get_multiple_nouns(i+1,array)

        # simple case of one single noun phase,
        else:
            varObject = list.pop(self.varSymbols)
	    semObject = self.get_noun_phase(i, array, varObject)
            
        return semObject

    # get multiple nouns that are joined using conjuction word "and"
    def get_multiple_nouns(self,i,array):
            i = i+1
	    next = array[i]['TEXT']
	    semFinal = semClass(0, "", [])
	    
            # get the first noun
            if (next == "+and"):
		# nested "+and"
                semNoun1 = self.get_multiple_nouns(i+1, array)
                i = semNoun1.index + 2
            else:
		# get the noun_phase
                var = list.pop(self.varSymbols)
                semNoun1 = self.get_noun_phase(i, array, var)
                i = semNoun1.index + 2

            # get the second noun
            next = array[i]['TEXT']
            if (next == "+and"):
		# nested "+and"
                semNoun2 = self.get_multiple_nouns(i+1, array)
            else:
		# get the noun_phase
                var = list.pop(self.varSymbols) 
                semNoun2 = self.get_noun_phase(i, array, var)

	    # add the 2 nouns together
	    semFinal.index = semNoun2.index
	    semFinal.predicate = semNoun1.predicate + ", " + semNoun2.predicate
	    semFinal.variable = semNoun1.variable + semNoun2.variable
	     
	    return semFinal
	    
	
    # get the subject
    def get_subject(self,i,array):
        curr = array[i]['TEXT']
 	# the case of more than one subject using the conjunction
	# word "and"
	if (curr=='+and'):
            semSubject=self.get_multiple_nouns(i+1,array)
	# get the single subject
        else:
            varSubject = list.pop(self.varSymbols)
	    semSubject = self.get_noun_phase(i, array, varSubject)
        
	return semSubject

    # get the curr+1 word in the array
    def get_next_word(self,curr,array):
        next = array[curr+1]['TEXT']
        return next

    # get the noun phase, including the adjectives
    def get_noun_phase(self, curr, array, varSymbol):
        i = curr
	next = array[i]['TEXT']

	adjPhase = ""
	
	# while the adjactive keyword is still found
	while(string.find(next,"adj") != -1):
		i = i + 1
		next = array[i]['TEXT']
		# add the adjective to the adjPhase
		adjPhase = adjPhase + next + "(" + varSymbol + "), "
		i = i + 1
		next = array[i]['TEXT']
	# get the noun
	if (next == "n"):
		i = i + 1
		next = array[i]['TEXT']
	# add the adjective together with the noun
	adjPhase = adjPhase + "equal(" + varSymbol + ", " + next + ")"

	# add the used variable to the data object created 
	var = []
	var.append(varSymbol)
	semObject = semClass(i, adjPhase, var)

	return semObject

# Data object used to pass the information around
# Index: Process till which array element (word)
# predicate: the predicate form with the words processed
# variable: variable used for the words processed
class semClass:
    def __init__(self,index, predicate, variable=[]):
        self.index = index
        self.predicate = predicate
	self.variable = variable

    def getIndex(self):
        return self.index
        
    def getStr(self):
        return self.predicate

# the function to run the program, it first invokes function main() from
# myMain.py to converting the input sentence into feature-based grammar. It
# then obtains the output of main(), checks whether the output is empty, if
# yes, it means the input sentence is ungrammatical, the program outputs an
# error message, and terminates. If the output is non-empty, it then begin
# the predicate-logic converting process.
def run():
    sent = main()
    text = sent['TREES']
    if(len(text) == 0):
	    print "ERROR: INVALID SENTENCE"
	    return
    tokenize = processor(text)
	# the output of main() is the entire parse tree, however, we are
	# only interested in the S[] part. Function extractString extracts
	# the part that we are interested in.
    extractedString = tokenize.extractString()
	# from the extractedString, tokenize it word by word using regular
	# expression tokenizer.
    tokens=tokenize.parser_tokenizer(extractedString)
	# convert the tokenized text into predicate logic representation
    tokenize.convert_to_predicate_logic(tokens) 
run()

