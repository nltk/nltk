# Natural Language Toolkit: Test Code for RegexpChunkParser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.parser.chunk.RegexpChunkParser} and associated
functions and classes.
"""

from nltk.parser.chunk import *
from nltk.tagger import TaggedTokenizer
from nltk.tokenizer import LineTokenizer

import unittest

def testChunkString(): r"""
Unit test cases for L{nltk.parser.chunk.ChunkString}.

A chunk string is a string-based encoding of a chunking of a text.
Chunk strings are constructed from lists of tagged tokens.

    >>> tok = Token(TEXT='A/x B/y C/z')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    >>> ChunkString(tok['WORDS'])
    <ChunkString: '<x><y><z>'>

The chunk string records:
  - Each token's tag (using labels demarkated by angle brackets)
  - The current chunking (using curly braces)

The subtokens' tags may contain a variety characters, including
punctuation:

    >>> tok = Token(TEXT='A/. B/$ C/@ D/# E/! F/% G/^ H/& I/* J/( K/)')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    >>> ChunkString(tok['WORDS'])
    <ChunkString: '<.><$><@><#><!><%><^><&><*><(><)>'>

The subtokens' tags should I{not} contain angle brackets ('C{<}' and
'C{>}') or curly brackets ('C{E{lb}}' and 'C{E{rb}}'); but this isn't
currently checked:

    >>> tok = Token(TEXT='A/< B/> C/{ D/}')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    >>> ChunkString(tok['WORDS'])
    <ChunkString: '<<><>><{><}>'>
    
The subtokens' texts are ignored, so can contain anything:

    >>> tok = Token(TEXT='./A $/B @/C #/D !/E %/F ^/G &/H */I (/J )/K')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    >>> ChunkString(tok['WORDS'])
    <ChunkString: '<A><B><C><D><E><F><G><H><I><J><K>'>
    
Chunk strings may be empty:

    >>> ChunkString([])
    <ChunkString: '<>'>

Regular-expression transformations can be applied to chunk strings:

    >>> tok = Token(TEXT='A/1 B/2 C/3 D/4 E/5 F/6 G/7 H/8 I/9 J/0')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs
    <ChunkString: '<1><2><3><4><5><6><7><8><9><0>'>
    >>> cs.xform(r'<2>', r'{<2>}')
    >>> cs
    <ChunkString: '<1>{<2>}<3><4><5><6><7><8><9><0>'>
    >>> cs.xform(r'(<3>)', r'{\1}')
    >>> cs
    <ChunkString: '<1>{<2>}{<3>}<4><5><6><7><8><9><0>'>
    >>> cs.xform(r'((<[5670]>)+)', r'{\1}')
    >>> cs
    <ChunkString: '<1>{<2>}{<3>}<4>{<5><6><7>}<8><9>{<0>}'>
    >>> cs.xform(r'((<[67]>)+)', r'}\1{')
    >>> cs
    <ChunkString: '<1>{<2>}{<3>}<4>{<5>}<6><7><8><9>{<0>}'>

The C{to_chunkstruct} method can be used to convert a chunk string to
the corresponding chunk structure:

    >>> print cs.to_chunkstruct()
    (TEXT:
      <A/1>
      (CHUNK: <B/2>)
      (CHUNK: <C/3>)
      <D/4>
      (CHUNK: <E/5>)
      <F/6>
      <G/7>
      <H/8>
      <I/9>
      (CHUNK: <J/0>))

Transformations can be limited to only chunks or only chinks:
      
    >>> tok = Token(TEXT='A/1 B/2 C/3 D/4 E/5 F/1 G/2 H/4 I/3 J/3')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs
    <ChunkString: '<1><2><3><4><5><1><2><4><3><3>'>
    >>> cs.xform_chink(r'((<(3|4)>)+)', r'{\1}')
    >>> cs
    <ChunkString: '<1><2>{<3><4>}<5><1><2>{<4><3><3>}'>
    >>> cs.xform_chink(r'((<(4|5)>)+)', r'{\1}')
    >>> cs
    <ChunkString: '<1><2>{<3><4>}{<5>}<1><2>{<4><3><3>}'>
    >>> cs.xform_chink(r'(<2><3>)', r'{\1}')
    >>> cs
    <ChunkString: '<1><2>{<3><4>}{<5>}<1><2>{<4><3><3>}'>
    >>> cs.xform_chunk(r'(<3>)(<3>)', r'\1}{\2')
    >>> cs
    <ChunkString: '<1><2>{<3><4>}{<5>}<1><2>{<4><3>}{<3>}'>

With the default debugging level, the chunk string is checked for
validity on each transformation, and on conversion to a chunk
structure:

    >>> tok = Token(TEXT='A/1 B/2 C/3 D/4 E/5 F/1 G/2 H/4 I/3 J/3')
    >>> TaggedTokenizer(SUBTOKENS='WORDS').tokenize(tok)
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2>', r'{<2>')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2>', r'<2>}')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2>', r'<3>')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2>', r'')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2>', r'{{<2>}}')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2><3><4>', r'{<2>{<3>}<4>}')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
    
    >>> cs = ChunkString(tok['WORDS'])
    >>> cs.xform(r'<2><3><4>', r'}<2>{<3>}<4>{')
    Traceback (most recent call last):
      ...
    ValueError: Transformation generated invalid chunkstring
"""

def test_tag_pattern2re_pattern(): r"""
Unit test cases for L{nltk.parser.chunk.tag_pattern2re_pattern}

C{tag_pattern2re_pattern} converts a tag pattern to a regexp, suitable
for use with the C{re} module.

All whitespace is stripped:
    >>> tag_pattern2re_pattern('a b c')
    'abc'
    >>> tag_pattern2re_pattern(' a b c')
    'abc'
    >>> tag_pattern2re_pattern(' a    b\n\t   c  \n')
    'abc'

Parenthases are added both inside and outside each set of angle
brackets:

    >>> tag_pattern2re_pattern('<><><>')
    '(<()>)(<()>)(<()>)'
    >>> tag_pattern2re_pattern('<x>+<y>')
    '(<(x)>)+(<(y)>)'

Dots are replaced by an expression that matches anything except angle
brackets and curly brackets:

    >>> tag_pattern2re_pattern(r'a.b')
    'a[^\\{\\}<>]b'
    >>> tag_pattern2re_pattern(r'..')
    '[^\\{\\}<>][^\\{\\}<>]'
    >>> tag_pattern2re_pattern(r'\..\.')
    '\\.[^\\{\\}<>]\\.'
    >>> tag_pattern2re_pattern(r'\\..\.')
    '\\\\[^\\{\\}<>][^\\{\\}<>]\\.'
    >>> tag_pattern2re_pattern(r'\\\..\.')
    '\\\\\\.[^\\{\\}<>]\\.'
    >>> tag_pattern2re_pattern(r'.\\.\.')
    '[^\\{\\}<>]\\\\[^\\{\\}<>]\\.'
"""

def test_RegexpChunkParser(): r"""
Unit test cases for L{nltk.parser.chunk.RegexpChunkParser} and associated
rules.

Set up a test sample.

    >>> text = '''
    ... [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
    ... [ The/DT cats/NNS ] ./.
    ... [ dog/NN ] ./.
    ... [ John/NNP ] saw/VBD [the/DT cat/NN] [the/DT dog/NN] liked/VBD ./.
    ... '''
    >>> tok = Token(TEXT=text)
    >>> TaggedTokenizer().tokenize(tok)

Now test some chunk parsers.

Chunk Rule
==========
    >>> rule1 = ChunkRule('<NN>', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<NN>'>
    -----------------------------------------------------------------------------
    Precision:  33.3%      Recall:  14.3%        F-Measure:  20.0%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <little/JJ>, <cat/NN>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
       (<John/NNP>,)
    Incorrect:
       (<cat/NN>,)
       (<mat/NN>,)
    \===========================================================================/
        
    >>> rule1 = ChunkRule('<NN>', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<NN>'>
    -----------------------------------------------------------------------------
    Precision:  33.3%      Recall:  14.3%        F-Measure:  20.0%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <little/JJ>, <cat/NN>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
       (<John/NNP>,)
    Incorrect:
       (<cat/NN>,)
       (<mat/NN>,)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<NN|DT>', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<NN|DT>'>
    -----------------------------------------------------------------------------
    Precision:  20.0%      Recall:  14.3%        F-Measure:  16.7%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <little/JJ>, <cat/NN>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
       (<John/NNP>,)
    Incorrect:
       (<The/DT>,)
       (<the/DT>,)
       (<cat/NN>,)
       (<mat/NN>,)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<NN|DT>+', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<NN|DT>+'>
    -----------------------------------------------------------------------------
    Precision:  33.3%      Recall:  28.6%        F-Measure:  30.8%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <little/JJ>, <cat/NN>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<John/NNP>,)
    Incorrect:
       (<The/DT>,)
       (<the/DT>,)
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
       (<cat/NN>,)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<NN|DT|JJ>+', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<NN|DT|JJ>+'>
    -----------------------------------------------------------------------------
    Precision:  60.0%      Recall:  42.9%        F-Measure:  50.0%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<John/NNP>,)
    Incorrect:
       (<The/DT>,)
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<DT>?<JJ>*<NN>+', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<DT>?<JJ>*<NN>+'>
    -----------------------------------------------------------------------------
    Precision: 100.0%      Recall:  71.4%        F-Measure:  83.3%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<John/NNP>,)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<DT>?<JJ>*<NN.*>', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 1 rules:
        Chunk NPs   <ChunkRule: '<DT>?<JJ>*<NN.*>'>
    -----------------------------------------------------------------------------
    Precision: 100.0%      Recall: 100.0%        F-Measure: 100.0%
    \===========================================================================/
            
Make sure we don't allow overlaps:
            
    >>> rule1 = ChunkRule('<DT>?<JJ>*<NN.*>', 'Chunk NPs')
    >>> rule2 = ChunkRule('<NN><.*>', 'Chunk NPs')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk NPs   <ChunkRule: '<DT>?<JJ>*<NN.*>'>
        Chunk NPs   <ChunkRule: '<NN><.*>'>
    -----------------------------------------------------------------------------
    Precision: 100.0%      Recall: 100.0%        F-Measure: 100.0%
    \===========================================================================/
            
Chink Rule
==========
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN|VB.*>', 'Chink')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN|VB.*>'>
    -----------------------------------------------------------------------------
    Precision:  28.6%      Recall:  28.6%        F-Measure:  28.6%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
       (<dog/NN>,)
    Incorrect:
       (<./.>,)
       (<The/DT>, <cats/NNS>, <./.>)
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>, <./.>)
       (<dog/NN>, <./.>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN|VB.*>+', 'Chink')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN|VB.*>+'>
    -----------------------------------------------------------------------------
    Precision:  28.6%      Recall:  28.6%        F-Measure:  28.6%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
       (<dog/NN>,)
    Incorrect:
       (<./.>,)
       (<The/DT>, <cats/NNS>, <./.>)
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>, <./.>)
       (<dog/NN>, <./.>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN>|<VB.*>', 'Chink')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN>|<VB.*>'>
    -----------------------------------------------------------------------------
    Precision:  28.6%      Recall:  28.6%        F-Measure:  28.6%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
       (<dog/NN>,)
    Incorrect:
       (<./.>,)
       (<The/DT>, <cats/NNS>, <./.>)
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>, <./.>)
       (<dog/NN>, <./.>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN|VB.*|\.>', 'Chink')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN|VB.*|\\.>'>
    -----------------------------------------------------------------------------
    Precision:  83.3%      Recall:  71.4%        F-Measure:  76.9%
    Missed:
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
    Incorrect:
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN|VB.*|\.>+', 'Chink')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN|VB.*|\\.>+'>
    -----------------------------------------------------------------------------
    Precision:  83.3%      Recall:  71.4%        F-Measure:  76.9%
    Missed:
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
    Incorrect:
       (<the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN|VB.*|\.>|(?=<DT>)', 'Chink')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN|VB.*|\\.>|(?=<DT>)'>
    -----------------------------------------------------------------------------
    Precision: 100.0%      Recall: 100.0%        F-Measure: 100.0%
    \===========================================================================/
            
UnChunk Rule
============
    >>> rule1 = ChunkRule('<.*>', 'Chunk Every token')
    >>> rule2 = UnChunkRule('<IN|VB.*>', 'Unchunk')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Every token   <ChunkRule: '<.*>'>
        Unchunk             <UnChunkRule: '<IN|VB.*>'>
    -----------------------------------------------------------------------------
    Precision:  22.2%      Recall:  28.6%        F-Measure:  25.0%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <little/JJ>, <cat/NN>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
    Incorrect:
       (<./.>,)
       (<The/DT>,)
       (<the/DT>,)
       (<little/JJ>,)
       (<cat/NN>,)
       (<mat/NN>,)
       (<cats/NNS>,)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>', 'Chunk Every token')
    >>> rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
    >>> parser = RegexpChunkParser([rule1, rule2])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 2 rules:
        Chunk Every token   <ChunkRule: '<.*>'>
        Unchunk             <UnChunkRule: '<IN|VB.*|\\.>'>
    -----------------------------------------------------------------------------
    Precision:  25.0%      Recall:  28.6%        F-Measure:  26.7%
    Missed:
       (<The/DT>, <cats/NNS>)
       (<the/DT>, <little/JJ>, <cat/NN>)
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<the/DT>, <mat/NN>)
    Incorrect:
       (<The/DT>,)
       (<the/DT>,)
       (<little/JJ>,)
       (<cat/NN>,)
       (<mat/NN>,)
       (<cats/NNS>,)
    \===========================================================================/
            
Merge Rule
==========
    >>> rule1 = ChunkRule('<.*>', 'Chunk Every token')
    >>> rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
    >>> rule3 = MergeRule('<DT>', '<NN.*>', 'Merge')
    >>> parser = RegexpChunkParser([rule1, rule2, rule3])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 3 rules:
        Chunk Every token   <ChunkRule: '<.*>'>
        Unchunk             <UnChunkRule: '<IN|VB.*|\\.>'>
        Merge               <MergeRule: '<DT>', '<NN.*>'>
    -----------------------------------------------------------------------------
    Precision:  66.7%      Recall:  85.7%        F-Measure:  75.0%
    Missed:
       (<the/DT>, <little/JJ>, <cat/NN>)
    Incorrect:
       (<the/DT>,)
       (<little/JJ>,)
       (<cat/NN>,)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>', 'Chunk Every token')
    >>> rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
    >>> rule3 = MergeRule('<DT|JJ>', '<NN.*>', 'Merge')
    >>> parser = RegexpChunkParser([rule1, rule2, rule3])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 3 rules:
        Chunk Every token   <ChunkRule: '<.*>'>
        Unchunk             <UnChunkRule: '<IN|VB.*|\\.>'>
        Merge               <MergeRule: '<DT|JJ>', '<NN.*>'>
    -----------------------------------------------------------------------------
    Precision:  75.0%      Recall:  85.7%        F-Measure:  80.0%
    Missed:
       (<the/DT>, <little/JJ>, <cat/NN>)
    Incorrect:
       (<the/DT>,)
       (<little/JJ>, <cat/NN>)
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>', 'Chunk Every token')
    >>> rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
    >>> rule3 = MergeRule('<DT|JJ>', '<NN.*>', 'Merge')
    >>> rule4 = MergeRule('<DT>', '<JJ.*>', 'Merge')
    >>> parser = RegexpChunkParser([rule1, rule2, rule3, rule4])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 4 rules:
        Chunk Every token   <ChunkRule: '<.*>'>
        Unchunk             <UnChunkRule: '<IN|VB.*|\\.>'>
        Merge               <MergeRule: '<DT|JJ>', '<NN.*>'>
        Merge               <MergeRule: '<DT>', '<JJ.*>'>
    -----------------------------------------------------------------------------
    Precision: 100.0%      Recall: 100.0%        F-Measure: 100.0%
    \===========================================================================/
            
Split Rule
==========
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = ChinkRule('<IN|VB.*|\.>+', 'Chink')
    >>> rule3 = SplitRule('', '<DT>', 'Split')
    >>> parser = RegexpChunkParser([rule1, rule2, rule3])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 3 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Chink              <ChinkRule: '<IN|VB.*|\\.>+'>
        Split              <SplitRule: '', '<DT>'>
    -----------------------------------------------------------------------------
    Precision: 100.0%      Recall: 100.0%        F-Measure: 100.0%
    \===========================================================================/
            
    >>> rule1 = ChunkRule('<.*>*', 'Chunk Everything')
    >>> rule2 = SplitRule('<NN>', '<VBD>', 'Split')
    >>> rule3 = SplitRule('<IN>', '<DT>', 'Split')
    >>> rule4 = SplitRule('', '<\.>', 'Split')
    >>> parser = RegexpChunkParser([rule1, rule2, rule3, rule4])
    >>> demo_eval(parser, text)
    /===========================================================================\
    Scoring RegexpChunkParser with 4 rules:
        Chunk Everything   <ChunkRule: '<.*>*'>
        Split              <SplitRule: '<NN>', '<VBD>'>
        Split              <SplitRule: '<IN>', '<DT>'>
        Split              <SplitRule: '', '<\\.>'>
    -----------------------------------------------------------------------------
    Precision:  50.0%      Recall:  57.1%        F-Measure:  53.3%
    Missed:
       (<the/DT>, <cat/NN>)
       (<the/DT>, <dog/NN>)
       (<John/NNP>,)
    Incorrect:
       (<./.>,)
       (<John/NNP>, <saw/VBD>, <the/DT>, <cat/NN>, <the/DT>, <dog/NN>)
       (<liked/VBD>,)
       (<sat/VBD>, <on/IN>)
    \===========================================================================/
"""
    
#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite(reload_module=False):
    import doctest, nltk.test.rechunkparser
    if reload_module: reload(nltk.test.rechunkparser)
    return doctest.DocTestSuite(nltk.test.rechunkparser)

def test(verbosity=2, reload_module=False):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite(reload_module))

if __name__ == '__main__':
    test(reload_module=True)
