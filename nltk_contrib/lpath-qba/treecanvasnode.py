from qt import *
from qtcanvas import *
from lpathtree_qt import *

class Point:
    def __init__(self, *args):
        if len(args) == 2 and \
           (isinstance(args[0],int) or isinstance(args[0],float)) and \
           (isinstance(args[1],int) or isinstance(args[0],float)):
            self.x = float(args[0])
            self.y = float(args[1])
        elif len(args) == 1 and \
             isinstance(args[0],QPoint):
            self.x = float(args[0].x())
            self.y = float(args[0].y())
        else:
            raise TypeError("invalid argument type")

    def __add__(self, p):
        if not isinstance(p,Point):
            raise TypeError("invalid argument type")
        return Point(self.x+p.x, self.y+p.y)

    def __sub__(self, p):
        if not isinstance(p,Point):
            raise TypeError("invalid argument type")
        return Point(self.x-p.x, self.y-p.y)

    def __mul__(self, n):
        if not isinstance(n,int) and \
           not isinstance(n,float):
            raise TypeError("invalid argument type")
        n = float(n)
        return Point(self.x*n,self.y*n)

    def __div__(self, n):
        if not isinstance(n,int) and \
           not isinstance(n,float):
            raise TypeError("invalid argument type")
        n = float(n)
        return Point(self.x/n,self.y/n)

    
class TreeCanvasNode(QCanvasText):
    def __init__(self, node=None, canvas=None):
        assert(isinstance(node,LPathTreeModel))
        if 'label' in node.data and node.data['label']:
            QCanvasText.__init__(self, node.data['label'], canvas)
        else:
            QCanvasText.__init__(self, '', canvas)
        node.gui = self

        self.numberWidget = QCanvasText(canvas)
        self.numberWidget.setColor(Qt.lightGray)
        self.numberHidden = True
        self.node = node
        self.triangle = QCanvasPolygon(canvas)
        self.triangle.setBrush(QBrush(Qt.gray))

    def hide(self):
        self.numberWidget.hide()
        self.triangle.hide()
        QCanvasText.hide(self)
        
    def draw(self, painter):
        self.updateNumber()
        alignment = self.node.lpAlignment()
        if alignment == self.node.AlignLeft:
            self.setText('^'+self.node.data['label'])
        elif alignment == self.node.AlignRight:
            self.setText(self.node.data['label']+'$')
        elif alignment == self.node.AlignBoth:
            self.setText("^%s$" % self.node.data['label'])
        elif self.node.data['label']:
            self.setText(self.node.data['label'])
        else:
            self.setText('')

        if self.node.collapsed:
            dw = self.width() / 2.0
            x1 = self.x() + dw
            y1 = self.y() + self.height()
            pa = QPointArray(3)
            pa.setPoint(0, x1,y1)
            pa.setPoint(1, x1-dw,y1+self.height())
            pa.setPoint(2, x1+dw,y1+self.height())
            self.triangle.setPoints(pa)
            self.triangle.show()
        else:
            self.triangle.hide()
            
        QCanvasText.draw(self, painter)

    def clear(self):
        f = self.font()
        f.setUnderline(False)
        self.setFont(f)
        
    def width(self):
        return self.boundingRect().width()

    def height(self):
        return self.boundingRect().height()

    def intersection(self, item):
        p = Point(item.boundingRect().center())
        box = self.boundingRect()
        c = Point(box.center())
        v = p - c
        if self == item:
            return c
        elif v.x != 0:
            v = v / abs(v.x)
        elif v.y > 0:
            return Point(c.x,box.bottom())
        else:
            return Point(c.x,box.top())
        v1 = Point(box.bottomRight() - box.topLeft())
        if v1.x > 0.0:
            v1 = v1 / v1.x

        if abs(v.y) < v1.y:
            dx = box.width() / 2.0
            x = c.x + dx * v.x
            y = c.y + dx * v.y
        else:
            if v.y != 0:
                v = v / abs(v.y)
                dy = box.height() / 2.0
                x = c.x + dy * v.x
                y = c.y + dy * v.y
            elif v.x > 0:
                x = box.right()
                y = c.y
            else:
                x = box.left()
                y = c.y
        return Point(x, y)

    def connectingLine(self, item):
        p1 = self.intersection(item)
        p2 = item.intersection(self)
        return p1.x,p1.y,p2.x,p2.y

    def updateNumber(self):
        if self.node.lpIsolated():
            self.numberHidden = True
            self.numberWidget.hide()
        else:
            number = self.node.lpScopeDepth()
            c = self.canvas()
            w = self.numberWidget
            c.setChanged(w.boundingRect())
            w.setText("%d" % number)
            r = self.boundingRect()
            wr = w.boundingRect()
            wy = r.top() - wr.height()
            wx = r.left() + (r.width() - wr.width()) / 2.0
            w.move(wx,wy)
            c.setChanged(w.boundingRect())
            self.numberHidden = False
            w.show()

    def getNumber(self):
        self.node.lpScopeDepth()

    def updateTrace(self):
        f = self.font()
        f.setUnderline(self.node.filterExpression is not None)
        self.setFont(f)
        self.canvas().update()
        
if __name__ == "__main__":
    from qt import *
    app = QApplication([])
    c = QCanvas(100,100)
    c.setBackgroundColor(Qt.blue)
    w = QCanvasView(c)
    n = TreeCanvasNode("test",c)
    n.setColor(Qt.red)
    n.show()
    
    app.setMainWidget(w)
    w.show()
    app.exec_loop()
