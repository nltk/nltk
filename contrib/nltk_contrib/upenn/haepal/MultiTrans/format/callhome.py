
import re, string

class Callhome:
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
        
            self.add(self.Annotation(start=st, end=et,
                                     TYPE='segment',
                                     SPKR=ch[:-1],
                                     CHANNEL=ord(ch[0])-ord('A'),
                                     TEXT=text))
        file.close()

    def save(self, filename):
        print "saving", filename
        
    def add(self, seg):
        ch = seg['SPKR']
        for ann in self:
            if ann['SPKR']==ch and seg.overlaps(ann):
                raise ValueError("can't add overlapping segment: " + str(seg))
        self.AnnotationSet.add(self, seg)
