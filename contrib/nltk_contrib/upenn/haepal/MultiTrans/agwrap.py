"""
This is an interface to aglite.py (data model module), used by GUI components.

Annotation wraps aglite.Annotation to add interactivity, i.e. the a user-
defined callback function (set by Annotation.setCallback) will be called
whenever the contents of annotation is changed.

This is a way of monitoring changes in the data. which is useful for GUI
components.
"""

import aglite


class Annotation(aglite.Annotation):

    __slots__ = ('_changeHook', '_changeHook2')

    def __init__(self, *args, **kw):
        aglite.Annotation.__init__(self, *args, **kw)
        self._changeHook = None
        self._changeHook2 = None

    def __setitem__(self, k, v):
        if self._changeHook: self._changeHook(self, "feature", k, v)
        aglite.Annotation.__setitem__(self, k, v)
        if self._changeHook2: self._changeHook2(self, "feature", k, v)
        
    def setStart(self, v):
        if self._changeHook: self._changeHook(self, "start", v)
        aglite.Annotation.setStart(self, v)
        if self._changeHook2: self._changeHook2(self, "start", v)

    def setEnd(self, v):
        if self._changeHook: self._changeHook(self, "end", v)
        aglite.Annotation.setEnd(self, v)
        if self._changeHook2: self._changeHook2(self, "end", v)

    def setCallback(self, f):
        self._changeHook = f
    
    def setCallback2(self, f):
        self._changeHook2 = f
    
    start = property(aglite.Annotation.getStart, setStart)
    end = property(aglite.Annotation.getEnd, setEnd)


class AnnotationSet(aglite.AnnotationSet):

    __slots__ = ('_addHook','_delHook')

    def __init__(self, *args):
        aglite.AnnotationSet.__init__(self, *args)
        self._addHook = None
        self._delHook = None
        self._changeHook = None
        self._addHook2 = None
        self._delHook2 = None
        self._changeHook2 = None


    def add(self, ann):
        if self._addHook: self._addHook(ann)
        r = aglite.AnnotationSet.add(self, ann)
        ann.setCallback(self._changeHook)
        ann.setCallback2(self._changeHook2)
        if self._addHook2: self._addHook2(ann)
        return r

    def remove(self, ann):
        if self._delHook: self._delHook(ann)
        r = aglite.AnnotationSet.remove(self, ann)
        if self._delHook2: self._delHook2(ann)
        return r
        
    def setAddCallback(self, f):
        self._addHook = f

    def setRemoveCallback(self, f):
        self._delHook = f

    def setChangeCallback(self, f):
        self._changeHook = f

    def setAddCallback2(self, f):
        self._addHook2 = f

    def setRemoveCallback2(self, f):
        self._delHook2 = f

    def setChangeCallback2(self, f):
        self._changeHook2 = f



    
if __name__ == "__main__":
    a = AnnotationSet()
