# Natural Language Toolkit: Word Sense Disambiguation Algorithms
#
# Authors: Liling Tan <alvations@gmail.com>,
#          Dmitrijs Milajevs <dimazest@gmail.com>
#
# Copyright (C) 2001-2021 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.stem import PorterStemmer
ps = PorterStemmer()
lm = WordNetLemmatizer()


def stem(word):
    word=lm.lemmatize(word)
    if wordnet.synsets(ps.stem(word))==wordnet.synsets(word):
        return ps.stem(word)
    else:
        return word

def lesk(context_sentence, ambiguous_word, pos=None, synsets=None):
    """Return a synset for an ambiguous word in a context.
    :param iter context_sentence: The context sentence where the ambiguous word
         occurs, passed as an iterable of words.
    :param str ambiguous_word: The ambiguous word that requires WSD.
    :param str pos: A specified Part-of-Speech (POS).
    :param iter synsets: Possible synsets of the ambiguous word.
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.    
    This function is an implementation of the original Lesk algorithm (1986) [1].    
    Usage example::
        >>> lesk(['I', 'went', 'to', 'the', 'bank', 'to', 'deposit', 'money', '.'], 'bank', 'n')        
        Synset('savings_bank.n.02')
        
    [1] Lesk, Michael. "Automatic sense disambiguation using machine
    readable dictionaries: how to tell a pine cone from an ice cream
    cone." Proceedings of the 5th Annual International Conference on
    Systems Documentation. ACM, 1986.
    http://dl.acm.org/citation.cfm?id=318728
    """
    
    stopword = set(stopwords.words('english')) 
    context = set(context_sentence)
    context = [stem(w) for w in context] "Stemming each word"
    
    if synsets is None:
        synsets = wordnet.synsets(ambiguous_word)

    if pos:
        synsets = [ss for ss in synsets if str(ss.pos()) == pos]
        
    bag=[] 
    "Creating A bag of words ,for each synset , using its hypernyms,hyponyms definiation and examples"
    for ss in synsets:        
        gloss= set(ss.definition().split())  
        
        for s in ss.hypernyms():            
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]','', str(s.definition()))))
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]','', str(s.examples()))))            
        for s in ss.hyponyms():            
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]', '', str(s.definition()))))
            gloss=gloss.union(tokenized_sent(re.sub('[^a-zA-Z.\d\s]','', str(s.examples()))))  
            
        gloss = gloss.difference(stopword) "to remove stopwords" 
        gloss = list(gloss)
        for i in range(len(gloss)):            
            gloss[i]=str(stem(gloss[i]))   "Stemming each word"         
        gloss= set(gloss)  "to remove duplicates"      
        bag.append(gloss)  "Successful Creation for each synsets" 
        
    if not synsets:
        return None

    best_sense=synsets[0]
    max_overlap=0
    "Finding best Intersection -Stemming makes it faster"
    for k in range(len(synsets)):
        overlap = len(context.intersection(bag[k]))    
        if overlap > max_overlap:
            max_overlap = overlap
            best_sense = synsets[k]
            
    return best_sense "Returns best sense of the word"
