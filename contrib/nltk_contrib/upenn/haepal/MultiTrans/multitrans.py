
import sys
import qtcanvas
import QWave
from seglistview import *
import os.path

class Waveform(QWave.QWave):

    def __init__(self, filename, parent=None, name=None):
        QWave.QWave.__init__(self, parent, name)
        if not self.openAudio(filename): return

        self.toolbar = QWave.QWaveToolBar(self)
        self.addLayout(self.toolbar,0,1)

        i = 1
        ch = 0
        self.vrs = []
        self.slmap = {}
        self.ch2id = {}
        while ch < self.getInputChannels():
            id = self.addWaveform(ch,i,1)
            self.ch2id[ch] = id

            vr = QWave.QWaveVRuler(self,id)
            self.addWidget(vr,i,0)
            self.vrs.append(vr)

            sl = QSlider(self)
            sl.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Minimum)
            sl.setRange(1,10);
            self.connect(sl,SIGNAL("valueChanged(int)"),self.sl_changed)
            self.addWidget(sl,i,2)
            self.slmap[sl] = id

            i += 1
            ch += 1
            
        self.ruler = QWave.QWaveRuler(self)
        self.addWidget(self.ruler,i,1)
        i += 1

        self.sb = QWave.QWaveScrollBar(self)
        self.addWidget(self.sb,i,1)

    def sl_changed(self, v):
        sl = self.sender()
        self.castWaveformAmplitude(self.slmap[sl],v)

        
class MyGrid(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        self._layout = QGridLayout(self)

    
class MultiTrans(QMainWindow):
    def __init__(self, *args):
        QMainWindow.__init__(self, *args)

        self._buildMenu()

        self._grid = QVBox(self)
        self.annset = None
        self.text = SeglistView(parent=self._grid)
        self.wave = None
        self._grid.setStretchFactor(self.text, 1)

        self.connect(self.text,
                     PYSIGNAL("currentParagraphRegion(int,int,int)"),
                     self._emitCastSetRegion)

        self.setCentralWidget(self._grid)

    def _buildMenu(self):
        fileMenu = QPopupMenu(self)
        fileMenu.insertItem("New Transcript", self._fileMenu_NewTrans)
        fileMenu.insertItem("Open Transcript", self._fileMenu_OpenTrans)
        fileMenu.insertItem("Open Audio", self._fileMenu_OpenAudio)
        fileMenu.insertItem("Exit", self._fileMenu_Exit)
        self.menuBar().insertItem("File", fileMenu)

    def _emitCastSetRegion(self, a,b,c):
        if self.wave is not None:
            x = self.wave.time2frm(a)
            y = self.wave.time2frm(b)
            self.wave.castSetRegion(x, y, self.wave.ch2id[c])

    def _createAnnotation(self, a,b,c):
        if self.text is not None:
            x = self.wave.frm2time(a)
            y = self.wave.frm2time(b)
            chchr = chr(ord('A')+c)
            seg = Segment(start=x,end=y,SPKR=chchr,CHANNEL=c)
            self.annset.add(seg)
            print x,y,c

    def _changeAnnotationSpan(self, a, b, c):
        if self.text is not None:
            x = self.wave.frm2time(a)
            y = self.wave.frm2time(b)
            self.text.setCurrentAnnotationSpan(x, y, c)

    def _fileMenu_NewTrans(self):
        self.annset = Seglist()
        self.text.setAnnotationSet(self.annset)
    
    def _fileMenu_OpenTrans(self):
        filename = QFileDialog.getOpenFileName().ascii()
        if filename is None: return     # canceled

        self.annset = Seglist()
        self.text.setAnnotationSet(self.annset)
        self.annset.load(filename)
        
    def _fileMenu_OpenAudio(self):
        filename = QFileDialog.getOpenFileName().ascii()
        if filename is None: return     # canceled

        del self.wave  # this also releases the audio device,
                       # avoiding a deadlock condition
        self.wave = Waveform(filename, self._grid)
        self.wave.show()

        self.connect(self.wave, SIGNAL("createAnnotation(int,int,int)"),
                     self._createAnnotation)
        self.connect(self.wave, SIGNAL("setRegion(int,int,int)"),
                     self._changeAnnotationSpan)

        
    def _fileMenu_Exit(self):
        QApplication.exit(0)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    mw = MultiTrans()

    app.setMainWidget(mw);
    mw.show()
    app.exec_loop()

