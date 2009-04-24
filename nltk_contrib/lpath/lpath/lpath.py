import time

T0 = time.time()

import sys
import re
from nltk import parse_cfg
from nltk import Tree
from nltk import parse

__all__ = ["translate", "translate2", "get_profile", "get_grammar", "get_base_grammar", "tokenize"]


GR = ""
# The following is the LPath+ grammar.
# Some rules of original grammar, which appear in LPath papers
# until 2006, are commented out using a single pound sign (#).
grammar_text = """
#P -> AP | AP '{' P '}'
P -> S | P S | P LCB P RCB
#AP ->  | S AP
#S -> A T | A T '[' R ']'
S -> S2 | LRB S2 RRB STAR | LRB S2 RRB PLUS | LRB S2 RRB OPT
#
S2 -> S1 | S1 LSB R RSB
#
S1 -> A T
A -> "/" | "//" | "." | "\\" | "\\\\" | "<=" | "=>" | "<==" | "==>" | "<-" | "->" | "<--" | "-->"
#T -> Qname | "_" | "@" Qname C Qname
T -> Qname | "_"
ATT -> AT Qname C Qname
#R -> R "or" R | R "and" R | "not" R | "(" R ")" | P | P C Qname
R -> R OR R | R AND R | LRB R RRB | P | LCB R RCB | ATT | NOT P | NOT ATT | NOT LRB R RRB
C -> "=" | "<=" | ">=" | "<>" | "like"
LCB -> '{'
RCB -> '}'
LRB -> '('
RRB -> ')'
LSB -> '['
RSB -> ']'
PLUS -> '+'
STAR -> '*'
OPT -> '?'
AT -> '@'
OR -> 'or'
AND -> 'and'
NOT -> 'not'
"""


def tokenize(q):
    p = re.compile(r"\s*({|}|\[|]|//|/|\.|\\\\|\\|<==|==>|<=|=>|<--|-->|<-|->|@|or|and|not|\(|\)|>=|=|<>|like|_|\*|\+|\?)\s*")

    tokens = []
    q = q.strip()
    N = len(q)
    d = 0           # scan position
    while d < N:

        # scan and add double-quoted string
        if q[d] == '"':
            for j in range(d+1,N):
                if q[j]=='"' and m!='\\':
                    break
            tokens.append(('s',q[d+1:j]))
            d = j+1
        elif q[d] == '@':
            # If we have an attribute, scan ahead until we reach the end of the attribute name.
            for j in range(d + 1, N):
                if not q[j].isalnum():
                    break
            tokens.append(('r', '@'))
            tokens.append(('s', q[d + 1: j]))
            d = j

        # find next reserved word while scanning free string before it
        d0 = d
        while d < N:
            m = p.match(q, d)
            if m:
                if m.group(1) == '_':
                    if d == d0:
                        break
                else:
                    break
            d += 1
        qname = q[d0:d]

        # if there is a free string, split it and add them to the tokens list
        if qname:
            for s in qname.split():
                tokens.append(('s',s))

        # add the reserved word to the tokens list
        if m:
            tokens.append(('r',m.group(1)))
            d = m.span()[1]
    return tokens


class SerialNumber:
    def __init__(self):
        self.n = 0
    def inc(self):
        self.n += 1
    def __int__(self):
        return self.n
    def __sub__(self, n):
        return self.n - n

    
class AND(list):
    def __init__(self, *args):
        list.__init__(self)
        self.joiner = "and"
        for e in args:
            if isinstance(e, flatten):
                self += e
            else:
                self.append(e)

    def __str__(self):
        L = []
        for x in self:
            if isinstance(x, str):
                L.append(x)
            elif isinstance(x, AND) or isinstance(x, OR) or isinstance(x, NOT):
                L.append(str(x))
            elif isinstance(x, flatten):
                for e in x:
                    L.append("%s%s%s" % tuple(e))
            elif isinstance(x, list):
                L.append("%s%s%s" % tuple(x))
            elif isinstance(x, Trans):
                L.append("exists (%s)" % x.getSql())
            else:
                L.append(str(x))
            L.append(self.joiner)
        return "(" + " ".join(L[:-1]) + ")"

    def __unicode__(self):
        L = []
        for x in self:
            if isinstance(x, str):
                L.append(unicode(x))
            elif isinstance(x, unicode):
                L.append(x)
            elif isinstance(x, AND) or isinstance(x, OR) or isinstance(x, NOT):
                L.append(unicode(x))
            elif isinstance(x, flatten):
                for e in x:
                    L.append("%s%s%s" % tuple(e))
            elif isinstance(x, list):
                L.append("%s%s%s" % tuple(x))
            elif isinstance(x, Trans):
                L.append("exists (%s)" % x.getSql())
            else:
                L.append(unicode(x))
            L.append(self.joiner)
        return "(" + " ".join(L[:-1]) + ")"
    
    def __add__(self, lst):
        self += lst
        return self

        
class OR(AND):
    def __init__(self, *args):
        AND.__init__(self, *args)
        self.joiner = "or"


class GRP(AND):
    pass

    
class NOT:
    def __init__(self, lst):
        self.lst = lst

    def __str__(self):
        return "not " + str(self.lst)

    def __unicode__(self):
        return "not " + unicode(self.lst)

    
class flatten(list):
    pass


class Step:
    FIELDMAP = {
        'sid':'sid',
        'tid':'tid',
        'id':'id',
        'pid':'pid',
        'left':'l',
        'right':'r',
        'depth':'d',
        'type':'type',
        'name':'name',
        'value':'value',
        }
    def __init__(self):
        self.conditional = None
        self.WHERE = []

    def getConstraints(self):
        C = []
        for c1,op,c2 in self.WHERE:
            C.append(["%s.%s" % (self.tab,c1), op, c2])
        return C

    def __getattr__(self, k):
        if k in self.FIELDMAP:
            return self.tab + "." + self.FIELDMAP[k]
        else:
            if hasattr(self, k):
                eval('self.' + k)
            else:
                raise(AttributeError("Step instance has no attribute '%s'" % k))

    
class Trans:
    TR = {
        '_':'under',
        }
    
    def __init__(self, t, sn, pstep=None, tname='T', scope=None):
        assert(type(t) == Tree)
        assert(t.node == 'P' or t.node == 'ATT' or t.node == 'R')

        self.sn = sn
        self.pstep = pstep
        self.tname = tname
        if self.pstep:
            self.prefix = self.pstep.tab
            self.step = pstep
        else:
            self.prefix = ""
        self.WHERE = AND()
        self.WHEREs = []    # context stack
        #self.WHERE2 = []    # restrictions
        #self.WHERE3 = []    # inter-step constraints
        #self.WHERE3 = []
        #self.WHERE4 = []    # scopic constraints
        #self.WHERE5 = []    # alignment constraints
        #self.WHERE6 = []    # conditional axis
        self.steps = []
        self.scope = scope
        
        self._expand(t)

        if self.pstep:
            self._interpreteAxis(self.pstep, self.steps[0].axis, self.steps[0])

    def _getNewTableName(self):
        s = "%s%d" % (self.tname,self.sn,)
        self.sn.inc()
        return s
    
    def _beginGrp(self, cls=GRP):
        self.WHEREs.append(self.WHERE)
        self.WHERE = cls()

    def _finishGrp(self, cls=None):
        if cls is not None:
            self.WHEREs[-1].append(cls(self.WHERE))
        else:
            self.WHEREs[-1].append(self.WHERE)
        self.WHERE = self.WHEREs.pop()
        
    def getSql(self):
        if self.pstep:
            sql = "select 1 "
        else:
            sql = "select %s.* " % self.steps[-1].tab
        sql += "from %s " % ",".join([self.tname+" "+s.tab for s in self.steps])

        for s in self.steps:
            if not s.conditional:
                self.WHERE += s.getConstraints()
            
        for i,s in enumerate(self.steps[:-1]):
            s2 = self.steps[i+1]
            self._interpreteAxis(s, s2.axis, s2)

        w = unicode(self.WHERE).strip()
        if w: sql += "where %s" % w

        return sql
            
    def _expand(self, t):
        name = "_" + t.node
        for c in t:
            name += "_"
            if isinstance(c,str) or isinstance(c,unicode):
                name += self.TR[c]
            else:
                name += c.node
        return eval("self.%s" % name)(t)
            
    def _interpreteScope(self, scope, step):
        self.WHERE += [
            [scope.left, "<=", step.left],
            [scope.right, ">=", step.right]
            ]

    def _alignLeft(self, step1, step2):
        self.WHERE += [
            [step1.left, "=", step2.left],
            ]

    def _alignRight(self, step1, step2):
        self.WHERE += [
            [step1.right, "=", step2.right],
            ]
        
    def _interpreteAxis(self, step1, axis, step2):
        if step2.conditional is not None:
            if axis == '/': 
                zWHERE = AND(
                    ["z.sid", "=", step2.sid],
                    ["z.tid", "=", step2.tid],
                    ["z.left", ">=", step1.left],
                    ["z.left", "<=", step2.left],
                    ["z.right", "<=", step1.right],
                    ["z.right", ">=", step2.right],
                    ["z.depth", ">", step1.depth],
                    ["z.depth", "<=", step2.depth],
                    )

                if hasattr(step2, 'conditionalRestriction'):
                    s = step2.conditionalRestriction.getSql()
                    s = re.sub(" "+step2.tab+"\\.", " z.", s)
                    s = "exists (%s)" % s
                    zWHERE.append(NOT(GRP(flatten(step2.getConstraints()),s)))
                else:
                    zWHERE.append(NOT(GRP(flatten(step2.getConstraints()))))

                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    ]
                    
                if step2.conditional == '?':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.id, "=", step2.pid]) +
                        step2.getConstraints()
                        ))
                        ]
                elif step2.conditional == '+':
                    self.WHERE += [
                        [step1.left, "<=", step2.left],
                        [step1.right, ">=", step2.right],
                        [step1.depth, "<", step2.depth],
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ]
                elif step2.conditional == '*':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.left, "<=", step2.left],
                            [step1.right, ">=", step2.right],
                            [step1.depth, "<", step2.depth],
                            "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE)))
                        ))
                        ]
                    
            elif axis == '\\': 
                zWHERE = AND(
                    ["z.sid", "=", step2.sid],
                    ["z.tid", "=", step2.tid],
                    ["z.left", "<=", step1.left],
                    ["z.left", ">=", step2.left],
                    ["z.right", ">=", step1.right],
                    ["z.right", "<=", step2.right],
                    ["z.depth", "<", step1.depth],
                    ["z.depth", ">=", step2.depth],
                    )

                if hasattr(step2, 'conditionalRestriction'):
                    s = step2.conditionalRestriction.getSql()
                    s = re.sub(" "+step2.tab+"\\.", " z.", s)
                    s = "exists (%s)" % s
                    zWHERE.append(NOT(GRP(flatten(step2.getConstraints()),s)))
                else:
                    zWHERE.append(NOT(GRP(flatten(step2.getConstraints()))))

                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    ]
                    
                if step2.conditional == '?':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.pid, "=", step2.id]) +
                        step2.getConstraints()
                        ))
                        ]
                elif step2.conditional == '+':
                    self.WHERE += [
                        [step1.left, ">=", step2.left],
                        [step1.right, "<=", step2.right],
                        [step1.depth, ">", step2.depth],
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ]
                elif step2.conditional == '*':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.left, ">=", step2.left],
                            [step1.right, "<=", step2.right],
                            [step1.depth, ">", step2.depth],
                            "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE)))
                        ))
                        ]
                    
            elif axis == '->':
                cWHERE = AND(
                    ["c.sid", "=", "z.sid"],
                    ["c.tid", "=", "z.tid"],
                    ["c.pid", "=", "z.id"]
                    )
                wWHERE = AND(
                    ["w.sid", "=", "z.sid"],
                    ["w.tid", "=", "z.tid"],
                    ["w.left", "<", "z.right"],
                    ["w.right", ">", "z.left"],
                    ["w.left", ">=", step1.right],
                    ["w.right", "<=", step2.left],
                    flatten(step2.getConstraints())
                    )

                if hasattr(step2, 'conditionalRestriction'):
                    s = step2.conditionalRestriction.getSql()
                    s = re.sub(" "+step2.tab+"\\.", " w.", s)
                    s = "exists (%s)" % s
                    zWHERE.append(s)

                zWHERE = AND(
                    ["z.sid", "=", step2.sid],
                    ["z.tid", "=", step2.tid],
                    ["z.left", ">=", step1.right],
                    ["z.right", "<=", step2.left],
                    NOT(GRP(flatten(step2.getConstraints()))),
                    "not exists (select 1 from %s c where %s)" % (self.tname,unicode(cWHERE)),
                    "not exists (select 1 from %s w where %s)" % (self.tname,unicode(wWHERE))
                    )

                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    ]
                
                if step2.conditional == '?':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.right, "=", step2.left],
                            flatten(step2.getConstraints())
                        )))
                        ]
                elif step2.conditional == '+':
                    self.WHERE += [
                        [step1.right, "<=", step2.left],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ]
                elif step2.conditional == '*':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        GRP(AND(
                        [step1.right, "<=", step2.left],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ))))
                        ]
                        
            elif axis == '<-':
                cWHERE = AND(
                    ["c.sid", "=", "z.sid"],
                    ["c.tid", "=", "z.tid"],
                    ["c.pid", "=", "z.id"]
                    )
                wWHERE = AND(
                    ["w.sid", "=", "z.sid"],
                    ["w.tid", "=", "z.tid"],
                    ["w.left", "<", "z.right"],
                    ["w.right", ">", "z.left"],
                    ["w.left", ">=", step2.right],
                    ["w.right", "<=", step1.left],
                    flatten(step2.getConstraints())
                    )

                if hasattr(step2, 'conditionalRestriction'):
                    s = step2.conditionalRestriction.getSql()
                    s = re.sub(" "+step2.tab+"\\.", " w.", s)
                    s = "exists (%s)" % s
                    zWHERE.append(s)

                zWHERE = AND(
                    ["z.sid", "=", step2.sid],
                    ["z.tid", "=", step2.tid],
                    ["z.left", ">=", step2.right],
                    ["z.right", "<=", step1.left],
                    NOT(GRP(flatten(step2.getConstraints()))),
                    "not exists (select 1 from %s c where %s)" % (self.tname,unicode(cWHERE)),
                    "not exists (select 1 from %s w where %s)" % (self.tname,unicode(wWHERE))
                    )

                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    ]
                
                if step2.conditional == '?':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.left, "=", step2.right],
                            flatten(step2.getConstraints())
                        )))
                        ]
                elif step2.conditional == '+':
                    self.WHERE += [
                        [step1.left, ">=", step2.right],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ]
                elif step2.conditional == '*':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        GRP(AND(
                        [step1.left, ">=", step2.right],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ))))
                        ]
                        
            elif axis == '=>':
                cWHERE = AND(
                    ["c.sid", "=", "z.sid"],
                    ["c.tid", "=", "z.tid"],
                    ["c.pid", "=", "z.id"]
                    )
                wWHERE = AND(
                    ["w.sid", "=", "z.sid"],
                    ["w.tid", "=", "z.tid"],
                    ["w.left", "<", "z.right"],
                    ["w.right", ">", "z.left"],
                    ["w.left", ">=", step1.right],
                    ["w.right", "<=", step2.left],
                    flatten(step2.getConstraints())
                    )

                if hasattr(step2, 'conditionalRestriction'):
                    s = step2.conditionalRestriction.getSql()
                    s = re.sub(" "+step2.tab+"\\.", " w.", s)
                    s = "exists (%s)" % s
                    zWHERE.append(s)

                zWHERE = AND(
                    ["z.sid", "=", step2.sid],
                    ["z.tid", "=", step2.tid],
                    ["z.left", ">=", step1.right],
                    ["z.right", "<=", step2.left],
                    NOT(GRP(flatten(step2.getConstraints()))),
                    "not exists (select 1 from %s c where %s)" % (self.tname,unicode(cWHERE)),
                    "not exists (select 1 from %s w where %s)" % (self.tname,unicode(wWHERE))
                    )

                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    ]
                
                if step2.conditional == '?':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.right, "=", step2.left],
                            [step1.pid, "=", step2.pid],
                            flatten(step2.getConstraints())
                        )))
                        ]
                elif step2.conditional == '+':
                    self.WHERE += [
                        [step1.right, "<=", step2.left],
                        [step1.pid, "=", step2.pid],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ]
                elif step2.conditional == '*':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        GRP(AND(
                        [step1.right, "<=", step2.left],
                        [step1.pid, "=", step2.pid],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ))))
                        ]
                        
            elif axis == '<=':
                cWHERE = AND(
                    ["c.sid", "=", "z.sid"],
                    ["c.tid", "=", "z.tid"],
                    ["c.pid", "=", "z.id"]
                    )
                wWHERE = AND(
                    ["w.sid", "=", "z.sid"],
                    ["w.tid", "=", "z.tid"],
                    ["w.left", "<", "z.right"],
                    ["w.right", ">", "z.left"],
                    ["w.left", ">=", step2.right],
                    ["w.right", "<=", step1.left],
                    flatten(step2.getConstraints())
                    )

                if hasattr(step2, 'conditionalRestriction'):
                    s = step2.conditionalRestriction.getSql()
                    s = re.sub(" "+step2.tab+"\\.", " w.", s)
                    s = "exists (%s)" % s
                    zWHERE.append(s)

                zWHERE = AND(
                    ["z.sid", "=", step2.sid],
                    ["z.tid", "=", step2.tid],
                    ["z.left", ">=", step2.right],
                    ["z.right", "<=", step1.left],
                    NOT(GRP(flatten(step2.getConstraints()))),
                    "not exists (select 1 from %s c where %s)" % (self.tname,unicode(cWHERE)),
                    "not exists (select 1 from %s w where %s)" % (self.tname,unicode(wWHERE))
                    )

                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    ]
                
                if step2.conditional == '?':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        AND([step1.left, "=", step2.right],
                            [step1.pid, "=", step2.pid],
                            flatten(step2.getConstraints())
                        )))
                        ]
                elif step2.conditional == '+':
                    self.WHERE += [
                        [step1.left, ">=", step2.right],
                        [step1.pid, "=", step2.pid],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ]
                elif step2.conditional == '*':
                    self.WHERE += [
                        GRP(OR(
                        [step1.id, "=", step2.id],
                        GRP(AND(
                        [step1.left, ">=", step2.right],
                        [step1.pid, "=", step2.pid],
                        flatten(step2.getConstraints()),
                        "not exists (select 1 from %s z where %s)" % (self.tname,unicode(zWHERE))
                        ))))
                        ]
                        
        # normal (non-conditional) axis
        elif step2.conditional is None:
            if axis == '/':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.id, "=", step2.pid],
                    ]
            elif axis == '//':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.left, "<=", step2.left],
                    [step1.right, ">=", step2.right],
                    [step1.depth, "<", step2.depth],
                    ]
            elif axis == '\\':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.pid, "=", step2.id]
                    ]
            elif axis == '\\\\':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.depth, ">", step2.depth],
                    [step1.left, ">=", step2.left],
                    [step1.right, "<=", step2.right]
                    ]
            elif axis == '->':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.right, "=", step2.left],
                    ]
            elif axis == '-->':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.right, "<=", step2.left],
                    ]
            elif axis == '<-':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.left, "=", step2.right],
                    ]
            elif axis == '<--':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.left, ">=", step2.right],
                    ]
            elif axis == '=>':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.right, "=", step2.left],
                    [step1.pid, "=", step2.pid]
                    ]
            elif axis == '==>':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.right, "<=", step2.left],
                    [step1.pid, "=", step2.pid]
                    ]
            elif axis == '<=':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.left, "=", step2.right],
                    [step1.pid, "=", step2.pid]
                    ]
            elif axis == '<==':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.left, ">=", step2.right],
                    [step1.pid, "=", step2.pid]
                    ]
            elif axis == '.' or axis == '@':
                self.WHERE += [
                    [step1.sid, "=", step2.sid],
                    [step1.tid, "=", step2.tid],
                    [step1.id, "=", step2.id]
                    ]
                
    def _P_S(self, tree):
        self._expand(tree[0])
        
    def _P_P_S(self, tree):
        p = tree[0]
        s = tree[1]
        self._expand(p)
        self._expand(s)
        
    def _P_P_LCB_P_RCB(self, tree):
        p1 = tree[0]
        p2 = tree[2]
        self._expand(p1)
        oldscope = self.scope
        self.scope = self.step
        self._expand(p2)
        self.scope = oldscope
        
    def _S_S2(self, tree):
        self._expand(tree[0])
        
    def _S_LRB_S2_RRB_STAR(self, tree):
        s2 = tree[1]
        
        self.step.conditional = '*'
        self._expand(s2)
    
    def _S_LRB_S2_RRB_PLUS(self, tree):
        s2 = tree[1]
        
        self.step.conditional = '+'
        self._expand(s2)
        
    def _S_LRB_S2_RRB_OPT(self, tree):
        s2 = tree[1]
        
        self.step.conditional = '?'
        self._expand(s2)
        
    def _S2_S1(self, tree):
        self._expand(tree[0])
        
    def _S2_S1_LSB_R_RSB(self, tree):
        s1 = tree[0]
        r = tree[2]
        
        self._expand(s1)
        self._expand(r)
        
    def _S1_A_T(self, tree):
        a = tree[0]
        t = tree[1]
        
        self.step = Step()
        if self.steps:
            self.step.sn = self.steps[-1].sn + 1
        else:
            self.step.sn = 0
        self.step.axis = a[0]
        #self.step.tab = self.prefix + self.tname + str(self.step.sn)
        self.step.tab = self._getNewTableName()
        self.steps.append(self.step)

        self._expand(t)

        if self.scope:
            self._interpreteScope(self.scope, self.step)

    def _T_Qname(self, t):
        tag = t[0][0]
        if tag[0] == '^':
            tag = tag[1:]
            if len(self.steps) > 1:
                if self.scope:
                    self._alignLeft(self.scope, self.step)
        if tag[-1] == '$':
            tag = tag[:-1]
            if len(self.steps) > 1:
                if self.scope:
                    self._alignRight(self.scope, self.step)
        self.step.WHERE = [
                ['type','=',"'syn'"],
                ['name','=',"'%s'" % tag],
                ]

    def _T_under(self, t):
        self.step.WHERE = [
            ['type','=',"'syn'"]
            ]
    
    def _ATT_AT_Qname_C_Qname(self, t):
        self.step = Step()
        if self.steps:
            self.step.sn = self.steps[-1].sn + 1
        else:
            self.step.sn = 0
        self.step.axis = '@'
        #self.step.tab = self.prefix + self.tname + str(self.step.sn)
        self.step.tab = self._getNewTableName()
        self.steps.append(self.step)

        self.step.WHERE = [
            ['type','=',"'att'"],
            ['name','=',"'@%s'" % t[1][0]],
            ['value', " %s " % t[2][0],"'%s'" % t[3][0]],
            ]

    def _R_R_OR_R(self, t):
        self._beginGrp(OR)
        self._expand(t[0])
        self._expand(t[2])
        self._finishGrp()

    def _R_R_AND_R(self, t):
        self._beginGrp(AND)
        self._expand(t[0])
        self._expand(t[2])
        self._finishGrp()

    def _R_LRB_R_RRB(self, t):
        self._beginGrp(GRP)
        self._expand(t[1])
        self._finishGrp()

    def _R_P(self, t):
        tr = Trans(t[0], self.sn, self.step, self.tname, self.scope)
        self.WHERE.append(tr)

    def _R_LCB_R_RCB(self, t):
        oldscope = self.scope
        self.scope = self.step
        self._beginGrp()
        self._expand(t[1])
        self._finishGrp()
        self.scope = oldscope
        
    def _R_ATT(self, t):
        tr = Trans(t[0], self.sn, self.step, self.tname, self.scope)
        self.WHERE.append(tr)

    def _R_NOT_P(self, t):
        tr = Trans(t[1], self.sn, self.step, self.tname, self.scope)
        self.WHERE.append(NOT(GRP(tr)))

    def _R_NOT_ATT(self, t):
        tr = Trans(t[1], self.sn, self.step, self.tname, self.scope)
        self.WHERE.append(NOT(GRP(tr)))
        
    def _R_NOT_LRB_R_RRB(self, t):
        self._beginGrp(GRP)
        self._expand(t[2])
        self._finishGrp(NOT)

class TransFlat(Trans):
    def getSql(self):
        if not hasattr(self,"steps2"):
            self.steps2 = []
        if self.pstep:
            sql = "select 1 "
        else:
            s = ",".join([x.tab+".*" for x in self.steps+self.steps2])                
            sql = "select %s " % s
        sql += "from %s " % ",".join([self.tname+" "+s.tab for s in self.steps+self.steps2])

        for s in self.steps:
            if not s.conditional:
                self.WHERE += s.getConstraints()
            
        for i,s in enumerate(self.steps[:-1]):
            s2 = self.steps[i+1]
            self._interpreteAxis(s, s2.axis, s2)

        w = unicode(self.WHERE).strip()
        if w: sql += "where %s" % w
        return sql
    
    def _R_P(self, t):
        if not hasattr(self,'steps2'): self.steps2 = []
        tr = TransFlat(t[0], self.sn, self.step, self.tname, self.scope)
        self.steps2 += tr.steps
        for s in tr.steps:
            if not s.conditional:
                tr.WHERE += s.getConstraints()
        for i,s in enumerate(tr.steps[:-1]):
            s2 = tr.steps[i+1]
            tr._interpreteAxis(s, s2.axis, s2)
        self.WHERE.append(unicode(tr.WHERE).strip())
    
def translate2(q,tname='T'):
    global T2, T3, T4, T5, T6, GR
    
    T2 = time.time()

    # tokenization
    l = tokenize(q)
    tokens = [a[1] for a in l]
    assert(tokens[0] == '//')
    T3 = time.time()

    # build grammar
    GR = grammar_text
    for typ, t in l:
        if typ == 's':
            GR += "Qname -> '" + t + "'\n"
    grammar = parse_cfg(GR)
    parser = parse.ChartParser(grammar, parse.TD_STRATEGY)
    T4 = time.time()

    # chart-parse the query
    trees = parser.nbest_parse(tokens)
    if not trees:
        T5 = T6 = time.time()
        return None, None
    tree = trees[0]
    T5 = time.time()

    # translate the parse tree
    r = Trans(tree,SerialNumber(),tname=tname).getSql()
    T6 = time.time()

    try:
        r1 = TransFlat(tree,SerialNumber(),tname=tname).getSql()
    except:
        r1 = None
   
    r1 = TransFlat(tree,SerialNumber(),tname=tname).getSql()
    return r, r1


def translate(q,tname='T'):
    return translate2(q,tname)[0]


def print_profile():
    print
    print "     python startup: %6.3fs" % (T1-T0)
    print " query tokenization: %6.3fs" % (T3-T2)
    print "    grammar parsing: %6.3fs" % (T4-T3)
    print "      chart parsing: %6.3fs" % (T5-T4)
    print "        translation: %6.3fs" % (T6-T5)
    print

def get_profile():
    # tok/grammar/parsing/trans times
    return (T3-T2,T4-T3,T5-T4,T6-T5)

def get_grammar():
    """
    Returns the CFG grammar that has recently been used.
    """
    return GR

def get_base_grammar():
    """
    Returns the base LPath+ CFG grammar.
    """
    return grammar_text

T1 = time.time()
T2 = T3 = T4 = T5 = T6 = 0.0


if __name__ == "__main__":
    
    import sys
    #l = tokenize('//A//B')
    q = '//A(/B[{//C->D$}])+'
    #l = tokenize('//A[{//B-->C}]')
    #l = tokenize('//A[//B or //C]')
    #l = tokenize('//S[//@lex="saw"]')
    #l = tokenize('//VP[//NP$]')
    #l = tokenize('//VP[{//^V->NP->PP$}]')
    #l = tokenize('//A//B//C')

    print translate2(sys.argv[1])[1]
    print_profile()
    #print get_grammar()
