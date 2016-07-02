#coding=utf-8
# CHILDES XML Corpus Reader

# Copyright (C) 2001-2016 NLTK Project
# Author: Tomonori Nagano <tnagano@gc.cuny.edu>
#         Alexis Dimitriadis <A.Dimitriadis@uu.nl>
#         Nathan Schneider <nschneid@cs.cmu.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for the XML version of the CHILDES corpus.
"""
from __future__ import print_function

__docformat__ = 'epytext en'

import re, sys
from collections import defaultdict

from nltk.util import flatten, LazyMap, LazyConcatenation
from nltk.compat import string_types, python_2_unicode_compatible

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.xmldocs import XMLCorpusReader, ElementTree

def ch2upos(chpos):
    """
    Convert an English CHILDES part-of-speech tag to a Universal POS tag
    (refer to http://universaldependencies.org/en/pos/all.html). 
    Based on the English Brown corpus; not guaranteed to work for other datasets.
    """
    if len(chpos)>1 and chpos.startswith('0'):
        return ch2upos(chpos[1:])   # omitted word POS is prefixed with 0
    p1 = chpos.split(':')[0]
    if chpos in ('n', 'n:gerund', 'n:pt', 'n:adj'): return 'NOUN'    # n:pt appears to be for 
    # nouns that are morphologically always plural: pants, clothes, pliers, means, etc. 
    # n:adj is apparently for adjectives with plural endings (including, mistakenly, "overalls").
    if p1=='pro' or chpos=='rel': return 'PRON'
    if chpos=='n:prop': return 'PROPN'
    if chpos=='prep': return 'ADP'
    if chpos in (',', 'cm', '.', '?', '!', 'bq', 'eq', 'beg', 'end', '+...', '+/.', 
        '<interruption question>', '<quotation next line>'): return 'PUNCT'
        # cm = comma, bq = begin quote, eq = end quote
    if p1=='adv': return 'ADV'
    if chpos=='adj': return 'ADJ'
    if chpos in ('aux', 'mod', 'mod:aux'): return 'AUX'
    if chpos in ('art', 'det', 'det:wh', 'qn'): return 'DET'
    if chpos=='co': return 'INTJ' # communicator
    if chpos=='conj': return 'SCONJ'
    if chpos=='coord': return 'CONJ'
    if chpos in ('cop', 'part', 'v'): return 'VERB'
    if chpos=='det:num': return 'NUM'
    if chpos in ('inf', 'neg', 'poss'): return 'PART'
    if chpos=='n:let': return 'SYM' # letter of the alphabet
    if chpos=='post': return 'ADV' # else, too
    if chpos=='meta': return 'NOUN' # metalinguistic reference to a word
    if chpos in ('bab', 'L2', 'on', 'test', 'chi', 'fam', 'neo', 'wplay', 'uni', 'phon', 'none'): return 'X' 
    # babbling, foreign word, onomatopoeia, experimental nonce word, 
    # child-invented word, family-specific word, neologism, wordplay, UNIBET [phonemic alphabet]. 
    # "phon" is labeled "phonology consistent". not sure what "none" is
    raise ValueError("Unknown CHILDES POS: "+chpos)

class CHILDESError(Exception):
    pass

@python_2_unicode_compatible
class CHILDESWord(object):
    

    def __init__(self, wordform, mor=None, sepprefix=False, 
                 replacement=None, is_replacement=False, real=None):
        """
        @param wordform: String.
        
        @param mor: Morphological/grammatical analysis. 
        Will not be present on the original uttered word 
        if there is a replacement.
        
        @param sepprefix: True if this is a separated-prefix. 
        (Used in Hebrew for preclitics.)
        
        @param replacement: List of replacement CHILDESWord objects 
        indicating the transcriber's interpretation.
        
        @param is_replacement: True if the word is part of a replacement 
        (and therefore nested within a parent CHILDESWord).
        
        @param real: True if there is a <replacement> of a real word with an intended word
        (apparently this distinction is not made in practice for the corpora examined).
        """
        self.wordform = wordform
        if replacement is not None:
            assert not mor
        assert not (replacement is not None and is_replacement)
        assert not (replacement is None and real is not None)
        if replacement is not None:
            self.replacement = replacement
            self.real = real
            self.mor = None
            self.is_replacement = False
        else:
            self.replacement = []
            self.mor = mor
            self.is_replacement = is_replacement
            self.real = None
        self.is_sepprefix = sepprefix  # separated-prefix (used in Hebrew CHIDLES for preclitics)

    def interpreted_words(self):
        """
        A list containing the replacement word(s), if any, 
        and the present word otherwise.
        """
        return self.replacement or [self]
    
    def has_replacement(self):
        return bool(self.replacement)
    
    @property
    def nMorphs(self):
        if self.mor:
            return self.mor.nMorphs
        return sum(w.nMorphs for w in self.replacement or [])

    def split(self, clitics=True, compounds=False, affixes=False):
        if self.mor:
            return self.mor.split(clitics,compounds,affixes)
        if not self.has_replacement():
            raise CHILDESError('No morphology available for this word: '+unicode(self))
        return [m for w in self.replacement for m in w.split(clitics,compounds,affixes)]

    def get_stem_str(self):
        return self.mor.get_stem_str()

    def __str__(self):
        """Approximate .cha rendering of word layer (not morphology)"""
        s = self.wordform
        if self.has_replacement():
            # <replacement>
            s += ' [:: '  if self.real else ' [: '
            s += u' '.join(map(unicode, self.replacement))
            s += ']'
        return s
    
    def _display_str(self):
        """A proper unicode string"""
        return '<'+unicode(self)+' ({} morph components)>'.format(self.nMorphs)
    
    def __repr__(self):
        """Will be converted to str in Python 2, exposing escapes for non-ASCII characters"""
        return self._display_str()

@python_2_unicode_compatible
class CHILDESMorph(object):
    """Unit of morphological analysis; may have nested `CHILDESMorph` instances."""
    
    is_compound = False
    """True for <mwc>"""
    
    clitic_status = None
    """`'pre'` for preclitics, `'post'` for postclitics"""
    
    affix_status = None
    """`'prefix'` for <mpfx>, `'suffix'` for <mk>"""
    
    submorphs = []
    """Subunits"""
    
    pos = None
    """Part-of-speech tag"""
    
    gold_index = None
    """Index from <gra type="grt">"""
    
    gold_head = None
    """Head from <gra type="grt">"""
    
    gold_rel = None
    """Dependency relation type from <gra type="grt">"""
    
    auto_index = None
    """Index from <gra type="gra">"""
    
    auto_head = None
    """Head from <gra type="gra">"""
    
    auto_rel = None
    """Dependency relation type from <gra type="gra">"""
    
    @property
    def nMorphs(self):
        return 1 + sum(m.nMorphs for m in self.submorphs)
    
    @staticmethod
    def stringify_morphs(morphs, key=unicode, joiner=u''):
        result = []
        for m in morphs:
            s = key(m)
            if m.clitic_status=='pre':
                s += '~'
            elif m.clitic_status=='post':
                s = '~' + s
            result.append(s)
        return joiner.join(result)
    
    def __init__(self, form_or_submorphs, pos=None, 
            is_compound=False, clitic_status=None, affix_status=None, is_punct=False):
        
        self.is_compound = is_compound
        self.clitic_status = clitic_status
        self.affix_status = affix_status
        self.is_punct = is_punct
        if isinstance(form_or_submorphs, string_types):
            self._form = form_or_submorphs
            self.submorphs = []
        else:
            self._form = None
            self.submorphs = form_or_submorphs
        
        if pos is None:
            joiner = u'+' if self.is_compound else u''
            self.pos = CHILDESMorph.stringify_morphs(self.submorphs, 
                                                     key=lambda m: m.pos or '', 
                                                     joiner=joiner)
            self._dep_str = CHILDESMorph.stringify_morphs(self.submorphs, 
                                                     key=lambda m: m.get_dep_str() or '', 
                                                     joiner=joiner)
                                                      
        else:
            self.pos = pos
            self._dep_str = None
    
    def __iter__(self):
        return iter(self.submorphs)
    
    def __getitem__(self, index):
        return list(self)[index]
    
    def __str__(self):
        return self.get_str()
        
    def _display_str(self):
        """A proper unicode string"""
        return u'|'.join(map(unicode,
                            (self.pos or '', 
                             self,
                             self.get_stem_str() or '',
                             self.get_dep_str() or '')))
    
    def __repr__(self):
        """Will be converted to str in Python 2, exposing escapes for non-ASCII characters"""
        return self._display_str()
    
    def set_gra(self, gra_type, dep):
        i, head, rel = dep
        if gra_type=='grt':
            self.gold_index = i
            self.gold_head = head
            self.gold_rel = rel
        else:
            assert gra_type=='gra',gra_type
            self.auto_index = i
            self.auto_head = head
            self.auto_rel = rel
            
    def dep(self, gold_status=None):
        if (gold_status is True) or (gold_status is None and self.gold_index is not None):
            return (self.gold_index, self.gold_head, self.gold_rel)
        elif self.auto_index is not None:
            return (self.auto_index, self.auto_head, self.auto_rel)
        else:
            return None
    
    def get_dep_str(self, gold_status=None):
        if self._dep_str:
            return self._dep_str
        dep = self.dep(gold_status)
        if not dep:
            return dep
        return ','.join(map(unicode, dep))
    
    def get_stem_str(self):
        if self.affix_status:
            return ''
        submss = [m.get_stem_str() for m in self.submorphs]
        joiner = u'+' if self.is_compound else u''
        if self.clitic_status=='pre':
            return (self._form or joiner.join(submss)) + '~'
        if self.clitic_status=='post':
            return '~'+(self._form or joiner.join(submss))
        return self._form or joiner.join(submss)
    
    def get_str(self, include_suffixes=True):
        s = ''
        if self.submorphs:
            assert not self._form
            mm = self.submorphs
            if not include_suffixes:
                mm = filter(lambda m: m.affix_status!='suffix', mm)
            if self.is_compound:
                s = u'+'.join(map(unicode, mm))
            else:
                assert sum(1 for m in self.submorphs if not (m.clitic_status or m.affix_status))==1,self.submorphs
                s = u''.join(map(unicode, mm))
        else:
            s = self._form
        
        if self.clitic_status=='pre':
            return s + '~'
        elif self.clitic_status=='post':
            return '~' + s
        return s

    
    def split(self, clitics=True, compounds=False, affixes=False):
        """Return a list of morphemes based on the given split criteria.
        Note: splitting affixes will always cause clitics to be split.
        """
        queue = [self]
        result = []
        while queue:
            m = queue.pop(0)
            if not m:
                result.append(m)
            elif m.is_compound:
                if compounds:
                    queue = list(m) + queue
                else:
                    result.append(m)
            elif m._form is not None:
                # must be a stem (or punctuation)
                result.append(m)
            elif len(m.submorphs)==0:
                assert False,(m,)
            elif m[0].clitic_status or m[-1].clitic_status:
                if clitics:
                    queue = list(m) + queue
                else:
                    result.append(m)
            elif m[0].affix_status or m[-1].affix_status:
                if affixes:
                    queue = list(m) + queue
                else:
                    result.append(m)
            else:
                assert False,(m,)
        assert result,self.__dict__
        return result

class CHILDESCorpusReader(XMLCorpusReader):
    """
    Corpus reader for the XML version of the CHILDES corpus.
    The CHILDES corpus is available at ``http://childes.psy.cmu.edu/``. The XML
    version of CHILDES is located at ``http://childes.psy.cmu.edu/data-xml/``.
    Copy the needed parts of the CHILDES XML corpus into the NLTK data directory
    (``nltk_data/corpora/CHILDES/``).

    
    
    Main access methods
    ===================
    
    This reader provides the usual NLTK methods, including
    ``words()`` and ``sents()`` (just the utterances), as well as
    ``tagged_words()`` and ``tagged_sents()`` (including part-of-speech tags). 
    It also offers methods that are specialized to CHILDES data:
    
    * ``raw_words()`` and ``raw_sents()``: Some uttered tokens 
    (particularly by children) are nonstandard words, and have 
    are transcribed in both their original form and a normalized form. 
    These methods provide access to the original form of each word/sentence. 
    Note that morphological/grammatical information (if present) always refers to
    the normalized form.
    
    * ``morphs()`` and ``morph_sents()``: These provide morpheme-level analysis 
    for corpora where it is available, offering options for the level of 
    granularity at which morphemes are split (e.g., it is sometimes necessary 
    to split clitics but not affixes).
    
    All of the above methods have an ``as_obj`` parameter. 
    If this is set to True, then in place of string representations of the words/morphemes, 
    there will be an instance of ``CHILDESWord`` or ``CHILDESMorph``, 
    which provides structural information and metadata about the word/morpheme.
    
    * ``morph_deps()`` and ``conllu_parses()``: These provide access to grammatical 
    relations, i.e., syntactic dependencies, which are noted for some morphologically-analyzed 
    corpora. A subset of corpora provide both manual and automatically parsed syntactic 
    annotations: the ``gold_status`` parameter will determine whether the manual 
    (gold standard) one is returned. ``conllu_parses()`` produces, for each sentence, 
    a string according to the CoNLL-U standard: http://universaldependencies.org/format.html
    
    Summary of main method names and parameters
    ===========================================
    
    (tagged_|raw_)sents
    (tagged_|raw_)words
    (tagged_)morph_sents
    (tagged_)morphs
    morph_deps
    conllu_parses()
    
    - fileids, speakers: all methods
    - punct, strip_space: all methods except conllu_parses()
    - include_speaker: all sentence-level methods (*sents, morph_deps, conllu_parses)
    - split_*, skip_uananlyzed: all *morph* methods
    - skip_uanalyzed_tokens: conllu_parses()
    - stem: non-raw_* methods, excluding conllu_parses()
    - as_obj: all but morph_deps() and conllu_parses()
    - gold_status, include_suffixes: morph_deps() and conllu_parses()
    
    Code dependencies
    =================
    
    raw_sents(as_obj=True) <-- raw_words()
    ^-- sents(as_obj=True) <-- words()
        ^-- morph_sents(as_obj=True) <-- morphs()
            ^-- tagged_morph_sents() <-- tagged_morphs()
                ^-- morph_deps()
        ^-- tagged_sents() <-- tagged_words()
        ^-- conllu_parses() [doesn't depend on morph_deps() because of multiwords]
    """
    def __init__(self, root, fileids, lazy=True):
        XMLCorpusReader.__init__(self, root, fileids)
        self._lazy = lazy

    def _raw_sents_in_file(self, fileid, speakers='ALL', include_speaker=False, punct=True,
            as_obj=False, strip_space=True):
        
        xmldoc = self._clean_doc(fileid)
        participants = None
        
        # Filter to relevant speakers
        
        if speakers in ('is_child','is_adult') or callable(speakers):
            # we need participant info
            participants = self._get_participants_dict(xmldoc)
            if speakers=='is_child':
                speakers = self.is_child
            elif speakers=='is_adult':
                speakers = self.is_adult
            speakers = [p['id'] for p in participants.values() if speakers(p)]
        elif isinstance(speakers, string_types) and speakers != 'ALL':  # ensure we have a list of speakers
            speakers = [speakers]
        
        
        results = []
        
        # Iterate over utterances from relevant speakers
        for who,xmlsent in self._utterance_nodes(xmldoc, speakers):
            sent = []
            
            for xmlword in self._word_nodes(xmlsent, punct):
                # Construct object for the XML uttered word 
                # (it will hold replacement word(s) if applicable)
                
                assert xmlword is not None,(xmlsent.attrib,fileid)
                wordform = self._wordform(xmlword, strip_space)
                
                xmlrepl = xmlword.find('.//replacement')
                if xmlrepl is not None: # has replacement
                    real = xmlrepl.get('real')
                    xmlww = xmlrepl.findall('.//w')
                    # if there is a <replacement>, then any <mor> tiers are within it
                    
                    ww = []
                    for xmlw in xmlww:
                        wform = self._wordform(xmlw, strip_space)
                        
                        if xmlw.find(".//mor[@type='mor']") is None:
                            morphs = ()
                        else:
                            morphs = self._morphs(xmlw, wform=wform)
                            assert morphs
                        
                        w = CHILDESWord(wform, morphs, is_replacement=True, real=real,
                                        sepprefix=(xmlw.get('separated-prefix')=='true'))
                        ww.append(w)
                
                    word = CHILDESWord(wordform, replacement=ww, # nest replacement words within original word
                                       sepprefix=(xmlword.get('separated-prefix')=='true'))    
                else:   # no replacement
                    real = None
                    if xmlword.find(".//mor[@type='mor']") is None:
                        morphs = ()
                    else:
                        morphs = self._morphs(xmlword, wform=wordform)
                        assert morphs
                    word = CHILDESWord(wordform, mor=morphs, 
                                       sepprefix=(xmlword.get('separated-prefix')=='true'))

                # Put word object in a list
                try:
                    sent.append(word if as_obj else unicode(word))
                except Exception:
                    assert False,(fileid,xmlsent.attrib,wordform)
            # all results will be grouped by sentence
            results.append((who,sent) if include_speaker else sent)
        return results

    def raw_sents(self, fileids=None, speakers='ALL', include_speaker=False, punct=True,
            as_obj=False, strip_space=True):
        """
        speakers: may be 
          - 'ALL'
          - a participant ID such as 'CHI' or 'MOT'
          - a list of participant IDs
          - a filter function that, when applied to the participant data dict, 
            returns a true value for included participants
          - 'is_child' or 'is_adult' (see methods of the same name)
        
        tag: one of 'pos', 'morph', 'word'. If 'pos' or 'morph', and 
        `replace` is false, then the tag will be a list 
        for any word with multiple replacement words. (??)
        
        stem: whether to return the stem instead of the full wordform. 
        If True, forces replacement (because morphology is in reference 
        to the normalized word); the value of `replace` will be ignored.
        
        gold_gra: Some documents contain two tiers of grammatical analysis, 
        one of which is automatic (<gra type="gra">) 
        and one of which is gold standard (<gra type="grt">). 
        If this parameter is True, ONLY gold standard <gra> tiers will be loaded. 
        If it is False, then only non-gold <gra> tiers will be loaded.
        If it is None, then gold <gra> tiers will be preferred when available, 
        and non-gold tiers will be loaded only as a fallback.
        """
        def apply_to_file(fileid):
            return self._raw_sents_in_file(fileid, speakers=speakers, 
                include_speaker=include_speaker,
                punct=punct, as_obj=as_obj, strip_space=strip_space)
        return LazyConcatenation(LazyMap(apply_to_file, self.abspaths(fileids)))

    def sents(self, fileids=None, speakers='ALL', include_speaker=False, stem=False, 
            punct=True, as_obj=False, strip_space=True):
        if not as_obj:
            # 'stem' only applies if as_obj is false
            stringify = CHILDESWord.get_stem_str if stem else unicode
            return LazyMap(lambda (who,sent): (who,map(stringify, sent)) if include_speaker else map(stringify, sent), 
                self.sents(fileids=fileids, speakers=speakers, 
                    include_speaker=True,
                    stem=stem, punct=punct, as_obj=True, strip_space=strip_space))
        
        # as_obj is True
        
        def replace((who, sent)):
            # use <replacement> word(s) where present
            replaced = list(LazyConcatenation(map(CHILDESWord.interpreted_words, sent)))
            return (who, replaced) if include_speaker else replaced
        
        return LazyMap(replace, 
            self.raw_sents(fileids=fileids, speakers=speakers, include_speaker=True, 
                punct=punct, as_obj=True, strip_space=strip_space))

    def tagged_sents(self, fileids=None, speakers='ALL', include_speaker=False, stem=False, 
            punct=True, as_obj=False, strip_space=True):
        """Like ``sents()``, but entries in the sentence are tuples of the form
        (word, POStag)."""
        if not as_obj:
            stringify = CHILDESWord.get_stem_str if stem else unicode
        def add_pos((who,sent)):
            tagged = map(lambda w: (w if as_obj else stringify(w), w.mor.pos if w.mor else None),
                         sent)
            return (who,tagged) if include_speaker else tagged
        return LazyMap(add_pos,
            self.sents(fileids=fileids, speakers=speakers, include_speaker=True, 
                    stem=stem, punct=punct, as_obj=True, strip_space=strip_space))
    
    def raw_words(self, fileids=None, speakers='ALL', 
            punct=True, as_obj=False, strip_space=True):
        """Concatenation of ```raw_sents()``."""
        return LazyConcatenation(raw_sents(fileids=fileids, speakers=speakers, 
            punct=punct, as_obj=as_obj, strip_space=strip_space))
    
    def words(self, fileids=None, speakers='ALL', stem=False, 
            punct=True, as_obj=False, strip_space=True):
        """
        The results of ``sents()`` concatenated together. 
        """
        return LazyConcatenation(self.sents(fileids=fileids, speakers=speakers, 
            stem=stem, punct=punct, as_obj=as_obj, strip_space=strip_space))

    def tagged_words(self, fileids=None, speakers='ALL', stem=False, 
            punct=True, as_obj=False, strip_space=True):
        """
        The results of ``tagged_sents()`` concatenated together. 
        """
        return LazyConcatenation(self.tagged_sents(fileids=fileids, speakers=speakers, 
            stem=stem, punct=punct, as_obj=as_obj, strip_space=strip_space))

    def morph_sents(self, fileids=None, speakers='ALL', include_speaker=False, stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            punct=True, as_obj=False, skip_unanalyzed=False, strip_space=True):
        """
        Note that ``stem`` only applies if ``as_obj`` is false. 
        If ``stem=True`` and ``split_affixes=True`` are both passed, 
        then prefix and suffix morphs will be returned as empty strings.
        """
        
        if not as_obj:
            # 'stem' only applies if as_obj is false
            stringify = CHILDESMorph.get_stem_str if stem else unicode
            return LazyMap(lambda (who,sent): (who,map(stringify, sent)) if include_speaker else map(stringify, sent), 
                self.morph_sents(fileids=fileids, speakers=speakers, include_speaker=True, 
                    stem=stem, split_clitics=split_clitics, 
                    split_compounds=split_compounds, split_affixes=split_affixes,
                    punct=punct, as_obj=True, skip_unanalyzed=skip_unanalyzed, 
                    strip_space=strip_space))
        
        
        def morphize(w):
            # extract morphemes from word
            try:
                return w.split(clitics=split_clitics,
                               compounds=split_compounds,
                               affixes=split_affixes)
            except CHILDESError:    # no morphological annotation
                if skip_unanalyzed:
                    return []
                else:
                    return [w]  # just return the entire word
        
        def morphize_sent((who,sent)):
            morphized = list(LazyConcatenation(map(morphize, sent)))
            return (who, morphized) if include_speaker else morphized
        
        return LazyMap(morphize_sent,
            self.sents(fileids=fileids, speakers=speakers, include_speaker=True, stem=stem, 
                    punct=punct, as_obj=True, strip_space=strip_space))
    
    def tagged_morph_sents(self, fileids=None, speakers='ALL', include_speaker=False, stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            punct=True, as_obj=False, skip_unanalyzed=False, strip_space=True):
        """Like ``morph_sents()``, but entries in the sentence are tuples of the form
        (morph, POStag)."""
        if not as_obj:
            stringify = CHILDESMorph.get_stem_str if stem else unicode
        def add_pos(m):
            try:
                return (m if as_obj else stringify(m), m.pos if m else None)
            except AttributeError:
                # if there is no morphological analysis and 'm' is actually a CHILDESWord
                # (which has no 'pos')
                return (m if as_obj else stringify(m), None)
        return LazyMap(lambda (who,sent): (who,map(add_pos, sent)) if include_speaker else map(add_pos, sent),
            self.morph_sents(fileids=fileids, speakers=speakers, include_speaker=True, 
                stem=stem, split_clitics=split_clitics, 
                split_compounds=split_compounds, split_affixes=split_affixes, 
                punct=punct, as_obj=True, skip_unanalyzed=skip_unanalyzed, 
                strip_space=strip_space))
    
    def morphs(self, fileids=None, speakers='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            punct=True, as_obj=False, skip_unanalyzed=False, strip_space=True):
        """
        The results of ``morph_sents()`` concatenated together. 
        """
        return LazyConcatenation(self.morph_sents(fileids=fileids, speakers=speakers, stem=stem, punct=punct,
                    split_clitics=split_clitics, split_compounds=split_compounds, 
                    split_affixes=split_affixes, as_obj=as_obj, 
                    skip_unanalyzed=skip_unanalyzed, strip_space=strip_space))
    
    def tagged_morphs(self, fileids=None, speakers='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            punct=True, as_obj=False, skip_unanalyzed=False, strip_space=True):
        """The results of ``tagged_morph_sents()`` concatenated together."""
        return LazyConcatenation(self.tagged_morph_sents(fileids=fileids, speakers=speakers, stem=stem, punct=punct,
                    split_clitics=split_clitics, split_compounds=split_compounds, 
                    split_affixes=split_affixes, as_obj=as_obj, 
                    skip_unanalyzed=skip_unanalyzed, strip_space=strip_space))
    
    def morph_deps(self, fileids=None, speakers='ALL', include_speaker=False, 
            include_suffixes=True, gold_status=None, stem=False,
            punct=True, skip_unanalyzed=False, strip_space=True):
            
        def add_dep((m,p)):
            if not m: return ()
            try:
                form = m.get_str(include_suffixes=include_suffixes)
                return (form, p)+(m.dep(gold_status=gold_status) or ())
            except AttributeError:
                # no morphological analysis, so 'm' is actually a CHILDESWord
                return (unicode(m), p, None, None, None)
        
        return LazyMap(lambda (who,sent): (who,map(add_dep, sent)) if include_speaker else map(add_dep, sent), 
            self.tagged_morph_sents(fileids=fileids, speakers=speakers, include_speaker=True, 
                stem=stem, split_clitics=True, split_compounds=False, split_affixes=False,
                punct=punct, as_obj=True, skip_unanalyzed=skip_unanalyzed, 
                strip_space=strip_space))

    """
        :return: the given file(s) as a list of sentences or utterances, each
            encoded as a list of word strings.
        :rtype: list(list(str))

        :param speakers: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems, omitting affixes (but not clitics).
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        """
    
    def _conllu_format(self, (who,ww), gold_status=None, include_speaker=False, 
        include_suffixes=False, skip_unanalyzed_tokens=False, 
        convert_pos=ch2upos):
        
        try:
            lines = []
            i = 1
            sepprefixes = []
            sepprefixesS = ''
            for w in ww:
                if w.is_sepprefix:  # for CONLL-U purposes, count the separated prefix as part of a multiword with its stem
                    try:
                        sepprefixes.extend(w.split(clitics=True))
                    except CHILDESError:
                        # no morphologoy for 'w'
                        if skip_unanalyzed_tokens:
                            continue
                        sepprefixes.append(w)
                    sepprefixesS += unicode(w)
                    continue    # don't increment i
                tokform = w.wordform
                try:
                    mm = sepprefixes + w.split(clitics=True)
                except CHILDESError:
                    # no morphology for 'w'
                    if skip_unanalyzed_tokens:
                        continue
                    mm = sepprefixes + [w]
                sepprefixes = []
                if len(mm)>1:
                    # multiword
                    I = '{}-{}'.format(i, i+len(mm)-1)
                    lines.append(u'{}\t{}\t'.format(I, sepprefixesS+tokform) + '\t'.join('_'*8))
            
                for m in mm:
                    try:
                        if len(mm)==1:
                            form = sepprefixesS+tokform
                        else:
                            form = m.get_str(include_suffixes=include_suffixes)
                        sepprefixesS = ''

                        pos = m.pos
                        suffixes = u'|'.join(unicode(subm) for subm in m if subm.affix_status=='suffix')
                        upos = convert_pos(pos)
                        dep = m.dep(gold_status=gold_status) 
                        if not dep:
                            dep = ('_', '_', '_')
                        s = u'{}\t{}\t{}\t'.format(i, form, m.get_stem_str())
                        s += u'{}\t{}\t{}\t'.format(upos, pos, suffixes or '_')
                        s += u'{}\t{}\t_'.format(*dep[1:])
                        s += u'\t{}'.format(who if include_speaker else '_')
                        if dep[0]!='_':
                            assert dep[0]==i,(i,m.dep(gold_status=gold_status),s,lines)
                    except AttributeError:
                        # no morphology, so 'm' is actually a CHILDESWord
                        s = u'_\t{}\t'.format(unicode(m))
                        s += u'\t'.join('_'*7)
                        s += u'\t{}'.format(who if include_speaker else '_')
                        i -= 1  # this token isn't part of the parse, so it doesn't count
                    
                    lines.append(s)
                    i += 1
        except AssertionError as ex:
            print(u' '.join(map(unicode, ww)), file=sys.stderr)
            raise
                    
        return u'\n'.join(lines)

    def conllu_parses(self, fileids=None, speakers='ALL', gold_status=None, 
        include_speaker=False, include_suffixes=False, skip_unanalyzed_tokens=False, 
        convert_pos=ch2upos):
        return LazyMap(lambda sent: self._conllu_format(sent, gold_status=gold_status, 
                include_speaker=include_speaker, include_suffixes=include_suffixes, 
                skip_unanalyzed_tokens=skip_unanalyzed_tokens, convert_pos=convert_pos), 
            self.sents(fileids=fileids, speakers=speakers, include_speaker=True, stem=False, 
                punct=True, as_obj=True, strip_space=True))

    def corpus(self, fileids=None):
        """
        :return: the given file(s) as a dict of ``(corpus_property_key, value)``
        :rtype: list(dict)
        """
        if not self._lazy:
            return [self._get_corpus(fileid) for fileid in self.abspaths(fileids)]
        return LazyMap(self._get_corpus, self.abspaths(fileids))

    def _get_corpus(self, fileid):
        results = dict()
        xmldoc = ElementTree.parse(fileid).getroot()
        for key, value in xmldoc.items():
            results[key] = value
        return results

    def participants(self, fileids=None):
        """
        :return: the given file(s) as a dict of
            ``(participant_property_key, value)``
        :rtype: list(dict)
        """
        if not self._lazy:
            return [self._get_participants(fileid) for fileid in self.abspaths(fileids)]
        return LazyMap(self._get_participants, self.abspaths(fileids))

    def _clean_doc(self, fileid):
        """
        :return: the XML root of the document, with namespace URLs removed from tag names.
        Otherwise, because the document declares `xmlns="http://www.talkbank.org/ns/talkbank"`, 
        tag names would look like `{http://www.talkbank.org/ns/talkbank}tag`, which is 
        painful to work with.
        """
        # Unfortunately no elegant solution; this one is from https://bugs.python.org/issue18304
        it = ElementTree.iterparse(fileid)
        for _, el in it:
            el.tag = el.tag.split('}', 1)[1]  # strip all namespaces
        root = it.root
        return root

    def _get_participants(self, fileid):
        xmldoc = self._clean_doc(fileid)
        return self._get_participants_dict(xmldoc)
        
    def _get_participants_dict(self, xmldoc):
        # getting participants' data
        pat = defaultdict(dict)
        for participant in xmldoc.findall('.//Participants/participant'):
            for (key,value) in participant.items():
                pat[participant.get('id')][key] = value
        return dict(pat)

    def is_child(self, participant, fileid=None):
        """
        Returns True if any of the following apply:
         - the participant ID is 'CHI'
         - the participant's role is 'Child' or 'Target_Child'
         - the participant's age is provided and <15 years (180 months)
        """
        if isinstance(participant, string_types):
            participant = self.participants(fileids=fileid)[0][participant]
        id = participant['id']
        role = participant.get('role')
        age = participant.get('age')
        if age:
            age = self.convert_age(age)
        return bool(id=='CHI' or role.upper() in ('CHILD','TARGET_CHILD') or (age is not None and age<180))

    def is_adult(self, participant, fileid=None):
        """
        Returns True if none of the heuristics for identifying children apply. 
        See `is_child()`.
        """
        return not self.is_child(participant, fileid)

    def age(self, fileids=None, speaker='CHI', month=False):
        """
        :return: the given file(s) as string or int
        :rtype: list or int

        :param month: If true, return months instead of year-month-date
        """
        if not self._lazy:
            return [self._get_age(fileid, speaker, month)
                for fileid in self.abspaths(fileids)]
        get_age = lambda fileid: self._get_age(fileid, speaker, month)
        return LazyMap(get_age, self.abspaths(fileids))

    def _get_age(self, fileid, speaker, month):
        xmldoc = self._clean_doc(fileid)
        for pat in xmldoc.findall('.//Participants/participant'):
            try:
                if pat.get('id') == speaker:
                    age = pat.get('age')
                    if month:
                        age = self.convert_age(age)
                    return age
            # some files don't have age data
            except (TypeError, AttributeError) as e:
                return None

    def convert_age(self, age_year):
        "Caclculate age in months from a string in CHILDES format"
        m = re.match(r"P(\d+)Y(\d+)M?(\d?\d?)D?", age_year)
        age_month = int(m.group(1))*12 + int(m.group(2))
        try:
            if int(m.group(3)) > 15:
                age_month += 1
        # some corpora don't have age information?
        except ValueError as e:
            pass
        return age_month

    def MLU(self, fileids=None, speakers='CHI'):
        """
        :return: the given file(s) as a floating number
        :rtype: list(float)
        """
        if not self._lazy:
            return [self._getMLU(fileid, speakers=speakers)
                for fileid in self.abspaths(fileids)]
        get_MLU = lambda fileid: self._getMLU(fileid, speakers=speakers)
        return LazyMap(get_MLU, self.abspaths(fileids))

    def _getMLU(self, fileid, speakers):
        sents = self._get_words(fileid, speakers=speakers, sent=True, stem=True,
                    relation=False, pos=True, strip_space=True, replace=True)
        results = []
        lastSent = []
        numFillers = 0
        sentDiscount = 0
        for sent in sents:
            posList = [pos for (word,pos) in sent]
            # if any part of the sentence is intelligible
            if any(pos == 'unk' for pos in posList):
                next
            # if the sentence is null
            elif sent == []:
                next
            # if the sentence is the same as the last sent
            elif sent == lastSent:
                next
            else:
                results.append([word for (word,pos) in sent])
                # count number of fillers
                if len(set(['co',None]).intersection(posList)) > 0:
                    numFillers += posList.count('co')
                    numFillers += posList.count(None)
                    sentDiscount += 1
            lastSent = sent
        try:
            thisWordList = flatten(results)
            # count number of morphemes
            # (e.g., 'read' = 1 morpheme but 'read-PAST' is 2 morphemes)
            numWords = float(len(flatten([word.split('-')
                                          for word in thisWordList]))) - numFillers
            numSents = float(len(results)) - sentDiscount
            mlu = numWords/numSents
        except ZeroDivisionError:
            mlu = 0
        # return {'mlu':mlu,'wordNum':numWords,'sentNum':numSents}
        return mlu

    def _utterance_nodes(self, xmldoc, speakers):
        # processing each xml doc
        for xmlsent in xmldoc.findall('.//u'):
            # filter by speakers
            if speakers == 'ALL' or xmlsent.get('who') in speakers:
                yield xmlsent.get('who'), xmlsent

    def _word_nodes(self, xmlsent, punct):
        def expand_g(xmlwords):
            """<g> can group multiple <w> words together. This iterates over the <w> words."""
            for xmlword in xmlwords:
                if xmlword.tag=='g': # <g> is used, e.g., when there is a replacement. immediately dominates <w>
                    xmlsubwords = xmlword.findall('./w')
                    if not xmlsubwords:
                        xmlsubwords = xmlword.findall(".//ga[@type='paralinguistics']")
                    assert xmlsubwords is not None,(xmlsent.attrib,fileid)
                    for xmlsubword in xmlsubwords:
                        yield xmlsubword
                else:
                    yield xmlword
    
        for xmlword in expand_g(xmlsent.findall('./*')):
            
            """
            # getting replaced words
            if replace and xmlsent.find(token_path+'/replacement'):
                xmlword = xmlsent.find(token_path+'/replacement/w')
            elif replace and xmlsent.find(token_path+'/wk'):
                xmlword = xmlsent.find(token_path+'/wk')
            """
            
            if not punct and xmlword.tag in ('tagMarker', 't'):
                # skip punctuation (though note that <tagMarker> and <t> elements ARE in the dependency parse)
                continue
            elif xmlword.tag in ('a', 'e', 'pause', 'linker'):
                # nodes directly under the utterance that don't count as words
                # <a> mainly for transcriber comments, <e> for actions, etc.
                continue
            
            yield xmlword
            
    def _wordform(self, xmlword, strip_space):
        if xmlword.tag=='tagMarker':
            marker_type = xmlword.attrib["type"]
            if marker_type=='comma':
                word = ','
            elif marker_type=='vocative':
                word = '‡'.decode('utf-8') # symbol used in CHAT format for <tagMarker type="vocative">
            elif marker_type=='tag':
                word = '„'.decode('utf-8') # symbol used in CHAT format for <tagMarker type="tag">
            else:
                raise ValueError('Unknown tagMarker type: '+marker_type)
        elif xmlword.tag=='t':
            # end-of-utterance punctuation
            t_type = xmlword.attrib["type"]
            if t_type=='p':
                word = '.'
            elif t_type=='q':
                word = '?'
            elif t_type=='e':
                word = '!'
            elif t_type=='trail off':
                word = '+...'
            elif t_type=='interruption':
                word = '+/.'
            else:
                word = '<'+t_type+'>'
        elif xmlword.tag=='ga' and xmlword.attrib['type']=='paralinguistics':
            word = '[=! '+xmlword.text+']'
        elif xmlword.tag=='quotation':
            q_type = xmlword.get('type')
            if q_type=='begin':
                word = '``'
            elif q_type=='end':
                word = "''"
            else:
                raise ValueError('Unknown quotation mark type: '+q_type)
        else:
            word = ''
            if xmlword.get('type')=='fragment':
                word += '&'
            elif xmlword.get('type')=='omission':
                word += '0'
            word += xmlword.text or ''    # text before the first child tag
            for ch in xmlword:
                if ch.tag=='shortening':
                    word += '('+ch.text+')' # elided part of word
                elif ch.tag=='wk':  # compound separator
                    word += {'cmp': '+', 'cli': '~'}[ch.attrib['type']]
                word += ch.tail or '' # text following this child and within the word
            if xmlword.get('separated-prefix')=='true':
                word += '#'
        
            # strip tailing space
            if strip_space:
                word = word.strip()
        
        return word

    def _morph_mw(self, xmlmw):
        """
        Morphemic word.
        <mw> contains <mpfx>* <pos> <stem> <mk>*
        
        <mk> is for suffixes, of which there are 3 kinds:
        https://talkbank.org/software/xsddoc/schemas/talkbank_xsd/elements/mk.html
        
        In English, the suffix is a morphological attribute (e.g., "PL") rather than a morph form.
        """
        stem = xmlmw.find('.//stem').text
        prefix = u''.join(mpfx.text+'#' for mpfx in xmlmw.findall('.//mpfx'))
        #prefixed_stem = prefix + stem
        coarsepos = xmlmw.find('.//pos/c').text
        pos = coarsepos + u''.join(':'+x.text for x in xmlmw.findall('.//pos/s'))
        SUFFIX_TYPES = {'sfx': '-', # suffix
                        'sfxf': '&', # fusional suffix
                        'mc': ':'}  # morphological category
        suffix = u''.join(SUFFIX_TYPES[mk.attrib['type']]+mk.text for mk in xmlmw.findall('.//mk'))
        #return (prefixed_stem, stem, pos, infl)
        if prefix or suffix:
            morphs = []
            if prefix:
                morphs.append(CHILDESMorph(prefix, affix_status='prefix'))
            morphs.append(CHILDESMorph(stem))
            if suffix:
                morphs.append(CHILDESMorph(suffix, affix_status='suffix'))
            return CHILDESMorph(morphs, pos=pos)
        else:
            return CHILDESMorph(stem, pos=pos)

    def _morph_mwc(self, xmlmwc):
        """
        Compound morphemic word.
        <mwc> contains <mpfx>* <pos> <mw>{2,}
        """
        morphs = [self._morph_mw(xmlmw) for xmlmw in xmlmwc.findall('.//mw')]
        #compound_morphs = '='.join(prefixed_stem for prefixed_stem,_,_,_ in morphs)
        #prefix = u''.join(mpfx.text+'++' for mpfx in xmlmw.findall('.//mpfx'))
        prefix = u''.join(mpfx.text+'#' for mpfx in xmlmw.findall('.//mpfx'))
        prefixL = [CHILDESMorph(prefix, affix_status='prefix')] if prefix else []
        #prefixed_compound = prefix + compound_morphs
        coarsepos = xmlmwc.find('.//pos/c').text
        pos = coarsepos + u''.join(':'+x.text for x in xmlmwc.findall('.//pos/s'))
        #return (prefixed_compound, compound_morphs, pos, morphs)
        return CHILDESMorph(prefixL + morphs, pos=pos, is_compound=True)

    def _morph_gra(self, xmlgra):
        dep = (int(xmlgra.attrib['index']),
               int(xmlgra.attrib['head']),
               xmlgra.attrib['relation'])
        return dep

    def _morphs(self, xmlword, clitic_status=None, wform=None):
        """
        Main morphological unit and pre-/post-clitics. 
        Each of these participate in grammatical (dependency) relations.
        Schema documentation at https://talkbank.org/software/xsddoc/schemas/talkbank_xsd/complexTypes/morType.html
        <mor> contains (<mw> | <mwc> | <mt>) <menx>* <gra>* <mor-pre>* <mor-post>*
        """
        preclitics = [] # <mor-pre>
        postclitics = []    # <mor-post>
        mainmorph = None    # <mw> or <mwc> [ignore <mt>, which is for terminal punctuation]
        mainmorphtag = None
        # ignore <menx> [translation] for now
        
        # dependency information for the main unit (<mw>, <mwc>, or <mt>)
        gra = {}    # gra_type -> dependency triple
        
        # We always load the <mor type="mor"> tier and ignore <mor type="trn"> 
        # if present (this seems to be analogous to gra/grt: the latter is for 
        # training a system, i.e., it is a gold standard).
        
        for xmlm in (xmlword if clitic_status else xmlword.findall(".//mor[@type='mor']/*")):
            if xmlm.tag=='mw':
                assert mainmorph is None,mainmorph
                mainmorph = self._morph_mw(xmlm)
                mainmorphtag = 'mw'
            elif xmlm.tag=='mwc':
                assert mainmorph is None,mainmorph
                mainmorph = self._morph_mwc(xmlm)
                mainmorphtag = 'mwc'
            elif xmlm.tag=='mt':    # terminal punctuation
                assert mainmorph is None,mainmorph
                # nothing interesting here
                mainmorph = CHILDESMorph(wform, pos=wform, is_punct=True)
                mainmorphtag = 'mt'
            elif xmlm.tag=='mor-pre':
                preclitics.append(self._morphs(xmlm, clitic_status='pre'))
            elif xmlm.tag=='mor-post':
                postclitics.append(self._morphs(xmlm, clitic_status='post'))
            elif xmlm.tag=='gra':
                gra_type = xmlm.attrib['type']
                assert gra_type not in gra
                gra[gra_type] = self._morph_gra(xmlm)
                
        assert mainmorph is not None,(clitic_status,xmlword.tag,xmlword.text,list(xmlword))
        assert unicode(mainmorph) or mainmorphtag=='mt',mainmorph
        
        for gra_type,dep in gra.items():
            mainmorph.set_gra(gra_type, dep)
        
        if clitic_status:
            assert not preclitics+postclitics
            mainmorph.clitic_status = clitic_status
            return mainmorph
        else:
            if preclitics+postclitics:
                return CHILDESMorph(preclitics+[mainmorph]+postclitics)
            return mainmorph


    # Ready-to-use browser opener

    """
    The base URL for viewing files on the childes website. This
    shouldn't need to be changed, unless CHILDES changes the configuration
    of their server or unless the user sets up their own corpus webserver.
    """
    childes_url_base = r'http://childes.psy.cmu.edu/browser/index.php?url='


    def webview_file(self, fileid, urlbase=None):
        """Map a corpus file to its web version on the CHILDES website,
        and open it in a web browser.

        The complete URL to be used is:
            childes.childes_url_base + urlbase + fileid.replace('.xml', '.cha')

        If no urlbase is passed, we try to calculate it.  This
        requires that the childes corpus was set up to mirror the
        folder hierarchy under childes.psy.cmu.edu/data-xml/, e.g.:
        nltk_data/corpora/childes/Eng-USA/Cornell/??? or
        nltk_data/corpora/childes/Romance/Spanish/Aguirre/???

        The function first looks (as a special case) if "Eng-USA" is
        on the path consisting of <corpus root>+fileid; then if
        "childes", possibly followed by "data-xml", appears. If neither
        one is found, we use the unmodified fileid and hope for the best.
        If this is not right, specify urlbase explicitly, e.g., if the
        corpus root points to the Cornell folder, urlbase='Eng-USA/Cornell'.
        """

        import webbrowser, re

        if urlbase:
            path = urlbase+"/"+fileid
        else:
            full = self.root + "/" + fileid
            full = re.sub(r'\\', '/', full)
            if '/childes/' in full.lower():
                # Discard /data-xml/ if present
                path = re.findall(r'(?i)/childes(?:/data-xml)?/(.*)\.xml', full)[0]
            elif 'eng-usa' in full.lower():
                path = 'Eng-USA/' + re.findall(r'/(?i)Eng-USA/(.*)\.xml', full)[0]
            else:
                path = fileid

        # Strip ".xml" and add ".cha", as necessary:
        if path.endswith('.xml'):
            path = path[:-4]

        if not path.endswith('.cha'):
            path = path+'.cha'

        url = self.childes_url_base + path

        webbrowser.open_new_tab(url)
        print("Opening in browser:", url)
        # Pausing is a good idea, but it's up to the user...
        # raw_input("Hit Return to continue")



def demo(corpus_root=None):
    """
    The CHILDES corpus should be manually downloaded and saved
    to ``[NLTK_Data_Dir]/corpora/childes/``
    """
    if not corpus_root:
        from nltk.data import find
        corpus_root = find('corpora/childes/data-xml/Eng-USA/')

    try:
        childes = CHILDESCorpusReader(corpus_root, '.*.xml')
        # describe all corpus
        for file in childes.fileids()[:5]:
            corpus = ''
            corpus_id = ''
            for (key,value) in childes.corpus(file)[0].items():
                if key == "Corpus": corpus = value
                if key == "Id": corpus_id = value
            print('Reading', corpus,corpus_id,' .....')
            print("words:", childes.words(file)[:7],"...")
            print("words with replaced words:", childes.words(file, replace=True)[:7]," ...")
            print("words with pos tags:", childes.tagged_words(file)[:7]," ...")
            print("words (only MOT):", childes.words(file, speakers='MOT')[:7], "...")
            print("words (only CHI):", childes.words(file, speakers='CHI')[:7], "...")
            print("stemmed words:", childes.words(file, stem=True)[:7]," ...")
            print("words with relations and pos-tag:", childes.words(file, relation=True)[:5]," ...")
            print("sentence:", childes.sents(file)[:2]," ...")
            for (participant, values) in childes.participants(file)[0].items():
                    for (key, value) in values.items():
                        print("\tparticipant", participant, key, ":", value)
            print("num of sent:", len(childes.sents(file)))
            print("num of morphemes:", len(childes.words(file, stem=True)))
            print("age:", childes.age(file))
            print("age in month:", childes.age(file, month=True))
            print("MLU:", childes.MLU(file))
            print()

    except LookupError as e:
        print("""The CHILDES corpus, or the parts you need, should be manually
        downloaded from http://childes.psy.cmu.edu/data-xml/ and saved at
        [NLTK_Data_Dir]/corpora/childes/
            Alternately, you can call the demo with the path to a portion of the CHILDES corpus, e.g.:
        demo('/path/to/childes/data-xml/Eng-USA/")
        """)
        #corpus_root_http = urllib2.urlopen('http://childes.psy.cmu.edu/data-xml/Eng-USA/Bates.zip')
        #corpus_root_http_bates = zipfile.ZipFile(cStringIO.StringIO(corpus_root_http.read()))
        ##this fails
        #childes = CHILDESCorpusReader(corpus_root_http_bates,corpus_root_http_bates.namelist())


if __name__ == "__main__":
    demo()

