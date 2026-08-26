# Natural Language Toolkit: Interface to MaltParser
#
# Author: Dan Garrette <dhgarrette@gmail.com>
# Contributor: Liling Tan, Mustufain, osamamukhtar11
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import atexit
import inspect
import os
import shutil
import sys
import tempfile

from nltk.data import ZipFilePathPointer, make_staging_dir
from nltk.internals import (
    find_dir,
    find_file,
    find_jars_within_path,
    java,
)
from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph
from nltk.parse.util import taggedsents_to_conll
from nltk.pathsec import validate_model_resource, validate_path, validate_tool_path


def malt_regex_tagger():
    from nltk.tag import RegexpTagger

    _tagger = RegexpTagger(
        [
            (r"\.$", "."),
            (r"\,$", ","),
            (r"\?$", "?"),  # fullstop, comma, Qmark
            (r"\($", "("),
            (r"\)$", ")"),  # round brackets
            (r"\[$", "["),
            (r"\]$", "]"),  # square brackets
            (r"^-?[0-9]+(\.[0-9]+)?$", "CD"),  # cardinal numbers
            (r"(The|the|A|a|An|an)$", "DT"),  # articles
            (r"(He|he|She|she|It|it|I|me|Me|You|you)$", "PRP"),  # pronouns
            (r"(His|his|Her|her|Its|its)$", "PRP$"),  # possessive
            (r"(my|Your|your|Yours|yours)$", "PRP$"),  # possessive
            (r"(on|On|in|In|at|At|since|Since)$", "IN"),  # time prepopsitions
            (r"(for|For|ago|Ago|before|Before)$", "IN"),  # time prepopsitions
            (r"(till|Till|until|Until)$", "IN"),  # time prepopsitions
            (r"(by|By|beside|Beside)$", "IN"),  # space prepopsitions
            (r"(under|Under|below|Below)$", "IN"),  # space prepopsitions
            (r"(over|Over|above|Above)$", "IN"),  # space prepopsitions
            (r"(across|Across|through|Through)$", "IN"),  # space prepopsitions
            (r"(into|Into|towards|Towards)$", "IN"),  # space prepopsitions
            (r"(onto|Onto|from|From)$", "IN"),  # space prepopsitions
            (r".*able$", "JJ"),  # adjectives
            (r".*ness$", "NN"),  # nouns formed from adjectives
            (r".*ly$", "RB"),  # adverbs
            (r".*s$", "NNS"),  # plural nouns
            (r".*ing$", "VBG"),  # gerunds
            (r".*ed$", "VBD"),  # past tense verbs
            (r".*", "NN"),  # nouns (default)
        ]
    )
    return _tagger.tag


def find_maltparser(parser_dirname):
    """
    A module to find MaltParser .jar file and its dependencies.
    """
    # Accept str or os.PathLike uniformly (find_dir() requires a str).
    parser_dirname = os.fspath(parser_dirname)
    # Only accept an explicit *absolute* directory as-is. A relative name must
    # not be resolved against the current working directory: an attacker able to
    # write to the CWD could otherwise plant a ``maltparser-*/`` directory there
    # and have its jars placed on the Java classpath (and its ``org.maltparser``
    # main class executed), overriding a trusted ``MALT_PARSER`` -- an untrusted
    # search path (CWE-426). A relative name is resolved through ``MALT_PARSER``.
    if os.path.isabs(parser_dirname) and os.path.isdir(parser_dirname):
        _malt_dir = parser_dirname
    else:  # Try to find path to maltparser directory in environment variables.
        _malt_dir = find_dir(parser_dirname, env_vars=("MALT_PARSER",))
    # Checks that that the found directory contains all the necessary .jar
    malt_dependencies = ["", "", ""]
    _malt_jars = set(find_jars_within_path(_malt_dir))
    _jars = {os.path.split(jar)[1] for jar in _malt_jars}
    malt_dependencies = {"log4j.jar", "libsvm.jar", "liblinear-1.8.jar"}

    assert malt_dependencies.issubset(_jars)
    assert any(
        filter(lambda i: i.startswith("maltparser-") and i.endswith(".jar"), _jars)
    )
    return list(_malt_jars)


def find_malt_model(model_filename):
    """
    A module to find pre-trained MaltParser model.
    """
    if model_filename is None:
        return "malt_temp.mco"
    elif os.path.exists(model_filename):  # If a full path is given.
        return model_filename
    else:  # Try to find path to malt model in environment variables.
        return find_file(model_filename, env_vars=("MALT_MODEL",), verbose=False)


class MaltParser(ParserI):
    """
    A class for dependency parsing with MaltParser. The input is the paths to:
    - (optionally) a maltparser directory
    - (optionally) the path to a pre-trained MaltParser .mco model file
    - (optionally) the tagger to use for POS tagging before parsing
    - (optionally) additional Java arguments

    Example:
        >>> from nltk.parse import malt
        >>> # With MALT_PARSER and MALT_MODEL environment set.
        >>> mp = malt.MaltParser(model_filename='engmalt.linear-1.7.mco') # doctest: +SKIP
        >>> mp.parse_one('I shot an elephant in my pajamas .'.split()).tree() # doctest: +SKIP
        (shot I (elephant an) (in (pajamas my)) .)
        >>> # Without MALT_PARSER and MALT_MODEL environment.
        >>> mp = malt.MaltParser('/home/user/maltparser-1.9.2/', '/home/user/engmalt.linear-1.7.mco') # doctest: +SKIP
        >>> mp.parse_one('I shot an elephant in my pajamas .'.split()).tree() # doctest: +SKIP
        (shot I (elephant an) (in (pajamas my)) .)
    """

    def __init__(
        self,
        parser_dirname="",
        model_filename=None,
        tagger=None,
        additional_java_args=None,
    ):
        """
        An interface for parsing with the Malt Parser.

        :param parser_dirname: The path to the maltparser directory that
            contains the maltparser-1.x.jar
        :type parser_dirname: str
        :param model_filename: The name of the pre-trained model with .mco file
            extension. If provided, training will not be required.
            (see http://www.maltparser.org/mco/mco.html and
            see http://www.patful.com/chalk/node/185)
        :type model_filename: str
        :param tagger: The tagger used to POS tag the raw string before
            formatting to CONLL format. It should behave like `nltk.pos_tag`
        :type tagger: function
        :param additional_java_args: This is the additional Java arguments that
            one can use when calling Maltparser, usually this is the heapsize
            limits, e.g. `additional_java_args=['-Xmx1024m']`
            (see https://javarevisited.blogspot.com/2011/05/java-heap-space-memory-size-jvm.html)
        :type additional_java_args: list
        """

        # Find all the necessary jar files for MaltParser.
        self.malt_jars = find_maltparser(parser_dirname)
        # Initialize additional java arguments.
        self.additional_java_args = (
            additional_java_args if additional_java_args is not None else []
        )
        # Initialize model.
        self.model = find_malt_model(model_filename)
        self._trained = self.model != "malt_temp.mco"
        # `-w` is allocated lazily inside a data root; see the working_dir property.
        self._working_dir = None
        # Initialize POS tagger.
        self.tagger = tagger if tagger is not None else malt_regex_tagger()

    @property
    def working_dir(self):
        """MaltParser's ``-w`` directory, holding the temporary CoNLL files and,
        for an untrained parser, the ``malt_temp.mco`` model that ``train()``
        writes.

        Allocated lazily by ``nltk.data.make_staging_dir`` INSIDE an allowed data
        root, with an unpredictable name and mode 0700. The previous default was
        the shared ``tempfile.gettempdir()``, which is world-writable on Linux and
        gives a predictable, squattable path for both the CoNLL files and the model.
        """
        if self._working_dir is None:
            staged = make_staging_dir(prefix="nltk_malt_")
            # The old shared tempdir was reaped by the OS; a dir under a data
            # root is not, so remove it ourselves rather than leaking one per
            # parser (the .mco it holds is a temporary model by definition).
            atexit.register(shutil.rmtree, staged, ignore_errors=True)
            self._working_dir = staged
        return self._working_dir

    @working_dir.setter
    def working_dir(self, value):
        # None restores the unset state, so the property allocates again on next
        # access rather than raising.
        if value is None:
            self._working_dir = None
            return
        # A caller may still choose the directory, but only inside the sandbox.
        # An empty value would reach MaltParser as `-w ""`, i.e. the CWD.
        text = os.fspath(value)
        if not text.strip():
            raise ValueError(
                "MaltParser.working_dir may not be empty; it would resolve to the "
                "current working directory."
            )
        validate_path(text, context="MaltParser.working_dir")
        self._working_dir = text

    def parse_tagged_sents(self, sentences, verbose=False, top_relation_label="null"):
        """
        Use MaltParser to parse multiple POS tagged sentences. Takes multiple
        sentences where each sentence is a list of (word, tag) tuples.
        The sentences must have already been tokenized and tagged.

        :param sentences: Input sentences to parse
        :type sentence: list(list(tuple(str, str)))
        :return: iter(iter(``DependencyGraph``)) the dependency graph
            representation of each sentence
        """
        if not self._trained:
            raise Exception("Parser has not been trained. Call train() first.")

        input_file_name = None
        output_file_name = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="malt_input.conll.", dir=self.working_dir, mode="w", delete=False
            ) as input_file, tempfile.NamedTemporaryFile(
                prefix="malt_output.conll.",
                dir=self.working_dir,
                mode="w",
                delete=False,
            ) as output_file:
                input_file_name = input_file.name
                output_file_name = output_file.name

                # Convert list of sentences to CONLL format.
                for line in taggedsents_to_conll(sentences):
                    input_file.write(str(line))
                input_file.close()

                # Generate command to run maltparser. The model's directory is
                # passed to MaltParser via its ``-w`` argument (inside
                # generate_malt_command), so no JVM working-directory is needed.
                cmd = self.generate_malt_command(
                    input_file_name, output_file_name, mode="parse"
                )

                ret = self._execute(cmd, verbose)  # Run command.

                if ret != 0:
                    raise Exception(
                        "MaltParser parsing (%s) failed with exit "
                        "code %d" % (" ".join(cmd), ret)
                    )

                # Must return iter(iter(Tree))
                with open(output_file_name) as infile:
                    for tree_str in infile.read().split("\n\n"):
                        yield (
                            iter(
                                [
                                    DependencyGraph(
                                        tree_str,
                                        top_relation_label=top_relation_label,
                                    )
                                ]
                            )
                        )
        finally:
            for filename in (input_file_name, output_file_name):
                if filename:
                    try:
                        os.remove(filename)
                    except OSError:
                        pass

    def parse_sents(self, sentences, verbose=False, top_relation_label="null"):
        """
        Use MaltParser to parse multiple sentences.
        Takes a list of sentences, where each sentence is a list of words.
        Each sentence will be automatically tagged with this
        MaltParser instance's tagger.

        :param sentences: Input sentences to parse
        :type sentence: list(list(str))
        :return: iter(DependencyGraph)
        """
        tagged_sentences = (self.tagger(sentence) for sentence in sentences)
        return self.parse_tagged_sents(
            tagged_sentences, verbose, top_relation_label=top_relation_label
        )

    def generate_malt_command(self, inputfilename, outputfilename=None, mode=None):
        """
        This function generates the maltparser command use at the terminal.

        :param inputfilename: path to the input file
        :type inputfilename: str
        :param outputfilename: path to the output file
        :type outputfilename: str

        Both filenames are bounded to the NLTK data roots. ``-i`` is read by the
        JVM and ``-o`` is *written* by it, so an unbounded value here is an
        arbitrary file read and an arbitrary file write respectively. The
        internal callers pass temporary files inside :attr:`working_dir`, which
        is itself allocated inside a data root.
        """

        # Build only MaltParser's own arguments (main class + program args). The
        # JVM binary, classpath sandbox, JVM-option allowlist and env sanitisation
        # are all applied by nltk.internals.java() in _execute; this wrapper no
        # longer rolls its own subprocess, so those protections cannot drift.
        cmd = ["org.maltparser.Malt"]

        # MaltParser reads/writes the .mco model in its working directory. Pass that
        # directory as the ``-w`` program argument rather than chdir-ing the JVM
        # process: no cwd is handed to java(), so there is no working-directory
        # class-injection surface (an empty/CWD -cp element, CWE-88).
        # Rejects an empty / option-like / URL / traversing model name, and bounds
        # it to the sandbox when it is a real path. Use the value it returns:
        # __fspath__ may answer differently on every call, so re-reading
        # self.model here would let the JVM open a file the guard never saw.
        model = validate_model_resource(self.model, context="MaltParser model")
        model_dir, model_name = os.path.split(model)
        if model_dir:
            # A model carrying a directory is a real path: bound the directory too,
            # since in learn mode MaltParser WRITES the .mco into it.
            validate_path(model, context="MaltParser model")
            workingdir = os.path.abspath(model_dir)
        else:
            # A bare model name lives in the private dir that train() wrote it to.
            workingdir = self.working_dir
        cmd += ["-w", workingdir, "-c", model_name]

        # -i is read by the JVM and -o is written by it; train_from_file() and
        # generate_malt_command() are both public, so neither may leave the roots.
        cmd += ["-i", validate_tool_path(inputfilename, context="MaltParser input")]
        if mode == "parse":
            cmd += [
                "-o",
                validate_tool_path(
                    outputfilename, context="MaltParser output", for_write=True
                ),
            ]
        cmd += ["-m", mode]  # mode use to generate parses.
        return cmd

    def _execute(self, cmd, verbose=False):
        # Route MaltParser's JVM through the single hardened entry point so the
        # classpath sandbox, JVM-option allowlist and env sanitisation all apply.
        stdout = None if verbose else "pipe"
        try:
            java(
                cmd,
                classpath=self.malt_jars,
                options=self.additional_java_args,
                stdout=stdout,
                stderr=stdout,
            )
            return 0
        except OSError:
            return 1  # non-zero exit; the caller raises its descriptive error

    def train(self, depgraphs, verbose=False):
        """
        Train MaltParser from a list of ``DependencyGraph`` objects

        :param depgraphs: list of ``DependencyGraph`` objects for training input data
        :type depgraphs: DependencyGraph
        """

        # Write the conll_str to malt_train.conll file in /tmp/
        with tempfile.NamedTemporaryFile(
            prefix="malt_train.conll.", dir=self.working_dir, mode="w", delete=False
        ) as input_file:
            input_str = "\n".join(dg.to_conll(10) for dg in depgraphs)
            input_file.write(str(input_str))
        # Trains the model with the malt_train.conll
        self.train_from_file(input_file.name, verbose=verbose)
        # Removes the malt_train.conll once training finishes.
        os.remove(input_file.name)

    def train_from_file(self, conll_file, verbose=False):
        """
        Train MaltParser from a file
        :param conll_file: str for the filename of the training input data
        :type conll_file: str
        """

        # If conll_file is a ZipFilePathPointer,
        # then we need to do some extra massaging
        if isinstance(conll_file, ZipFilePathPointer):
            with tempfile.NamedTemporaryFile(
                prefix="malt_train.conll.", dir=self.working_dir, mode="w", delete=False
            ) as input_file:
                with conll_file.open() as conll_input_file:
                    conll_str = conll_input_file.read()
                    input_file.write(str(conll_str))
                return self.train_from_file(input_file.name, verbose=verbose)

        # Generate command to run maltparser.
        cmd = self.generate_malt_command(conll_file, mode="learn")
        ret = self._execute(cmd, verbose)
        if ret != 0:
            raise Exception(
                "MaltParser training (%s) failed with exit "
                "code %d" % (" ".join(cmd), ret)
            )
        self._trained = True


if __name__ == "__main__":
    """
    A demonstration function to show how NLTK users can use the malt parser API.

    >>> from nltk import pos_tag
    >>> assert 'MALT_PARSER' in os.environ, str(
    ... "Please set MALT_PARSER in your global environment, e.g.:\n"
    ... "$ export MALT_PARSER='/home/user/maltparser-1.9.2/'")
    >>>
    >>> assert 'MALT_MODEL' in os.environ, str(
    ... "Please set MALT_MODEL in your global environment, e.g.:\n"
    ... "$ export MALT_MODEL='/home/user/engmalt.linear-1.7.mco'")
    >>>
    >>> _dg1_str = str("1    John    _    NNP   _    _    2    SUBJ    _    _\n"
    ...             "2    sees    _    VB    _    _    0    ROOT    _    _\n"
    ...             "3    a       _    DT    _    _    4    SPEC    _    _\n"
    ...             "4    dog     _    NN    _    _    2    OBJ     _    _\n"
    ...             "5    .     _    .    _    _    2    PUNCT     _    _\n")
    >>>
    >>>
    >>> _dg2_str  = str("1    John    _    NNP   _    _    2    SUBJ    _    _\n"
    ...             "2    walks   _    VB    _    _    0    ROOT    _    _\n"
    ...             "3    .     _    .    _    _    2    PUNCT     _    _\n")
    >>> dg1 = DependencyGraph(_dg1_str)
    >>> dg2 = DependencyGraph(_dg2_str)
    >>> # Initialize a MaltParser object
    >>> mp = MaltParser()
    >>>
    >>> # Trains a model.
    >>> mp.train([dg1,dg2], verbose=False)
    >>> sent1 = ['John','sees','Mary', '.']
    >>> sent2 = ['John', 'walks', 'a', 'dog', '.']
    >>>
    >>> # Parse a single sentence.
    >>> parsed_sent1 = mp.parse_one(sent1)
    >>> parsed_sent2 = mp.parse_one(sent2)
    >>> print(parsed_sent1.tree())
    (sees John Mary .)
    >>> print(parsed_sent2.tree())
    (walks John (dog a) .)
    >>>
    >>> # Parsing multiple sentences.
    >>> sentences = [sent1,sent2]
    >>> parsed_sents = mp.parse_sents(sentences)
    >>> print(next(next(parsed_sents)).tree())
    (sees John Mary .)
    >>> print(next(next(parsed_sents)).tree())
    (walks John (dog a) .)
    >>>
    >>> # Initialize a MaltParser object with an English pre-trained model.
    >>> parser_dirname = 'maltparser-1.9.2'
    >>> model_name = 'engmalt.linear-1.7.mco'
    >>> mp = MaltParser(parser_dirname=parser_dirname, model_filename=model_name, tagger=pos_tag)
    >>> sent1 = 'I shot an elephant in my pajamas .'.split()
    >>> sent2 = 'Time flies like banana .'.split()
    >>> # Parse a single sentence.
    >>> print(mp.parse_one(sent1).tree())
    (shot I (elephant an) (in (pajamas my)) .)
    # Parsing multiple sentences
    >>> sentences = [sent1,sent2]
    >>> parsed_sents = mp.parse_sents(sentences)
    >>> print(next(next(parsed_sents)).tree())
    (shot I (elephant an) (in (pajamas my)) .)
    >>> print(next(next(parsed_sents)).tree())
    (flies Time (like banana) .)
    """

    import doctest

    doctest.testmod()
