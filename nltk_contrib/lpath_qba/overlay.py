import re
from translator import translate_sub

__all__ = ["find_overlays", "Overlay"];

class Overlay:
    def __init__(self, matches):
        self._L = matches
        
    def findMatchingNode(self, node):
        for oldNode, newNode in self._L:
            if oldNode == node:
                return newNode
            elif newNode == node:
                return oldNode
        return None
    
    def markNegation(self, n, m):
        """
        @type  n: TreeModel
        @param n: A node in the old tree.
        @type  m: TreeModel
        @param m: A node in the new tree.
        """
        for c in n.lpChildren[1:]:
            if c.getNot():
                s = re.sub(r"[^[]*\[(.*)\].*",r"\1",translate_sub(c,None))
                if 'lpathFilter' in m.data:
                    v = m.data['lpathFilter']
                    v += " and not " + s
                    v = v.strip()
                else:
                    v = "not " + s.strip()
                m.data['lpathFilter'] = v
                m.gui.updateTrace()
                
    def display(self):
        A = [a[0] for a in self._L]
        for i,(a0,b0) in enumerate(self._L):
            a1 = a0.lpChildren[0]
            if a1 in A:
                j = A.index(a1)
                b1 = self._L[j][1]
                b0.lpSetChild(b1)
                b1.setAxisType(a1.getAxisType())
            for a1 in a0.lpChildren[1:]:
                if 'lexical' in a1.data and a1.data['lexical']==True:
                    # terminal node == lexical node
                    b1 = b0.children[0]
                else:
                    try:
                        j = A.index(a1)
                    except ValueError:
                        continue
                    b1 = self._L[j][1]
                b0.lpAttachBranch(b1)
                b1.setAxisType(a1.getAxisType())
            self.markNegation(a0,b0)
    
    def clear(self):
        def g(t,L): L.append(t)
        L = []
        self._L[0][1].lpDfs(g,L)
        for n in L:
            n.lpPrune()
            n.gui.clear()
            if 'lpathFilter' in n.data:
                del n.data['lpathFilter']
        if L: n.gui.canvas().update()


def find_overlays(sql, localdb, oldTree, newTree):
    # get table names from sql: tnames
    if sql is None: return []
    m = re.match(r"^\s*select (.*?) from .*", sql)
    if m is None: return []
    a = m.group(1)
    tnames = [s.strip().split('.')[0] for s in a.split(",")]
    
    # get result table
    TAB = []
    localdb.cursor.execute(sql)
    for r in localdb.cursor.fetchall():
        h = {}
        for i,nam in enumerate(tnames):
            h[nam] = r[i*10:(i+1)*10]
        TAB.append(h)

    # create mapping from node id to tree node
    def f(t, h):
        if 'id' in t.data:
            h[t.data['id']] = t
        else:
            # attribute nodes
            h[-t.parent.data['id']] = t
    h = {}
    newTree.dfs(f, h)

    #
    def g(t, L):
        # skip lexical nodes
        if 'lexical' in t.data and t.data['lexical']==True:
            return
        # skip if it belongs to a negative branch
        p = t.lpBranchRoot()
        while p:
            if p.getNot(): return
            p = p.lpParent
        # add (old,new) pair
        L.append((t,L[0]))
        del L[0]
    
    M = []
    for match in TAB:
        m = match.items()
        m.sort()
        L = []
        for sym,tup in m:
            L.append(h[tup[2]])
        oldTree.lpBfs(g,L)
        M.append(Overlay(L))
    return M

