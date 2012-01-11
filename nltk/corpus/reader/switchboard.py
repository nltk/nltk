# Natural Language Toolkit: Switchboard Corpus Reader
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

from nltk.tag import str2tuple

from util import *
from api import *

class SwitchboardTurn(list):
    """
    A specialized list object used to encode switchboard utterances.
    The elements of the list are the words in the utterance; and two
    attributes, ``speaker`` and ``id``, are provided to retrieve the
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

    def __init__(self, root, tag_mapping_function=None):
        CorpusReader.__init__(self, root, self._FILES)
        self._tag_mapping_function = tag_mapping_function

    def words(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._words_block_reader)

    def tagged_words(self, simplify_tags=False):
        def tagged_words_block_reader(stream):
            return self._tagged_words_block_reader(stream, simplify_tags)
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      tagged_words_block_reader)

    def turns(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._turns_block_reader)

    def tagged_turns(self, simplify_tags=False):
        def tagged_turns_block_reader(stream):
            return self._tagged_turns_block_reader(stream, simplify_tags)
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      tagged_turns_block_reader)

    def discourses(self):
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      self._discourses_block_reader)

    def tagged_discourses(self, simplify_tags=False):
        def tagged_discourses_block_reader(stream):
            return self._tagged_discourses_block_reader(stream, simplify_tags)
        return StreamBackedCorpusView(self.abspath('tagged'),
                                      tagged_discourses_block_reader)

    def _discourses_block_reader(self, stream):
        # returns at most 1 discourse.  (The other methods depend on this.)
        return [[self._parse_utterance(u, include_tag=False)
                 for b in read_blankline_block(stream)
                 for u in b.split('\n') if u.strip()]]

    def _tagged_discourses_block_reader(self, stream, simplify_tags=False):
        # returns at most 1 discourse.  (The other methods depend on this.)
        return [[self._parse_utterance(u, include_tag=True,
                                       simplify_tags=simplify_tags)
                 for b in read_blankline_block(stream)
                 for u in b.split('\n') if u.strip()]]

    def _turns_block_reader(self, stream):
        return self._discourses_block_reader(stream)[0]

    def _tagged_turns_block_reader(self, stream, simplify_tags=False):
        return self._tagged_discourses_block_reader(stream, simplify_tags)[0]

    def _words_block_reader(self, stream):
        return sum(self._discourses_block_reader(stream)[0], [])

    def _tagged_words_block_reader(self, stream, simplify_tags=False):
        return sum(self._tagged_discourses_block_reader(stream,
                                                        simplify_tags)[0], [])

    _UTTERANCE_RE = re.compile('(\w+)\.(\d+)\:\s*(.*)')
    _SEP = '/'
    def _parse_utterance(self, utterance, include_tag, simplify_tags=False):
        m = self._UTTERANCE_RE.match(utterance)
        if m is None:
            raise ValueError('Bad utterance %r' % utterance)
        speaker, id, text = m.groups()
        words = [str2tuple(s, self._SEP) for s in text.split()]
        if not include_tag:
            words = [w for (w,t) in words]
        elif simplify_tags:
            words = [(w, self._tag_mapping_function(t)) for (w,t) in words]
        return SwitchboardTurn(words, speaker, id)


