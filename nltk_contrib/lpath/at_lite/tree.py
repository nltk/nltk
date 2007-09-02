from treeio import TreeIo

__all__ = ['TreeModel']

class TreeModel(TreeIo):
    def __init__(self):
        self.root = self
        self.parent = None
        self.leftSibling = None
        self.rightSibling = None
        self.children = []
        self.data = {}

    def dfs(self, func, *args):
        L = [self]
        while L:
            n = L[0]
            func(n, *args)
            L = n.children + L[1:]
                
    def prune(self):
        if self.root == self:
            return False
        if self.parent is not None:
            self.parent.children.remove(self)
        if self.leftSibling is not None:
            self.leftSibling.rightSibling = self.rightSibling
        if self.rightSibling is not None:
            self.rightSibling.leftSibling = self.leftSibling
        self.parent = None
        self.leftSibling = None
        self.rightSibling = None

        def f(t):t.root=self
        self.dfs(f)

        return True
    
    def splice(self):
        if self.parent is not None:
            i = self.parent.children.index(self)
            # error should be raised if i < 0
            self.parent.children.remove(self)
            if self.children:
                for c in self.children:
                    c.parent = self.parent
                    self.parent.children.insert(i,c)
                    i += 1
                if self.leftSibling:
                    self.leftSibling.rightSibling = self.children[0]
                    self.children[0].leftSibling = self.leftSibling
                if self.rightSibling:
                    self.rightSibling.leftSibling = self.children[-1]
                    self.children[-1].rightSibling = self.rightSibling
            else:
                if self.leftSibling is not None:
                    self.leftSibling.rightSibling = self.rightSibling
                if self.rightSibling is not None:
                    self.rightSibling.leftSibling = self.leftSibling
            self.parent = None
            self.leftSibling = None
            self.rightSibling = None
            self.children = []

            self.root = self

            return True
        else:
            return False
            
    def insertLeft(self,node):
        if self.root == self or self.root == node.root:
            return False
        
        if self.leftSibling:
            self.leftSibling.rightSibling = node
            node.leftSibling = self.leftSibling
        node.rightSibling = self
        node.parent = self.parent
        i = self.parent.children.index(self)
        self.parent.children.insert(i,node)

        def f(t):t.root=self.root
        node.dfs(f)

        return True
    
    def insertRight(self,node):
        if self.root == self or self.root == node.root:
            return False
        
        if self.rightSibling:
            self.rightSibling.leftSibling = node
            node.rightSibling = self.rightSibling
        node.leftSibling = self
        node.parent = self.parent
        i = self.parent.children.index(self)
        self.parent.children.insert(i+1,node)

        def f(t):t.root=self.root
        node.dfs(f)

        return True
    
    def attach(self,node):
        if self.root == node.root:
            return False
        
        node.parent = self
        if self.children:
            node.leftSibling = self.children[-1]
            self.children[-1].rightSibling = node
        node.rightSibling = None
        self.children.append(node)

        def f(t):t.root=self.root
        node.dfs(f)

        return True

    def isParentOf(self, n):
        return n.parent == self

    def isAncestorOf(self, n):
        p = n.parent
        while p:
            if p == self: return True
            p = p.parent
        return False

    def follows(self, n):
        L = [n]
        p = n.parent
        while p:
            L.append(p)
            p = p.parent
        p = self
        pp = None
        while p not in L:
            pp, p = p, p.parent
        if pp is None or p==n: return False
        i = L.index(p)
        ni = p.children.index(L[i-1])
        mi = p.children.index(pp)
        return ni < mi
    
if __name__ == "__main__":
    from nltk.tree import bracket_parse
    s = "(S (NP (N I)) (VP (VP (V saw) (NP (DT the) (N man))) (PP (P with) (NP (DT a) (N telescope)))))"
    t = bracket_parse(s)
    root = TreeModel.importNltkLiteTree(t)
    print root.treebankString("label")
