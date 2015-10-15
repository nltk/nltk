"""
A reader for corpora whose documents are in MTE format.
"""
import os
from functools import reduce
from nltk import compat
from nltk.corpus.reader import concat, TaggedCorpusReader

lxmlAvailable = False
try:
    from lxml import etree
    lxmlAvailable = True
except ImportError:
    #first try c version of ElementTree
    try:
        import xml.etree.cElementTree as etree
    except ImportError:
        import xml.etree.ElementTree as etree
import re

def xpath(root, path, ns):
    if lxmlAvailable:
        return root.xpath(path, namespaces=ns)
    else:
        return root.findall(path, ns)


class MTEFileReader:
    """
    Class for loading the content of the multext-east corpus. It
    parses the xml files and does some tag-filtering depending on the
    given method parameters.
    """
    ns = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}
    tag_ns = '{http://www.tei-c.org/ns/1.0}'
    xml_ns = '{http://www.w3.org/XML/1998/namespace}'

    def __init__(self, file_path):
        tree = etree.parse(file_path)
        self.__root = xpath(tree.getroot(), './tei:text/tei:body', self.ns)[0]

    @classmethod
    def _words(self, text_root):
        return [w.text for w in xpath(text_root, './/*', self.ns) if
                w.tag == self.tag_ns + "w" or w.tag == self.tag_ns + "c"]

    @classmethod
    def _sents(self, text_root):
        return [MTEFileReader._words(s) for s in xpath(text_root, './/tei:s', self.ns)]

    @classmethod
    def _paras(self, text_root):
        return [MTEFileReader._sents(p) for p in xpath(text_root, './/tei:p', self.ns)]

    @classmethod
    def _lemma_words(self, text_root):
        return [(w.text, w.attrib['lemma']) for w in xpath(text_root, './/tei:w', self.ns)]

    @classmethod
    def _tagged_words(self, text_root, tags=""):
        if tags is None or tags == "":
            return [(w.text, w.attrib['ana']) for w in xpath(text_root, './/tei:w', self.ns)]

        else:
            tags = re.compile('^' + re.sub("-",".",tags) + '.*$')
            return [(w.text, w.attrib['ana']) for w in xpath(text_root, './/tei:w', self.ns)
                                              if tags.match(w.attrib['ana'])]

    @classmethod
    def _lemma_sents(self, text_root):
        return [MTEFileReader._lemma_words(s) for s in xpath(text_root, './/tei:s', self.ns)]

    @classmethod
    def _tagged_sents(self, text_root, tags=""):
        # double list comprehension to remove empty sentences in case there is a sentence only containing punctuation marks
        return [t for t in [MTEFileReader._tagged_words(s, tags) for s in xpath(text_root, './/tei:s', self.ns)] if len(t) > 0]

    @classmethod
    def _lemma_paras(self, text_root):
        return [MTEFileReader._lemma_sents(p) for p in xpath(text_root, './/tei:p', self.ns)]

    @classmethod
    def _tagged_paras(self, text_root, tags=""):
        return [t for t in [MTEFileReader._tagged_sents(p, tags) for p in xpath(text_root, './/tei:p', self.ns)] if len(t) > 0]


    def words(self):
        return MTEFileReader._words(self.__root)

    def sents(self):
        return MTEFileReader._sents(self.__root)

    def paras(self):
        return MTEFileReader._paras(self.__root)

    def lemma_words(self):
        return MTEFileReader._lemma_words(self.__root)

    def tagged_words(self, tags=""):
        return MTEFileReader._tagged_words(self.__root, tags)

    def lemma_sents(self):
        return MTEFileReader._lemma_sents(self.__root)

    def tagged_sents(self, tags=""):
        return MTEFileReader._tagged_sents(self.__root)

    def lemma_paras(self):
        return MTEFileReader._lemma_paras(self.__root)

    def tagged_paras(self, tags=""):
        return MTEFileReader._tagged_paras(self.__root)

class MTETagConverter:
    """
    Class for converting msd tags to universal tags, more conversion
    options are currently not implemented.
    """

    mapping_msd_universal = {
        'A': 'ADJ', 'S': 'ADP', 'R': 'ADV', 'C': 'CONJ',
        'D': 'DET', 'N': 'NOUN', 'M': 'NUM', 'Q': 'PRT',
        'P': 'PRON', 'V': 'VERB', '.': '.', '-': 'X'}

    @staticmethod
    def msd_to_universal(tag):
        """
        This function converts the annotation from the Multex-East to the universal tagset
        as described in Chapter 5 of the NLTK-Book

        Unknown Tags will be mapped to X. Punctuation marks are not supported in MSD tags, so
        """
        indicator = tag[0] if not tag[0] == "#" else tag[1]

        if not indicator in MTETagConverter.mapping_msd_universal:
            indicator = '-'

        return MTETagConverter.mapping_msd_universal[indicator]

class MTECorpusReader(TaggedCorpusReader):
    """
    Reader for corpora following the TEI-p5 xml scheme, such as MULTEXT-East.
    MULTEXT-East contains part-of-speech-tagged words with a quite precise tagging
    scheme. These tags can be converted to the Universal tagset
    """

    def __init__(self, root=None, fileids=None, encoding='utf8'):
        """
        Construct a new MTECorpusreader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = MTECorpusReader(root, 'oana-*.xml', 'utf8') # doctest: +SKIP

        :param root: The root directory for this corpus. (default points to location in multext config file)
        :param fileids: A list or regexp specifying the fileids in this corpus. (default is oana-en.xml)
        :param enconding: The encoding of the given files (default is utf8)
        """
        TaggedCorpusReader.__init__(self, root, fileids, encoding)

    def __fileids(self, fileids):
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, compat.string_types): fileids = [fileids]
        # filter wrong userinput
        fileids = filter(lambda x : x in self._fileids, fileids)
        # filter multext-east sourcefiles that are not compatible to the teip5 specification
        fileids = filter(lambda x : x not in ["oana-bg.xml", "oana-mk.xml"], fileids)
        if not fileids:
            print("No valid multext-east file specified")
        return fileids

    def readme(self):
        """
        Prints some information about this corpus.
        :return: the content of the attached README file
        :rtype: str
        """
        return self.open("00README.txt").read()

    def raw(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a single string.
        :rtype: str
        """
        return concat([self.open(f).read() for f in self.__fileids(fileids)])

    def words(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        return  reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).words() for f in self.__fileids(fileids)], [])

    def sents(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of sentences or utterances,
                 each encoded as a list of word strings
        :rtype: list(list(str))
        """
        return  reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).sents() for f in self.__fileids(fileids)], [])

    def paras(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of paragraphs, each encoded as a list
                 of sentences, which are in turn encoded as lists of word string
        :rtype: list(list(list(str)))
        """
        return  reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).paras() for f in self.__fileids(fileids)], [])

    def lemma_words(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of words, the corresponding lemmas
                 and punctuation symbols, encoded as tuples (word, lemma)
        :rtype: list(tuple(str,str))
        """
        return  reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).lemma_words() for f in self.__fileids(fileids)], [])

    def tagged_words(self, fileids=None, tagset="msd", tags=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :param tagset: The tagset that should be used in the returned object,
                       either "universal" or "msd", "msd" is the default
        :param tags: An MSD Tag that is used to filter all parts of the used corpus
                     that are not more precise or at least equal to the given tag
        :return: the given file(s) as a list of tagged words and punctuation symbols
                 encoded as tuples (word, tag)
        :rtype: list(tuple(str, str))
        """
        words = reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).tagged_words(tags=tags) for f in self.__fileids(fileids)], [])
        if tagset == "universal":
            return map(lambda wt : (wt[0], MTETagConverter.msd_to_universal(wt[1])), words)
        elif tagset == "msd":
            return words
        else:
            print("Unknown tagset specified.")

    def lemma_sents(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of sentences or utterances, each
                 encoded as a list of tuples of the word and the corresponding
                 lemma (word, lemma)
        :rtype: list(list(tuple(str, str)))
        """
        return  reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).lemma_sents() for f in self.__fileids(fileids)], [])


    def tagged_sents(self, fileids=None, tagset="msd", tags=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :param tagset: The tagset that should be used in the returned object,
                       either "universal" or "msd", "msd" is the default
        :param tags: An MSD Tag that is used to filter all parts of the used corpus
                     that are not more precise or at least equal to the given tag
        :return: the given file(s) as a list of sentences or utterances, each
                 each encoded as a list of (word,tag) tuples
        :rtype: list(list(tuple(str, str)))
        """
        sents = reduce(lambda a, b : a + b, [MTEFileReader(os.path.join(self._root, f)).tagged_sents(tags=tags) for f in self.__fileids(fileids)], [])
        if tagset == "universal":
            return map(lambda s : map (lambda wt : (wt[0], MTETagConverter.msd_to_universal(wt[1])), s), sents)
        elif tagset == "msd":
            return sents
        else:
            print("Unknown tagset specified.")

    def lemma_paras(self, fileids=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of paragraphs, each encoded as a
                 list of sentences, which are in turn encoded as a list of
                 tuples of the word and the corresponding lemma (word, lemma)
        :rtype: list(List(List(tuple(str, str))))
        """
        return reduce(lambda a, b : a + b ,[MTEFileReader(os.path.join(self._root, f)).lemma_paras() for f in self.__fileids(fileids)], [])

    def tagged_paras(self, fileids=None, tagset="msd", tags=None):
        """
	    :param fileids: A list specifying the fileids that should be used.
        :param tagset: The tagset that should be used in the returned object,
                       either "universal" or "msd", "msd" is the default
        :param tags: An MSD Tag that is used to filter all parts of the used corpus
                     that are not more precise or at least equal to the given tag
        :return: the given file(s) as a list of paragraphs, each encoded as a
                 list of sentences, which are in turn encoded as a list
                 of (word,tag) tuples
        :rtype: list(list(list(tuple(str, str))))
        """
        paras = reduce(lambda a, b : a + b, [MTEFileReader(os.path.join(self._root, f)).tagged_paras(tags=tags) for f in self.__fileids(fileids)], [])
        if tagset == "universal":
            return map(lambda p : map(lambda s : map (lambda wt : (wt[0], MTETagConverter.msd_to_universal(wt[0])), s), p), paras)
        elif tagset == "msd":
            return paras
        else:
            print("Unknown tagset specified.")
