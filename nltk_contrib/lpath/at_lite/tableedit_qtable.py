from qttable import QTable
from qt import SIGNAL,PYSIGNAL

class TableEdit(QTable):
    def __init__(self, parent=None):
        QTable.__init__(self, parent)
        self.data = None

    def setData(self, data):
        self.removeColumns(range(self.numCols()))
        self.removeRows(range(self.numRows()))

        self.setNumCols(len(data.header))
        for j,(h,t) in enumerate(data.header):
            self.horizontalHeader().setLabel(j,h)
        self.setNumRows(len(data))
        for i,row in enumerate(data):
            for j,h in enumerate(row):
                if h is not None:
                    if type(h)==str or type(h)==unicode:
                        self.setText(i,j,h)
                    else:
                        self.setText(i,j,str(h))
        for j,_ in enumerate(data.header):
            self.adjustColumn(j)
        if data != self.data:
            for sig in ('setHeader','cellChanged','insertRow','insertColumn','takeRow','takeColumn','sort'):
                self.connect(data.emitter,PYSIGNAL(sig),eval("self._%s"%sig))
            self.connect(self,SIGNAL("valueChanged(int,int)"),self.__cellChanged)
            self.data = data
            
    # incoming; model-to-gui
    def _setHeader(self, col, header):
        self.horizontalHeader().setLabel(col,header[0])
    def _cellChanged(self, i, j, val):
        if val is None:
            val = ''
        self.disconnect(self,SIGNAL("valueChanged(int,int)"),self.__cellChanged)
        self.setText(i,j,unicode(val))
        self.connect(self,SIGNAL("valueChanged(int,int)"),self.__cellChanged)

    def _insertRow(self, i, row):
        self.insertRows(i)
        if row is not None:
            for j,c in enumerate(row):
                if c is not None:
                    self.setText(i,j,str(c))
    def _insertColumn(self, j, col):
        self.insertColumns(j)
        if col is not None:
            self.horizontalHeader().setLabel(j,col[0][0])
            for i,c in enumerate(col[1:]):
                if c is not None:
                    self.setText(i,j,str(c))
    def _takeRow(self, i, r):
        self.removeRow(i)
    def _takeColumn(self, j):
        self.removeColumn(j)
    def _sort(self):
        self.setData(self.data)

    # outgoing; gui-to-model
    def __cellChanged(self, row, col):
        self.disconnect(self,SIGNAL("valueChanged(int,int)"),self.__cellChanged)
        self.disconnect(self.data.emitter,PYSIGNAL("cellChanged"),self._cellChanged)
        self.data[row][col] = self.item(row,col).text()
        self.setText(row,col,self.data[row][col])
        self.connect(self,SIGNAL("valueChanged(int,int)"),self.__cellChanged)
        self.connect(self.data.emitter,PYSIGNAL("cellChanged"),self._cellChanged)
        
if __name__ == '__main__':
    import qt
    from table_qt import TableModel

    class Demo(qt.QVBox):
        def __init__(self):
            qt.QVBox.__init__(self)
            self.b1 = qt.QPushButton('reset / load table',self)
            self.connect(self.b1,qt.SIGNAL("clicked()"),self.action)
            self.tab = TableEdit(self)
            self.stage = 0
            self.b2 = qt.QPushButton('print table at console',self)
            self.connect(self.b2,qt.SIGNAL("clicked()"),self.printTable)

        def printTable(self):
            self.data.printTable()
            
        def action(self):
            if self.stage == 0:
                t = [[('start',float),('end',float),('ch',str),('transcript',str)],
                     [1.23,2.34,'A','hello'],
                     [2.45,2.67,'B','hi'],
                     [2.88,3.09,'A','how are you']]
                self.data = TableModel.importList(t)
                self.tab.setData(self.data)
                self.stage = 1
                self.b1.setText('add row')
            elif self.stage == 1:
                self.data.insertRow(len(self.data))
                self.stage = 2
                self.b1.setText('take row 4')
            elif self.stage == 2:
                self.tmprow = self.data.takeRow(3)
                self.stage = 3
                self.b1.setText('insert row at the top')
            elif self.stage == 3:
                self.data.insertRow(0,self.tmprow)
                self.stage = 4
                self.b1.setText('sort by start')
            elif self.stage == 4:
                self.data.sort()
                self.stage = 5
                self.b1.setText('add column at the begining')
            elif self.stage == 5:
                self.data.insertColumn(0)
                self.data.setHeader(0,('review',str))
                self.stage = 6
                self.b1.setText('take review column')
            elif self.stage == 6:
                self.tmpcol = self.data.takeColumn(0)
                self.stage = 7
                self.b1.setText('insert the column before ch column')
            elif self.stage == 7:
                self.data.insertColumn(2,self.tmpcol)
                self.stage = 8
                self.b1.setText('change start time of row 1 to 9.99')
            elif self.stage == 8:
                self.data[0][0] = 9.99
                self.stage = 0
                self.b1.setText('reset / load table')
                

    app = qt.QApplication([])
    w = Demo()
    app.setMainWidget(w)
    w.show()
    app.exec_loop()
