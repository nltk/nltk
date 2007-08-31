from qt import QObject, PYSIGNAL

__all__ = ['getProxy']

class UndoStack:
    def __init__(self):
        self.reset()

    def reset(self):
        self._stack = []
        self._top = -1
        self._limit = -1
        
    def prev(self):
        if self._top >= 0:
            r = self._stack[self._top]
            self._top -= 1
            return r
        else:
            return None

    def next(self):
        if self._limit > self._top:
            self._top += 1
            return self._stack[self._top]
        else:
            return None
        
    def push(self, *args):
        self._top += 1
        if len(self._stack) == self._top:
            self._stack.append(args)
        else:
            self._stack[self._top] = args
        self._limit = self._top
        if self._limit >= 2000:
            del self._stack[0]
            self._limit -= 1
            self._top -= 1

    def status(self):
        return self._top+1, self._limit-self._top
    
class _TableRowProxy(object):
    """
    self.num is a row index in the table
    """
    def __setitem__(self,i,v):
        if type(i) == str:
            i = self.getColumnIndex(i)
        w = self[i]
        super(self.__class__,self).__setitem__(i,v)
        self.tab.emitter.emit(PYSIGNAL("cellChanged"),(self.num,i,self.data[i],w))
        if not self.tab.undoStackReadOnly:
            self.tab.undoStack.push("cellChanged",(self.num,i),(v,w))

    def select(self):
        self.tab.select(self.num)
        
class _TableModelProxy(object):
    def __init__(self, *args):
        self.super = super(self.__class__,self)
        self.super.__init__(*args)
        self.emitter = QObject()
        self.selection = None
        self.undoStack = UndoStack()
        self.undoStackReadOnly = False
        
    def setHeader(self, col, header):
        self.super.setHeader(col, header)
        self.emitter.emit(PYSIGNAL("setHeader"),(col,header))
        
    def insertRow(self,i=None,row=None):
        if i is None: i=len(self.table)
        if self.super.insertRow(i,row):
            for k in range(i,len(self.table)):
                self.table[k].num = k
            self.emitter.emit(PYSIGNAL("insertRow"),(i,self.table[i]))
            if not self.undoStackReadOnly:
                self.undoStack.push("insertRow",i,row)
            return True
        else:
            return False
        
    def insertColumn(self,i=None,col=None):
        if self.super.insertColumn(i,col):
            self.emitter.emit(PYSIGNAL("insertColumn"),(i,col))
            if type(i)==int and i <= self.selection:
                self.selection += 1
            return True
        else:
            return False
    
    def takeRow(self,i):
        r = self.super.takeRow(i)
        for k in range(i,len(self.table)):
            self.table[k].num = k
        if i == self.selection:
            self.selection = None
        self.emitter.emit(PYSIGNAL("takeRow"),(i,r))
        if not self.undoStackReadOnly:
            self.undoStack.push("takeRow",i,r)
        return r
    
    def takeColumn(self,i):
        c = self.super.takeColumn(i)
        self.emitter.emit(PYSIGNAL("takeColumn"),(i,))
        if i == self.selection:
            self.selection = None
        elif i < self.selection:
            self.selection -= 1
        return c
    
    def sort(self, *args):
        self.super.sort(*args)
        for i,row in enumerate(self.table):
            row.num = i
        self.emitter.emit(PYSIGNAL("sort"),())

    def select(self, sel):
        self.selection = sel
        self.emitter.emit(PYSIGNAL("select"),(sel,))

    def getSelection(self):
        return self.selection

    def resetUndoStack(self):
        self.undoStack.reset()
        
    def undo(self, n=1):
        for m in range(n):
            try:
                op, arg1, arg2 = self.undoStack.prev()
                #print "undo", op, arg1, arg2
                #print len(self.undoStack._stack)
            except TypeError:
                break
            self.undoStackReadOnly = True
            if op == 'insertRow':
                self.takeRow(arg1)
            elif op == 'takeRow':
                self.insertRow(arg1,arg2)
            elif op == 'cellChanged':
                i, j = arg1
                v, w = arg2
                self[i][j] = w
            self.undoStackReadOnly = False
    
    def redo(self, n=1):
        for m in range(n):
            try:
                op, arg1, arg2 = self.undoStack.next()
                #print "redo", op, arg1, arg2
                #print len(self.undoStack._stack)
            except TypeError:
                break
            self.undoStackReadOnly = True
            if op == 'insertRow':
                self.insertRow(arg1,arg2)
            elif op == 'takeRow':
                self.takeRow(arg1)
            elif op == 'cellChanged':
                i, j = arg1
                v, w = arg2
                self[i][j] = v
            self.undoStackReadOnly = False

    def undoStackStatus(self):
        return self.undoStack.status()
    
def getProxy(cls):
    name = "Proxy_TableRow"
    bases = (cls.TableRow,) + _TableRowProxy.__bases__
    dic = dict(_TableRowProxy.__dict__)
    rowModelClass = type(name, bases, dic)
    
    name = "Proxy_" + cls.__name__
    bases = (cls,) + _TableModelProxy.__bases__
    dic = dict(_TableModelProxy.__dict__)
    dic['TableRow'] = rowModelClass
    
    return type(name, bases, dic)

