"""
This is an interface to aglite.py (data model module), used by GUI components.

Annotation wraps aglite.Annotation to add interactivity, i.e. the a user-
defined callback function (set by Annotation.setCallback) will be called
whenever the contents of annotation is changed.

This is a way of monitoring changes in the data. which is useful for GUI
components.
"""

import aglite


class Annotation(aglite.Annotation, object):

    __slots__ = ()

    def __init__(self, propdict=None, start=None, end=None, **kw):
        aglite.Annotation.__init__(self, propdict, start, end, **kw)

    def __setitem__(self, k, v):
        aglite.Annotation.__setitem__(self, k, v)
        if Annotation.changeCallback:
            Annotation.changeCallback.__call__(self)
        
    def setStart(self, v):
        aglite.Annotation.setStart(self, v)
        if Annotation.changeCallback:
            Annotation.changeCallback.__call__(self)

    def setEnd(self, v):
        aglite.Annotation.setEnd(self, v)
        if Annotation.changeCallback:
            Annotation.changeCallback.__call__(self)

    def setCallback(f=None):
        Annotation.changeCallback = f
    setCallback = staticmethod(setCallback)
    
    start = property(aglite.Annotation.getStart, setStart)
    end = property(aglite.Annotation.getEnd, setEnd)
    changeCallback = None


class AnnotationSet(aglite.AnnotationSet):

    __slots__ = ()

    def add(self, ann):
        r = aglite.AnnotationSet.add(self, ann)
        if AnnotationSet.addCallback:
            AnnotationSet.addCallback.__call__(ann)
        return r

    def remove(self, ann):
        r = aglite.AnnotationSet.remove(self, ann)
        if AnnotationSet.removeCallback:
            AnnotationSet.removeCallback.__call__(r)
        return r
        
    def setCallback(addf=None, remf=None):
        """
        addf - called when adding annotation
        remf - called when deleting annotation
        """
        AnnotationSet.addCallback = addf
        AnnotationSet.removeCallback = remf
    setCallback = staticmethod(setCallback)

    addCallback = None
    removeCallback = None

    
if __name__ == "__main__":
    def callback(x):
        print x

    Annotation.setCallback(callback)
    a = Annotation()
    a['text'] = 'bar'
    a.start, a.end = 1.0, 2.0
    print a

    AnnotationSet.setCallback(callback, callback)
    annset = AnnotationSet()
    print "***"
    id = annset.add(a)
    print annset
    annset.remove(id)
    print annset
