# Natural Language Toolkit: Switchboard Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

from nltk.tag import str2tuple

from util import *
from api import *

class SwitchboardUtterance(list):
    """
    A specialized list object used to encode switchboard utterances.
    The elements of the list are the words in the utterance; and two
    attributes, C{speaker} and C{id}, are provided to retrieve the
    spearker identifier and utterance id.  Note that utterance ids
    are only unique within a given discourse.
    """
    def __init__(self, words, speaker, id):
        list.__init__(self, words)
        self.speaker = speaker
        self.id = int(id)
    def __repr__(self):
        if len(self) == 0:
            text = ''
        elif isinstance(self[0], tuple):
            text = ' '.join('%s/%s' % w for w in self)
        else:
            text = ' '.join(self)
        return '<%s.%s: %r>' % (self.speaker, self.id, text)

class SwitchboardCorpusReader(CorpusReader):
    _FILES = ['tagged']
    # Use the "tagged" file even for non-tagged data methods, since
    # it's tokenized.
    
    def __init__(self, root):
        CorpusReader.__init__(self, root, self._FILES)

    def words(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._words_block_reader)

    def tagged_words(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._tagged_words_block_reader)

    def utterances(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._utterances_block_reader)

    def tagged_utterances(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._tagged_utterances_block_reader)

    def discourses(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._discourses_block_reader)

    def tagged_discourses(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._tagged_discourses_block_reader)

    def _discourses_block_reader(self, stream):
        # returns at most 1 discourse.  (The other methods depend on this.)
        return [[self._parse_utterance(u, include_tag=False)
                 for b in read_blankline_block(stream)
                 for u in b.split('\n') if u.strip()]]

    def _tagged_discourses_block_reader(self, stream):
        # returns at most 1 discourse.  (The other methods depend on this.)
        return [[self._parse_utterance(u, include_tag=True)
                 for b in read_blankline_block(stream)
                 for u in b.split('\n') if u.strip()]]

    def _utterances_block_reader(self, stream):
        return self._discourses_block_reader(stream)[0]

    def _tagged_utterances_block_reader(self, stream):
        return self._tagged_discourses_block_reader(stream)[0]

    def _words_block_reader(self, stream):
        return sum(self._discourses_block_reader(stream)[0], [])

    def _tagged_words_block_reader(self, stream):
        return sum(self._tagged_discourses_block_reader(stream)[0], [])

    _UTTERANCE_RE = re.compile('(\w+)\.(\d+)\:\s+(.*)')
    _SEP = '/'
    def _parse_utterance(self, utterance, include_tag):
        m = self._UTTERANCE_RE.match(utterance)
        if m is None:
            raise ValueError('Bad utterance %r' % utterance)
        speaker, id, text = m.groups()
        words = [str2tuple(s, self._SEP) for s in text.split()]
        if not include_tag:
            words = [w for (w,t) in words]
        return SwitchboardUtterance(words, speaker, id)
        
        
