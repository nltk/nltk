#! /usr/bin/env python

import sys
import fcntl
import marshal
import nltk.corpus
import os
import os.path
import string
import time
import gzip

class GzipSimpleCorpusReader(nltk.corpus.SimpleCorpusReader):
    def __init__(self,
                 # Basic Information
                 name, rootdir, items_regexp,
                 # Grouping
                 groups=None):

        nltk.corpus.SimpleCorpusReader.__init__(
            self,
            name, rootdir, items_regexp,
            groups)

    def open(self, item):
        self._initialize()
        return gzip.open(self.path(item))


class GigawordCounter:
    
    def __init__(self):
        gigaword_path = os.getenv("LDC_GIGAWORD")
        nltk.corpus.set_basedir(gigaword_path)
        self.brown = GzipSimpleCorpusReader("gigaword_eng","gigaword_eng", ".*\.gz")
        self.groups = self.brown.items()
        self.lockfile = 'wordcounter-lock.gigaword'
        if not os.path.exists(self.lockfile):
            f = open(self.lockfile,'w+b')
            marshal.dump({},f)
            f.close()

    def get_word_frequency(self, grps):

        h = {}

        for grp in grps:
            try:
                i = self.groups.index(grp)
                resfile = "wordcounter-result.gigaword.group%d" % i
            except ValueError:
                return None

            f = open(self.lockfile,'r+b')
            fcntl.lockf(f.fileno(),fcntl.LOCK_EX)
            lock = marshal.load(f)
            #print lock
            if lock.has_key(grp):
                # release lock
                # it's already been calculated
                # or it's being calculated
                fcntl.lockf(f.fileno(),fcntl.LOCK_UN)
                while lock[grp] is None:
                    time.sleep(5)
                    f.seek(0)
                    lock = marshal.load(f)
                f.close()
                f = open(resfile, 'rb')
                h = marshal.load(f)
                f.close()
            else:
                # update the lock file
                lock[grp] = None   # meaning "in progress"
                f.truncate()
                f.seek(0)
                marshal.dump(lock, f)

                # release lock
                fcntl.lockf(f.fileno(),fcntl.LOCK_UN)
                f.close()

                for item in [grp]:
                    toks = self.brown.xtokenize(item)
                    for t in toks['SUBTOKENS']:
                        w = t['TEXT'].lower()
                        try:
                            h[w] += 1
                        except KeyError:
                            h[w] = 1

                # write the result
                f = open(resfile, 'wb')
                marshal.dump(h, f)
                f.close()

                # update the lock file (finished)
                f = open(self.lockfile,'r+b')
                fcntl.lockf(f.fileno(),fcntl.LOCK_EX)
                lock = marshal.load(f)
                lock[grp] = resfile
                f.truncate()
                f.seek(0)
                marshal.dump(lock, f)
                fcntl.lockf(f.fileno(),fcntl.LOCK_UN)
                f.close()
        
        return h


if __name__ == "__main__":
    browncounter = GigawordCounter()

    def usage():
        print "usage: %s <group,>" % os.path.basename(sys.argv[0])
        print
        print "where group is one of:", \
              string.join(map(lambda a:`a`, browncounter.groups), ', ')
        print
        sys.exit(1)
        
    if len(sys.argv) < 2:
        usage()

    grps = sys.argv[1:]

    for grp in grps:
        try:
            browncounter.groups.index(grp)
        except ValueError:
            print "unknown group: %s\n" % `grp`
            usage()
        
        
    freq = browncounter.get_word_frequency(grps)

    if freq is None:
        print MyBrown().groups
        sys.exit(1)

    sys.exit(0)

    #####
    keys = freq.keys()
    keys.sort()
    for k in keys:
        print "%10d %-20s" % (freq[k], k)

