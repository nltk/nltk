# Natural Language Toolkit: ISO GrAF Corpus Reader
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Stephen Matysik <smatysik@gmail.com>
# URL: <http://www.nltk.org/>
# For License informations, see LICENSE.TXT

"""
A reader for corpora that consist of documents in
the ISO GrAF format.
"""
import os.path    	

## note - these imports will change once the
## graf package is placed within the nltk
from graf.PyGraph import *
from graf.PyGraphParser import *

from util import *
from api import *

class MascCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of documents from MASC collection.
    Paragraphs, sentences, words, nouns, verbs, and other annotations 
    are contained within MASC.
    """
    CorpusView = StreamBackedCorpusView
    """The corpus view class used be this reader"""

    def __init__(self, root, fileids, encoding):
        """
        Construct a new MASC corpus reader for a set of documents
        located at the given root directory.  Example usage:
    
            >>> root = '/...path to corpus.../'
            >>> reader = MascCorpusReader(root, r'(?!\.).*\.txt', 
                                                      encoding = 'utf-8')

        @param root: The root directory for this corpus.
        @param fileids: A list of regexp specifying the fileids in 
                        this corpus.
        @param encoding: The encoding used for the text files in the corpus.
        """
        self._cur_file = ""
        self._cur_sents_file = ""
        self._cur_paras_file = ""
        self._cur_offsets = []
        self._cur_sents_offsets = []
        self._cur_paras_offsets = []
        self._char_to_byte = {}
        self._byte_to_char = {}
        self._file_end = 0
        CorpusReader.__init__(self, root, fileids, encoding)

    def raw(self, fileids=None):
        """
        @return: the given file(s) as a single string.
        @rtype: C{str}
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def words(self, fileids=None):
        """
        @return: the given file(s) as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([self.CorpusView(fileid, self._read_word_block,
                        encoding='utf-8')
                for fileid in self.abspaths(fileids)])

    def sents(self, fileids=None):
        """
        @return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings
        @rtype: C{list} of (C{list} of C{str})
        """
        return concat([self.CorpusView(fileid, self._read_sent_block, 
                        encoding='utf-8')
                for fileid in self.abspaths(fileids)])

    def paras(self, fileids=None):
        """
        @return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([self.CorpusView(fileid, self._read_para_block,
                        encoding='utf-8')
                for fileid in self.abspaths(fileids)])

    def nouns(self, fileids=None):
        """
        @return: the given file(s) as a list of nouns
        @rtype: C{list} of C{str}
        """
        return concat([self.CorpusView(fileid, self._read_noun_block,
                        encoding = 'utf-8')
                for fileid in self.abspaths(fileids)])

    def verbs(self, fileids=None):
        """
        @return: the given file(s) as a list of verbs
        @rtype: C{list} of C{str}
        """
        return concat([self.CorpusView(fileid, self._read_verb_block,
                        encoding='utf-8')
                for fileid in self.abspaths(fileids)])

    def persons(self, fileids=None):
        """
        @return: the given file(s) as a list of verbs
        @rtype: C{list} of C{str}
        """
        return concat([self.CorpusView(fileid, self._read_person_block,
                        encoding='utf-8')
                for fileid in self.abspaths(fileids)])

    def _get_basename(self, file):
        """
        @type file: C{str}
        @param file: full filename
        @return: the basename of the specified file
        @rtype: C{str}
        """
        return file[0:len(file)-4]

    def _get_disc(self, stream):
        """
        Using the specified file stream, this method creates two
        discrepency mappings, both as dictionaries:
            1. self._char_to_byte uses key = character number, 
                                       entry = byte number
            2. self._byte_to_char uses key = byte number, 
                                       entry = character number
        @type stream: StreamBackedCorpusView
        @param stream: file stream
        """
        self._char_to_byte = {}
        self._byte_to_char = {}
        stream.read()
        file_end = stream.tell()
        self._file_end = file_end
        stream.seek(0)
        for i in range(file_end+1):
            if i != stream.tell():
                self._char_to_byte[i] = stream.tell()
                self._byte_to_char[stream.tell()] = i
            stream.read(1)
        stream.seek(0)

    def _get_subset(self, offsets, offsets_start, offsets_end):
        """
        @type offsets: C{list} of C{int} pairs
        @param offsets: List of all offsets
        @type offsets_start: C{int}
        @param offsets_start: start of requested set of offsets
        @type offsets_end: C{int}
        @param offsets_end: end of requested set of offsets
        @return: a list of all offsets between offsets_start and offset_end
        @rtype: C{list} of C{str}
        """
        subset = []
        for i in offsets:
            if (i[0] >= offsets_start and i[1] <= offsets_end and 
                i[0] != i[1]):
                subset.append(i)
            elif (i[0] >= offsets_start and i[1] > offsets_end and 
                i[0] != i[1] and i[0] <= offsets_end):
                subset.append(i)
        return subset

    def _get_read_size(self, subset, char_to_byte, slimit, offset_end):
        """
        @return: the byte size of text that should be read 
        next from the file stream
        @rtype: C{int}
        """
        if len(subset) != 0:
            last1 = subset[len(subset)-1]
            last = last1[1]
            last = char_to_byte.get(last, last)
            read_size = last - slimit
        else:
            elimit = char_to_byte.get(offset_end, offset_end)
            read_size = elimit - slimit
        return read_size
            
    def _get_block(self, subset, text, offsets_start):
        """
        Retrieve the annotated text, annotations are contained in subset
        @type subset: C{list}
        @param subset: list of annotation offset pairs
        @type text: C{str}
        @param text: text read from text stream
        @type offsets_start: C{int}
        @param offset_start: integer to correct for discrepency 
                            between offsets and text character number
        @return: list of annotated text
        @rtype: C{list} of C{str} 
        """
        block = []
        for s in subset:
            start = s[0] - offsets_start
            end = s[1] - offsets_start
            chunk = text[start:end].encode('utf-8')
            chunk = self._remove_ws(chunk)
            block.append(chunk)
        return block

    def _read_block(self, stream, file_ending, label):
        """
        Generic method for retrieving annotated text from a file stream.
        @type stream: SeekableUnicodeStreamReader
        @param stream: file stream from StreamBackedCorpusView in 
                       corpus/reader/util.py
        @type file_ending: C{str}
        @param file_ending: xml annotation file containing annotation
                            offsets
        @type label: C{str}
        @param label: label of requested annotation
        @return: list of annotated text from a block of the file stream
        @rtype: C{list} of C{str}
        """
        file = self._get_basename(stream.name) + file_ending
        if file != self._cur_file:
            self._cur_file = file
            offsets = self._get_annotation(file, label)
            self._cur_offsets = offsets
            self._get_disc(stream)
            char_to_byte = self._char_to_byte
            byte_to_char = self._byte_to_char
        else:
            offsets = self._cur_offsets
            char_to_byte = self._char_to_byte
            byte_to_char = self._byte_to_char
        slimit = stream.tell()
        offset_slimit = byte_to_char.get(slimit, slimit)
        offset_elimit = offset_slimit + 500

        subset = self._get_subset(offsets, offset_slimit, offset_elimit)

        read_size = (self._get_read_size(subset, char_to_byte, slimit, 
                    offset_elimit))

        text = stream.read(read_size)

        block = self._get_block(subset, text, offset_slimit)
        return block


    def _read_person_block(self, stream):
        """ calls _read_block to retrieve 'person' tagged text """
        return self._read_block(stream, '-ne.xml', 'person')        

    def _read_verb_block(self, stream):
        """ calls _read_block to retrieve 'vchunk' (verb chunks) 
            tagged text """
        return self._read_block(stream, '-vc.xml', 'vchunk')

    def _read_noun_block(self, stream):
        """ calls _read_block to retrieve 'nchunk' (noun chunks) 
            tagged text """
        return self._read_block(stream, '-nc.xml', 'nchunk')

    def _read_word_block(self, stream):
        """ calls _read_block to retrieve 'tok' (words) tagged text """
        return self._read_block(stream, '-ptbtok.xml', 'tok')

    def _read_sent_block(self, stream):
        """
        Method for retrieving sentence annotations from text, and 
        the tok annotations within each sentence.
        @type stream: SeekableUnicodeStreamReader
        @param stream: file stream from StreamBackedCorpusView 
                        in corpus/reader/util.py
        @return: list of sentences, each of which is a list of words, 
                        from a block of the file stream
        @rtype: C{list} of C{str}
        """
        file = self._get_basename(stream.name) + '-s.xml'
        words_file = self._get_basename(stream.name) + '-ptbtok.xml'

        if not file == self._cur_sents_file:
            self._cur_sents_file = file
            self._cur_words_file = words_file
            offsets = self._get_annotation(file, 's')
            words_offsets = self._get_annotation(words_file, 'tok')
            self._cur_sents_offsets = offsets
            self._cur_words_offsets = words_offsets
            self._get_disc(stream)
            char_to_byte = self._char_to_byte
            byte_to_char = self._byte_to_char
        else:
            offsets = self._cur_sents_offsets
            words_offsets = self._cur_words_offsets
            char_to_byte = self._char_to_byte
            byte_to_char = self._byte_to_char

        slimit = stream.tell()
        offset_slimit = byte_to_char.get(slimit, slimit)
        offset_elimit = offset_slimit + 500

        subset = self._get_subset(offsets, offset_slimit, offset_elimit)

        read_size = self._get_read_size(subset, char_to_byte, 
                        slimit, offset_elimit)
        text = stream.read(read_size)


        block = []
        for s in subset:
            sent = []
            for w in words_offsets:
                if w[0] >= s[0] and w[1] <= s[1] and w[0] != w[1]:
                    start = w[0] - offset_slimit
                    end = w[1] - offset_slimit
                    chunk = text[start:end].encode('utf-8')
                    chunk = self._remove_ws(chunk)
                    sent.append(chunk)
            block.append(sent)

        return block

    def _read_para_block(self, stream):
        """
        Method for retrieving paragraph annotations from text, 
        and the sentence and word annotations within each paragraph.
        @type stream: SeekableUnicodeStreamReader
        @param stream: file stream from StreamBackedCorpusView 
                        in corpus/reader/util.py
        @return: list of paragraphs, each of which is a list of sentences, 
                        each of which is a list of words, 
                        from a block of the file stream
        @rtype: C{list} of C{list} of C{str}
        """
        file = self._get_basename(stream.name) + '-logical.xml'
        sents_file = self._get_basename(stream.name) + '-s.xml'
        words_file = self._get_basename(stream.name) + '-ptbtok.xml'

        if not file == self._cur_paras_file:
            self._cur_paras_file = file
            self._cur_sents_file = sents_file
            self._cur_words_file = words_file
            offsets = self._get_annotation(file, 'p')
            sents_offsets = self._get_annotation(sents_file, 's')
            words_offsets = self._get_annotation(words_file, 'tok')
            self._cur_paras_offsets = offsets
            self._cur_sents_offsets = sents_offsets
            self._cur_words_offsets = words_offsets
            self._get_disc(stream)
            char_to_byte = self._char_to_byte
            byte_to_char = self._byte_to_char
        else:
            offsets = self._cur_paras_offsets
            sents_offsets = self._cur_sents_offsets
            words_offsets = self._cur_words_offsets
            char_to_byte = self._char_to_byte
            byte_to_char = self._byte_to_char

#        if len(offsets) == 0:
#            print "No paragraph annotations for file " + file
            # TODO skip file (advance file stream) if no tokens are found

        slimit = stream.tell()
        offset_slimit = byte_to_char.get(slimit, slimit)
        offset_elimit = offset_slimit + 500

        subset = []
        for i in offsets:
            if (i[0] >= offset_slimit and i[1] <= offset_elimit 
                                        and i[0] != i[1]):
                subset.append(i)
            if (i[0] >= offset_slimit and i[1] > offset_elimit 
                                        and i[0] != i[1]):
                subset.append(i)
                break

        if len(subset) != 0:
            last1 = subset[len(subset)-1]
            last = last1[1]
            last = char_to_byte.get(last, last)
            read_size = last - slimit
            text = stream.read(read_size)
        else:
            if offset_elimit < self._file_end:
                elimit = char_to_byte.get(offset_elimit, offset_elimit)
                read_size = elimit - slimit
                text = stream.read(read_size)
            else:
                stream.read()

        block = []
        for p in subset:
            para = []
            for s in sents_offsets:
                if s[0] >= p[0] and s[1] <= p[1] and s[0] != s[1]:
                    sent = []
                    for w in words_offsets:
                        if w[0] >= s[0] and w[1] <= s[1] and w[0] != w[1]:
                            start = w[0] - offset_slimit
                            end = w[1] - offset_slimit
                            chunk = text[start:end].encode('utf-8')
                            chunk = self._remove_ws(chunk)
                            sent.append(chunk)
                    para.append(sent)
            if len(para) != 0:    # If a paragraph has no internal 
                                  # sentence tokens, we disregard it
                block.append(para)
        return block

    def _get_annotation(self, annfile, label):
        """
        Parses the given annfile and returns the offsets of all
        annotations of type 'label'

        @type annfile: C{str}
        @param annfile: xml file containing annotation offsets
        @type label: C{str}
        @param label: annotation type label
        @return: list of annotation offsets
        @rtype: C{list} of C{pairs} of C{int}
        """
        parser = PyGraphParser()
        g = parser.parse(annfile)
        
        node_list = g.nodes()

        offsets = []
        
        for node in node_list:
            pair = self._add_annotations(node, label)
            offsets.extend(pair)

        offsets.sort()
        return offsets

    def _add_annotations(self, node, label):
        """
        Given a node and annotation label, this method calls 
        _get_offsets for each annotation contained by node, 
        and adds them to the return list if they are oftype 'label'

        @type node: C{PyNode}
        @param node: a node in the Graf graph
        @type label: C{str}
        @param label: annotation type label 
        @return: the annotation offsets of type 'label' 
                 contained by the specified node
        @rtype: C{list} of C{pairs} of C{int}
        """
        node_offsets = []
        for a in node._annotations:
            if a._label == label:
                pair = self._get_offsets(node)
                if pair is not None:
                    pair.sort()
                    node_offsets.append(pair)
        return node_offsets

    def _get_offsets(self, node):
        """
        @type node: C{PyNode}
        @param node: a node in the Graf graph
        @return: the offsets contained by a given node
        @rtype: C{pair} of C{int}, or C{None}
        """
        
        if len(node._links) == 0 and node._outEdgeList != []:
            offsets = []
            edge_list = node._outEdgeList
            edge_list.reverse()
            for edge in edge_list:
                temp_offsets = self._get_offsets(edge._toNode)
                if temp_offsets is not None:
                    offsets.extend(self._get_offsets(edge._toNode))
            if len(offsets) == 0:
                return None
            offsets.sort()
            start = offsets[0]
            end = offsets[len(offsets)-1]
            return [start, end]
        elif len(node._links) != 0:
            offsets = []
            for link in node._links:
                for region in link._regions:
                    for anchor in region._anchors:
                        offsets.append(int(anchor._offset))
            offsets.sort()
            start = offsets[0]
            end = offsets[len(offsets)-1]
            return [start, end]
        else:
            return None
            
    def _remove_ws(self, chunk):
        """
        @return: string of text from chunk without end line characters
        and multiple spaces
        @rtype: C{str}
        """
        chunk = chunk.replace("\n", "")
        words = chunk.split()
        new_str = ""
        for i in words:
            if i == words[len(words)-1]:
                new_str += i
            else:
                new_str = new_str + i + " "
        return new_str
