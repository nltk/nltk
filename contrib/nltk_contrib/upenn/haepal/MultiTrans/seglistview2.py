
from qt import *
from qtcanvas import *
#from agwrap import *
from format.callhome2 import *
import speakercode

"""

format = list of annotations + query functions + I/O + API
query functions = Mixin for list of annotations
I/O = load() and save()
API = convenience functions

Design overview
---------------

                          AG

                          ^
                          |
                          | inheritance
                          |

                  Derived "format" (fmt1)
            
                          ^ 
                          |
                          | modify
                          | 
        
               Broker or AG Wrapper (fmt1)

                          ^
                          |
                 reports  +----------------.----------- ... -----.
                 changes  |                |                     |
                 on disp. |                |            ...      |

                        View1(fmt1)   View2(general AG) ... ViewX(fmt1)

                          ^                ^                     ^
                          |                |            ...      |
                          |                |                     |
                          +----------------+----------- ... -----'
                          | selection
                          | span changes
                          | ...
                          v

                        QWave


Seglist is just a list of segments with some smart behaviours.

Seglist needs to be a QObject to handle signal-slot stuff.

"""

class CallhomeText(QTextEdit):
    def __init__(self, parent=None, name=None):
        QTextEdit.__init__(self, parent, name)

        self._data = None
        self._qwave = None
        self._seglock = None


        self.connect(self, SIGNAL("clicked(int,int)"), self._clicked)



    # interface to user input (keyboard/mouse)
    def keyPressEvent(self, e):
        if self._data is None: return
        if len(self._data) == 0: return

        k = e.key()
        if k == Qt.Key_Return: return

        p,c = self.getCursorPosition()

        if k == Qt.Key_Up or k == Qt.Key_Down:
            QTextEdit.keyPressEvent(self, e)
            if self._qwave is not None:
                p1,c = self.getCursorPosition()
                if p != p1:
                    seg = self._data[p1]
                    self._qwave.markRegionS(seg['CHANNEL'], seg.start, seg.end)
            return

        def propagateChanges():
            h0 = self.paragraphRect(p).height()

            QTextEdit.keyPressEvent(self, e)

            self._data[p]['TEXT'] = self.text(p).ascii()
            if h0 != self.paragraphRect(p).height():
                self.emit(PYSIGNAL("paragraphHeightChanged()"), ())


        if k == Qt.Key_Delete:
            if e.state() == Qt.AltButton:
                self._deleteSegment(p)
            elif c != self.paragraphLength(p):
                propagateChanges()
        elif k == Qt.Key_BackSpace:
            if c != 0:
                propagateChanges()
        else:
            propagateChanges()


    def _clicked(self, p, c):
        if self._data is None: return
        if len(self._data) == 0: return
        if p >= len(self._data):
            p = len(self._data) - 1
            self.setCursorPosition(p, self.paragraphLength(p))

        seg = self._data[p]

        # mark the corresponding region in the waveform
        if self._qwave is not None:
            self._qwave.markRegionS(seg['CHANNEL'], seg.start, seg.end)
                                     
    

    ### interface to bullet board
    def getSpeakerId(self, para):
        return self._data[para]['SPKR']

    def paragraphs(self):
        if self._data is None:
            return 0
        else:
            return len(self._data)

    ### interface to waveform widgets
    def changeSpan(self, a, b, c):
        if self._seglock is not None:
            #seg = self._data[self._seglock]
            seg = self._seglock

            # find left-right limits
            left = self._leftLimit
            right = self._rightLimit

            # check with limits
            if left:
                if a < left: a = left
                if b < left: b = left
            if right:
                if right < a: a = right
                if right < b: b = right

            while self._leftList:
                if a < self._leftList[-1].start:
                    self.moveUpSegment(seg)
                    self._rightList.append(self._leftList[-1])
                    self._leftList.pop()
                else:
                    break
            while self._rightList:
                if a > self._rightList[-1].start:
                    self.moveDownSegment(seg)
                    self._leftList.append(self._rightList[-1])
                    self._rightList.pop()
                else:
                    break
                
            seg.start = a
            seg.end = b

            #self._data.sort(lambda a,b:cmp(a.start,b.start))
            #self.emit(PYSIGNAL("paragraphHeightChanged()"), ())

        return (a,b)
            

    ### interface to higher level application
    def load(self, filename):
        self._data = Callhome()
        self._data.load(filename)
        self.clear()
        for i,ann in enumerate(self._data):
            self.insertParagraph(ann['TEXT'],i)
        if i == len(self._data)-1: self.removeParagraph(i+1)
        self.emit(PYSIGNAL("segmentAdded()"),())    # ... to the display
        return self._data

    def newFile(self):
        self._data = Callhome()
        self.clear()
        self.emit(PYSIGNAL("segmentAdded()"),())
        # not really but just acknowledge updates
        return self._data
    
    def setFile(self, f):
        if not isinstance(f, Callhome): return
        self._data = f
        # do initialization

    def unsetFile(self):
        #clear the view
        pass

    def setQWave(self, qwave):
        self._qwave = qwave
        self.connect(qwave, SIGNAL("setRegion(int,int,int)"),
                     self.selectSegmentByFrame)

    def rememberCurrentSegment(self):
        if self._data is not None and \
           len(self._data) > 0:
            p, c = self.getCursorPosition()
            seg = self._data[p]
            ch = seg['CHANNEL']
            
            # to the left
            x = p - 1
            leftList = []
            leftLimit = 0.0
            while x >= 0:
                q = self._data[x]
                if q['CHANNEL'] == ch:
                    leftLimit = q.end
                    break
                else:
                    leftList.append(q)
                x -= 1
            leftList.reverse()

            # to the right
            x = p + 1
            n = len(self._data)
            rightList = []
            rightLimit = self._qwave.frm2time(self._qwave.frames())
            while x < n:
                q = self._data[x]
                if q['CHANNEL'] == ch:
                    rightLimit = q.start
                    break
                else:
                    rightList.append(q)
                x += 1
            rightList.reverse()
            
            self._leftLimit = leftLimit
            self._rightLimit = rightLimit
            self._leftList = leftList
            self._rightList = rightList
            self._seglock = seg
            
            print leftList, rightList

    def forgetCurrentSegment(self):
        self._seglock = None


    def addSegment(self, seg):
        try:
            self._data.add(seg)
        except ValueError:
            # failed (because of overlap)
            return
        i = self._data.index(seg)
        self.insertParagraph(seg['TEXT'], i)
        self.setCursorPosition(i,0)

        # weird but works
        if i == len(self._data)-1: self.removeParagraph(i+1)
        
        self.emit(PYSIGNAL("segmentAdded()"),())    # ... to the display

    def _deleteSegment(self, para):
        """
        This is usually called internally, especially when
        the para num is known.
        """
        self.removeParagraph(para)
        del self._data[para]
        self.emit(PYSIGNAL("segmentDeleted()"),())  # ... from the display
        
    def deleteSegment(self, seg):
        try:
            segi = self._data.index(seg)
            self._deleteSegment(segi)
        except ValueError:
            pass

    def createSegmentForCurrentRegion(self):
        if self._qwave is not None:
            c, a, b = self._qwave.getSelectedRegionS()
            seg = self._data.new(c, a, b)
            self.addSegment(seg)

    def moveUpSegment(self, seg):
        i = self._data.index(seg)
        if i <= 0: return
        del self._data[i]
        self.removeParagraph(i)
        self._data.insert(i-1, seg)
        self.insertParagraph(seg['TEXT'], i-1)
        self.emit(PYSIGNAL("paragraphHeightChanged()"), ())
        

    def moveDownSegment(self, seg):
        i = self._data.index(seg)
        if i >= len(self._data)-1: return
        del self._data[i]
        self.removeParagraph(i)
        self._data.insert(i+1, seg)
        self.insertParagraph(seg['TEXT'], i+1)
        self.emit(PYSIGNAL("paragraphHeightChanged()"), ())

    def selectSegmentByFrame(self, a, b, c):
        if self._qwave is not None and \
           self._data is not None:
            x = self._qwave.frm2time(a)
            y = self._qwave.frm2time(b)
            ch = c  # is this true?
            candidate = None
            for i,seg in enumerate(self._data):
                if seg.start <= x:
                    if seg.end > x:
                        if seg['CHANNEL'] == ch:
                            candidate = i
                            break
                        elif candidate is None:
                            candidate = i
                elif seg.start <= y:
                    if seg['CHANNEL'] == ch:
                        candidate = i
                        break
                    elif candidate is None:
                        candidate = i
                elif seg.start >= x and candidate is None:
                    candidate = i
                    
            if candidate is not None:
                p,c = self.getCursorPosition()
                if candidate != p:
                    self.setCursorPosition(candidate,0)
                self.setFocus()
            
           
##     def setSegment(self, seg, *args):
##         """
##         args could be:
##         ("feature", name, value)
##         ("start", start_offset)
##         ("end", end_offset)
##         """
##         if seg.flagIgnoreCallback:
##             seg.flagIgnoreCallback = False  # ignored
##             return
        
##         if args[0] == "feature":
##             if args[1] == "TEXT":
##                 i = self.anns.index(seg)
##                 self.setSelection(i,0,i,self.paragraphLength(i))
##                 self.removeSelectedText()
##                 self.insertAt(seg["TEXT"], i, 0)
##         elif args[0] == "start":
##             i = self.anns.index(seg)
##             anns = self.getSortedAnnotationSet()
##             j = anns.index(seg)
##             if i != j:
##                 self.removeParagraph(i)
##                 self.insert(seg["TEXT"], j)
##                 self.anns = anns


class SeglistTextBulletBoard(QCanvasView):
    def __init__(self, seglistText, parent=None, name=None):
        QCanvasView.__init__(self, parent, name)

        self.setFrameShape(QFrame.NoFrame)
        self.setFixedWidth(20)
        self.setVScrollBarMode(QScrollView.AlwaysOff)
        self.setHScrollBarMode(QScrollView.AlwaysOff)
        
        # speaker code
        self.spkrCode = speakercode.SpeakerCode()

        # initialize text widget
        self.text = seglistText

        # bullet canvas
        self.canvas = QCanvas(self)
        self.canvas.setBackgroundColor(Qt.lightGray)
        self.setCanvas(self.canvas)
        self.connect(self.text.verticalScrollBar(),
                     SIGNAL("valueChanged(int)"),
                     self._paintBullet)
        self.connect(self.text, PYSIGNAL("paragraphHeightChanged()"),
                     self.repaint)
        self.connect(self.text, PYSIGNAL("segmentAdded()"),
                     self.repaint)
        self.connect(self.text, PYSIGNAL("segmentDeleted()"),
                     self.repaint)
        
    def _paintBullet(self, v):
        
        for item in self.canvas.allItems():
            item.setCanvas(None)
            del item

        bulletWidth = self.width()
        cy = self.text.contentsY()
        viewportBottom = self.text.contentsHeight()
        para = self.text.paragraphAt(QPoint(0,cy))
        paraNum = self.text.paragraphs()

        while para < paraNum:
            r = self.text.paragraphRect(para)
            top = self.text.contentsToViewport(r.topLeft()).y()
            height = r.height()
            color = QColor(self.spkrCode.color(self.text.getSpeakerId(para)))

            if top > viewportBottom: break
            
            item = QCanvasRectangle(0,top,bulletWidth,height, self.canvas)
            item.setBrush(QBrush(color))
            item.show()
            para += 1
            
        self.canvas.update()

        
    def resizeEvent(self, e):
        h = e.size().height()
        self.canvas.resize(20,h)
    

    def paintEvent(self, *args):
        self._paintBullet(0)

        
class CallhomeMixedView(QWidget):
    def __init__(self, parent=None, name=None):
        QWidget.__init__(self, parent, name)

        self._layout = QGridLayout(self)

        self._text = CallhomeText(self)
        #self._text.setFile(Callhome())
        self._side = SeglistTextBulletBoard(self._text, self)

        self._layout.addWidget(self._side, 0,0)
        self._layout.addWidget(self._text, 0,1)
        

    # interface to QWave
    def setQWave(self, qwave):
        self.connect(qwave, SIGNAL("setRegion(int,int,int)"),
                     self.changeSpan)
        self._qwave = qwave
        self._text.setQWave(qwave)

    def changeSpan(self, a, b, c):
        x = self._qwave.frm2time(a)
        y = self._qwave.frm2time(b)
        s,t = self._text.changeSpan(x, y, c)
        if s != x or t != y:
            a = self._qwave.time2frm(s)
            b = self._qwave.time2frm(t)
            self._qwave.castSetRegionNoEcho(a,b,c)

    # interface to higher level application
    def load(self, filename):
        return self._text.load(filename)

    def newFile(self):
        self._text.newFile()
        
    def newSegment(self):
        if self._text is not None:
            self._text.createSegmentForCurrentRegion()

    def rememberCurrentSegment(self):
        self._text.rememberCurrentSegment()

    def forgetCurrentSegment(self):
        self._text.forgetCurrentSegment()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    s = SeglistView()
    s.load(sys.argv[1])
    
    s.show()
    
    app.setMainWidget(s)
    app.exec_loop()
