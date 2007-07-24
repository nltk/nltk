from qt import QObject, PYSIGNAL
from tree import TreeModel as PureTree

__all__ = ['TreeModel']

class TreeModel(PureTree, QObject):
    def __init__(self):
        PureTree.__init__(self)
        QObject.__init__(self)

    def attach(self,node):
        if PureTree.attach(self,node):
            self.emit(PYSIGNAL("attach"),(self,node,))
            return True
        else:
            return False
        
    def insertLeft(self,node):
        if PureTree.insertLeft(self,node):
            self.emit(PYSIGNAL("insertLeft"),(self,node,))
            return True
        else:
            return False
       
    def insertRight(self,node):
        if PureTree.insertRight(self,node):
            self.emit(PYSIGNAL("insertRight"),(self,node,))
            return True
        else:
            return False
        
    def prune(self):
        if PureTree.prune(self):
            self.emit(PYSIGNAL("prune"),(self,))
            return True
        else:
            return False
        
    def splice(self):
        if PureTree.splice(self):
            self.emit(PYSIGNAL("splice"),(self,))
            return True
        else:
            return False
