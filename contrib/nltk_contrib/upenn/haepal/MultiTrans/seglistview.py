
from qt import *
from qtcanvas import *
from agwrap import *
from format.callhome import Callhome
import speakercode

"""
Design overview
---------------

       ,--------->  AnnotationSet
       |
       | user            | 
       | modified        |  3 editing operations (insert, delete, set)
       | something       |    plus querying operations
       | on disp.        v 
       |
       `--------------  Views (bulletted text view,
                               horizontal box (sinc'ed with QWave) view, etc.)

                         ^^^
                         |||  segment selection
                         |||  span changes
                         vvv

                        QWave


Seglist is just a list of segments with some smart behaviours.

Seglist needs to be a QObject to handle signal-slot stuff.

"""


class Segment(Annotation):
    __slots__ = ('flagIgnoreCallback')

    def __init__(self, *args, **kw):
        if 'TYPE' not in kw:
            kw['TYPE'] = 'segment'
        if 'TEXT' not in kw:
            kw['TEXT'] = ''
        Annotation.__init__(self, *args, **kw)
        self.flagIgnoreCallback = False
        
    def setStart(self, t):
        print t
        Annotation.setStart(self, t)

    def setEnd(self, t):
        print t
        Annotation.setEnd(self, t)
        
    start = property(Annotation.getStart, setStart)
    end = property(Annotation.getEnd, setEnd)

class Seglist(Callhome, AnnotationSet):
    __slots__ = ()

    def __init__(self, *args, **kw):
        AnnotationSet.__init__(self, *args, **kw)
        self.Annotation = Segment
        self.AnnotationSet = AnnotationSet

    def add(self, seg):
        ch = seg['SPKR']
        for ann in self:
            if ann['SPKR']==ch and seg.overlaps(ann):
                raise ValueError("can't add overlapping segment: " + str(seg))
        self.AnnotationSet.add(self, seg)

class SeglistText(QTextEdit):
    def __init__(self, annSet=None, parent=None, name=None):
        QTextEdit.__init__(self, parent, name)

        self.clear()
        self.anns = []
        self._seglock = None

        if annSet is None:
            self.annSet = Seglist()
        else:
            self.annSet = annSet
            for ann in self.getSortedAnnotationSet():
                self.appendSegment(ann)

        # set agwrap callbacks
        self.annSet.setAddCallback2(self.addSegment)
        self.annSet.setRemoveCallback(self.deleteSegment)
        self.annSet.setChangeCallback2(self.setSegment)

        self.connect(self, SIGNAL("clicked(int,int)"), self._clicked)


    def _empty(self):
        return self.anns == []

    def eventFilter(self, obj, e):
        """
        Eat any mouse event if a segment is locked.
        """
        if self._seglock is not None and \
           (e.type() == QEvent.MouseButtonPress or \
            e.type() == QEvent.MouseButtonRelease):
            return True
        else:
            return QTextEdit.eventFilter(self, obj, e)
        
    def keyPressEvent(self, e):
        if self._empty(): return
        
        k = e.key()

        p,c = self.getCursorPosition()

        if k == Qt.Key_Down and p == len(self.anns)-1:
            return

        if k == Qt.Key_Return:
            if self._seglock:
                self._seglock = None
            else:
                self._seglock = p
            return

        if self._seglock: return
        
        if k == Qt.Key_Up or k == Qt.Key_Down:
            QTextEdit.keyPressEvent(self, e)
            p,c = self.getCursorPosition()
            self.emit(PYSIGNAL("currentParagraphRegion(int,int,int)"),
                      (self.anns[p].start, self.anns[p].end,
                       self.anns[p]['CHANNEL']))
            return

        def propagateChanges():
            h0 = self.paragraphRect(p).height()

            QTextEdit.keyPressEvent(self, e)

            # don't update gui yet
            self.anns[p].flagIgnoreCallback = True
            self.anns[p]['TEXT'] = self.text(p)
            self.anns[p].flagIgnoreCallback = False

            # update gui if necessary
            if h0 != self.paragraphRect(p).height():
                self.emit(PYSIGNAL("paragraphHeightChanged()"), ())


        if k == Qt.Key_Delete:
            if e.state() == Qt.AltButton:
                self.annSet.remove(self.anns[p])
            elif c != self.paragraphLength(p):
                propagateChanges()
        elif k == Qt.Key_BackSpace:
            if c != 0:
                propagateChanges()
        else:
            propagateChanges()


    def _clicked(self, p, c):
        if self._empty(): return
        if p >= len(self.anns):
            p = len(self.anns) - 1
            self.setCursorPosition(p, self.paragraphLength(p))
        
        self.emit(PYSIGNAL("currentParagraphRegion(int,int,int)"),
                  (self.anns[p].start, self.anns[p].end,
                   self.anns[p]['CHANNEL']))
        
        
    

    def getSortedAnnotationSet(self):
        anns = self.annSet.getAnnotationSet(TYPE='segment')
        anns.sort(lambda a,b:cmp(a.start,b.start))
        return anns

    def getAnnotationSet(self):
        return self.annSet

    
    def appendSegment(self, seg):
        try:
            self.append(seg["TEXT"])
        except KeyError:
            self.append("")
        self.anns.append(seg)

    def addSegment(self, seg):
        if seg.flagIgnoreCallback:
            seg.flagIgnoreCallback = False  # ignored
            return
        anns = self.getSortedAnnotationSet()
        i = anns.index(seg)
        text = seg['TEXT']
        self.insertParagraph(text, i)
        self.anns = anns
        self.emit(PYSIGNAL("segmentAdded()"),())        # ... to the display
    
    def deleteSegment(self, seg):
        if seg.flagIgnoreCallback:
            seg.flagIgnoreCallback = False  # ignored
            return
        
        #anns = self.getSortedAnnotationSet()
        try:
            i = self.anns.index(seg)
            self.removeLine(i)
            del self.anns[i]
            self.emit(PYSIGNAL("segmentDeleted()"),())  # ... from the display
        except ValueError:
            pass
        #self.anns = anns

    def setSegment(self, seg, *args):
        """
        args could be:
        ("feature", name, value)
        ("start", start_offset)
        ("end", end_offset)
        """
        if seg.flagIgnoreCallback:
            seg.flagIgnoreCallback = False  # ignored
            return
        
        if args[0] == "feature":
            if args[1] == "TEXT":
                i = self.anns.index(seg)
                self.setSelection(i,0,i,self.paragraphLength(i))
                self.removeSelectedText()
                self.insertAt(seg["TEXT"], i, 0)
        elif args[0] == "start":
            i = self.anns.index(seg)
            anns = self.getSortedAnnotationSet()
            j = anns.index(seg)
            if i != j:
                self.removeParagraph(i)
                self.insert(seg["TEXT"], j)
                self.anns = anns

    def getCurrentSegment(self):
        if self._seglock is not None:
            return self.anns[self._seglock]
        else:
            return None

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
        paraNum = len(self.text.anns)

        while para < paraNum:
            r = self.text.paragraphRect(para)
            top = self.text.contentsToViewport(r.topLeft()).y()
            height = r.height()
            color = QColor(self.spkrCode.color(self.text.anns[para]["SPKR"]))

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

        
class SeglistView(QWidget):
    def __init__(self, annSet=None, parent=None, name=None):
        QWidget.__init__(self, parent, name)

        self._layout = QGridLayout(self)
        
        self._side = None
        self._text = None

    def castCurrentParagraphRegion(self, a, b, c):
        self.emit(PYSIGNAL("currentParagraphRegion(int,int,int)"), (a,b,c))

    def setCurrentAnnotationSpan(self, a, b, c):
        seg = self._text.getCurrentSegment()
        if seg is None: return
        #seg.flagIgnoreCallback = True
        seg.start, seg.end = a, b



    def setAnnotationSet(self, annSet):
        self._layout.remove(self._side)
        self._layout.remove(self._text)
        self._text = SeglistText(annSet, self)
        self._side = SeglistTextBulletBoard(self._text, self)
        self._layout.addWidget(self._side, 0,0)
        self._layout.addWidget(self._text, 0,1)
        self.connect(self._text, PYSIGNAL("currentParagraphRegion(int,int,int)"),
                     self.castCurrentParagraphRegion)
        self._text.show()
        self._side.show()

    def getAnnotationSet(self):
        if self._text is None:
            return None
        else:
            return self._text.getAnnotationSet()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    annset = Seglist()
    annset.load(sys.argv[1])
    s = SeglistView()
    

    ###
    seg = Segment(start=1000,end=1001,SPKR='A',TEXT='AAA')
    annset.add(seg)
    seg2 = Segment(start=27.10,end=27.56,SPKR='B',TEXT='BBB')
    annset.add(seg2)
    seg3 = Segment(start=1001,end=1002,SPKR='C',TEXT='CCC')
    annset.add(seg3)
    annset.remove(seg)
    seg2['TEXT'] = "test test test ..."
    ###
    
    s.show()
    
    app.setMainWidget(s)
    app.exec_loop()
