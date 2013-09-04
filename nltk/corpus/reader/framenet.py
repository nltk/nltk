# Natural Language Toolkit: Framenet Corpus Reader
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Chuck Wooters <wooters@icsi.berkeley.edu>x
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
from __future__ import print_function

"""
Corpus reader for the Framenet 1.5 Corpus.
"""

__docformat__ = 'epytext en'

import os
import re
import textwrap
from pprint import pprint, pformat
from nltk.internals import ElementWrapper
from nltk.corpus.reader import XMLCorpusReader, XMLCorpusView
from nltk.compat import text_type, string_types, python_2_unicode_compatible

def _pretty_longstring(defstr, prefix='', wrap_at=65):

    """
    Helper function for pretty-printing a long string.

    :param defstr: The string to be printed.
    :type defstr: str
    :return: A nicely formated string representation of the long string.
    :rtype: str
    """

    outstr = ""
    for line in textwrap.fill(defstr, wrap_at).split('\n'):
        outstr += "{0}{1}\n".format(prefix, line)
    return outstr

def _pretty_any(obj):

    """
    Helper function for pretty-printing any AttrDict object.

    :param obj: The obj to be printed.
    :type obj: AttrDict
    :return: A nicely formated string representation of the AttrDict object.
    :rtype: str
    """

    outstr = ""
    for k in obj:
        if isinstance(obj[k], string_types) and len(obj[k]) > 65:
            outstr += "[{0}]\n".format(k)
            outstr += "{0}".format(_pretty_longstring(obj[k], prefix='  '))
            outstr += '\n'
        else:
            outstr += "[{0}] {1}\n".format(k, obj[k])

    return outstr

def _pretty_semtype(st):

    """
    Helper function for pretty-printing a semantic type.

    :param st: The semantic type to be printed.
    :type st: AttrDict
    :return: A nicely formated string representation of the semantic type.
    :rtype: str
    """

    semkeys = st.keys()
    if len(semkeys) == 1: return "<None>"

    outstr = ""
    outstr += "semantic type ({0.ID}): {0.name}\n".format(st)
    if 'abbrev' in semkeys:
        outstr += "[abbrev] {0}\n".format(st.abbrev)
    if 'definition' in semkeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(st.definition,'  ')
    if 'superType' in semkeys:
        outstr += "[superType]\n"
        ststr = "{0}".format(st.superType)
        for line in ststr.split("\n"):
            outstr += "  {0}\n".format(line)

    return outstr

def _pretty_frame_relation_type(frt):

    """
    Helper function for pretty-printing a frame relation type.

    :param frt: The frame relation type to be printed.
    :type frt: AttrDict
    :return: A nicely formated string representation of the frame relation type.
    :rtype: str
    """

    outstr = ""
    outstr += "frame relation type ({0.ID}): {0.name}\n".format(frt)
    outstr += "[superFrameName] {0}\n".format(frt.superFrameName)
    outstr += "[subFrameName] {0}\n".format(frt.subFrameName)

    return outstr

def _pretty_lu(lu):

    """
    Helper function for pretty-printing a lexical unit.

    :param lu: The lu to be printed.
    :type lu: AttrDict
    :return: A nicely formated string representation of the lexical unit.
    :rtype: str
    """

    lukeys = lu.keys()
    outstr = ""
    outstr += "lexical unit ({0.ID}): {0.name}\n\n".format(lu)
    if 'definition' in lukeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(lu.definition,'  ')
    if 'frame' in lukeys:
        outstr += "\n[frame] {0}({1})\n".format(lu.frame,lu.frameID)
    if 'incorporatedFE' in lukeys:
        outstr += "\n[incorporatedFE] {0}\n".format(lu.incorporatedFE)
    if 'POS' in lukeys:
        outstr += "\n[POS] {0}\n".format(lu.POS)
    if 'status' in lukeys:
        outstr += "\n[status] {0}\n".format(lu.status)
    if 'totalAnnotated' in lukeys:
        outstr += "\n[totalAnnotated] {0} annotated examples\n".format(lu.totalAnnotated)
    if 'lexeme' in lukeys:
        outstr += "\n[lexeme] {0}({1})\n".format(lu.lexeme['name'],lu.lexeme['POS'])
    if 'semType' in lukeys:
        outstr += "\n[semType] {0} semantic types".format(len(lu.semType))
        outstr += "  " + ", ".join([x.name for x in lu.semType]) + '\n'
        outstr += '\n'
    if 'subCorpus' in lukeys:
        subc = [x.name for x in lu.subCorpus]
        outstr += "\n[subCorpus] {0} subcorpora\n".format(len(lu.subCorpus))
        for line in textwrap.fill(", ".join(sorted(subc)), 60).split('\n'): 
            outstr += "  {0}\n".format(line)

    return outstr

def _pretty_fe(fe):

    """
    Helper function for pretty-printing a frame element.

    :param fe: The frame element to be printed.
    :type fe: AttrDict
    :return: A nicely formated string representation of the frame element.
    :rtype: str
    """
    fekeys = fe.keys()
    outstr = ""
    outstr += "frame element ({0.ID}): {0.name}\n\n".format(fe)
    if 'definition' in fekeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(fe.definition,'  ')
    if 'abbrev' in fekeys:
        outstr += "[abbrev] {0}\n".format(fe.abbrev)
    if 'requiresFE' in fekeys:
        outstr += "[requiresFE] "
        if fe.requiresFE is None:
            outstr += "<None>\n"
        else:
            outstr += "{0}\n".format(fe.requiresFE.name)
    if 'excludesFE' in fekeys:
        outstr += "[excludesFE] "
        if fe.excludesFE is None:
            outstr += "<None>\n"
        else:
            outstr += "{0}\n".format(fe.excludesFE.name)
    if 'semType' in fekeys:
        outstr += "[semType] "
        if fe.semType is None:
            outstr += "<None>\n"
        else:
            outstr += "\n  " + _pretty_semtype(fe.semType) + '\n'

    return outstr

def _pretty_frame(frame):

    """
    Helper function for pretty-printing a frame.

    :param frame: The frame to be printed.
    :type frame: AttrDict
    :return: A nicely formated string representation of the frame.
    :rtype: str
    """

    outstr = ""
    outstr += "frame ({0.ID}): {0.name}\n\n".format(frame)
    outstr += "[definition]\n"
    outstr += _pretty_longstring(frame.definition, '  ') + '\n'

    outstr += "[semType] {0} semantic types\n".format(len(frame.semType))
    outstr += "  " + ", ".join([x.name for x in frame.semType]) + '\n'

    outstr += "[FEcoreSet] {0} frame element core sets\n".format(len(frame.FEcoreSet))
    outstr += "  " + ", ".join([x.name for x in frame.FEcoreSet]) + '\n'

    outstr += "[frameRelation] {0} frame relations\n".format(len(frame.frameRelation))
    frels = []
    for fr in frame.frameRelation:
        frels.append("{0}({1})\n".format(fr['type'],
                                         ','.join([x for x in fr['relatedFrame']])))
    outstr += "  " + ", ".join(frels) + '\n'

    outstr += "\n[lexUnit] {0} lexical units\n".format(len(frame.lexUnit))
    lustrs = []
    for luName,lu in sorted(frame.lexUnit.items()):
        tmpstr = '{0} ({1})'.format(luName, lu.ID)
        lustrs.append(tmpstr)
    outstr += "{0}\n".format(_pretty_longstring(', '.join(lustrs),prefix='  '))

    outstr += "\n[FE] {0} frame elements\n".format(len(frame.FE))
    fes = {}
    for feName,fe in sorted(frame.FE.items()):
        try:
            fes[fe.coreType].append('{0} ({1})'.format(feName, fe.ID))
        except KeyError:
            fes[fe.coreType] = []
            fes[fe.coreType].append('{0} ({1})'.format(feName, fe.ID))
    for ct in sorted(fes.keys()):
        outstr += '{0:>15}: {1}\n'.format(ct, ', '.join(sorted(fes[ct])))

    return outstr

class FramenetError(Exception):

    """An exception class for framenet-related errors."""

@python_2_unicode_compatible
class AttrDict(dict):

    """A class that wraps a dict and allows accessing the keys of the
    dict as if they were attributes. Taken from here:
       http://stackoverflow.com/a/14620633/8879

    >>> foo = {'a':1, 'b':2, 'c':3}
    >>> bar = AttrDict(foo)
    >>> dict(bar)
    {'a': 1, 'c': 3, 'b': 2}
    >>> bar.b
    2
    >>> bar.d = 4
    >>> dict(bar)
    {'a': 1, 'c': 3, 'b': 2, 'd': 4}
    >>>
    """

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def short_repr(self):
        if hasattr(self,'_type'):
            return '<{0} ID={1} name={2}>'.format(self['_type'], self['ID'], self['name'])
        else:
            return dict.__repr__(self)
        
    def __str__(self):
        outstr = ""

        if not self.has_key('_type'):
            return _pretty_any(self)

        if self['_type'] == 'frame':
            outstr = _pretty_frame(self)
        elif self['_type'] == 'fe':
            outstr = _pretty_fe(self)
        elif self['_type'] == 'lu':
            outstr = _pretty_lu(self)
        elif self['_type'] == 'semtype':
            outstr = _pretty_semtype(self)
        elif self['_type'] == 'framerelationtype':
            outstr = _pretty_frame_relation_type(self)
        else:
            outstr = _pretty_any(self)

        return outstr
    __repr__ = __str__

@python_2_unicode_compatible
class PrettyDict(dict):
    """
    Displays an abbreviated repr of values where possible.
    """
    def __repr__(self):
        parts = []
        for k,v in self.items():
            kv = repr(k)+': '
            try:
                kv += v.short_repr()
            except AttributeError:
                kv += repr(v)
            parts.append(kv)
        return '{'+', '.join(parts)+'}'

@python_2_unicode_compatible
class PrettyList(list):
    """
    Displays an abbreviated repr of only the first several elements, not the whole list.
    """
    # from nltk.util
    _MAX_REPR_SIZE = 60
    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(elt.short_repr())
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return '[%s, ...]' % text_type(', ').join(pieces[:-1])
        else:
            return '[%s]' % text_type(', ').join(pieces)

class FramenetCorpusReader(XMLCorpusReader):

    """A corpus reader for the Framenet Corpus."""

    def __init__(self, root, fileids):
        XMLCorpusReader.__init__(self, root, fileids)

        # framenet corpus sub dirs
        # sub dir containing the xml files for frames
        self._frame_dir = "frame"
        # sub dir containing the xml files for lexical units
        self._lu_dir = "lu"
        # sub dir containing the xml files for fulltext annotation files
        self._fulltext_dir = "fulltext"

        # Indexes used for faster look-ups
        self._frame_idx = None
        self._lu_idx = None
        self._fulltext_idx = None
        self._semtypes = None

    def _buildframeindex(self):
        # The total number of Frames in Framenet is fairly small (~1200) so
        # this index should not be very large
        self._frame_idx = {}
        for f in XMLCorpusView(self.abspath("frameIndex.xml"),
                               'frameIndex/frame', self._handle_elt):
            self._frame_idx[f['ID']] = f

    def _buildcorpusindex(self):
        # The total number of fulltext annotated documents in Framenet
        # is fairly small (~90) so this index should not be very large
        self._fulltext_idx = {}
        for doclist in XMLCorpusView(self.abspath("fulltextIndex.xml"),
                                     'fulltextIndex/corpus',
                                     self._handle_fulltextindex_elt):
            for doc in doclist:
                self._fulltext_idx[doc.ID] = doc

    def _buildluindex(self):
        # The number of LUs in Framenet is about 13,000 so this index
        # should not be very large
        self._lu_idx = {}
        for lu in XMLCorpusView(self.abspath("luIndex.xml"),
                                'luIndex/lu', self._handle_elt):
            self._lu_idx[lu['ID']] = lu

    def readme(self):
        """
        Return the contents of the corpus README.txt (or README) file.
        """
        try:
            return self.open("README.txt").read()
        except IOError:
            return self.open("README").read()

    def buildindexes(self):
        """
        Build the internal indexes to make look-ups faster.
        """
        # Frames
        self._buildframeindex()
        # LUs
        self._buildluindex()
        # Fulltext annotation corpora index
        self._buildcorpusindex()

    def annotated_document(self, fn_docid):
        """
        Returns the annotated document whose id number is
        ``fn_docid``. This id number can be obtained by calling the
        Documents() function.

        The dict that is returned from this function will contain the
        following information about the annotated document:

        - 'sentence'   : a list of sentences in the document
           - Each item in the list is a dict containing the following keys:
              - 'ID'
              - 'text'
              - 'paragNo'
              - 'sentNo'
              - 'docID'
              - 'corpID'
              - 'aPos'
              - 'annotationSet' : a list of annotation layers for the sentence
                 - Each item in the list is a dict containing the following keys:
                    - 'ID'
                    - 'status'   : either 'MANUAL' or 'UNANN'
                    - 'luName'   : (only if status is 'MANUAL')
                    - 'luID'     : (only if status is 'MANUAL')
                    - 'frameID'  : (only if status is 'MANUAL')
                    - 'frameName': (only if status is 'MANUAL')
                    - 'layer' : a list of labels for the layer
                       - Each item in the layer is a dict containing the following keys:
                          - 'rank'
                          - 'name'
                          - 'label' : a list of labels in the layer
                             - Each item is a dict containing the following keys:
                                - 'start'
                                - 'end'
                                - 'name'
                                - 'feID' (optional)

        :param fn_docid: The Framenet id number of the document
        :type fn_docid: int
        :return: Information about the annotated document
        :rtype: dict
        """
        try:
            xmlfname = self._fulltext_idx[fn_docid].filename
        except TypeError:  # happens when self._fulltext_idx == None
            # build the index
            self._buildcorpusindex()
            xmlfname = self._fulltext_idx[fn_docid].filename
        except KeyError:  # probably means that fn_docid was not in the index
            raise FramenetError("Unknown document id: {0}".format(fn_docid))

        # construct the path name for the xml file containing the document info
        locpath = os.path.join(
            "{0}".format(self._root), self._fulltext_dir, xmlfname)

        # Grab the top-level xml element containing the fulltext annotation
        elt = XMLCorpusView(locpath, 'fullTextAnnotation')[0]
        return self._handle_fulltextannotation_elt(elt)

    def frame_by_id(self, fn_fid, ignorekeys=[]):
        """
        Get the details for the specified Frame using the frame's id
        number.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame_by_id(256)
        >>> f.ID
        256
        >>> f.name
        'Medical_specialties'
        >>> f.definition # doctest: +ELLIPSIS
        "This frame includes words that name ..."

        :param fn_fid: The Framenet id number of the frame
        :type fn_fid: int
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: Information about a frame
        :rtype: dict

        Also see the ``frame()`` function for details about what is
        contained in the dict that is returned.
        """

        # get the name of the frame with this id number
        try:
            name = self._frame_idx[fn_fid]['name']
        except TypeError:
            self._buildframeindex()
            name = self._frame_idx[fn_fid]['name']
        except KeyError:
            raise FramenetError('Unknown frame id: {0}'.format(fn_fid))

        return self.frame_by_name(name, ignorekeys)

    def frame_by_name(self, fn_fname, ignorekeys=[]):
        """
        Get the details for the specified Frame using the frame's name.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame_by_name('Medical_specialties')
        >>> f.ID
        256
        >>> f.name
        'Medical_specialties'
        >>> f.definition # doctest: +ELLIPSIS
        "This frame includes words that name ..."

        :param fn_fname: The name of the frame
        :type fn_fname: str
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: Information about a frame
        :rtype: dict

        Also see the ``frame()`` function for details about what is
        contained in the dict that is returned.
        """

        # construct the path name for the xml file containing the Frame info
        locpath = os.path.join(
            "{0}".format(self._root), self._frame_dir, fn_fname + ".xml")

        # Grab the xml for the frame
        try:
            elt = XMLCorpusView(locpath, 'frame')[0]
        except IOError:
            raise FramenetError('Unknown frame: {0}'.format(fn_fname)) 

        return self._handle_frame_elt(elt, ignorekeys)

    def frame(self, fn_fid_or_fname, ignorekeys=[]):
        """
        Get the details for the specified Frame using the frame's name
        or id number.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame(256)
        >>> f.name
        'Medical_specialties'
        >>> f = fn.frame('Medical_specialties')
        >>> f.ID
        256

        The dict that is returned from this function will contain the
        following information about the Frame:

        - 'name'       : the name of the Frame (e.g. 'Birth', 'Apply_heat', etc.)
        - 'definition' : textual definition of the Frame
        - 'ID'         : the internal ID number of the Frame
        - 'semType'    : a list of semantic types for this frame
           - Each item in the list is a dict containing the following keys:
              - 'name' : can be used with the semtype() function
              - 'ID'   : can be used with the semtype() function

        - 'lexUnit'    : a list of the LUs for this frame
           - Each item in the list is a dict containing the following keys:
              - 'name' : lemma+POS (e.g. 'acromegaly.n')
              - 'ID'   : id number of the LU (can be used with the lu() function)
              - 'status':
              - 'incorporatedFE': FE that incorporates this LU (e.g. 'Ailment')
              - 'POS'  : e.g. 'N'
              - 'lemmaID': Can be used to connect lemmas in different LUs, not needed though.
              - 'definition': meaning of this LU
              - 'sentenceCount': a dict with the following two keys:
                 - 'annotated': number of sentences annotated with this LU
                 - 'total': total number of sentences with this LU
              - 'lexeme': a list of dicts, where each dict has the following keys:
                 - 'order': the order of the lexeme in the lemma (starting from 1)
                 - 'headword': a boolean ('true' or 'false')
                 - 'breakBefore': Can this lexeme be separated from the previous lexeme?
                                  Consider: "take over.v" as in:
                                      Germany took over the Netherlands in 2 days.
                                      Germany took the Netherlands over in 2 days.
                                  In this case, 'breakBefore' would be "true" for the lexeme
                                  "over". Contrast this with "take after.v" as in:
                                      Mary takes after her grandmother.
                                     *Mary takes her grandmother after.
                                  In this case, 'breakBefore' would be "false" for the lexeme
                                  "after".
                 - 'POS': part of speech of this lexeme
                 - 'name': the lexeme name (e.g. "german" or "measles")

        - 'FE' : a list of the Frame Elements that are part of this frame
           - Each item in the list is a dict containing the following keys
              - 'definition'
              - 'name'
              - 'ID'
              - 'abbrev'
              - 'coreType': one of "Core", "Peripheral", or "Extra-Thematic"
              - 'semType' : a dict containing the following two keys
                 - 'name' : name of the semantic type. can be used with the semtype() function
                 - 'ID'   : id number of the semantic type. can be used with the semtype() function
              - 'requiresFE' : a dict containing the following two keys:
                 - 'name' : the name of another FE in this frame
                 - 'ID'   : the id of the other FE in this frame
              - 'excludesFE' : a dict containing the following two keys:
                 - 'name' : the name of another FE in this frame
                 - 'ID'   : the id of the other FE in this frame

        - 'frameRelation'      : a list frame relations
           - Each item in the list is dict containing the following keys:
              - 'type'         : a string describing the relationship
              - 'relatedFrame' : a list of frame names that participate in this relationship

        - 'FEcoreSet'  : a list of Frame Element core sets for this frame
           - Each item in the list is a dict with the following keys:
              - 'name' : the name of the Frame Element
              - 'ID'   : the id number of the Frame Element

        :param fn_fid_or_fname: The Framenet name or id number of the frame
        :type fn_fid_or_fname: int or str
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: Information about a frame
        :rtype: dict
        """

        # get the frame info by name or id number
        if isinstance(fn_fid_or_fname, string_types):
            f = self.frame_by_name(fn_fid_or_fname, ignorekeys)
        else:
            f = self.frame_by_id(fn_fid_or_fname, ignorekeys)

        return f

    def frames_by_lemma(self, pat):
        """
        Returns a list of all frames that contain LUs in which the
        ``name`` attribute of the LU matchs the given regular expression
        ``pat``. Note that LU names are composed of "lemma.POS", where
        the "lemma" part can be made up of either a single lexeme
        (e.g. 'run') or multiple lexemes (e.g. 'a little').

        Note: if you are going to be doing a lot of this type of
        searching, you'd want to build an index that maps from lemmas to
        frames because each time frames_by_lemma() is called, it has to
        search through ALL of the frame XML files in the db.

        >>> from nltk.corpus import framenet as fn
        >>> fn.frames_by_lemma(r'(?i)a little')
        [<frame ID=189 name=Quantity>, <frame ID=2001 name=Degree>]

        :return: A list of frame objects.
        :rtype: list(AttrDict)
        """
        return PrettyList(f for f in self.frames() if any(re.search(pat, luName) for luName in f.lexUnit))

    def lu_basic(self, fn_luid):
        """
        Returns basic information about the LU whose id is
        ``fn_luid``. This is basically just a wrapper around the
        ``lu()`` function with "subCorpus" info excluded.

        >>> from nltk.corpus import framenet as fn
        >>> PrettyDict(fn.lu_basic(256))
        {'status': 'FN1_Sent', 'definition': 'COD: be aware of beforehand; predict.', '_type': 'lu', 'name': 'foresee.v', 'frame': 'Expectation', 'POS': 'V', 'frameID': 26, 'lexeme': {'POS': 'V', 'name': 'foresee'}, 'semType': {}, 'totalAnnotated': 44, 'ID': 256}

        :param fn_luid: The id number of the desired LU
        :type fn_luid: int
        :return: Basic information about the lexical unit
        :rtype: dict
        """
        return self.lu(fn_luid, ignorekeys=['subCorpus'])

    def lu(self, fn_luid, ignorekeys=[]):
        """
        Get information about a specific Lexical Unit using the id number
        ``fn_luid``. This function reads the LU information from the xml
        file on disk each time it is called. You may want to cache this
        info if you plan to call this function with the same id number
        multiple times.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> fn.lu(256).name
        'foresee.v'
        >>> fn.lu(256).definition
        'COD: be aware of beforehand; predict.'
        >>> fn.lu(256).frame
        'Expectation'
        >>> dict(fn.lu(256).lexeme)
        {'POS': 'V', 'name': 'foresee'}

        The dict that is returned from this function will contain the
        following information about the LU:

        - 'name'       : the name of the LU (e.g. 'merger.n')
        - 'definition' : textual definition of the LU
        - 'ID'         : the internal ID number of the LU
        - 'status'     : e.g. 'Created'
        - 'frame'      : name of the Frame that this LU belongs to
        - 'frameID'    : id number of the Frame that this LU belongs to
        - 'POS'        : the part of speech of this LU (e.g. 'N')
        - 'totalAnnotated' : total number of examples annotated with this LU
        - 'lexeme'     : a dict describing the lemma of this LU. Contains these keys:
           - 'POS'     : part of speech e.g. 'N'
           - 'name'    : either single-lexeme e.g. 'merger' or multi-lexeme e.g. 'a little'
        - 'semType'    : a list of semantic types for this LU
           - Each item in the list is a dict containing the following keys:
              - 'name' : can be used with the semtype() function
              - 'ID'   : can be used with the semtype() function
        - 'subCorpus'  : a list of subcorpora
           - Each item in the list is a dict containing the following keys:
              - 'name' :
              - 'sentence' : a list of sentences in the subcorpus
                 - each item in the list is a dict with the following keys:
                    - 'ID':
                    - 'sentNo':
                    - 'text': the text of the sentence
                    - 'aPos':
                    - 'annotationSet': a list of annotation sets
                       - each item in the list is a dict with the following keys:
                          - 'ID':
                          - 'status':
                          - 'layer': a list of layers
                             - each layer is a dict containing the following keys:
                                - 'name': layer name (e.g. 'BNC')
                                - 'rank':
                                - 'label': a list of labels for the layer
                                   - each label is a dict containing the following keys:
                                      - 'start': start pos of label in sentence 'text' (0-based)
                                      - 'end': end pos of label in sentence 'text' (0-based)
                                      - 'name': name of label (e.g. 'NN1')

        :param fn_luid: The id number of the lexical unit
        :type fn_luid: int
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: All information about the lexical unit
        :rtype: dict
        """

        fname = "lu{0}.xml".format(fn_luid)
        locpath = os.path.join("{0}".format(self._root), self._lu_dir, fname)

        try:
            elt = XMLCorpusView(locpath, 'lexUnit')[0]
        except IOError:
            raise FramenetError('Unknown LU id: {0}'.format(fn_luid))

        return self._handle_lexunit_elt(elt, ignorekeys)

    def _loadsemtypes(self):
        """Create the semantic types index."""
        self._semtypes = AttrDict()
        for st in self.semtypes():
            n = st['name']
            a = st['abbrev']
            i = st['ID']
            # Both name and abbrev should be able to retrieve the
            # ID. The ID will retrieve the semantic type dict itself.
            self._semtypes[n] = i
            self._semtypes[a] = i
            self._semtypes[i] = st

    def semtype(self, key):
        """
        >>> from nltk.corpus import framenet as fn
        >>> fn.semtype(233).name
        'Temperature'
        >>> fn.semtype(233).abbrev
        'Temp'
        >>> fn.semtype('Temperature').ID
        233

        :param key: The name, abbreviation, or id number of the semantic type
        :type key: string or int
        :return: Information about a semantic type
        :rtype: dict
        """
        if isinstance(key,int):
            stid = key
        else:
            try:
                stid = self._semtypes[key]
            except TypeError:
                self._loadsemtypes()
                stid = self._semtypes[key]

        try:
            st = self._semtypes[stid]
        except TypeError:
            self._loadsemtypes()
            st = self._semtypes[stid]

        return st

    def frames(self, name=None):
        """
        Obtain details for a specific frame.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.frames())
        1019
        >>> fn.frames(r'(?i)medical')
        [<frame ID=239 name=Medical_conditions>, <frame ID=256 name=Medical_specialties>, ...]

        A brief intro to Frames (excerpted from "FrameNet II: Extended
        Theory and Practice" by Ruppenhofer et. al., 2010):

        A Frame is a script-like conceptual structure that describes a
        particular type of situation, object, or event along with the
        participants and props that are needed for that Frame. For
        example, the "Apply_heat" frame describes a common situation
        involving a Cook, some Food, and a Heating_Instrument, and is
        evoked by words such as bake, blanch, boil, broil, brown,
        simmer, steam, etc.

        We call the roles of a Frame "frame elements" (FEs) and the
        frame-evoking words are called "lexical units" (LUs).

        FrameNet includes relations between Frames. Several types of
        relations are defined, of which the most important are:

           - Inheritance: An IS-A relation. The child frame is a subtype
             of the parent frame, and each FE in the parent is bound to
             a corresponding FE in the child. An example is the
             "Revenge" frame which inherits from the
             "Rewards_and_punishments" frame.

           - Using: The child frame presupposes the parent frame as
             background, e.g the "Speed" frame "uses" (or presupposes)
             the "Motion" frame; however, not all parent FEs need to be
             bound to child FEs.

           - Subframe: The child frame is a subevent of a complex event
             represented by the parent, e.g. the "Criminal_process" frame
             has subframes of "Arrest", "Arraignment", "Trial", and
             "Sentencing".

           - Perspective_on: The child frame provides a particular
             perspective on an un-perspectivized parent frame. A pair of
             examples consists of the "Hiring" and "Get_a_job" frames,
             which perspectivize the "Employment_start" frame from the
             Employer's and the Employee's point of view, respectively.

        :param name: A regular expression pattern used to match against
            Frame names. If 'name' is None, then a list of all
            Framenet Frames will be returned.
        :type name: str
        :return: A list of matching Frames (or all Frames).
        :rtype: list(AttrDict)
        """
        try:
            flist = self._frame_idx.values()
        except AttributeError:
            self._buildframeindex()
            flist = self._frame_idx.values()

        if name is None:
            return PrettyList(self.frame(f.ID) for f in flist)
        else:
            return PrettyList(self.frame(f.ID) for f in flist if re.search(name, f.name) is not None)

    def lus(self, name=None):
        """
        Obtain details for a specific lexical unit.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.lus())
        11829
        >>> fn.lus(r'(?i)a little')
        [<lu ID=14733 name=a little.n>, <lu ID=14743 name=a little.adv>, ...]
        >>> PrettyDict(fn.lu(14743))
        {'status': 'Created', 'definition': 'FN: to a small degree', '_type': 'lu', 'subCorpus': [], 'name': 'a little.adv', 'frame': 'Degree', 'POS': 'ADV', 'frameID': 2001, 'lexeme': {'POS': 'A', 'headword': 'true', 'breakBefore': 'false', 'order': 2, 'name': 'little'}, 'semType': {}, 'totalAnnotated': 0, 'ID': 14743}

        A brief intro to Lexical Units (excerpted from "FrameNet II:
        Extended Theory and Practice" by Ruppenhofer et. al., 2010):

        A lexical unit (LU) is a pairing of a word with a meaning. For
        example, the "Apply_heat" Frame describes a common situation
        involving a Cook, some Food, and a Heating Instrument, and is
        _evoked_ by words such as bake, blanch, boil, broil, brown,
        simmer, steam, etc. These frame-evoking words are the LUs in the
        Apply_heat frame. Each sense of a polysemous word is a different
        LU.

        We have used the word "word" in talking about LUs. The reality
        is actually rather complex. When we say that the word "bake" is
        polysemous, we mean that the lemma "bake.v" (which has the
        word-forms "bake", "bakes", "baked", and "baking") is linked to
        three different frames:

           - Apply_heat: "Michelle baked the potatoes for 45 minutes."

           - Cooking_creation: "Michelle baked her mother a cake for her birthday."

           - Absorb_heat: "The potatoes have to bake for more than 30 minutes."

        These constitute three different LUs, with different
        definitions.

        Multiword expressions such as "given name" and hyphenated words
        like "shut-eye" can also be LUs. Idiomatic phrases such as
        "middle of nowhere" and "give the slip (to)" are also defined as
        LUs in the appropriate frames ("Isolated_places" and "Evading",
        respectively), and their internal structure is not analyzed.

        Framenet provides multiple annotated examples of each sense of a
        word (i.e. each LU).  Moreover, the set of examples
        (approximately 20 per LU) illustrates all of the combinatorial
        possibilities of the lexical unit.

        Each LU is linked to a Frame, and hence to the other words which
        evoke that Frame. This makes the FrameNet database similar to a
        thesaurus, grouping together semantically similar words.

        In the simplest case, frame-evoking words are verbs such as
        "fried" in:

           "Matilde fried the catfish in a heavy iron skillet."

        Sometimes event nouns may evoke a Frame. For example,
        "reduction" evokes "Cause_change_of_scalar_position" in:

           "...the reduction of debt levels to $665 million from $2.6 billion."

        Adjectives may also evoke a Frame. For example, "asleep" may
        evoke the "Sleep" frame as in:

           "They were asleep for hours."

        Many common nouns, such as artifacts like "hat" or "tower",
        typically serve as dependents rather than clearly evoking their
        own frames.

        :param name: A regular expression pattern used to search the LU
            names. Note that LU names take the form of a dotted
            string (e.g. "run.v" or "a little.adv") in which a
            lemma preceeds the "." and a POS follows the
            dot. The lemma may be composed of a single lexeme
            (e.g. "run") or of multiple lexemes (e.g. "a
            little"). If 'name' is not given, then all LUs will
            be returned.

            The list of valid POSs are:

                   v    - verb
                   n    - noun
                   a    - adjective
                   adv  - adverb
                   prep - preposition
                   num  - numbers
                   intj - interjection
        :type name: str
        :return: A list of selected (or all) lexical units
        :rtype: list of dicts, where each dict object contains the following
           keys:

               - 'name'
               - 'ID'
               - 'hasAnnotation'
               - 'frameID'
               - 'frameName'
               - 'status'
        """

        try:
            lulist = PrettyList(self._lu_idx.values())
        except AttributeError:
            self._buildluindex()
            lulist = PrettyList(self._lu_idx.values())

        for lu in lulist:
            lu['_type'] = 'lu'

        if name is None:
            return lulist
        else:
            return PrettyList(x for x in lulist if re.search(name, x['name']) is not None)

    def documents(self, name=None):
        """
        Return a list of the annotated documents in Framenet.

        Details for a specific annotated document can be obtained using this
        class's annotated_document() function and pass it the value of the 'ID' field.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.documents())
        78
        >>> set([x.corpname for x in fn.documents()])
        set(['NTI', 'LUCorpus-v0.3', 'ANC', 'Miscellaneous', 'PropBank', 'KBEval', 'QA', 'SemAnno', 'C-4'])

        :param name: A regular expression pattern used to search the
            file name of each annotated document. The document's
            file name contains the name of the corpus that the
            document is from, followed by two underscores "__"
            followed by the document name. So, for example, the
            file name "LUCorpus-v0.3__20000410_nyt-NEW.xml" is
            from the corpus named "LUCorpus-v0.3" and the
            document name is "20000410_nyt-NEW.xml".
        :type name: str
        :return: A list of selected (or all) annotated documents
        :rtype: list of dicts, where each dict object contains the following
                keys:

                - 'name'
                - 'ID'
                - 'corpid'
                - 'corpname'
                - 'description'
                - 'filename'
        """
        try:
            ftlist = PrettyList(self._fulltext_idx.values())
        except AttributeError:
            self._buildcorpusindex()
            ftlist = PrettyList(self._fulltext_idx.values())

        if name is None:
            return ftlist
        else:
            return PrettyList(x for x in ftlist if re.search(name, x['filename']) is not None)

    def frame_relation_types(self):
        """
        Obtain a list of frame relation types.

        >>> from nltk.corpus import framenet as fn
        >>> frts = fn.frame_relation_types()
        >>> isinstance(frts,list)
        True
        >>> len(frts)
        9
        >>> dict(frts[0])
        {'_type': 'framerelationtype', 'subFrameName': 'Child', 'ID': 1, 'name': 'Inheritance', 'superFrameName': 'Parent'}

        :return: A list of all of the frame relation types in framenet
        :rtype: list(dict)
        """
        frtypes = PrettyList(x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                            'frameRelations/frameRelationType',
                                            self._handle_elt))
        for frt in frtypes:
            frt['_type'] = 'framerelationtype'

        return frtypes

    def frame_relations(self):
        """
        :return: A list of all of the frame relations in framenet
        :rtype: list(dict)

        >>> from nltk.corpus import framenet as fn
        >>> frels = fn.frame_relations()
        >>> isinstance(frels,list)
        True
        >>> len(frels)
        1676

        """
        return PrettyList(x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                         'frameRelations/frameRelationType/frameRelation',
                                         self._handle_elt))

    def fe_relations(self):
        """
        Obtain a list of frame element relations.

        >>> from nltk.corpus import framenet as fn
        >>> ferels = fn.fe_relations()
        >>> isinstance(ferels,list)
        True
        >>> len(ferels)
        10020
        >>> dict(ferels[0])
        {'subID': 2921, 'subFEName': 'Time', 'superFEName': 'Time', 'ID': 808, 'supID': 1446}

        :return: A list of all of the frame element relations in framenet
        :rtype: list(dict)
        """
        return PrettyList(x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                         'frameRelations/frameRelationType/frameRelation/FERelation',
                                         self._handle_elt))

    def semtypes(self):
        """
        Obtain a list of semantic types.

        >>> from nltk.corpus import framenet as fn
        >>> stypes = fn.semtypes()
        >>> len(stypes)
        73
        >>> stypes[0].keys()
        ['definition', '_type', 'name', 'abbrev', 'superType', 'ID']

        :return: A list of all of the semantic types in framenet
        :rtype: list(dict)
        """
        return PrettyList(x for x in XMLCorpusView(self.abspath("semTypes.xml"),
                                         'semTypes/semType',
                                         self._handle_semtype_elt))

    def _load_xml_attributes(self, d, elt):
        """
        Extracts a subset of the attributes from the given element and
        returns them in a dictionary.

        :param d: A dictionary in which to store the attributes.
        :type d: dict
        :param elt: An ElementTree Element
        :type elt: Element
        :return: Returns the input dict ``d`` possibly including attributes from ``elt``
        :rtype: dict
        """

        d = AttrDict(d)

        try:
            attr_dict = elt.attrib
        except AttributeError:
            return d

        if attr_dict is None:
            return d

        # Ignore these attributes when loading attributes from an xml node
        ignore_attrs = ['cBy', 'cDate', 'mDate', 'xsi',
                        'schemaLocation', 'xmlns', 'bgColor', 'fgColor']

        for attr in list(attr_dict.keys()):

            if any(attr.endswith(x) for x in ignore_attrs):
                continue

            val = attr_dict[attr]
            if val.isdigit():
                d[attr] = int(val)
            else:
                d[attr] = val

        return d

    def _strip_tags(self, data):
        """
        Gets rid of all tags and newline characters from the given input

        :return: A cleaned-up version of the input string
        :rtype: str
        """

        try:
            data = data.replace('<t>', '')
            data = data.replace('</t>', '')
            data = re.sub('<fex name="[^"]+">', '', data)
            data = data.replace('</fex>', '')
            data = data.replace('<fen>', '')
            data = data.replace('</fen>', '')
            data = data.replace('<m>', '')
            data = data.replace('</m>', '')
            data = data.replace('<ment>', '')
            data = data.replace('</ment>', '')
            data = data.replace('<ex>', "'")
            data = data.replace('</ex>', "'")
            data = data.replace('<gov>', '')
            data = data.replace('</gov>', '')
            data = data.replace('<x>', '')
            data = data.replace('</x>', '')

            # Get rid of <def-root> and </def-root> tags
            data = data.replace('<def-root>', '')
            data = data.replace('</def-root>', '')

            data = data.replace('\n', ' ')
        except AttributeError:
            pass

        return data

    def _handle_elt(self, elt, tagspec=None):
        """Extracts and returns the attributes of the given element"""
        return self._load_xml_attributes(AttrDict(), elt)

    def _handle_fulltextindex_elt(self, elt, tagspec=None):
        """
        Extracts corpus/document info from the fulltextIndex.xml file.

        Note that this function "flattens" the information contained
        in each of the "corpus" elements, so that each "document"
        element will contain attributes for the corpus and
        corpusid. Also, each of the "document" items will contain a
        new attribute called "filename" that is the base file name of
        the xml file for the document in the "fulltext" subdir of the
        Framenet corpus.
        """
        ftinfo = self._load_xml_attributes(AttrDict(), elt)
        corpname = ftinfo.name
        corpid = ftinfo.ID
        retlist = []
        for sub in elt:
            if sub.tag.endswith('document'):
                doc = self._load_xml_attributes(AttrDict(), sub)
                if 'name' in doc:
                    docname = doc.name
                else:
                    docname = doc.description
                doc.filename = "{0}__{1}.xml".format(corpname, docname)
                doc.corpname = corpname
                doc.corpid = corpid
                retlist.append(doc)

        return retlist

    def _handle_frame_elt(self, elt, ignorekeys=[]):
        """Load the info for a Frame from an frame xml file"""
        frinfo = self._load_xml_attributes(AttrDict(), elt)

        frinfo['_type'] = 'frame'
        frinfo['definition'] = ""
        frinfo['FE'] = PrettyDict()
        frinfo['FEcoreSet'] = []
        frinfo['frameRelation'] = []
        frinfo['lexUnit'] = PrettyDict()
        frinfo['semType'] = []
        for k in ignorekeys:
            if k in frinfo:
                del frinfo[k]

        for sub in elt:
            if sub.tag.endswith('definition') and 'definition' not in ignorekeys:
                frinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('FE') and 'FE' not in ignorekeys:
                feinfo = self._handle_fe_elt(sub)
                frinfo['FE'][feinfo.name] = feinfo
            elif sub.tag.endswith('FEcoreSet') and 'FEcoreSet' not in ignorekeys:
                frinfo['FEcoreSet'].extend(self._handle_fecoreset_elt(sub))
            elif sub.tag.endswith('frameRelation') and 'frameRelation' not in ignorekeys:
                fr = self._handle_framerelation_elt(sub)
                if fr is not None:
                    frinfo['frameRelation'].append(fr)
            elif sub.tag.endswith('lexUnit') and 'lexUnit' not in ignorekeys:
                luinfo = self._handle_framelexunit_elt(sub)
                frinfo['lexUnit'][luinfo.name] = luinfo
            elif sub.tag.endswith('semType') and 'semType' not in ignorekeys:
                frinfo['semType'].append(
                    self._load_xml_attributes(AttrDict(), sub))

        return frinfo

    def _handle_fecoreset_elt(self, elt):
        """Load fe coreset info from xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        tmp = []
        for sub in elt:
            tmp.append(self._load_xml_attributes(AttrDict(), sub))

        return tmp

    def _handle_framerelation_elt(self, elt):
        """Load frame relation info from an xml element in a frame."""
        if len(elt) == 0:
            return None
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = 'framerelation'
        info['relatedFrame'] = []
        for sub in elt:
            if sub.tag.endswith('relatedFrame'):
                info['relatedFrame'].append(sub.text)

        return info

    def _handle_fulltextannotation_elt(self, elt):
        """Load full annotation info for a document from its xml
        file. The main element (fullTextAnnotation) contains a 'header'
        element (which we ignore here) and a bunch of 'sentence'
        elements."""
        info = AttrDict()
        info['_type'] = 'fulltextannotation'
        info['sentence'] = []

        for sub in elt:
            if sub.tag.endswith('header'):
                continue  # not used
            elif sub.tag.endswith('sentence'):
                s = self._handle_fulltext_sentence_elt(sub)
                info['sentence'].append(s)

        return info

    def _handle_fulltext_sentence_elt(self, elt):
        """Load information from the given 'sentence' element. Each
        'sentence' element contains a "text" and an "annotationSet" sub
        element."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = "sentence"
        info['annotationSet'] = []
        info['text'] = ""

        for sub in elt:
            if sub.tag.endswith('text'):
                info['text'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('annotationSet'):
                a = self._handle_fulltextannotationset_elt(sub)
                info['annotationSet'].append(a)

        return info

    def _handle_fulltextannotationset_elt(self, elt):
        """Load information from the given 'annotationSet' element. Each
        'annotationSet' contains several "layer" elements."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = "annotationset"
        info['layer'] = []

        for sub in elt:
            if sub.tag.endswith('layer'):
                l = self._handle_fulltextlayer_elt(sub)
                info['layer'].append(l)

        return info

    def _handle_fulltextlayer_elt(self, elt):
        """Load information from the given 'layer' element. Each
        'layer' contains several "label" elements."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = 'layer'
        info['label'] = []

        for sub in elt:
            if sub.tag.endswith('label'):
                l = self._load_xml_attributes(AttrDict(), sub)
                info['label'].append(l)

        return info

    def _handle_framelexunit_elt(self, elt):
        """Load the lexical unit info from an xml element in a frame's xml file."""
        luinfo = AttrDict()
        luinfo['_type'] = 'framelexunit'
        luinfo['incorporatedFE'] = ""
        luinfo = self._load_xml_attributes(luinfo, elt)
        luinfo["definition"] = ""
        luinfo["sentenceCount"] = AttrDict()
        luinfo["lexeme"] = []

        for sub in elt:
            if sub.tag.endswith('definition'):
                luinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('sentenceCount'):
                luinfo['sentenceCount'] = self._load_xml_attributes(
                    AttrDict(), sub)
            elif sub.tag.endswith('lexeme'):
                luinfo['lexeme'].append(
                    self._load_xml_attributes(AttrDict(), sub))

        return luinfo

    def _handle_lexunit_elt(self, elt, ignorekeys):
        """Load full info for a lexical unit from its xml file."""
        luinfo = self._load_xml_attributes(AttrDict(), elt)
        luinfo['_type'] = 'lu'
        luinfo['definition'] = ""
        luinfo['subCorpus'] = []
        luinfo['lexeme'] = AttrDict()
        luinfo['semType'] = AttrDict()
        for k in ignorekeys:
            if k in luinfo:
                del luinfo[k]

        for sub in elt:
            if sub.tag.endswith('header'):
                continue  # not used
            elif sub.tag.endswith('valences'):
                continue  # not used
            elif sub.tag.endswith('definition') and 'definition' not in ignorekeys:
                luinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('subCorpus') and 'subCorpus' not in ignorekeys:
                sc = self._handle_lusubcorpus_elt(sub)
                if sc is not None:
                    luinfo['subCorpus'].append(sc)
            elif sub.tag.endswith('lexeme') and 'lexeme' not in ignorekeys:
                luinfo['lexeme'] = self._load_xml_attributes(AttrDict(), sub)
            elif sub.tag.endswith('semType') and 'semType' not in ignorekeys:
                luinfo['semType'] = self._load_xml_attributes(AttrDict(), sub)

        return luinfo

    def _handle_lusubcorpus_elt(self, elt):
        """Load a subcorpus of a lexical unit from the given xml."""
        sc = AttrDict()
        try:
            sc['name'] = str(elt.get('name'))
        except AttributeError:
            return None
        sc['_type'] = "lusubsorpus"
        sc['sentence'] = []

        for sub in elt:
            if sub.tag.endswith('sentence'):
                s = self._handle_lusentence_elt(sub)
                if s is not None:
                    sc['sentence'].append(s)

        return sc

    def _handle_lusentence_elt(self, elt):
        """Load a sentence from a subcorpus of an lu from xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = 'lusentence'
        info['annotationSet'] = []
        for sub in elt:
            if sub.tag.endswith('text'):
                info['text'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('annotationSet'):
                annset = self._handle_luannotationset_elt(sub)
                if annset is not None:
                    info['annotationSet'].append(annset)
        return info

    def _handle_luannotationset_elt(self, elt):
        """Load an annotation set from a sentence in an subcorpus of an LU"""
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = 'luannotationset'
        info['layer'] = []
        for sub in elt:
            if sub.tag.endswith('layer'):
                l = self._handle_lulayer_elt(sub)
                if l is not None:
                    info['layer'].append(l)
        return info

    def _handle_lulayer_elt(self, elt):
        """Load a layer from an annotation set"""
        layer = self._load_xml_attributes(AttrDict(), elt)
        layer['_type'] = 'lulayer'
        layer['label'] = []

        for sub in elt:
            if sub.tag.endswith('label'):
                l = self._load_xml_attributes(AttrDict(), sub)
                if l is not None:
                    layer['label'].append(l)
        return layer

    def _handle_fe_elt(self, elt):
        feinfo = self._load_xml_attributes(AttrDict(), elt)
        feinfo['_type'] = 'fe'
        feinfo['definition'] = ""
        feinfo['semType'] = None
        feinfo['requiresFE'] = None
        feinfo['excludesFE'] = None
        for sub in elt:
            if sub.tag.endswith('definition'):
                feinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('semType'):
                feinfo['semType'] = self._load_xml_attributes(AttrDict(), sub)
            elif sub.tag.endswith('requiresFE'):
                feinfo['requiresFE'] = self._load_xml_attributes(AttrDict(), sub)
            elif sub.tag.endswith('excludesFE'):
                feinfo['excludesFE'] = self._load_xml_attributes(AttrDict(), sub)

        return feinfo

    def _handle_semtype_elt(self, elt, tagspec=None):
        semt = self._load_xml_attributes(AttrDict(), elt)
        semt['_type'] = 'semtype'
        for sub in elt:
            if sub.text is not None:
                semt['definition'] = self._strip_tags(sub.text)
            else:
                semt['superType'] = self._load_xml_attributes(AttrDict(), sub)

        return semt


#
# Demo
#
def demo():
    from nltk.corpus import framenet as fn

    #
    # It is not necessary to explicitly build the indexes by calling
    # buildindexes(). We do this here just for demo purposes. If the
    # indexes are not built explicitely, they will be built as needed.
    #
    print('Building the indexes...')
    fn.buildindexes()

    #
    # Get some statistics about the corpus
    #
    print('Number of Frames:', len(fn.frames()))
    print('Number of Lexical Units:', len(fn.lus()))
    print('Number of annotated documents:', len(fn.documents()))
    print()

    #
    # Frames
    #
    print('getting frames whose name matches the (case insensitive) regex: "(?i)medical"')
    medframes = fn.frames(r'(?i)medical')
    print(
        'Found {0} Frames whose name matches "(?i)medical":'.format(len(medframes)))
    print([(f.name, f.ID) for f in medframes])

    #
    # store the first frame in the list of frames
    #
    tmp_id = medframes[0].ID
    m_frame = fn.frame(tmp_id)  # reads all info for the frame

    #
    # get the frame relations
    #
    print(
        '\nNumber of frame relations for the "{0}" ({1}) frame:'.format(m_frame.name,
                                                                        m_frame.ID),
        len(m_frame.frameRelation))
    for fr in m_frame.frameRelation:
        print('   ', fr.type + ":", fr.relatedFrame)

    #
    # get the names of the Frame Elements
    #
    print(
        '\nNumber of Frame Elements in the "{0}" frame:'.format(m_frame.name),
        len(m_frame.FE))
    print('   ', [x for x in m_frame.FE])

    #
    # get the names of the "Core" Frame Elements
    #
    print(
        '\nThe "core" Frame Elements in the "{0}" frame:'.format(m_frame.name))
    print('   ', [x.name for x in m_frame.FE.values() if x.coreType == "Core"])

    #
    # get all of the Lexical Units that are incorporated in the
    # 'Ailment' FE of the 'Medical_conditions' frame (id=239)
    #
    print('\nAll Lexical Units that are incorporated in the "Ailment" FE:')
    m_frame = fn.frame(239)
    ailment_lus = [x for x in m_frame.lexUnit.values() if x.incorporatedFE == 'Ailment']
    print([x.name for x in ailment_lus])

    #
    # get all of the Lexical Units for the frame
    #
    print('\nNumber of Lexical Units in the "{0}" frame:'.format(m_frame.name),
          len(m_frame.lexUnit))
    print('  ', [x.name for x in m_frame.lexUnit.values()[:5]], '...')

    #
    # get basic info on the second LU in the frame
    #
    tmp_id = m_frame.lexUnit['ailment.n'].ID  # grab the id of the specified LU
    luinfo = fn.lu_basic(tmp_id)  # get basic info on the LU
    print('\nInformation on the LU: {0}'.format(luinfo.name))
    pprint(luinfo)

    #
    # Get a list of all of the corpora used for fulltext annotation
    #
    print('\nNames of all of the corpora used for fulltext annotation:')
    allcorpora = set([x.corpname for x in fn.documents()])
    pprint(list(allcorpora))

    #
    # Get the names of the annotated documents in the first corpus
    #
    firstcorp = list(allcorpora)[0]
    firstcorp_docs = fn.documents(firstcorp)
    print(
        '\nNames of the annotated documents in the "{0}" corpus:'.format(firstcorp))
    pprint([x.filename for x in firstcorp_docs])

    #
    # Search for frames containing LUs whose name attribute matches a
    # regexp pattern.
    #
    # Note: if you were going to be doing a lot of this type of
    #       searching, you'd want to build an index that maps from
    #       lemmas to frames because each time frames_by_lemma() is
    #       called, it has to search through ALL of the frame XML files
    #       in the db.
    print('\nSearching for all Frames that have a lemma that matches the regexp: "^run.v$":')
    pprint(fn.frames_by_lemma(r'^run.v$'))

if __name__ == '__main__':
    demo()
