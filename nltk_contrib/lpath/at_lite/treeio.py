import re

__all__ = ['TreeIo']

class TreeIo:
    def treebankString(self, p):
        L = [self]
        s = ''
        while L:
            n = L[0]
            if n is None:
                s += ')'
                L = L[1:]
                continue
            c = n.children
            if c:
                s += ' (' + unicode(n.data[p])
                L = c + [None] + L[1:]
            else:
                s += ' ' + unicode(n.data[p])
                L = L[1:]
        return s[1:]

    def importNltkLiteTree(cls, t):
        from nltk.tree import Tree as NltkTree

        L = [t]
        T = [cls()]
        while L:
            n = L[0]
            if n is None:
                L = L[1:]
                T.pop()
                continue
            
            x = cls()
            if type(n) == NltkTree:
                x.data['label'] = n.node
                T[-1].attach(x)
                T.append(x)
                L = n[:] + [None] + L[1:]
            else:
                x.data['label'] = n
                T[-1].attach(x)
                L = L[1:]

        root = T[0].children[0]
        root.prune()
        return root

    importNltkLiteTree = classmethod(importNltkLiteTree)

    def importTreebank(cls, lines):
        p = re.compile(r"\s*([^()]+)\s*")
        L = [cls()]
        for i,l in enumerate(lines):
            l = l.lstrip()
            while l:
                if l[0] == '(':
                    l = l[1:].lstrip()
                    args = []
                    m = p.match(l)
                    if m:
                        args = m.group(1).split()
                        l = l[m.span()[1]:]
                    n = len(args)
                    node = cls()
                    L[-1].attach(node)
                    if n > 0:
                        node.data['label'] = args[0]
                        if n > 1:
                            node1 = cls()
                            node1.data['label'] = args[1]
                            node.attach(node1)
                            if n > 2:
                                node.data['extra'] = args[2:]
                    else:
                        node.data['label'] = ''
                    L.append(node)
                elif l[0] == ')':
                    l = l[1:].lstrip()
                    L.pop()
                else:
                    node = cls()
                    node.data['label'] = 'garbage'
                    node.data['garbage'] = l
                    L[-1].attach(node)
                    break
                if len(L) == 1 and L[0].children:
                    t = L[0].children[-1]
                    t.prune()
                    yield t
        #res = L[0].children[:]
        #for c in res: c.prune()
        #return res

    importTreebank = classmethod(importTreebank)

    def exportLPathTable(self, TableModel, sid=0, tid=0):
        L = [self]     # dfs queue, None delimits nodes of different levels
        C = []         # stack storing information about latest parent node
        TAB = []
        left = 0
        depth = 0
        nodeid = 0
        while L:
            n = L[0]
            if n is None:
                # done with children; update parent's "right" index
                r = C.pop()
                r['right'] = left
                L = L[1:]
                depth -= 1
                continue
            else:
                r = {}

            # Make sure all the node's application-specific attributes are recorded.
            r['attributes'] = []
            if n.data != None:
                for attr, value in n.data.iteritems():
                    if attr == 'label':
                        r['name'] = value
                    else:
                        r['attributes'].append(('@' + attr, value))

            r['left'] = left
            if n.children:
                nodeid += 1
                r['depth'] = depth
                if depth == 0:
                    r['pid'] = nodeid
                else:
                    r['pid'] = C[-1]['id']
                C.append(r)
                L = n.children + [None] + L[1:]
                depth += 1
                TAB.append(r)
            else:
                if depth == 0:
                    # this is one-node tree
                    nodeid += 1
                    r['depth'] = depth
                    r['pid'] = nodeid
                    TAB.append(r)
                else:
                    # Attributes from lexical nodes get pushed up one level.
                    # @label is a special case.
                    C[-1]['attributes'].append(('@label',r['name']))
                    for attr in r['attributes']:
                        C[-1]['attributes'].append(attr)
                left += 1
                L = L[1:]
            r['sid'] = sid
            r['tid'] = tid
            r['id'] = nodeid

        TAB2 = TableModel([("sid",int),("tid",int),("id",int),("pid",int),
                           ("left",int),("right",int),("depth",int),
                           ("type",str),("name",str),("value",str)])

        fields = ('sid','tid','id','pid','left','right','depth')
        for r in TAB:
            TAB2.insertRow()
            row = TAB2[-1]
            for f in fields:
                row[f] = r[f]
            row['type'] = 'syn'
            row['name'] = r['name']
            row['value'] = None
            for k,v in r['attributes']:
                TAB2.insertRow(None,row)
                row2 = TAB2[-1]
                row2['type'] = 'att'
                row2['name'] = k
                row2['value'] = v
        return TAB2

    def importLPathTable(cls, table):
        # copy "table" to "tab" to avoid changing "table"
        # "tab" is sorted later
        tab = table.__class__(table.header)
        for row in table:
            tab.insertRow(None,row)
            
        tab.sort('sid','tid','left','depth','value')
        T = [cls()]
        P = [tab[0]['pid']]
        for row in tab:
            if row['type'] == 'att':
                p = row['id']
                while P[-1] != p:
                    T.pop()
                    P.pop()
                f = row['name']
                v = row['value']
                if f == '@label':
                    node = cls()
                    node.data['label'] = v
                    T[-1].attach(node)
                else:
                    if f in T[-1].data:
                        T[-1].data[f].append(v)
                    else:
                        T[-1].data[f] = [v]
            else:
                p = row['pid']
                while P[-1] != p:
                    T.pop()
                    P.pop()
                node = cls()
                node.data['label'] = row['name']
                node.data['type'] = row['type']
                node.data['id'] = row['id']
                T[-1].attach(node)
                T.append(node)
                P.append(row['id'])
        t = T[0].children[0]
        t.prune()
        return t

    importLPathTable = classmethod(importLPathTable)

