
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


class AnnotationQuery:
    """
    Mixin for a list of Annotations
    """

    def getByFeatureName(self, name):
        """
        Retrieve annotation with the specified feature,
        no matter what the value is.
        """
        return [ann for ann in self if name in ann]
    
    def getAnnotationSet(self, *args, **kw):
        """
        The followings are used to selectively retrieve annotations
        from the annotation set:
        
        *args - contains a set of boolean functions
        **kw  - a list of feature-value pairs
        """
        r = []
        for ann in self:
            append = True
            for k,v in kw.items():
                if k not in ann or ann[k]!=v:
                    append = False
                    break
            if not append: continue
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
    
