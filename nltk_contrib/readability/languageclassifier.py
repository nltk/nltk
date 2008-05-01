#!/usr/bin/python
# -*- coding: utf-8 -*- 
# Sets the encoding to utf-8 to avoid problems with æøå
import glob
import re
import random
import math
import pickle
import os

from nltk.corpus import stopwords

from urlextracter import URLextracter
from sgmllib import *

class NaiveBayes(object):
       
    p_word_given_lang = {}
    
    training_files = []
    test_files = []
    candidate_languages = []

    def __init__(self):
        self.nor_stopwords = {}
        for word in stopwords.words('norwegian'):
            self.nor_stopwords[word] = True
            
        self.eng_stopwords = {}
        for word in stopwords.words('english'):
            self.eng_stopwords[word] = True
            
        self.load(os.path.join("files","lang_data.pickle"))

     
    """
    load pickled training results
    picklepath is the local path to your picklefile
    """        
    def load(self,picklepath):
        try:
            p = open(picklepath, 'rb')
            data = pickle.load(p)
            self.p_word_given_lang = data["p_word_given_lang"]
            self.candidate_languages = data["canidate_languages"]
            self.p_lang = data["p_lang"]
            self.vocabulary = data["vocabulary"]
        except IOError:
            self.p_word_given_lang = {}
            print "Nothing to load here!"
        
        
    """
    Train the classifier with data placed 
    in a folder named as the related language.
    Example: /path/to/files/eng/file01.txt
    """    
    def train(self, path):
        # Setup
        data_files = glob.glob(path + "/*/*")
        random.shuffle(data_files)
        
        self.training_files = data_files[0:300]
        self.test_files = data_files[300:]
        
        self.files = {}
        self.p_lang = {}
        
        # Calculate P(H)
        for file in self.training_files:
            values = file.split('/')
            lang = values[-2]
        
            if not self.p_lang.has_key(lang):
                self.p_lang[lang] = 0.0
            
            self.p_lang[lang] += 1.0
            
            if not self.files.has_key(lang):
                self.files[lang] = []
            
            f = open(file, 'r')
            self.files[lang] += f.read().replace("\n", " ").replace(".", "").split(" ")
            f.close()
            
        # Calculate probabilities
        for lang in self.p_lang.keys():
            self.p_lang[lang] /= len(self.training_files)
            
        self.vocabulary = self.__createVocabulary(self.files)
        
        # Calculate P(O | H) 
        p_word_given_lang = self.p_word_given_lang
        for lang in self.files.keys():
            p_word_given_lang[lang] = {}
            
            for word in self.vocabulary[lang].keys():
                p_word_given_lang[lang][word] = 1.0
            
            for word in self.files[lang]:
                if self.vocabulary[lang].has_key(word):
                    p_word_given_lang[lang][word] += 1.0
                    
            for word in self.vocabulary[lang].keys():
                p_word_given_lang[lang][word] /= len(self.files[lang]) + len(self.vocabulary[lang])
                
        print "Training finished...(training-set of size %d)" % len(self.training_files)
        self.p_word_given_lang = p_word_given_lang
        self.candidate_languages = self.files.keys()
        
        # Save result as a file
        output = open(os.path.join("files","lang_data.pickle"),'wb')
        data = {}
        data["p_word_given_lang"] = p_word_given_lang
        data["canidate_languages"] = self.files.keys()
        data["p_lang"] = self.p_lang
        data["vocabulary"] = self.vocabulary
        pickler = pickle.dump(data, output, -1)
        output.close()   
    
    """
    Filter out the words we're not interessted in
    and return a dictionary with all remaining words
    sorted by language.
    Example: vocabulary[eng] = {'lazy','fox',...}
    """
    def __createVocabulary(self, files):
        # Count number of occurance of each word
        word_count = {}
        for lang in files.keys():
            for word in files[lang]:
                if not word_count.has_key(word):
                    word_count[word] = 0
                word_count[word] += 1
        
        vocabulary = {}
        vocabulary['eng'] = {}
        vocabulary['no'] = {}
        for word in word_count.keys():
            if word_count[word] > 2:
                if word != '':
                    if not word in self.nor_stopwords:
                        vocabulary['no'][word] = True
                    if not word in self.eng_stopwords:
                        vocabulary['eng'][word] = True
        return vocabulary
    
    
    """
    Test the accuracy of the classifier.
    Provide test files as list or path.
    The path must be on the same form as when training.
    """
    def testAccuracy(self,test_files = ""):
        
        if test_files == "":
            print "No test files given"
            return
        elif os.path.isdir(str(test_files)):
            self.test_files = glob.glob(test_files + "/*/*")
            random.shuffle(self.test_files)
        else:
            self.test_files = test_files
  
        errors = 0.0
        total = 0.0
        
        # Use if test_files is provided as path
        #test_files = glob.glob(path + "/*/*")
        #random.shuffle(test_files)
        
        
        for file in self.test_files:
            values = file.split(os.sep)
            true_lang = values[-2]

            f = open(file, "r")    
            file_to_be_classified = f.read().replace("\n", " ").replace(".", "").split(" ")
            f.close()
            
            # Finds group with max P(O | H) * P(H)
            max_lang = 0
            max_p = 1
            for candidate_lang in self.candidate_languages:
                # Calculates P(O | H) * P(H) for candidate group
                p = math.log(self.p_lang[candidate_lang])
                for word in file_to_be_classified:
                    if self.vocabulary[candidate_lang].has_key(word):
                        p += math.log(self.p_word_given_lang[candidate_lang][word])
        
                if p > max_p or max_p == 1:
                    max_p = p
                    max_lang = candidate_lang
        
            total += 1.0
            if true_lang != max_lang:
                errors += 1.0
        print "Classifying finished...(test-set of size %d)" % len(self.test_files)
        print "Errors %d" % errors
        print "Total %d" % total
        print "Accuracy: %.3f" % (1.0 - errors/total)
    
    def classifyText(self, text):
        max_lang = 0
        max_p = 1
        for candidate_lang in self.candidate_languages:
            # Calculates P(O | H) * P(H) for candidate group
            p = math.log(self.p_lang[candidate_lang])
            words = text.split(' ')
            unknown_words = []
            known_words = []
            for word in words:
                if self.vocabulary[candidate_lang].has_key(word):
                    p += math.log(self.p_word_given_lang[candidate_lang][word])
                    if word not in known_words:
                        known_words.append(word)
                else:
                    if word not in unknown_words:
                        unknown_words.append(word)
            if p > max_p or max_p == 1:
                max_p = p
                max_lang = candidate_lang
        
        percent = (float(len(known_words)) / float(len(unknown_words)))
        # return unknown if the ratio of known words is less or equal to 0.25
        if percent <= 0.25:        
            max_lang = "unknown"
        
        return max_lang
    
    def classifyURL(self, url):
        ue = URLextracter(url)
        print 'Classifying %s' % url
        content = ue.output() 
        content = re.sub(r"[^a-zA-ZæøåÆØÅ]", " ", content)
        content = content.strip()
        return self.classifyText(content)
    
    def handle_decl(self,data):
        pass

    def report_unbalanced(self,tag):
        pass
    
    def demo(self):
        print "Demo of language classifier"
        print "=" * 40
        nb = NaiveBayes()
        nb.load(os.path.join("files","lang_data.pickle"))
        
        print "Classifying plain text(10 first sentences from \"nltk.corpus.abc.sents\")"
        print "=" * 40
        text = ""
        import nltk.corpus
        sents = nltk.corpus.abc.sents()
        for words in sents[0:10]:
            text+= " ".join(words) + "\n"
        print text
        print "=" * 40
        print "Languages is: %s" % nb.classifyText(text)
        
        print "\n"
        print "Classifying 10 URLs"
        print "=" * 40
        
        lang = nb.classifyURL("http://harvardscience.harvard.edu/")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://vg.no")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://bbc.co.uk")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://startsiden.no")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://news.com")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://www.munimadrid.es")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://www.welt.de/")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://www.news.pl/")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://www.ekstrabladet.dk/")
        print "-->language: %s \n" % lang
        lang = nb.classifyURL("http://www.gazzetta.it/")
        print "-->language: %s \n" % lang      
    demo = classmethod(demo)
    
def demo():
    NaiveBayes.demo()
    
if __name__=="__main__":
    NaiveBayes.demo()    
    
    
