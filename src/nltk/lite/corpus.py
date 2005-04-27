import sys, os.path, re
from tokenizer import whitespaceTokenize

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
            slash = t.rfind('/')
            if slash >= 0:
                yield (t[:slash], t[slash+1:])
            else:
                yield (t, None)


def demo():
    """
    Demonstrate corpus access for each of the defined corpora.
    """
    set_basedir('/data/nltk/data/')   # location for modified corpus
    for token in brown('a'):
        print token
    
if __name__ == '__main__':
    demo()

# create modified corpus with "cat ca* > a" etc
