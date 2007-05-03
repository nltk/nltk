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

from nltk_lite.corpora import ieer
from nltk_lite.parse import tree, Tree
from string import join
import re
from itertools import islice

    
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
      - a Named Entity (i.e subtree), called the 'subject' of the triple, 
      - a string of words (i.e. leaves), called the 'filler' of the triple,
      - another Named Entity, called the 'object' of the triple.
      
    To help in data analysis, we also identify a fourth item, C{rcon},
    i.e., a few words of right context immediately following the
    second Named Entity.
     
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
    return []


def relextract(stype, otype, pattern = None, rcontext = None):
    """
    Extract a relation by filtering the results of C{ne_fillers}.

    @param stype: the type of the subject Named Entity.
    @type stype: C{string}
    @param otype: the type of the object Named Entity.
    @type otype: C{string}
    @param pattern: a regular expression for filtering the fillers of
    retrieved triples.
    @type pattern: C{SRE_Pattern}
    @param rcontext: if C{True}, a few words of right context are added
    to the output triples.
    @type rcontext: C{bool}
    @return: generates 3-tuples or 4-tuples <subj, filler, obj, rcontext>.
    @rtype: C{generator}
    """
    for d in ieer.dictionary():
        tree = d['text']
        rels = ne_fillers(tree, stype=stype, otype=otype)
        if pattern:
            rels = [r for r in rels if pattern.match(r[1])]
        for (subj, filler, obj, rcon)  in rels:
            if rcontext:
                yield subj, filler, obj, rcon
            else:
                yield subj, filler, obj                

def demo():
    """
    A demonstration of two relations extracted by simple regexps:
    
      - in(ORG, LOC), and
      - has_role(PERS, ORG)

    """

    ############################################################
    # Example of in(ORG, LOC)
    ############################################################
    IN = re.compile(r'.*\bin\b(?!\b.+ing\b)')

    print "in(ORG, LOC):"
    for r in islice(relextract('ORGANIZATION', 'LOCATION', pattern = IN), 29, 39): 
        print r
    print
    
    ############################################################
    # Example of has_role(PERS, LOC)
    ############################################################  
    roles = """
    (.*(                   # assorted roles
    analyst|
    chair(wo)?man|
    commissioner|
    counsel|
    director|
    economist|
    editor|
    executive|         
    foreman|
    governor|
    head|
    lawyer|
    leader|
    librarian).*)|
    manager|
    partner|
    president|
    producer|
    professor|
    researcher|
    spokes(wo)?man|
    writer|
    ,\sof\sthe?\s*  # "X, of (the) Y"
    """
    ROLES = re.compile(roles, re.VERBOSE)

    print "has_role(PERS, ORG):"
    for r in islice(relextract('PERSON', 'ORGANIZATION', pattern = ROLES), 10): 
        print r
    print

if __name__ == '__main__':
    demo()


