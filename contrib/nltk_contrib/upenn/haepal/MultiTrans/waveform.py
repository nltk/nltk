
from qt import *
import qtcanvas
import QWave

class Waveform(QWave.QWave):

    def __init__(self, filename, parent=None, name=None):
        QWave.QWave.__init__(self, parent, name)
        self.setFocusPolicy(self.NoFocus)
        if not self.openAudio(filename): return

        # 0-th row is reserved for a tool bar

        i = 1
        ch = 0
        self.vrs = []
        self.slmap = {}
        self.ch2id = {}
        while ch < self.getInputChannels():
            print i
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


    ### slots
    def sl_changed(self, v):
        sl = self.sender()
        self.castWaveformAmplitude(self.slmap[sl],v)


    ### convenience functions
    def getSelectedRegionS(self):
        return (self.getSelectedRegionWaveformId(),
                self.frm2time(self.getSelectedRegionStartFrame()),
                self.frm2time(self.getSelectedRegionEndFrame()))

    def getSelectedRegionF(self):
        return (self.getSelectedRegionWaveformId(),
                self.getSelectedRegionStartFrame(),
                self.getSelectedRegionEndFrame())

    def markRegionS(self, ch, beg, end):
        x = self.time2frm(beg)
        y = self.time2frm(end)
        
        s = self.startf()
        w = self.widthf()
        if x < s or y > s+w:
            s = (x + y - w) / 2
            if s < 0:
                s = 0
            elif s + w > self.frames():
                s = self.frames() - w
            self.castSetWaveformWindow(s, w)
            
        self.castSetRegion(x, y, ch)
    
