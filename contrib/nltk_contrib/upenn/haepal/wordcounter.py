#! /usr/bin/env python

import sys
import fcntl
import marshal
import nltk.corpus
import os.path
import string
import time             ### ADDED BY SB

class BrownCounter:
    
    def __init__(self):
        self.brown = nltk.corpus.brown
        self.groups = self.brown.groups()
        self.lockfile = 'wordcounter-lock.brown'
        if not os.path.exists(self.lockfile):
            f = open(self.lockfile,'w+b')
            marshal.dump({},f)
            f.close()

    def get_word_frequency(self, grp):

        try:
            i = self.groups.index(grp)
            resfile = "wordcounter-result.brown.group%d" % i
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
            f.close()
            while lock[grp] is None:
                time.sleep(5)
                f.seek(0)      ### SB: I/O operation on closed file
                lock = marshal.load(f)
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

            h = {}
            for item in  nltk.corpus.brown.items(grp):
                toks = nltk.corpus.brown.tokenize(item)
                for t in toks:
                    w = t['TEXT'].lower()  ### SB: fixed for NLTK 1.3
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
    browncounter = BrownCounter()

    def usage():
        print "usage: %s <group>" % os.path.basename(sys.argv[0])
        print
        print "where <group> is one of:", \
              string.join(map(lambda a:`a`, browncounter.groups), ', ')
        print
        sys.exit(1)
        
    if len(sys.argv) != 2:
        usage()

    grp = sys.argv[1]
    
    try:
        browncounter.groups.index(grp)
    except ValueError:
        print "unknown group: %s\n" % `grp`
        usage()
        
        
    freq = browncounter.get_word_frequency(grp)

    if freq is None:
        print MyBrown().groups
        sys.exit(1)

    sys.exit(0)

    #####
    keys = freq.keys()
    keys.sort()
    for k in keys:
        print "%10d %-20s" % (freq[k], k)

