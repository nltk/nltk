# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford Parser
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals

import tempfile
import os
import re
import json
from subprocess import PIPE

import requests

from nltk import compat
from nltk.internals import find_jar_iter, config_java, java, _java_options

from nltk.parse.api import ParserI
from nltk.tokenize.api import TokenizerI
from nltk.parse.dependencygraph import DependencyGraph
from nltk.tree import Tree

_stanford_url = 'http://nlp.stanford.edu/software/lex-parser.shtml'


class GenericStanfordParser(ParserI, TokenizerI):
    """Interface to the Stanford Parser"""

    _MODEL_JAR_PATTERN = r'stanford-parser-(\d+)(\.(\d+))+-models\.jar'
    _JAR = r'stanford-parser\.jar'
    _MAIN_CLASS = 'edu.stanford.nlp.parser.lexparser.LexicalizedParser'

    _USE_STDIN = False
    _DOUBLE_SPACED_OUTPUT = False

    def __init__(self, url='http://localhost:9000', encoding='utf8'):

        self.url = url
        self.encoding = encoding

        self.session = requests.Session()

        return

        # find the most recent code and model jar
        stanford_jar = max(
            find_jar_iter(
                self._JAR, path_to_jar,
                env_vars=('STANFORD_PARSER', 'STANFORD_CORENLP'),
                searchpath=(), url=_stanford_url,
                verbose=verbose, is_regex=True
            ),
            key=lambda model_name: re.match(self._JAR, model_name)
        )

        model_jar=max(
            find_jar_iter(
                self._MODEL_JAR_PATTERN, path_to_models_jar,
                env_vars=('STANFORD_MODELS', 'STANFORD_CORENLP'),
                searchpath=(), url=_stanford_url,
                verbose=verbose, is_regex=True
            ),
            key=lambda model_name: re.match(self._MODEL_JAR_PATTERN, model_name)
        )

        self._classpath = (stanford_jar, model_jar)

        self.model_path = model_path
        self._encoding = encoding
        self.corenlp_options = corenlp_options
        self.java_options = java_options

    def _parse_trees_output(self, output_):
        res = []
        cur_lines = []
        cur_trees = []
        blank = False
        for line in output_.splitlines(False):
            if line == '':
                if blank:
                    res.append(iter(cur_trees))
                    cur_trees = []
                    blank = False
                elif self._DOUBLE_SPACED_OUTPUT:
                    cur_trees.append(self._make_tree('\n'.join(cur_lines)))
                    cur_lines = []
                    blank = True
                else:
                    res.append(iter([self._make_tree('\n'.join(cur_lines))]))
                    cur_lines = []
            else:
                cur_lines.append(line)
                blank = False
        return iter(res)

    def parse_sents(self, sentences, *args, **kwargs):
        """Parse multiple sentences.

        Takes multiple sentences as a list where each sentence is a list of
        words. Each sentence will be automatically tagged with this
        StanfordParser instance's tagger.

        If a whitespace exists inside a token, then the token will be treated as
        several tokens.

        :param sentences: Input sentences to parse
        :type sentences: list(list(str))
        :rtype: iter(iter(Tree))
        """

        sentences = (' '.join(words) for words in sentences)
        return self.raw_parse_sents(sentences, *args, **kwargs)

    def raw_parse(self, sentence, properties=None, *args, **kwargs):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a string;
        before parsing, it will be automatically tokenized and tagged by
        the Stanford Parser.

        :param sentence: Input sentence to parse
        :type sentence: str
        :rtype: iter(Tree)
        """
        default_properties = {
                    'tokenize.whitespace': 'false',
        }

        default_properties.update(properties or {})

        return next(
            self.raw_parse_sents(
                [sentence],
                properties=default_properties,
                *args,
                **kwargs
            )
        )

    def api_call(self, data, properties=None):
        default_properties = {
            'outputFormat': 'json',
            'annotators': 'tokenize,pos,lemma,ssplit,{parser_annotator}'.format(
                parser_annotator=self.parser_annotator,
            ),
        }

        default_properties.update(properties or {})

        response = self.session.post(
            self.url,
            params={
                'properties': json.dumps(default_properties),
            },
            data=data.encode(self.encoding),
        )

        response.raise_for_status()

        return response.json()

    def raw_parse_sents(
        self,
        sentences,
        verbose=False,
        properties=None,
        *args,
        **kwargs
    ):
        """Use StanfordParser to parse multiple sentences.

        Takes multiple sentences as a list of strings. Each sentence will be
        automatically tokenized and tagged by the Stanford Parser.

        :param sentences: Input sentences to parse.
        :type sentences: list(str)
        :rtype: iter(iter(Tree))

        """
        default_properties = {
            'ssplit.isOneSentence': 'true',
        }

        default_properties.update(properties or {})

        for sentence in sentences:
            parsed_data = self.api_call(sentence, properties=default_properties)

            assert len(parsed_data['sentences']) == 1

            for parse in parsed_data['sentences']:
                tree = self.make_tree(parse)
                yield iter([tree])

    def tagged_parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized and
        tagged.

        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :rtype: iter(Tree)
        """
        return next(self.tagged_parse_sents([sentence], verbose))

    def tagged_parse_sents(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences
        where each sentence is a list of (word, tag) tuples.
        The sentences must have already been tokenized and tagged.

        :param sentences: Input sentences to parse
        :type sentences: list(list(tuple(str, str)))
        :rtype: iter(iter(Tree))
        """
        tag_separator = '/'
        cmd = [
            self._MAIN_CLASS,
            '-model', self.model_path,
            '-sentences', 'newline',
            '-outputFormat', self._OUTPUT_FORMAT,
            '-tokenized',
            '-tagSeparator', tag_separator,
            '-tokenizerFactory', 'edu.stanford.nlp.process.WhitespaceTokenizer',
            '-tokenizerMethod', 'newCoreLabelTokenizerFactory',
        ]
        # We don't need to escape slashes as "splitting is done on the last instance of the character in the token"
        return self._parse_trees_output(self._execute(
            cmd, '\n'.join(' '.join(tag_separator.join(tagged) for tagged in sentence) for sentence in sentences), verbose))

    def _execute(self, cmd, input_, verbose=False):
        encoding = self._encoding
        cmd.extend(['-encoding', encoding])
        if self.corenlp_options:
            cmd.append(self.corenlp_options)

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

            # Run the tagger and get the output.
            if self._USE_STDIN:
                input_file.seek(0)
                stdout, stderr = java(cmd, classpath=self._classpath,
                                      stdin=input_file, stdout=PIPE, stderr=PIPE)
            else:
                cmd.append(input_file.name)
                stdout, stderr = java(cmd, classpath=self._classpath,
                                      stdout=PIPE, stderr=PIPE)

            stdout = stdout.replace(b'\xc2\xa0',b' ')
            stdout = stdout.replace(b'\xa0',b' ')
            stdout = stdout.decode(encoding)

        os.unlink(input_file.name)

        # Return java configurations to their default values.
        config_java(options=default_options, verbose=False)

        return stdout

    def parse_text(self, text, properties=None, *args, **kwargs):
        """Parse a piece of text.

        The text might contain several sentences which will be split by CoreNLP.

        :param str text: text to be split.
        :returns: an iterable of syntactic structures.  # TODO: should it be an iterable of iterables.

        """
        if properties is None:
            properties is {}

        default_properties = {
            ''
        }

        parsed_data = self.api_call(text, properties=properties, *args, **kwargs)

        for parse in parsed_data['sentences']:
            yield self.make_tree(parse)

    def tokenize(self, text, properties=None):
        """Tokenize a string of text.

        >>> parser = StanfordParser()

        >>> text = 'Good muffins cost $3.88\\nin New York.  Please buy me\\ntwo of them.\\nThanks.'
        >>> list(parser.tokenize(text))
        ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.', 'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
        >>> s = "The colour of the wall is blue."

        >>> list(
        ...     parser.tokenize(
        ...         'The colour of the wall is blue.',
        ...         properties={'tokenize.options': 'americanize=true'},
        ...     )
        ... )
        ['The', 'color', 'of', 'the', 'wall', 'is', 'blue', '.']

        """
        default_properties = {
            'annotators': 'tokenize,ssplit',
        }

        default_properties.update(properties or {})

        result = self.api_call(text, properties=default_properties)

        for sentence in result['sentences']:
            for token in sentence['tokens']:
                yield token['originalText']


class StanfordParser(GenericStanfordParser):
    """
    >>> parser=StanfordParser()

    >>> next(
    ...     parser.raw_parse('the quick brown fox jumps over the lazy dog')
    ... ).pretty_print()  # doctest: +NORMALIZE_WHITESPACE
                         ROOT
                          |
                          S
           _______________|_________
          |                         VP
          |                _________|___
          |               |             PP
          |               |     ________|___
          NP              |    |            NP
      ____|__________     |    |     _______|____
     DT   JJ    JJ   NN  VBZ   IN   DT      JJ   NN
     |    |     |    |    |    |    |       |    |
    the quick brown fox jumps over the     lazy dog

    >>> (parse_fox, ), (parse_wolf, ) = parser.raw_parse_sents(
    ...     [
    ...         'the quick brown fox jumps over the lazy dog',
    ...         'the quick grey wolf jumps over the lazy fox',
    ...     ]
    ... )

    >>> parse_fox.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
                         ROOT
                          |
                          S
           _______________|_________
          |                         VP
          |                _________|___
          |               |             PP
          |               |     ________|___
          NP              |    |            NP
      ____|__________     |    |     _______|____
     DT   JJ    JJ   NN  VBZ   IN   DT      JJ   NN
     |    |     |    |    |    |    |       |    |
    the quick brown fox jumps over the     lazy dog

    >>> parse_wolf.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
                         ROOT
                          |
                          S
           _______________|_________
          |                         VP
          |                _________|___
          |               |             PP
          |               |     ________|___
          NP              |    |            NP
      ____|_________      |    |     _______|____
     DT   JJ   JJ   NN   VBZ   IN   DT      JJ   NN
     |    |    |    |     |    |    |       |    |
    the quick grey wolf jumps over the     lazy fox

    >>> (parse_dog, ), (parse_friends, ) = parser.parse_sents(
    ...     [
    ...         "I 'm a dog".split(),
    ...         "This is my friends ' cat ( the tabby )".split(),
    ...     ]
    ... )

    >>> parse_dog.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
            ROOT
             |
             S
      _______|____
     |            VP
     |    ________|___
     NP  |            NP
     |   |         ___|___
    PRP VBP       DT      NN
     |   |        |       |
     I   'm       a      dog

    >>> parse_friends.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
         ROOT
          |
          S
      ____|___________
     |                VP
     |     ___________|_____________
     |    |                         NP
     |    |                  _______|_________
     |    |                 NP               PRN
     |    |            _____|_______      ____|______________
     NP   |           NP            |    |        NP         |
     |    |     ______|_________    |    |     ___|____      |
     DT  VBZ  PRP$   NNS       POS  NN -LRB-  DT       NN  -RRB-
     |    |    |      |         |   |    |    |        |     |
    This  is   my  friends      '  cat -LRB- the     tabby -RRB-

    >>> parse_john, parse_mary, = parser.parse_text(
    ...     'John loves Mary. Mary walks.'
    ... )

    >>> parse_john.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
          ROOT
           |
           S
      _____|_____________
     |          VP       |
     |      ____|___     |
     NP    |        NP   |
     |     |        |    |
    NNP   VBZ      NNP   .
     |     |        |    |
    John loves     Mary  .

    >>> parse_mary.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
          ROOT
           |
           S
      _____|____
     NP    VP   |
     |     |    |
    NNP   VBZ   .
     |     |    |
    Mary walks  .

    Special cases
    -------------

    >>> next(
    ...     parser.raw_parse(
    ...         'NASIRIYA, Iraq—Iraqi doctors who treated former prisoner of war '
    ...         'Jessica Lynch have angrily dismissed claims made in her biography '
    ...         'that she was raped by her Iraqi captors.'
    ...     )
    ... ).height()
    17

    >>> next(
    ...     parser.raw_parse(
    ...         "The broader Standard & Poor's 500 Index <.SPX> was 0.46 points lower, or "
    ...         '0.05 percent, at 997.02.'
    ...     )
    ... ).height()
    10

    """

    _OUTPUT_FORMAT = 'penn'
    parser_annotator = 'parse'

    def make_tree(self, result):
        return Tree.fromstring(result['parse'])


class StanfordDependencyParser(GenericStanfordParser):

    """
    >>> dep_parser = StanfordDependencyParser()

    >>> parse, = dep_parser.raw_parse(
    ...     'The quick brown fox jumps over the lazy dog.'
    ... )
    >>> print(parse.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    The     DT      4       det
    quick   JJ      4       amod
    brown   JJ      4       amod
    fox     NN      5       nsubj
    jumps   VBZ     0       ROOT
    over    IN      9       case
    the     DT      9       det
    lazy    JJ      9       amod
    dog     NN      5       nmod
    .       .       5       punct

    >>> print(parse.tree())  # doctest: +NORMALIZE_WHITESPACE
    (jumps (fox The quick brown) (dog over the lazy) .)

    >>> for governor, dep, dependent in parse.triples():
    ...     print(governor, dep, dependent)  # doctest: +NORMALIZE_WHITESPACE
        ('jumps', 'VBZ') nsubj ('fox', 'NN')
        ('fox', 'NN') det ('The', 'DT')
        ('fox', 'NN') amod ('quick', 'JJ')
        ('fox', 'NN') amod ('brown', 'JJ')
        ('jumps', 'VBZ') nmod ('dog', 'NN')
        ('dog', 'NN') case ('over', 'IN')
        ('dog', 'NN') det ('the', 'DT')
        ('dog', 'NN') amod ('lazy', 'JJ')
        ('jumps', 'VBZ') punct ('.', '.')

    >>> (parse_fox, ), (parse_dog, ) = dep_parser.raw_parse_sents(
    ...     [
    ...         'The quick brown fox jumps over the lazy dog.',
    ...         'The quick grey wolf jumps over the lazy fox.',
    ...     ]
    ... )
    >>> print(parse_fox.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    The DT      4       det
    quick       JJ      4       amod
    brown       JJ      4       amod
    fox NN      5       nsubj
    jumps       VBZ     0       ROOT
    over        IN      9       case
    the DT      9       det
    lazy        JJ      9       amod
    dog NN      5       nmod
    .   .       5       punct

    >>> print(parse_dog.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    The DT      4       det
    quick       JJ      4       amod
    grey        JJ      4       amod
    wolf        NN      5       nsubj
    jumps       VBZ     0       ROOT
    over        IN      9       case
    the DT      9       det
    lazy        JJ      9       amod
    fox NN      5       nmod
    .   .       5       punct

    >>> (parse_dog, ), (parse_friends, ) = dep_parser.parse_sents(
    ...     [
    ...         "I 'm a dog".split(),
    ...         "This is my friends ' cat ( the tabby )".split(),
    ...     ]
    ... )
    >>> print(parse_dog.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    I   PRP     4       nsubj
    'm  VBP     4       cop
    a   DT      4       det
    dog NN      0       ROOT

    >>> print(parse_friends.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    This        DT      6       nsubj
    is  VBZ     6       cop
    my  PRP$    4       nmod:poss
    friends     NNS     6       nmod:poss
    '   POS     4       case
    cat NN      0       ROOT
    -LRB-       -LRB-   9       punct
    the DT      9       det
    tabby       NN      6       appos
    -RRB-       -RRB-   9       punct

    >>> parse_john, parse_mary, = dep_parser.parse_text(
    ...     'John loves Mary. Mary walks.'
    ... )

    >>> print(parse_john.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    John        NNP     2       nsubj
    loves       VBZ     0       ROOT
    Mary        NNP     2       dobj
    .   .       2       punct

    >>> print(parse_mary.to_conll(4))  # doctest: +NORMALIZE_WHITESPACE
    Mary        NNP     2       nsubj
    walks       VBZ     0       ROOT
    .   .       2       punct

    Special cases
    -------------

    Non-breaking space inside of a token.

    >>> len(
    ...     next(
    ...         dep_parser.raw_parse(
    ...             'Anhalt said children typically treat a 20-ounce soda bottle as one '
    ...             'serving, while it actually contains 2 1/2 servings.'
    ...         )
    ...     ).nodes
    ... )
    21

    """

    _OUTPUT_FORMAT = 'conll2007'
    parser_annotator = 'depparse'

    def make_tree(self, result):

        return DependencyGraph(
            (
                ' '.join(items)  # NLTK expects an iterable of strings...
                for n, *items in sorted(transform(result))
            ),
            cell_separator=' ',  # To make sure that a non-breaking space is kept inside of a token.
        )


def transform(sentence):
    for dependency in sentence['basic-dependencies']:

        dependent_index = dependency['dependent']
        token = sentence['tokens'][dependent_index - 1]

        # Return values we don't know as '_'. Also, consider tag and ctag to be
        # equal.
        yield (
            dependent_index,
            '_',
            token['word'],
            token['lemma'],
            token['pos'],
            token['pos'],
            '_',
            str(dependency['governor']),
            dependency['dep'],
            '_',
            '_',
        )


def setup_module(module):
    from nose import SkipTest

    if not requests.get('http://localhost:9000').ok:
        raise SkipTest(
            'Doctests from nltk.parse.stanford are skipped because '
            'the CoreNLP server is not available.'
        )
