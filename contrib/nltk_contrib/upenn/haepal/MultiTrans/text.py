
from qt import *
from agwrap import *

"""
Design overview
---------------

                       Seglist

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

class Segment(QObject):
    pass
    
    
class Seglist(QObject):
    def __init__(self, parent=None, name=None):
        QObject.__init__(self, parent, name)
        self._seglist = AnnotationSet()


class SeglistTextView(QMultiLineEdit):
    def __init__(self, parent=None, name=None):
        QMultiLineEdit.__init__(self, parent, name)

    def keyPressEvent(self, e):
        pass

    ###############################
    
    def addSegment(self, seg):
        """
        seg - nltk.Token() with SpanLocation
        """
        
        pass

    def newSegment(self):
        pass
    
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    s = SegmentList()


    s.show()
    app.setMainWidget(s)
    app.exec_loop()
