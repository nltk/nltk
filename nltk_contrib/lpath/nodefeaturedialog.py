from qt import *
from at_lite import TableModel, TableEdit
import lpath

class NodeFeatureDialog(QDialog):
    def __init__(self, node, parent):
        QDialog.__init__(self, parent)
        self.setCaption('Node Attribute Dialog')
        self.resize(320,240)
        
        tab = TableModel([("Name",unicode),("Value",unicode)])
        tab.insertRow(None, ['label',node.data['label']])
        if '@func' in node.data:
            for v in node.data['@func']:
                tab.insertRow(None, ['@func',v])
        if 'lpathFilter' in node.data:
            tab.insertRow(None, ['filter', node.data['lpathFilter']])
        
        if node.children:
            tv = QVBox(self)
            QLabel("n      - add a new filter expression", tv)
            QLabel("Insert - add a new 'function' attribute ", tv)
            QLabel("Delete - delete an attribute", tv)
            font = QFont('typewriter')
            font.setFixedPitch(True)
            tv.setFont(font)
            tv.setMargin(10)
        
        hbox = QHBox(self)
        bOk = QPushButton("&OK", hbox)
        bCancel = QPushButton("&Cancel", hbox)
        hbox.setMargin(5)
        hbox.setSpacing(10)

        te = TableEdit(self)
        te.setData(tab)
        te.setColumnReadOnly(0,True)
        te.setColumnStretchable(1,True)
        
        self.connect(bOk, SIGNAL("clicked()"), self.slotOk)
        self.connect(bCancel, SIGNAL("clicked()"), self.slotCancel)
        self.connect(tab.emitter, PYSIGNAL("cellChanged"), self.validateFilter)
        
        layout = QVBoxLayout(self)
        layout.addWidget(te)
        if node.children: layout.addWidget(tv)
        layout.addWidget(hbox)
        layout.setSpacing(5)
        layout.setMargin(5)
        
        self.tab = tab
        self.te = te
        self.node = node
        self.filterOK = True
        
    def slotOk(self):
        if self.filterOK == False:
            QMessageBox.critical(self, "Error", "Invalid filter expression.")
            return
        f = []
        for name in ('label','@func','lpathFilter'):
            try:
                del self.node.data[name]
            except KeyError:
                pass
        for row in self.tab:
            if row['Name'] == 'label':
                self.node.label = row['Value']
            elif row['Name'] == '@func':
                f.append(row['Value'])
            elif row['Name'] == 'filter':
                if row['Value']:
                    self.node.filterExpression = row['Value']
        if f: self.node.funcatts = f
        #self.node.gui.update()
        self.accept()
        
    def slotCancel(self):
        self.reject()
        
    def validateFilter(self, row, col, val, w):
        if self.tab[row][0] == 'filter':
            if not val or lpath.translate("//A[%s]"%val.strip()) is None:
                QMessageBox.critical(self, "Error", "Invalid filter expression.")
                self.filterOK = False
            else:
                self.filterOK = True
        
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            L = []
            for i in range(self.te.numRows()):
                if self.te.isRowSelected(i):
                    if self.tab[i]['Name'] != 'label':
                        L.append(self.tab[i])
            for row in L:
                self.tab.takeRow(row.num)
        elif e.key() == Qt.Key_Insert and self.node.children:
            i = self.te.currentRow() + 1
            self.tab.insertRow(i, ["@func",""])
            self.te.setCurrentCell(i,1)
        elif e.key() == Qt.Key_N and self.node.children:
            i = self.te.currentRow() + 1
            # make sure that there's only one filter row
            for row in self.tab:
                if row['Name'] == 'filter':
                    return
            self.tab.insertRow(i, ["filter",""])
            self.te.setCurrentCell(i,1)
            
