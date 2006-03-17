# Natural Language Toolkit: TIMIT Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Haejoong Lee <haejoong@ldc.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens, phoneses and audio data from the NLTK TIMIT Corpus.

This corpus contains selected portion of the TIMIT corpus.

* 16 speakers from 8 dialect regions
* 1 male and 1 female from each dialect region
* total 130 sentences (10 sentences per speaker.  Note that some
  sentences are shared among other speakers, especially sa1 and sa2
  are spoken by all speakers.)
* total 160 recording of sentences (10 recordings per speaker)
* audio format: NIST Sphere, single channel, 16kHz sampling,
  16 bit sample, PCM encoding

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
    
__all__ = ["items", "raw", "phonetic", "speakers", "dictionary", "spkrinfo", "audiodata", "play"]

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
for l in open(os.path.join(PREFIX,"spkrinfo.txt")):
    if l[0] == ';': continue
    rec = l[:54].split() + [l[54:].strip()]
    key = "dr%s-%s%s" % (rec[2],rec[1].lower(),rec[0].lower())
    spkrinfo[key] = rec
    
def _prim(ext, sentences=items, offset=False):
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
    return _prim(".wrd", sentences, offset)

    
def phonetic(sentences=items, offset=False):
    return _prim(".phn", sentences, offset)

def audiodata(item, start=0, end=None):
    """
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

    print "sentence 5"
    print "----------"
    itemid = timit.items[5]
    spkrid, sentid = itemid.split(':')
    print "  item id:    ", itemid
    print "  speaker id: ", spkrid
    print "  sentence id:", sentid
    print
    record = timit.spkrinfo[spkrid]
    print "  speaker information:"
    print "    TIMIT speaker id: ", record[0]
    print "    speaker sex:      ", record[1]
    print "    dialect region:   ", record[2]
    print "    data type:        ", record[3]
    print "    recording date:   ", record[4]
    print "    date of birth:    ", record[5]
    print "    speaker height:   ", record[6]
    print "    speaker race:     ", record[7]
    print "    speaker education:", record[8]
    print "    comments:         ", record[9]
    print

    print "  words of the sentence:"
    print "   ", timit.raw(sentences=[itemid]).next()
    print

    print "  words of the sentence with offsets (first 3):"
    print "   ", timit.raw(sentences=[itemid], offset=True).next()[:3]
    print
    
    print "  phonemes of the sentence (first 10):"
    print "   ", timit.phonetic(sentences=[itemid]).next()[:10]
    print
    
    print "  phonemes of the sentence with offsets (first 3):"
    print "   ", timit.phonetic(sentences=[itemid], offset=True).next()[:3]
    print
    
    print "  looking up dictionary for words of the sentence..."
    words = timit.raw(sentences=[itemid]).next()
    for word in words:
        print "    %-5s:" % word, timit.dictionary[word]
    print


    print "audio playback:"
    print "---------------"
    print "  playing words:"
    words = timit.raw(sentences=[itemid], offset=True).next()
    for word, start, end in words:
        print "    playing %-10s in 1.5 seconds ..." % `word`
        time.sleep(1.5)
        data = timit.audiodata(itemid, start, end)
        timit.play(data)
    print
    print "  playing phonemes (first 10):"
    phones = timit.phonetic(sentences=[itemid], offset=True).next()
    for phone, start, end in phones[:10]:
        print "    playing %-10s in 1.5 seconds ..." % `phone`
        time.sleep(1.5)
        data = timit.audiodata(itemid, start, end)
        timit.play(data)
    
    
if __name__ == '__main__':
    demo()
