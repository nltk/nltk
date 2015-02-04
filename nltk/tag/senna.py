# encoding: utf-8
# Natural Language Toolkit: Senna POS Tagger
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Senna POS tagger, NER Tagger, Chunk Tagger

The input is:
- path to the directory that contains SENNA executables. If the path is incorrect, 
   SennaTagger will automatically search for executable file specified in SENNA environment variable 
- (optionally) the encoding of the input data (default:utf-8)

    >>> from nltk.tag import SennaTagger
    >>> tagger = SennaTagger('/usr/share/senna-v2.0')
    >>> tagger.tag('What is the airspeed of an unladen swallow ?'.split())
    [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'),
    ('of', 'IN'), ('an', 'DT'), ('unladen', 'NN'), ('swallow', 'NN'), ('?', '.')]

    >>> from nltk.tag import SennaChunkTagger
    >>> chktagger = SennaChunkTagger('/usr/share/senna-v2.0')
    >>> chktagger.tag('What is the airspeed of an unladen swallow ?'.split())
    [('What', 'B-NP'), ('is', 'B-VP'), ('the', 'B-NP'), ('airspeed', 'I-NP'),
    ('of', 'B-PP'), ('an', 'B-NP'), ('unladen', 'I-NP'), ('swallow', 'I-NP'),
    ('?', 'O')]

    >>> from nltk.tag import SennaNERTagger
    >>> nertagger = SennaNERTagger('/usr/share/senna-v2.0')
    >>> nertagger.tag('Shakespeare theatre was in London .'.split())
    [('Shakespeare', 'B-PER'), ('theatre', 'O'), ('was', 'O'), ('in', 'O'),
    ('London', 'B-LOC'), ('.', 'O')]
    >>> nertagger.tag('UN headquarters are in NY , USA .'.split())
    [('UN', 'B-ORG'), ('headquarters', 'O'), ('are', 'O'), ('in', 'O'),
    ('NY', 'B-LOC'), (',', 'O'), ('USA', 'B-LOC'), ('.', 'O')]
"""

from nltk.compat import python_2_unicode_compatible
from nltk.classify import Senna

@python_2_unicode_compatible
class SennaTagger(Senna):
    def __init__(self, path, encoding='utf-8'):
        super(SennaTagger, self).__init__(path, ['pos'], encoding)

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return
        for each sentence a list of tuples of (word, tag).
        """
        tagged_sents = super(SennaTagger, self).tag_sents(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                annotations = tagged_sents[i][j]
                tagged_sents[i][j] = (annotations['word'], annotations['pos'])
        return tagged_sents

@python_2_unicode_compatible
class SennaChunkTagger(Senna):
    def __init__(self, path, encoding='utf-8'):
        super(SennaChunkTagger, self).__init__(path, ['chk'], encoding)

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return
        for each sentence a list of tuples of (word, tag).
        """
        tagged_sents = super(SennaChunkTagger, self).tag_sents(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                annotations = tagged_sents[i][j]
                tagged_sents[i][j] = (annotations['word'], annotations['chk'])
        return tagged_sents

@python_2_unicode_compatible
class SennaNERTagger(Senna):
    def __init__(self, path, encoding='utf-8'):
        super(SennaNERTagger, self).__init__(path, ['ner'], encoding)

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return
        for each sentence a list of tuples of (word, tag).
        """
        tagged_sents = super(SennaNERTagger, self).tag_sents(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                annotations = tagged_sents[i][j]
                tagged_sents[i][j] = (annotations['word'], annotations['ner'])
        return tagged_sents



# skip doctests if Senna is not installed
def setup_module(module):
    from nose import SkipTest
    try:
        tagger = Senna('/usr/share/senna-v2.0', ['pos', 'chk', 'ner'])
    except OSError:
        raise SkipTest("Senna executable not found")

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
