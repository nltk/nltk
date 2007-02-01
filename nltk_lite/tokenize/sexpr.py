# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Yoav Goldberg <yoavg@cs.bgu.ac.il>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor edits)
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

import re

def sexpr(s):
    """
    Tokenize the text into s-expressions.  For example, the input
    "(a b (c d)) e (f)" is tokenized into the following sequence:
    "(a b (c d))", "e", "(f)".
    
    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens (each of which is an s-expression)
    """
    def matching_paren(s,start=0):
        count = 1
        for (i,c) in enumerate(s[start+1:]):
            if c == '(':
                count += 1
            elif c == ')':
                count -= 1
            if count == 0:
                return i+1
        return -1
          
    while s:
        s = s.strip()
        if s[0] == '(':
            matching_paren_pos = matching_paren(s)
            if matching_paren_pos == -1:
                yield s
                s = ''
            else:
                yield s[0:matching_paren_pos+1]
                s = s[matching_paren_pos+1:]
        else: 
            space_pos = re.search("\s|$",s).start()
            yield s[0:space_pos]
            s = s[space_pos:]

def demo():
    from nltk_lite import tokenize

    example = "a b d (d e (f)) r (t i) (iu a"
    print 'Input text:'
    print example
    print
    print 'Tokenize s-expressions:'
    for x in tokenize.sexpr(example):
	print x

if __name__ == '__main__':
    demo()
