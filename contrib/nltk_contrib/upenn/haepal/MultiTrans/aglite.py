
from nltk.token import *

class Region(SpanLocation):
    __slots__ = ()
    UNIT = 's'  # seconds
        
class Annotation(Token):
    """
    Annotation is compatible with Token.
    It is automatically associated with a Location (Region, which is a
    subclass of SpanLocation, to be more specific).
    For convenience, it exports two properties: start, end.
    Here's a usage:

    >>> ann = Annotation()
    >>> ann.start = 1.23
    >>> ann.end = 1.27
    >>> ann['TEXT'] = 'foo'
    >>> print ann
    <'foo'>@[1.23:1.27s]

    Equivallently,

    >>> ann = Annotation(start=1.23, end=1.27, TEXT='foo')
    
    """
    
    __slots__ = ('id')
    
    def __init__(self, propdict=None, start=None, end=None, **kw):
        kw['LOC'] = Region(start, end)
        Token.__init__(self, propdict, **kw)

    def getStart(self):
        return self['LOC']._start
    
    def setStart(self, v):
        self['LOC']._start = v

    def getEnd(self):
        return self['LOC']._end
    
    def setEnd(self, v):
        self['LOC']._end = v

    start = property(getStart, setStart)
    end = property(getEnd, setEnd)


class AnnotationSet(object):
    """
    AnnotationSet manages a set of Annotations.
    Each annotation added to the set is assigned a unique id.
    
    """

    __slots__ = ['_list','_recycle']

    class Iterator:
        def __init__(self, annset):
            self._list = annset
            self._next = 0
        def __iter__(self):
            return self
        def next(self):
            try:
                r = self._list[self._next]
                self._next += 1
                while not r:
                    r = self._list[self._next]
                    self._next += 1
                return r
            except IndexError:
                raise StopIteration()


    def __init__(self, ival=[]):
        self._list = ival
        self._recycle = []

    def add(self, ann):
        ann.id = len(self._list)
        self._list.append(ann)
        return ann
    
    def remove(self, ann):
        if type(ann) == int:
            try:
                a = self._list[ann]
            except IndexError:
                return None
        else:
            try:
                a = self._list[ann.id]
            except ValueError:
                return None
            
        self._recycle.append(a)
        self._list[a.id] = None
        return a

    def find(self, ann):
        try:
            return self._list.index(ann)
        except:
            return None
        
    def __len__(self):
        return len(self._list)

    def __getitem__(self, i):
        try:
            return self._list[i]
        except IndexError:
            return None

    def __str__(self):
        return str([(i,a) for i,a in enumerate(self._list) if a is not None])
    
    def __iter__(self):
        return AnnotationSet.Iterator(self)


if __name__ == "__main__":
    pass

    
