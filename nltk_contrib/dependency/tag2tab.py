"""
Utilities for converting chunked treebank into format that can be 
input to Nivre's MaltParser.
"""
from nltk.corpora import get_basedir
from nltk import tokenize
from itertools import islice
import os

def tag2tab(s, sep='/'):
    loc = s.rfind(sep)
    if loc >= 0:
            word = s[:loc]
            tag = s[loc+1:]
            tag = tag.replace('(', '-LRB-').replace(')', '-RRB-')
            return "%s\t%s\n" % (word, tag)
    else:
            return (s, None)

def tabtagged(files = 'chunked', basedir= None):
    """
    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @return: iterator over lines in Malt-TAB input format
    """       
    if type(files) is str: files = (files,)

    if not basedir: basedir = get_basedir()

    for file in files:
        path = os.path.join(get_basedir(), "treebank", file)
        f = open(path).read()

        for sent in tokenize.blankline(f):
            l = []
            for t in tokenize.whitespace(sent):
                if (t != '[' and t != ']'):
                    l.append(tag2tab(t))
            #add a blank line as sentence separator
            l.append('\n')
            yield l

def demo():
    from nltk.corpora import treebank
    #f = open('ptb_input.tab', 'w')
    #s = ''
    for sent in islice(tabtagged(), 3):
        for line in sent:
            print line,
            #s += ''.join(sent)
    #print >>f, s
    #f.close()
    


if __name__ == '__main__':
    demo()

