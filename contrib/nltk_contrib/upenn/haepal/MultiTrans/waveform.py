
from qt import *
import qtcanvas
import QWave

class Waveform(QWave.QWave):

    def __init__(self, filename, parent=None, name=None):
        QWave.QWave.__init__(self, parent, name)
        self.setFocusPolicy(self.NoFocus)
        if not self.openAudio(filename): return

        #
        #   0 1 2
        # 0   T
        # 1   S
        # 2   R
        # 3 V W A
        # 4
        # 5 V W A
        # 6
        #
        # T - toolbar
        # S - scrollbar
        # R - horizontal ruler
        # V - vertical ruler
        # W - waveform display
        # A - amplitude slider
        #
        i = 3
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

            i += 2
            ch += 1

        self.sb = QWave.QWaveScrollBar(self)
        self.addWidget(self.sb,1,1)
            
        self.ruler = QWave.QWaveRuler(self, True)
        self.addWidget(self.ruler,2,1)

        self.nextrow = i
        

    def getNextRow(self):
        return self.nextrow
    
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
    
