# Natural Language Toolkit: Word2Vec Wrapper through Gensim
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Word2Vec Wrapping through Gensim. Allowing 
- Training new model
- Load the pre-trained model from nltk.corpus 
- Run some demo tasks  
"""
from __future__ import absolute_import, division, unicode_literals
import gensim



class Word2Vec():
    """
    A Word2Vec Wrapper through Gensim. See demo() for examples.  
    """
    
    def __init__(self):
        self.model = None
        
    
    def train(self, sentences, sg=1, min_count=5, size=100, window=5, thread=1,  hs=1, negative=0, iteration=1 ):
        """
        :param sentences: list of sentences for training 
        :type sentences: iter(list(str)) 
        :param sg: defines the training algorithm. By default (sg=1), skip-gram is used. Otherwise, cbow is employed.
        :param min_count:  ignore all words with total frequency lower than this.
        :param size:  is the dimensionality of the feature vectors.
        :param window:  is the maximum distance between the current and predicted word within a sentence.
        :param thread: Number of thread for training. Noteed that Cython is needed for multiple thread training. 
        :param hs: if 1 (default), hierarchical sampling will be used for model training (else set to 0).
        :param negative: if > 0, negative sampling will be used, the int for negative specifies how many "noise words" should be drawn (usually between 5-20). If negative > 0, hs must set to 0.  
        :param iteration: number of iterations (epochs) over the corpus.
        """
        _model = gensim.models.Word2Vec(sentences,min_count= min_count, size = size, workers = thread, window = window,
                                       hs = hs, negative = negative, iter = iteration, sg=sg)
        self.model = _model;

    def _check_model(self):
        if self.model is None : 
            raise ValueError(" Need to train or load the model ")
        
    def save_model(self, file_name):
        """
        Save the model using pickle
        """ 
        self._check_model()
        self.model.save(file_name)
        
    def load_model(self,file_name):
        """
        Load the saved model
        """ 
        self.model = gensim.models.Word2Vec.load(file_name)

    def get_vector(self, word):
        """
        :return : Get the vector representation of the word. None if the word is missing from the model.  
        """ 
        self._check_model()
        
        try:
            return self.model[word]
        except KeyError:
            return None   
    
    def similarity(self,word1,word2):
        """
        :return: the cosine similarity of two words. -1 if any word is missing from the model.   
        """ 
        self._check_model()
        
        try:
            return self.model.similarity(word1,word2);
        except KeyError:
            return -1  
        
    def most_similar(self, positive=[], negative=[], topn=10):
        """
        :param positive: the list of positive words contribute positively towards the similarity.
        :param negative: the list of negative words contribute negatively toward the similarity. 
        :param topn: return n result with the score.   
        """
        self._check_model()
        try:
            return self.model.most_similar(positive, negative, topn)
        except KeyError:
            return None 
    
        
def demo():
    ####### DEMO TRAINING ####### #######
    
    from nltk.corpus import brown
    w2v = Word2Vec()
    # Train the model 
    w2v.train(brown.sents())
    # Save model 
    w2v.save_model("brown.embedding")
    
    # Load the model 
    w2v.load_model("brown.embedding")
    
    # Get vector representation 
    print(w2v.get_vector("university"))
    # For unknown word, the result is None 
    print(w2v.get_vector("universita"))
    # Similarity between 2 words 
    print(w2v.similarity("university", "school"))
    
    ####### DEMO USING PRE-TRAINED MODEL ####
    # The pre-trained model is part of the model trained on 100 billion words, pruned for most common words. 
    
    from nltk.corpus import word_embedding
    w2v.load_model(word_embedding)
            
    # top-n most similar words 
    print(w2v.most_similar(positive=['university'], topn = 10))
    
    # Answer the question : A is to B as C is to ? 
    # e.g. man is to king as woman is to ?  
    print(w2v.most_similar(positive=['woman','king'], negative=['man'], topn = 1))
    
    #another example: Berlin is to Germany as Paris is to ?  
    print(w2v.most_similar(positive=['Paris','Germany'], negative=['Berlin'], topn = 1))
    
if __name__ == '__main__':
    demo()
