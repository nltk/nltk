"""
This is an interface to aglite.py (data model module), used by GUI components.

Annotation wraps aglite.Annotation to add interactivity, i.e. the a user-
defined callback function (set by Annotation.setCallback) will be called
whenever the contents of annotation is changed.

This is a way of monitoring changes in the data. which is useful for GUI
components.
"""

import aglite2 as aglite
AnnotationQuery = aglite.AnnotationQuery

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


    
if __name__ == "__main__":
    a = AnnotationSet()
