######################################################################
##
##  What words occur in similar contexts?
##

from nltk import *
from collections import defaultdict

######################################################################
def build_context_map():
    """Build a dictionary mapping words in the brown corpus to lists
    of local lexical contexts, where a context is encoded as a tuple
    (prevword, nextword)."""
    context_map = defaultdict(list)
    for document in corpus.brown.files():
        words = corpus.brown.words(document)
        words = [word.lower() for word in words]
        for i in range(1, len(words)-1):
            prevword, word, nextword = words[i-1:i+2]
            context_map[word].append( (prevword, nextword) )
    return context_map

if 'context_map' not in globals():
    context_map = build_context_map()
    
######################################################################
def dist_sim(context_map, word, num=6):
    """Display words that appear in similar contexts to the given
    word, based on the given context map."""
    contexts = set(context_map.get(word, ()))
    fd = nltk.FreqDist(w for w in context_map
                           for c in context_map[w]
                             if c in contexts and w!=word)
    
    print(('Words similar to %r:' % word))
    print((' '.join('%10s' % wd for wd in list(fd.keys())[:num])))
    print((' '.join('%10s' % fd[wd] for wd in list(fd.keys())[:num])))

######################################################################
    
dist_sim(context_map, 'man')
dist_sim(context_map, 'woman')
dist_sim(context_map, 'walk')
dist_sim(context_map, 'in')
