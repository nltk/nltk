# Natural Language Toolkit: PP Attachment Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read lines from the Prepositional Phrase Attachment Corpus.

The PP Attachment Corpus contains several files having the format:

sentence_id verb noun1 preposition noun2 attachment

For example:

42960 gives authority to administration V
46742 gives inventors of microchip N

The PP attachment is to the verb phrase (V) or noun phrase (N), i.e.:

(VP gives (NP authority) (PP to administration))
(VP gives (NP inventors (PP of microchip)))

The corpus contains the following files:

training:   training set
devset:     development test set, used for algorithm development.
test:       test set, used to report results
bitstrings: word classes derived from Mutual Information Clustering for the Wall Street Journal.

Ratnaparkhi, Adwait (1994). A Maximum Entropy Model for Prepositional
Phrase Attachment.  Proceedings of the ARPA Human Language Technology
Conference.  [http://www.cis.upenn.edu/~adwait/papers/hlt94.ps]

The PP Attachment Corpus is distributed with NLTK with the permission
of the author.
"""       

from util import *
from api import *
from nltk import tokenize
from nltk.tag import string2tags, string2words
import os
from nltk.utilities import deprecated

class PPAttachment:
    def __init__(self, sent, verb, noun1, prep, noun2, attachment):
        self.sent = sent
        self.verb = verb
        self.noun1 = noun1
        self.prep = prep
        self.noun2 = noun2
        self.attachment = attachment

    def __repr__(self):
        return ('PPAttachment(sent=%r, verb=%r, noun1=%r, prep=%r, '
                'noun2=%r, attachment=%r)' %
                (self.sent, self.verb, self.noun1, self.prep,
                 self.noun2, self.attachment))

class PPAttachmentCorpusReader(CorpusReader):
    """
    sentence_id verb noun1 preposition noun2 attachment
    """
    def __init__(self, root, items, extension=''):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension
        
    def attachments(self, items):
        return concat([StreamBackedCorpusView(filename, self._read_obj_block)
                       for filename in self._item_filenames(items)])

    def tuples(self, items):
        return concat([StreamBackedCorpusView(filename, self._read_tuple_block)
                       for filename in self._item_filenames(items)])

    def raw(self, items):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
    def _read_tuple_block(self, stream):
        line = stream.readline()
        if line:
            return [tuple(line.split())]
        else:
            return []

    def _read_obj_block(self, stream):
        line = stream.readline()
        if line:
            return [PPAttachment(*line.split())]
        else:
            return []

    #{ Deprecated since 0.8
    @deprecated("Use .tuples() or .raw() or .attachments() instead.")
    def read(self, items, format='tuple'):
        if format == 'tuple': return self.tuples(items)
        if format == 'raw': return self.raw(items)
        raise ValueError('bad format %r' % format)
    #}
