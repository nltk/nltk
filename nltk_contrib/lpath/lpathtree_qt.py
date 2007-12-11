from lpathtree import LPathTreeModel as PureLPathTree
from axis import *
from qt import QObject

__all__ = ['LPathTreeModel']

class LPathTreeModel(PureLPathTree,object):
    def __init__(self):
        PureLPathTree.__init__(self)
        self.gui = None
        self.axis = None
        self.line = None
        self.hidden = False

    def hide(self):
        self.gui.hide()
        self.line.hide()
        if self.axis:
            self.axis.hide()
        self.hidden = True
    
    def show(self):
        self.gui.show()
        self.line.show()
        if self.axis:
            self.axis.show()
        self.hidden = False
        
    def _findCollapseRoot(self, node):
        while node:
            if node.collapsed and node.hidden==False:
                return node
            else:
                node = node.parent
                
    def redrawAxis(self):
        if self.axis:
            root = root1 = self.axis.root
            target = target1 = self.axis.target
            if root.hidden:
                root1 = self._findCollapseRoot(root)
            if target.hidden:
                target1 = self._findCollapseRoot(target)
            coords = list(root1.gui.connectingLine(target1.gui))
            if root.hidden:
                coords[1] += root.gui.height()
            if target.hidden:
                coords[3] += target.gui.height()
            if root==target1 and (len(root1.lpChildren) > 1 or root1.lpChildren[0]):
                coords[1] += root1.gui.height() / 2.0
            if target==root1 and target1.lpParent:
                coords[3] += target1.gui.height() / 2.0
            self.axis.setCanvas(None)
            cls = eval(self.getAxisType())
            self.axis = cls(self.gui.canvas())
            self.axis.target = target
            self.axis.root = root
            apply(self.axis.setPoints, coords)
            if self.getNot():
                self.axis.setHeadType(Axis.HeadNegation)
            elif not self.lpOnMainTrunk():
                self.axis.setHeadType(Axis.HeadBranch)
            self.axis.show()
            self.axis.canvas().update()

    def _newAxis(self, node):
        if node.axis is None:
            cls = eval(node.getAxisType())
            node.axis = cls(self.gui.canvas())
            node.axis.root = self
            node.axis.target = node
            #coords = node.gui.connectingLine(self.gui)
            coords = self.gui.connectingLine(node.gui)
            apply(node.axis.setPoints, coords)
            if node.getNot():
                node.axis.setHeadType(Axis.HeadNegation)
            elif not node.lpOnMainTrunk():
                node.axis.setHeadType(Axis.HeadBranch)
            node.axis.show()
            node.axis.canvas().update()

    def setNot(self, v):
        if PureLPathTree.setNot(self,v):
            self.redrawAxis()

    def setAxisType(self, v):
        if PureLPathTree.setAxisType(self,v):
            self.redrawAxis()
            return True
        else:
            return False

    def resetScope(self):
        PureLPathTree.resetScope(self)
        self.gui.canvas().update()

    def setScope(self, node):
        PureLPathTree.setScope(self, node)
        self.gui.canvas().update()
        self.gui.canvas().signal()
        
    def shiftScope(self):
        PureLPathTree.shiftScope(self)
        self.gui.canvas().update()
        self.gui.canvas().signal()
        
    def lpSetChild(self, node):
        if PureLPathTree.lpSetChild(self, node):
            self.lpResetAlignment()
            if node.axis is None:
                self._newAxis(node)
            else:
                node.redrawAxis()
            return True
        else:
            return False

    def lpAttachBranch(self, node):
        if PureLPathTree.lpAttachBranch(self, node):
            self.lpResetAlignment()
            if node.axis is None:
                self._newAxis(node)
            else:
                node.redrawAxis()
            return True
        else:
            return False

    def lpPrune(self):
        p = self.lpParent
        if PureLPathTree.lpPrune(self):
            self.axis.setCanvas(None)
            self.axis = None
            self.gui.updateNumber()
            self.lpResetAlignment()
            if p:
                p.gui.updateNumber()
                p.lpResetAlignment()
            self.gui.canvas().update()
            return True
        else:
            return False
        
    def lpAlignLeft(self):
        if PureLPathTree.lpAlignLeft(self):
            self.gui.update()
            self.gui.canvas().update()
            self.gui.canvas().signal()
            self.gui.canvas().redraw()
            return True
        else:
            return False
    
    def lpAlignRight(self):
        if PureLPathTree.lpAlignRight(self):
            self.gui.update()
            self.gui.canvas().update()
            self.gui.canvas().signal()
            self.gui.canvas().redraw()
            return True
        else:
            return False
    
    def lpClearAlignment(self):
        PureLPathTree.lpClearAlignment(self)
        self.gui.update()
        self.gui.canvas().update()
        self.gui.canvas().signal()
        self.gui.canvas().redraw()

    def _getFilterExpression(self):
        if 'lpathFilter' in self.data:
            return self.data['lpathFilter']
        else:
            return None
    def _setFilterExpression(self, v):
        self.data['lpathFilter'] = v
        self.gui.updateTrace()
        self.gui.canvas().signal()
    def _delFilterExpression(self):
        if 'lpathFilter' in self.data:
            del self.data['lpathFilter']
            self.gui.updateTrace()
            self.gui.canvas().signal()
    def _getCollapsed(self):
        if 'collapsed' in self.data:
            return self.data['collapsed']
        else:
            return False
    def _setCollapsed(self, v):
        self.data['collapsed'] = v
        self.gui.canvas().redraw()
        self.gui.canvas().update()
    def _getLabel(self):
        return self.data['label']
    def _setLabel(self, v):
        self.data['label'] = v
        #self.gui.update()
        self.gui.canvas().update()
        self.gui.canvas().signal()
        self.gui.canvas().redraw()
    def _getFuncAtts(self):    
        return self.data['@func']
    def _setFuncAtts(self, v):
        self.data['@func'] = v
        self.gui.update()
        self.gui.canvas().update()
        self.gui.canvas().signal()
    def _delFuncAtts(self):
        if '@func' in self.data:
            del self.data['@func']
            self.gui.update()
            self.gui.canvas().update()
            self.gui.canvas().signal()
            
    label = property(_getLabel,_setLabel)
    filterExpression = property(_getFilterExpression,_setFilterExpression,_delFilterExpression)
    funcatts = property(_getFuncAtts,_setFuncAtts,_delFuncAtts)
    collapsed = property(_getCollapsed,_setCollapsed)
    
