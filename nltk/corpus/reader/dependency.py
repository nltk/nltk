# Natural Language Toolkit: Dependency Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Kepa Sarasola <kepa.sarasola@ehu.es>
#         Iker Manterola <returntothehangar@hotmail.com>
#         
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.parse import DependencyGraph
from nltk.tokenize import *

from util import *
from api import *

class DependencyCorpusReader(SyntaxCorpusReader):
        
    def __init__(self, root, fileids, encoding=None,
                 word_tokenizer=TabTokenizer(),
                 sent_tokenizer=RegexpTokenizer('\n', gaps=True),
                 para_block_reader=read_blankline_block):
        
        CorpusReader.__init__(self, root, fileids, encoding)
            
    #########################################################

    def raw(self, fileids=None):
        """
        @return: the given file(s) as a single string.
        @rtype: C{str}
        """
        return concat([open(fileid).read()
                      for fileid in self.abspaths(fileids)])
    
    def words(self, fileids=None):
        return concat([DependencyCorpusView(fileid, False, False, False)
                       for fileid in self.abspaths(fileids)])
    
    def tagged_words(self, fileids=None):
        return concat([DependencyCorpusView(fileid, True, False, False)
                       for fileid in self.abspaths(fileids)])

    def sents(self, fileids=None):
        return concat([DependencyCorpusView(fileid, False, True, False)
                       for fileid in self.abspaths(fileids)])

    def tagged_sents(self, fileids=None):
            return concat([DependencyCorpusView(fileid, True, True, False)
                                  for fileid in self.abspaths(fileids)])

    def parsed_sents(self, fileids=None):
        sents=concat([DependencyCorpusView(fileid, False, True, True)
                                  for fileid in self.abspaths(fileids)])
        return [DependencyGraph(sent) for sent in sents]


class DependencyCorpusView(StreamBackedCorpusView):
    _DOCSTART = '-DOCSTART- -DOCSTART- O\n' #dokumentu hasiera definitzen da

    def __init__(self, corpus_file, tagged, group_by_sent, dependencies, 
                 chunk_types=None):
        self._tagged = tagged
        self._dependencies = dependencies
        self._group_by_sent = group_by_sent
        self._chunk_types = chunk_types
        StreamBackedCorpusView.__init__(self, corpus_file)

    def read_block(self, stream):
        # Read the next sentence.
        sent = read_blankline_block(stream)[0].strip()
        # Strip off the docstart marker, if present.
        if sent.startswith(self._DOCSTART):
            sent = sent[len(self._DOCSTART):].lstrip()
        
        # extract word and tag from any of the formats
        if not self._dependencies:
            lines = [line.split('\t') for line in sent.split('\n')]
            if len(lines[0]) == 3 or len(lines[0]) == 4:
                sent = [(line[0], line[1]) for line in lines]
            elif len(lines[0]) == 10:
                sent = [(line[1], line[4]) for line in lines]
            else:
                raise ValueError('Unexpected number of fields in dependency tree file')

            # discard tags if they weren't requested
            if not self._tagged:
                sent = [word for (word, tag) in sent]
                
        # Return the result.
        if self._group_by_sent:
            return [sent]
        else:
            return list(sent)
