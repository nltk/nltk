# Natural Language Toolkit: Interface to BLLIP Parser
#
# Author: David McClosky <dmcc@bigasterisk.com>
#
# Copyright (C) 2001-2014 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_function

from nltk.parse.api import ParserI
from nltk.tree import Tree

try:
    from bllipparser import RerankingParser
    from bllipparser.RerankingParser import get_unified_model_parameters

    def _check_bllip_import_success():
        pass
except ImportError as ie:
    def _check_bllip_import_success(ie=ie):
        raise ImportError("Couldn't import bllipparser module: %s" % ie)


def _nbest_list_item_to_tree(nbest_list_item):
    return Tree(str(nbest_list_item.ptb_parse))


def _get_top_parse(nbest_list):
    if len(nbest_list):
        return _nbest_list_item_to_tree(nbest_list[0])
    else:
        return None


def _ensure_ascii(words):
    try:
        for i, word in enumerate(words):
            word.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError("Token %d (%r) is non-ASCII. BLLIP Parser currently doesn't support non-ASCII inputs." % (i, word))


class BllipParser(ParserI):

    """
    Interface for parsing with BLLIP Parser using a SWIG wrapper.
    BllipParser objects can be constructed manually using their
    constructor or with the ``BllipParser.from_unified_model_dir``
    class method. The latter is generally easier if you have a unified
    model directory. Unified model directories can be obtained with the
    command-line utility ``python -m bllipparser.ModelFetcher`` or the
    ``bllipparser.ModelFetcher.download_and_install_model`` function
    in Python.

    Note that BLLIP Parser is not currently threadsafe. Since this module
    uses a SWIG interface, it is potentially unsafe to create multiple
    ``BllipParser`` objects in the same process. BLLIP Parser may have
    issues with non-ASCII text currently and will raise an error if
    given any.

    See http://pypi.python.org/pypi/bllipparser/ for more information
    on BLLIP Parser's Python interface.

    References:

    Charniak, Eugene. "A maximum-entropy-inspired parser." Proceedings of
    the 1st North American chapter of the Association for Computational
    Linguistics conference. Association for Computational Linguistics,
    2000.

    Charniak, Eugene, and Mark Johnson. "Coarse-to-fine n-best parsing
    and MaxEnt discriminative reranking." Proceedings of the 43rd Annual
    Meeting on Association for Computational Linguistics. Association
    for Computational Linguistics, 2005.

    Basic usage:

    >>> from bllipparser.ModelFetcher import download_and_install_model
    >>> model_dir = download_and_install_model('WSJ', '/tmp/models', verbose=False)
    >>> bllip = BllipParser.from_unified_model_dir(model_dir)

    # 1-best parsing
    >>> print(bllip.parse('British left waffles on Falklands .'.split()))
    (S1
      (S
        (NP (JJ British) (NN left))
        (VP (VBZ waffles) (PP (IN on) (NP (NNP Falklands))))
        (. .)))
    >>> print(bllip.parse('I saw the man with the telescope .'.split()))
    (S1
      (S
        (NP (PRP I))
        (VP
          (VBD saw)
          (NP (DT the) (NN man))
          (PP (IN with) (NP (DT the) (NN telescope))))
        (. .)))

    # n-best parsing (default n=50)
    >>> for parse in bllip.nbest_parse('Hey Jude'.split())[:5]:
    ...     print(parse)
    (S1 (NP (NNP Hey) (NNP Jude)))
    (S1 (S (NP (NNP Hey) (NNP Jude))))
    (S1 (ADJP (NNP Hey) (NNP Jude)))
    (S1 (NP (NP (NNP Hey)) (NP (NNP Jude))))
    (S1 (X (NP (NNP Hey) (NNP Jude))))

    # n-best parsing with a smaller n
    >>> for i, parse in enumerate(bllip.nbest_parse('Just 10 parses'.split(), n=3)):
    ...     print(i, parse)
    0 (S1 (NP (QP (RB Just) (CD 10)) (NNS parses)))
    1 (S1 (NP (RB Just) (CD 10) (NNS parses)))
    2 (S1 (NP (QP (RB Just) (CD 10)) (NN parses)))

    # this "sentence" is known to fail under the WSJ model
    >>> print(bllip.parse('# ! ? : -'.split()))
    None
    >>> print(bllip.nbest_parse('# ! ? : -'.split()))
    []

    # using external POS tag constraints to force tree to be 'NN'
    >>> print(bllip.tagged_parse([('A', None), ('tree', 'NN')]))
    (S1 (NP (DT A) (NN tree)))

    # forcing 'A' to be 'DT' and 'tree' to be 'NNP'
    >>> print(bllip.tagged_parse([('A', 'DT'), ('tree', 'NNP')]))
    (S1 (NP (DT A) (NNP tree)))

    # forcing 'A' to be 'NNP'
    >>> print(bllip.tagged_parse([('A', 'NNP'), ('tree', None)]))
    (S1 (NP (NNP A) (NN tree)))

    # using tag constraints with n-best parsing
    >>> for parse in bllip.tagged_nbest_parse([('A', 'NNP'), ('tree', None)])[:5]:
    ...     print(parse)
    (S1 (NP (NNP A) (NN tree)))
    (S1 (FRAG (NP (NNP A) (NN tree))))
    (S1 (S (NP (NNP A) (NN tree))))
    (S1 (NP (NP (NNP A)) (NP (NN tree))))
    (S1 (S (NP (NNP A)) (VP (NN tree))))

    >>> for parse in bllip.tagged_nbest_parse([('A', 'DT'), ('tree', 'NN')], n=3):
    ...     print(parse)
    (S1 (NP (DT A) (NN tree)))
    (S1 (FRAG (NP (DT A) (NN tree))))
    (S1 (S (NP (DT A) (NN tree))))
    """

    def __init__(self, parser_model=None, reranker_features=None,
                 reranker_weights=None, parser_options=None,
                 reranker_options=None):
        """
        :param parser_model: Path to parser model directory
        :type parser_model: str

        :param reranker_features: Path the reranker model's features file
        :type reranker_features: str

        :param reranker_weights: Path the reranker model's weights file
        :type reranker_weights: str

        :param parser_options: optional dictionary of parser options, see
        bllipparser.RerankingParser.RerankingParser.load_parser_options()
        for more information.
        :type parser_options: dict(str)

        :param reranker_options: optional
        dictionary of reranker options, see
        bllipparser.RerankingParser.RerankingParser.load_reranker_model()
        for more information.
        :type reranker_options: dict(str)
        """
        _check_bllip_import_success()

        parser_options = parser_options or {}
        reranker_options = reranker_options or {}

        self.rrp = RerankingParser()
        self.rrp.load_parser_model(parser_model, **parser_options)
        if reranker_features and reranker_weights:
            self.rerank = True
            self.rrp.load_reranker_model(features_filename=reranker_features,
                                         weights_filename=reranker_weights,
                                         **reranker_options)
        else:
            self.rerank = False

    def parse(self, sentence):
        """
        Use BLLIP Parser to parse a sentence.  Takes a sentence as a list
        of words; it will be automatically tagged with this BLLIP Parser
        instance's tagger. Returns ``None`` if no parse is available
        (e.g., due to a parse failure).

        :return: The most likely parse of the sentence.

        :param sentence: Input sentence to parse
        :type sentence: list(str)
        :rtype: Tree
        """
        _ensure_ascii(sentence)
        nbest_list = self.rrp.parse(sentence, rerank=self.rerank)
        return _get_top_parse(nbest_list)

    def nbest_parse(self, sentence, n=None):
        """
        Use BLLIP Parser to parse a sentence.  Takes a sentence as a
        list of words; it will be automatically tagged with this BLLIP
        Parser instance's tagger. Returns an empty list if no parse is
        available (e.g., due to a parse failure).

        :return: A list of parse trees that represent possible structures
        for the given sentence, sorted from most likely to least likely.
        If ``n`` is specified, then the returned list will contain at most
        ``n`` parse trees.

        :param sentence: The sentence to be parsed
        :type sentence: list(str)
        :param n: The maximum number of trees to return.
        :type n: int
        :rtype: list(Tree)
        """
        _ensure_ascii(sentence)
        nbest_list = self.rrp.parse(sentence, rerank=self.rerank)
        if n is not None:
            nbest_list = nbest_list[:n]

        return [_nbest_list_item_to_tree(item) for item in nbest_list]

    def _parse_with_tag_constraints(self, word_and_tag_pairs):
        words = []
        tag_map = {}
        for i, (word, tag) in enumerate(word_and_tag_pairs):
            words.append(word)
            if tag is not None:
                tag_map[i] = tag

        _ensure_ascii(words)
        nbest_list = self.rrp.parse_tagged(words, tag_map, rerank=self.rerank)
        return nbest_list

    def tagged_parse(self, sentence):
        """
        Use BLLIP to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized
        and tagged. BLLIP will attempt to use the tags provided but may
        use others if it can't come up with a complete parse subject
        to those constraints. You may also specify a tag as ``None``
        to leave a token's tag unconstrained.

        :return: The most likely parse of the sentence.

        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :rtype: Tree
        """
        nbest_list = self._parse_with_tag_constraints(sentence)
        return _get_top_parse(nbest_list)

    def tagged_nbest_parse(self, sentence, n=None):
        """
        Use BLLIP to parse a sentence. Takes a sentence as a list of
        (word, tag) tuples; the sentence must have already been tokenized
        and tagged. BLLIP will attempt to use the tags provided but may
        use others if it can't come up with a complete parse subject to
        those constraints. You may also specify a tag as None to leave
        a token's tag unconstrained.  If ``n`` is specified, then the
        returned list will contain at most ``n`` parse trees.

        :return: A list of parse trees that represent possible structures
        for the given sentence, sorted from most likely to least likely.
        If ``n`` is specified, then the returned list will contain at most
        ``n`` parse trees.

        :param sentence: Input sentence to parse
        :type sentence: list(tuple(str, str))
        :param n: The maximum number of trees to return.
        :type n: int
        :rtype: list(Tree)
        """
        nbest_list = self._parse_with_tag_constraints(sentence)
        if n is not None:
            nbest_list = nbest_list[:n]

        return [_nbest_list_item_to_tree(item) for item in nbest_list[:n]]

    @classmethod
    def from_unified_model_dir(this_class, model_dir, parser_options=None,
                               reranker_options=None):
        """
        Create a BllipParser from a unified parsing model directory.
        Unified parsing model directories are a standardized way of
        storing BLLIP parser and reranker models together on disk.
        See ``bllipparser.RerankingParser.get_unified_model_parameters()``
        for more information about unified model directories.

        :return: A BllipParser object using the models in the model
        directory.

        :param model_dir: Path to the unified model directory.
        :type model_dir: str
        :param parser_options: optional dictionary of parser options, see
        bllipparser.RerankingParser.RerankingParser.load_parser_options()
        for more information.
        :type parser_options: dict(str)
        :param reranker_options: optional
        dictionary of reranker options, see
        bllipparser.RerankingParser.RerankingParser.load_reranker_model()
        for more information.
        :type reranker_options: dict(str)
        :rtype: BllipParser
        """
        (parser_model_dir, reranker_features_filename,
         reranker_weights_filename) = get_unified_model_parameters(model_dir)
        return this_class(parser_model_dir, reranker_features_filename,
                          reranker_weights_filename, parser_options,
                          reranker_options)


def demo():
    """This assumes bllipparser is installed."""
    import nltk
    # download and install a basic unified parsing model
    try:
        nltk.downloader('bllip-wsj', download_dir='/tmp', raise_on_error=True)
        model_dir = '/tmp/models/bllip-wsj'
    except:
        # this is just here temporarily until nltk_data has the BLLIP WSJ model
        from bllipparser.ModelFetcher import download_and_install_model
        model_dir = download_and_install_model('WSJ', '/tmp/models',
                                               verbose=True)

    print('Loading models...')
    # the easiest way to get started is to use a unified model
    bllip = BllipParser.from_unified_model_dir(model_dir)
    print('Loaded!')

    print(bllip.parse('British left waffles on Falklands .'.split()).pprint())
    print(bllip.parse('I saw the man with the telescope .'.split()).pprint())

    # n-best parsing (default n=50)
    for i, parse in enumerate(bllip.nbest_parse('Hey Jude'.split())):
        print('nbest parses', i, parse)
    print()
    # n-best parsing with a smaller n
    for i, parse in enumerate(bllip.nbest_parse('Just 10 parses'.split(),
                                                n=10)):
        print('10best parses', i, parse)
    print()

    # this "sentence" is known to fail under the WSJ model
    print('1best with failed parse', bllip.parse('# ! ? : -'.split()))
    print('nbest with failed parse', bllip.nbest_parse('# ! ? : -'.split()))

    # using external POS tag constraints
    print("forcing 'tree' to be 'NN'",
          bllip.tagged_parse([('A', None), ('tree', 'NN')]))
    print("forcing 'A' to be 'DT' and 'tree' to be 'NNP'",
          bllip.tagged_parse([('A', 'DT'), ('tree', 'NNP')]))
    print("forcing 'A' to be 'NNP'",
          bllip.tagged_parse([('A', 'NNP'), ('tree', None)]))

    # using external POS tag constraints in n-best mode
    for i, parse in enumerate(bllip.tagged_nbest_parse([('A', 'NNP'),
                                                        ('tree', None)])):
        print('tagged nbest parse', i, parse)
    print()
    # using external POS tag constraints in n-best mode with a smaller n
    for i, parse in enumerate(bllip.tagged_nbest_parse([('A', 'DT'),
                                                        ('tree', 'NN')], n=3)):
        print('tagged 3best parse', i, parse)


def setup_module(module):
    from nose import SkipTest

    try:
        _check_bllip_import_success()
    except ImportError:
        raise SkipTest('doctests from nltk.parse.bllip are skipped because the bllipparser module is not installed')


if __name__ == '__main__':
    demo()
