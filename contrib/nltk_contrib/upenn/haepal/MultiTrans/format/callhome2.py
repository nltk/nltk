
import re, string

###
import sys
sys.path.append("..")
from aglite2 import *
###

__all__ = ["Callhome", "Annotation"]

class Callhome(list,AnnotationQuery):
    def load(self, filename):
        file = open(filename)
        for i,l in enumerate(file):
            a = l.split()
            if not a: continue
            try:
                st = float(a[0])
                et = float(a[1])
                ch = a[2]
                if not re.match("^[AB]1?:", ch):
                    file.close()
                    raise ValueError("channel format error at line %d" % i)
                text = string.join(a[3:])
            except ValueError:
                file.close()
                raise ValueError("time format error at line %d" % i)
            except IndexError:
                file.close()
                raise ValueError("format error at line %d" % i)
        
            self.add(Annotation(start=st, end=et,
                                TYPE='segment',
                                SPKR=ch[:-1],
                                CHANNEL=ord(ch[0])-ord('A'),
                                TEXT=text))
        file.close()
        self.sort(lambda a,b:cmp(a.start,b.start))

    def save(self, filename):
        print "saving", filename
        
    def add(self, seg):
        ch = seg['SPKR']
        for ann in self:
            if ann['SPKR']==ch and seg.overlaps(ann):
                raise ValueError("can't add overlapping segment: " + str(seg))
        self.append(seg)
        self.sort(lambda a,b:cmp(a.start,b.start))

    def new(self, c, a, b):
        return Annotation(start=a, end=b,
                          TYPE='segment',
                          SPKR=chr(ord('A')+c),
                          CHANNEL=c,
                          TEXT="")
                          
                          
