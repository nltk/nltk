# Natural Language Toolkit: TIMIT Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Haejoong Lee <haejoong@ldc.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
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

  List of speakers.  An example:

      dr1-fvmh0

  Note that if you split an item ID with colon and take the first element of
  the result, you will get a speaker ID.

      >>> itemid = dr1-fvmh0:sx206
      >>> spkrid,sentid = itemid.split(':')
      >>> spkrid
      'dr1-fvmh0'
      
  The second element of the result is a sentence ID.
  
* dictionary

  Phonetic dictionary of words contained in this corpus.  This is a Python
  dictionary from words to phoneme lists.
  
* spkrinfo

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
  
The 4 functions are as follows are as follows.

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

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from itertools import islice
import ossaudiodev, time
import sys, os, re

if sys.platform.startswith('linux') or sys.platform.startswith('freebsd'):
    PLAY_ENABLED = True
else:
    PLAY_ENABLED = False
    
__all__ = ["items", "raw", "phonetic", "speakers", "dictionary", "spkrinfo",
           "audiodata", "play"]

PREFIX = os.path.join(get_basedir(),"timit")

speakers = []
items = []
dictionary = {}
spkrinfo = {}

for f in os.listdir(PREFIX):
    if re.match("^dr[0-9]-[a-z]{4}[0-9]$", f):
        speakers.append(f)
        for g in os.listdir(os.path.join(PREFIX,f)):
            if g.endswith(".txt"):
                items.append(f+':'+g[:-4])
speakers.sort()
items.sort()

# read dictionary
for l in open(os.path.join(PREFIX,"timitdic.txt")):
    if l[0] == ';': continue
    a = l.strip().split('  ')
    dictionary[a[0]] = a[1].strip('/').split()

# read spkrinfo
header = ['id','sex','dr','use','recdate','birthdate','ht','race','edu',
          'comments']
for l in open(os.path.join(PREFIX,"spkrinfo.txt")):
    if l[0] == ';': continue
    rec = l[:54].split() + [l[54:].strip()]
    key = "dr%s-%s%s" % (rec[2],rec[1].lower(),rec[0].lower())
    spkrinfo[key] = dict([(header[i],rec[i]) for i in range(10)])
    
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
    fnam = os.path.join(PREFIX,item.replace(':',os.path.sep)) + '.wav'
    if end is None:
        data = open(fnam).read()
    else:
        data = open(fnam).read(1024+end*2)
    return data[1024+start*2:]

def play(data):
    """
    Play the given audio samples.
    
    @param data: audio samples
    @type data: string of bytes of audio samples
    """
    if not PLAY_ENABLED:
        print >>sys.stderr, "sorry, currently we don't support audio playback on this platform:", sys.platform
        return

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
    from nltk_lite.corpora import timit

    print "6th item (timit.items[5])"
    print "-------------------------"
    itemid = timit.items[5]
    spkrid, sentid = itemid.split(':')
    print "  item id:    ", itemid
    print "  speaker id: ", spkrid
    print "  sentence id:", sentid
    print
    record = timit.spkrinfo[spkrid]
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
    for word in words:
        print "    %-5s:" % word, timit.dictionary[word]
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
    for spkr in timit.speakers:
        if timit.spkrinfo[spkr]['sex'] == 'F':
            itemid = spkr + ':' + sentid
            print "  playing sentence %s of speaker %s ..." % (sentid, spkr)
            data = timit.audiodata(itemid)
            timit.play(data)
    print
    
if __name__ == '__main__':
    demo()

