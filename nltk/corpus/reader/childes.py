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

import re
from collections import defaultdict

from nltk.util import flatten, LazyMap, LazyConcatenation
from nltk.compat import string_types

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.xmldocs import XMLCorpusReader, ElementTree

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

    def words(self, fileids=None, speaker='ALL', stem=False,
            relation=False, strip_space=True, replace=False):
        """
        :return: the given file(s) as a list of words
        :rtype: list(str)

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=None
        pos=False
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, stem, relation,
                pos, strip_space, replace) for fileid in self.abspaths(fileids)]

        get_words = lambda fileid: self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def tagged_words(self, fileids=None, speaker='ALL', stem=False,
            relation=False, strip_space=True, replace=False, punct=False):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=None
        pos=True
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, stem, relation,
                pos, strip_space, replace, punct=punct) for fileid in self.abspaths(fileids)]

        get_words = lambda fileid: self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace, punct=punct)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def sents(self, fileids=None, speaker='ALL', stem=False,
            relation=None, strip_space=True, replace=False, punct=False):
        """
        :return: the given file(s) as a list of sentences or utterances, each
            encoded as a list of word strings.
        :rtype: list(list(str))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=True
        pos=False
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, stem, relation,
                pos, strip_space, replace, punct=punct) for fileid in self.abspaths(fileids)]
        
        get_words = lambda fileid: self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace, punct=punct)
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def tagged_sents(self, fileids=None, speaker='ALL', stem=False,
            relation=None, strip_space=True, replace=False):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.
        :rtype: list(list(tuple(str,str)))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent=True
        pos=True
        if not self._lazy:
            return [self._get_words(fileid, speaker, sent, stem, relation,
                pos, strip_space, replace) for fileid in self.abspaths(fileids)]
        
        get_words = lambda fileid: self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace)
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

    def _get_words(self, fileid, speaker, sent, stem, relation, pos,
            strip_space, replace, punct=False, gold_gra=None):
            """
            gold_gra: Some documents contain two tiers of grammatical analysis, 
            one of which is automatic (<gra type="gra">) 
            and one of which is gold standard (<gra type="grt">). 
            If this parameter is True, ONLY gold standard <gra> tiers will be loaded. 
            If it is False, then only non-gold <gra> tiers will be loaded.
            If it is None, then gold <gra> tiers will be preferred when available, 
            and non-gold tiers will be loaded only as a fallback.
            """
        if isinstance(speaker, string_types) and speaker != 'ALL':  # ensure we have a list of speakers
            speaker = [ speaker ]
        xmldoc = self._clean_doc(fileid)
        # processing each xml doc
        results = []
        for xmlsent in xmldoc.findall('.//u'):
            sents = []
            # select speakers
            if speaker == 'ALL' or xmlsent.get('who') in speaker:
                token_path = ('.//w') if not punct else './*'
                for xmlword in xmlsent.findall(token_path):
                    if xmlword.tag=='g': # <g> is used, e.g., when there is a replacement. immediately dominates <w>
                        xmlsubword = xmlword.find('.//w')
                        if xmlsubword is None:
                            xmlsubword = xmlword.find(".//ga[@type='paralinguistics']")
                        xmlword = xmlsubword
                        assert xmlword is not None,(xmlsent.attrib,xmldoc.attrib,fileid)
                    
                    infl = None ; suffixStem = None; suffixTag = None
                    # getting replaced words
                    if replace and xmlsent.find(token_path+'/replacement'):
                        xmlword = xmlsent.find(token_path+'/replacement/w')
                    elif replace and xmlsent.find(token_path+'/wk'):
                        xmlword = xmlsent.find(token_path+'/wk')
                    
                    assert xmlword is not None,(xmlsent.attrib,xmldoc.attrib,fileid)
                        
                    # get text
                    VOCATIVE = '‡'  # symbol used in CHILDES .cha format for <tagMarker type="vocative">
                    TAG = '„' # symbol used in CHILDES .cha format for <tagMarker type="tag">
                    # note that <tagMarker>s ARE included in the dependency parse

                    if xmlword.tag=='tagMarker':
                        marker_type = xmlword.attrib["type"]
                        if marker_type=='comma':
                            word = ','
                        elif marker_type=='vocative':
                            word = VOCATIVE
                        elif marker_type=='tag':
                            word = TAG
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
                    elif xmlword.tag=='ga' and xmlword.attrib['type']=='paralinguistics':
                        word = '[=! '+xmlword.text+']'
                    elif xmlword.tag in ('a', 'e', 'pause', 'linker'):
                        # <a> mainly for transcriber comments, <e> for actions, etc.
                        continue
                    else:
                        word = ''
                        if xmlword.attrib.get('type')=='fragment':
                            word += '&'
                        word += xmlword.text or ''    # text before the first child tag
                        for ch in xmlword:
                            if ch.tag=='shortening':
                                word += '('+ch.text+')' # elided part of word
                            word += ch.tail or '' # text following this child and within the word
                        if xmlword.attrib.get('separated-prefix')=='true':
                            word += '#'
                    
                    # strip tailing space
                    if strip_space:
                        word = word.strip()
                    tok = word
                    # stem and suffix
                    mor = ''
                    if relation or stem:
                        try:
                            xmlstem = xmlword.find('.//stem')
                            mor = xmlstem.text
                        except AttributeError as e:
                            pass
                        # if there is an inflection
                        try:
                            xmlinfl = xmlword.find('.//mor/mw/mk')
                            mor += '-' + xmlinfl.text
                        except:
                            pass
                        # if there is a suffix
                        try:
                            xmlsuffix = xmlword.find('.//mor/mor-post/mw/stem')
                            suffixStem = xmlsuffix.text
                        except AttributeError:
                            suffixStem = ""
                        if suffixStem:
                            mor += "~"+suffixStem
                    # pos
                    if relation or pos:
                        try:
                            xmlpos = xmlword.findall(".//c")
                            xmlpos2 = xmlword.findall(".//s")
                            if xmlpos2 != []:
                                tag = xmlpos[0].text+":"+xmlpos2[0].text
                            else:
                                tag = xmlpos[0].text
                        except (AttributeError,IndexError) as e:
                            tag = ""
                        try:
                            xmlsuffixpos = xmlword.findall('.//mor/mor-post/mw/pos/c')
                            xmlsuffixpos2 = xmlword.findall('.//mor/mor-post/mw/pos/s')
                            if xmlsuffixpos2:
                                suffixTag = xmlsuffixpos[0].text+":"+xmlsuffixpos2[0].text
                            else:
                                suffixTag = xmlsuffixpos[0].text
                        except:
                            pass
                        if suffixTag:
                            tag += "~"+suffixTag
                        tok = (word, mor, tag, '')
                        assert ''.join(tok),(xmlword.tag, sents, xmlword.text, [ch.tail for ch in xmlword], xmlword.attrib, xmlsent.attrib, xmldoc.attrib, fileid)
                        # note that some words in certain documents may be missing morphological analysis
                        
                    # relational
                    # the gold standard is stored in
                    # <mor></mor><mor type="trn"><gra type="grt">
                    if relation == True:
                        a, b, c, r = tok
                        for xmlstem_rel in xmlword.findall('.//mor/gra'):
                            
                            if r:
                                r += '+'
                            if not xmlstem_rel.get('type') == 'grt':    # non-gold <gra> tier
                                r += (xmlstem_rel.get('index')
                                        + "|" + xmlstem_rel.get('head')
                                        + "|" + xmlstem_rel.get('relation'))
                            else:   # TODO: gold <gra> tier
                                tok = (tok[0], tok[1], tok[2],
                                        tok[0], tok[1],
                                        xmlstem_rel.get('index')
                                        + "|" + xmlstem_rel.get('head')
                                        + "|" + xmlstem_rel.get('relation'))
                        tok = (a, b, c, r)
                        try:
                            for xmlpost_rel in xmlword.findall('.//mor/mor-post/gra'):
                                if not xmlpost_rel.get('type') == 'grt':    # non-gold <gra> tier
                                    a, b, c, r = tok
                                    r += '~' + (xmlpost_rel.get('index')
                                                  + "|" + xmlpost_rel.get('head')
                                                  + "|" + xmlpost_rel.get('relation'))
                                    tok = (a, b, c, r)
                                else:   # TODO: gold <gra> tier
                                    suffixStem = (suffixStem[0], suffixStem[1],
                                                  suffixStem[2], suffixStem[0],
                                                  suffixStem[1],
                                                  xmlpost_rel.get('index')
                                                  + "|" + xmlpost_rel.get('head')
                                                  + "|" + xmlpost_rel.get('relation'))
                        except:
                            pass
                    sents.append(tok[:-1] if (stem and not relation) else tok)
                if sent or relation:
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

