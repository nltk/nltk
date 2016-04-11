# Natural Language Toolkit: Framenet Corpus Reader
#
# Copyright (C) 2001-2016 NLTK Project
# Authors: Chuck Wooters <wooters@icsi.berkeley.edu>,
#          Nathan Schneider <nschneid@cs.cmu.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
from __future__ import print_function, unicode_literals

"""
Corpus reader for the Framenet 1.5 Corpus.
"""

__docformat__ = 'epytext en'

import os, sys
import re
import textwrap
from collections import defaultdict
from pprint import pprint, pformat
from nltk.internals import ElementWrapper
from nltk.corpus.reader import XMLCorpusReader, XMLCorpusView
from nltk.compat import text_type, string_types, python_2_unicode_compatible
from nltk.util import AbstractLazySequence, LazyMap


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
        outstr += prefix + line + '\n'
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
    outstr += "[rootType] {0}({1})\n".format(st.rootType.name, st.rootType.ID)
    if st.superType is None:
        outstr += "[superType] <None>\n"
    else:
        outstr += "[superType] {0}({1})\n".format(st.superType.name, st.superType.ID)
    outstr += "[subTypes] {0} subtypes\n".format(len(st.subTypes))
    outstr += "  " + ", ".join('{0}({1})'.format(x.name, x.ID) for x in st.subTypes) + '\n'*(len(st.subTypes)>0)
    return outstr

def _pretty_frame_relation_type(freltyp):

    """
    Helper function for pretty-printing a frame relation type.

    :param freltyp: The frame relation type to be printed.
    :type freltyp: AttrDict
    :return: A nicely formated string representation of the frame relation type.
    :rtype: str
    """
    outstr = "<frame relation type ({0.ID}): {0.superFrameName} -- {0.name} -> {0.subFrameName}>".format(freltyp)
    return outstr

def _pretty_frame_relation(frel):

    """
    Helper function for pretty-printing a frame relation.

    :param frel: The frame relation to be printed.
    :type frel: AttrDict
    :return: A nicely formated string representation of the frame relation.
    :rtype: str
    """
    outstr = "<{0.type.superFrameName}={0.superFrameName} -- {0.type.name} -> {0.type.subFrameName}={0.subFrameName}>".format(frel)
    return outstr

def _pretty_fe_relation(ferel):

    """
    Helper function for pretty-printing an FE relation.

    :param ferel: The FE relation to be printed.
    :type ferel: AttrDict
    :return: A nicely formated string representation of the FE relation.
    :rtype: str
    """
    outstr = "<{0.type.superFrameName}={0.frameRelation.superFrameName}.{0.superFEName} -- {0.type.name} -> {0.type.subFrameName}={0.frameRelation.subFrameName}.{0.subFEName}>".format(ferel)
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
        outstr += "\n[frame] {0}({1})\n".format(lu.frame.name,lu.frame.ID)
    if 'incorporatedFE' in lukeys:
        outstr += "\n[incorporatedFE] {0}\n".format(lu.incorporatedFE)
    if 'POS' in lukeys:
        outstr += "\n[POS] {0}\n".format(lu.POS)
    if 'status' in lukeys:
        outstr += "\n[status] {0}\n".format(lu.status)
    if 'totalAnnotated' in lukeys:
        outstr += "\n[totalAnnotated] {0} annotated examples\n".format(lu.totalAnnotated)
    if 'lexemes' in lukeys:
        outstr += "\n[lexemes] {0}\n".format(' '.join('{0}/{1}'.format(lex.name,lex.POS) for lex in lu.lexemes))
    if 'semTypes' in lukeys:
        outstr += "\n[semTypes] {0} semantic types\n".format(len(lu.semTypes))
        outstr += "  "*(len(lu.semTypes)>0) + ", ".join('{0}({1})'.format(x.name, x.ID) for x in lu.semTypes) + '\n'*(len(lu.semTypes)>0)
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
    outstr += "frame element ({0.ID}): {0.name}\n    of {1.name}({1.ID})\n".format(fe, fe.frame)
    if 'definition' in fekeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(fe.definition,'  ')
    if 'abbrev' in fekeys:
        outstr += "[abbrev] {0}\n".format(fe.abbrev)
    if 'coreType' in fekeys:
        outstr += "[coreType] {0}\n".format(fe.coreType)
    if 'requiresFE' in fekeys:
        outstr += "[requiresFE] "
        if fe.requiresFE is None:
            outstr += "<None>\n"
        else:
            outstr += "{0}({1})\n".format(fe.requiresFE.name, fe.requiresFE.ID)
    if 'excludesFE' in fekeys:
        outstr += "[excludesFE] "
        if fe.excludesFE is None:
            outstr += "<None>\n"
        else:
            outstr += "{0}({1})\n".format(fe.excludesFE.name, fe.excludesFE.ID)
    if 'semType' in fekeys:
        outstr += "[semType] "
        if fe.semType is None:
            outstr += "<None>\n"
        else:
            outstr += "\n  " + "{0}({1})".format(fe.semType.name, fe.semType.ID) + '\n'

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

    outstr += "[semTypes] {0} semantic types\n".format(len(frame.semTypes))
    outstr += "  "*(len(frame.semTypes)>0) + ", ".join("{0}({1})".format(x.name, x.ID) for x in frame.semTypes) + '\n'*(len(frame.semTypes)>0)

    outstr += "\n[frameRelations] {0} frame relations\n".format(len(frame.frameRelations))
    outstr += '  ' + '\n  '.join(repr(frel) for frel in frame.frameRelations) + '\n'

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
            fes[fe.coreType].append("{0} ({1})".format(feName, fe.ID))
        except KeyError:
            fes[fe.coreType] = []
            fes[fe.coreType].append("{0} ({1})".format(feName, fe.ID))
    for ct in sorted(fes.keys(), key=lambda ct2: ['Core','Core-Unexpressed','Peripheral','Extra-Thematic'].index(ct2)):
        outstr += "{0:>16}: {1}\n".format(ct, ', '.join(sorted(fes[ct])))

    outstr += "\n[FEcoreSets] {0} frame element core sets\n".format(len(frame.FEcoreSets))
    outstr += "  " + '\n  '.join(", ".join([x.name for x in coreSet]) for coreSet in frame.FEcoreSets) + '\n'

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
    >>> pprint(dict(bar))
    {'a': 1, 'b': 2, 'c': 3}
    >>> bar.b
    2
    >>> bar.d = 4
    >>> pprint(dict(bar))
    {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    """

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        #self.__dict__ = self

    def __setattr__(self, name, value):
        self[name] = value
    def __getattr__(self, name):
        if name=='_short_repr':
            return self._short_repr
        return self[name]
    def __getitem__(self, name):
        v = super(AttrDict,self).__getitem__(name)
        if isinstance(v,Future):
            return v._data()
        return v

    def _short_repr(self):
        if '_type' in self:
            if self['_type'].endswith('relation'):
                return self.__repr__()
            try:
                return "<{0} ID={1} name={2}>".format(self['_type'], self['ID'], self['name'])
            except KeyError:    # no ID--e.g., for _type=lusubcorpus
                return "<{0} name={1}>".format(self['_type'], self['name'])
        else:
            return self.__repr__()

    def _str(self):
        outstr = ""

        if not '_type' in self:
            outstr = _pretty_any(self)
        elif self['_type'] == 'frame':
            outstr = _pretty_frame(self)
        elif self['_type'] == 'fe':
            outstr = _pretty_fe(self)
        elif self['_type'] == 'lu':
            outstr = _pretty_lu(self)
        elif self['_type'] == 'semtype':
            outstr = _pretty_semtype(self)
        elif self['_type'] == 'framerelationtype':
            outstr = _pretty_frame_relation_type(self)
        elif self['_type'] == 'framerelation':
            outstr = _pretty_frame_relation(self)
        elif self['_type'] == 'ferelation':
            outstr = _pretty_fe_relation(self)
        else:
            outstr = _pretty_any(self)

        # ensure result is unicode string prior to applying the
        # @python_2_unicode_compatible decorator (because non-ASCII characters
        # could in principle occur in the data and would trigger an encoding error when
        # passed as arguments to str.format()).
        # assert isinstance(outstr, unicode) # not in Python 3.2
        return outstr

    def __str__(self):
        return self._str()
    def __repr__(self):
        return self.__str__()

class Future(object):
    """
    Wraps and acts as a proxy for a value to be loaded lazily (on demand).
    Adapted from https://gist.github.com/sergey-miryanov/2935416
    """
    def __init__(self, loader, *args, **kwargs):
        """
        :param loader: when called with no arguments, returns the value to be stored
        :type loader: callable
        """
        super (Future, self).__init__(*args, **kwargs)
        self._loader = loader
        self._d = None
    def _data(self):
        if callable(self._loader):
            self._d = self._loader()
            self._loader = None # the data is now cached
        return self._d

    def __nonzero__(self):
        return bool(self._data())
    def __len__(self):
        return len(self._data())

    def __setitem__(self, key, value):
        return self._data ().__setitem__(key, value)
    def __getitem__(self, key):
        return self._data ().__getitem__(key)
    def __getattr__(self, key):
        return self._data().__getattr__(key)

    def __str__(self):
        return self._data().__str__()
    def __repr__(self):
        return self._data().__repr__()


@python_2_unicode_compatible
class PrettyDict(AttrDict):
    """
    Displays an abbreviated repr of values where possible.
    Inherits from AttrDict, so a callable value will
    be lazily converted to an actual value.
    """
    def __init__(self, *args, **kwargs):
        _BREAK_LINES = kwargs.pop('breakLines', False)
        super(PrettyDict, self).__init__(*args, **kwargs)
        dict.__setattr__(self, '_BREAK_LINES', _BREAK_LINES)
    def __repr__(self):
        parts = []
        for k,v in sorted(self.items()):
            kv = repr(k)+': '
            try:
                kv += v._short_repr()
            except AttributeError:
                kv += repr(v)
            parts.append(kv)
        return '{'+(',\n ' if self._BREAK_LINES else ', ').join(parts)+'}'

@python_2_unicode_compatible
class PrettyList(list):
    """
    Displays an abbreviated repr of only the first several elements, not the whole list.
    """
    # from nltk.util
    def __init__(self, *args, **kwargs):
        self._MAX_REPR_SIZE = kwargs.pop('maxReprSize', 60)
        self._BREAK_LINES = kwargs.pop('breakLines', False)
        super(PrettyList, self).__init__(*args, **kwargs)
    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5

        for elt in self:
            pieces.append(elt._short_repr()) # key difference from inherited version: call to _short_repr()
            length += len(pieces[-1]) + 2
            if self._MAX_REPR_SIZE and length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % text_type(',\n ' if self._BREAK_LINES else ', ').join(pieces[:-1])
        return "[%s]" % text_type(',\n ' if self._BREAK_LINES else ', ').join(pieces)

@python_2_unicode_compatible
class PrettyLazyMap(LazyMap):
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
            pieces.append(elt._short_repr()) # key difference from inherited version: call to _short_repr()
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % text_type(', ').join(pieces[:-1])
        else:
            return "[%s]" % text_type(', ').join(pieces)

class FramenetCorpusReader(XMLCorpusReader):
    """A corpus reader for the Framenet Corpus.

    >>> from nltk.corpus import framenet as fn
    >>> fn.lu(3238).frame.lexUnit['glint.v'] is fn.lu(3238)
    True
    >>> fn.frame_by_name('Replacing') is fn.lus('replace.v')[0].frame
    True
    >>> fn.lus('prejudice.n')[0].frame.frameRelations == fn.frame_relations('Partiality')
    True
    """

    _bad_statuses = ['Problem']
    """
    When loading LUs for a frame, those whose status is in this list will be ignored.
    Due to caching, if user code modifies this, it should do so before loading any data.
    'Problem' should always be listed for FrameNet 1.5, as these LUs are not included
    in the XML index.
    """

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
        self._cached_frames = {}    # name -> ID
        self._lu_idx = None
        self._fulltext_idx = None
        self._semtypes = None
        self._freltyp_idx = None    # frame relation types (Inheritance, Using, etc.)
        self._frel_idx = None   # frame-to-frame relation instances
        self._ferel_idx = None  # FE-to-FE relation instances
        self._frel_f_idx = None # frame-to-frame relations associated with each frame

    def _buildframeindex(self):
        # The total number of Frames in Framenet is fairly small (~1200) so
        # this index should not be very large
        if not self._frel_idx:
            self._buildrelationindex()  # always load frame relations before frames,
            # otherwise weird ordering effects might result in incomplete information
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
            self._lu_idx[lu['ID']] = lu # populate with LU index entries. if any of these
            # are looked up they will be replaced by full LU objects.

    def _buildrelationindex(self):
        #print('building relation index...', file=sys.stderr)
        freltypes = PrettyList(x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                            'frameRelations/frameRelationType',
                                            self._handle_framerelationtype_elt))
        self._freltyp_idx = {}
        self._frel_idx = {}
        self._frel_f_idx = defaultdict(set)
        self._ferel_idx = {}

        for freltyp in freltypes:
            self._freltyp_idx[freltyp.ID] = freltyp
            for frel in freltyp.frameRelations:
                supF = frel.superFrame = frel[freltyp.superFrameName] = Future((lambda fID: lambda: self.frame_by_id(fID))(frel.supID))
                subF = frel.subFrame = frel[freltyp.subFrameName] = Future((lambda fID: lambda: self.frame_by_id(fID))(frel.subID))
                self._frel_idx[frel.ID] = frel
                self._frel_f_idx[frel.supID].add(frel.ID)
                self._frel_f_idx[frel.subID].add(frel.ID)
                for ferel in frel.feRelations:
                    ferel.superFrame = supF
                    ferel.subFrame = subF
                    ferel.superFE = Future((lambda fer: lambda: fer.superFrame.FE[fer.superFEName])(ferel))
                    ferel.subFE = Future((lambda fer: lambda: fer.subFrame.FE[fer.subFEName])(ferel))
                    self._ferel_idx[ferel.ID] = ferel
        #print('...done building relation index', file=sys.stderr)

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
        # frame and FE relations
        self._buildrelationindex()

    def annotated_document(self, fn_docid):
        """
        Returns the annotated document whose id number is
        ``fn_docid``. This id number can be obtained by calling the
        Documents() function.

        The dict that is returned from this function will contain the
        following keys:

        - '_type'      : 'fulltextannotation'
        - 'sentence'   : a list of sentences in the document
           - Each item in the list is a dict containing the following keys:
              - 'ID'    : the ID number of the sentence
              - '_type' : 'sentence'
              - 'text'  : the text of the sentence
              - 'paragNo' : the paragraph number
              - 'sentNo'  : the sentence number
              - 'docID'   : the document ID number
              - 'corpID'  : the corpus ID number
              - 'aPos'    : the annotation position
              - 'annotationSet' : a list of annotation layers for the sentence
                 - Each item in the list is a dict containing the following keys:
                    - 'ID'       : the ID number of the annotation set
                    - '_type'    : 'annotationset'
                    - 'status'   : either 'MANUAL' or 'UNANN'
                    - 'luName'   : (only if status is 'MANUAL')
                    - 'luID'     : (only if status is 'MANUAL')
                    - 'frameID'  : (only if status is 'MANUAL')
                    - 'frameName': (only if status is 'MANUAL')
                    - 'layer' : a list of labels for the layer
                       - Each item in the layer is a dict containing the
                         following keys:
                          - '_type': 'layer'
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
        >>> f.definition
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
            fentry = self._frame_idx[fn_fid]
            if '_type' in fentry:
                return fentry   # full frame object is cached
            name = fentry['name']
        except TypeError:
            self._buildframeindex()
            name = self._frame_idx[fn_fid]['name']
        except KeyError:
            raise FramenetError('Unknown frame id: {0}'.format(fn_fid))

        return self.frame_by_name(name, ignorekeys, check_cache=False)

    def frame_by_name(self, fn_fname, ignorekeys=[], check_cache=True):
        """
        Get the details for the specified Frame using the frame's name.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame_by_name('Medical_specialties')
        >>> f.ID
        256
        >>> f.name
        'Medical_specialties'
        >>> f.definition
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

        if check_cache and fn_fname in self._cached_frames:
            return self._frame_idx[self._cached_frames[fn_fname]]
        elif not self._frame_idx:
            self._buildframeindex()

        # construct the path name for the xml file containing the Frame info
        locpath = os.path.join(
            "{0}".format(self._root), self._frame_dir, fn_fname + ".xml")
        #print(locpath, file=sys.stderr)
        # Grab the xml for the frame
        try:
            elt = XMLCorpusView(locpath, 'frame')[0]
        except IOError:
            raise FramenetError('Unknown frame: {0}'.format(fn_fname))

        fentry = self._handle_frame_elt(elt, ignorekeys)
        assert fentry

        # INFERENCE RULE: propagate lexical semtypes from the frame to all its LUs
        for st in fentry.semTypes:
            if st.rootType.name=='Lexical_type':
                for lu in fentry.lexUnit.values():
                    if st not in lu.semTypes:
                        lu.semTypes.append(st)


        self._frame_idx[fentry.ID] = fentry
        self._cached_frames[fentry.name] = fentry.ID
        '''
        # now set up callables to resolve the LU pointers lazily.
        # (could also do this here--caching avoids infinite recursion.)
        for luName,luinfo in fentry.lexUnit.items():
            fentry.lexUnit[luName] = (lambda luID: Future(lambda: self.lu(luID)))(luinfo.ID)
        '''
        return fentry

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
        >>> # ensure non-ASCII character in definition doesn't trigger an encoding error:
        >>> fn.frame('Imposing_obligation')
        frame (1494): Imposing_obligation...

        The dict that is returned from this function will contain the
        following information about the Frame:

        - 'name'       : the name of the Frame (e.g. 'Birth', 'Apply_heat', etc.)
        - 'definition' : textual definition of the Frame
        - 'ID'         : the internal ID number of the Frame
        - 'semTypes'   : a list of semantic types for this frame
           - Each item in the list is a dict containing the following keys:
              - 'name' : can be used with the semtype() function
              - 'ID'   : can be used with the semtype() function

        - 'lexUnit'    : a dict containing all of the LUs for this frame.
                         The keys in this dict are the names of the LUs and
                         the value for each key is itself a dict containing
                         info about the LU (see the lu() function for more info.)

        - 'FE' : a dict containing the Frame Elements that are part of this frame
                 The keys in this dict are the names of the FEs (e.g. 'Body_system')
                 and the values are dicts containing the following keys
              - 'definition' : The definition of the FE
              - 'name'       : The name of the FE e.g. 'Body_system'
              - 'ID'         : The id number
              - '_type'      : 'fe'
              - 'abbrev'     : Abbreviation e.g. 'bod'
              - 'coreType'   : one of "Core", "Peripheral", or "Extra-Thematic"
              - 'semType'    : if not None, a dict with the following two keys:
                 - 'name' : name of the semantic type. can be used with
                            the semtype() function
                 - 'ID'   : id number of the semantic type. can be used with
                            the semtype() function
              - 'requiresFE' : if not None, a dict with the following two keys:
                 - 'name' : the name of another FE in this frame
                 - 'ID'   : the id of the other FE in this frame
              - 'excludesFE' : if not None, a dict with the following two keys:
                 - 'name' : the name of another FE in this frame
                 - 'ID'   : the id of the other FE in this frame

        - 'frameRelation'      : a list of objects describing frame relations
        - 'FEcoreSets'  : a list of Frame Element core sets for this frame
           - Each item in the list is a list of FE objects

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
        >>> PrettyDict(fn.lu_basic(256), breakLines=True)
        {'ID': 256,
         'POS': 'V',
         '_type': 'lu',
         'definition': 'COD: be aware of beforehand; predict.',
         'frame': <frame ID=26 name=Expectation>,
         'lemmaID': 15082,
         'lexemes': [{'POS': 'V', 'breakBefore': 'false', 'headword': 'false', 'name': 'foresee', 'order': 1}],
         'name': 'foresee.v',
         'semTypes': [],
         'sentenceCount': {'annotated': 44, 'total': 227},
         'status': 'FN1_Sent'}

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
        >>> fn.lu(256).frame.name
        'Expectation'
        >>> pprint(list(map(PrettyDict, fn.lu(256).lexemes)))
        [{'POS': 'V', 'breakBefore': 'false', 'headword': 'false', 'name': 'foresee', 'order': 1}]

        The dict that is returned from this function will contain most of the
        following information about the LU. Note that some LUs do not contain
        all of these pieces of information - particularly 'totalAnnotated' and
        'incorporatedFE' may be missing in some LUs:

        - 'name'       : the name of the LU (e.g. 'merger.n')
        - 'definition' : textual definition of the LU
        - 'ID'         : the internal ID number of the LU
        - '_type'      : 'lu'
        - 'status'     : e.g. 'Created'
        - 'frame'      : Frame that this LU belongs to
        - 'POS'        : the part of speech of this LU (e.g. 'N')
        - 'totalAnnotated' : total number of examples annotated with this LU
        - 'incorporatedFE' : FE that incorporates this LU (e.g. 'Ailment')
        - 'sentenceCount'  : a dict with the following two keys:
                 - 'annotated': number of sentences annotated with this LU
                 - 'total'    : total number of sentences with this LU

        - 'lexemes'  : a list of dicts describing the lemma of this LU.
           Each dict in the list contains these keys:
           - 'POS'     : part of speech e.g. 'N'
           - 'name'    : either single-lexeme e.g. 'merger' or
                         multi-lexeme e.g. 'a little'
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
                In this case, 'breakBefore' would be "false" for the lexeme "after"

        - 'lemmaID'    : Can be used to connect lemmas in different LUs
        - 'semTypes'   : a list of semantic type objects for this LU
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

        Under the hood, this implementation looks up the lexical unit information
        in the *frame* definition file. That file does not contain
        corpus annotations, so the LU files will be accessed on demand if those are
        needed. In principle, valence patterns could be loaded here too,
        though these are not currently supported.

        :param fn_luid: The id number of the lexical unit
        :type fn_luid: int
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: All information about the lexical unit
        :rtype: dict
        """
        # look for this LU in cache
        if not self._lu_idx:
            self._buildluindex()
        luinfo = self._lu_idx[fn_luid]
        if '_type' not in luinfo:
            # we only have an index entry for the LU. loading the frame will replace this.
            f = self.frame_by_id(luinfo.frameID)
            luinfo = self._lu_idx[fn_luid]
        if ignorekeys:
            return AttrDict(dict((k, v) for k, v in luinfo.items() if k not in ignorekeys))

        return luinfo

    def _lu_file(self, lu, ignorekeys=[]):
        """
        Augment the LU information that was loaded from the frame file
        with additional information from the LU file.
        """
        fn_luid = lu.ID

        fname = "lu{0}.xml".format(fn_luid)
        locpath = os.path.join("{0}".format(self._root), self._lu_dir, fname)
        #print(locpath, file=sys.stderr)
        if not self._lu_idx:
            self._buildluindex()

        try:
            elt = XMLCorpusView(locpath, 'lexUnit')[0]
        except IOError:
            raise FramenetError('Unknown LU id: {0}'.format(fn_luid))

        lu2 = self._handle_lexunit_elt(elt, ignorekeys)
        lu.subCorpus = lu2.subCorpus

        return lu.subCorpus

    def _loadsemtypes(self):
        """Create the semantic types index."""
        self._semtypes = AttrDict()
        semtypeXML = [x for x in XMLCorpusView(self.abspath("semTypes.xml"),
                                             'semTypes/semType',
                                             self._handle_semtype_elt)]
        for st in semtypeXML:
            n = st['name']
            a = st['abbrev']
            i = st['ID']
            # Both name and abbrev should be able to retrieve the
            # ID. The ID will retrieve the semantic type dict itself.
            self._semtypes[n] = i
            self._semtypes[a] = i
            self._semtypes[i] = st
        # now that all individual semtype XML is loaded, we can link them together
        roots = []
        for st in self.semtypes():
            if st.superType:
                st.superType = self.semtype(st.superType.supID)
                st.superType.subTypes.append(st)
            else:
                if st not in roots: roots.append(st)
                st.rootType = st
        queue = list(roots)
        assert queue
        while queue:
            st = queue.pop(0)
            for child in st.subTypes:
                child.rootType = st.rootType
                queue.append(child)
        #self.propagate_semtypes()  # apply inferencing over FE relations

    def propagate_semtypes(self):
        """
        Apply inference rules to distribute semtypes over relations between FEs.
        For FrameNet 1.5, this results in 1011 semtypes being propagated.
        (Not done by default because it requires loading all frame files,
        which takes several seconds. If this needed to be fast, it could be rewritten
        to traverse the neighboring relations on demand for each FE semtype.)

        >>> from nltk.corpus import framenet as fn
        >>> sum(1 for f in fn.frames() for fe in f.FE.values() if fe.semType)
        4241
        >>> fn.propagate_semtypes()
        >>> sum(1 for f in fn.frames() for fe in f.FE.values() if fe.semType)
        5252
        """
        if not self._semtypes:
            self._loadsemtypes()
        if not self._ferel_idx:
            self._buildrelationindex()
        changed = True
        i = 0
        nPropagations = 0
        while changed:
            # make a pass and see if anything needs to be propagated
            i += 1
            changed = False
            for ferel in self.fe_relations():
                superST = ferel.superFE.semType
                subST = ferel.subFE.semType
                try:
                    if superST and superST is not subST:
                        # propagate downward
                        assert subST is None or self.semtype_inherits(subST, superST),(superST.name,ferel,subST.name)
                        if subST is None:
                            ferel.subFE.semType = subST = superST
                            changed = True
                            nPropagations += 1
                    if ferel.type.name in ['Perspective_on', 'Subframe', 'Precedes'] and subST \
                        and subST is not superST:
                        # propagate upward
                        assert superST is None,(superST.name,ferel,subST.name)
                        ferel.superFE.semType = superST = subST
                        changed = True
                        nPropagations += 1
                except AssertionError as ex:
                    # bug in the data! ignore
                    #print(ex, file=sys.stderr)
                    continue
            #print(i, nPropagations, file=sys.stderr)

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
        if isinstance(key, int):
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

    def semtype_inherits(self, st, superST):
        if not isinstance(st, dict):
            st = self.semtype(st)
        if not isinstance(superST, dict):
            superST = self.semtype(superST)
        par = st.superType
        while par:
            if par is superST:
                return True
            par = par.superType
        return False

    def frames(self, name=None):
        """
        Obtain details for a specific frame.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.frames())
        1019
        >>> PrettyList(fn.frames(r'(?i)medical'), maxReprSize=0, breakLines=True)
        [<frame ID=256 name=Medical_specialties>,
         <frame ID=257 name=Medical_instruments>,
         <frame ID=255 name=Medical_professionals>,
         <frame ID=239 name=Medical_conditions>]

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
            fIDs = list(self._frame_idx.keys())
        except AttributeError:
            self._buildframeindex()
            fIDs = list(self._frame_idx.keys())

        if name is not None:
            return PrettyList(self.frame(fID) for fID,finfo in self.frame_ids_and_names(name).items())
        else:
            return PrettyLazyMap(self.frame, fIDs)

    def frame_ids_and_names(self, name=None):
        """
        Uses the frame index, which is much faster than looking up each frame definition
        if only the names and IDs are needed.
        """
        if not self._frame_idx:
            self._buildframeindex()
        return dict((fID, finfo.name) for fID,finfo in self._frame_idx.items() if name is None or re.search(name, finfo.name) is not None)

    def fes(self, name=None):
        '''
        Lists frame element objects. If 'name' is provided, this is treated as 
        a case-insensitive regular expression to filter by frame name. 
        (Case-insensitivity is because casing of frame element names is not always 
        consistent across frames.)
        
        >>> from nltk.corpus import framenet as fn
        >>> fn.fes('Noise_maker')
        [<fe ID=6043 name=Noise_maker>]
        >>> sorted([(fe.frame.name,fe.name) for fe in fn.fes('sound')])
        [('Cause_to_make_noise', 'Sound_maker'), ('Make_noise', 'Sound'), 
         ('Make_noise', 'Sound_source'), ('Sound_movement', 'Location_of_sound_source'), 
         ('Sound_movement', 'Sound'), ('Sound_movement', 'Sound_source'), 
         ('Sounds', 'Component_sound'), ('Sounds', 'Location_of_sound_source'), 
         ('Sounds', 'Sound_source'), ('Vocalizations', 'Location_of_sound_source'), 
         ('Vocalizations', 'Sound_source')]
        >>> sorted(set(fe.name for fe in fn.fes('^sound')))
        ['Sound', 'Sound_maker', 'Sound_source']
        >>> len(fn.fes('^sound$'))
        2
        
        :param name: A regular expression pattern used to match against
            frame element names. If 'name' is None, then a list of all
            frame elements will be returned.
        :type name: str
        :return: A list of matching frame elements
        :rtype: list(AttrDict)
        '''
        return PrettyList(fe for f in self.frames() for fename,fe in f.FE.items() if name is None or re.search(name, fename, re.I))

    def lus(self, name=None):
        """
        Obtain details for a specific lexical unit.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.lus())
        11829
        >>> PrettyList(fn.lus(r'(?i)a little'), maxReprSize=0, breakLines=True)
        [<lu ID=14744 name=a little bit.adv>,
         <lu ID=14733 name=a little.n>,
         <lu ID=14743 name=a little.adv>]

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

            The valid POSes are:

                   v    - verb
                   n    - noun
                   a    - adjective
                   adv  - adverb
                   prep - preposition
                   num  - numbers
                   intj - interjection
                   art  - article
                   c    - conjunction
                   scon - subordinating conjunction

        :type name: str
        :return: A list of selected (or all) lexical units
        :rtype: list of LU objects (dicts). See the lu() function for info
          about the specifics of LU objects.

        """
        try:
            luIDs = list(self._lu_idx.keys())
        except AttributeError:
            self._buildluindex()
            luIDs = list(self._lu_idx.keys())

        if name is not None:
            return PrettyList(self.lu(luID) for luID,luName in self.lu_ids_and_names(name).items())
        else:
            return PrettyLazyMap(self.lu, luIDs)

    def lu_ids_and_names(self, name=None):
        """
        Uses the LU index, which is much faster than looking up each LU definition
        if only the names and IDs are needed.
        """
        if not self._lu_idx:
            self._buildluindex()
        return dict((luID, luinfo.name) for luID,luinfo in self._lu_idx.items() if name is None or re.search(name, luinfo.name) is not None)

    def documents(self, name=None):
        """
        Return a list of the annotated documents in Framenet.

        Details for a specific annotated document can be obtained using this
        class's annotated_document() function and pass it the value of the 'ID' field.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.documents())
        78
        >>> set([x.corpname for x in fn.documents()])==set(['ANC', 'C-4', 'KBEval', \
                    'LUCorpus-v0.3', 'Miscellaneous', 'NTI', 'PropBank', 'QA', 'SemAnno'])
        True

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
        >>> frts = list(fn.frame_relation_types())
        >>> isinstance(frts, list)
        True
        >>> len(frts)
        9
        >>> PrettyDict(frts[0], breakLines=True)
        {'ID': 1,
         '_type': 'framerelationtype',
         'frameRelations': [<Parent=Event -- Inheritance -> Child=Change_of_consistency>, <Parent=Event -- Inheritance -> Child=Rotting>, ...],
         'name': 'Inheritance',
         'subFrameName': 'Child',
         'superFrameName': 'Parent'}

        :return: A list of all of the frame relation types in framenet
        :rtype: list(dict)
        """
        if not self._freltyp_idx:
            self._buildrelationindex()
        return self._freltyp_idx.values()

    def frame_relations(self, frame=None, frame2=None, type=None):
        """
        :param frame: (optional) frame object, name, or ID; only relations involving
        this frame will be returned
        :param frame2: (optional; 'frame' must be a different frame) only show relations
        between the two specified frames, in either direction
        :param type: (optional) frame relation type (name or object); show only relations
        of this type
        :type frame: int or str or AttrDict
        :return: A list of all of the frame relations in framenet
        :rtype: list(dict)

        >>> from nltk.corpus import framenet as fn
        >>> frels = fn.frame_relations()
        >>> isinstance(frels, list)
        True
        >>> len(frels)
        1676
        >>> PrettyList(fn.frame_relations('Cooking_creation'), maxReprSize=0, breakLines=True)
        [<Parent=Intentionally_create -- Inheritance -> Child=Cooking_creation>,
         <Parent=Apply_heat -- Using -> Child=Cooking_creation>,
         <MainEntry=Apply_heat -- See_also -> ReferringEntry=Cooking_creation>]
        >>> PrettyList(fn.frame_relations(373), breakLines=True)
        [<Parent=Topic -- Using -> Child=Communication>,
         <Source=Discussion -- ReFraming_Mapping -> Target=Topic>, ...]
        >>> PrettyList(fn.frame_relations(fn.frame('Cooking_creation')), breakLines=True)
        [<Parent=Intentionally_create -- Inheritance -> Child=Cooking_creation>,
         <Parent=Apply_heat -- Using -> Child=Cooking_creation>, ...]
        >>> PrettyList(fn.frame_relations('Cooking_creation', type='Inheritance'))
        [<Parent=Intentionally_create -- Inheritance -> Child=Cooking_creation>]
        >>> PrettyList(fn.frame_relations('Cooking_creation', 'Apply_heat'), breakLines=True)
        [<Parent=Apply_heat -- Using -> Child=Cooking_creation>,
        <MainEntry=Apply_heat -- See_also -> ReferringEntry=Cooking_creation>]
        """
        relation_type = type

        if not self._frel_idx:
            self._buildrelationindex()

        rels = None

        if relation_type is not None:
            if not isinstance(relation_type, dict):
                type = [rt for rt in self.frame_relation_types() if rt.name==type][0]
                assert isinstance(type,dict)

        # lookup by 'frame'
        if frame is not None:
            if isinstance(frame,dict) and 'frameRelations' in frame:
                rels = PrettyList(frame.frameRelations)
            else:
                if not isinstance(frame, int):
                    if isinstance(frame, dict):
                        frame = frame.ID
                    else:
                        frame = self.frame_by_name(frame).ID
                rels = [self._frel_idx[frelID] for frelID in self._frel_f_idx[frame]]

            # filter by 'type'
            if type is not None:
                rels = [rel for rel in rels if rel.type is type]
        elif type is not None:
            # lookup by 'type'
            rels = type.frameRelations
        else:
            rels = self._frel_idx.values()

        # filter by 'frame2'
        if frame2 is not None:
            if frame is None:
                raise FramenetError("frame_relations(frame=None, frame2=<value>) is not allowed")
            if not isinstance(frame2, int):
                if isinstance(frame2, dict):
                    frame2 = frame2.ID
                else:
                    frame2 = self.frame_by_name(frame2).ID
            if frame==frame2:
                raise FramenetError("The two frame arguments to frame_relations() must be different frames")
            rels = [rel for rel in rels if rel.superFrame.ID==frame2 or rel.subFrame.ID==frame2]

        return PrettyList(sorted(rels,
                key=lambda frel: (frel.type.ID, frel.superFrameName, frel.subFrameName)))

    def fe_relations(self):
        """
        Obtain a list of frame element relations.

        >>> from nltk.corpus import framenet as fn
        >>> ferels = fn.fe_relations()
        >>> isinstance(ferels, list)
        True
        >>> len(ferels)
        10020
        >>> PrettyDict(ferels[0], breakLines=True)
        {'ID': 14642,
        '_type': 'ferelation',
        'frameRelation': <Parent=Abounding_with -- Inheritance -> Child=Lively_place>,
        'subFE': <fe ID=11370 name=Degree>,
        'subFEName': 'Degree',
        'subFrame': <frame ID=1904 name=Lively_place>,
        'subID': 11370,
        'supID': 2271,
        'superFE': <fe ID=2271 name=Degree>,
        'superFEName': 'Degree',
        'superFrame': <frame ID=262 name=Abounding_with>,
        'type': <framerelationtype ID=1 name=Inheritance>}

        :return: A list of all of the frame element relations in framenet
        :rtype: list(dict)
        """
        if not self._ferel_idx:
            self._buildrelationindex()
        return PrettyList(sorted(self._ferel_idx.values(),
                key=lambda ferel: (ferel.type.ID, ferel.frameRelation.superFrameName,
                    ferel.superFEName, ferel.frameRelation.subFrameName, ferel.subFEName)))

    def semtypes(self):
        """
        Obtain a list of semantic types.

        >>> from nltk.corpus import framenet as fn
        >>> stypes = fn.semtypes()
        >>> len(stypes)
        73
        >>> sorted(stypes[0].keys())
        ['ID', '_type', 'abbrev', 'definition', 'name', 'rootType', 'subTypes', 'superType']

        :return: A list of all of the semantic types in framenet
        :rtype: list(dict)
        """
        if not self._semtypes:
            self._loadsemtypes()
        return PrettyList(self._semtypes[i] for i in self._semtypes if isinstance(i, int))

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

        d = type(d)(d)

        try:
            attr_dict = elt.attrib
        except AttributeError:
            return d

        if attr_dict is None:
            return d

        # Ignore these attributes when loading attributes from an xml node
        ignore_attrs = ['cBy', 'cDate', 'mDate', 'xsi',
                        'schemaLocation', 'xmlns', 'bgColor', 'fgColor']

        for attr in attr_dict:

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
        frinfo['FEcoreSets'] = []
        frinfo['lexUnit'] = PrettyDict()
        frinfo['semTypes'] = []
        for k in ignorekeys:
            if k in frinfo:
                del frinfo[k]

        for sub in elt:
            if sub.tag.endswith('definition') and 'definition' not in ignorekeys:
                frinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('FE') and 'FE' not in ignorekeys:
                feinfo = self._handle_fe_elt(sub)
                frinfo['FE'][feinfo.name] = feinfo
                feinfo['frame'] = frinfo    # backpointer
            elif sub.tag.endswith('FEcoreSet') and 'FEcoreSet' not in ignorekeys:
                coreset = self._handle_fecoreset_elt(sub)
                # assumes all FEs have been loaded before coresets
                frinfo['FEcoreSets'].append(PrettyList(frinfo['FE'][fe.name] for fe in coreset))
            elif sub.tag.endswith('lexUnit') and 'lexUnit' not in ignorekeys:
                luentry = self._handle_framelexunit_elt(sub)
                if luentry['status'] in self._bad_statuses:
                    # problematic LU entry; ignore it
                    continue
                luentry['frame'] = frinfo
                luentry['subCorpus'] = Future((lambda lu: lambda: self._lu_file(lu))(luentry))
                frinfo['lexUnit'][luentry.name] = luentry
                if not self._lu_idx:
                    self._buildluindex()
                self._lu_idx[luentry.ID] = luentry
            elif sub.tag.endswith('semType') and 'semTypes' not in ignorekeys:
                semtypeinfo = self._load_xml_attributes(AttrDict(), sub)
                frinfo['semTypes'].append(self.semtype(semtypeinfo.ID))

        frinfo['frameRelations'] = self.frame_relations(frame=frinfo)

        # resolve 'requires' and 'excludes' links between FEs of this frame
        for fe in frinfo.FE.values():
            if fe.requiresFE:
                name, ID = fe.requiresFE.name, fe.requiresFE.ID
                fe.requiresFE = frinfo.FE[name]
                assert fe.requiresFE.ID==ID
            if fe.excludesFE:
                name, ID = fe.excludesFE.name, fe.excludesFE.ID
                fe.excludesFE = frinfo.FE[name]
                assert fe.excludesFE.ID==ID

        return frinfo

    def _handle_fecoreset_elt(self, elt):
        """Load fe coreset info from xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        tmp = []
        for sub in elt:
            tmp.append(self._load_xml_attributes(AttrDict(), sub))

        return tmp

    def _handle_framerelationtype_elt(self, elt, *args):
        """Load frame-relation element and its child fe-relation elements from frRelation.xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info['_type'] = 'framerelationtype'
        info['frameRelations'] = PrettyList()

        for sub in elt:
            if sub.tag.endswith('frameRelation'):
                frel = self._handle_framerelation_elt(sub)
                frel['type'] = info   # backpointer
                for ferel in frel.feRelations:
                    ferel['type'] = info
                info['frameRelations'].append(frel)

        return info

    def _handle_framerelation_elt(self, elt):
        """Load frame-relation element and its child fe-relation elements from frRelation.xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        assert info['superFrameName']!=info['subFrameName'],(elt,info)
        info['_type'] = 'framerelation'
        info['feRelations'] = PrettyList()

        for sub in elt:
            if sub.tag.endswith('FERelation'):
                ferel = self._handle_elt(sub)
                ferel['_type'] = 'ferelation'
                ferel['frameRelation'] = info   # backpointer
                info['feRelations'].append(ferel)

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
        luinfo['_type'] = 'lu'
        luinfo = self._load_xml_attributes(luinfo, elt)
        luinfo["definition"] = ""
        luinfo["sentenceCount"] = PrettyDict()
        luinfo['lexemes'] = PrettyList()   # multiword LUs have multiple lexemes
        luinfo['semTypes'] = PrettyList()  # an LU can have multiple semtypes

        for sub in elt:
            if sub.tag.endswith('definition'):
                luinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('sentenceCount'):
                luinfo['sentenceCount'] = self._load_xml_attributes(
                    PrettyDict(), sub)
            elif sub.tag.endswith('lexeme'):
                luinfo['lexemes'].append(self._load_xml_attributes(PrettyDict(), sub))
            elif sub.tag.endswith('semType'):
                semtypeinfo = self._load_xml_attributes(PrettyDict(), sub)
                luinfo['semTypes'].append(self.semtype(semtypeinfo.ID))

        return luinfo

    def _handle_lexunit_elt(self, elt, ignorekeys):
        """
        Load full info for a lexical unit from its xml file.
        This should only be called when accessing corpus annotations
        (which are not included in frame files).
        """
        luinfo = self._load_xml_attributes(AttrDict(), elt)
        luinfo['_type'] = 'lu'
        luinfo['definition'] = ""
        luinfo['subCorpus'] = PrettyList()
        luinfo['lexemes'] = PrettyList()   # multiword LUs have multiple lexemes
        luinfo['semTypes'] = PrettyList()  # an LU can have multiple semtypes
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
                luinfo['lexemes'].append(self._load_xml_attributes(PrettyDict(), sub))
            elif sub.tag.endswith('semType') and 'semType' not in ignorekeys:
                semtypeinfo = self._load_xml_attributes(AttrDict(), sub)
                luinfo['semTypes'].append(self.semtype(semtypeinfo.ID))

        return luinfo

    def _handle_lusubcorpus_elt(self, elt):
        """Load a subcorpus of a lexical unit from the given xml."""
        sc = AttrDict()
        try:
            sc['name'] = str(elt.get('name'))
        except AttributeError:
            return None
        sc['_type'] = "lusubcorpus"
        sc['sentence'] = []

        for sub in elt:
            if sub.tag.endswith('sentence'):
                s = self._handle_lusentence_elt(sub)
                if s is not None:
                    sc['sentence'].append(s)

        return sc

    def _handle_lusentence_elt(self, elt):
        """Load a sentence from a subcorpus of an LU from xml."""
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
                stinfo = self._load_xml_attributes(AttrDict(), sub)
                feinfo['semType'] = self.semtype(stinfo.ID)
            elif sub.tag.endswith('requiresFE'):
                feinfo['requiresFE'] = self._load_xml_attributes(AttrDict(), sub)
            elif sub.tag.endswith('excludesFE'):
                feinfo['excludesFE'] = self._load_xml_attributes(AttrDict(), sub)

        return feinfo

    def _handle_semtype_elt(self, elt, tagspec=None):
        semt = self._load_xml_attributes(AttrDict(), elt)
        semt['_type'] = 'semtype'
        semt['superType'] = None
        semt['subTypes'] = PrettyList()
        for sub in elt:
            if sub.text is not None:
                semt['definition'] = self._strip_tags(sub.text)
            else:
                supertypeinfo = self._load_xml_attributes(AttrDict(), sub)
                semt['superType'] = supertypeinfo
                # the supertype may not have been loaded yet

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
        len(m_frame.frameRelations))
    for fr in m_frame.frameRelations:
        print('   ', fr)

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
    ailment_lus = [x for x in m_frame.lexUnit.values() if 'incorporatedFE' in x and x.incorporatedFE == 'Ailment']
    print('   ', [x.name for x in ailment_lus])

    #
    # get all of the Lexical Units for the frame
    #
    print('\nNumber of Lexical Units in the "{0}" frame:'.format(m_frame.name),
          len(m_frame.lexUnit))
    print('  ', [x.name for x in m_frame.lexUnit.values()][:5], '...')

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
