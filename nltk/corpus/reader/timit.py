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

* tokenized(sentences=items, offset=False)

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

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.tree import Tree
import sys, os, re

if sys.platform.startswith('linux') or sys.platform.startswith('freebsd'):
    PLAY_ENABLED = True
else:
    PLAY_ENABLED = False

__all__ = ["items", "raw", "phonetic", "speakers", "dictionary", "spkrinfo",
           "audiodata", "play"]

class TimitCorpusReader(CorpusReader):
    """
    Reader for the TIMIT corpus (or any other corpus with the same
    file layout and use of file formats).  The corpus root directory
    should contain the following files:
    
      - timitdic.txt: dictionary of standard transcriptions
      - spkrinfo.txt: table of speaker information
      
    In addition, the root directory should contain one subdirectory
    for each speaker, containing three files for each utterance:

      - <utterance-id>.txt: text content of utterances
      - <utterance-id>.phn: phonetic transcription of utterances
      - <utterance-id>.wav: utterance sound file
    """
    def __init__(self, root):
        """
        Construct a new TIMIT corpus reader in the given directory.
        """
        self._speakerinfo = None
        self._root = root
        self.items = tuple(find_corpus_items(root, '\w+-\w+/\w+', '.wav'))
        self.speakers = tuple(sorted(set(item.split('/')[0]
                                         for item in self.items)))

    def transcription_dict(self):
        """
        @return: A dictionary giving the 'standard' transcription for
        each word.
        """
        _transcriptions = {}
        for line in open(os.path.join(self._root, 'timitdic.txt')):
            if not line.strip() or line[0] == ';': continue
            m = re.match(r'\s*(\S+)\s+/(.*)/\s*$', line)
            if not m: raise ValueError('Bad line: %r' % line)
            _transcriptions[m.group(1)] = m.group(2).split()
        return _transcriptions

    def spkrid(self, itemid):
        return itemid.split('/')[0]

    def sentid(self, itemid):
        return itemid.split('/')[1]

    def itemid(self, spkrid, sentid):
        return '%s/%s' % (spkrid, sentid)

    def spkritems(self, speaker):
        """
        @return: A list of all utterance items associated with a given
        speaker.
        """
        return [item for item in self.items
                if item.startswith(speaker)+'/']

    def spkrinfo(self, speaker):
        """
        @return: A dictionary mapping .. something.
        """
        if speaker in self.items:
            speaker = self.spkrid(speaker)
        
        if self._speakerinfo is None:
            self._speakerinfo = {}
            for line in open(os.path.join(self._root, 'spkrinfo.txt')):
                if not line.strip() or line[0] == ';': continue
                rec = line.strip().split(None, 9)
                key = "dr%s-%s%s" % (rec[2],rec[1].lower(),rec[0].lower())
                self._speakerinfo[key] = SpeakerInfo(*rec)

        return self._speakerinfo[speaker]

    def phons(self, items=None):
        return [line.split()[-1]
                for filename in self._item_filenames(items, '.phn')
                for line in open(filename) if line.strip()]

    def phon_times(self, items=None):
        """
        offset is represented as a number of 16kHz samples!
        """
        return [(line.split()[2], int(line.split()[0]), int(line.split()[1]))
                for filename in self._item_filenames(items, '.phn')
                for line in open(filename) if line.strip()]

    def words(self, items=None):
        return [line.split()[-1]
                for filename in self._item_filenames(items, '.wrd')
                for line in open(filename) if line.strip()]

    def word_times(self, items=None):
        return [(line.split()[2], int(line.split()[0]), int(line.split()[1]))
                for filename in self._item_filenames(items, '.wrd')
                for line in open(filename) if line.strip()]

    def sents(self, items=None):
        return [[line.split()[-1]
                 for line in open(filename) if line.strip()]
                for filename in self._item_filenames(items, '.wrd')]

    def sent_times(self, items=None):
        return [(line.split(None,2)[-1].strip(),
                 int(line.split()[0]), int(line.split()[1]))
                for filename in self._item_filenames(items, '.txt')
                for line in open(filename) if line.strip()]

    def phon_trees(self, items=None):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        
        trees = []
        for item in items:
            word_times = self.word_times(item)
            phon_times = self.phon_times(item)
            sent_times = self.sent_times(item)
    
            while sent_times:
                (sent, sent_start, sent_end) = sent_times.pop(0)
                trees.append(Tree('S', []))
                while (word_times and phon_times and
                       phon_times[0][2] <= word_times[0][1]):
                    trees[-1].append(phon_times.pop(0)[0])
                while word_times and word_times[0][2] <= sent_end:
                    (word, word_start, word_end) = word_times.pop(0)
                    trees[-1].append(Tree(word, []))
                    while phon_times and phon_times[0][2] <= word_end:
                        trees[-1][-1].append(phon_times.pop(0)[0])
                while phon_times and phon_times[0][2] <= sent_end:
                    trees[-1].append(phon_times.pop(0)[0])
        return trees

    def wav(self, item):
        return open(os.path.join(self._root, item+'.wav')).read()

    def audiodata(self, item, start=0, end=None):
        assert(end is None or end > start)
        headersize = 44
        fnam = os.path.join(self._root, item+'.wav')
        if end is None:
            data = open(fnam).read()
        else:
            data = open(fnam).read(headersize+end*2)
        return data[headersize+start*2:]

    def _item_filenames(self, items, extension):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, extension))
                for item in items]

    def play(self, data):
        """
        Play the given audio samples.
        
        @param data: audio samples
        @type data: string of bytes of audio samples
        """
        if not PLAY_ENABLED:
            print >>sys.stderr, ("sorry, currently we don't support "
                                 "audio playback on this platform: %s"
                                 % sys.platform)
            return
    
        import ossaudiodev
        try:
            dsp = ossaudiodev.open('w')
        except IOError, e:
            print >>sys.stderr, ("can't acquire the audio device; please "
                                 "activate your audio device.")
            print >>sys.stderr, "system error message:", str(e)
            return
        
        dsp.setfmt(ossaudiodev.AFMT_S16_LE)
        dsp.channels(1)
        dsp.speed(16000)
        dsp.write(data)
        dsp.close()
    
class SpeakerInfo:
    def __init__(self, id, sex, dr, use, recdate, birthdate,
                 ht, race, edu, comments=None):
        self.id = id
        self.sex = sex
        self.dr = dr
        self.use = use
        self.recdate = recdate
        self.birthdate = birthdate
        self.ht = ht
        self.race = race
        self.edu = edu
        self.comments = comments

    def __repr__(self):
        args = [self.id, self.sex, self.dr, self.use, self.recdate,
                self.birthdate, self.ht, self.race, self.edu, self.comments]
        return 'SpeakerInfo(%s)' % (', '.join(['%r' % arg for arg in args]))
        
def demo(audio=True):
    from nltk.corpus import timit
    import time

    print "6th item (timit.items[5])"
    print "-------------------------"
    itemid = timit.items[5]
    print "  item id:    ", itemid
    print "  speaker id: ", timit.spkrid(itemid)
    print "  sentence id:", timit.sentid(itemid)
    print
    record = timit.spkrinfo(itemid)
    print "  speaker information:"
    print "    TIMIT speaker id: ", record.id
    print "    speaker sex:      ", record.sex
    print "    dialect region:   ", record.dr
    print "    data type:        ", record.use
    print "    recording date:   ", record.recdate
    print "    date of birth:    ", record.birthdate
    print "    speaker height:   ", record.ht
    print "    speaker race:     ", record.race
    print "    speaker education:", record.edu
    print "    comments:         ", record.comments
    print

    print "  words of the sentence:"
    print "   ", timit.words(itemid)
    print

    print "  words of the sentence with offsets (first 3):"
    print "   ", timit.word_times(itemid)[:3]
    print
    
    print "  phonemes of the sentence (first 10):"
    print "   ", timit.phons(itemid)[:10]
    print
    
    print "  phonemes of the sentence with offsets (first 3):"
    print "   ", timit.phon_times(itemid)[:3]
    print

    print "  phoneme tree:"
    for tree in timit.phon_trees(itemid):
        print tree
    

    print "  looking up dictionary for words of the sentence..."
    words = timit.words(itemid)
    dictionary = timit.transcription_dict()
    for word in words:
        print "    %-5s:" % word, dictionary[word]
    print

    if PLAY_ENABLED and audio:
        print "audio playback:"
        print "---------------"
        print "  playing sentence", timit.sentid(itemid), "by speaker",
        print timit.spkrid(itemid), "(a.k.a. %s)..." % record.id
        data = timit.audiodata(itemid)
        if audio: timit.play(data)
        print
        print "  playing words:"
        words = timit.word_times(itemid)
        for word, start, end in words:
            print "    playing %-10s in 1.5 seconds ..." % `word`
            if PLAY_ENABLED: time.sleep(1.5)
            data = timit.audiodata(itemid, start, end)
            if audio: timit.play(data)
        print
        print "  playing phonemes (first 10):"
        phones = timit.phon_times(itemid)
        for phone, start, end in phones[:10]:
            print "    playing %-10s in 1.5 seconds ..." % `phone`
            if PLAY_ENABLED: time.sleep(1.5)
            data = timit.audiodata(itemid, start, end)
            if audio: timit.play(data)
        print

        # play sentence sa1 of all female speakers
        sentid = 'sa1'
        for spkr in timit.speakers:
            if timit.spkrinfo(spkr).sex == 'F':
                itemid = timit.itemid(spkr, sentid)
                print "  playing sentence %s of speaker %s ..." % (sentid, spkr)
                data = timit.audiodata(itemid)
                if audio: timit.play(data)
        print
    
if __name__ == '__main__':
    demo()

