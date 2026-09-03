# Natural Language Toolkit: Senna Interface
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A general interface to the SENNA pipeline that supports any of the
operations specified in SUPPORTED_OPERATIONS.

Applying multiple operations at once has the speed advantage. For example,
Senna will automatically determine POS tags if you are extracting named
entities. Applying both of the operations will cost only the time of
extracting the named entities.

The SENNA pipeline has a fixed maximum size of the sentences that it can read.
By default it is 1024 token/sentence. If you have larger sentences, changing
the MAX_SENTENCE_SIZE value in SENNA_main.c should be considered and your
system specific binary should be rebuilt. Otherwise this could introduce
misalignment errors.

The input is:

- path to the directory that contains SENNA executables. If the path is incorrect,
  Senna will automatically search for executable file specified in SENNA environment variable
- List of the operations needed to be performed.
- (optionally) the encoding of the input data (default:utf-8)

Note: Unit tests for this module can be found in test/unit/test_senna.py

>>> from nltk.classify import Senna
>>> pipeline = Senna('/usr/share/senna-v3.0', ['pos', 'chk', 'ner'])  # doctest: +SKIP
>>> sent = 'Dusseldorf is an international business center'.split()
>>> [(token['word'], token['chk'], token['ner'], token['pos']) for token in pipeline.tag(sent)]  # doctest: +SKIP
[('Dusseldorf', 'B-NP', 'B-LOC', 'NNP'), ('is', 'B-VP', 'O', 'VBZ'), ('an', 'B-NP', 'O', 'DT'),
('international', 'I-NP', 'O', 'JJ'), ('business', 'I-NP', 'O', 'NN'), ('center', 'I-NP', 'O', 'NN')]
"""

from os import environ, path, sep
from platform import architecture, system
from subprocess import PIPE

from nltk.pathsec import TrustError, spawn_trusted
from nltk.tag.api import TaggerI


class Senna(TaggerI):
    SUPPORTED_OPERATIONS = ["pos", "chk", "ner"]

    def __init__(self, senna_path, operations, encoding="utf-8"):
        self._encoding = encoding

        # Only an ABSOLUTE senna_path is accepted; a relative one (e.g. ".") would
        # make executable() a separator path Popen runs from the CWD without $PATH,
        # executing a planted senna-<platform> file (CWE-426/CWE-427). Else use SENNA.
        self._path = None
        if path.isabs(senna_path):
            self._path = path.normpath(senna_path) + sep

        # If the explicit (absolute) senna_path does not contain the executable,
        # fall back to the SENNA environment variable, which must also be
        # absolute for the same reason.
        if self._path is None or not path.isfile(self.executable(self._path)):
            senna_env = environ.get("SENNA")
            if senna_env and path.isabs(senna_env):
                self._path = path.normpath(senna_env) + sep

        # The executable must exist at this point; fail fast so construction is
        # consistent (the path is verified here, not deferred to tag_sents()).
        if self._path is None or not path.isfile(self.executable(self._path)):
            raise LookupError(
                "Senna executable not found. Pass an absolute senna_path to "
                "Senna(...) or set the SENNA environment variable to the "
                "absolute directory that contains the senna binary."
            )

        self.operations = operations

    def executable(self, base_path):
        """
        The function that determines the system specific binary that should be
        used in the pipeline. In case, the system is not known the default senna binary will
        be used.
        """
        os_name = system()
        if os_name == "Linux":
            bits = architecture()[0]
            if bits == "64bit":
                return path.join(base_path, "senna-linux64")
            return path.join(base_path, "senna-linux32")
        if os_name == "Windows":
            return path.join(base_path, "senna-win32.exe")
        if os_name == "Darwin":
            return path.join(base_path, "senna-osx")
        return path.join(base_path, "senna")

    def _map(self):
        """
        A method that calculates the order of the columns that SENNA pipeline
        will output the tags into. This depends on the operations being ordered.
        """
        _map = {}
        i = 1
        for operation in Senna.SUPPORTED_OPERATIONS:
            if operation in self.operations:
                _map[operation] = i
                i += 1
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

        # self._path is a plain mutable attribute; a non-absolute (or non-str)
        # reassignment makes executable() a CWD-relative path Popen runs without
        # $PATH, executing a planted senna-<platform> binary (CWE-426/CWE-427).
        if not (isinstance(self._path, str) and path.isabs(self._path)):
            raise LookupError(
                "Senna path %r is not an absolute string; a relative path would be "
                "run from the current working directory. Construct Senna(...) with an "
                "absolute senna_path or set the SENNA environment variable."
                % (self._path,)
            )
        executable = self.executable(self._path)
        if not path.isfile(executable):
            raise LookupError(
                "Senna executable expected at %s but not found" % executable
            )
        # self.operations is a plain mutable attribute turned into '-<op>' flags;
        # an arbitrary string would be an injected senna option (e.g. '-path'
        # redirecting the data dir), so bound it to SUPPORTED_OPERATIONS (CWE-88).
        invalid = [op for op in self.operations if op not in self.SUPPORTED_OPERATIONS]
        if invalid:
            raise ValueError(
                f"Unsupported Senna operation(s) {invalid!r}; choose from "
                f"{self.SUPPORTED_OPERATIONS!r}."
            )
        # spawn_trusted() (below) verifies executable is on a trusted path, refuses
        # a shell, and scrubs the loader environment before exec (CWE-426/427/732).
        _args = ["-path", self._path, "-usrtokens", "-iobtags"]
        _args.extend(["-" + op for op in self.operations])

        # A CR/LF in a token adds an input line and breaks the 1:1 sentence->output
        # mapping senna relies on, smuggling a spurious sentence or corrupting the
        # alignment (CWE-93). Reject it, as the tokenizer/repp guards do.
        for sentence in sentences:
            for token in sentence:
                if "\n" in token or "\r" in token:
                    raise ValueError(
                        "Senna input tokens must not contain newline or carriage "
                        "return characters (CWE-93)."
                    )

        # Serialize the actual sentences to a temporary string
        _input = "\n".join(" ".join(x) for x in sentences) + "\n"
        if isinstance(_input, str) and encoding:
            _input = _input.encode(encoding)

        # Run the tagger and get the output.
        try:
            p = spawn_trusted(executable, _args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except TrustError as e:
            raise LookupError(
                "Senna executable %r is not on a trusted path; install senna where "
                "only you (or root) can write. (%s)" % (executable, e)
            ) from e
        (stdout, stderr) = p.communicate(input=_input)
        senna_output = stdout

        # Check the return code.
        if p.returncode != 0:
            raise RuntimeError("Senna command failed! Details: %s" % stderr)

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
            tags = tagged_word.split("\t")
            result = {}
            for tag in map_:
                result[tag] = tags[map_[tag]].strip()
            try:
                result["word"] = sentences[sentence_index][token_index]
            except IndexError as e:
                raise IndexError(
                    "Misalignment error occurred at sentence number %d. Possible reason"
                    " is that the sentence size exceeded the maximum size. Check the "
                    "documentation of Senna class for more information."
                    % sentence_index
                ) from e
            tagged_sentences[-1].append(result)
            token_index += 1
        return tagged_sentences
