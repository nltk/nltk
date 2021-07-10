# Upgrading The LESK algorithm for word sense disambiguation using Wordnet Features 
# Author - anantdashpute@gmail.com


import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.stem import PorterStemmer
ps = PorterStemmer()
lm = WordNetLemmatizer()
import numpy as np
import re

functionwords = {'everyone',';','(',')','himself', 'it', 'his', 'everything', 'little', 'those', 'inside', 'on', 'off', 'over', 
                 'of', 'first', 'within', 'around', 'near', 'so', 'would', 'else', 'for', 'moreover', 'besides', 
                 'into', 'while', 'here', 'never', 'such', 'each', 'who', 'anyone', 'through', 'despite', 'might',
                 'that', 'will', 'anything', 'in', 'therefore', 'your', 'someone', 'a', 'few', 'do', 'second', 'down',
                 'themself', 'usually', 'one', 'with', 'any', 'onto', 'all', 'to', 'must', 'herself', 'him', 'most', 'much',
                 'but', 'along', 'should', 'my', 'an', 'no', 'against', 'before', 'could', 'now', 'there', 'meanwhile',
                 'be', 'instead', 'during', 'them', 'from', 'less', 'if', 'something', 'ones', 'he', 'two', 'sometimes',
                 'yours', 'have', 'however', 'otherwise', 'its', 'though', 'often', 'toward', 'than', 'their', 'then',
                 'half', 'least', 'although', 'nothing', 'her', 'next', 'as', 'across', 'always', 'many', 'how', 'anyway',
                 'when', 'this', 'behind', 'own', 'both', 'at', 'itself', 'last', 'hers', 'other', 'they', 'our',
                 'incidentally', 'may', 'whose', 'beside', 'without', 'about', 'she', 'some', 'where', 'can', 'and',
                 'because', 'every', 'theirs', 'twice', 'another', 'since', 'what', 'after', 'which', 'these', 'more',
                 'shall', 'by', 'several', 'the', 'or','he','she'}
def stem(word):
    word=lm.lemmatize(word)
    if wordnet.synsets(ps.stem(word))==wordnet.synsets(word):
        return ps.stem(word)
    else:
        return word
    
def findpos(word,sentence):    
    def change(i): 
        if i=='VB' or i=='VBD' or i=='VBG' or i=='VBN' or i=='VBP' or i=='VBZ' :
            return 'v'
        elif i== 'NN' or i=='NNS' or i=='NNP' or i=='NNPS' :
            return 'n'
        elif i== 'RB'or i=='RBR' or i=='RBS' or i=='RP':
            return 'r'
        elif i=='JJ'or i=='JJR'or i=='JJS':
            return 's'
        else:
            return 'a'
        
    t1 = nltk.word_tokenize(sentence)
    tag1 = np.array(nltk.pos_tag(t1))    
    for i in range(len(tag1)):
        tag1[i][1]=str(change(tag1[i][1]))
        if tag1[i][0]==word:
            pos=tag1[i][1]    
    return pos
        
def tokenized_sent(k):
        string=str(k)
        tokens = set(word_tokenize(string))
        tokens=list(tokens)
        for i in range(len(tokens)):
            tokens[i]=str(stem(tokens[i])) 
        tokens=set(tokens)        
        return tokens
    
def lesk(context_sentence, ambiguous_word, synsets=None):
    stopword = set(stopwords.words('english'))    
    stopword.update(functionwords) 
    context = tokenized_sent(context_sentence)
    context=set(context)    
    pos= findpos(ambiguous_word,context_sentence)    
    if synsets is None:
        synsets = wordnet.synsets(ambiguous_word)      
    if pos:
        synsets = [ss for ss in synsets if str(ss.pos()) == pos]    
    if not synsets:
        return None
    
    bag=[]    
    for ss in synsets:        
        gloss=set(tokenized_sent(ss.definition()))        
        for s in ss.hypernyms():            
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]','', str(s.definition()))))
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]','', str(s.examples()))))            
        for s in ss.hyponyms():            
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]', '', str(s.definition()))))
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]','', str(s.examples()))))  
            
        gloss = gloss.difference(stopword)
        gloss = list(gloss)
        for i in range(len(gloss)):            
            gloss[i]=str(stem(gloss[i]))            
        gloss= set(gloss)        
        bag.append(gloss)
    
    
    best_sense=synsets[0]
    max_overlap=0
    for k in range(len(synsets)):
        overlap = len(context.intersection(bag[k]))        
        if overlap > max_overlap:
            max_overlap = overlap
            best_sense = synsets[k]
            
    return best_sense
