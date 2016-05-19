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
from nltk.compat import string_types

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.xmldocs import XMLCorpusReader, ElementTree

class CHILDESWord(object):
    uttered = None
    "Uttered wordform"
    
    interpreted = []
    """Wordform(s) that the transcriber understood from the uttered word: 
    either the same as `uttered`, or a normalized form in a <replacement>."""
    
    real = None
    """True if there is a <replacement> of a real word with an intended word
    (apparently this distinction is not made in practice for the corpora examined)."""
    
    mor = []
    "Morphological/grammatical analysis per interpreted word"

    def __init__(self, uttered, mor=None, replacement_wordforms=None, real=None):
        self.uttered = uttered
        if replacement_wordforms is None:
            self.interpreted = [uttered]
            self.mor = [mor]
        else:
            self.interpreted = replacement_wordforms
            self.mor = mor
            assert len(self.mor)==len(replacement_wordforms),(replacement_wordforms,self.mor)
        self.real = real

    @property
    def nMorphs(self):
        return sum(m.nMorphs for m in self.mor)

    def descendants(self):
        """Morphological units under this word."""
        return mor + [d for m in mor for d in mor.descendants()]

    def split(self, clitics=True, compounds=False, affixes=False):
        """Return a list of morphemes based on the given split criteria.
        Note: splitting affixes will always cause clitics to be split.
        """
        queue = list(self.mor)
        result = []
        while queue:
            m = queue.pop(0)
            if m.is_compound:
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
        assert result,self.mor
        return result

    def __iter__(self):
        """Iterate over morphological units under this word"""
        return iter(self.mor)

    def __str__(self):
        """Approximate .cha rendering of word layer (not morphology)"""
        s = self.uttered
        if len(self.interpreted)>1 or self.interpreted[0]!=self.uttered:
            # <replacement>
            s += ' [:: '  if self.real else ' [: '
            s += u' '.join(interpreted)
            s += ']'
        return s
    
    def __repr__(self):
        return '<'+unicode(self)+' ({} morph components)>'.format(self.nMorphs)

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
        if isinstance(form_or_submorphs, basestring):
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
        s = ''
        if self.submorphs:
            assert not self._form
            if self.is_compound:
                s = u'+'.join(map(unicode, self.submorphs))
            else:
                # TODO: is this assertion true for compounds?
                assert sum(1 for m in self.submorphs if not (m.clitic_status or m.affix_status))==1,self.submorphs
                s = u''.join(map(unicode, self.submorphs))
        else:
            s = self._form
        
        if self.clitic_status=='pre':
            return s + '~'
        elif self.clitic_status=='post':
            return '~' + s
        return s
        
    def __repr__(self):
        return u'|'.join(map(unicode,
                            (self.pos or '', 
                             self,
                             self.get_stem_str() or '',
                             self.get_dep_str() or '')))
    
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
    
    def descendants(self):
        return self.submorphs + [d for subm in self.submorphs for d in subm.descendants()]

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

class CHILDESCorpusReader(XMLCorpusReader):
    """
    Corpus reader for the XML version of the CHILDES corpus.
    The CHILDES corpus is available at ``http://childes.psy.cmu.edu/``. The XML
    version of CHILDES is located at ``http://childes.psy.cmu.edu/data-xml/``.
    Copy the needed parts of the CHILDES XML corpus into the NLTK data directory
    (``nltk_data/corpora/CHILDES/``).

    For access to the file text use the usual nltk functions,
    ``words()``, ``sents()``, ``tagged_words()`` and ``tagged_sents()``.
    """
    def __init__(self, root, fileids, lazy=True):
        XMLCorpusReader.__init__(self, root, fileids)
        self._lazy = lazy

    def morphs(self, fileids=None, speaker='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            strip_space=True, replace=False, punct=False):
            
        return LazyMap((lambda m: unicode(m)),
            self.tagged_morphs(fileids=fileids, speaker=speaker, stem=stem, 
            split_clitics=split_clitics, split_compounds=split_compounds, split_affixes=split_affixes, 
            strip_space=strip_space, replace=replace, punct=punct))
        
    def tagged_morphs(self, fileids=None, speaker='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            strip_space=True, replace=False, punct=False):
        
        return LazyMap((lambda m: (unicode(m), m)),
            LazyConcatenation(LazyMap((lambda (s,m): m.split(clitics=split_clitics, 
            compounds=split_compounds, affixes=split_affixes) if m else None), 
            self.tagged_words(fileids=fileids, speaker=speaker, tag='word', stem=stem, 
                strip_space=strip_space, replace=replace, punct=punct))))
    
    def _morph_sents(self, fileids=None, speaker='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            strip_space=True, replace=False, punct=False):
        """Returns sentences of CHILDESMorph objects"""
        
        return LazyMap(lambda sent: LazyConcatenation(map(lambda (s,w): w.split(clitics=split_clitics, 
            compounds=split_compounds, affixes=split_affixes), sent)), 
            self.tagged_sents(fileids=fileids, speaker=speaker, tag='word', stem=stem, 
            strip_space=strip_space, replace=replace, punct=punct))
    
    def morph_sents(self, fileids=None, speaker='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            strip_space=True, replace=False, punct=False):
            
        return LazyMap((lambda sent: map(lambda (s,m): s, sent)),
            self.tagged_morph_sents(fileids=fileids, speaker=speaker, stem=stem, 
            split_clitics=split_clitics, split_compounds=split_compounds, split_affixes=split_affixes, 
            strip_space=strip_space, replace=replace, punct=punct))
    
    def tagged_morph_sents(self, fileids=None, speaker='ALL', stem=False, 
            split_clitics=True, split_compounds=False, split_affixes=False,
            strip_space=True, replace=False, punct=False):
            
        return LazyMap((lambda sent: map(lambda m: (unicode(m), m), sent)),
            self._morph_sents(fileids=fileids, speaker=speaker, stem=stem, 
            split_clitics=split_clitics, split_compounds=split_compounds, split_affixes=split_affixes, 
            strip_space=strip_space, replace=replace, punct=punct))
    
    def morph_deps(self, fileids=None, speaker='ALL', gold_status=None, stem=False,
            strip_space=True, punct=True):
            
        return LazyMap((lambda sent: map(lambda (s,m): (s,)+(m.dep(gold_status=gold_status) or ()), sent)), 
            self.tagged_morph_sents(fileids=fileids, speaker=speaker, stem=stem,
                split_clitics=True, split_compounds=False, split_affixes=False,
                strip_space=strip_space, replace=True, punct=punct))

    def words(self, fileids=None, speaker='ALL', stem=False,
            strip_space=True, replace=False, punct=False):
        """
        :return: the given file(s) as a list of words
        :rtype: list(str)

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems, omitting affixes (but not clitics).
        --:param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=None
        mor=False
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, mor, stem,
                strip_space, replace, punct=punct) for fileid in self.abspaths(fileids)]

        get_words = lambda fileid: self._get_words(fileid, speaker, sent, mor, stem,
            strip_space, replace, punct=punct)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def tagged_words(self, fileids=None, speaker='ALL', tag='morph', stem=False,
            strip_space=True, replace=False, punct=False):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems, omitting affixes (but not clitics).
        --:param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=None
        assert tag in ('pos', 'morph', 'word')
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, tag, stem,
                strip_space, replace, punct=punct) for fileid in self.abspaths(fileids)]

        get_words = lambda fileid: self._get_words(fileid, speaker, sent, tag, stem,
            strip_space, replace, punct=punct)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def sents(self, fileids=None, speaker='ALL', stem=False,
            strip_space=True, replace=False, punct=False):
        """
        :return: the given file(s) as a list of sentences or utterances, each
            encoded as a list of word strings.
        :rtype: list(list(str))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems, omitting affixes (but not clitics).
        --:param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=True
        mor=False
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, mor, stem,
                strip_space, replace, punct=punct) for fileid in self.abspaths(fileids)]
        
        get_words = lambda fileid: self._get_words(fileid, speaker, sent, mor, stem,
            strip_space, replace, punct=punct)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def tagged_sents(self, fileids=None, speaker='ALL', tag='morph', stem=False,
            strip_space=True, replace=False, punct=False):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.
        :rtype: list(list(tuple(str,str)))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems, omitting affixes (but not clitics).
        --:param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=True
        assert tag in ('pos', 'morph', 'word')
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, tag, stem,
                strip_space, replace, punct=punct) for fileid in self.abspaths(fileids)]
        
        get_words = lambda fileid: self._get_words(fileid, speaker, sent, tag, stem,
            strip_space, replace, punct=punct)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

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
        # multidimensional dicts
        def dictOfDicts():
            return defaultdict(dictOfDicts)

        xmldoc = self._clean_doc(fileid)
        # getting participants' data
        pat = dictOfDicts()
        for participant in xmldoc.findall('.//Participants/participant'):
            for (key,value) in participant.items():
                pat[participant.get('id')][key] = value
        return pat

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
        m = re.match("P(\d+)Y(\d+)M?(\d?\d?)D?",age_year)
        age_month = int(m.group(1))*12 + int(m.group(2))
        try:
            if int(m.group(3)) > 15:
                age_month += 1
        # some corpora don't have age information?
        except ValueError as e:
            pass
        return age_month

    def MLU(self, fileids=None, speaker='CHI'):
        """
        :return: the given file(s) as a floating number
        :rtype: list(float)
        """
        if not self._lazy:
            return [self._getMLU(fileid, speaker=speaker)
                for fileid in self.abspaths(fileids)]
        get_MLU = lambda fileid: self._getMLU(fileid, speaker=speaker)
        return LazyMap(get_MLU, self.abspaths(fileids))

    def _getMLU(self, fileid, speaker):
        sents = self._get_words(fileid, speaker=speaker, sent=True, stem=True,
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

    def _utterance_nodes(self, fileid, speaker):
        if isinstance(speaker, string_types) and speaker != 'ALL':  # ensure we have a list of speakers
            speaker = [ speaker ]
        xmldoc = self._clean_doc(fileid)
        # processing each xml doc
        for xmlsent in xmldoc.findall('.//u'):
            # filter by speakers
            if speaker == 'ALL' or xmlsent.get('who') in speaker:
                yield xmlsent

    def _word_nodes(self, xmlsent, punct):
        for xmlword in xmlsent.findall('./*'):
            if xmlword.tag=='g': # <g> is used, e.g., when there is a replacement. immediately dominates <w>
                xmlsubword = xmlword.find('.//w')
                if xmlsubword is None:
                    xmlsubword = xmlword.find(".//ga[@type='paralinguistics']")
                xmlword = xmlsubword
                assert xmlword is not None,(xmlsent.attrib,fileid)
            
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
                word = '‡'  # symbol used in CHILDES .cha format for <tagMarker type="vocative">
            elif marker_type=='tag':
                word = '„' # symbol used in CHILDES .cha format for <tagMarker type="tag">
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
        else:
            word = ''
            if xmlword.attrib.get('type')=='fragment':
                word += '&'
            word += xmlword.text or ''    # text before the first child tag
            for ch in xmlword:
                if ch.tag=='shortening':
                    word += '('+ch.text+')' # elided part of word
                elif ch.tag=='wk':  # compound separator
                    word += {'cmp': '+', 'cli': '~'}[ch.attrib['type']]
                word += ch.tail or '' # text following this child and within the word
            if xmlword.attrib.get('separated-prefix')=='true':
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

    def _morphs(self, xmlword, gold_gra, clitic_status=None, wform=None):
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
                preclitics.append(self._morphs(xmlm, gold_gra, clitic_status='pre'))
            elif xmlm.tag=='mor-post':
                postclitics.append(self._morphs(xmlm, gold_gra, clitic_status='post'))
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

    def _get_words(self, fileid, speaker, bysent, tag, stem,
            strip_space, replace, punct=False, gold_gra=None):
        """
        tag: one of 'pos', 'morph', 'word'.
        
        gold_gra: Some documents contain two tiers of grammatical analysis, 
        one of which is automatic (<gra type="gra">) 
        and one of which is gold standard (<gra type="grt">). 
        If this parameter is True, ONLY gold standard <gra> tiers will be loaded. 
        If it is False, then only non-gold <gra> tiers will be loaded.
        If it is None, then gold <gra> tiers will be preferred when available, 
        and non-gold tiers will be loaded only as a fallback.
        """
        results = []
        for xmlsent in self._utterance_nodes(fileid, speaker):
            sents = []
            
            for xmlword in self._word_nodes(xmlsent, punct):
                # one uttered word, though if there is a <replacement> 
                # it may have multiple words
                assert xmlword is not None,(xmlsent.attrib,fileid)
                wordform = self._wordform(xmlword, strip_space)
                
                xmlrepl = xmlword.find('.//replacement')
                if xmlrepl is not None:
                    real = xmlrepl.get('real')
                    ww = xmlrepl.findall('.//w')
                    # if there is a <replacement>, then any <mor> tiers are within it
                else:
                    real = None
                    ww = [xmlword]
                
                try:
                
                    wforms = []
                    mor = []
                    for w in ww:
                        wform = self._wordform(w, strip_space)
                        wforms.append(wform)
                    
                        if w.find(".//mor[@type='mor']") is None:
                            morphs = ()
                        else:
                            morphs = self._morphs(w, gold_gra, wform=wform)
                        mor.append(morphs)
                
                    word = CHILDESWord(wordform, mor, wforms, real=real)
                
                except AssertionError:
                    print(fileid, xmlsent.attrib['uID'], wordform, file=sys.stderr)
                    raise

                if not stem:
                    wordSL = word.interpreted if replace else [word.uttered]
                else:
                    wordSL = [m.get_stem_str() if m else None for m in word.mor]
                
                if tag:
                    if tag=='pos':
                        sents.extend(zip(wordSL,[(m.pos if m else None) for m in word.mor]))
                    elif tag=='morph':
                        sents.extend(zip(wordSL,word.mor))
                    elif tag=='word':
                        sents.extend(zip(wordSL, [word]*len(wordSL)))
                    else:
                        raise ValueError('Invalid value of tag parameter: '+tag)
                else:
                    sents.extend(wordSL)
            if bysent:
                results.append(sents)
            else:
                results.extend(sents)
        return LazyMap(lambda x: x, results)


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
            print("words (only MOT):", childes.words(file, speaker='MOT')[:7], "...")
            print("words (only CHI):", childes.words(file, speaker='CHI')[:7], "...")
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

