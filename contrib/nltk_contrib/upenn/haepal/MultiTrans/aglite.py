
from nltk.token import *

AllAnnotationSet = []

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
    
    __slots__ = ('id', 'parent')
    
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

    def overlaps(self, ann):
        return self['LOC'].overlaps(ann['LOC'])
    
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
            r = None
            while r is None:
                if self._next >= len(self._list):
                    raise StopIteration()
                r = self._list[self._next]
                self._next += 1
            return r


    def __init__(self, ival=None):
        object.__init__(self)
        AllAnnotationSet.append(self)
        if ival is None:
            self._list = []
        else:
            self._list = ival
        self._recycle = []


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

    ##############################
    
    def add(self, ann):
        ann.id = len(self._list)
        ann.parent = self
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

    def getByFeatureName(self, name):
        """
        Retrieve annotation with the specified feature,
        no matter what the value is.
        """
        return [ann for ann in self._list \
                if name in ann]
    
    def getAnnotationSet(self, *args, **kw):
        """
        The followings are used to selectively retrieve annotations
        from the annotation set:
        
        *args - contains a set of boolean functions
        **kw  - a list of feature-value pairs
        """
        r = []
        for ann in self._list:
            if ann is None: continue
            append = True
            for k,v in kw.items():
                if k not in ann or ann[k]!=v:
                    append = False
                    break
            for f in args:
                if not f(ann):
                    append = False
                    break
            if append:
                r.append(ann)
        return r
                    
                

if __name__ == "__main__":
    a = AnnotationSet()
    a.x = 1
    
