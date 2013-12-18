# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford Parser
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_function

import tempfile
import os
from subprocess import PIPE

from nltk import compat
from nltk.internals import find_jar, config_java, java, _java_options

from nltk.parse.api import ParserI
from nltk.tree import Tree

_stanford_url = 'http://nlp.stanford.edu/software/lex-parser.shtml'

class StanfordParser(ParserI):
    _MODEL_JAR = 'stanford-parser-3.3.0-models.jar'
    _JAR = 'stanford-parser.jar'

    def __init__(self, path_to_jar=None, path_to_models_jar=None,
                 model_path='edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz',
                 encoding='UTF-8', verbose=False, java_options='-mx1000m'):

        self._stanford_jar = find_jar(
                self._JAR, path_to_jar,
                searchpath=(), url=_stanford_url,
                verbose=verbose)

        self._model_jar = find_jar(
                self._MODEL_JAR, path_to_models_jar,
                searchpath=(), url=_stanford_url,
                verbose=verbose)

        self.model_path = model_path
        self._encoding = encoding
        self.java_options = java_options

    def _parse_trees_output(self, output_):
        res = []
        cur_lines = []
        for line in output_.splitlines(False):
            if line == '':
                res.append(Tree.parse('\n'.join(cur_lines)))
                cur_lines = []
            else:
                cur_lines.append(line)
        return res

    def parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a list of
        words; it will be automatically tagged with this StanfordParser instance's
        tagger.

        :param sentence: Input sentence to parse
        :type sentence: list(str)
        :rtype: Tree
        """
        return self.batch_parse([sentence], verbose)[0]

    def batch_parse(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list where each sentence is a list of words.
        Each sentence will be automatically tagged with this StanfordParser instance's
        tagger.
        If whitespaces exists inside a token, then the token will be treated as
        separate tokens.

        :param sentences: Input sentences to parse
        :type sentence: list(list(str))
        :rtype: list(Tree)
        """
        cmd = [
            'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
            '-model', self.model_path,
            '-sentences', 'newline',
            '-outputFormat', 'penn',
            '-tokenized',
            '-escaper', 'edu.stanford.nlp.process.PTBEscapingProcessor',
        ]
        return self._parse_trees_output(self._execute(
            cmd, '\n'.join(' '.join(sentence) for sentence in sentences), verbose))

    def raw_parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a string;
        before parsing, it will be automatically tokenized and tagged by
        the Stanford Parser.

        :param sentence: Input sentence to parse
        :type sentence: str
        :rtype: Tree
        """
        return self.raw_batch_parse((sentence,), verbose)

    def raw_batch_parse(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list of strings.
        Each sentence will be automatically tokenized and tagged by the Stanford Parser.

        :param sentences: Input sentences to parse
        :type sentences: list(str)
        :rtype: list(Tree)
        """
        cmd = [
            'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
            '-model', self.model_path,
            '-sentences', 'newline',
            '-outputFormat', 'penn',
        ]
        return self._parse_trees_output(self._execute(cmd, '\n'.join(sentences), verbose))

    def tagged_parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized and
        tagged.

        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :rtype: Tree
        """
        return self.tagged_batch_parse([sentence], verbose)[0]

    def tagged_batch_parse(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences
        where each sentence is a list of (word, tag) tuples.
        The sentences must have already been tokenized and tagged.

        :param sentences: Input sentences to parse
        :type sentences: list(list(tuple(str, str)))
        :rtype: Tree
        """
        tagSeparator = '/'
        cmd = [
            'edu.stanford.nlp.parser.lexparser.LexicalizedParser',
            '-model', self.model_path,
            '-sentences', 'newline',
            '-outputFormat', 'penn',
            '-tokenized',
            '-tagSeparator', tagSeparator,
            '-tokenizerFactory', 'edu.stanford.nlp.process.WhitespaceTokenizer',
            '-tokenizerMethod', 'newCoreLabelTokenizerFactory',
        ]
        # We don't need to escape slashes as "splitting is done on the last instance of the character in the token"
        return self._parse_trees_output(self._execute(
            cmd, '\n'.join(' '.join(tagSeparator.join(tagged) for tagged in sentence) for sentence in sentences), verbose))

    def _execute(self, cmd, input_, verbose=False):
        encoding = self._encoding
        cmd.extend(['-encoding', encoding])

        default_options = ' '.join(_java_options)

        # Configure java.
        config_java(options=self.java_options, verbose=verbose)

        # Windows is incompatible with NamedTemporaryFile() without passing in delete=False.
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as input_file:
            # Write the actual sentences to the temporary input file
            if isinstance(input_, compat.text_type) and encoding:
                input_ = input_.encode(encoding)
            input_file.write(input_)
            input_file.flush()

            cmd.append(input_file.name)

            # Run the tagger and get the output.
            stdout, stderr = java(cmd, classpath=(self._stanford_jar, self._model_jar),
                                  stdout=PIPE, stderr=PIPE)
            stdout = stdout.decode(encoding)
            if (not compat.PY3) and encoding == 'ascii':
                stdout = str(stdout)

        os.unlink(input_file.name)

        # Return java configurations to their default values.
        config_java(options=default_options, verbose=False)

        return stdout

