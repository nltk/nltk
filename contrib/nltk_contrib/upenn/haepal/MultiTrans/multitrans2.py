
import sys
from waveform import Waveform, QWave
from seglistview2 import *
import os.path

class PlayerControl(QHBoxLayout):
    def __init__(self, qwave):
        QHBoxLayout.__init__(self)

        lb1 = QWave.QWaveTimeLabel(qwave)
        lb2 = QWave.QWaveTimeLabel(qwave)
        lb3 = QWave.QWaveTimeLabel(qwave)
        lb4 = QWave.QWaveTimeLabel(qwave)
        lb5 = QWave.QWaveTimeLabel(qwave)

        lb1.setFrameStyle(QFrame.Box | QFrame.Sunken)
        lb2.setFrameStyle(QFrame.Box | QFrame.Sunken)
        lb3.setFrameStyle(QFrame.Box | QFrame.Sunken)
        lb4.setFrameStyle(QFrame.Box | QFrame.Sunken)
        #lb5.setFrameStyle(QFrame.Box | QFrame.Sunken)

        lb1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lb2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lb3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lb4.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #lb5.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lb1.setFixedWidth(80)
        lb2.setFixedWidth(80)
        lb3.setFixedWidth(80)
        lb4.setFixedWidth(80)

        btn1 = QPushButton(">", qwave)
        btn2 = QPushButton("R", qwave)
        btn3 = QPushButton("||", qwave)
        btn4 = QPushButton("X", qwave)

        btn1.setFixedSize(20,20)
        btn2.setFixedSize(20,20)
        btn3.setFixedSize(20,20)
        btn4.setFixedSize(20,20)

        btn1.setFocusPolicy(QWidget.NoFocus)
        btn2.setFocusPolicy(QWidget.NoFocus)
        btn3.setFocusPolicy(QWidget.NoFocus)
        btn4.setFocusPolicy(QWidget.NoFocus)

        self.addWidget(lb1)
        self.addWidget(lb2)
        self.addWidget(lb3)
        self.addWidget(lb4)
        self.addWidget(lb5)

        self.addWidget(btn1)
        self.addWidget(btn2)
        self.addWidget(btn3)
        self.addWidget(btn4)

        self.connect(qwave, SIGNAL("newCursorPos(int)"),lb1.setTime)
        self.connect(qwave, SIGNAL("setRegion(int,int,int)"),self.setRegion)
        self.connect(qwave, SIGNAL("playerCursorPos(int)"),
                     self.setPlayerCursorPos)
        
        self._qwave = qwave
        self._lb1 = lb1
        self._lb2 = lb2
        self._lb3 = lb3
        self._lb4 = lb4
        self._lb5 = lb5
        
        self.playButton = btn1
        self.repeatButton = btn2
        self.pauseButton = btn3
        self.stopButton = btn4

    def setRegion(self, a, b, c):
        if a < 0 or a > b:
            self._lb2.clear()
            self._lb3.clear()
            self._lb4.clear()
        else:
            self._lb2.setTime(a)
            self._lb3.setTime(b)
            self._lb4.setTime(b-a)

    def setPlayerCursorPos(self, f):
        self._cursorPos = f
        self._lb1.setTime(f)
        
    def getPlayerCursorPos(self):
        return self._cursorPos

    
class MyGrid(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        self._layout = QGridLayout(self)


class MultiTrans(QMainWindow):

    class ShiftFilter(QObject):
        def __init__(self, parent=None, name=None):
            QObject.__init__(self, parent, name)
            self.parent = parent
        
        def eventFilter(self, obj, e):
            typ = e.type()
            if typ == QEvent.KeyPress:
                if e.key() == Qt.Key_Shift:
                    self.parent._text.rememberCurrentSegment()
            elif typ == QEvent.KeyRelease:
                if e.key() == Qt.Key_Shift:
                    self.parent._text.forgetCurrentSegment()
            return False

    def __init__(self, *args):
        QMainWindow.__init__(self, *args)

        self._buildMenu()

        self._grid = QVBox(self)
        self._text = CallhomeMixedView(parent=self._grid)
        self._grid.setStretchFactor(self._text, 1)

        self._wave = None
        self._playerControl = None

        self.setCentralWidget(self._grid)

        self._setKeyControls()
        self._eventFilter = MultiTrans.ShiftFilter(self)
        self.installEventFilter(self._eventFilter)

    # menu
    def _buildMenu(self):
        fileMenu = QPopupMenu(self)
        fileMenu.insertItem("New Transcript", self._fileMenu_NewTrans)
        fileMenu.insertItem("Open Transcript", self._fileMenu_OpenTrans)
        fileMenu.insertItem("Open Audio", self._fileMenu_OpenAudio)
        fileMenu.insertItem("Exit", self._fileMenu_Exit)
        self.menuBar().insertItem("File", fileMenu)

    def _fileMenu_NewTrans(self):
        # ask if user wants to save the file
        self._text.newFile()
    
    def _fileMenu_OpenTrans(self):
        filename = QFileDialog.getOpenFileName().ascii()
        if filename is None: return     # canceled

        self._text.load(filename)

        
    def _fileMenu_OpenAudio(self):
        filename = QFileDialog.getOpenFileName().ascii()
        if filename is None: return     # canceled

        if self._wave is not None:
            self._wave.closeAudio()

        # load waveform
        self._wave = Waveform(filename, self._grid)

        # set up player control
        self._playerControl = PlayerControl(self._wave)
        self._wave.addLayout(self._playerControl, 0, 1)
        self.connect(self._playerControl.playButton, SIGNAL("clicked()"),
                     self._waveformPlay)
        self.connect(self._playerControl.repeatButton, SIGNAL("clicked()"),
                     self._waveformRepeat)
        self.connect(self._playerControl.pauseButton, SIGNAL("clicked()"),
                     self._waveformTogglePause)
        self.connect(self._playerControl.stopButton, SIGNAL("clicked()"),
                     self._waveformStop)
        
        self._wave.show()

        # inform text widget of creatioin of new waveform
        self._text.setQWave(self._wave)
        

    def _fileMenu_Exit(self):
        QApplication.exit(0)

    # user interface
    def _setKeyControls(self):
        a = QAccel(self)
        a.connectItem(a.insertItem(Qt.Key_Insert+Qt.ALT),
                      self._createSegment)
        a.connectItem(a.insertItem(Qt.Key_M+Qt.ALT),
                      self._createSegment2)
        self._segmentStarted = False
        a.connectItem(a.insertItem(Qt.Key_A+Qt.ALT),
                      self._waveformZoomIn)
        a.connectItem(a.insertItem(Qt.Key_X+Qt.ALT),
                      self._waveformZoomIn2)
        a.connectItem(a.insertItem(Qt.Key_Z+Qt.ALT),
                      self._waveformZoomOut)
        a.connectItem(a.insertItem(Qt.Key_Space+Qt.ALT),
                      self._waveformPlay)
        a.connectItem(a.insertItem(Qt.Key_Tab+Qt.ALT),
                      self._waveformTogglePause)
        self._playing = False
        self._paused = False
      
    def _createSegment(self):
        if self._text is not None:
            self._text.newSegment()

    def _createSegment2(self):
        if self._segmentStarted:
            b = self._playerControl.getPlayerCursorPos()
            c = self._wave.getSelectedRegionWaveformId()
            self._wave.castSetRegion(self._segmentStart, b, c)
            self._createSegment()
            self._segmentStarted = False
        else:
            a = self._segmentStart = self._playerControl.getPlayerCursorPos()
            c = self._wave.getSelectedRegionWaveformId()
            self._wave.castSetRegion(a, a, c)
            self._segmentStarted = True
            
    def _waveformZoomIn(self):
        if self._wave is not None:
            self._wave.castZoomIn(self._wave.startf() + self._wave.widthf()/2)

    def _waveformZoomIn2(self):
        if self._wave is not None:
            c, a, b = self._wave.getSelectedRegionF()
            self._wave.castZoomIn2(a, b)

    def _waveformZoomOut(self):
        if self._wave is not None:
            self._wave.castZoomOut(self._wave.startf() + self._wave.widthf()/2)

    def _waveformPlay(self):
        self._segmentStarted = False
        
        self._playing = False
        self._playerControl.pauseButton.setText("||")
        self._wave.stopAudio()
        self._wave.playAudio()
        self._playing = True

    def _waveformRepeat(self):
        self._paused = False
        self._playerControl.pauseButton.setText("||")
        self._wave.stopAudio()
        self._wave.repeatAudio()
        self._playing = True

    def _waveformTogglePause(self):
        if self._playing:
            self._playerControl.pauseButton.setText("=")
            self._wave.pauseAudio()
            self._playing = False
            self._paused = True
        elif self._paused:
            self._playerControl.pauseButton.setText("||")
            self._wave.unpauseAudio()
            self._playing = True
            self._paused = False

    def _waveformStop(self):
        self._paused = False
        self._playerControl.pauseButton.setText("||")
        self._wave.stopAudio()
        self._palying = False
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    mw = MultiTrans()

    app.setMainWidget(mw);
    mw.show()
    app.exec_loop()

