######################################################################
##
##  What words tend to co-occur?
##

from nltk.probability import ConditionalFreqDist
from nltk.corpus import brown

######################################################################
def build_association_distribution():
    assoc = ConditionalFreqDist()
    
    # For each document in the "Brown Corpus"...
    for document in brown.files():
        words = brown.tagged_words(document)
        
        # For each word that's a noun...
        for index, (word, tag) in enumerate(words):
            if tag.startswith('N'):

                # Look at any nouns in the next 5 words...
                window = words[index+1:index+5]
                for (window_word, window_tag) in window:
                    if window_tag.startswith('N'):

                        # And add them to our freq. distribution
                        assoc[word].inc(window_word.lower())

    return assoc

if 'associations' not in globals():
    associations = build_association_distribution()
    
######################################################################
def assoc(word):
    print(('%20s -> %s' % (word, associations[word].max())))

######################################################################
assoc('man')
assoc('woman')
assoc('level')


