from qt import *

class CallhomeBoxView(QGrid):
    def __init__(self, parent=None, name=None):
        QGrid.__init__(self, 1, parent, name)
        
    def setFile(self, data):
        for ann in data:
            print ann
