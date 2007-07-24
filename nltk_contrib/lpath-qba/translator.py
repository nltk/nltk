from StringIO import StringIO
import at_lite as at

__all__ = ["translate", "translate_sub"]

def translate_sub(t, selected):
    f = StringIO()

    scope = [None]
    while t:
        while scope[-1] and scope[-1] != t.lpScope:
            f.write('}')
            scope.pop()
            
        if len(t.children) == 0:
            if t == selected: f.write('<font color="red">')
            f.write('@label="%s"' % t.data['label'])
        else:
            ax = translate_axis(t)
            if selected is not None: ax = ax.replace('<','&lt;')
            f.write(ax)
            if t == selected: f.write('<font color="red">')
            if t.lpAlignment() == t.AlignLeft or t.lpAlignment() == t.AlignBoth:
                f.write('^')
            f.write(t.data['label'])
            if t.lpAlignment() == t.AlignRight or t.lpAlignment() == t.AlignBoth:
                f.write('$')

        g = StringIO()
        if '@func' in t.data:
            for v in t.data['@func']:
                g.write('@func="%s" and ' % v)
        if 'lpathFilter' in t.data:
            v = t.data['lpathFilter']
            if selected is not None: v=v.replace('<','&lt;')
            g.write(v+' and ')
        for c in t.lpChildren[1:]:
            h = StringIO()
            if c.getNot():
                h.write('not ')
            h.write(translate_sub(c,selected))
            if c.lpScope == t and len(c.children)>0:
                # terminal(=lexical) node doesn't need '{' and '}'
                g.write('{')
                g.write(h.getvalue())
                g.write('}')
            else:
                g.write(h.getvalue())
            g.write(' and ')
            
        if g.getvalue():
            f.write('[')
            f.write(g.getvalue())
            f.write(']')

        if t == selected: f.write('</font>')

        if t.lpChildren[0] and t.lpChildren[0].lpScope == t:
            scope.append(t)
            f.write('{')
            
        t = t.lpChildren[0]

    f.write('}'*(len(scope)-1))

    return f.getvalue().replace(' and ]', ']')

def translate(t,selected=None):
    L = t.lpRoots()
    if L:
        if t not in L:
            return translate_sub(L[0], selected)
        else:
            return translate_sub(t, selected)
    
def translate_axis(t):
    if t.lpParent is None:
        return '//'

    x = t.getAxisType()
    n1 = t.lpParent
    n2 = t
    if x == t.AxisFollowing:
        if n1.follows(n2):
            return "<--"
        else:
            return "-->"
    elif x == t.AxisImmediateFollowing:
        if n1.follows(n2):
            return "<-"
        else:
            return "->"
    elif x == t.AxisSibling:
        if n1.follows(n2):
            return "<=="
        else:
            return "==>"
    elif x == t.AxisImmediateSibling:
        if n1.follows(n2):
            return "<="
        else:
            return "=>"
    elif x == t.AxisAncestor:
        if n1.isAncestorOf(n2):
            return "//"
        else:
            return "\\\\"
    elif x == t.AxisParent:
        if n1.isAncestorOf(n2):
            return "/"
        else:
            return "\\"

