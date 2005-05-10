import sys, os.path, re
from tokenizer import whitespaceTokenize
from tagger import tag2tuple

#################################################################
# Base Directory for Corpora
#################################################################

def set_basedir(path):
    """
    Set the path to the directory where NLTK looks for corpora.
    
    @type path: C{string}
    @param path: The path to the directory where NLTK should look for
        corpora.
    """
    global _BASEDIR
    _BASEDIR = path

def get_basedir():
    """
    @return: The path of the directory where NLTK looks for corpora.
    @rtype: C{string}
    """
    return _BASEDIR

def corpus_path(name):
    """
    Return the full path to an installed corpus

    @param name: The name of the corpus directory
    @type name: C{string}
    @return: The path to the directory where the corpus is stored
    @rtype: C{string}
    """
    corpus_dir = os.path.join(get_basedir(), name)
    if not os.path.isdir(corpus_dir):
        raise IOError('%s is not installed' % name)
    return corpus_dir


# Find a default base directory.
if os.environ.has_key('NLTK_CORPORA'):
    set_basedir(os.environ['NLTK_CORPORA'])
elif sys.platform.startswith('win'):
    if os.path.isdir(os.path.join(sys.prefix, 'nltk')):
        set_basedir(os.path.join(sys.prefix, 'nltk'))
    elif os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk')):
        set_basedir(os.path.join(sys.prefix, 'lib', 'nltk'))
    else:
        set_basedir(os.path.join(sys.prefix, 'nltk'))
elif os.path.isdir('/usr/lib/nltk'):
    set_basedir('/usr/lib/nltk')
elif os.path.isdir('/usr/local/lib/nltk'):
    set_basedir('/usr/local/lib/nltk')
elif os.path.isdir('/usr/share/nltk'):
    set_basedir('/usr/share/nltk')
else:
    set_basedir('/usr/lib/nltk')


def brown(files = list('abcdefghjklmnpr')):

    """
    Read tokens from the Brown Corpus.

    Brown Corpus: A Standard Corpus of Present-Day Edited American
    English, for use with Digital Computers, by W. N. Francis and
    H. Kucera (1964), Department of Linguistics, Brown University,
    Providence, Rhode Island, USA.  Revised 1971, Revised and
    Amplified 1979.  Distributed with NLTK with the permission of the
    copyright holder.  Source: http://www.hit.uib.no/icame/brown/bcm.html

    The Brown Corpus is divided into the following files:

    a. press: reportage
    b. press: editorial
    c. press: reviews
    d. religion
    e. skill and hobbies
    f. popular lore
    g. belles-lettres
    h. miscellaneous: government & house organs
    j. learned
    k: fiction: general
    l: fiction: mystery
    m: fiction: science
    n: fiction: adventure
    p. fiction: romance
    r. humor
    """       

    path = corpus_path('brown')

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        f = open(os.path.join(path, file))
        for t in whitespaceTokenize(f):
            yield tag2tuple(t)


from tokenizer import blanklineTokenize
import tree

def treebank_parsed(files = 'wsj_00_parsed'):

    """
    Read trees from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: parsed data from Wall Street Journal for 1650 sentences, e.g.:

    ( (S 
      (NP-SBJ 
        (NP (NNP Pierre) (NNP Vinken) )
        (, ,) 
        (ADJP 
          (NP (CD 61) (NNS years) )
          (JJ old) )
        (, ,) )
      (VP (MD will) 
        (VP (VB join) 
          (NP (DT the) (NN board) )
          (PP-CLR (IN as) 
            (NP (DT a) (JJ nonexecutive) (NN director) ))
          (NP-TMP (NNP Nov.) (CD 29) )))
      (. .) ))
    """       

    path = corpus_path('treebank')

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        s = open(os.path.join(path, file)).read()
        for t in blanklineTokenize(s):
            yield tree.parse(t)


def treebank_chunked(files = 'wsj_00_chunked'):

    """
    Read chunks from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: chunked data from Wall Street Journal for 1650 sentences, e.g.:

    [ Pierre/NNP Vinken/NNP ]
    ,/, 
    [ 61/CD years/NNS ]
    old/JJ ,/, will/MD join/VB 
    [ the/DT board/NN ]
    as/IN 
    [ a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ]
    ./.
    """       

    path = corpus_path('treebank')

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        s = open(os.path.join(path, file)).read()
        for t in blanklineTokenize(s):
            yield tree.chunk(t)


def treebank_tagged(files = 'wsj_00_tagged'):

    """
    Read tagged tokens from the Penn Treebank corpus sample.

    This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
    available under fair use for the purposes of illustrating NLTK
    tools for tokenizing, tagging, chunking and parsing.  This data is
    for non-commercial use only.

    Contents: tagged data from Wall Street Journal for 1650 sentences, e.g.:

    Pierre/NNP Vinken/NNP ,/, 61/CD years/NNS old/JJ ,/, will/MD join/VB 
    the/DT board/NN as/IN a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ./.
    """       

    path = corpus_path('treebank')

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        f = open(os.path.join(path, file)).read()
        for sent in blanklineTokenize(f):
            l = []
            for t in whitespaceTokenize(sent):
                l.append(tag2tuple(t))
            yield l


def demo():
    """
    Demonstrate corpus access for each of the defined corpora.
    """
    set_basedir('/home/sb/nltk/data/')   # location for modified corpus
#    set_basedir('/data/nltk/data/')   # location for modified corpus

    i=0
    for token in brown(files='a'):
        print token
        i+=1
        if i>50: break

    i=0
    for tree in treebank_parsed():
        print tree.pp()
        i+=1
        if i>3: break

    i=0
    for tree in treebank_chunked():
        print tree.pp()
        i+=1
        if i>3: break
    
    i=0
    for token in treebank_tagged():
        print token()
        i+=1
        if i>3: break
    
if __name__ == '__main__':
    demo()

# create modified corpus with "cat ca* > a" etc


