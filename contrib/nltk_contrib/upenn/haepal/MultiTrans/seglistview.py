
from qt import *
from qtcanvas import *
from agwrap import *
from format.callhome import Callhome
import speakercode

"""
Design overview
---------------

                    AnnotationSet

                         | ^
              'Changed'  | | 3 editing operations (insert, delete, set)
                 signal  | |   plus querying operations
                         v |

                        Views (bulletted text view,
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
        
class Seglist(Callhome, AnnotationSet):
    __slots__ = ()

    def __init__(self, *args, **kw):
        AnnotationSet.__init__(self, *args, **kw)
        self.Annotation = Segment
        self.AnnotationSet = AnnotationSet


class SeglistText(QMultiLineEdit):
    def __init__(self, annSet=None, parent=None, name=None):
        QMultiLineEdit.__init__(self, parent, name)

        self.clear()
        self.anns = []

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

    def keyPressEvent(self, e):
        k = e.key()

        if k == Qt.Key_Up or k == Qt.Key_Down:
            QMultiLineEdit.keyPressEvent(self, e)
            p,c = self.getCursorPosition()
            self.emit(PYSIGNAL("currentParagraphRegion(int,int,int)"),
                      (self.anns[p].start, self.anns[p].end,
                       self.anns[p]['CHANNEL']))
            return
        elif k == Qt.Key_Return:
            print "return"
            return

        p,c = self.getCursorPosition()
        def propagateChanges():
            h0 = self.paragraphRect(p).height()

            QMultiLineEdit.keyPressEvent(self, e)

            # don't update gui yet
            self.anns[p].flagIgnoreCallback = True
            self.anns[p]['TEXT'] = self.textLine(p)
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
        self.emit(PYSIGNAL("currentParagraphRegion(int,int,int)"),
                  (self.anns[p].start, self.anns[p].end,
                   self.anns[p]['CHANNEL']))
        
        
    
    ###############################
    def getSortedAnnotationSet(self):
        anns = self.annSet.getAnnotationSet(TYPE='segment')
        anns.sort(lambda a,b:cmp(a.start,b.start))
        return anns

    ###############################

    
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
        if i == self.numLines():
            # this prevents an empty line being added at the end
            self.append(seg['TEXT'])
            #anns.append(seg)
        else:
            self.insertLine(seg['TEXT'], i)
            #anns.insert(i, seg)
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
        
        # speaker code
        self._spkrCode = speakercode.SpeakerCode()

        # initialize text widget
        self._text = SeglistText(annSet, self)

        # bullet board
        self._side = SeglistTextBulletBoard(self._text, self)
        
        self._layout.addWidget(self._side, 0,0)
        self._layout.addWidget(self._text, 0,1)

        self.connect(self._text, PYSIGNAL("currentParagraphRegion(int,int,int)"),
                     self.emitCurrentParagraphRegion)

    def emitCurrentParagraphRegion(self, a, b, c):
        self.emit(PYSIGNAL("currentParagraphRegion(int,int,int)"), (a,b,c))

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    annset = Seglist()
    annset.load(sys.argv[1])
    s = SeglistView(annset)
    

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
