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

from nltk.corpora import ieer, conll2002
from nltk.parse import tree, Tree
from nltk.tag import tag2tuple
from string import join
import re
from itertools import islice

ne_types = {'ieer': ['LOCATION', 'ORGANIZATION', 'PERSON', 'DURATION', 
                    'DATE', 'CARDINAL', 'PERCENT', 'MONEY', 'MEASURE'],
            'conll2002': ['LOC', 'PER', 'ORG'],
            'conll2002-ned': ['LOC', 'PER', 'ORG'],
            'conll2002-esp': ['LOC', 'PER', 'ORG']
                }
                    

short2long = dict(LOC = 'LOCATION', ORG = 'ORGANIZATION', PER = 'PERSON')
long2short = dict(LOCATION ='LOC', ORGANIZATION = 'ORG', PERSON = 'PER')

corpora = {
    'ieer': (d[key] for key in ['text','headline'] for d in ieer.dictionary()),
    'conll2002': (tree for tree in conll2002.ne_chunked()),
    'conll2002-ned': (tree for tree in conll2002.ne_chunked(files = ['ned.train'])),
    'conll2002-esp': (tree for tree in conll2002.ne_chunked(files = ['esp.train']))
}

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
    
def _tuple2tag(item):
    if isinstance(item, tuple): 
        (token, tag) = item
        return "".join(token + "/" + str(tag))
    else: return item
          
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
                    next = _tuple2tag(next)
                    #if isinstance(next, tuple): 
                        #(token, tag) = next
                        #next = "".join(token + "/" + str(tag))
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
                        rcon= [_tuple2tag(item) for item in tail[pos+1:pos+5]]
                        triple = (subj, filler, obj, rcon)
                        try:
                            return [triple] + ne_fillers(tail, stype, otype)
                        except:
                            # nothing left to loop over -- ne_fillers(tail) returns None
                            return [triple]
                    # current triple is no good; carry on with the tail
                    else: 
                        return ne_fillers(tail, stype, otype)
    # nothing to loop over
    return []

def _expand(type):
    try:
        return short2long[type]
    except KeyError:
        return ''

def relextract(stype, otype, corpus = 'ieer', pattern = None, rcontext = None):
    """
    Extract a relation by filtering the results of C{ne_fillers}.

    @param trees: the syntax trees to be processed
    @type trees: list of C{Tree}
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
    try:
        trees = corpora[corpus]
    except KeyError:
        print "corpus not recognized: '%s'" % corpus
    
    if stype not in ne_types[corpus]:
        if _expand(stype) in ne_types[corpus]:
            stype = _expand(stype)
        else:
            raise ValueError, "your value for the subject type has not been recognized: %s" % stype
    if otype not in ne_types[corpus]:
        if _expand(otype) in ne_types[corpus]:
            otype = _expand(otype)
        else:
            raise ValueError, "your value for the object type has not been recognized: %s" % otype

    for tree in trees:
        rels = ne_fillers(tree, stype=stype, otype=otype)
        if pattern:
            rels = [r for r in rels if pattern.match(r[1])]
        for (subj, filler, obj, rcon)  in rels:
            if rcontext:
                yield subj, filler, obj, rcon
            else:
                yield subj, filler, obj                
        
def _shorten(type):
    try:
        return long2short[type]
    except KeyError:
        return type

def _show(item, tags=None):
    if isinstance(item, Tree):
        label = _shorten(item.node)
        try:
            words = [word for (word, tag) in item.leaves()]
        except ValueError:
            words = item.leaves()
        text = join(words)
        return '[%s: %s]' % (label, text)
    elif isinstance(item, list):
        return join([_show(e) for e in item])
    else:
        if tags:
            return item
        else:
            item = tag2tuple(item)
            return item[0]

def show_tuple(t):
    """
    Utility function for displaying tuples in succinct format.
    
    @param t: a (subj, filler, obj) tuple (possibly with right context as a fourth item).
    @type t: C{tuple}
    """
    l = [_show(t[0]), t[1], _show(t[2])]
    if len(t) > 3:
        l.append(_show(t[3]))
        return '%s %s %s (%s...' % tuple(l)
    return '%s %s %s' % tuple(l)
    
def demo():
    
    ieer_trees = [d['text'] for d in ieer.dictionary()]
    """
    A demonstration of two relations extracted by simple regexps:
       - in(ORG, LOC), and
      - has_role(PERS, ORG)
    """
    ############################################
    # Example of in(ORG, LOC)
    ############################################
    IN = re.compile(r'.*\bin\b(?!\b.+ing\b)')

    print "in(ORG, LOC):"
    print "=" * 30
    for r in islice(relextract('ORG', 'LOC', pattern = IN), 29, 39): 
       print show_tuple(r)
    print
    
    ############################################
    # Example of has_role(PER, LOC)
    ############################################
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

    print "has_role(PER, ORG):"
    print "=" * 30
    for r in islice(relextract('PER', 'ORG', pattern = ROLES, rcontext = True), 10): 
        print show_tuple(r)
    print
    
    ############################################
    # Show what's in the IEER Headlines
    ############################################
    
    print "NER in Headlines"
    print "=" * 30
    for d in ieer.dictionary():
        tree = d['headline']
        for r in ne_fillers(tree):
            print show_tuple(r[:-1])
    print
        
    ############################################
    # Dutch CONLL2002: take_on_role(PER, ORG
    ############################################
    
    vnv = """
    (
    is/V|
    was/V|
    werd/V|
    wordt/V
    )
    .*
    van/Prep
    """
    VAN = re.compile(vnv, re.VERBOSE)
     
    print "van(PER, ORG):"
    print "=" * 30
    for r in relextract('PER', 'ORG', corpus='conll2002-ned', pattern = VAN): 
        print show_tuple(r)
    print
    
    ############################################
    # Spanish CONLL2002: (PER, ORG)
    ############################################
    
    de = """
    .*
    (
    de/SP|
    del/SP
    )
    """
    DE = re.compile(de, re.VERBOSE)
     
    print "de(ORG, LOC):"
    print "=" * 30
    for r in islice(relextract('ORG', 'LOC', corpus='conll2002-esp', pattern = DE), 10): 
        print show_tuple(r)
    print
    

if __name__ == '__main__':
    demo()


