
import sys
import qt, qtcanvas
import QWave
from seglistview import *

class Waveform(QWave.QWave):

    def __init__(self, audiofile, parent=None, name=None):
        QWave.QWave.__init__(self, parent, name)
        self.openAudio(audiofile)

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

            sl = qt.QSlider(self)
            sl.setSizePolicy(qt.QSizePolicy.Maximum,qt.QSizePolicy.Minimum)
            sl.setRange(1,10);
            self.connect(sl,qt.SIGNAL("valueChanged(int)"),self.sl_changed)
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


if __name__ == '__main__':
    app = qt.QApplication(sys.argv)
    
    mw = qt.QMainWindow()

    grid = QGrid(1, mw)

    annset = Seglist()
    annset.load(sys.argv[1])
    text = SeglistView(annset, grid)

    wave = Waveform(sys.argv[2], grid)
    print wave.height()
    wave.setFixedHeight(240)

    ###
    def emitCastSetRegion(a,b,c):
        x = wave.time2frm(a)
        y = wave.time2frm(b)
        wave.castSetRegion(x, y, wave.ch2id[c])

    def createAnnotation(a,b,c):
        x = wave.frm2time(a)
        y = wave.frm2time(b)
        chchr = chr(ord('A')+c)
        seg = Segment(start=x,end=y,SPKR=chchr,CHANNEL=c)
        annset.add(seg)
        print x,y,c
        
    wave.connect(text, PYSIGNAL("currentParagraphRegion(int,int,int)"),
                 emitCastSetRegion)
    wave.connect(wave, SIGNAL("createAnnotation(int,int,int)"),
                 createAnnotation)
    ###
    
    mw.setCentralWidget(grid)
    
    app.setMainWidget(mw);
    mw.show()
    app.exec_loop()

