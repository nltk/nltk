# CHILDES XML Corpus Reader

# Copyright (C) 2001-2012 NLTK Project
# Author: Tomonori Nagano <tnagano@gc.cuny.edu>
#         Alexis Dimitriadis <A.Dimitriadis@uu.nl>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for the XML version of the CHILDES corpus.
"""
__docformat__ = 'epytext en'

import re
from collections import defaultdict

from nltk.util import flatten

from nltk.corpus.reader.util import concat
from xmldocs import XMLCorpusReader, ElementTree

# to resolve the namespace issue
NS = 'http://www.talkbank.org/ns/talkbank'

class CHILDESCorpusReader(XMLCorpusReader):
    """
    Corpus reader for the XML version of the CHILDES corpus.
    The CHILDES corpus is available at ``http://childes.psy.cmu.edu/``. The XML
    version of CHILDES is located at ``http://childes.psy.cmu.edu/data-xml/``.
    Copy the CHILDES XML corpus (at the moment, this CorpusReader
    supports only English corpora at ``http://childes.psy.cmu.edu/data-xml/Eng-USA/``)
    into the NLTK data directory (``nltk_data/corpora/CHILDES/``).
    For access to simple word lists and tagged word lists, use
    ``words()`` and ``sents()``.
    """
    def __init__(self, root, fileids, lazy=True):
        XMLCorpusReader.__init__(self, root, fileids)
        self._lazy = lazy

    def words(self, fileids=None, speaker='ALL', sent=None, stem=False,
            relation=False, pos=False, strip_space=True, replace=False):
        """
        :return: the given file(s) as a list of words
        :rtype: list(str)

        :param speaker: If list is specified, select specitic speakers defined
        	in the corpus. Default is 'All' (all participants). Common choices
        	are ['CHI'] (all children), ['MOT'] (mothers), ['CHI','MOT'] (exclude
        	researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        return concat([self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace) for fileid in self.abspaths(fileids)])

    def tagged_words(self, fileids=None, speaker='ALL', sent=None, stem=False,
            relation=False, pos=True, strip_space=True, replace=False):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))

        :param speaker: If list is specified, select specitic speakers defined
        	in the corpus. Default is 'All' (all participants). Common choices
        	are ['CHI'] (all children), ['MOT'] (mothers), ['CHI','MOT'] (exclude
        	researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        return concat([self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace) for fileid in self.abspaths(fileids)])

    def sents(self, fileids=None, speaker='ALL', sent=True, stem=False,
            relation=None, pos=False, strip_space=True, replace=False):
        """
        :return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        :rtype: list(list(str))

        :param speaker: If list is specified, select specitic speakers defined
        	in the corpus. Default is 'All' (all participants). Common choices
        	are ['CHI'] (all children), ['MOT'] (mothers), ['CHI','MOT'] (exclude
        	researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return tuples of
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        return concat([self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace) for fileid in self.abspaths(fileids)])

    def tagged_sents(self, fileids=None, speaker='ALL', sent=True, stem=False,
            relation=None, pos=True, strip_space=True, replace=False):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.
        :rtype: list(list(tuple(str,str)))

        :param speaker: If list is specified, select specitic speakers defined
        	in the corpus. Default is 'All' (all participants). Common choices
        	are ['CHI'] (all children), ['MOT'] (mothers), ['CHI','MOT'] (exclude
        	researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return tuples of
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        return concat([self._get_words(fileid, speaker, sent, stem, relation,
            pos, strip_space, replace) for fileid in self.abspaths(fileids)])

    def corpus(self, fileids=None):
        """
        :return: the given file(s) as a dict of ``(corpus_property_key, value)``
        :rtype: list(dict)
        """
        return [self._get_corpus(fileid) for fileid in self.abspaths(fileids)]

    def _get_corpus(self, fileid):
        results = dict()
        xmldoc = ElementTree.parse(fileid).getroot()
        for key, value in xmldoc.items():
            results[key] = value
        return results

    def participants(self, fileids=None):
        """
        :return: the given file(s) as a dict of ``(participant_propperty_key, value)``
        :rtype: list(dict)
        """
        return [self._get_participants(fileid)
                            for fileid in self.abspaths(fileids)]

    def _get_participants(self, fileid):
        # multidimensional dicts
        def dictOfDicts():
            return defaultdict(dictOfDicts)

        xmldoc = ElementTree.parse(fileid).getroot()
        # getting participants' data
        pat = dictOfDicts()
        for participant in xmldoc.findall('.//{%s}Participants/{%s}participant' % (NS,NS)):
            for (key,value) in participant.items():
                pat[participant.get('id')][key] = value
        return pat

    def age(self, fileids=None, month=False):
        """
        :return: the given file(s) as string or int
        :rtype: list or int

        :param month: If true, return months instead of year-month-date
        """
        return [self._get_age(fileid,month) for fileid in self.abspaths(fileids)]

    def _get_age(self, fileid, month):
        xmldoc = ElementTree.parse(fileid).getroot()
        for pat in xmldoc.findall('.//{%s}Participants/{%s}participant' % (NS,NS)):
            try:
                if pat.get('id') == 'CHI':
                    age = pat.get('age')
                    if month:
                        age = self._convert_age(age)
                    return age
            # some files don't have age data
            except (TypeError, AttributeError), e:
                return None

    def _convert_age(self, age_year):
        m = re.match("P(\d+)Y(\d+)M?(\d?\d?)D?",age_year)
        age_month = int(m.group(1))*12 + int(m.group(2))
        try:
            if int(m.group(3)) > 15:
                age_month += 1
        # some corpora don't have age information?
        except ValueError, e:
            pass
        return age_month

    def MLU(self, fileids=None):
        """
        :return: the given file(s) as a floating number
        :rtype: list(float)
        """
        return [self._getMLU(fileid) for fileid in self.abspaths(fileids)]

    def _getMLU(self, fileid):
        sents = self._get_words(fileid, speaker=['CHI'], sent=True, stem=True,
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
            # count number of morphemes (e.g., 'read' = 1 morpheme but 'read-PAST' is 2 morphemes)
            numWords = float(len(flatten([word.split('-') for word in thisWordList]))) - numFillers
            numSents = float(len(results)) - sentDiscount
            mlu = numWords/numSents
        except ZeroDivisionError:
            mlu = 0
        # return {'mlu':mlu,'wordNum':numWords,'sentNum':numSents}
        return mlu

    def _get_words(self, fileid, speaker, sent, stem, relation, pos,
            strip_space, replace):
        xmldoc = ElementTree.parse(fileid).getroot()
        # processing each xml doc
        results = []
        for xmlsent in xmldoc.findall('.//{%s}u' % NS):
            sents = []
            # select speakers
            if speaker == 'ALL' or xmlsent.get('who') in speaker:
                for xmlword in xmlsent.findall('.//{%s}w' % NS):
                    infl = None ; suffixStem = None
                    # getting replaced words
                    if replace and xmlsent.find('.//{%s}w/{%s}replacement' % (NS,NS)):
                        xmlword = xmlsent.find('.//{%s}w/{%s}replacement/{%s}w' % (NS,NS,NS))
                    elif replace and xmlsent.find('.//{%s}w/{%s}wk' % (NS,NS)):
                        xmlword = xmlsent.find('.//{%s}w/{%s}wk' % (NS,NS))
                    # get text
                    if xmlword.text:
                        word = xmlword.text
                    else:
                        word = ''
                    # strip tailing space
                    if strip_space:
                        word = word.strip()
                    # stem
                    if relation or stem:
                        try:
                            xmlstem = xmlword.find('.//{%s}stem' % NS)
                            word = xmlstem.text
                        except AttributeError, e:
                            pass
                        # if there is an inflection
                        try:
                            xmlinfl = xmlword.find('.//{%s}mor/{%s}mw/{%s}mk' % (NS,NS,NS))
                            word += '-' + xmlinfl.text
                        except:
                            pass
                        # if there is a suffix
                        try:
                            xmlsuffix = xmlword.find('.//{%s}mor/{%s}mor-post/{%s}mw/{%s}stem' % (NS,NS,NS,NS))
                            suffixStem = xmlsuffix.text
                        except AttributeError:
                            suffixStem = ""
                    # pos
                    if relation or pos:
                        try:
                            xmlpos = xmlword.findall(".//{%s}c" % NS)
                            word = (word,xmlpos[0].text)
                            if len(xmlpos) != 1 and suffixStem:
                                suffixStem = (suffixStem,xmlpos[1].text)
                        except (AttributeError,IndexError), e:
                            word = (word,None)
                            if suffixStem:
                                suffixStem = (suffixStem,None)
                    # relational
                    # the gold standard is stored in <mor></mor><mor type="trn"><gra type="grt">
                    if relation == True:
                        for xmlstem_rel in xmlword.findall('.//{%s}mor/{%s}gra' % (NS,NS)):
                            if not xmlstem_rel.get('type') == 'grt':
                                word = (word[0],word[1],xmlstem_rel.get('index')+"|"+xmlstem_rel.get('head')+
                                        "|"+xmlstem_rel.get('relation'))
                            else:
                                word = (word[0],word[1],word[2],word[0],word[1],xmlstem_rel.get('index')+"|"+
                                        xmlstem_rel.get('head')+"|"+xmlstem_rel.get('relation'))
                        try:
                            for xmlpost_rel in xmlword.findall('.//{%s}mor/{%s}mor-post/{%s}gra' % (NS,NS,NS)):
                                if not xmlpost_rel.get('type') == 'grt':
                                    suffixStem = (suffixStem[0],suffixStem[1],xmlpost_rel.get('index')+"|"+xmlpost_rel.get('head')+
                                        "|"+xmlpost_rel.get('relation'))
                                else:
                                    suffixStem = (suffixStem[0],suffixStem[1],suffixStem[2],suffixStem[0],suffixStem[1],xmlpost_rel.get('index')+"|"+xmlpost_rel.get('head')+
                                        "|"+xmlpost_rel.get('relation'))
                        except:
                            pass
                    sents.append(word)
                    if suffixStem:
                        sents.append(suffixStem)
                if sent or relation:
                    results.append(sents)
                else:
                    results.extend(sents)
        return results


def demo():
    """
    The CHILDES corpus should be manually downloaded and saved
    to ``[NLTK_Data_Dir]/corpora/childes/``
    """
    from nltk.data import find
    #import urllib2, zipfile, cStringIO

    try:
        corpus_root = find('corpora/childes/data-xml/Eng-USA/')
        childes = CHILDESCorpusReader(corpus_root, u'.*.xml')
        # describe all corpus
        for file in childes.fileids()[:5]:
            corpus = ''
            corpus_id = ''
            for (key,value) in childes.corpus(file)[0].items():
                if key == "Corpus": corpus = value
                if key == "Id": corpus_id = value
            print 'Reading', corpus,corpus_id,' .....'
            print "words:", childes.words(file)[:7],"..."
            print "words with replaced words:", childes.words(file, replace=True)[:7]," ..."
            print "words with pos tags:", childes.tagged_words(file)[:7]," ..."
            print "words (only MOT):", childes.words(file, speaker=['MOT'])[:7], "..."
            print "words (only CHI):", childes.words(file, speaker=['CHI'])[:7], "..."
            print "stemmed words:", childes.words(file, stem=True)[:7]," ..."
            print "words with relations and pos-tag:", childes.words(file, relation=True)[:5]," ..."
            print "sentence:", childes.sents(file)[:2]," ..."
            for (participant, values) in childes.participants(file)[0].items():
                    for (key, value) in values.items():
                        print "\tparticipant", participant, key, ":", value
            print "num of sent:", len(childes.sents(file))
            print "num of morphemes:", len(childes.words(file, stem=True))
            print "age:", childes.age(file)
            print "age in month:", childes.age(file, month=True)
            print "MLU:", childes.MLU(file)
            print '\r'
    except LookupError, e:
        print """The CHILDES corpus should be manually downloaded from
        http://childes.psy.cmu.edu/data-xml/Eng-USA/ and save it at
        [NLTK_Data_Dir]/corpora/childes/"""
        #corpus_root_http = urllib2.urlopen('http://childes.psy.cmu.edu/data-xml/Eng-USA/Bates.zip')
        #corpus_root_http_bates = zipfile.ZipFile(cStringIO.StringIO(corpus_root_http.read()))
        ##this fails
        #childes = CHILDESCorpusReader(corpus_root_http_bates,corpus_root_http_bates.namelist())


if __name__ == "__main__":
    demo()
