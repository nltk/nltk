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
from nltk.internals import ElementWrapper
from nltk.corpus.reader import XMLCorpusReader, XMLCorpusView


class FramenetError(Exception):

    '''An exception class for framenet-related errors.'''


class AttrDict(dict):

    '''A class that wraps a dict and allows accessing the keys of the
    dict as if they were attributes. Taken from here:
       http://stackoverflow.com/a/14620633/8879

    >>> foo = {'a':1, 'b':2, 'c':3}
    >>> bar = AttrDict(foo)
    >>> bar
    {'a': 1, 'c': 3, 'b': 2}
    >>> bar.b
    2
    >>> bar.d = 4
    >>> bar
    {'a': 1, 'c': 3, 'b': 2, 'd': 4}
    >>>
    '''

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class FramenetCorpusReader(XMLCorpusReader):

    """
    A corpus reader for the Framenet Corpus.
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
        self._lu_idx = None
        self._fulltext_idx = None
        self._semTypes = None

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
        '''
        Returns the annotated document whose id number is
        ``fn_docid``. This id number can be obtained by calling the
        Documents() function.

        :param fn_docid: The Framenet id number of the document
        :type fn_docid: int

        :return: Information about the annotated document
        :rtype: dict

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

        '''
        try:
            xmlfname = self._fulltext_idx[fn_docid].filename
        except TypeError:  # happens when self._fulltext_idx == None
            # build the index
            self._buildcorpusindex()
            xmlfname = self._fulltext_idx[fn_docid].filename
        except:  # probably means that fn_docid was not in the index
            raise FramenetError("Unknown document id: {0}".format(fn_docid))

        # construct the path name for the xml file containing the document info
        locpath = os.path.join(
            "{0}".format(self._root), self._fulltext_dir, xmlfname)

        # Grab the top-level xml element containing the fulltext annotation
        elt = XMLCorpusView(locpath, 'fullTextAnnotation')[0]
        return AttrDict(self._handle_fulltextannotation_elt(elt))

    def frame(self, fn_fid, ignorekeys=[]):
        '''
        Get the details for the specified Frame using the frame's id
        number. This function reads the Frame information from the xml
        file on disk each time it is called. So, you may want to cache
        this info if you plan to call this function with the same id
        number multiple times.

        :param fn_fid: The Framenet id number of the frame
        :type fn_fid: int

        :param ignorekeys: The keys to ignore. These keys will not be
                           included in the output. (optional) 
        :type ignorekeys: list of key names

        :return: Information about a frame
        :rtype: dict

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame(256)
        >>> f.ID
        256
        >>> f.name
        'Medical_specialties'
        >>> f.definition # doctest:+ELLIPSIS
        u"This frame includes words that name ..."
        >>> len(f.lexUnit)
        29
        >>> [x.name for x in f.FE]
        ['Specialty', 'Type', 'Body_system', 'Affliction']
        >>> f.frameRelation
        [{u'relatedFrame': ['Medical_interaction_scenario'], 'type': 'Uses'}]

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
        
        '''
        # get the name of the frame with this id number
        try:
            name = self._frame_idx[fn_fid]['name']
        except TypeError:
            self._buildframeindex()
            name = self._frame_idx[fn_fid]['name']
        except:
            raise FramenetError('Unknown frame id: {0}'.format(fn_fid))

        # construct the path name for the xml file containing the Frame info
        locpath = os.path.join(
            "{0}".format(self._root), self._frame_dir, name + ".xml")

        # Grab the xml for the frame from the file
        elt = XMLCorpusView(locpath, 'frame')[0]
        return AttrDict(self._handle_frame_elt(elt, ignorekeys))

    def frames_by_lemma(self, pat):
        '''
        Returns a list of all frames that contain LUs in which the
        ``name`` attribute of the LU matchs the given regular expression
        ``pat``. Note that LU names are composed of "lemma.POS", where
        the "lemma" part can be made up of either a single lexeme
        (e.g. 'run') or multiple lexemes (e.g. 'a little').

        Note: if you are going to be doing a lot of this type of
        searching, you'd want to build an index that maps from lemmas to
        frames because each time frames_by_lemma() is called, it has to
        search through ALL of the frame XML files in the db.

        :return: A list of tuples where each tuple has the frame name and ID.
        :rtype: list(tuple)

        >>> from nltk.corpus import framenet as fn
        >>> fn.frames_by_lemma(r'(?i)a little')
        [('Quantified_mass', 189), ('Degree', 2001)]

        '''
        if self._frame_idx is None:
            self._buildframeindex()

        outlist = []
        for fid in list(self._frame_idx.keys()):
            f = self.frame(fid)
            if any([re.search(pat, lu.name) for lu in f.lexUnit]):
                outlist.append((f.name, f.ID))

        return outlist

    def lu_basic(self, fn_luid):
        '''
        Returns basic information about the LU whose id is
        ``fn_luid``. This is basically just a wrapper around the
        ``lu()`` function with "subCorpus" info excluded.

        :param fn_luid: The id number of the desired LU
        :type fn_luid: int

        :return: Basic information about the lexical unit
        :rtype: dict

        >>> from nltk.corpus import framenet as fn
        >>> fn.lu_basic(256)
        {'status': 'FN1_Sent', u'definition': u'COD: be aware of beforehand; predict.', 'name': 'foresee.v', 'frame': 'Expectation', 'POS': 'V', 'frameID': 26, u'lexeme': {'POS': 'V', 'name': 'foresee'}, u'semType': {}, 'totalAnnotated': 44, 'ID': 256}
        '''
        return self.lu(fn_luid, ignorekeys=['subCorpus'])

    def lu(self, fn_luid, ignorekeys=[]):
        '''
        Get information about a specific Lexical Unit using the id number
        ``fn_luid``. This function reads the LU information from the xml
        file on disk each time it is called. You may want to cache this
        info if you plan to call this function with the same id number
        multiple times.

        :param fn_luid: The id number of the lexical unit
        :type fn_luid: int

        :param ignorekeys: The keys to ignore. These keys will not be
                           included in the output. (optional) 
        :type ignorekeys: A list of key names.

        :return: All information about the lexical unit
        :rtype: dict

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> fn.lu(256).name
        'foresee.v'
        >>> fn.lu(256).definition
        u'COD: be aware of beforehand; predict.'
        >>> fn.lu(256).frame
        'Expectation'
        >>> fn.lu(256).lexeme
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

        '''

        fname = "lu{0}.xml".format(fn_luid)
        locpath = os.path.join("{0}".format(self._root), self._lu_dir, fname)

        try:
            elt = XMLCorpusView(locpath, 'lexUnit')[0]
        except:
            raise FramenetError('Unknown LU id: {0}'.format(fn_luid))

        return AttrDict(self._handle_lexunit_elt(elt, ignorekeys))

    def _loadSemTypes(self):
        '''Create the semantic types index.'''
        self._semTypes = AttrDict()
        for st in self.semTypes():
            n = st['name']
            a = st['abbrev']
            i = st['ID']
            # Both name and abbrev should be able to retrieve the
            # ID. The ID will retrieve the semantic type dict itself.
            self._semTypes[n] = i
            self._semTypes[a] = i
            self._semTypes[i] = st

    def semtype(self, name=None, abbrev=None, id=None):
        '''
        :param name: The name of the semantic type
        :type name: string or None

        :param abbrev: The abbreviation of the semantic type
        :type abbrev: string or None

        :param id: The id number of the semantic type
        :type id: int or None

        :return: Information about a semantic type
        :rtype: dict

        >>> from nltk.corpus import framenet as fn
        >>> fn.semtype(id=233).name
        'Temperature'
        >>> fn.semtype(id=233).abbrev
        'Temp'
        >>> fn.semtype(name='Temperature').ID
        233

        '''
        if sum([1 for x in [name, abbrev, id] if x is not None]) != 1:
            raise FramenetError(
                "semtype(): Must specify one (and only one) arg")

        if id is None:
            key = name
            if key is None:
                key = abbrev

            try:
                id = self._semTypes[key]
            except TypeError:
                self._loadSemTypes()
                id = self._semTypes[key]

        try:
            st = self._semTypes[id]
        except TypeError:
            self._loadSemTypes()
            st = self._semTypes[id]

        return st

    def Frames(self, name=None):
        """
        :param name: A regular expression pattern used to match against
                     Frame names. If 'name' is None, then a list of all
                     Framenet Frames will be returned.

        :return: A list of matching Frames (or all Frames)
        :rtype: list(dict) Each dict in the returned list will contain two keys:
                  - 'name': the name of the Frame
                  - 'ID'  : the id number of the Frame

        Details for a specific frame can be obtained using this class's
        frame() function.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.Frames())
        1019
        >>> fn.Frames(r'(?i)medical')
        [{'ID': 239, 'name': 'Medical_conditions'}, {'ID': 256, 'name': 'Medical_specialties'}, {'ID': 257, 'name': 'Medical_instruments'}, {'ID': 255, 'name': 'Medical_professionals'}]

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

        """
        try:
            flist = list(self._frame_idx.values())
        except:
            self._buildframeindex()
            flist = list(self._frame_idx.values())

        if name is None:
            return flist
        else:
            return [x for x in flist if re.search(name, x['name']) is not None]

    def lexicalUnits(self, name=None):
        """
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

        :return: A list of selected (or all) lexical units
        :rtype: list of dicts, where each dict object contains the following
                keys:

                'name'
                'ID'
                'hasAnnotation'
                'frameID'
                'frameName'
                'status'

        Details for a specific lexical unit can be obtained using this
        class's lu() function.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.lexicalUnits())
        11829
        >>> fn.lexicalUnits(r'(?i)a little')
        [{'status': 'Created', 'hasAnnotation': 'false', 'name': 'a little.n', 'frameID': 189, 'frameName': 'Quantity', 'ID': 14733}, {'status': 'Created', 'hasAnnotation': 'false', 'name': 'a little.adv', 'frameID': 2001, 'frameName': 'Degree', 'ID': 14743}, {'status': 'Created', 'hasAnnotation': 'false', 'name': 'a little bit.adv', 'frameID': 2001, 'frameName': 'Degree', 'ID': 14744}]

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
        """

        try:
            lulist = list(self._lu_idx.values())
        except:
            self._buildluindex()
            lulist = list(self._lu_idx.values())

        if name is None:
            return lulist
        else:
            return [x for x in lulist if re.search(name, x['name']) is not None]

    def Documents(self, name=None):
        '''
        Returns a list of the annotated documents in Framenet.

        :param name: A regular expression pattern used to search the
                     file name of each annotated document. The document's
                     file name contains the name of the corpus that the
                     document is from, followed by two underscores "__"
                     followed by the document name. So, for example, the
                     file name "LUCorpus-v0.3__20000410_nyt-NEW.xml" is
                     from the corpus named "LUCorpus-v0.3" and the
                     document name is "20000410_nyt-NEW.xml".

        :return: A list of selected (or all) annotated documents
        :rtype: list of dicts, where each dict object contains the following
                keys:
                  'name'
                  'ID'
                  'corpid'
                  'corpname'
                  'description'
                  'filename'

        Details for a specific annotated document can be obtained using this
        class's annotated_document() function and pass it the value of the 'ID' field.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.Documents())
        78
        >>> set([x.corpname for x in fn.Documents()])
        set(['NTI', 'LUCorpus-v0.3', 'ANC', 'Miscellaneous', 'PropBank', 'KBEval', 'QA', 'SemAnno', 'C-4'])

        '''
        try:
            ftlist = list(self._fulltext_idx.values())
        except:
            self._buildcorpusindex()
            ftlist = list(self._fulltext_idx.values())

        if name is None:
            return ftlist
        else:
            return [x for x in ftlist if re.search(name, x['filename']) is not None]

    def frameRelationTypes(self):
        """
        :return: A list of all of the frame relation types in framenet
        :rtype: list(dict)
        """
        return [x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                         'frameRelations/frameRelationType',
                                         self._handle_elt)]

    def frameRelations(self):
        """
        :return: A list of all of the frame relations in framenet
        :rtype: list(dict)
        """
        return [x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                         'frameRelations/frameRelationType/frameRelation',
                                         self._handle_elt)]

    def FERelations(self):
        """
        :return: A list of all of the frame element relations in framenet
        :rtype: list(dict)
        """
        return [x for x in XMLCorpusView(self.abspath("frRelation.xml"),
                                         'frameRelations/frameRelationType/frameRelation/FERelation',
                                         self._handle_elt)]

    def semTypes(self):
        """
        :return: A list of all of the semantic types  in framenet
        :rtype: list(dict)
        """
        return [x for x in XMLCorpusView(self.abspath("semTypes.xml"),
                                         'semTypes/semType',
                                         self._handle_semtype_elt)]

    def _loadXMLAttributes(self, d, elt):
        """
        Extracts a subset of the attributes from the given element and
        returns them in a dictionary.

        :param d: A dictionary in which to store the attributes.
        :param elt: An ElementTree Element
        :return: Returns the input dict ``d`` possibly including attributes from ``elt``
        :rtype: dict
        """

        d = AttrDict(d)

        try:
            attr_dict = elt.attrib
        except:
            return d

        if attr_dict is None:
            return d

        # Ignore these attributes when loading attributes from an xml node
        ignore_attrs = ['cBy', 'cDate', 'mDate', 'xsi',
                        'schemaLocation', 'xmlns', 'bgColor', 'fgColor']

        for attr in list(attr_dict.keys()):

            if any([attr.endswith(x) for x in ignore_attrs]):
                continue

            val = attr_dict[attr]
            if val.isdigit():
                d[attr] = int(val)
            else:
                d[attr] = val

        return d

    def _strip_tags(self, data):
        """
        :return: A cleaned-up version of the input string
        :rtype: str

        Gets rid of all tags and newline characters from the given input
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
        except:
            pass

        return data

    def _handle_elt(self, elt, tagspec=None):
        '''Extracts and returns the attributes of the given element'''
        return self._loadXMLAttributes(AttrDict(), elt)

    def _handle_fulltextindex_elt(self, elt, tagspec=None):
        '''Extracts corpus/document info from the fulltextIndex.xml
        file. Note that this function "flattens" the information
        contained in each of the "corpus" elements, so that each
        "document" element will contain attributes for the corpus and
        corpusid. Also, each of the "document" items will contain a new
        attribute called "filename" that is the base file name of the
        xml file for the document in the "fulltext" subdir of the
        Framenet corpus.
        '''
        ftinfo = self._loadXMLAttributes(AttrDict(), elt)
        corpname = ftinfo.name
        corpid = ftinfo.ID
        retlist = []
        for sub in elt:
            if sub.tag.endswith('document'):
                doc = self._loadXMLAttributes(AttrDict(), sub)
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
        '''Load the info for a Frame from an frame xml file'''
        frinfo = self._loadXMLAttributes(AttrDict(), elt)

        frinfo['definition'] = ""
        frinfo['FE'] = []
        frinfo['FEcoreSet'] = []
        frinfo['frameRelation'] = []
        frinfo['lexUnit'] = []
        frinfo['semType'] = []
        list(
            map(frinfo.pop, [k for k in list(frinfo.keys()) if k in ignorekeys]))

        for sub in elt:
            if sub.tag.endswith('definition') and 'definition' not in ignorekeys:
                frinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('FE') and 'FE' not in ignorekeys:
                frinfo['FE'].append(self._handle_fe_elt(sub))
            elif sub.tag.endswith('FEcoreSet') and 'FEcoreSet' not in ignorekeys:
                frinfo['FEcoreSet'].extend(self._handle_fecoreset_elt(sub))
            elif sub.tag.endswith('frameRelation') and 'frameRelation' not in ignorekeys:
                fr = self._handle_framerelation_elt(sub)
                if fr is not None:
                    frinfo['frameRelation'].append(fr)
            elif sub.tag.endswith('lexUnit') and 'lexUnit' not in ignorekeys:
                frinfo['lexUnit'].append(self._handle_framelexunit_elt(sub))
            elif sub.tag.endswith('semType') and 'semType' not in ignorekeys:
                frinfo['semType'].append(
                    self._loadXMLAttributes(AttrDict(), sub))

        return frinfo

    def _handle_fecoreset_elt(self, elt):
        '''Load fe coreset info from xml.'''
        info = self._loadXMLAttributes(AttrDict(), elt)
        tmp = []
        for sub in elt:
            tmp.append(self._loadXMLAttributes(AttrDict(), sub))

        return tmp

    def _handle_framerelation_elt(self, elt):
        '''Load frame relation info from an xml element in a frame.'''
        if len(elt) == 0:
            return None
        info = self._loadXMLAttributes(AttrDict(), elt)
        info['relatedFrame'] = []
        for sub in elt:
            if sub.tag.endswith('relatedFrame'):
                info['relatedFrame'].append(sub.text)

        return info

    def _handle_fulltextannotation_elt(self, elt):
        '''Load full annotation info for a document from its xml
        file. The main element (fullTextAnnotation) contains a "header"
        element (which we ignore here) and a bunch of "sentence"
        elements.'''
        info = AttrDict()
        info['sentence'] = []

        for sub in elt:
            if sub.tag.endswith('header'):
                continue  # not used
            elif sub.tag.endswith('sentence'):
                s = self._handle_fulltext_sentence_elt(sub)
                info['sentence'].append(s)

        return info

    def _handle_fulltext_sentence_elt(self, elt):
        '''Load information from the given "sentence" element. Each
        "sentence" element contains a "text" and an "annotationSet" sub
        element.'''
        info = self._loadXMLAttributes(AttrDict(), elt)
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
        '''Load information from the given "annotationSet" element. Each
        "annotationSet" contains several "layer" elements.'''
        info = self._loadXMLAttributes(AttrDict(), elt)
        info['layer'] = []

        for sub in elt:
            if sub.tag.endswith('layer'):
                l = self._handle_fulltextlayer_elt(sub)
                info['layer'].append(l)

        return info

    def _handle_fulltextlayer_elt(self, elt):
        '''Load information from the given "layer" element. Each
        "layer" contains several "label" elements.'''
        info = self._loadXMLAttributes(AttrDict(), elt)
        info['label'] = []

        for sub in elt:
            if sub.tag.endswith('label'):
                l = self._loadXMLAttributes(AttrDict(), sub)
                info['label'].append(l)

        return info

    def _handle_framelexunit_elt(self, elt):
        '''Load the lexical unit info from an xml element in a frame's xml file.'''
        luinfo = AttrDict()
        luinfo['incorporatedFE'] = ""
        luinfo = self._loadXMLAttributes(luinfo, elt)
        luinfo["definition"] = ""
        luinfo["sentenceCount"] = AttrDict()
        luinfo["lexeme"] = []

        for sub in elt:
            if sub.tag.endswith('definition'):
                luinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('sentenceCount'):
                luinfo['sentenceCount'] = self._loadXMLAttributes(
                    AttrDict(), sub)
            elif sub.tag.endswith('lexeme'):
                luinfo['lexeme'].append(
                    self._loadXMLAttributes(AttrDict(), sub))

        return luinfo

    def _handle_lexunit_elt(self, elt, ignorekeys):
        '''Load full info for a lexical unit from its xml file.'''
        luinfo = self._loadXMLAttributes(AttrDict(), elt)
        luinfo['definition'] = ""
        luinfo['subCorpus'] = []
        luinfo['lexeme'] = AttrDict()
        luinfo['semType'] = AttrDict()
        list(
            map(luinfo.pop, [k for k in list(luinfo.keys()) if k in ignorekeys]))

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
                luinfo['lexeme'] = self._loadXMLAttributes(AttrDict(), sub)
            elif sub.tag.endswith('semType') and 'semType' not in ignorekeys:
                luinfo['semType'] = self._loadXMLAttributes(AttrDict(), sub)

        return luinfo

    def _handle_lusubcorpus_elt(self, elt):
        '''Load a subcorpus of a lexical unit from the given xml.'''
        sc = AttrDict()
        try:
            sc['name'] = str(elt.get('name'))
        except:
            return None
        sc['sentence'] = []

        for sub in elt:
            if sub.tag.endswith('sentence'):
                s = self._handle_lusentence_elt(sub)
                if s is not None:
                    sc['sentence'].append(s)

        return sc

    def _handle_lusentence_elt(self, elt):
        '''Load a sentence from a subcorpus of an lu from xml.'''
        info = self._loadXMLAttributes(AttrDict(), elt)
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
        '''Load an annotation set from a sentence in an subcorpus of an LU'''
        info = self._loadXMLAttributes(AttrDict(), elt)
        info['layer'] = []
        for sub in elt:
            if sub.tag.endswith('layer'):
                l = self._handle_lulayer_elt(sub)
                if l is not None:
                    info['layer'].append(l)
        return info

    def _handle_lulayer_elt(self, elt):
        '''Load a layer from an annotation set'''
        layer = self._loadXMLAttributes(AttrDict(), elt)
        layer['label'] = []

        for sub in elt:
            if sub.tag.endswith('label'):
                l = self._loadXMLAttributes(AttrDict(), sub)
                if l is not None:
                    layer['label'].append(l)
        return layer

    def _handle_fe_elt(self, elt):
        feinfo = self._loadXMLAttributes(AttrDict(), elt)
        feinfo['definition'] = ""
        feinfo['semType'] = AttrDict()
        feinfo['requiresFE'] = AttrDict()
        feinfo['excludesFE'] = AttrDict()
        for sub in elt:
            if sub.tag.endswith('definition'):
                feinfo['definition'] = self._strip_tags(sub.text)
            elif sub.tag.endswith('semType'):
                feinfo['semType'] = self._loadXMLAttributes(AttrDict(), sub)
            elif sub.tag.endswith('requiresFE'):
                feinfo['requiresFE'] = self._loadXMLAttributes(AttrDict(), sub)
            elif sub.tag.endswith('excludesFE'):
                feinfo['excludesFE'] = self._loadXMLAttributes(AttrDict(), sub)

        return feinfo

    def _handle_semtype_elt(self, elt, tagspec=None):
        semt = self._loadXMLAttributes(AttrDict(), elt)
        for sub in elt:
            if sub.text is not None:
                semt['definition'] = self._strip_tags(sub.text)
            else:
                semt['superType'] = self._loadXMLAttributes(AttrDict(), sub)

        return semt


#
# Demo
#
def demo():
    from pprint import pprint
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
    print('Number of Frames:', len(fn.Frames()))
    print('Number of Lexical Units:', len(fn.lexicalUnits()))
    print('Number of annotated documents:', len(fn.Documents()))
    print()

    #
    # Frames
    #
    print('getting frames whose name matches the (case insensitive) regex: "(?i)medical"')
    medframes = fn.Frames(r'(?i)medical')
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
    print('   ', [x.name for x in m_frame.FE])

    #
    # get the names of the "Core" Frame Elements
    #
    print(
        '\nThe "core" Frame Elements in the "{0}" frame:'.format(m_frame.name))
    print('   ', [x.name for x in m_frame.FE if x.coreType == "Core"])

    #
    # get all of the Lexical Units that are incorporated in the
    # 'Ailment' FE of the 'Medical_conditions' frame (id=239)
    #
    print('\nAll Lexical Units that are incorporated in the "Ailment" FE:')
    m_frame = fn.frame(239)
    ailment_lus = [x for x in m_frame.lexUnit if x.incorporatedFE == 'Ailment']
    print([x.name for x in ailment_lus])

    #
    # get all of the Lexical Units for the frame
    #
    print('\nNumber of Lexical Units in the "{0}" frame:'.format(m_frame.name),
          len(m_frame.lexUnit))
    print('  ', [x.name for x in m_frame.lexUnit[:5]], '...')

    #
    # get basic info on the second LU in the frame
    #
    tmp_id = m_frame.lexUnit[1].ID  # grab the id of the second LU
    luinfo = fn.lu_basic(tmp_id)  # get basic info on the LU
    print('\nInformation on the LU: {0}'.format(luinfo.name))
    pprint(luinfo)

    #
    # Get a list of all of the corpora used for fulltext annotation
    #
    print('\nNames of all of the corpora used for fulltext annotation:')
    allcorpora = set([x.corpname for x in fn.Documents()])
    pprint(list(allcorpora))

    #
    # Get the names of the annotated documents in the first corpus
    #
    firstcorp = list(allcorpora)[0]
    firstcorp_docs = fn.Documents(firstcorp)
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
