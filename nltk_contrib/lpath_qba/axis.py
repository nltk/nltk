from qt import *
from qtcanvas import *
import math

def dxdy(w, x1, y1, x2, y2):
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
    a = x2-x1
    b = y2-y1
    c = math.sqrt(a*a + b*b)

    if c == 0:
        dx = dy = 0
    else:
        dx = b * w / c / 2.0
        dy = a * w / c / 2.0

    return dx,dy, x1,y1, x2,y2


class Axis(QCanvasPolygonalItem):
    # there should be no gap between two consecutive types
    HeadContinue = 0
    HeadBranch = 1
    HeadNegation = 2
    
    def __init__(self, canvas):
        QCanvasPolygonalItem.__init__(self, canvas)
        self.pen = QPen(Qt.red)
        self.setPen(self.pen)

        self.points = (0,0,0,0)
        self.area = QPointArray(4)
        self.area.setPoint(0,0,0)
        self.area.setPoint(1,1,0)
        self.area.setPoint(2,1,1)
        self.area.setPoint(3,0,1)

        self.headType = self.HeadContinue
        self.root = None
        self.target = None
        
   
    def areaPoints(self):
        return self.area
    
    def setPoints(self, x1,y1,x2,y2):
        """
        The line has an orientation; (x1,y1) is the start point and
        (x2,y2) is the end point.
        """
        self.points = (x1,y1,x2,y2)

        dx,dy, x1,y1, x2,y2 = dxdy(self.pen.width()+5.0, x1,y1,x2,y2)

        self.area.setPoint(0, x1 + dx, y1 - dy)
        self.area.setPoint(1, x1 - dx, y1 + dy)
        self.area.setPoint(2, x2 - dx, y2 + dy)
        self.area.setPoint(3, x2 + dx, y2 - dy)

    def lineWidth(self):
        return self.pen.width()

    def _drawBranchHead(self, painter):
        h = 5.0
        x1, y1, x2, y2 = self.points
        if x1 == x2:
            x = x1 - h
            if y2 > y1:
                y = y1
            else:
                y = y1 - 2.0 * h
        elif y1 == y2:
            if x2 > x1:
                x = x1
            else:
                x = x1 - 2.0 * h
            y = y1 - h
        else:
            xx = float(x2 - x1)
            yy = float(y2 - y1)
            r = abs(yy / xx)
            h1 = h / math.sqrt(2.0)
            x = x1 + h * xx / abs(xx) / math.sqrt(1 + r*r) - h1
            y = y1 + h * yy / abs(yy) / math.sqrt(1 + r*r) * r - h1
        p = QPen(self.pen)
        p.setWidth(1)
        p.setStyle(Qt.SolidLine)
        painter.setPen(p)
        painter.setBrush(QBrush(p.color()))
        painter.drawEllipse(x,y, 2*h, 2*h)

    def _drawNegationHead(self, painter):
        h = 5.0
        x1, y1, x2, y2 = self.points
        if x1 == x2:
            new_x1 = x1 - h
            new_x2 = x1 + h
            if y1 > y2:
                new_y1 = new_y2 = y1 - h
            else:
                new_y1 = new_y2 = y1 + h
        elif y1 == y2:
            if x1 > x2:
                new_x1 = new_x2 = x1 - h
            else:
                new_x1 = new_x2 = x1 + h
            new_y1 = y1 - h
            new_y2 = y1 + h
        else:
            xx = x2 - x1
            yy = y2 - y1
            sigx = xx / abs(xx)
            sigy = yy / abs(yy)
            r = abs(yy / xx)
            c = h / r
            a = math.sqrt(c*c + h*h) / (1+r*r)
            dx = sigx * a * r * r
            dy = sigy * a * r
            x11 = x1 + sigx * abs(dy)
            y11 = y1 + sigy * abs(dx)
            new_x1 = x11 + dx
            new_y1 = y11 - dy
            new_x2 = x11 - dx
            new_y2 = y11 + dy
        pen = QPen(self.pen)
        pen.setWidth(2)
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.drawLine(new_x1,new_y1,new_x2,new_y2)
    
    def drawLineHead(self, painter):
        if self.headType == self.HeadBranch:
            self._drawBranchHead(painter)
        elif self.headType == self.HeadNegation:
            self._drawNegationHead(painter)
            
    def drawShape(self, painter):
        apply(painter.drawLine, self.points)
        self.drawLineHead(painter)
        
    def toggleHeadType(self):
        self.headType = (self.headType + 1) % 3
        self.update()
        self.canvas().update()

    def setHeadType(self, typ):
        if typ not in (self.HeadContinue,
                       self.HeadBranch,
                       self.HeadNegation):
            return
        self.headType = typ
        self.update()
        self.canvas().update()

class AxisFollowing(Axis):
    def __init__(self, canvas):
        Axis.__init__(self, canvas)
        self.pen.setWidth(3)
        self.pen.setStyle(Qt.DashLine)
        self.setPen(self.pen)

class AxisImmediateFollowing(Axis):
    def __init__(self, canvas):
        Axis.__init__(self, canvas)
        self.pen.setWidth(3)
        self.setPen(self.pen)

class AxisSibling(Axis):
    def __init__(self, canvas):
        Axis.__init__(self, canvas)
        self.pen.setWidth(2)
        self.pen.setStyle(Qt.DashLine)
        self.setPen(self.pen)
        self.distance = 2.0

    def drawShape(self, painter):
        x1,y1,x2,y2 = self.points
        dx, dy, x1,y1, x2,y2  = dxdy(self.distance+self.pen.width(), x1,y1, x2,y2)
        painter.drawLine(x1+dx,y1-dy,x2+dx,y2-dy)
        painter.drawLine(x1-dx,y1+dy,x2-dx,y2+dy)
        self.drawLineHead(painter)

    def lineWidth(self):
        return self.pen.width() * 2.0 + self.distance


class AxisImmediateSibling(Axis):
    def __init__(self, canvas):
        Axis.__init__(self, canvas)
        self.pen.setWidth(2)
        self.setPen(self.pen)
        self.distance = 2.0

    def drawShape(self, painter):
        x1,y1,x2,y2 = self.points
        dx, dy, x1,y1, x2,y2  = dxdy(self.distance+self.pen.width(), x1,y1, x2,y2)
        painter.drawLine(x1+dx,y1-dy,x2+dx,y2-dy)
        painter.drawLine(x1-dx,y1+dy,x2-dx,y2+dy)
        self.drawLineHead(painter)

    def lineWidth(self):
        return self.pen.width() * 2.0 + self.distance


class AxisAncestor(Axis):
    def __init__(self, canvas):
        Axis.__init__(self, canvas)
        self.pen.setWidth(3)
        self.pen.setStyle(Qt.DashLine)
        self.pen.setColor(Qt.blue)
        self.setPen(self.pen)


class AxisParent(Axis):
    def __init__(self, canvas):
        Axis.__init__(self, canvas)
        self.pen.setWidth(3)
        self.pen.setColor(Qt.blue)
        self.setPen(self.pen)


pen = QPen(Qt.red)
pen.setWidth(3)
pen.setStyle(Qt.DashLine)
penFollowing = pen

pen = QPen(Qt.red)
pen.setWidth(3)
penImmFollowing = pen

class AxisButton(QPushButton):
    def __init__(self, pen, parent):
        QPushButton.__init__(self, parent)
        self.pen = pen

    def drawLine(self, y):
        p = QPainter(self)
        p.setPen(self.pen)
        x1 = 10
        x2 = self.width() - 10
        p.drawLine(x1, y, x2, y)

    def paintEvent(self, e):
        QPushButton.paintEvent(self, e)
        self.drawLine(self.height() / 2.0)
        
class AxisButtonFollowing(AxisButton):
    def __init__(self, parent, pen=penFollowing):
        AxisButton.__init__(self, pen, parent)
        
class AxisButtonImmFollowing(AxisButtonFollowing):
    def __init__(self, parent, pen=penImmFollowing):
        AxisButtonFollowing.__init__(self, parent, pen)
        
class AxisButtonSibling(AxisButton):
    def __init__(self, parent, pen=penFollowing):
        AxisButton.__init__(self, pen, parent)

    def paintEvent(self, e):
        QPushButton.paintEvent(self, e)
        y = self.height() / 2.0
        dy = 1 + self.pen.width() / 2.0
        y1 = y - dy
        y2 = y + dy
        self.drawLine(y1)
        self.drawLine(y2)

class AxisButtonImmSibling(AxisButtonSibling):
    def __init__(self, parent):
        AxisButtonSibling.__init__(self, parent, penImmFollowing)

class AxisButtonParent(AxisButtonImmFollowing):
    def __init__(self, parent):
        AxisButtonImmFollowing.__init__(self, parent)
        self.pen = QPen(self.pen)
        self.pen.setColor(Qt.blue)
        
class AxisButtonAncestor(AxisButtonFollowing):
    def __init__(self, parent):
        AxisButtonFollowing.__init__(self, parent)
        self.pen = QPen(self.pen)
        self.pen.setColor(Qt.blue)
        
iconAxisFollowing = [
    '22 1 1 1',
    'r c #FF0000',
    'rrrrrrrrrrrrrrrrrrrrrr',
    ]

textfileopen = [
    '16 13 5 1',
    '. c #040404',
    '# c #333333',
    'a c None',
    'b c #ffffff',
    'c c #ffffff',
    'aaaaaaaaa...aaaa',
    'aaaaaaaa.aaa.a.a',
    'aaaaaaaaaaaaa..a',
    'a...aaaaaaaa...a',
    '.bcb.......aaaaa',
    '.cbcbcbcbc.aaaaa',
    '.bcbcbcbcb.aaaaa',
    '.cbcb...........',
    '.bcb.#########.a',
    '.cb.#########.aa',
    '.b.#########.aaa',
    '..#########.aaaa',
    '...........aaaaa'
    ]
