
import re, string
import codecs

###
import sys
sys.path.append("..")
from agwrap2 import *
from qt import QObject, PYSIGNAL
###

__all__ = ["Callhome", "Annotation"]


class Callhome(list,AnnotationQuery):
    def __init__(self):
        list.__init__(self)
        self._filename = None
        self.emitter = QObject()
        
    def load(self, filename):
        encoder, decoder, reader, writer = codecs.lookup("utf-8")
        file = reader(open(filename))
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
        self._filename = filename

    def save(self, filename=None):
        if filename is not None:
            self._filename = filename
        if self._filename is not None:
            f = file(self._filename, "w")
            for i,seg in enumerate(self):
                print >> f
                print >> f, seg.start, seg.end, seg['SPKR']+':', seg['TEXT']
            print >> f
        
    def add(self, seg):
        ch = seg['SPKR']
        for ann in self:
            if ann['SPKR']==ch and seg.overlaps(ann):
                raise ValueError("can't add overlapping segment: " + str(seg))
        list.append(self, seg)
        self.sort(lambda a,b:cmp(a.start,b.start))
        seg.setCallback(self._agwrapCallback)
        seg.setCallback2(self._agwrapCallback2)
        i = self.index(seg)
        self.emitter.emit(PYSIGNAL("annotationAdded(Annotation,int)"),(seg,i))

    def insert(self, i, seg):
        list.insert(self, i, seg)
        self.emitter.emit(PYSIGNAL("annotationAdded(Annotation,int)"),(seg,i))


    def delete(self, seg):
        if isinstance(seg,Annotation):
            i = self.index(seg)
        else:
            i = seg
            seg = self[i]
        list.__delitem__(self, i)
        self.emitter.emit(PYSIGNAL('annotationDeleted(Annotation,int)'), (seg,i))

    def new(self, c, a, b):
        return Annotation(start=a, end=b,
                          TYPE='segment',
                          SPKR=chr(ord('A')+c),
                          CHANNEL=c,
                          TEXT="")
                          

    def _agwrapCallback(self, *args):
        self.emitter.emit(PYSIGNAL("annotationChanged(args)"),(args,))
        
    def _agwrapCallback2(self, *args):
        self.emitter.emit(PYSIGNAL("annotationChanged2(args)"),(args,))


    # disabled methods

    def __delitem__(self, *args):
        pass

    def __delslice__(self, *args):
        pass

    def __add__(self, *args):
        pass
    
    def append(self, *args):
        pass

    def pop(self, *args):
        pass

    def remove(self, *args):
        pass
    
