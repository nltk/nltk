
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
        Annotation.__init__(self, *args, **kw)
        self.flagIgnoreCallback = False
        
class Seglist(Callhome, AnnotationSet):
    __slots__ = ()

    def __init__(self, *args, **kw):
        AnnotationSet.__init__(self, *args, **kw)
        self.Annotation = Segment
        self.AnnotationSet = AnnotationSet


class SeglistTextView(QGrid):
    def __init__(self, annSet=None, parent=None, name=None):
        QGrid.__init__(self, 2, parent, name)

        # speaker code
        self.spkrCode = speakercode.SpeakerCode()

        # bullet board
        self.side = QCanvasView(self)
        self.side.setFrameShape(QFrame.NoFrame)
        self.side.setFixedWidth(20)
        self.side.setVScrollBarMode(QScrollView.AlwaysOff)
        self.side.setHScrollBarMode(QScrollView.AlwaysOff)
        
        # initialize text widget
        self.text = QMultiLineEdit(self)
        self.text.clear()
        self.anns = []
        
        if annSet is None:
            self.annSet = Seglist()
        else:
            self.annSet = annSet
            for ann in self.getSortedAnnotationSet():
                self.appendSegment(ann)

        # bullet canvas
        self.canvas = QCanvas(self.side)
        self.canvas.setBackgroundColor(Qt.lightGray)
        self.side.setCanvas(self.canvas)
        self.connect(self.text.verticalScrollBar(),
                     SIGNAL("valueChanged(int)"),
                     self._paintBullet)
        
        # set agwrap callbacks
        self.annSet.setAddCallback2(self.addSegment)
        self.annSet.setRemoveCallback(self.deleteSegment)
        self.annSet.setChangeCallback2(self.setSegment)


    def _paintBullet(self, v):
        
        for item in self.canvas.allItems():
            item.setCanvas(None)
            del item

        bulletWidth = self.side.width()
        cy = self.text.contentsY()
        viewportBottom = self.text.contentsHeight()
        para = self.text.paragraphAt(QPoint(0,cy))
        paraNum = len(self.anns)

        while para < paraNum:
            r = self.text.paragraphRect(para)
            top = self.text.contentsToViewport(r.topLeft()).y()
            height = r.height()
            color = QColor(self.spkrCode.color(self.anns[para]["SPKR"]))

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
        

    ###############################
    def getSortedAnnotationSet(self):
        anns = self.annSet.getAnnotationSet(TYPE='segment')
        anns.sort(lambda a,b:cmp(a.start,b.start))
        return anns
    
    ###############################

    
    def appendSegment(self, seg):
        try:
            self.text.append(seg["TEXT"])
        except KeyError:
            self.text.append("")
        self.anns.append(seg)

    def addSegment(self, seg):
        if seg.flagIgnoreCallback: return
        anns = self.getSortedAnnotationSet()
        i = anns.index(seg)
        if i == self.text.numLines():
            # this prevents an empty line being added at the end
            self.text.append(seg['TEXT'])
            anns.append(seg)
        else:
            self.text.insertLine(seg['TEXT'], i)
            anns.insert(i, seg)
        self.anns = anns
    
    def deleteSegment(self, seg):
        if seg.flagIgnoreCallback: return
        anns = self.getSortedAnnotationSet()
        try:
            i = anns.index(seg)
            self.text.removeLine(i)
            del anns[i]
        except ValueError:
            pass
        self.anns = anns

    def setSegment(self, seg, *args):
        """
        args could be:
        ("feature", name, value)
        ("start", start_offset)
        ("end", end_offset)
        """
        if seg.flagIgnoreCallback: return
        if args[0] == "feature":
            if args[1] == "TEXT":
                i = self.anns.index(seg)
                self.text.setSelection(i,0,i,self.text.paragraphLength(i))
                self.text.removeSelectedText()
                self.text.insertAt(seg["TEXT"], i, 0)
    
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    annset = Seglist()
    annset.load(sys.argv[1])
    s = SeglistTextView(annset)
    

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
