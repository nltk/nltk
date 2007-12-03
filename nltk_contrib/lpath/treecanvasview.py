from qt import *
from qtcanvas import *
from treecanvasnode import *
from nodefeaturedialog import *
from translator import translate
from axis import *
import lpath
import math

class FilterExpressionPopup(QLabel):
    def __init__(self, parent):
        self.super = QLineEdit
        self.super.__init__(self, parent)
        self.super.hide(self)
        self.timer = None
        self.locked = False
        
    def popup(self, p, node):
        self.node = node
        r = QRect(p,QSize(100,20))
        self.setGeometry(r)
        if node.filterExpression:
            self.setText(node.filterExpression)
        else:
            self.setText('')
        self.show()
        self.locked = False

    def show(self):
        self.stopTimer()
        self.super.show(self)
        
    def startTimer(self):
        self.stopTimer()
        self.timer = self.super.startTimer(self,300)
        
    def stopTimer(self):
        if self.timer is not None:
            self.killTimer(self.timer)
            self.timer = None
            
    def hide(self):
        if not self.locked:
            self.stopTimer()
            self.startTimer()
    
    def getText(self):
        return self._text
    
    def timerEvent(self, e):
        if e.timerId() == self.timer:
            self.super.hide(self)
            self.stopTimer()
        else:
            self.super.timerEvent(self, e)
            
    def mousePressEvent(self, e):
        self.super.hide(self)
        s,ans = QInputDialog.getText('Edit Filter Expression','Enter new filter expression',
                                     QLineEdit.Normal,self.text(),self)
        if ans:
            s = unicode(s).strip()
            if s:
                self.node.filterExpression = s
            else:
                del self.node.filterExpression
        
class TreeCanvasView(QCanvasView):

    AXIS_TOGGLE_MAP = {
        AxisParent:AxisAncestor,
        AxisAncestor:AxisParent,
        AxisImmediateSibling:AxisSibling,
        AxisSibling:AxisImmediateFollowing,
        AxisImmediateFollowing:AxisFollowing,
        AxisFollowing:AxisImmediateSibling,
        }
    
    def __init__(self, *args):
        QCanvasView.__init__(self, *args)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.filterExpPopup = FilterExpressionPopup(self)
        self.rightClickPopup = QPopupMenu(self)
        self.rightClickPopup.insertItem('Shift &Scope',self.processRightClickPopup,0,1)
        self.rightClickPopup.insertItem('&Toggle Left Alignment',self.processRightClickPopup,0,2)
        self.rightClickPopup.insertItem('Toggle &Right Alignment',self.processRightClickPopup,0,7)
        self.rightClickPopup.insertItem('Edit &Label',self.processRightClickPopup,0,5)
        self.rightClickPopup.insertItem('Edit &Filter Expression',self.processRightClickPopup,0,3)
        self.rightClickPopup.insertItem('Delete Filter E&xpression',self.processRightClickPopup,0,4)
        self.rightClickPopup.insertItem('Node Attribute &Dialog',self.processRightClickPopup,0,6)
        self.rightClickPopup.insertItem('&Reset',self.processRightClickPopup,0,8)
        self.rightClickPopupNode = None  # temporary storage of right-clicked node
        self._initialize()

    def _initialize(self):
        self.highlightedNode = None
        self.selectedNode = None
        self.clickCount = 0
        
    def setCanvas(self, c):
        self._initialize()
        c.resize(self.width(), self.height())
        QCanvasView.setCanvas(self, c)
        
    def processRightClickPopup(self, *args):
        item = self.rightClickPopupNode
        menuid, = args
        if menuid == 1:
            item.node.shiftScope()
        elif menuid == 2:
            a = item.node.lpAlignment()
            if a == item.node.AlignNone or a == item.node.AlignRight:
                item.node.lpAlignLeft()
            else:
                item.node.lpClearAlignment()
                if a == item.node.AlignBoth:
                    item.node.lpAlignRight()
        elif menuid == 7:
            a = item.node.lpAlignment()
            if a == item.node.AlignNone or a == item.node.AlignLeft:
                item.node.lpAlignRight()
            else:
                item.node.lpClearAlignment()
                if a == item.node.AlignBoth:
                    item.node.lpAlignLeft()
                
        elif menuid == 3:
            s = item.node.filterExpression
            if s is None: s = ''
            while True:
                s,ans = QInputDialog.getText('New Filter Expression','Enter filter expression',
                                             QLineEdit.Normal,s,self)
                if ans:
                    s = unicode(s).strip()
                    if s:
                        if lpath.translate("//A[%s]"%s) is None:
                            QMessageBox.critical(self,"Error","Invalid filter expression.")
                            continue
                        else:
                            item.node.filterExpression = s
                break
                        
        elif menuid == 4 and item.node.filterExpression is not None:
            del item.node.filterExpression
        elif menuid == 5:
            s,ans = QInputDialog.getText('Edit Label','Enter new label',
                                         QLineEdit.Normal,item.node.label,self)
            if ans:
                s = unicode(s).strip()
                if s:
                    if 'originalLabel' not in item.node.data:
                        item.node.data['originalLabel'] = item.node.label
                    item.node.label = s
        elif menuid == 6:
            d = NodeFeatureDialog(item.node, self)
            d.exec_loop()
        elif menuid == 8:
            if 'originalLabel' in item.node.data:
                item.node.label = item.node.data['originalLabel']
                del item.node.data['originalLabel']
            item.node.lpClearAlignment()
            del item.node.filterExpression

    def enableDisableRightClickPopupMenuItems(self):
        item = self.rightClickPopupNode
        # menuid == 1:
        self.rightClickPopup.setItemEnabled(1, item.node.canShiftScope())

        # menuid == 2:
        self.rightClickPopup.setItemEnabled(2, item.node.lpLeftAlignable())

        # menuid == 7:
        self.rightClickPopup.setItemEnabled(7, item.node.lpRightAlignable())
        
        # menuid == 3:
        self.rightClickPopup.setItemEnabled(3, len(item.node.children) != 0)
        
        # menuid == 4:
        self.rightClickPopup.setItemEnabled(4, item.node.filterExpression is not None)

        # menuid == 5:
        self.rightClickPopup.setItemEnabled(5, True)
        
        # menuid == 6:
        
        # menuid == 8
        self.rightClickPopup.setItemEnabled(8, 'originalLabel' in item.node.data or \
                                            item.node.lpAlignment()!=item.node.AlignNone or \
                                            item.node.filterExpression is not None)
        
    def mousePressEvent(self, e):
        b = e.button()
        c = self.canvas()
        if b not in (Qt.LeftButton,Qt.RightButton,Qt.MidButton) or c is None:
            return
        axes = []
        nodes = []
        p = self.viewportToContents(e.pos())
        for item in c.collisions(p):
            if isinstance(item,TreeCanvasNode):
                nodes.append(item)
            elif isinstance(item,Axis):
                axes.append(item)
        if b == Qt.LeftButton:
            if nodes:
                item = nodes[0]
                node = item.node
                if self.selectedNode:
                    if item != self.selectedNode:
                        if not self.selectedNode.lpSetChild(node):
                            self.selectedNode.lpAttachBranch(node)
                        if len(node.children) > 0:
                            self.selectNode(node)
                else:
                    self.selectNode(node)
                self.emitLPath()
            elif axes:
                # toggle through different axis
                item = axes[0]
                self.overrideLineShape(item, self.AXIS_TOGGLE_MAP[item.__class__])
                self.emitLPath()
                    
        elif b == Qt.RightButton:
            if nodes:
                item = nodes[0]
                self.rightClickPopupNode = item
                p = self.mapToGlobal(self.contentsToViewport(item.boundingRect().bottomLeft()))
                # don't want to edit features on terminal node
                #enableVal = len(item.node.children) != 0
                #for i in (1,2,3,4,6):
                #    self.rightClickPopup.setItemEnabled(i,enableVal)
                self.enableDisableRightClickPopupMenuItems()
                self.rightClickPopup.popup(p)
            elif axes:
                item = axes[0]
                if item.target.lpOnMainTrunk():
                    # -> branch
                    item.root.lpAttachBranch(item.target)
                elif item.target.getNot():
                    if item.root.lpChildren[0] or len(item.target.children)==0:
                        # -> branch
                        item.target.setNot(False)
                    else:
                        # -> main trunk
                        item.root.lpSetChild(item.target)
                else:
                    # -> negation
                    item.target.setNot(True)
                self.emitLPath()
            else:
                self.unselectNode()
        elif b == Qt.MidButton:
            if nodes:
                item = nodes[0]
                item.node.collapsed = not item.node.collapsed
            elif axes:
                item = axes[0]
                item.target.lpPrune()
                self.emitLPath()
                    
    def resetNode(self, node):
        if 'originalLabel' in node.data:
            node.label = node.data['originalLabel']
            del node.data['originalLabel']
        node.lpClearAlignment()
        del node.filterExpression
    
    def mousePressEventHandler_destMode(self, e):
        if e.button() == Qt.LeftButton:
            self.mousePressEventHandler_removeLine(e)
        elif e.button() == Qt.RightButton:
            self.unselectNode()
        
    def highlight(self, node):
        #if node != self.selectedNode:
        node.gui.setColor(Qt.red)
        self.canvas().update()
        self.highlightedNode = node

    def unhighlight(self):
        if self.highlightedNode and self.highlightedNode != self.selectedNode:
            self.highlightedNode.gui.setColor(Qt.black)
            self.canvas().update()
        self.highlightedNode = None

    def selectNode(self, node):
        self.unselectNode()
        item = node.gui
        item.setColor(Qt.red)
        self.canvas().update()
        self.selectedNode = node

    def unselectNode(self):
        if self.selectedNode:
            self.selectedNode.gui.setColor(Qt.black)
            self.canvas().update()
            self.selectedNode = None

    def mouseMoveEvent(self, e):
        c = self.canvas()
        if not c: return

        p = self.viewportToContents(e.pos())
        for item in c.collisions(p):
            if isinstance(item, TreeCanvasNode):
                if item.node != self.highlightedNode:
                    if item.node.filterExpression:
                        x = self.contentsToViewport(item.boundingRect().topRight())
                        self.filterExpPopup.popup(x, item.node)
                    self.unhighlight()
                    self.highlight(item.node)
                    
                    s = translate(item.node.lpRoot, item.node, ' ')
                    if s is not None:
                        self.emit(PYSIGNAL('highlightLPath'),(s,))
                break
        else:
            if self.highlightedNode is not None:
                self.filterExpPopup.hide()
                self.unhighlight()

    def _computeAxisType(self, n1, n2):
        c = self.canvas()

        if n1.parent == n2 or n2.parent == n1:
            return AxisParent

        if n1.rightSibling == n2 or n2.rightSibling == n1:
            return AxisImmediateSibling

        if n1.parent == n2.parent:
            return AxisSibling

        a1L = [n1]
        p = n1.parent
        while p:
            if p == n2:
                return AxisAncestor
            a1L.append(p)
            p = p.parent

        a2L = [n2]
        p = n2.parent
        while p:
            if p == n1:
                return AxisAncestor
            a2L.append(p)
            p = p.parent

        for i,x in enumerate(a1L):
            try:
                j = a2L.index(x)
                break
            except ValueError:
                pass

        a1L = a1L[:i]
        a2L = a2L[:j]
        i = x.children.index(a1L.pop())
        j = x.children.index(a2L.pop())

        if abs(i-j) > 1:
            return AxisFollowing
        
        if i < j:
            L1 = a1L
            L2 = a2L
        else:
            L1 = a2L
            L2 = a1L

        for x in L1:
            if x.rightSibling:
                return AxisFollowing
        for x in L2:
            if x.leftSibling:
                return AxisFollowing

        return AxisImmediateFollowing
            

    def _scopicRoot(self, n):
        num = n.getNumber()
        L = [(n1,l) for n1,n2,l in self.edges if n2==n]
        while L and L[0][0].getNumber() >= num:
            n = L[0][0]
            L = [(n1,l) for n1,n2,l in self.edges if n2==n]
        else:
            if L:
                return L[0][0]
        return None
            
    def _computeNestLevel(self, n1, n2):
        m1 = self.canvas().item2node(n1)
        m2 = self.canvas().item2node(n2)
        if m1.isAncestorOf(m2):
            return n1.getNumber() + 1
        else:
            r = self._scopicRoot(n1)
            if r:
                rnode = self.canvas().item2node(r)
                if rnode.isAncestorOf(m2):
                    return r.getNumber() + 1
                else:
                    return self._computeNestLevel(r, n2)
            else:
                return 0

    def overrideLineShape(self, item, cls):
        clsName = str(cls).split("'")[1].split('.')[-1]
        item.target.setAxisType(clsName)
        self.emitLPath()

    def clear(self):
        c = self.canvas()
        if c is None: return
        tree = c.getTreeModel()
        def g(t,L): L.append(t)
        L = []
        for r in tree.lpRoots(): r.lpDfs(g,L)
        for n in L:
            n.lpPrune()
            #n.lpClearAlignment()
            self.resetNode(n)
            n.gui.clear()
        self.unselectNode()
        c.update()


    def emitLPath(self):
        self.emit(PYSIGNAL("changed"),())
                        
    def resizeEvent(self, e):
        QCanvasView.resizeEvent(self, e)
        if self.canvas():
            self.canvas().resize(e.size().width(),e.size().height())
            
