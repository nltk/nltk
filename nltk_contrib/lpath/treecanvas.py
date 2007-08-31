from qtcanvas import *
from qt import *
from treecanvasnode import *

__all__ = ["TreeCanvas"]

class TreeCanvas(QCanvas):
    """
    TreeCanvas is a canvas on which a tree and LPath query are drawn.
    The tree to be rendered is set when TreeCanvas is instantiated.
    Once the tree is set, it is impossible to replace the currently
    tree with another tree.
    """
    
    def __init__(self, treeModel):
        """
        @type  treeModel: TreeModel
        @param treeModel: tree model that will be rendered on this canvas.
        """
        QCanvas.__init__(self)

        self._depth = {}
        self._width = {}

        self._data = treeModel
        self._w = None     # width and height of the box
        self._h = None     # enclosing the tree
        self._layout()

    def getTreeModel(self):
        """
        @rtype: TreeModel
        @return: tree model currently rendered on the canvas.
        """
        return self._data
    
    def item2node(self, item):
        """
        Deprecated.
        """
        return item.node

    def getAsPixmap(self, left=0,top=0,width=None,height=None):
        """
        Take a snapshot of the canvas. The region to be captured can be
        specified as a rectangle which is described by the top left point
        and witdth and height.
        
        Note: Currently the 4 arguments of the method are just place-holders.
        These arguments are ignored and the image of the whole canvas is
        returned.
        
        @type left: int
        @param left: x coordinate of the top left point.
        @type top: int
        @param top: y coordinate of the top left point.
        @type width: int
        @param width: width of the rectangle.
        @type height: int
        @param height: height of the rectangle.
        @rtype: QPixmap
        @return: a snapshot of the canvas
        """
        if width is None or width > self._w:
            width = self._w
        if height is None or height > self._h:
            height = self._h
            
        pixmap = QPixmap(width, height)
        painter = QPainter(pixmap)
        clip = QRect(left, top, width, height)
        wm = painter.worldMatrix()
        wm.translate(-left, -top)
        painter.setWorldMatrix(wm)
        self.drawArea(clip, painter)
        return pixmap
        
    def resize(self, w, h):
        if w < self._w:
            w = self._w
        if h < self._h:
            h = self._h
        QCanvas.resize(self, w, h)
    
    def collapse(self, node):    
        if node.collapsed == True:
            hide = lambda x:x.hide()
            for c in node.children:
                c.dfs(hide)
        else:
            for c in node.children:
                self.collapse(c)
        
    def redraw(self):
        self._depth = {}
        self._width = {}
        self._computeWidthDepthRecursive(self._data)
        levelHeight = 30
        h = self._depth[self._data] * levelHeight
        self._computeXYRecursive(self._data, 0, 0, h)
        Q = []
        self._data.dfs(lambda x:Q.append(x))
        self._data.gui.show()
        for node in Q[1:]:
            item = node.gui
            item2 = node.parent.gui
            coords = item.connectingLine(item2)
            apply(node.line.setPoints, coords)
            node.show()
            
        self.collapse(self._data)
        
        self._w = self._width[self._data]
        self._h = h + levelHeight
        w = max(self.width(), self._w)
        h = max(self.height(), self._h)
        QCanvas.resize(self, w, h)
        
        for root in self._data.lpRoots():
            root.lpDfs(lambda x:x.redrawAxis())
        self.update()
        
    def _layout(self):
        self._depth = {}
        self._width = {}
        
        self._data.dfs(TreeCanvasNode, self)
        self._computeWidthDepthRecursive(self._data)

        levelHeight = 30
        h = self._depth[self._data] * levelHeight
        self._computeXYRecursive(self._data, 0, 0, h)

        Q = []
        self._data.dfs(lambda x:Q.append(x))
        self._data.gui.show()
        for node in Q[1:]:
            item = node.gui
            item2 = node.parent.gui
            coords = item.connectingLine(item2)
            pen = QPen(QColor(0xc0,0xc0,0xc0))
            pen.setStyle(Qt.DotLine)
            line = QCanvasLine(self)
            line.setPen(pen)
            node.line = line
            apply(line.setPoints, coords)
            node.show()
            
        self._w = self._width[self._data]
        self._h = h + levelHeight
        QCanvas.resize(self, self._w, self._h)

    def _pad(self, node, w):
        if node.children and node.collapsed == False:
            d = w / len(node.children)
            for c in node.children:
                self._width[c] += d
                self._pad(c, d)

    def _computeWidthDepthRecursive(self, node):
        sumwidth = 0.0
        maxdepth = 0
        if node.collapsed == False:
            for c in node.children:
                w,d = self._computeWidthDepthRecursive(c)
                sumwidth += w
                if d > maxdepth: maxdepth = d
        width = node.gui.boundingRect().width() + 10.0
        if sumwidth < width:
            self._pad(node, width-sumwidth)
        else:
            width = sumwidth
        #if not node.children: width += 10
        maxdepth += 1
        self._depth[node] = maxdepth
        self._width[node] = width
        return width, maxdepth

    def _computeXYRecursive(self, node, x, y, height):
        item = node.gui

        if node.children and node.collapsed == False:
            fromLeft = 0
            fromTop = height / (self._depth[node]-1)
            y1 = y + fromTop
            h1 = height - fromTop
            for c in node.children:
                self._computeXYRecursive(c, x+fromLeft, y1, h1)
                fromLeft += self._width[c]

            c1 = node.children[0].gui
            c2 = node.children[-1].gui
            x1 = c1.boundingRect().left()
            x2 = c2.boundingRect().left() + c2.width()
            if abs(item.boundingRect().left()-item.x()) < 1.0:
                item.setX( (x1 + x2 - item.width()) / 2.0 )
            else:
                item.setX( (x1 + x2 + item.width()) / 2.0 )
        else:
            if abs(item.boundingRect().left()-item.x()) < 1.0:
                item.setX(x + (self._width[node] - item.width()) / 2.0)
            else:
                item.setX(x + (self._width[node] + item.width()) / 2.0)
        item.setY(y)

    def signal(self, *args):
        self.emit(PYSIGNAL('treeUpdated'),args)
