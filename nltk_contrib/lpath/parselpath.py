from lpath import tokenize
from lpathtree import LPathTreeModel
from translator import translate

SCOPE = ['{','}']
BRANCH = ['[',']']
VAXIS = ['//','/','.','\\\\','\\']
HAXIS = ['<==','==>','<=','=>','<--','-->','<-','->']
AXIS = VAXIS + HAXIS
ATTRIBUTE = ['@']
CONNECTIVES = ['or','and']
GROUP = ['(',')']
OPERATION = ['>=','=','<>','like']
ANNONYMOUS = ['_']

AXISMAP = {
    '//':LPathTreeModel.AxisAncestor,
    '/':LPathTreeModel.AxisParent,
    '\\\\':LPathTreeModel.AxisAncestor,
    '\\':LPathTreeModel.AxisParent,
    '==>':LPathTreeModel.AxisSibling,
    '<==':LPathTreeModel.AxisSibling,
    '=>':LPathTreeModel.AxisImmediateSibling,
    '<=':LPathTreeModel.AxisImmediateSibling,
    '<--':LPathTreeModel.AxisFollowing,
    '-->':LPathTreeModel.AxisFollowing,
    '<-':LPathTreeModel.AxisImmediateFollowing,
    '->':LPathTreeModel.AxisImmediateFollowing,
    }

def parse_lpath(q):
    tokens = tokenize(q)
    root = p = LPathTreeModel()
    p.data['label'] = 'root'
    i = 0
    ret = [p]
    branch = False
    scope = [None]
    while i < len(tokens):
        a, b = tokens[i]
        if a == 'r':
            if b == '[':
                ret.append(None)
                branch = True
            elif b == ']':
                ret.pop()
                p = ret[-1]
                branch = False
            elif b in AXIS:
                node = LPathTreeModel()
                node.data['label'] = tokens[i+1][1]
                dummy = LPathTreeModel()
                dummy.data['label'] = '.'
                node.attach(dummy)
                
                if b in HAXIS:
                    if b == '<=':
                        p.insertLeft(node)
                    elif b == '=>':
                        p.insertRight(node)
                    elif b[0] == '<':
                        if p.leftSibling:
                            p.leftSibling.insertLeft(node)
                        else:
                            p.insertLeft(node)
                    else:
                        if p.rightSibling:
                            p.rightSibling.insertRight(node)
                        else:
                            p.insertRight(node)
                else:
                    if b[0] == '/':
                        p.attach(node)
                    elif b == '\\':
                        if p.root != p:
                            pp = p.parent
                            p.prune()
                            node.attach(p)
                            pp.attach(node)
                    else:
                        node.attach(p.root)

                if branch:
                    assert(p.lpAttachBranch(node))
                else:
                    assert(p.lpSetChild(node))
                    
                node.setAxisType(AXISMAP[b])   # reset axis type
                if tokens[i-1][1] == 'not': node.setNot(True)
                if node.data['label'][0] == '^': node.lpAlignLeft()
                if node.data['label'][-1] == '$': node.lpAlignRight()

                node.setScope(scope[-1])
                
                p = node
                ret[-1] = p
                i += 1
                branch = False
            elif b in CONNECTIVES:
                p = ret[-2]
                branch = True
            elif b == '@':
                if tokens[i+1][1] == 'label':
                    # lexical node
                    node = LPathTreeModel()
                    node.data['lexical'] = True
                    if tokens[i+2][1] == '=':
                        node.data['label'] = tokens[i+3][1]
                    p.attach(node)
                    p.lpAttachBranch(node)
                    node.setScope(scope[-1])
                if tokens[i+2][1] in OPERATION:
                    i += 3
                else:
                    i += 1
            elif b == '{':
                scope.append(p)
            elif b == '}':
                scope.pop()
        i += 1

    root = root.lpChildren[0]
    #root.lpPrune()
    return root
                
if __name__ == "__main__":
    q = '//VP//NP[==>JJ and ==>NN]'
    t = parse_lpath(q)

    def f(t, n):
        if t is not None:
            print (" "*n) + t.data['label']
            for c in t.children:
                f(c, n+4)
        
    def g(t, n):
        if t is not None:
            print (" "*n) + t.data['label']
            for c in t.lpChildren:
                g(c, n+4)
        else:
            print " "*n + "None"

    g(t,0)
    print translate(t)
