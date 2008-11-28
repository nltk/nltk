"""
Utilities for converting chunked treebank into format that can be 
input to Nivre's MaltParser.
"""
from nltk import tokenize
from itertools import islice
import os
from deptree import DepGraph
from nltk.stem.wordnet import WordNetLemmatizer 

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

    if not basedir: basedir = os.environ['NLTK_DATA']

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

def conll_to_depgraph(input_str, stem=False, verbose=False):
    if stem: 
        stemmer = WordNetLemmatizer()

    tokenizer = tokenize.TabTokenizer()
    depgraph_input = ''
    for line in _normalize(input_str).split('\n'):
        tokens = tokenizer.tokenize(line.strip())
        if len(tokens) > 1:
            word = tokens[1]
            if stem:
                word_stem = stemmer.lemmatize(word)
                if word_stem:
                    word = word_stem
            depgraph_input += '%s\t%s\t%s\t%s\n' % (word, tokens[3], tokens[6], tokens[7])

    assert depgraph_input, 'depgraph_input is empty'

    if verbose:
        print 'Begin DepGraph creation'
        print 'depgraph_input=\n%s' % depgraph_input
    
    return DepGraph().read(depgraph_input)

def _normalize(line):
    """
    Deal with lines in which spaces are used rather than tabs.
    """
    import re
    SPC = re.compile(' +')
    return re.sub(SPC, '\t', line)

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

