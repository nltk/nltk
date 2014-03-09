# encoding: utf-8
# Natural Language Toolkit: Interface to the Senna tagger
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the SENNA pipeline.
"""

from os import path, sep
from subprocess import Popen, PIPE
from platform import architecture, system
from nltk.tag.api import TaggerI
from nltk import compat

_senna_url = 'http://ml.nec-labs.com/senna/'


class Error(Exception):
    """Basic error handling class to be extended by the module specific
    exceptions"""


class ExecutableNotFound(Error):
    """Raised if the senna executable does not exist"""


class RunFailure(Error):
    """Raised if the pipeline fails to execute"""


class SentenceMisalignment(Error):
    """Raised if the new sentence is shorter than the original one or the number
    of sentences in the result is less than the input."""


class SennaTagger(TaggerI):
    r"""
    A general interface of the SENNA pipeline that supports any of the
    operations specified in SUPPORTED_OPERATIONS.

    Applying multiple operations at once has the speed advantage. For example,
    senna v2.0 will calculate the POS tags in case you are extracting the named
    entities. Applying both of the operations will cost only the time of
    extracting the named entities.

    SENNA pipeline has a fixed maximum size of the sentences that it can read.
    By default it is 1024 token/sentence. If you have larger sentences, changing
    the MAX_SENTENCE_SIZE value in SENNA_main.c should be considered and your
    system specific binary should be rebuilt. Otherwise this could introduce
    misalignment errors.

    The input is:
    - path to the directory that contains SENNA executables.
    - List of the operations needed to be performed.
    - (optionally) the encoding of the input data (default:utf-8)

    Example:

        >>> from nltk.tag.senna import SennaTagger
        >>> pipeline = SennaTagger('/usr/share/senna-v2.0', ['pos', 'chk', 'ner'])
        >>> sent = u'Düsseldorf is an international business center'.split()
        >>> pipeline.tag(sent)
        [{'word': u'D\xfcsseldorf', 'chk': u'B-NP', 'ner': u'B-PER', 'pos': u'NNP'},
        {'word': u'is', 'chk': u'B-VP', 'ner': u'O', 'pos': u'VBZ'},
        {'word': u'an', 'chk': u'B-NP', 'ner': u'O', 'pos': u'DT'},
        {'word': u'international', 'chk': u'I-NP', 'ner': u'O', 'pos': u'JJ'},
        {'word': u'business', 'chk': u'I-NP', 'ner': u'O', 'pos': u'NN'},
        {'word': u'center', 'chk': u'I-NP', 'ner': u'O','pos': u'NN'}]
    """

    SUPPORTED_OPERATIONS = ['pos', 'chk', 'ner']

    def __init__(self, senna_path, operations, encoding='utf-8'):
        self._encoding = encoding
        self._path = path.normpath(senna_path) + sep
        self.operations = operations

    @property
    def executable(self):
        """
        A property that determines the system specific binary that should be
        used in the pipeline. In case, the system is not known the senna binary will
        be used.
        """
        os_name = system()
        if os_name == 'Linux':
            bits = architecture()[0]
            if bits == '64bit':
                return path.join(self._path, 'senna-linux64')
            return path.join(self._path, 'senna-linux32')
        if os_name == 'Windows':
            return path.join(self._path, 'senna-win32.exe')
        if os_name == 'Darwin':
            return path.join(self._path, 'senna-osx')
        return path.join(self._path, 'senna')

    def _map(self):
        """
        A method that calculates the order of the columns that SENNA pipeline
        will output the tags into. This depends on the operations being ordered.
        """
        _map = {}
        i = 1
        for operation in SennaTagger.SUPPORTED_OPERATIONS:
            if operation in self.operations:
                _map[operation] = i
                i+= 1
        return _map

    def tag(self, tokens):
        """
        Applies the specified operation(s) on a list of tokens.
        """
        return self.tag_sents([tokens])[0]

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return a
        list of dictionaries. Every dictionary will contain a word with its
        calculated annotations/tags.
        """
        encoding = self._encoding

        # Verifies the existence of the executable
        if not path.isfile(self.executable):
          raise ExecutableNotFound("Senna executable expected at %s but not found" %
                                   self.executable)

        # Build the senna command to run the tagger
        _senna_cmd = [self.executable, '-path', self._path, '-usrtokens', '-iobtags']
        _senna_cmd.extend(['-'+op for op in self.operations])

        # Serialize the actual sentences to a temporary string
        _input = '\n'.join((' '.join(x) for x in sentences))+'\n'
        if isinstance(_input, compat.text_type) and encoding:
            _input = _input.encode(encoding)

        # Run the tagger and get the output
        p = Popen(_senna_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate(input=_input)
        senna_output = stdout

        # Check the return code.
        if p.returncode != 0:
            raise RunFailure('Senna command failed! Details: %s' % stderr)

        if encoding:
            senna_output = stdout.decode(encoding)

        # Output the tagged sentences
        map_ = self._map()
        tagged_sentences = [[]]
        sentence_index = 0
        token_index = 0
        for tagged_word in senna_output.strip().split("\n"):
            if not tagged_word:
                tagged_sentences.append([])
                sentence_index += 1
                token_index = 0
                continue
            tags = tagged_word.split('\t')
            result = {}
            for tag in map_:
              result[tag] = tags[map_[tag]].strip()
            try:
              result['word'] = sentences[sentence_index][token_index]
            except IndexError:
              raise SentenceMisalignment(
                "Misalignment error occurred at sentence number %d. Possible reason"
                " is that the sentence size exceeded the maximum size. Check the "
                "documentation of SennaTagger class for more information."
                % sentence_index)
            tagged_sentences[-1].append(result)
            token_index += 1
        return tagged_sentences


class POSTagger(SennaTagger):
    """
    A Part of Speech tagger.

    The input is:
    - path to the directory that contains SENNA executables.
    - (optionally) the encoding of the input data (default:utf-8)

    Example:

        >>> from nltk.tag.senna import POSTagger
        >>> postagger = POSTagger('/usr/share/senna-v2.0')
        >>> postagger.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'),
        ('of', 'IN'), ('an', 'DT'), ('unladen', 'JJ'), ('swallow', 'VB'), ('?', '.')]
    """
    def __init__(self, path, encoding='utf-8'):
        super(POSTagger, self).__init__(path, ['pos'], encoding)

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return
        for each sentence a list of tuples of (word, tag).
        """
        tagged_sents = super(POSTagger, self).tag_sents(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                annotations = tagged_sents[i][j]
                tagged_sents[i][j] = (annotations['word'], annotations['pos'])
        return tagged_sents


class NERTagger(SennaTagger):
    """
    A named entity extractor.

    The input is:
    - path to the directory that contains SENNA executables.
    - (optionally) the encoding of the input data (default:utf-8)

    Example:

        >>> from nltk.tag.senna import NERTagger
        >>> nertagger = NERTagger('/usr/share/senna-v2.0')
        >>> nertagger.tag('Shakespeare theatre was in London .'.split())
        [('Shakespeare', u'B-PER'), ('theatre', u'O'), ('was', u'O'), ('in', u'O'),
        ('London', u'B-LOC'), ('.', u'O')]
        >>> nertagger.tag('UN headquarters are in NY , USA .'.split())
        [('UN', u'B-ORG'), ('headquarters', u'O'), ('are', u'O'), ('in', u'O'),
        ('NY', u'B-LOC'), (',', u'O'), ('USA', u'B-LOC'), ('.', u'O')]
    """
    def __init__(self, path, encoding='utf-8'):
        super(NERTagger, self).__init__(path, ['ner'], encoding)

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return
        for each sentence a list of tuples of (word, tag).
        """
        tagged_sents = super(NERTagger, self).tag_sents(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                annotations = tagged_sents[i][j]
                tagged_sents[i][j] = (annotations['word'], annotations['ner'])
        return tagged_sents


class CHKTagger(SennaTagger):
    """
    A chunker.

    The input is:
    - path to the directory that contains SENNA executables.
    - (optionally) the encoding of the input data (default:utf-8)

    Example:

        >>> from nltk.tag.senna import CHKTagger
        >>> chktagger = CHKTagger('/usr/share/senna-v2.0')
        >>> chktagger.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', u'B-NP'), ('is', u'B-VP'), ('the', u'B-NP'), ('airspeed', u'I-NP'),
        ('of', u'B-PP'), ('an', u'B-NP'), ('unladen', u'I-NP'), ('swallow',u'I-NP'),
        ('?', u'O')]
    """
    def __init__(self, path, encoding='utf-8'):
        super(CHKTagger, self).__init__(path, ['chk'], encoding)

    def tag_sents(self, sentences):
        """
        Applies the tag method over a list of sentences. This method will return
        for each sentence a list of tuples of (word, tag).
        """
        tagged_sents = super(CHKTagger, self).tag_sents(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                annotations = tagged_sents[i][j]
                tagged_sents[i][j] = (annotations['word'], annotations['chk'])
        return tagged_sents

# skip doctests if Senna is not installed
def setup_module(module):
    from nose import SkipTest
    tagger = POSTagger('/usr/share/senna-v2.0')
    if not path.isfile(tagger.executable):
        raise SkipTest("Senna executable expected at /usr/share/senna-v2.0/senna-osx but not found")
