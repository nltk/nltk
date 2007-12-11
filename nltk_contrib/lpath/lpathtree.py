import at_lite as at
from at_lite.tree import TreeModel as PureTree

__all__ = ['LPathTreeModel']

# IMPORTANT: We assume that the underlying tree is frozen and not modified
# in any case.

class LPathTreeModel(PureTree):
    AxisParent = "AxisParent"
    AxisAncestor = "AxisAncestor"
    AxisSibling = "AxisSibling"
    AxisImmediateSibling = "AxisImmediateSibling"
    AxisFollowing = "AxisFollowing"
    AxisImmediateFollowing = "AxisImmediateFollowing"
    AlignNone = 0
    AlignLeft = 1
    AlignRight = 2
    AlignBoth = 3
    
    def __init__(self):
        PureTree.__init__(self)
        self.lpRoot = self
        self.lpScope = None
        self.lpParent = None
        self.lpChildren = [None]
        self._lpAxisType = None
        self._lpNot = False
        self._lpAlignment = self.AlignNone
        # self.lpChildren[0]  - the main trunk child
        # self.lpChildren[1:] - branches (rectrictions)

    def getNot(self):
        """
        @rtype: bool
        @return: True if it is a negation branch, False otherwise.
        """
        return self._lpNot

    def setNot(self, v):
        """
        @type  v: bool
        @param v: True for negation branch, False for normal branch.
        @rtype: bool
        @return: True if successful, False otherwise.
        """
        if self._lpAxisType is None or self.lpParent.lpChildren[0]==self:
            return False
        self._lpNot = v
        self.lpDfs(lambda t:t.resetScope())
        return True

    def getAxisType(self):
        return self._lpAxisType

    def setAxisType(self, v):
        if self._lpAxisType is None:
            return False
        self._lpAxisType = v
        #self.lpDfs(lambda t:t.resetScope())
        return True
    
    def lpDfs(self, func, *args):
        L = [self]
        while L:
            n = L[0]
            func(n, *args)
            if n.lpChildren[0] is None:
                L = n.lpChildren[1:] + L[1:]
            else:
                L = n.lpChildren + L[1:]

    def lpBfs(self, func, *args):
        """
        Branch First Search.
        """
        L = [self]
        while L:
            n = L[0]
            func(n, *args)
            if n.lpChildren[0] is None:
                L = n.lpChildren[1:] + L[1:]
            else:
                L = n.lpChildren[1:] + [n.lpChildren[0]] + L[1:]
            
        
    def lpIsolated(self):
        return len(self.lpChildren)==1 and self.lpChildren[0] is None and self.lpParent is None
    
    def lpHasChild(self):
        return self.Children[0] is not None

    def lpOnMainTrunk(self):
        if self.lpParent is None:
            return True
        else:
            return self.lpParent.lpChildren[0] == self

    def _computeAxisType(self, n1, n2):
        if n1.parent == n2 or n2.parent == n1:
            return self.AxisParent

        if n1.rightSibling == n2 or n2.rightSibling == n1:
            return self.AxisImmediateSibling

        if n1.parent == n2.parent:
            return self.AxisSibling

        a1L = [n1]
        p = n1.parent
        while p:
            if p == n2:
                return self.AxisAncestor
            a1L.append(p)
            p = p.parent

        a2L = [n2]
        p = n2.parent
        while p:
            if p == n1:
                return self.AxisAncestor
            a2L.append(p)
            p = p.parent

        for i,x in enumerate(a1L):
            try:
                j = a2L.index(x)
                break
            except ValueError:
                pass

        a1L = a1L[:i]
        a2L = a2L[:j]
        i = x.children.index(a1L.pop())
        j = x.children.index(a2L.pop())

        if abs(i-j) > 1:
            return self.AxisFollowing
        
        if i < j:
            L1 = a1L
            L2 = a2L
        else:
            L1 = a2L
            L2 = a1L

        for x in L1:
            if x.rightSibling:
                return self.AxisFollowing
        for x in L2:
            if x.leftSibling:
                return self.AxisFollowing

        return self.AxisImmediateFollowing


    def resetScope(self):
        if not self.lpOnMainTrunk():
            if self.lpParent.isAncestorOf(self):
                self.lpScope = self.lpParent
            else:
                self.lpScope = self.lpParent.lpScope
            return
        
        p = self.lpParent
        while p:

            if p.isAncestorOf(self):
                self.lpScope = p
                break
            elif not p.lpOnMainTrunk():
                self.lpScope = p.lpScope
                break

            p1 = p.lpParent
            while p1 and p1.lpOnMainTrunk() and p1 != p.lpScope:
                p1 = p1.lpParent
            p = p1

        else:
            self.lpScope = None


    def lpBranchRoot(self):
        if not self.lpOnMainTrunk():
            return self
        p = self.lpParent
        while p and p.lpOnMainTrunk():
            p = p.lpParent
        return p


    def lpAncestorOf(self, node):
        p = node.lpParent
        while p and p != self:
            p = p.lpParent
        return p is not None

    def setScope(self, node):
        if node is None or node.lpAncestorOf(self):
            self.lpScope = node
            for c in self.lpChildren:
                if c is not None:
                    c.lpDfs(lambda t:t.resetScope())
            
    def shiftScope(self):
        if self._lpAxisType == self.AxisParent or \
           self._lpAxisType == self.AxisAncestor or \
           self._lpAxisType is None:
            return

        br = self.lpBranchRoot()
        if br:
            if br._lpAxisType == self.AxisParent or \
               br._lpAxisType == self.AxisAncestor:
                limit = br.lpParent
            else:
                limit = br.lpParent.lpScope
        else:
            limit = None

        if self.lpScope:
            self.lpScope = self.lpScope.lpScope
            if self.lpScope is None:
                if limit is not None:
                    self.lpScope = self.lpParent.lpScope
            else:
                if limit is not None and self.lpScope.lpAncestorOf(limit):
                    self.lpScope = self.lpParent.lpScope
        else:
            self.lpScope = self.lpParent.lpScope
            
        for c in self.lpChildren:
            if c is not None:
                c.lpDfs(lambda t:t.resetScope())
            
    def canShiftScope(self):
        if self._lpAxisType == self.AxisParent or \
           self._lpAxisType == self.AxisAncestor or \
           self._lpAxisType is None:
            return False

        br = self.lpBranchRoot()
        if br:
            if br._lpAxisType == self.AxisParent or \
               br._lpAxisType == self.AxisAncestor:
                limit = br.lpParent
            else:
                limit = br.lpParent.lpScope
        else:
            limit = None

        if self.lpScope:
            newScope = self.lpScope.lpScope
            if self.lpScope is None:
                if limit is not None:
                    newScope = self.lpParent.lpScope
            else:
                if limit is not None and self.lpScope.lpAncestorOf(limit):
                    newScope = self.lpParent.lpScope
        else:
            newScope = self.lpParent.lpScope
            
        return self.lpScope != newScope
    
            
    def lpSetChild(self, node):
        # terminal node can't have an LPath child
        # also, terminal node can't be put on the backbone
        if len(self.children) == 0 or len(node.children) == 0:
            return False
        
        # if the node comes from siblings, just change order of children
        if node in self.lpChildren and node != self.lpChildren[0]:
            oldroot = self.lpChildren[0]
            self.lpChildren.remove(node)
            self.lpChildren[0] = node
            if oldroot is not None:
                self.lpChildren.append(oldroot)
            node._lpNot = False
            node.lpDfs(lambda t:t.resetScope())
            return True
        
        if self.lpChildren[0] or node.lpRoot!=node or node.lpRoot==self.lpRoot:
            return False
            
        node.lpParent = self
        self.lpChildren[0] = node
        
        def f(t):t.lpRoot=self.lpRoot
        node.lpDfs(f)

        node._lpAxisType = self._computeAxisType(self, node)
        node.lpDfs(lambda t:t.resetScope())

        return True
    
    def lpAttachBranch(self, node):
        # terminal node can't have an LPath child
        if len(self.children) == 0 or \
            (len(node.children)==0 and node.parent!=self):
            return False
        
        if node == self.lpChildren[0]:
            self.lpChildren[0] = None
            self.lpChildren.append(node)
            node.lpDfs(lambda t:t.resetScope())
            return True

        # node is non-root node or in the same tree as self
        if node.lpRoot!=node or self.lpRoot==node.lpRoot:
            return False
        
        node.lpParent = self
        self.lpChildren.append(node)

        def f(t):t.lpRoot=self.lpRoot
        node.lpDfs(f)

        node._lpAxisType = self._computeAxisType(self, node)
        node.lpDfs(lambda t:t.resetScope())

        return True
    
    def lpPrune(self):
        if self.lpRoot == self:
            return False
        if self.lpParent is not None:
            if self.lpParent.lpChildren[0] == self:
                self.lpParent.lpChildren[0] = None
            else:
                self.lpParent.lpChildren.remove(self)
        self.lpParent = None
        self._lpAxisType = None
        self._lpNot = False

        def f(t):t.lpRoot=self
        self.lpDfs(f)
        self.lpDfs(lambda t:t.resetScope())

        return True

    def lpRoots(self):
        def f(t,L):
            if t.lpRoot==t and not t.lpIsolated():
                L.append(t)
        L = []
        self.root.dfs(f,L)
        return L

    def lpScopeDepth(self):
        d = 0
        n = self
        while n.lpScope:
            n = n.lpScope
            d += 1
        return d
    
#    def _hasHorizontalAxis(self, n):
#        axis = n.getAxisType()
#        return axis is not None and axis not in (self.AxisAncestor,self.AxisParent)
#    
#    def _upperHorizontalSpanningTree(self, filter=lambda x:True):
#        L = []
#        c = self
#        while c.lpParent and self._hasHorizontalAxis(c):
#            if filter(c.lpParent): L.append(c.lpParent)
#            c = c.lpParent
#        return L
#    
#    def _lowerHorizontalSpanningTree(self, filter=lambda x:True):
#        L = []
#        for c in self.lpChildren:
#            if c and self._hasHorizontalAxis(c):
#                if filter(c): L.append(c)
#                L += c._lowerHorizontalSpanningTree(filter)
#        return L
#    
    def lpScopeSiblings(self, filter=lambda x:True):
        L = []
        if self.lpScope is not None:
            def f(node):
                if node.lpScope == self.lpScope and filter(node):
                    L.append(node)
            self.root.dfs(f)
        return L
        
    def lpLeftAlignable(self):
        return len(self.children) > 0 and \
                self.lpScope is not None and \
                len(self.lpScopeSiblings(self.follows)) == 0
                 
            
    def lpRightAlignable(self):
        filter = lambda x:x.follows(self)
        return len(self.children) > 0 and \
                self.lpScope is not None and \
                len(self.lpScopeSiblings(filter)) == 0
        
    def lpAlignLeft(self):
        if self.lpLeftAlignable():
            if self._lpAlignment == self.AlignBoth or self._lpAlignment == self.AlignRight:
                self._lpAlignment = self.AlignBoth
            else:
                self._lpAlignment = self.AlignLeft
            return True
        else:
            return False
        
    def lpAlignRight(self):
        if self.lpRightAlignable():
            if self._lpAlignment == self.AlignBoth or self._lpAlignment == self.AlignLeft:
                self._lpAlignment = self.AlignBoth
            else:
                self._lpAlignment = self.AlignRight
            return True
        else:
            return False
    
    def lpClearAlignment(self):
        self._lpAlignment = self.AlignNone
        
    def lpResetAlignment(self):
        def f(node):
            a = node.lpAlignment()
            if ((a == self.AlignRight and not node.lpRightAlignable()) or \
                (a == self.AlignLeft and not node.lpLeftAlignable())):
                node.lpClearAlignment()
        self.lpRoot.lpDfs(f)
        
    def lpAlignment(self):
        return self._lpAlignment

