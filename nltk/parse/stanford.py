# Natural Language Toolkit: Interface to the Stanford Parser
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import tempfile
import warnings
from subprocess import PIPE

from nltk.data import staging_tempdir
from nltk.internals import find_jar_iter, find_jars_within_path, java
from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph
from nltk.pathsec import validate_model_resource
from nltk.tree import Tree

_stanford_url = "https://nlp.stanford.edu/software/lex-parser.shtml"


class GenericStanfordParser(ParserI):
    """Interface to the Stanford Parser"""

    _MODEL_JAR_PATTERN = r"stanford-parser-(\d+)(\.(\d+))+-models\.jar"
    _JAR = r"stanford-parser\.jar"
    _MAIN_CLASS = "edu.stanford.nlp.parser.lexparser.LexicalizedParser"

    _USE_STDIN = False
    _DOUBLE_SPACED_OUTPUT = False

    def __init__(
        self,
        path_to_jar=None,
        path_to_models_jar=None,
        model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
        encoding="utf8",
        verbose=False,
        java_options="-mx4g",
        corenlp_options="",
    ):
        # find the most recent code and model jar
        stanford_jar = max(
            find_jar_iter(
                self._JAR,
                path_to_jar,
                env_vars=("STANFORD_PARSER", "STANFORD_CORENLP"),
                searchpath=(),
                url=_stanford_url,
                verbose=verbose,
                is_regex=True,
            ),
            key=lambda model_path: os.path.dirname(model_path),
        )

        model_jar = max(
            find_jar_iter(
                self._MODEL_JAR_PATTERN,
                path_to_models_jar,
                env_vars=("STANFORD_MODELS", "STANFORD_CORENLP"),
                searchpath=(),
                url=_stanford_url,
                verbose=verbose,
                is_regex=True,
            ),
            key=lambda model_path: os.path.dirname(model_path),
        )

        # self._classpath = (stanford_jar, model_jar)

        # Adding logging jar files to classpath
        stanford_dir = os.path.split(stanford_jar)[0]
        self._classpath = tuple([model_jar] + find_jars_within_path(stanford_dir))

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
            if line == "":
                if blank:
                    res.append(iter(cur_trees))
                    cur_trees = []
                    blank = False
                elif self._DOUBLE_SPACED_OUTPUT:
                    cur_trees.append(self._make_tree("\n".join(cur_lines)))
                    cur_lines = []
                    blank = True
                else:
                    res.append(iter([self._make_tree("\n".join(cur_lines))]))
                    cur_lines = []
            else:
                cur_lines.append(line)
                blank = False
        return iter(res)

    def parse_sents(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list where each sentence is a list of words.
        Each sentence will be automatically tagged with this StanfordParser instance's
        tagger.
        If whitespaces exists inside a token, then the token will be treated as
        separate tokens.

        :param sentences: Input sentences to parse
        :type sentences: list(list(str))
        :rtype: iter(iter(Tree))
        """
        # Prevent generator exhaustion
        sentences = list(sentences)

        # Security check: Validate individual tokens before joining
        for sentence in sentences:
            for token in sentence:
                if "\n" in token or "\r" in token:
                    raise ValueError("Tokens cannot contain newline characters.")
        cmd = [
            self._MAIN_CLASS,
            "-model",
            self.model_path,
            "-sentences",
            "newline",
            "-outputFormat",
            self._OUTPUT_FORMAT,
            "-tokenized",
            "-escaper",
            "edu.stanford.nlp.process.PTBEscapingProcessor",
        ]
        return self._parse_trees_output(
            self._execute(
                cmd, "\n".join(" ".join(sentence) for sentence in sentences), verbose
            )
        )

    def raw_parse(self, sentence, verbose=False):
        """
        Use StanfordParser to parse a sentence. Takes a sentence as a string;
        before parsing, it will be automatically tokenized and tagged by
        the Stanford Parser.

        :param sentence: Input sentence to parse
        :type sentence: str
        :rtype: iter(Tree)
        """
        return next(self.raw_parse_sents([sentence], verbose))

    def raw_parse_sents(self, sentences, verbose=False):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list of strings.
        Each sentence will be automatically tokenized and tagged by the Stanford Parser.

        :param sentences: Input sentences to parse
        :type sentences: list(str)
        :rtype: iter(iter(Tree))
        """
        # Prevent generator exhaustion
        sentences = list(sentences)
        # Security check: Validate raw sentence strings
        for sentence in sentences:
            if "\n" in sentence or "\r" in sentence:
                raise ValueError("Sentences cannot contain newline characters.")
        cmd = [
            self._MAIN_CLASS,
            "-model",
            self.model_path,
            "-sentences",
            "newline",
            "-outputFormat",
            self._OUTPUT_FORMAT,
        ]
        return self._parse_trees_output(
            self._execute(cmd, "\n".join(sentences), verbose)
        )

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
        # 1. Prevent generator exhaustion
        sentences = list(sentences)

        # 2. Security check: Validate both words and tags for newline characters
        for sentence in sentences:
            for word, tag in sentence:
                if "\n" in word or "\r" in word or "\n" in tag or "\r" in tag:
                    raise ValueError(
                        "Tokens and tags cannot contain newline characters."
                    )

        tag_separator = "/"
        cmd = [
            self._MAIN_CLASS,
            "-model",
            self.model_path,
            "-sentences",
            "newline",
            "-outputFormat",
            self._OUTPUT_FORMAT,
            "-tokenized",
            "-tagSeparator",
            tag_separator,
            "-tokenizerFactory",
            "edu.stanford.nlp.process.WhitespaceTokenizer",
            "-tokenizerMethod",
            "newCoreLabelTokenizerFactory",
        ]
        # We don't need to escape slashes as "splitting is done on the last instance of the character in the token"
        return self._parse_trees_output(
            self._execute(
                cmd,
                "\n".join(
                    " ".join(tag_separator.join(tagged) for tagged in sentence)
                    for sentence in sentences
                ),
                verbose,
            )
        )

    def _validated_extra_options(self, cmd):
        """Bound the caller-supplied ``corenlp_options`` before it joins the argv.

        The string is *split* into separate argv elements, so it can append a
        second ``-model``. Stanford's ``LexicalizedParser`` honours the LAST
        occurrence, which was verified directly against the JVM, so an injected
        option silently replaced the model the guard above had just checked and
        the parser deserialized an arbitrary file instead.

        An option NLTK already set may therefore not be repeated here, and any
        value that looks like a filesystem path is bounded to the data roots. A
        value that is not a path (``xml``, ``key=value``) is left alone, since
        this is a general passthrough for the tool's own settings.
        """
        already_set = {
            argument
            for argument in cmd
            if isinstance(argument, str) and argument.startswith("-")
        }
        validated = []
        for token in self.corenlp_options.split():
            if token.startswith("-"):
                if token in already_set:
                    raise ValueError(
                        f"Security Violation [StanfordParser corenlp_options]: "
                        f"{token!r} is already set by NLTK and may not be "
                        "overridden; the tool would honour the injected value."
                    )
                validated.append(token)
                continue
            if os.path.isabs(token) or "/" in token or "\\" in token:
                token = validate_model_resource(
                    token, context="StanfordParser corenlp_options"
                )
            validated.append(token)
        return validated

    def _execute(self, cmd, input_, verbose=False):
        # Bound `-model` here, at the single hand-off to the JVM, so all three
        # callers are covered and a late reassignment cannot slip past. The argv
        # entry is replaced with the validated string: __fspath__ may answer
        # differently on every call, so the object the callers put in `cmd` could
        # otherwise resolve to a file the guard never saw.
        model = validate_model_resource(self.model_path, context="StanfordParser model")
        if "-model" in cmd:
            cmd[cmd.index("-model") + 1] = model
        encoding = self._encoding
        cmd.extend(["-encoding", encoding])
        if self.corenlp_options:
            cmd.extend(self._validated_extra_options(cmd))

        # Windows is incompatible with NamedTemporaryFile() without passing in delete=False.
        input_file_name = None
        java_succeeded = False
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, dir=staging_tempdir()
            ) as input_file:
                input_file_name = input_file.name
                # Write the actual sentences to the temporary input file
                if isinstance(input_, str) and encoding:
                    input_ = input_.encode(encoding)
                input_file.write(input_)
                input_file.flush()

                # Run the tagger and get the output.
                if self._USE_STDIN:
                    input_file.seek(0)
                    stdout, stderr = java(
                        cmd,
                        classpath=self._classpath,
                        stdin=input_file,
                        stdout=PIPE,
                        stderr=PIPE,
                        options=self.java_options,
                    )
                else:
                    cmd.append(input_file_name)
                    stdout, stderr = java(
                        cmd,
                        classpath=self._classpath,
                        stdout=PIPE,
                        stderr=PIPE,
                        options=self.java_options,
                    )

                # java() returns text (universal_newlines=True); only the older
                # bytes path needs the byte-level NBSP fixups and decode.
                if isinstance(stdout, bytes):
                    stdout = stdout.replace(b"\xc2\xa0", b" ")
                    stdout = stdout.replace(b"\x00\xa0", b" ")
                    stdout = stdout.decode(encoding)
                else:
                    stdout = stdout.replace("\xa0", " ")
                java_succeeded = True
        finally:
            if input_file_name:
                try:
                    os.unlink(input_file_name)
                except FileNotFoundError:
                    pass
                except OSError:
                    if java_succeeded:
                        raise

        return stdout


class StanfordParser(GenericStanfordParser):
    """
    >>> parser=StanfordParser(
    ...     model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"
    ... ) # doctest: +SKIP

    >>> list(parser.raw_parse("the quick brown fox jumps over the lazy dog")) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('NP', [Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['quick']), Tree('JJ', ['brown']),
    Tree('NN', ['fox'])]), Tree('NP', [Tree('NP', [Tree('NNS', ['jumps'])]), Tree('PP', [Tree('IN', ['over']),
    Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['lazy']), Tree('NN', ['dog'])])])])])])]

    >>> sum([list(dep_graphs) for dep_graphs in parser.raw_parse_sents((
    ...     "the quick brown fox jumps over the lazy dog",
    ...     "the quick grey wolf jumps over the lazy fox"
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('NP', [Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['quick']), Tree('JJ', ['brown']),
    Tree('NN', ['fox'])]), Tree('NP', [Tree('NP', [Tree('NNS', ['jumps'])]), Tree('PP', [Tree('IN', ['over']),
    Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['lazy']), Tree('NN', ['dog'])])])])])]), Tree('ROOT', [Tree('NP',
    [Tree('NP', [Tree('DT', ['the']), Tree('JJ', ['quick']), Tree('JJ', ['grey']), Tree('NN', ['wolf'])]), Tree('NP',
    [Tree('NP', [Tree('NNS', ['jumps'])]), Tree('PP', [Tree('IN', ['over']), Tree('NP', [Tree('DT', ['the']),
    Tree('JJ', ['lazy']), Tree('NN', ['fox'])])])])])])]

    >>> sum([list(dep_graphs) for dep_graphs in parser.parse_sents((
    ...     "I 'm a dog".split(),
    ...     "This is my friends ' cat ( the tabby )".split(),
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('S', [Tree('NP', [Tree('PRP', ['I'])]), Tree('VP', [Tree('VBP', ["'m"]),
    Tree('NP', [Tree('DT', ['a']), Tree('NN', ['dog'])])])])]), Tree('ROOT', [Tree('S', [Tree('NP',
    [Tree('DT', ['This'])]), Tree('VP', [Tree('VBZ', ['is']), Tree('NP', [Tree('NP', [Tree('NP', [Tree('PRP$', ['my']),
    Tree('NNS', ['friends']), Tree('POS', ["'"])]), Tree('NN', ['cat'])]), Tree('PRN', [Tree('-LRB-', [Tree('', []),
    Tree('NP', [Tree('DT', ['the']), Tree('NN', ['tabby'])]), Tree('-RRB-', [])])])])])])])]

    >>> sum([list(dep_graphs) for dep_graphs in parser.tagged_parse_sents((
    ...     (
    ...         ("The", "DT"),
    ...         ("quick", "JJ"),
    ...         ("brown", "JJ"),
    ...         ("fox", "NN"),
    ...         ("jumped", "VBD"),
    ...         ("over", "IN"),
    ...         ("the", "DT"),
    ...         ("lazy", "JJ"),
    ...         ("dog", "NN"),
    ...         (".", "."),
    ...     ),
    ... ))],[]) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('ROOT', [Tree('S', [Tree('NP', [Tree('DT', ['The']), Tree('JJ', ['quick']), Tree('JJ', ['brown']),
    Tree('NN', ['fox'])]), Tree('VP', [Tree('VBD', ['jumped']), Tree('PP', [Tree('IN', ['over']), Tree('NP',
    [Tree('DT', ['the']), Tree('JJ', ['lazy']), Tree('NN', ['dog'])])])]), Tree('.', ['.'])])])]
    """

    _OUTPUT_FORMAT = "penn"

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The StanfordParser will be deprecated\n"
            "Please use \033[91mnltk.parse.corenlp.CoreNLPParser\033[0m instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)

    def _make_tree(self, result):
        return Tree.fromstring(result)


class StanfordDependencyParser(GenericStanfordParser):
    """
    >>> dep_parser=StanfordDependencyParser(
    ...     model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"
    ... ) # doctest: +SKIP

    >>> [parse.tree() for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over', 'the', 'lazy'])])]

    >>> [list(parse.triples()) for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [[((u'jumps', u'VBZ'), u'nsubj', (u'fox', u'NN')), ((u'fox', u'NN'), u'det', (u'The', u'DT')),
    ((u'fox', u'NN'), u'amod', (u'quick', u'JJ')), ((u'fox', u'NN'), u'amod', (u'brown', u'JJ')),
    ((u'jumps', u'VBZ'), u'nmod', (u'dog', u'NN')), ((u'dog', u'NN'), u'case', (u'over', u'IN')),
    ((u'dog', u'NN'), u'det', (u'the', u'DT')), ((u'dog', u'NN'), u'amod', (u'lazy', u'JJ'))]]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.raw_parse_sents((
    ...     "The quick brown fox jumps over the lazy dog.",
    ...     "The quick grey wolf jumps over the lazy fox."
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over', 'the', 'lazy'])]),
    Tree('jumps', [Tree('wolf', ['The', 'quick', 'grey']), Tree('fox', ['over', 'the', 'lazy'])])]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.parse_sents((
    ...     "I 'm a dog".split(),
    ...     "This is my friends ' cat ( the tabby )".split(),
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('dog', ['I', "'m", 'a']), Tree('cat', ['This', 'is', Tree('friends', ['my', "'"]), Tree('tabby', ['the'])])]

    >>> sum([[list(parse.triples()) for parse in dep_graphs] for dep_graphs in dep_parser.tagged_parse_sents((
    ...     (
    ...         ("The", "DT"),
    ...         ("quick", "JJ"),
    ...         ("brown", "JJ"),
    ...         ("fox", "NN"),
    ...         ("jumped", "VBD"),
    ...         ("over", "IN"),
    ...         ("the", "DT"),
    ...         ("lazy", "JJ"),
    ...         ("dog", "NN"),
    ...         (".", "."),
    ...     ),
    ... ))],[]) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [[((u'jumped', u'VBD'), u'nsubj', (u'fox', u'NN')), ((u'fox', u'NN'), u'det', (u'The', u'DT')),
    ((u'fox', u'NN'), u'amod', (u'quick', u'JJ')), ((u'fox', u'NN'), u'amod', (u'brown', u'JJ')),
    ((u'jumped', u'VBD'), u'nmod', (u'dog', u'NN')), ((u'dog', u'NN'), u'case', (u'over', u'IN')),
    ((u'dog', u'NN'), u'det', (u'the', u'DT')), ((u'dog', u'NN'), u'amod', (u'lazy', u'JJ'))]]

    """

    _OUTPUT_FORMAT = "conll2007"

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The StanfordDependencyParser will be deprecated\n"
            "Please use \033[91mnltk.parse.corenlp.CoreNLPDependencyParser\033[0m instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)

    def _make_tree(self, result):
        return DependencyGraph(result, top_relation_label="root")


class StanfordNeuralDependencyParser(GenericStanfordParser):
    """
    >>> from nltk.parse.stanford import StanfordNeuralDependencyParser # doctest: +SKIP
    >>> dep_parser=StanfordNeuralDependencyParser(java_options='-mx4g')# doctest: +SKIP

    >>> [parse.tree() for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over', 'the', 'lazy']), '.'])]

    >>> [list(parse.triples()) for parse in dep_parser.raw_parse("The quick brown fox jumps over the lazy dog.")] # doctest: +NORMALIZE_WHITESPACE +SKIP
    [[((u'jumps', u'VBZ'), u'nsubj', (u'fox', u'NN')), ((u'fox', u'NN'), u'det',
    (u'The', u'DT')), ((u'fox', u'NN'), u'amod', (u'quick', u'JJ')), ((u'fox', u'NN'),
    u'amod', (u'brown', u'JJ')), ((u'jumps', u'VBZ'), u'nmod', (u'dog', u'NN')),
    ((u'dog', u'NN'), u'case', (u'over', u'IN')), ((u'dog', u'NN'), u'det',
    (u'the', u'DT')), ((u'dog', u'NN'), u'amod', (u'lazy', u'JJ')), ((u'jumps', u'VBZ'),
    u'punct', (u'.', u'.'))]]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.raw_parse_sents((
    ...     "The quick brown fox jumps over the lazy dog.",
    ...     "The quick grey wolf jumps over the lazy fox."
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('jumps', [Tree('fox', ['The', 'quick', 'brown']), Tree('dog', ['over',
    'the', 'lazy']), '.']), Tree('jumps', [Tree('wolf', ['The', 'quick', 'grey']),
    Tree('fox', ['over', 'the', 'lazy']), '.'])]

    >>> sum([[parse.tree() for parse in dep_graphs] for dep_graphs in dep_parser.parse_sents((
    ...     "I 'm a dog".split(),
    ...     "This is my friends ' cat ( the tabby )".split(),
    ... ))], []) # doctest: +NORMALIZE_WHITESPACE +SKIP
    [Tree('dog', ['I', "'m", 'a']), Tree('cat', ['This', 'is', Tree('friends',
    ['my', "'"]), Tree('tabby', ['-LRB-', 'the', '-RRB-'])])]
    """

    _OUTPUT_FORMAT = "conll"
    _MAIN_CLASS = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
    _JAR = r"stanford-corenlp-(\d+)(\.(\d+))+\.jar"
    _MODEL_JAR_PATTERN = r"stanford-corenlp-(\d+)(\.(\d+))+-models\.jar"
    _USE_STDIN = True
    _DOUBLE_SPACED_OUTPUT = True

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The StanfordNeuralDependencyParser will be deprecated\n"
            "Please use \033[91mnltk.parse.corenlp.CoreNLPDependencyParser\033[0m instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)
        self.corenlp_options += "-annotators tokenize,ssplit,pos,depparse"

    def tagged_parse_sents(self, sentences, verbose=False):
        """
        Currently unimplemented because the neural dependency parser (and
        the StanfordCoreNLP pipeline class) doesn't support passing in pre-
        tagged tokens.
        """
        raise NotImplementedError(
            "tagged_parse[_sents] is not supported by "
            "StanfordNeuralDependencyParser; use "
            "parse[_sents] or raw_parse[_sents] instead."
        )

    def _make_tree(self, result):
        return DependencyGraph(result, top_relation_label="ROOT")
