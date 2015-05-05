# Natural Language Toolkit: Word2Vec Wrapper through Gensim
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
Supporting code to extract part of the pre-trained model (GoogleNews-vectors-negative300.bin.gz) 
from  https://code.google.com/p/word2vec/
 """
 
from __future__ import absolute_import, division, unicode_literals
import gensim
from gensim.models.word2vec import Word2Vec

if __name__ == '__main__':
    # Load the C pre-trained model file 
    model = Word2Vec.load_word2vec_format('GoogleNews-vectors-negative300.bin.gz', binary = True);
    
    # Only output word that appear in the Brown corpus 
    from nltk.corpus import brown
    dict = {}  
    for word in brown.words():
        dict[word] = 1 
    print (len(dict.keys()))
    
    # Only print out the model that contain word in dict
    out_file = 'pruned.word2vec.txt'
    f = open(out_file,'wb')
    count = 0
    for key in dict.keys():
        try:
            temp = model[key]
            count +=1
        except KeyError:
            print (' Not containing key ' + key)
                       
    f.write(str(count) + ' ' + str(len(model['word'])) + '\n')
    
    for key in dict.keys():
        try:
            f.write(key + ' ' + ' '.join(str(value) for value in model[key]) + '\n')
        except KeyError:
            pass
    
    f.close()
    
    # Reload the model from text file 
    new_model = Word2Vec.load_word2vec_format(out_file, binary = False);
    
    # Save it as the Gensim model
    gensim_model = "pruned.word2vec.bin" 
    new_model.save(gensim_model)
    
    # Load the model 
    very_new_model = gensim.models.Word2Vec.load(gensim_model)
    
    # Test it 
    very_new_model.most_similar(positive=['king','woman'], negative=['man'], topn=1)
    