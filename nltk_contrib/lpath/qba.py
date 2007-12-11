import sys
import os
from qt import *
from qtcanvas import *
from treecanvas import *
from treecanvasview import *
from lpathtree_qt import *
from axis import *
from db import *
from dbdialog import *
from sqlviewdialog import *
from overlay import *
from translator import translate
from parselpath import parse_lpath
from lpath import tokenize

class QBA(QMainWindow):
    def __init__(self, tree=None):
        QMainWindow.__init__(self)

        self.setCaption("LPath QBA")
        self.statusBar()   # create a status bar
        self.db = None
        self.queryTree = None  # tree on which LPath query was built
        self.overlayIdx = None
        self.overlays = None
        self.treecanvas = None
        
        menuBar = self.menuBar()
        menu_File = QPopupMenu(menuBar)
        menu_File.insertItem("Save image", self.menu_File_SaveImage)
        menu_File.insertSeparator()
        menu_File.insertItem("E&xit", qApp, SLOT("closeAllWindows()"))
        menu_View = QPopupMenu(menuBar)
        menu_View.insertItem("&SQL Translation", self.menu_View_SqlTranslation)
        menu_Tools = QPopupMenu(menuBar)
        menu_Tools.insertItem("Connect to Database", self.menu_Tools_SetupDatabase)
        menu_Tools.insertItem("Select LPath table", self.menu_Tools_SelectLPathTable)
        menuBar.insertItem("&File", menu_File)
        menuBar.insertItem("&View", menu_View)
        menuBar.insertItem("&Tools", menu_Tools)

        self.cw = QWidget(self)
        self.setCentralWidget(self.cw)
        self.layout = QGridLayout(self.cw)
        self.treeview = TreeCanvasView(self.cw)
        self.layout.addWidget(self.treeview,2,1)
        self.layout.setRowStretch(2,1)

        if tree:
            self.setTree(tree)
            
        hbox = QHBox(self.cw)
        hbox.setSpacing(2)
        hbox.setMargin(3)
        QLabel("LPath\nQuery:", hbox)
        self.entQuery = QTextView(hbox)
        self.entQuery.setFixedHeight(40)
        self.btnQuery = QPushButton("Submit Query", hbox)
        self.btnQuery.setFixedHeight(40)
        self.layout.addWidget(hbox, 1, 1)
        self.layout.setRowStretch(1,0)

        self.toolPanel = QDockWindow(self)
        self.bgrpTools = QButtonGroup(1, Qt.Horizontal, self.toolPanel)
        self.toolPanel.setWidget(self.bgrpTools)
        self.addDockWindow(self.toolPanel, Qt.DockLeft)

        self.bgrpTools.setExclusive(True)
        self.btnClear = QPushButton("Clear", self.bgrpTools)
        self.btnNextTree = QPushButton("Next tree", self.bgrpTools)
        self.btnNextMatch = QPushButton("Next match", self.bgrpTools)
        self.btnNextTree.setEnabled(False)

        self.connect(self.btnClear, SIGNAL("clicked()"), self.clearDisplay)
        self.connect(self.btnQuery, SIGNAL("clicked()"), self.query)
        self.connect(self.btnNextTree, SIGNAL("clicked()"), self.fetchNextTree)
        self.connect(self.btnNextMatch, SIGNAL("clicked()"), self.displayNextOverlay)
        self.connect(self.treeview, PYSIGNAL("changed"), self._setLPath)
        self.connect(self.treeview, PYSIGNAL("highlightLPath"), self._setLPathColor)

        self._saveImageDir = None  # remember the last "save image" directory
        self._queryJustSubmitted = False
        
    def clearDisplay(self):
        self.treeview.clear()
        self.entQuery.clear()
        
    def query(self):
        if self.db is not None:            
            if not self.treeview.canvas(): return
            t = self.treeview.canvas().getTreeModel()
            lpath = translate(t)
            if lpath is None: return

            self.disconnect(self.db.emitter, PYSIGNAL("gotMoreTree"), self.gotMoreTree)

            self._queryJustSubmitted = True
            self.statusBar().message("Submitted the query. Please wait...")
            self.btnNextTree.setEnabled(False)
            if self.db.submitQuery(lpath) == True:
                self.queryTree = parse_lpath(lpath)
            else:
                self.statusBar().message("Query failed.")

    def _setLPath(self):
        t = self.treeview.canvas().getTreeModel()
        lpath = translate(t,space=' ')
        if lpath is None:
            self.entQuery.setText('')
        else:
            self.entQuery.setText(lpath)
    
    def _setLPathColor(self, s):
        self.entQuery.setText(s)
        
    def fetchNextTree(self):
        if self.db:
            res = self.db.fetchNextTree()
            if not res: return
            
            sid, tid, sql, t, ldb, sql2 = res
            self.setCaption("LPath QBA: Tree %s" % sid)
            self.setTree(t)
            self.overlays = find_overlays(sql2, ldb, self.queryTree, t)
            self.overlayIdx = len(self.overlays)-1
            self.displayNextOverlay()

            n = self.db.getNumTreesInMem()
            self.btnNextTree.setText("Next tree (%d)" % n)
            if n == 0:
                self.btnNextTree.setEnabled(False)
                
    def setLineShapeFollowing(self):
        self.treeview.overrideLineShape(AxisFollowing)
    def setLineShapeImmFollowing(self):
        self.treeview.overrideLineShape(AxisImmediateFollowing)
    def setLineShapeSibling(self):
        self.treeview.overrideLineShape(AxisSibling)
    def setLineShapeImmSibling(self):
        self.treeview.overrideLineShape(AxisImmediateSibling)
    def setLineShapeParent(self):
        self.treeview.overrideLineShape(AxisParent)
    def setLineShapeAncestor(self):
        self.treeview.overrideLineShape(AxisAncestor)
        
    def setTree(self, treemodel):
        self.treecanvas = TreeCanvas(treemodel)
        self.treeview.setCanvas(self.treecanvas)
        self.connect(self.treecanvas,PYSIGNAL('treeUpdated'),self._treeUpdated)
        #self.treecanvas.setData(treemodel)

    def _treeUpdated(self, *args):
        self._setLPath()
        
    # menu callbacks
    def menu_File_SaveImage(self):
        if self.treecanvas is None:
            QMessageBox.warning(self, "No image available",
                                "There is not tree image to save.")
            return
        pixmap = self.treecanvas.getAsPixmap()
        d = QFileDialog(self, None, True)
        d.setCaption("Save As")
        d.setMode(QFileDialog.AnyFile)
        if self._saveImageDir:
            d.setDir(self._saveImageDir)
        d.setFilters("PNG (*.png);;"
                     "JPEG (*.jpg);;"
                     "BMP (*.bmp);;"
                     "XPM (*.xpm)")
        if d.exec_loop() == QDialog.Rejected: return
        filenam = d.selectedFile()
        filenam = unicode(filenam)
        self._saveImageDir = os.path.dirname(filenam)
        if os.path.exists(filenam):
            res = QMessageBox.question(
                     self,
                     "Error",
                     "File already exists.\n\n%s\n\n"
                     "It will be overwritten." % filenam,
                     QMessageBox.Ok,
                     QMessageBox.Cancel
                     )
            if res == QMessageBox.Cancel: return
        filter = d.selectedFilter()
        fmt = str(filter).split()[0]
        res = pixmap.save(filenam, fmt)
        if res == False:
            QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to save image as:\n\n%s" % filenam)

    def menu_View_SqlTranslation(self):
        t = self.treeview.canvas().getTreeModel()
        q = translate(t)
        if q.strip():
            d = SqlViewDialog(lpql=q, parent=self)
            d.exec_loop()
        
    def menu_Tools_SetupDatabase(self):
        d = DatabaseConnectionDialog(parent=self)
        if d.exec_loop():
            self.statusBar().message("Connecting to the database...")
            self.db = d.getLPathDb()
            self.statusBar().message("Connecting to the database... ok", 150)
            self.db.connectToEvent(self.db.EVENT_MORE_TREE, self)
            tables = self.db.listTables()
            if len(tables) > 1:
                self.menu_Tools_SelectLPathTable()
            elif len(tables) == 1:
                msg = "Accessing table %s. Please wait..." % tables[0]
                self.statusBar().message(msg)
                self.db.switchLPathTable(tables[0])
                self._queryJustSubmitted = True
        else:
            self.db = None

    def menu_Tools_SelectLPathTable(self):
        # check if self.tables is not empty
        if self.db:
            d = TableSelectionDialog(self.db.listTables())
            if d.exec_loop():
                table = d.getSelectedTable()
                msg = "Accessing table %s. Please wait..." % table
                self.statusBar().message(msg)
                self.db.switchLPathTable(table)
                self._queryJustSubmitted = True
        else:
            QMessageBox.warning(self, "No DB connection",
                                "Connect to a database first.")

    def customEvent(self, e):
        if self.db and e.type()==self.db.EVENT_MORE_TREE:
            self.gotMoreTree(e.data())
        
    def gotMoreTree(self, numTrees):
        self.statusBar().clear()
        self.btnNextTree.setText("Next tree (%d)" % numTrees)
        if numTrees == 0:
            self.btnNextTree.setEnabled(False)
        else:
            self.btnNextTree.setEnabled(True)
            if numTrees == 1 and self._queryJustSubmitted:
                self.statusBar().message("Received the first tree.", 300)
                self.fetchNextTree()
        self._queryJustSubmitted = False
            
    def displayNextOverlay(self):
        if self.overlays:
            self.overlays[self.overlayIdx].clear()
            self.overlayIdx = (self.overlayIdx + 1) % len(self.overlays)
            self.overlays[self.overlayIdx].display()
            self.btnNextMatch.setText("Next match (%d/%d)" % \
                                      (self.overlayIdx+1, len(self.overlays)))
            self._setLPath()

def main():
    app = QApplication(sys.argv)
    w = QBA()
    app.setMainWidget(w)
    if len(sys.argv) == 2:
        generator = LPathTreeModel.importTreebank(file(sys.argv[1]))
        w.setTree(generator.next())
    w.show()
    w.setCaption('LPath QBA')   # this is only necessary on windows
    app.exec_loop()

if __name__ == "__main__":
    main()
