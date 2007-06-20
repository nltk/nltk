# Natural Language Toolkit: TIMIT Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Haejoong Lee <haejoong@ldc.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens, phonemes and audio data from the NLTK TIMIT Corpus.

This corpus contains selected portion of the TIMIT corpus.

* 16 speakers from 8 dialect regions
* 1 male and 1 female from each dialect region
* total 130 sentences (10 sentences per speaker.  Note that some
  sentences are shared among other speakers, especially sa1 and sa2
  are spoken by all speakers.)
* total 160 recording of sentences (10 recordings per speaker)
* audio format: NIST Sphere, single channel, 16kHz sampling,
  16 bit sample, PCM encoding


Module contents
---------------

The timit module provides 4 functions and 4 data items.

* items

  List of items in the corpus.  There are total 160 items, each of which
  corresponds to a unique utterance of a speaker.  Here's an example of an
  item in the list:

      dr1-fvmh0:sx206
        - _----  _---
        | |  |   | |
        | |  |   | |
        | |  |   | `--- sentence number
        | |  |   `----- sentence type (a:all, i:shared, x:exclusive)
        | |  `--------- speaker ID
        | `------------ sex (m:male, f:female)
        `-------------- dialect region (1..8)

* speakers

  List of speaker IDs.  An example of speaker ID:

      dr1-fvmh0

  Note that if you split an item ID with colon and take the first element of
  the result, you will get a speaker ID.

      >>> itemid = dr1-fvmh0:sx206
      >>> spkrid,sentid = itemid.split(':')
      >>> spkrid
      'dr1-fvmh0'
      
  The second element of the result is a sentence ID.
  
* dictionary()

  Phonetic dictionary of words contained in this corpus.  This is a Python
  dictionary from words to phoneme lists.
  
* spkrinfo()

  Speaker information table.  It's a Python dictionary from speaker IDs to
  records of 10 fields.  Speaker IDs the same as the ones in timie.speakers.
  Each record is a dictionary from field names to values, and the fields are
  as follows:

    id         speaker ID as defined in the original TIMIT speaker info table
    sex        speaker gender (M:male, F:female)
    dr         speaker dialect region (1:new england, 2:northern,
               3:north midland, 4:south midland, 5:southern, 6:new york city,
               7:western, 8:army brat (moved around))
    use        corpus type (TRN:training, TST:test)
               in this sample corpus only TRN is available
    recdate    recording date
    birthdate  speaker birth date
    ht         speaker height
    race       speaker race (WHT:white, BLK:black, AMR:american indian,
               SPN:spanish-american, ORN:oriental,???:unknown)
    edu        speaker education level (HS:high school, AS:associate degree,
               BS:bachelor's degree (BS or BA), MS:master's degree (MS or MA),
               PHD:doctorate degree (PhD,JD,MD), ??:unknown)
    comments   comments by the recorder
  
The 4 functions are as follows.

* raw(sentences=items, offset=False)

  Given a list of items, returns an iterator of a list of word lists,
  each of which corresponds to an item (sentence).  If offset is set to True,
  each element of the word list is a tuple of word(string), start offset and
  end offset, where offset is represented as a number of 16kHz samples.
    
* phonetic(sentences=items, offset=False)

  Given a list of items, returns an iterator of a list of phoneme lists,
  each of which corresponds to an item (sentence).  If offset is set to True,
  each element of the phoneme list is a tuple of word(string), start offset
  and end offset, where offset is represented as a number of 16kHz samples.

* audiodata(item, start=0, end=None)

  Given an item, returns a chunk of audio samples formatted into a string.
  When the fuction is called, if start and end are omitted, the entire
  samples of the recording will be returned.  If only end is omitted,
  samples from the start offset to the end of the recording will be returned.

* play(data)

  Play the given audio samples. The audio samples can be obtained from the
  timit.audiodata function.

"""       

from util import *
from nltk import tokenize
from itertools import islice
import sys, os, re

if sys.platform.startswith('linux') or sys.platform.startswith('freebsd'):
    PLAY_ENABLED = True
else:
    PLAY_ENABLED = False

__all__ = ["items", "raw", "phonetic", "speakers", "dictionary", "spkrinfo",
           "audiodata", "play"]

PREFIX = find_corpus('timit')

# speakers = []
# items = []
# for f in os.listdir(PREFIX):
#     if re.match("^dr[0-9]-[a-z]{4}[0-9]$", f):
#         speakers.append(f)
#         for g in os.listdir(os.path.join(PREFIX,f)):
#             if g.endswith(".txt"):
#                 items.append(f+':'+g[:-4])
# speakers.sort()
# items.sort()

documents = {
    'dr1-fvmh0': [
        'dr1-fvmh0:sa1', 'dr1-fvmh0:sa2', 'dr1-fvmh0:si1466',
        'dr1-fvmh0:si2096', 'dr1-fvmh0:si836', 'dr1-fvmh0:sx116',
        'dr1-fvmh0:sx206', 'dr1-fvmh0:sx26', 'dr1-fvmh0:sx296',
        'dr1-fvmh0:sx386'],
    'dr1-mcpm0': [
        'dr1-mcpm0:sa1', 'dr1-mcpm0:sa2',
        'dr1-mcpm0:si1194', 'dr1-mcpm0:si1824', 'dr1-mcpm0:si564',
        'dr1-mcpm0:sx114', 'dr1-mcpm0:sx204', 'dr1-mcpm0:sx24',
        'dr1-mcpm0:sx294', 'dr1-mcpm0:sx384'],
    'dr2-faem0': [
        'dr2-faem0:sa1', 'dr2-faem0:sa2', 'dr2-faem0:si1392',
        'dr2-faem0:si2022', 'dr2-faem0:si762', 'dr2-faem0:sx132',
        'dr2-faem0:sx222',
        'dr2-faem0:sx312', 'dr2-faem0:sx402', 'dr2-faem0:sx42'],
    'dr2-marc0': [
        'dr2-marc0:sa1', 'dr2-marc0:sa2', 'dr2-marc0:si1188',
        'dr2-marc0:si1818', 'dr2-marc0:si558', 'dr2-marc0:sx108',
        'dr2-marc0:sx18', 'dr2-marc0:sx198', 'dr2-marc0:sx288',
        'dr2-marc0:sx378'],
    'dr3-falk0': [
        'dr3-falk0:sa1', 'dr3-falk0:sa2',
        'dr3-falk0:si1086', 'dr3-falk0:si456', 'dr3-falk0:si658',
        'dr3-falk0:sx186', 'dr3-falk0:sx276', 'dr3-falk0:sx366',
        'dr3-falk0:sx6', 'dr3-falk0:sx96'],
    'dr3-madc0': [
        'dr3-madc0:sa1', 'dr3-madc0:sa2',
        'dr3-madc0:si1367', 'dr3-madc0:si1997', 'dr3-madc0:si737',
        'dr3-madc0:sx107', 'dr3-madc0:sx17', 'dr3-madc0:sx197',
        'dr3-madc0:sx287', 'dr3-madc0:sx377'],
    'dr4-falr0': [
        'dr4-falr0:sa1',
        'dr4-falr0:sa2', 'dr4-falr0:si1325', 'dr4-falr0:si1955',
        'dr4-falr0:si695', 'dr4-falr0:sx155', 'dr4-falr0:sx245',
        'dr4-falr0:sx335', 'dr4-falr0:sx425', 'dr4-falr0:sx65'],
    'dr4-maeb0': [
        'dr4-maeb0:sa1', 'dr4-maeb0:sa2', 'dr4-maeb0:si1411',
        'dr4-maeb0:si2250', 'dr4-maeb0:si990', 'dr4-maeb0:sx180',
        'dr4-maeb0:sx270', 'dr4-maeb0:sx360', 'dr4-maeb0:sx450',
        'dr4-maeb0:sx90'],
    'dr5-ftlg0': [
        'dr5-ftlg0:sa1', 'dr5-ftlg0:sa2',
        'dr5-ftlg0:si1743', 'dr5-ftlg0:si483', 'dr5-ftlg0:si840',
        'dr5-ftlg0:sx123', 'dr5-ftlg0:sx213', 'dr5-ftlg0:sx303',
        'dr5-ftlg0:sx33', 'dr5-ftlg0:sx393'],
    'dr5-mbgt0': [
        'dr5-mbgt0:sa1', 'dr5-mbgt0:sa2',
        'dr5-mbgt0:si1341', 'dr5-mbgt0:si1841', 'dr5-mbgt0:si711',
        'dr5-mbgt0:sx171', 'dr5-mbgt0:sx261', 'dr5-mbgt0:sx351',
        'dr5-mbgt0:sx441', 'dr5-mbgt0:sx81'],
    'dr6-fapb0': [
        'dr6-fapb0:sa1', 'dr6-fapb0:sa2',
        'dr6-fapb0:si1063', 'dr6-fapb0:si1693', 'dr6-fapb0:si2323',
        'dr6-fapb0:sx163', 'dr6-fapb0:sx253', 'dr6-fapb0:sx343',
        'dr6-fapb0:sx433', 'dr6-fapb0:sx73'],
    'dr6-mbma1': [
        'dr6-mbma1:sa1', 'dr6-mbma1:sa2',
        'dr6-mbma1:si2207', 'dr6-mbma1:si2214', 'dr6-mbma1:si954',
        'dr6-mbma1:sx144', 'dr6-mbma1:sx234', 'dr6-mbma1:sx324',
        'dr6-mbma1:sx414', 'dr6-mbma1:sx54'],
    'dr7-fblv0': [
        'dr7-fblv0:sa1', 'dr7-fblv0:sa2',
        'dr7-fblv0:si1058', 'dr7-fblv0:si1688', 'dr7-fblv0:si2318',
        'dr7-fblv0:sx158', 'dr7-fblv0:sx248', 'dr7-fblv0:sx338',
        'dr7-fblv0:sx428', 'dr7-fblv0:sx68'],
    'dr7-madd0': [
        'dr7-madd0:sa1', 'dr7-madd0:sa2',
        'dr7-madd0:si1295', 'dr7-madd0:si1798', 'dr7-madd0:si538',
        'dr7-madd0:sx178', 'dr7-madd0:sx268', 'dr7-madd0:sx358',
        'dr7-madd0:sx448', 'dr7-madd0:sx88'],
    'dr8-fbcg1': [
        'dr8-fbcg1:sa1', 'dr8-fbcg1:sa2',
        'dr8-fbcg1:si1612', 'dr8-fbcg1:si2242', 'dr8-fbcg1:si982',
        'dr8-fbcg1:sx172', 'dr8-fbcg1:sx262', 'dr8-fbcg1:sx352',
        'dr8-fbcg1:sx442', 'dr8-fbcg1:sx82'],
    'dr8-mbcg0': [
        'dr8-mbcg0:sa1', 'dr8-mbcg0:sa2',
        'dr8-mbcg0:si2217', 'dr8-mbcg0:si486', 'dr8-mbcg0:si957',
        'dr8-mbcg0:sx147', 'dr8-mbcg0:sx237', 'dr8-mbcg0:sx327',
        'dr8-mbcg0:sx417', 'dr8-mbcg0:sx57'],
    }

speakers = sorted(documents.keys())

items =  reduce(lambda a,b:a.union(b), documents.values(), set())

# read dictionary
def dictionary():
    d = {}
    path = os.path.join(PREFIX,"timitdic.txt")
    f = open_corpus(path)
    for l in f:
        if l[0] == ';': continue
        a = l.strip().split('  ')
        d[a[0]] = a[1].strip('/').split()
    return d

# read spkrinfo
def spkrinfo():
    spkrinfo = {}
    header = ['id','sex','dr','use','recdate','birthdate','ht','race','edu', 'comments']
    path = os.path.join(PREFIX,"spkrinfo.txt")
    f = open_corpus(path)
    for l in f:
        if l[0] == ';': continue
        rec = l[:54].split() + [l[54:].strip()]
        key = "dr%s-%s%s" % (rec[2],rec[1].lower(),rec[0].lower())
        spkrinfo[key] = dict((header[i],rec[i]) for i in range(10))
    return spkrinfo

def _prim(ext, sentences=items, offset=False):
    if isinstance(sentences,str):
        sentences = [sentences]
    for sent in sentences:
        fnam = os.path.sep.join([PREFIX] + sent.split(':')) + ext
        r = []
        for l in open(fnam):
            if not l.strip(): continue
            a = l.split()
            if offset:
                r.append((a[2],int(a[0]),int(a[1])))
            else:
                r.append(a[2])
        yield r

def raw(sentences=items, offset=False):
    """
    Given a list of items, returns an iterator of a list of word lists,
    each of which corresponds to an item (sentence).  If offset is set to True,
    each element of the word list is a tuple of word(string), start offset and
    end offset, where offset is represented as a number of 16kHz samples.
    
    @param sentences: List of items (sentences) for which tokenized word list
    will be returned.  In case there is only one item, it is possible to
    pass the item id as a string.
    @type sentences: list of strings or a string
    @param offset: If True, the start and end offsets are accompanied to each
    word in the returned list.  Note that here, an offset is represented by
    the number of 16kHz samples.
    @type offset: bool
    @return: List of list of strings (words) if offset is False. List of list
    of tuples (word, start offset, end offset) if offset if True.
    """
    return _prim(".wrd", sentences, offset)

    
def phonetic(sentences=items, offset=False):
    """
    Given a list of items, returns an iterator of a list of phoneme lists,
    each of which corresponds to an item (sentence).  If offset is set to True,
    each element of the phoneme list is a tuple of word(string), start offset
    and end offset, where offset is represented as a number of 16kHz samples.
    
    @param sentences: List of items (sentences) for which phoneme list
    will be returned.  In case there is only one item, it is possible to
    pass the item id as a string.
    @type sentences: list of strings or a string
    @param offset: If True, the start and end offsets are accompanied to each
    phoneme in the returned list.  Note that here, an offset is represented by
    the number of 16kHz samples.
    @type offset: bool
    @return: List of list of strings (phonemes) if offset is False. List of
    list of tuples (phoneme, start offset, end offset) if offset if True.
    """
    return _prim(".phn", sentences, offset)

def audiodata(item, start=0, end=None):
    """
    Given an item, returns a chunk of audio samples formatted into a string.
    When the fuction is called, if start and end are omitted, the entire
    samples of the recording will be returned.  If only end is omitted,
    samples from the start offset to the end of the recording will be returned.
    
    @param start: start offset
    @type start: integer (number of 16kHz frames)
    @param end: end offset
    @type end: integer (number of 16kHz frames) or None to indicate
    the end of file
    @return: string of sequence of bytes of audio samples
    """
    assert(end is None or end > start)
    headersize = 44
    fnam = os.path.join(PREFIX,item.replace(':',os.path.sep)) + '.wav'
    if end is None:
        data = open(fnam).read()
    else:
        data = open(fnam).read(headersize+end*2)
    return data[headersize+start*2:]

def play(data):
    """
    Play the given audio samples.
    
    @param data: audio samples
    @type data: string of bytes of audio samples
    """
    if not PLAY_ENABLED:
        print >>sys.stderr, "sorry, currently we don't support audio playback on this platform:", sys.platform
        return

    import ossaudiodev
    try:
        dsp = ossaudiodev.open('w')
    except IOError, e:
        print >>sys.stderr, "can't acquire the audio device; please activate your audio device."
        print >>sys.stderr, "system error message:", str(e)
        return
    
    dsp.setfmt(ossaudiodev.AFMT_S16_LE)
    dsp.channels(1)
    dsp.speed(16000)
    dsp.write(data)
    dsp.close()
    
def demo():
    from nltk.corpora import timit
    import time

    print "6th item (timit.items[5])"
    print "-------------------------"
    itemid = timit.items[5]
    spkrid, sentid = itemid.split(':')
    print "  item id:    ", itemid
    print "  speaker id: ", spkrid
    print "  sentence id:", sentid
    print
    record = timit.spkrinfo()[spkrid]
    print "  speaker information:"
    print "    TIMIT speaker id: ", record['id']
    print "    speaker sex:      ", record['sex']
    print "    dialect region:   ", record['dr']
    print "    data type:        ", record['use']
    print "    recording date:   ", record['recdate']
    print "    date of birth:    ", record['birthdate']
    print "    speaker height:   ", record['ht']
    print "    speaker race:     ", record['race']
    print "    speaker education:", record['edu']
    print "    comments:         ", record['comments']
    print

    print "  words of the sentence:"
    print "   ", timit.raw(sentences=itemid).next()
    print

    print "  words of the sentence with offsets (first 3):"
    print "   ", timit.raw(sentences=itemid, offset=True).next()[:3]
    print
    
    print "  phonemes of the sentence (first 10):"
    print "   ", timit.phonetic(sentences=itemid).next()[:10]
    print
    
    print "  phonemes of the sentence with offsets (first 3):"
    print "   ", timit.phonetic(sentences=itemid, offset=True).next()[:3]
    print
    
    print "  looking up dictionary for words of the sentence..."
    words = timit.raw(sentences=itemid).next()
    dictionary = timit.dictionary()
    for word in words:
        print "    %-5s:" % word, dictionary[word]
    print


    print "audio playback:"
    print "---------------"
    print "  playing sentence", sentid, "by speaker", spkrid, "(a.k.a. %s)"%record["id"], "..."
    data = timit.audiodata(itemid)
    timit.play(data)
    print
    print "  playing words:"
    words = timit.raw(sentences=itemid, offset=True).next()
    for word, start, end in words:
        print "    playing %-10s in 1.5 seconds ..." % `word`
        time.sleep(1.5)
        data = timit.audiodata(itemid, start, end)
        timit.play(data)
    print
    print "  playing phonemes (first 10):"
    phones = timit.phonetic(sentences=itemid, offset=True).next()
    for phone, start, end in phones[:10]:
        print "    playing %-10s in 1.5 seconds ..." % `phone`
        time.sleep(1.5)
        data = timit.audiodata(itemid, start, end)
        timit.play(data)
    print
    
    # play sentence sa1 of all female speakers
    sentid = 'sa1'
    spkrinfo = timit.spkrinfo()
    for spkr in timit.speakers:
        if spkrinfo[spkr]['sex'] == 'F':
            itemid = spkr + ':' + sentid
            print "  playing sentence %s of speaker %s ..." % (sentid, spkr)
            data = timit.audiodata(itemid)
            timit.play(data)
    print
    
if __name__ == '__main__':
    demo()

