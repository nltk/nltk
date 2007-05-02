# Natural Language Toolkit: Relation Extraction
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Code for extracting triples of the form C{(subj, filler, obj)} from the ieer corpus,
after the latter has been converted to chunk format.
C{sub} and C{obj} are pairs of Named Entities, and C{filler} is the string of words occuring between C{sub} and C{obj} (with no intervening NEs).
Subsequent processing can try to identify interesting relations expressed in 
C{filler}.
"""

from nltk_lite.corpora import ieer, extract
from nltk_lite.parse import tree, Tree
from string import join
import re
    



def check_words(s):
    """
    Filter out strings which introduce unwanted noise.
    
    @param s: The string to be filtered
    @type s: C{string}
    @rtype: C{string} or C{None}
    """
    PUNC = re.compile(r'[._-]')
    if PUNC.search(s):
        return None
    else:
        return s

def check_type(tree, type=None):
    """
    Given a Named Entity (represented as a C{Tree}), check whether it 
    has the required type (i.e., check the tree's root node).
    
    @param tree: The candidate Named Entity
    @type tree: C{Tree}
    @rtype: C{bool}
     """
    if type is None:
        return True
    else:
        return tree.node == type
        
        
def ne_fillers(t, stype= None, otype=None):
    """
    Search through a chunk structure, looking for relational triples.
    These consist of
      - a Named Entity (i.e subtree), 
      - a string of words (i.e. leaves),
      - another Named Entity.
    To help debugging, we also identify a fourth item, C{rcon}, i.e., a few 
    words of right context immediately following the second Named Entity.
     
    Apart from the first and last, every Named Entity can occur as both the
    subject and the object of a triple.
    
    The parameters C{stype} and C{otype} can be used to restrict the 
    Named Entities to particular types (any of 'LOCATION', 'ORGANIZATION', 
    'PERSON', 'DURATION', 'DATE', 'CARDINAL', 'PERCENT', 'MONEY', 'MEASURE').
    
    @param t: a chunk structured portion of the C{ieer} corpus.
    @type t: C{Tree}
    @param stype: the type of the subject Named Entity (by default, all types are 
    admissible). 
    @type stype: C{string} or C{None}.
    @param otype: the type of the object Named Entity (by default, all types are 
    admissible). 
    @type otype: C{string} or C{None}.
    @return: a list of 4-tuples C{(subj, filler, obj, rcon)}.
    @rtype: C{list}
     
    """
    words = []
    window = 10
    #look for the next potential subject NE
    for d in t:
        if isinstance(d, Tree) and check_type(d, stype):
            subj = d
            # process the rest of the tree
            tail = t[t.index(d)+1:]
            for next in tail:
                # accumulate some words
                if not isinstance(next, Tree):
                    words.append(next)
                # next is another NE; it's a potential object
                else:
                    obj = next
                    if len(words) <= window:
                        filler = check_words(join(words))
                    else:
                        filler = None
                    if check_type(obj, otype) and filler:
                        pos = tail.index(obj)
                        rcon= tail[pos+1:pos+5]
                        triple = (subj, filler, obj, rcon)
                        try:
                            return [triple] + ne_fillers(tail, stype, otype)
                        except:
                            # nothing left to loop over -- ne_fillers(tail) returns None
                            return [triple]
                    # current triple is no good; carry on with the tail
                    else: 
                        return ne_fillers(tail, stype, otype)
    

def demo():
    """
    A demonstration showing how to look for pairs of ORGANIZATIONs
    and LOCATIONs, where there is some evidence that the former is located
    in the latter.
    
    The regexp does some simple matching against the fillers returned by 
    L{ne_fillers}, and could usefully be expanded. 
    It would also be helpful to merge together sequences of LOCATIONs in
    the object slot.
    """
    IN = re.compile(r'(.*(chain|store)\s+)?in|at|,')
    for d in ieer.dictionary():
        tree = d['text']
        rels = ne_fillers(tree, stype='ORGANIZATION', otype='LOCATION')
        if rels: 
            for (subj, filler, obj, rcon) in rels:
                if IN.match(filler):
                    print subj, filler, obj


if __name__ == '__main__':
    demo()


