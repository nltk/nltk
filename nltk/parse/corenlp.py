# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the CoreNLP REST API.
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Dmitrijs Milajevs <dimazest@gmail.com>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals

import re
import json
import time
import socket

from nltk.internals import find_jar_iter, config_java, java, _java_options

from nltk.parse.api import ParserI
from nltk.tokenize.api import TokenizerI
from nltk.parse.dependencygraph import DependencyGraph
from nltk.tree import Tree

_stanford_url = 'http://stanfordnlp.github.io/CoreNLP/'


class CoreNLPServerError(EnvironmentError):
    """Exceptions associated with the Core NLP server."""


def try_port(port=0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', port))

    p = sock.getsockname()[1]
    sock.close()

    return p


class CoreNLPServer(object):

    _MODEL_JAR_PATTERN = r'stanford-corenlp-(\d+)\.(\d+)\.(\d+)-models\.jar'
    _JAR = r'stanford-corenlp-(\d+)\.(\d+)\.(\d+)\.jar'

    def __init__(
        self, path_to_jar=None, path_to_models_jar=None, verbose=False,
        java_options=None, corenlp_options=None, port=None,
    ):

        if corenlp_options is None:
            corenlp_options = [
                '-preload', 'tokenize,ssplit,pos,lemma,parse,depparse',
            ]

        jars = list(find_jar_iter(
            self._JAR,
            path_to_jar,
            env_vars=('CORENLP', ),
            searchpath=(),
            url=_stanford_url,
            verbose=verbose,
            is_regex=True,
        ))

        # find the most recent code and model jar
        stanford_jar = max(
            jars,
            key=lambda model_name: re.match(self._JAR, model_name)
        )

        if port is None:
            try:
                port = try_port(9000)
            except socket.error:
                port = try_port()
                corenlp_options.append(str(port))
        else:
            try_port(port)

        self.url = 'http://localhost:{}'.format(port)

        model_jar = max(
            find_jar_iter(
                self._MODEL_JAR_PATTERN,
                path_to_models_jar,
                env_vars=('CORENLP_MODELS', ),
                searchpath=(),
                url=_stanford_url,
                verbose=verbose,
                is_regex=True,
            ),
            key=lambda model_name: re.match(self._MODEL_JAR_PATTERN, model_name)
        )

        self.verbose = verbose

        self._classpath = stanford_jar, model_jar

        self.corenlp_options = corenlp_options
        self.java_options = java_options or ['-mx2g']

    def start(self):
        import requests

        cmd = ['edu.stanford.nlp.pipeline.StanfordCoreNLPServer']

        if self.corenlp_options:
            cmd.extend(self.corenlp_options)

        # Configure java.
        default_options = ' '.join(_java_options)
        config_java(options=self.java_options, verbose=self.verbose)

        try:
            # TODO: it's probably a bad idea to pipe stdout, as it will
            #       accumulate when lots of text is being parsed.
            self.popen = java(
                cmd,
                classpath=self._classpath,
                blocking=False,
                stdout='pipe',
                stderr='pipe',
            )
        finally:
            # Return java configurations to their default values.
            config_java(options=default_options, verbose=self.verbose)

        # Check that the server is istill running.
        returncode = self.popen.poll()
        if returncode is not None:
            _, stderrdata = self.popen.communicate()
            raise CoreNLPServerError(
                returncode,
                'Could not start the server. '
                'The error was: {}'.format(stderrdata.decode('ascii'))
            )

        for i in range(30):
            try:
                response = requests.get(requests.compat.urljoin(self.url, 'live'))
            except requests.exceptions.ConnectionError:
                time.sleep(1)
            else:
                if response.ok:
                    break
        else:
            raise CoreNLPServerError(
                'Could not connect to the server.'
            )

        for i in range(60):
            try:
                response = requests.get(requests.compat.urljoin(self.url, 'ready'))
            except requests.exceptions.ConnectionError:
                time.sleep(1)
            else:
                if response.ok:
                    break
        else:
            raise CoreNLPServerError(
                'The server is not ready.'
            )

    def stop(self):
        self.popen.terminate()
        self.popen.wait()

    def __enter__(self):
        self.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class GenericCoreNLPParser(ParserI, TokenizerI):
    """Interface to the CoreNLP Parser."""

    def __init__(self, url='http://localhost:9000', encoding='utf8'):
        import requests

        self.url = url
        self.encoding = encoding

        self.session = requests.Session()

    def parse_sents(self, sentences, *args, **kwargs):
        """Parse multiple sentences.

        Takes multiple sentences as a list where each sentence is a list of
        words. Each sentence will be automatically tagged with this
        CoreNLPParser instance's tagger.

        If a whitespace exists inside a token, then the token will be treated as
        several tokens.

        :param sentences: Input sentences to parse
        :type sentences: list(list(str))
        :rtype: iter(iter(Tree))
        """

        sentences = (' '.join(words) for words in sentences)
        return self.raw_parse_sents(sentences, *args, **kwargs)

    def raw_parse(self, sentence, properties=None, *args, **kwargs):
        """Parse a sentence.

        Takes a sentence as a string; before parsing, it will be automatically
        tokenized and tagged by the CoreNLP Parser.

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
            timeout=60,
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
        """Parse multiple sentences.

        Takes multiple sentences as a list of strings. Each sentence will be
        automatically tokenized and tagged.

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

    def parse_text(self, text, *args, **kwargs):
        """Parse a piece of text.

        The text might contain several sentences which will be split by CoreNLP.

        :param str text: text to be split.
        :returns: an iterable of syntactic structures.  # TODO: should it be an iterable of iterables?

        """
        parsed_data = self.api_call(text, *args, **kwargs)

        for parse in parsed_data['sentences']:
            yield self.make_tree(parse)

    def tokenize(self, text, properties=None):
        """Tokenize a string of text.

        >>> parser = CoreNLPParser(url='http://localhost:9000')

        >>> text = 'Good muffins cost $3.88\\nin New York.  Please buy me\\ntwo of them.\\nThanks.'
        >>> list(parser.tokenize(text))
        ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.', 'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']

        >>> s = "The colour of the wall is blue."
        >>> list(
        ...     parser.tokenize(
        ...         'The colour of the wall is blue.',
        ...             properties={'tokenize.options': 'americanize=true'},
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


class CoreNLPParser(GenericCoreNLPParser):
    """
    >>> parser = CoreNLPParser(url='http://localhost:9000')

    >>> next(
    ...     parser.raw_parse('The quick brown fox jumps over the lazy dog.')
    ... ).pretty_print()  # doctest: +NORMALIZE_WHITESPACE
                         ROOT
                          |
                          S
           _______________|__________________________
          |                         VP               |
          |                _________|___             |
          |               |             PP           |
          |               |     ________|___         |
          NP              |    |            NP       |
      ____|__________     |    |     _______|____    |
     DT   JJ    JJ   NN  VBZ   IN   DT      JJ   NN  .
     |    |     |    |    |    |    |       |    |   |
    The quick brown fox jumps over the     lazy dog  .

    >>> (parse_fox, ), (parse_wolf, ) = parser.raw_parse_sents(
    ...     [
    ...         'The quick brown fox jumps over the lazy dog.',
    ...         'The quick grey wolf jumps over the lazy fox.',
    ...     ]
    ... )

    >>> parse_fox.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
                         ROOT
                          |
                          S
           _______________|__________________________
          |                         VP               |
          |                _________|___             |
          |               |             PP           |
          |               |     ________|___         |
          NP              |    |            NP       |
      ____|__________     |    |     _______|____    |
     DT   JJ    JJ   NN  VBZ   IN   DT      JJ   NN  .
     |    |     |    |    |    |    |       |    |   |
    The quick brown fox jumps over the     lazy dog  .

    >>> parse_wolf.pretty_print()  # doctest: +NORMALIZE_WHITESPACE
                         ROOT
                          |
                          S
           _______________|__________________________
          |                         VP               |
          |                _________|___             |
          |               |             PP           |
          |               |     ________|___         |
          NP              |    |            NP       |
      ____|_________      |    |     _______|____    |
     DT   JJ   JJ   NN   VBZ   IN   DT      JJ   NN  .
     |    |    |    |     |    |    |       |    |   |
    The quick grey wolf jumps over the     lazy fox  .

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
    20

    >>> next(
    ...     parser.raw_parse(
    ...         "The broader Standard & Poor's 500 Index <.SPX> was 0.46 points lower, or "
    ...         '0.05 percent, at 997.02.'
    ...     )
    ... ).height()
    9

    """

    _OUTPUT_FORMAT = 'penn'
    parser_annotator = 'parse'

    def make_tree(self, result):
        return Tree.fromstring(result['parse'])


class CoreNLPDependencyParser(GenericCoreNLPParser):
    """Dependency parser.

    >>> dep_parser = CoreNLPDependencyParser(url='http://localhost:9000')

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

    Phone  numbers.

    >>> len(
    ...     next(
    ...         dep_parser.raw_parse('This is not going to crash: 01 111 555.')
    ...     ).nodes
    ... )
    10

    """

    _OUTPUT_FORMAT = 'conll2007'
    parser_annotator = 'depparse'

    def make_tree(self, result):

        return DependencyGraph(
            (
                ' '.join(n_items[1:])  # NLTK expects an iterable of strings...
                for n_items in sorted(transform(result))
            ),
            cell_separator=' ',  # To make sure that a non-breaking space is kept inside of a token.
        )


def transform(sentence):
    for dependency in sentence['basicDependencies']:

        dependent_index = dependency['dependent']
        token = sentence['tokens'][dependent_index - 1]

        # Return values that we don't know as '_'. Also, consider tag and ctag
        # to be equal.
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

    global server
    try:
        server = CoreNLPServer(port=9000)
    except LookupError as e:
        raise SkipTest('Could not instantiate CoreNLPServer.')

    try:
        server.start()
    except CoreNLPServerError as e:
        raise SkipTest(
            'Skipping CoreNLP tests because the server could not be started. '
            'Make sure that the 9000 port is free. '
            '{}'.format(e.strerror)
        )


def teardown_module(module):
    server.stop()
