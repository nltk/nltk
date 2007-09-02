from qt import QListView, QListViewItem, PYSIGNAL
from myaccel import AccelKeyHandler

__all__ = ['TreeEdit']
           
class TreeEditItem(QListViewItem):
    def __init__(self, *args):
        QListViewItem.__init__(self, *args)
        self.setOpen(True)
        for i in range(self.listView().columns()):
            self.setRenameEnabled(i,True)
            
    def attach(self, node):
        return self.treenode.attach(node.treenode)
    def insertLeft(self, node):
        return self.treenode.insertLeft(node.treenode)
    def insertRight(self, node):
        return self.treenode.insertRight(node.treenode)
    def prune(self):
        return self.treenode.prune()
    def splice(self):
        return self.treenode.splice()

    # mode -> gui
    def _attach(self,dst,src):
        c = dst.gui.firstChild()
        if c is None:
            dst.gui.insertItem(src.gui)
        else:
            while c.nextSibling():
                c = c.nextSibling()
            dst.gui.insertItem(src.gui)
            src.gui.moveItem(c)
        
    def _insertLeft(self,dst,src):
        p = dst.gui.parent()
        c = p.firstChild()
        p.insertItem(src.gui)
        if c != dst.gui:
            src.gui.moveItem(dst.gui)
            dst.gui.moveItem(src.gui)
        
    def _insertRight(self,dst,src):
        dst.gui.parent().insertItem(src.gui)
        src.gui.moveItem(dst.gui)
    
    def _prune(self,n):
        self.parent().takeItem(self)
        
    def _splice(self,n):
        p = self.parent()
        c = self.firstChild()
        M = []  # list of children
        while c:
            M.append(c)
            c = c.nextSibling()
        last = self
        for c in M:
            self.takeItem(c)
            p.insertItem(c)
            c.moveItem(last)
            last = c
        p.takeItem(self)

    def okRename(self, col):
        QListViewItem.okRename(self,col)
        f = self.listView().col2str[col]
        self.treenode.data[f] = self.text(col).ascii()
        

class TreeEdit(QListView,AccelKeyHandler):
    def __init__(self,parent=None):
        QListView.__init__(self,parent)
        self.data = None
        self.col2str = None
        self.setRootIsDecorated(True)
        self.setSorting(-1)
        self.clipBoard = None
        self.accelFilter = None
        self.keyBindingDescriptor = {
            "Ctrl+N":"new",
            "Ctrl+A":"attach",
            "Ctrl+I,Ctrl+L":"insertLeft",
            "Ctrl+I,Ctrl+R":"insertRight",
            "Ctrl+P":"prune",
            "Ctrl+S":"splice"
            }
        self.setKeyBindings(self.keyBindingDescriptor)
        
    def accel_new(self):
        if self.data is None: return
        n = self.data.__class__()
        x = [self] + [None] * len(self.col2str)
        item = apply(TreeEditItem,x)
        for sig in ("attach","insertLeft","insertRight","prune","splice"):
            n.connect(n,PYSIGNAL(sig),eval("item._%s"%sig))
        self.takeItem(item)
        item.treenode = n
        n.gui = item
        self.clipBoard = n
    def accel_attach(self):
        item = self.currentItem()
        if item and self.clipBoard is not None and \
           item.treenode.attach(self.clipBoard):
            self.clipBoard = None
    def accel_insertLeft(self):
        item = self.currentItem()
        if item and self.clipBoard is not None and \
           item.treenode.insertLeft(self.clipBoard):
            self.clipBoard = None
    def accel_insertRight(self):
        item = self.currentItem()
        if item and self.clipBoard is not None and \
           item.treenode.insertRight(self.clipBoard):
            self.clipBoard = None
    def accel_prune(self):
        item = self.currentItem()
        if item and item.treenode.prune():
            self.clipBoard = item.treenode
    def accel_splice(self):
        item = self.currentItem()
        if item and item.treenode.splice():
            self.clipBoard = item.treenode
        
    def setData(self, data, fields=[]):
        if data != data.root:
            return
        if self.data is not None:
            self.clear()
            for i in range(self.columns()):
                self.removeColumn(0)
        
        self.data = data
        self.col2str = {}
        for i,(f,v) in enumerate(fields):
            self.addColumn(v)
            self.col2str[i] = f

        L = [data]
        T = [self]
        while L:
            n = L.pop()
            if n is None:
                T.pop()
                continue
            c = n.children
            x = [T[-1],n.data[fields[0][0]]]
            for f,v in fields[1:]:
                x.append(str(n.data[f]))
            e = apply(TreeEditItem, x)
            for sig in ("attach","insertLeft","insertRight","prune","splice"):
                n.connect(n,PYSIGNAL(sig),eval("e._%s"%sig))
            e.treenode = n
            n.gui = e
            if c:
                T.append(e)
                L += [None] + c


    
if __name__ == "__main__":
    from tree_qt import TreeModel
    import qt

    class Demo(qt.QVBox):
        def __init__(self):
            qt.QVBox.__init__(self)
            self.button = qt.QPushButton('Reset',self)
            self.connect(self.button,qt.SIGNAL("clicked()"),self.load)
            self.button2 = qt.QPushButton(self)
            self.connect(self.button2,qt.SIGNAL("clicked()"),self.change)
            hbox = qt.QGrid(2, self)
            lbl1 = qt.QLabel("Edit Panel",hbox)
            lbl2 = qt.QLabel("Clipboard",hbox)
            lbl1.setMargin(2)
            lbl1.setAlignment(lbl1.AlignCenter)
            lbl2.setAlignment(lbl1.AlignCenter)
            self.treeview = TreeEdit(hbox)
            self.clipboard = TreeEdit(hbox)
            self.root = None
            self.load()
            self.resize(400,450)

        def load(self):
            from nltk import bracket_parse
            s = "(S (NP (N I)) (VP1 (VP2 (V saw) (NP (ART the) (N man))) (PP (P with) (NP (ART a) (N telescope)))))"
            t = bracket_parse(s)
            self.root = TreeModel.importNltkLiteTree(t)
            self.treeview.setData(self.root,'label')
            self.vp1 = self.root.children[1]
            self.pp = self.vp1.children[1]
            self.vp2 = self.vp1.children[0]
            self.stage = 0
            self.button2.setText('splice VP1')

        def change(self):
            if self.stage == 0:
                self.vp1.splice()
                self.clipboard.setData(self.vp1,'label')
                self.button2.setText('prune PP')
                self.stage = 1
            elif self.stage == 1:
                self.pp.prune()
                self.clipboard.setData(self.pp,'label')
                self.button2.setText('attach PP to VP2')
                self.stage = 2
            elif self.stage == 2:
                self.vp2.attach(self.pp)
                self.clipboard.setData(self.vp2,'label')
                self.button2.setText('')
                self.stage = 3

    app = qt.QApplication([])
    w = Demo()
    app.setMainWidget(w)
    w.show()
    app.exec_loop()
    
