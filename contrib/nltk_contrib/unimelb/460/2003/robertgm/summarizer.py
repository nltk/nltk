#433-460 Project
#Robert Marshall
#robertgm

from nltk.tokenizer import *
from re import match
from os import listdir
from sys import stderr
from random import random

default_filelist = filter(lambda name: match(r'.*\.xml$', name), listdir('cmplg-xml'))

from handler import *
from sample import *

#For each file in the list, convert its abstract to an extract and save the result to a cache
def cache(filelist = default_filelist):

    #get the stop list
    create_stop_list()
    parser = make_parser()

    for filename in filelist:
        print 'processing file:', filename
        handler = TrainingDocHandler()
        parser.setContentHandler(handler)
        fp = open('cmplg-xml//'+filename)
        parser.parse(fp)

        #process this file, and write it to disk
        sample = TrainingSample(handler.summary, handler.text)
        sample.write('cache//'+filename)

#train using the given measures on the given files
def train(measures = [SentenceLength(), FixedPhrase(), Paragraph()],
          filelist = default_filelist):

    document_counts = dict()
    summary_counts = dict()

    #initialise all our counts at 1 like the good Bayesians that we are
    for measure in measures:
        document_counts[measure] = FreqDist()
        summary_counts[measure] = FreqDist()    
        for feature in measure.feature_list:
            document_counts[measure].inc(feature)
            summary_counts[measure].inc(feature)            

    print 'training...'

    #for each file
    for filename in filelist:

        print 'processing', filename
        #load the cached version
        sample = TrainingSample(filename='cache//'+filename)
        #train with this sample
        training_data = sample.train(measures)

        #for each measure
        for measure in measures:
            (document_data, summary_data) = training_data[measure]

            #record the number of occurrences of each feature
            for feature in measure.feature_list:       
                for i in range(0, document_data.count(feature)):
                    document_counts[measure].inc(feature)
                for i in range(0, summary_data.count(feature)):
                    summary_counts[measure].inc(feature)

    #print the results
    for measure in measures:
        print measure
        for feature in measure.feature_list:
            print feature
            print "P(F) =", document_counts[measure].freq(feature)
            print "P(F|S) =", summary_counts[measure].freq(feature)
        print
    for measure in measures:
        print measure
        for feature in measure.feature_list:
            print feature
            print "P(F) =", document_counts[measure].freq(feature)
            print "P(F|S) =", summary_counts[measure].freq(feature)
        print

    return (document_counts, summary_counts)

#generate a summary of the given length for this document, using the training data provided
def summarize(document, length, measures, (document_counts, summary_counts)):

    #for each paragraph
    sentence_scores = dict()
    for p in range(0, len(document)):        
       
        paragraph = document[p]

        #and each sentence
        for s in range(0, len(paragraph.type())):            
            sentence = paragraph.type()[s]

            #multiply the score by P(F|S); divide by P(F)
            sentence_scores[(p, s)] = 1
            for measure in measures:
                sentence_scores[(p, s)] *= summary_counts[measure].freq(measure._evaluate_sentence(document, paragraph, s))
                sentence_scores[(p, s)] /= document_counts[measure].freq(measure._evaluate_sentence(document, paragraph, s))
    
    extract = []
    #get the required number of sentences
    for i in range(0, length):

        #find out the sentence with the highest score
        max_score = 0
        max_loc = (0, 0)
        for loc in sentence_scores:
            if sentence_scores[loc] > max_score:
                max_score = sentence_scores[loc]
                max_loc = loc

        #add it to the extract, and remove it from the sentence list
        extract.append(max_loc)
        del sentence_scores[max_loc]

        #print it
        paragraph = document[max_loc[0]]
        sentence = paragraph.type()[max_loc[1]].type()        
        print sentence, max_score

    return extract

    
def cross_validate(measures = [SentenceLength(), FixedPhrase(), Paragraph()],
                   filelist = default_filelist, n_folds = 10):
    score = 0
    count = 0
    
    for i in range(0, n_folds):

        #we need to create separate lists of training and testing files
        training_files = []
        testing_files = []

        #firstly make them all training files
        for file in filelist:
            training_files.append(file)

        #make 1/3 of the training files into testing files
        n_tests = len(training_files)/3
        for j in range(0, n_tests):

            #get a random file
            file = training_files[int(random()*len(training_files))]

            #shift it from the training set to the testing set
            training_files.remove(file)
            testing_files.append(file)

        #train on the training data
        training_data = train(measures, training_files)

        #test on the testing data
        for filename in testing_files:

            #load the file up
            sample = TrainingSample(filename='cache//'+filename)
            print 'extracting from', filename

            #summarize it
            extract = summarize(sample.text, len(sample.extract), measures, training_data)

            #for each sentence in the (real) extract
            for sentence in sample.extract:

                #get its location
                s = sentence.loc().start()
                p = sentence.loc().source().start()

                #see if its in the generated extract
                if (p, s) in extract:
                    score+=1
                    
                count+=1

            print

    #print the total score (after all cross-validation)
    print 'score:',score,'of',count
    print float(score)/count


def common_phrases(filelist = default_filelist):
    
    n = 4    
    counts = dict()
    for i in range(2, n+1):
        counts[i] = FreqDist()
    
    for filename in filelist:
        
        print 'processing', filename
        sample = TrainingSample(filename='cache//'+filename)

        parser = make_parser()
        handler = TrainingDocHandler()
        parser.setContentHandler(handler)
        fp = open('cmplg-xml//'+filename)
        parser.parse(fp)
        
        tokens = []
        for sentence in word_tokenizer.tokenize(handler.summary):
            tokens += [lower(word.type()) for word in sentence_tokenizer.tokenize(sentence.type())]
       
        #loop through the context sizes
        for i in range(2, n+1):
                                                                                
            #the context is initially i+1 <S> tokens
            phrase = ('<S>',).__mul__(i)
                                                                                
            #for each token in the input data - we assume it is in order still
            for token in tokens:
                #record that this word occurred in the current context
                counts[i].inc(phrase)
                
                #update it as we move through the training data
                phrase = phrase[1:len(phrase)]+(token,)
                    
    print counts
    
    #Make a list of all the words in our training set, along with
    #the probability of them occurring in this context

    for i in range(2, n+1):
        print 'calculating phrases of length', i
        phrases = [ (counts[i].count(phrase), phrase)for phrase in counts[i].samples()]

        for j in range(0, 20):

            while 1:
                maxphrase = max(phrases)
                phrases.remove(maxphrase)
                if not '<S>' in maxphrase[1]: break
            
            print maxphrase
   
#list all of the sentences of useful length which exactly match between the abstracts and documents
def exact_matches(filelist = default_filelist):
    
    parser = make_parser()
    n_yes = 0
    n_total = 0

    #go through all the xml files
    for filename in filelist:
        if match(r'.*\.xml$', filename):

            #read the file
            handler = TrainingDocHandler()
            parser.setContentHandler(handler)            
            fp = open('cmplg-xml//'+filename,'r')
            parser.parse(fp)
            
            summary = sentence_tokenizer.tokenize(handler.summary)

            #loop through each paragraph
            for paragraph in handler.text:
                sentence_list = [s.type() for s in sentence_tokenizer.tokenize(paragraph)]
                #and each sentence
                for sentence in [t.type() for t in summary]:
                    #look for sentences of useful length
                    if sentence in sentence_list and len(sentence)>2 :
                        print 'found:', sentence
                        print 'in:', filename
                        print
                        n_yes+=1
                        
            n_total += len(summary)
	
    print 'sentences from summary contained in document:', n_yes, 'of', n_total

def read_file(filename):
    fp = open(filename)
    text = fp.read()

    paragraph_list = RETokenizer('\n\n', negative=1).tokenize(text)

    document = []

    for i in range(0, len(paragraph_list)):
        paragraph_text = paragraph_list[i].type()

        document.append(Token(sentence_tokenizer.tokenize(paragraph_text), Location(i)))

    return document


