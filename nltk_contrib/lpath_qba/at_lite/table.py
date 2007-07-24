from tableio import TableIo
import bisect

__all__ = ['TableModel']

class TableModel(TableIo):
    
    class TableRow:
        def __init__(self, tab, iv=[]):
            """
            @param tab: TableModel
            @param iv: initial value
            """
            self.tab = tab
            self.data = list(iv)
            
        def __len__(self):
            return len(self.data)
        def __getitem__(self,i):
            if type(i) == str:
                i = self.tab.getColumnIndex(i)
            return self.data[i]
        def __setitem__(self,i,v):
            if type(i) == str:
                i = self.getColumnIndex(i)
            self.data[i] = self.transformValue(i, v)
        def __str__(self):
            return str(self.data)
        def getColumnIndex(self, i):
            return self.tab.getColumnIndex(i)
        def getColumnName(self,i):
            return self.tab.getColumnName(i)
        def getColumnType(self,i):
            return self.tab.getColumnType(i)
        def getColumnHeader(self,i):
            return self.tab.getColumnHeader(i)
        def transformValue(self, i, v):
            return self.tab.transformValue(i,v)
        def toList(self):
            return self.data[:]
    
    def __init__(self, header):
        self.header = header
        self.str2col = {}
        self.colnum = 0
        for i,(h,t) in enumerate(header):
            self.str2col[h] = i
        self.table = []
        self.metadata = {}

    def setColumnHeader(self, colIdx, colName, colType):
        """ Sets the header for one column.

        @param colIdx: Column index for which the given header
        information will be set.
        @type colIdx: int
        @param colName: Column name.
        @type colName: string
        @param colType: Data type of the values in the column.
        @type colType: type
        """
        del self.str2col[self.header[col][0]]
        self.header[col] = header
        self.str2col[header[0]] = col

    def insertRow(self,i=None,row=None):
        """ Inserts a row at a given index.  If the row size is less than
        that of header, None is padded.  If the row size if larger than
        that of header, the row will be truncated.

        @param i: Row index. New row is inserted before the i-th row,
        thus the new row become the i-th row after insertion.  If i is
        None or larger than the last index, the new row will be
        appended at the end of the table.
        @type i: int
        @param row: The new row to be inserted.  The size of the row
        must match the width of the table, and the value of each
        column must match  Otherwise, nothing happens
        and False will be returned.  If row is None, a new row filled
        with Nones is inserted.
        @type row: list
        """
        if i is None: i = len(self.table)
        if row is None:
            row = [None for x in self.header]
        else:
            n = len(row)
            m = len(self.header)
            if n < m:
                row += [None] * (m-n)
            elif n > m:
                del row[m:]
        self.table.insert(i,self.TableRow(self,row))
        return True
    
    def insertColumn(self,i=None,col=None):
        if i is None: i = len(self.header)
        if col is None:
            s = "col%d" % self.colnum
            self.colnum += 1
            self.header.insert(i,(s,str))
            self.str2col[s] = i
            for row in self.table:
                row.data.insert(i,None)
        elif len(col)-1 != len(self.table):
            return False
        else:
            self.header.insert(i,col[0])
            self.str2col[col[0][0]] = i
            for r,row in enumerate(self.table):
                row.data.insert(i,col[r+1])
        return True
    
    def takeRow(self,i):
        row = self.table[i]
        self.table.remove(row)
        return row
    
    def takeColumn(self,i):
        col = [self.header[i]]
        del self.str2col[self.header[i][0]]
        del self.header[i]
        for row in self.table:
            col.append(row[i])
            del row.data[i]
        return col

    def sort(self, *args):
        L = list(range(len(self.header)))
        for i in args:
            if type(i) == str:
                i = self.getColumnIndex(i)
            L.remove(i)
        L = list(args) + L

        def sf(a,b):
            for c in L:
                if a[c] < b[c]:
                    return -1
                elif a[c] > b[c]:
                    return 1
            return 0

        self.table.sort(sf)
        
    def __getitem__(self, i):
        return self.table[i]

    def __len__(self):
        return len(self.table)

    def transformValue(self, col, val):
        if val is None: return None
        try:
            return self.header[col][1](val)
        except TypeError:
            return None

    def getColumnIndex(self, col):
        return self.str2col[col]

    def toList(self):
        return [row.toList() for row in self.table]

    def getColumnName(self, col):
        return self.header[col][0]

    def getColumnType(self, col):
        return self.header[col][1]

    def getColumnHeader(self, col):
        return self.header[col]

    def bisect_left(self, col, val):
        """
        Assume that the column col is sorted.
        """
        if type(col) != int:
            col = self.str2col[col]
        return bisect.bisect_left(map(lambda x:x[col],self.table),val)

    def bisect_right(self, col, val):
        """
        Assume that the column col is sorted.
        """
        if type(col) != int:
            col = self.str2col[col]
        return bisect.bisect_right(map(lambda x:x[col],self.table),val)

    def setMetadata(self, nam, val):
        if type(val) != str:
            val = str(val)
        self.metadata[nam] = val

    def getMetadata(self, nam, evl=False):
        if evl:
            return eval(self.metadata[nam])
        else:
            return self.metadata[nam]

if __name__ == "__main__":
    tab = TableModel([('a',str),('b',int),('c',int)])
    tab.insertRow(0)
    tab.insertRow(1)
    tab[0][0] = "apple"
    tab[0][1] = 2
    tab[0][2] = 3
    tab[1][0] = "orange"
    tab[1][1] = 5
    tab[1][2] = 3
    tab.printTable()

    print

    tab.insertColumn(1,["extra",10,9])
    tab.printTable()

    print

    c = tab.takeColumn(1)
    tab.insertColumn(3,c)
    tab.printTable()

    print

    r = tab.takeRow(0)
    tab.insertRow(1,r)
    tab.printTable()

    print
    
    tab.sort(2,3)
    tab.printTable()

