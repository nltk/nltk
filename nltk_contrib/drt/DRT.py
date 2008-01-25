from nltk.internals import Counter
from Tkinter import Canvas
from Tkinter import Tk
from tkFont import Font
from nltk.sem import logic

class Error(Exception): pass

def unique_variable(counter=None):
    if counter is None: counter = DRS._counter
    unique = counter.get()
    return VariableExpression(Variable('z'+str(unique)))

class Expression(logic.Expression):
    def replace_unique(self, variable, counter=None, replace_bound=False):
        """
        Replace a variable v with a new, uniquely-named variable.
        """
        return self.replace(variable, unique_variable(counter), replace_bound)

    def toFol(self):
        return self
    
    def resolve_anaphora(self, trail=[]):
        return self

    def negate(self):
        if isinstance(self, AbstractDRS):
            return ApplicationDrs(DrsOperator('not'), self)
        else:
            return ApplicationExpression(FolOperator('not'), self)
        
class VariableBinderExpression(Expression, logic.VariableBinderExpression):
    """A variable binding expression: e.g. \\x.M."""

    # for generating "unique" variable names during alpha conversion.
    _counter = Counter()

    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve_anaphora(trail + [self]))

    def toFol(self):
        return self.__class__(self.variable, self.term.toFol())

class LambdaExpression(VariableBinderExpression, logic.LambdaExpression):
    pass

class SomeExpression(VariableBinderExpression, logic.SomeExpression):
    pass

class AllExpression(VariableBinderExpression, logic.AllExpression):
    pass

class Variable(logic.Variable):
    pass

class VariableExpression(Expression, logic.VariableExpression):
    pass

class Constant(logic.Constant):
    pass

class ConstantExpression(Expression, logic.ConstantExpression):
    pass

class IndVariableExpression(VariableExpression, logic.IndVariableExpression):
    pass 

class FolOperator(ConstantExpression, logic.Operator):
    pass

class AbstractDRS(Expression):
    """A Discourse Representation Structure."""
    def __init__(self):
        Expression.__init__(self)
        if self.__class__ is AbstractDRS:
            raise NotImplementedError
        self._size = None
    
    def __add__(self, other):
        raise NotImplementedError
        
    def replace(self, variable, expression, replace_bound=False):
        raise NotImplementedError

    def free(self):
        raise NotImplementedError

    def get_refs(self):
        return []

    def simplify(self):
        raise NotImplementedError
    
    def infixify(self):
        raise NotImplementedError
    
    def __repr__(self):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError
    
    def toFol(self):
        raise NotImplementedError
    
    def tp_equals(self, other):
        '''
        Pass the expression (self <-> other) to the theorem prover.   
        If the prover says it is valid, then the self and other are equal.
        '''
        assert isinstance(self, AbstractDRS)
        assert isinstance(other, AbstractDRS)
        
        from nltk_contrib.inference import inference
        f1 = self.simplify().toFol();
        f2 = other.simplify().toFol();
        bicond = ApplicationExpression(ApplicationExpression(FolOperator('iff'), f1), f2)
        return inference.get_prover(bicond).prove()

    def draw(self, x=3, y=3, canvas=None, use_parens=None):
        raise NotImplementedError

    def get_drawing_size(self, canvas=None, use_parens=None):
        raise NotImplementedError

class DRS(AbstractDRS):
    # for generating "unique" variable names during alpha conversion.
    _counter = Counter()

    """A Discourse Representation Structure."""
    def __init__(self, refs, conds):
        AbstractDRS.__init__(self)
        self.refs = refs   # a list of Variables
        self.conds = conds # a list of Expressions, DRSs, and DRS_concs

    def __add__(self, other):
        """DRS Concatenation"""
        assert isinstance(other, DRS)
        return ConcatenationDRS(ApplicationDRS(DrsOperator(Tokens.DRS_CONC), self), other)
    
    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        r_refs = [] #the list of refs after replacements
        r_conds = [cond for cond in self.conds]
        for ref in self.refs:
            if ref.variable in expression.free():
                v = Variable('z' + str(self._counter.get())) #get a new var name
                r_conds = [cond.replace(ref.variable, VariableExpression(v), True) for cond in r_conds] #replace every instance of 'ref' with 'v' in every condition
                r_refs.append(VariableExpression(v)) #add the new ref ('v') to the list
            else:
                r_refs.append(ref) #no replacement needed; add the ref to the list
        #===============================================================================
        # Alpha convert variables that appear on the left side of an implication.  This special processing is
        # required because referents on the left side of an implication are accessable to the right
        #===============================================================================
        for cond in r_conds:
            if isinstance(cond, ApplicationDRS) and isinstance(cond.first, ApplicationDRS) and isinstance(cond.first.first, DrsOperator) and cond.first.first.operator == 'implies':
                for ref in cond.first.second.get_refs():
                    if ref.variable in expression.free():
                        r_conds.remove(cond)
                        v = Variable('z' + str(self._counter.get())) #get a new var name
                        r_conds.append(cond.replace(ref.variable, VariableExpression(v), True)) #replace every instance of 'ref' with 'v' in the condition
        if replace_bound:
            try:
                r_refs.remove(IndVariableExpression(variable))
                r_refs.append(expression)
            except ValueError: pass
        r_conds = [cond.replace(variable, expression, replace_bound) for cond in r_conds] #replace 'variable' with 'expression' in each condition
        return DRS(r_refs, r_conds)

    def free(self):
        conds_free = set()
        for cond in self.conds:
            conds_free = conds_free.union(cond.free())
        refs_set = set([ref.variable for ref in self.refs])
        return conds_free #.difference(refs_set)

    def get_refs(self):
        return self.refs
    
    def resolve_anaphora(self, trail=[]):
        r_conds = []
        for cond in self.conds:
            r_cond = cond.resolve_anaphora(trail + [self])
            
            # if the condition is of the form '(x = [])' then do not include it
            if not DRS._isNullResolution(r_cond):
                r_conds.append(r_cond)
                
        return self.__class__(self.refs, r_conds)
    
    def _isNullResolution(self):
        return isinstance(self, ApplicationExpression) and \
               isinstance(self.first, ApplicationExpression) and \
               isinstance(self.first.first, FolOperator) and \
               self.first.first.operator == Tokens.EQ and \
               ((isinstance(self.second, PossibleAntecedents) and not self.second) or \
                (isinstance(self.first.second, PossibleAntecedents) and not self.first.second))

    _isNullResolution = staticmethod(_isNullResolution)

    def simplify(self):
        r_refs = [ref.simplify() for ref in self.refs]
        r_conds = [cond.simplify() for cond in self.conds]
        return DRS(r_refs, r_conds)
    
    def infixify(self):
        r_refs = [ref.infixify() for ref in self.refs]
        r_conds = [cond.infixify() for cond in self.conds]
        return DRS(r_refs, r_conds)
    
    def toFol(self):
        accum = None
        
        for cond in self.conds[::-1]:
            if not accum:
                accum = cond.toFol()
            else:
                accum = ApplicationExpression( ApplicationExpression(FolOperator('and'), cond.toFol()), accum) 

        for ref in self.refs[::-1]:
            accum = SomeExpression(ref.variable, accum)
        
        return accum
    
    def __repr__(self):
        accum = '%s([' % (Tokens.DRS)
        first = True
        for ref in self.refs:
            if not first:
                accum += ','
            else:
                first = False
            accum += ref.__str__()
        accum += '],['
        first = True
        for cond in self.conds:
            if not first:
                accum += ','
            else:
                first = False
            accum += cond.__str__()
        accum += '])'
        return accum

    def __str__(self):
        return self.__repr__()

    def draw(self, x=3, y=3, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)
            
        text_height = canvas.font.metrics("linespace")
        x_current = x+canvas._BUFFER #indent the left side
        y_current = y+canvas._BUFFER #indent the top
        
        ######################################
        # Draw Discourse Referents
        ######################################
        text = ''
        first = True
        for ref in self.refs:
            if not first:
                text += ', '
            else:
                first = False
            text += str(ref.variable)
        canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=text)
        max_width = canvas.font.measure(text)
        y_current += text_height+canvas._BUFFER
        horiz_line_y = y_current
        y_current += canvas._BUFFER

        ######################################
        # Draw Conditions
        ######################################
        for cond in self.conds:
            if isinstance(cond, AbstractDRS) or isinstance(cond, ApplicationExpression):
                bottom_right_corner = cond.draw(x_current, y_current, canvas)
                max_width = max(max_width, bottom_right_corner[0]-x_current)
                y_current = bottom_right_corner[1]+canvas._BUFFER
            else:
                text = str(cond)
                canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=text)
                max_width = max(max_width, canvas.font.measure(text))
                y_current += text_height+canvas._BUFFER

        ######################################
        # Draw Box
        ######################################
        x_current = x+max_width+canvas._BUFFER*2
        if (y_current - horiz_line_y) < text_height:
            y_current += text_height
        canvas.create_rectangle(x, y, x_current, y_current)
        canvas.create_line(x, horiz_line_y, x_current, horiz_line_y)

        return (x_current, y_current)

    def get_drawing_size(self, canvas=None, use_parens=None): 
        if not canvas:
            canvas = init_canvas(self)

        text_height = canvas.font.metrics("linespace")
        x_current = canvas._BUFFER #indent the left side
        y_current = canvas._BUFFER #indent the top
        
        ######################################
        # Draw Discourse Referents
        ######################################
        text = ''
        first = True
        for ref in self.refs:
            if not first:
                text += ', '
            else:
                first = False
            text += str(ref.variable)
        max_width = canvas.font.measure(text)
        y_current += text_height+canvas._BUFFER
        horiz_line_y = y_current
        y_current += canvas._BUFFER

        ######################################
        # Draw Conditions
        ######################################
        for cond in self.conds:
            if isinstance(cond, AbstractDRS) or isinstance(cond, ApplicationExpression):
                cond_size = cond.get_drawing_size(canvas)
                max_width = max(max_width, cond_size[0])
                y_current += cond_size[1]+canvas._BUFFER
            else:
                text = str(cond)
                max_width = max(max_width, canvas.font.measure(text))
                y_current += text_height+canvas._BUFFER

        ######################################
        # Draw Box
        ######################################
        x_current = max_width+canvas._BUFFER*2
        if (y_current - horiz_line_y) < text_height:
            y_current += text_height

        self._size = (x_current, y_current)
        return self._size

class DRSVariable(AbstractDRS):
    """A Variable DRS which consists solely of a variable."""
    def __init__(self, variable):
        AbstractDRS.__init__(self)
        assert isinstance(variable, Variable)
        self.variable = variable

    def variables(self):
        return set([self.variable])

    def free(self):
        return set([self.variable])

    def subterms(self):
        return set([self])

    def replace(self, variable, expression, replace_bound=False):
        if self.variable == variable:
            return expression
        else:
            return self
        
    def simplify(self):
        return self

    def infixify(self):
        return self

    def name(self):
        return self.__str__()

    def _skolemise(self, bound_vars, counter):
        return self

    def __str__(self): return '%s' % self.variable
    
    def toFol(self):
        return VariableExpression(self.variable)

    def __repr__(self): return "DRSVariable('%s')" % self.variable

    def __hash__(self): return hash(repr(self))

    def draw(self, x=3, y=3, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)
        text_height = canvas.font.metrics("linespace")

        canvas.create_text(x, y, anchor='nw', font=canvas.font, text=self.variable)
        return (x+canvas.font.measure(self.variable), y+text_height)
       
    def get_drawing_size(self, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        text_height = canvas.font.metrics("linespace")

        self._size = (canvas.font.measure(self.variable), text_height)
        return self._size
       

class LambdaDRS(AbstractDRS):
    """A lambda expression: \\x.M."""
    PREFIX = '\\'

    def __init__(self, variable, term):
        AbstractDRS.__init__(self)
        assert isinstance(variable, Variable)
        assert isinstance(term, AbstractDRS)
        self.variable = variable
        self.term = term
        self.prefix = self.__class__.PREFIX.rstrip()
        self.binder = (self.prefix, self.variable.name)
        self.body = str(self.term)

    def _relabel(self, other):
        """
        Relabel C{other}'s bound variables to be the same as C{self}'s
        variable.
        """
        var = VariableExpression(self.variable)
        return other.term.replace(other.variable, var)

    def applyto(self, other):
        return ApplicationDRS(self, other)

    def variables(self):
        return set([self.variable]).union(self.term.variables())

    def free(self):
        return self.term.free().difference(set([self.variable]))

    def subterms(self):
        return self.term.subterms().union([self])

    def replace(self, variable, expression, replace_bound=False):
        if self.variable == variable:
            return self
        if self.variable in expression.free():
            v = 'z' + str(DRS._counter.get())
            self = self.alpha_convert(Variable(v))
        return self.__class__(self.variable, self.term.replace(variable, expression, replace_bound))
                               

    def alpha_convert(self, newvar):
        """
        Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        """
        term = self.term.replace(self.variable, VariableExpression(newvar))
        return self.__class__(newvar, term)

    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve_anaphora(trail + [self]))

    def simplify(self):
        return self.__class__(self.variable, self.term.simplify())

    def infixify(self):
        return self.__class__(self.variable, self.term.infixify())
    
    def toFol(self):
        return LambdaExpression(self.variable, self.term.toFol())

    def __str__(self, continuation=0):
        # Print \x.\y.M as \x y.M.
        if continuation:
            prefix = ' '
        else:
            prefix = self.__class__.PREFIX
        if self.term.__class__ == self.__class__:
            return '%s%s%s' % (prefix, self.variable, self.term.__str__(1))
        else:
            return '%s%s.%s' % (prefix, self.variable, self.term)

    def __hash__(self):
        return hash(repr(self))

    def _skolemise(self, bound_vars, counter):
        bv = bound_vars.copy()
        bv.add(self.variable)
        return self.__class__(self.variable, self.term._skolemise(bv, counter))

    def __repr__(self):
        return "LambdaDRS('%s', '%s')" % (self.variable, self.term)

    def draw(self, x=3, y=3, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)
        text_height = canvas.font.metrics("linespace")
        
        # Get Variable Info
        text = '%s%s' % (self.__class__.PREFIX, self.variable)
        drs = self.term
        while isinstance(drs, LambdaDRS):
            text += ' %s' % drs.variable
            drs = drs.term
        text += Tokens.DOT
        variables_width = canvas.font.measure(text)

        # Draw Term (first, so that we know where to place the variable)
        bottom_right_corner = drs.draw(x+variables_width, y, canvas)
        # Draw Variables
        canvas.create_text(x, y+(bottom_right_corner[1]-y)/2, anchor='w', font=canvas.font, text=text)

        return bottom_right_corner

    def get_drawing_size(self, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        text_height = canvas.font.metrics("linespace")
        
        text = '%s%s' % (self.__class__.PREFIX, self.variable)
        drs = self.term
        while isinstance(drs, LambdaDRS):
            text += ' %s' % self.variable
            drs = drs.term
        text += Tokens.DOT
        variables_width = canvas.font.measure(text)

        size = drs.get_drawing_size(canvas)
        
        self._size = (size[0]+variables_width, size[1])
        return self._size

class DrsOperator(AbstractDRS):
    """
    A boolean operator, such as 'not' or 'and', or the equality
    relation ('=').
    """
    def __init__(self, operator):
        AbstractDRS.__init__(self)
        assert operator in Tokens.DRS_OPS
        self.constant = operator
        self.operator = operator

    def replace(self, variable, expression, replace_bound=False):
        return self

    def free(self):
        return set()

    def simplify(self):
        return self

    def infixify(self):
        return self
    
    def toFol(self):
        return FolOperator(self.operator)

    def __str__(self): return '%s' % self.operator

    def __repr__(self): return "DrsOperator('%s')" % self.operator

    def draw(self, x=3, y=3, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)
        text_height = canvas.font.metrics("linespace")

        canvas.create_text(x, y, anchor='nw', font=canvas.font, text=self.operator)
        return (x+canvas.font.measure(self.operator), y+text_height)
       
    def get_drawing_size(self, canvas=None, use_parens=None): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        self._size = (canvas.font.measure(self.operator), canvas.font.metrics("linespace"))
        return self._size
       
class ApplicationDRS(AbstractDRS):
    """An application expression: (M N)."""
    def __init__(self, first, second):
        AbstractDRS.__init__(self)
        first_simp = first.simplify()
        assert isinstance(first, AbstractDRS)
        if not (isinstance(first_simp, LambdaDRS) or isinstance(first_simp, DRSVariable)) :
            assert isinstance(second, AbstractDRS)
        self.first = first
        self.second = second

    def variables(self):
        return self.first.variables().union(self.second.variables())

    def free(self):
        return self.first.free().union(self.second.free())

    def _functor(self):
        if isinstance(self.first, ApplicationDRS):
            return self.first._functor()
        else:
            return self.first

    fun = property(_functor,
                   doc="Every ApplicationDRS has a functor.")


    def _operator(self):
        functor = self._functor()
        if isinstance(functor, DrsOperator):
            return str(functor)
        else: 
            raise AttributeError

    op = property(_operator,
                  doc="Only some ApplicationDRSs have operators." )

    def _arglist(self):
        """Uncurry the argument list."""
        arglist = [str(self.second)]
        if isinstance(self.first, ApplicationDRS):
            arglist.extend(self.first._arglist())
        return arglist

    def _args(self):
        arglist = self._arglist()
        arglist.reverse()
        return arglist

    args = property(_args,
                   doc="Every ApplicationDRS has args.")

    def subterms(self):
        first = self.first.subterms()

        second = self.second.subterms()
        return first.union(second).union(set([self]))

    def replace(self, variable, expression, replace_bound=False):
        return self.__class__(self.first.replace(variable, expression, replace_bound),\
                              self.second.replace(variable, expression, replace_bound))

    def get_refs(self):
        first = self.first.simplify()
        if isinstance(first, DrsOperator) and first.operator == Tokens.DRS_CONC:
            second = self.second.simplify()
            refs = second.get_refs()
            return refs
        else:
            return []

    def resolve_anaphora(self, trail=[]):
        trail_addition = [self]
        if isinstance(self.first, ApplicationDRS) \
                and isinstance(self.first.first, DrsOperator) \
                and self.first.first.operator == 'implies':
            trail_addition.append(self.first.second)

        r_first = self.first.resolve_anaphora(trail + trail_addition)
        r_second = self.second.resolve_anaphora(trail + trail_addition)
        return self.__class__(r_first, r_second)

    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()
        if isinstance(first, LambdaDRS):
            variable = first.variable
            term = first.term
            return term.replace(variable, second).simplify()
        else:
            return self.__class__(first, second)

    def infixify(self):
        first = self.first.infixify()
        second = self.second.infixify()
        if isinstance(first, DrsOperator) and not str(first) == 'not':
            return self.__class__(second, first)
        else:
            return self.__class__(first, second)    
        
    def toFol(self):
        if isinstance(self.first, ApplicationDRS) \
                and isinstance(self.first.first, DrsOperator) \
                and self.first.first.operator == 'implies':
            first_drs = self.first.second
            second_drs = self.second

            accum = None
            
            for cond in first_drs.conds[::-1]:
                if not accum:
                    accum = cond.toFol()
                else:
                    accum = ApplicationExpression(ApplicationExpression(FolOperator('and'), cond.toFol()), accum) 
   
            accum = ApplicationExpression(ApplicationExpression(FolOperator('implies'), accum ), second_drs.toFol())
    
            for ref in first_drs.refs[::-1]:
                accum = AllExpression(ref.variable, accum)
            
            return accum
        
        else:    
            return ApplicationExpression(self.first.toFol(), self.second.toFol())

    def _skolemise(self, bound_vars, counter):
        first = self.first._skolemise(bound_vars, counter)
        second = self.second._skolemise(bound_vars, counter)
        return self.__class__(first, second)

    def __str__(self):
        # Print ((M N) P) as (M N P).
        strFirst = str(self.first)
        if isinstance(self.first, ApplicationDRS) and \
           not isinstance(self.second, DrsOperator):
            strFirst = strFirst[1:-1]
        return '(%s %s)' % (strFirst, self.second)

    def __repr__(self): return "ApplicationDRS('%s', '%s')" % (self.first, self.second)

    def __hash__(self): return hash(repr(self))

    def draw(self, x=3, y=3, canvas=None, use_parens=True): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)

        ######################################
        # Get sizes of 'first' and 'second'
        ######################################
        if isinstance(self.first, AbstractDRS):
            first_size = self.first._size
        else:
            first_size = (canvas.font.measure(self.first), canvas.font.metrics("linespace"))
            
        if isinstance(self.second, AbstractDRS):
            second_size = self.second._size
        else:
            second_size = (canvas.font.measure(self.second), canvas.font.metrics("linespace"))
            
        max_height = max(first_size[1], second_size[1])

        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        x_current = x

        if use_parens:
            #Draw Open Paren
            y_current = y+(max_height-canvas.font.metrics("linespace"))/2
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=Tokens.OPEN_PAREN)
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        ######################################
        # Handle 'first'
        ######################################
        y_current = y+(max_height-first_size[1])/2
        if isinstance(self.first, AbstractDRS):
            first_bottom_right_corner = self.first.draw(x_current, y_current, canvas, first_use_parens)
        else:
            text = str(self.first)
            if not first_use_parens:
                text = text[1:-1]
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=text)
            first_bottom_right_corner = (x_current+canvas.font.measure(text), y_current+canvas.font.metrics("linespace"))

        #Put a space between 'first' and 'second'
        x_current = first_bottom_right_corner[0] + canvas.font.measure(' ')

        ######################################
        # Handle 'second'
        ######################################
        y_current = y+(max_height-second_size[1])/2
        if isinstance(self.second, AbstractDRS):
            second_bottom_right_corner = self.second.draw(x_current, y_current, canvas)
        else:
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=self.second)
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        x_current = second_bottom_right_corner[0]

        if use_parens:
            canvas.create_text(x_current, y+(max_height-canvas.font.metrics("linespace"))/2, anchor='nw', font=canvas.font, text=Tokens.CLOSE_PAREN)
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, y+max_height)

    def get_drawing_size(self, canvas=None, use_parens=True): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)

        ######################################
        # Get sizes of 'first' and 'second'
        ######################################
        if isinstance(self.first, AbstractDRS):
            first_size = self.first.get_drawing_size(canvas)
        else:
            first_size = (canvas.font.measure(self.first), canvas.font.metrics("linespace"))
            
        if isinstance(self.second, AbstractDRS):
            second_size = self.second.get_drawing_size(canvas)
        else:
            second_size = (canvas.font.measure(self.second), canvas.font.metrics("linespace"))
            
        max_height = max(first_size[1], second_size[1])

        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        x_current = 0

        if use_parens:
            #Draw Open Paren
            y_current = (max_height-canvas.font.metrics("linespace"))/2
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=Tokens.OPEN_PAREN)
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        ######################################
        # Handle 'first'
        ######################################
        y_current = (max_height-first_size[1])/2
        if isinstance(self.first, AbstractDRS):
            first_bottom_right_corner = (x_current+self.first._size[0], y_current+self.first._size[1])
        else:
            text = str(self.first)
            if not first_use_parens:
                text = text[1:-1]
            first_bottom_right_corner = (x_current+canvas.font.measure(text), y_current+canvas.font.metrics("linespace"))

        #Put a space between 'first' and 'second'
        x_current = first_bottom_right_corner[0] + canvas.font.measure(' ')

        ######################################
        # Handle 'second'
        ######################################
        y_current = (max_height-second_size[1])/2
        if isinstance(self.second, AbstractDRS):
            second_bottom_right_corner = (x_current+self.second._size[0], y_current+self.second._size[1])
        else:
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        if use_parens:
            x_current = second_bottom_right_corner[0]
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        self._size = (x_current, max_height)
        return self._size

class ConcatenationDRS(ApplicationDRS):
    """DRS of the form '(DRS + DRS)'"""
    def __init__(self, first, second):
        AbstractDRS.__init__(self)
        first_simp = first.simplify()
        second_simp = second.simplify()
        assert (isinstance(first, ApplicationDRS) and isinstance(first_simp.first, DrsOperator) and first_simp.first.operator == Tokens.DRS_CONC and isinstance(second, AbstractDRS)) or \
               (isinstance(first, ApplicationDRS) and isinstance(first_simp.second, DrsOperator) and first_simp.second.operator == Tokens.DRS_CONC and isinstance(second, AbstractDRS))
        self.first = first
        self.second = second

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        first = self.first
        second = self.second
        all_refs = self.get_refs()
        for ref in all_refs: # for every ref, across the whole concatenation sequence
            if ref.variable in expression.free():
                v = VariableExpression(Variable('z' + str(DRS._counter.get()))) #get a new var name
                first  = first.replace(ref.variable, v, True)
                second = second.replace(ref.variable, v, True)
        first  = first.replace(variable, expression, replace_bound)
        second = second.replace(variable, expression, replace_bound)
        return self.__class__(first, second)
    
    def resolve_anaphora(self, trail=[]):
        r_first = self.first.resolve_anaphora(trail + [self])
        r_second = self.second.resolve_anaphora(trail + [self])
        return self.__class__(r_first, r_second)

    def get_refs(self):
        return self.first.get_refs() + self.second.get_refs()
            
    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()

        if isinstance(first.second, DRS) and isinstance(second, DRS):
            r_refs = first.second.refs + second.refs
            r_conds = first.second.conds + second.conds
            return DRS(r_refs, r_conds)
        else:
            return self.__class__(first,second)
        
    def toFol(self):
        return ApplicationExpression( ApplicationExpression(FolOperator('and'), self.first.second.toFol()), self.second.toFol())
        
    def __repr__(self): return "ConcatenationDRS('%s', '%s')" % (self.first, self.second)

    def draw(self, x=3, y=3, canvas=None, use_parens=True): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)

        first_size = self.first._size
        second_size = self.second._size

        max_height = max(first_size[1], second_size[1])

        x_current = x
        
        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        if use_parens:
            canvas.create_text(x_current, y+(first_size[1]-canvas.font.metrics("linespace"))/2, anchor='nw', font=canvas.font, text=Tokens.OPEN_PAREN)
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        first_bottom_right_corner = self.first.draw(x_current, y + (max_height - first_size[1])/2, canvas, first_use_parens)
        x_current = first_bottom_right_corner[0] + canvas.font.measure(' ')
        second_bottom_right_corner = self.second.draw(x_current, y + (max_height - second_size[1])/2, canvas)
        x_current = second_bottom_right_corner[0]

        if use_parens:
            canvas.create_text(x_current, y+(first_size[1]-canvas.font.metrics("linespace"))/2, anchor='nw', font=canvas.font, text=Tokens.CLOSE_PAREN)
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, max(first_bottom_right_corner[1], second_bottom_right_corner[1]))

    def get_drawing_size(self, canvas=None, use_parens=True):
        if not canvas:
            canvas = init_canvas(self)

        first_size = self.first._size
        second_size = self.second._size

        max_height = max(first_size[1], second_size[1])

        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        x_current = 0

        if use_parens:
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        first_size = self.first.get_drawing_size(canvas, first_use_parens)
        x_current += first_size[0] + canvas.font.measure(' ')
        second_size = self.second._size
        x_current += second_size[0]

        if use_parens:
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        self._size = (x_current, max(first_size[1], second_size[1]))
        return self._size

class ApplicationExpression(Expression, logic.ApplicationExpression):
    def _arglist(self):
        """Uncurry the argument list."""
        arglist = [self.second]
        if isinstance(self.first, ApplicationExpression):
            arglist.extend(self.first._arglist())
        return arglist

    def resolve_anaphora(self, trail=[]):
        if isinstance(self.first, VariableExpression) and self.first.variable.name == Tokens.PRONOUN:
            possible_antecedents = PossibleAntecedents()
            for ancestor in trail:
                if isinstance(ancestor, AbstractDRS):
                    possible_antecedents.extend(ancestor.get_refs())
        #===============================================================================
        #   This line ensures that statements of the form ( x = x ) wont appear.
        #   Possibly amend to remove antecedents with the wrong 'gender' 
        #===============================================================================
            possible_antecedents.remove(self.second)
            if len(possible_antecedents) == 1:
                eqalityExp = ApplicationExpression(ApplicationExpression(FolOperator(Tokens.EQ), self.second),possible_antecedents[0])
            else:
                eqalityExp = ApplicationExpression(ApplicationExpression(FolOperator(Tokens.EQ), self.second),possible_antecedents) 
            return eqalityExp
        else:
            r_first = self.first.resolve_anaphora(trail + [self])
            r_second = self.second.resolve_anaphora(trail + [self])
            return self.__class__(r_first, r_second)

    def toFol(self):
        return self.__class__(self.first.toFol(), self.second.toFol())

    def draw(self, x=3, y=3, canvas=None, use_parens=True): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)
        if not self._size:
            self.get_drawing_size(canvas, use_parens)

        ######################################
        # Get sizes of 'first' and 'second'
        ######################################
        if isinstance(self.first, AbstractDRS):
            first_size = self.first._size
        else:
            first_size = (canvas.font.measure(self.first), canvas.font.metrics("linespace"))
            
        if isinstance(self.second, AbstractDRS):
            second_size = self.second._size
        else:
            second_size = (canvas.font.measure(self.second), canvas.font.metrics("linespace"))
            
        max_height = max(first_size[1], second_size[1])

        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        x_current = x

        if use_parens:
            #Draw Open Paren
            y_current = y+(max_height-canvas.font.metrics("linespace"))/2
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=Tokens.OPEN_PAREN)
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        ######################################
        # Handle 'first'
        ######################################
        y_current = y+(max_height-first_size[1])/2
        if isinstance(self.first, AbstractDRS):
            first_bottom_right_corner = self.first.draw(x_current, y_current, canvas, first_use_parens)
        else:
            text = str(self.first)
            if not first_use_parens:
                text = text[1:-1]
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=text)
            first_bottom_right_corner = (x_current+canvas.font.measure(text), y_current+canvas.font.metrics("linespace"))

        #Put a space between 'first' and 'second'
        x_current = first_bottom_right_corner[0] + canvas.font.measure(' ')

        ######################################
        # Handle 'second'
        ######################################
        y_current = y+(max_height-second_size[1])/2
        if isinstance(self.second, AbstractDRS):
            second_bottom_right_corner = self.second.draw(x_current, y_current, canvas)
        else:
            canvas.create_text(x_current, y_current, anchor='nw', font=canvas.font, text=self.second)
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        x_current = second_bottom_right_corner[0]

        if use_parens:
            canvas.create_text(x_current, y+(max_height-canvas.font.metrics("linespace"))/2, anchor='nw', font=canvas.font, text=Tokens.CLOSE_PAREN)
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, y+max_height)

    def get_drawing_size(self, canvas=None, use_parens=True): #args define the top-left corner of the box
        if not canvas:
            canvas = init_canvas(self)

        ######################################
        # Get sizes of 'first' and 'second'
        ######################################
        if isinstance(self.first, AbstractDRS):
            first_size = self.first.get_drawing_size(canvas)
        else:
            first_size = (canvas.font.measure(self.first), canvas.font.metrics("linespace"))
            
        if isinstance(self.second, AbstractDRS):
            second_size = self.second.get_drawing_size(canvas)
        else:
            second_size = (canvas.font.measure(self.second), canvas.font.metrics("linespace"))
            
        max_height = max(first_size[1], second_size[1])

        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        x_current = 0

        if use_parens:
            #Draw Open Paren
            y_current = (max_height-canvas.font.metrics("linespace"))/2
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        ######################################
        # Handle 'first'
        ######################################
        y_current = (max_height-first_size[1])/2
        if isinstance(self.first, AbstractDRS):
            first_bottom_right_corner = self.first.get_drawing_size(canvas, first_use_parens)
        else:
            text = str(self.first)
            if not first_use_parens:
                text = text[1:-1]
            first_bottom_right_corner = (x_current+canvas.font.measure(text), y_current+canvas.font.metrics("linespace"))

        #Put a space between 'first' and 'second'
        x_current = first_bottom_right_corner[0] + canvas.font.measure(' ')

        ######################################
        # Handle 'second'
        ######################################
        y_current = (max_height-second_size[1])/2
        if isinstance(self.second, AbstractDRS):
            second_bottom_right_corner = self.second._size
        else:
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        if use_parens:
            x_current = second_bottom_right_corner[0]
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        self._size = (x_current, max_height)
        return self._size

class PossibleAntecedents(list, Expression):
    def variables(self):
        """Set of all variables."""
        raise NotImplementedError

    def free(self):
        """Set of free variables."""
        return set(self)

    def subterms(self):
        """Set of all subterms (including self)."""
        return set([self]) + set(self)

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        result = PossibleAntecedents()
        for item in self:
            if item == variable:
                self.append(expression)
            else:
                self.append(item)
        return result
    
    def simplify(self):
        return self

    def infixify(self):
        return self
    
    def __str__(self):
        result = '['
        for item in self:
            result += item.__str__() + ','
        return result.rstrip(',') + ']'

class Tokens:
    DRS = 'DRS'
    DRS_CONC = '+'
    LAMBDA = '\\'
    DOT = '.'
    COMMA = ','
    OPEN_PAREN = '('
    CLOSE_PAREN = ')'
    OPEN_BRACKET = '['
    CLOSE_BRACKET = ']'
    DRS_OPS = ['or', 'not', 'implies', 'iff']
    DRS_OPS.append(DRS_CONC)
    EQ = '='
    FOL_OPS = [EQ]
    PRONOUN = 'PRO'
    
class Parser:
    """A lambda calculus expression parser."""
    
    def __init__(self, data=None, constants=None):
        if data is not None:
            self.buffer = data
            self.process()
        else:
            self.buffer = ''
        if constants is not None:
            self.constants = constants
        else:
            self.constants = []
        

    def feed(self, data):
        """Feed another batch of data to the parser."""
        self.buffer += data
        self.process()

    def parse(self, data):
        """
        Provides a method similar to other NLTK parsers.

        @type data: str
        @returns: a parsed Expression
        """
        self.feed(data)
        result = self.next()
        return result

    def process(self):
        """Process the waiting stream to make it trivial to parse."""
        self.buffer = self.buffer.replace('\t', ' ')
        self.buffer = self.buffer.replace('\n', ' ')
        self.buffer = self.buffer.replace(Tokens.LAMBDA, ' %s ' % Tokens.LAMBDA)
        self.buffer = self.buffer.replace(Tokens.DRS, ' %s ' % Tokens.DRS)
        self.buffer = self.buffer.replace(Tokens.DRS.lower(), ' %s ' % Tokens.DRS)
        self.buffer = self.buffer.replace(Tokens.DOT, ' %s ' % Tokens.DOT)
        self.buffer = self.buffer.replace(Tokens.COMMA, ' %s ' % Tokens.COMMA)
        self.buffer = self.buffer.replace(Tokens.OPEN_PAREN, ' %s ' % Tokens.OPEN_PAREN)
        self.buffer = self.buffer.replace(Tokens.CLOSE_PAREN, ' %s ' % Tokens.CLOSE_PAREN)
        self.buffer = self.buffer.replace(Tokens.OPEN_BRACKET, ' %s ' % Tokens.OPEN_BRACKET)
        self.buffer = self.buffer.replace(Tokens.CLOSE_BRACKET, ' %s ' % Tokens.CLOSE_BRACKET)
        self.buffer = self.buffer.replace(Tokens.EQ, ' %s ' % Tokens.EQ)

    def token(self, destructive=1):
        """Get the next waiting token.  The destructive flag indicates
        whether the token will be removed from the buffer; setting it to
        0 gives lookahead capability."""
        if self.buffer == '':
            raise Error, "end of stream"
        tok = None
        buffer = self.buffer
        while not tok:
            seq = buffer.split(' ', 1)
            if len(seq) == 1:
                tok, buffer = seq[0], ''
            else:
                assert len(seq) == 2
                tok, buffer = seq
            if tok:
                if destructive:
                    self.buffer = buffer
                return tok
        assert 0 # control never gets here
        return None

    def isVariable(self, token):
        """Is this token a variable (that is, not one of the other types)?"""
        TOKENS = [Tokens.DRS, Tokens.LAMBDA, Tokens.DOT, Tokens.OPEN_PAREN,
                  Tokens.CLOSE_PAREN, Tokens.OPEN_BRACKET, Tokens.CLOSE_BRACKET]
        TOKENS.extend(self.constants)
        TOKENS.extend(Tokens.DRS_OPS)
        TOKENS.extend(Tokens.FOL_OPS)

        return token not in TOKENS 

    def next(self):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
        
        if tok == Tokens.LAMBDA:
            # Expression is a lambda expression: \x.M

            vars = [self.token()]
            while self.isVariable(self.token(0)):
                # Support expressions like: \x y.M == \x.\y.M
                vars.append(self.token())
            tok = self.token()

            if tok != Tokens.DOT:
                raise Error, "parse error, unexpected token: %s" % tok
            term = self.next()
            accum = LambdaDRS(Variable(vars.pop()), term)
            while vars:
                accum = LambdaDRS(Variable(vars.pop()), accum)
            return accum

        elif tok == Tokens.DRS:
            # a DRS
            assert self.token() == Tokens.OPEN_PAREN
            assert self.token() == Tokens.OPEN_BRACKET
            refs = []
            while self.token(0) != Tokens.CLOSE_BRACKET:
                # Support expressions like: drs([x y],C) == drs([x, y],C)
                if self.token(0) == Tokens.COMMA:
                    self.token() # swallow the comma
                else:
                    refs.append(self.next())
            assert self.token() == Tokens.CLOSE_BRACKET # swallow the CLOSE_BRACKET token
            assert self.token() == Tokens.COMMA
            conds = self.next()
            assert self.token() == Tokens.CLOSE_PAREN
            return DRS(refs, conds)

        elif tok == Tokens.OPEN_BRACKET:
            # A list of DRS Conditions
            conds = []
            while self.token(0) != Tokens.CLOSE_BRACKET:
                if self.token(0) == Tokens.COMMA:
                    self.token() # swallow the comma
                else:
                    conds.append(self.next())
            self.token() # swallow the CLOSE_BRACKET token
            return conds
        
        elif tok == Tokens.OPEN_PAREN:
            # Expression is an application expression: (M N)
            first = self.next()
            second = self.next()
            exps = []
            while self.token(0) != Tokens.CLOSE_PAREN:
                # Support expressions like: (M N P) == ((M N) P)
                exps.append(self.next())
            tok = self.token() # swallow the CLOSE_PAREN token
            assert tok == Tokens.CLOSE_PAREN
            if isinstance(second, DrsOperator):
                accum = ApplicationDRS(second, first) # DrsOperators can only be applied to DRSs
            elif isinstance(second, FolOperator):
                accum = ApplicationExpression(second, first)
            else:
                accum = self.make_Application(first, second)
            while exps:
                exp, exps = exps[0], exps[1:]
                accum = self.make_Application(accum, exp)
            return accum

        elif tok in self.constants:
            # Expression is a simple constant expression: a
            return ConstantExpression(Constant(tok))

        elif tok in Tokens.DRS_OPS:
            # Expression is a boolean operator or the equality symbol
            return DrsOperator(tok)
    
        elif tok in Tokens.FOL_OPS:
            # Expression is a boolean operator or the equality symbol
            return FolOperator(tok)

        elif logic.is_indvar(tok):
            # Expression is a boolean operator or the equality symbol
            return IndVariableExpression(Variable(tok))
        
        else:
            if self.isVariable(tok):
                if tok[0].isupper() and tok != Tokens.PRONOUN:
                    # Uppercase variables stand for DRSs
                    return DRSVariable(Variable(tok))
                else:
                    # Expression is a simple variable expression: x
                    return VariableExpression(Variable(tok))
            else:
                raise Error, "parse error, unexpected token: %s" % tok
    
    # This is intended to be overridden, so that you can derive a Parser class
    # that constructs expressions using your subclasses.  So far we only need
    # to overridde Application, but the same thing could be done for
    # other expression types.
    def make_Application(self, first, second):
        first_simp = first.simplify()
        second_simp = second.simplify()
        if (isinstance(first_simp, ApplicationDRS) and isinstance(first_simp.first, DrsOperator) and first_simp.first.operator == Tokens.DRS_CONC and isinstance(second_simp, AbstractDRS)) or \
           (isinstance(second_simp, ApplicationDRS) and isinstance(second_simp.first, DrsOperator) and second_simp.first.operator == Tokens.DRS_CONC and isinstance(first_simp, AbstractDRS)):
            return ConcatenationDRS(first, second)
        elif isinstance(first, DrsOperator) or isinstance(first, AbstractDRS):
            return ApplicationDRS(first, second)
        else:
            return ApplicationExpression(first, second)


    def __repr__(self):
        return 'Next token: \'%s\'' % self.token(0)

    def __str__(self):
        return self.__repr__()

def init_canvas(drs):
    #font = Font(family='helvetica', size=12)
    buffer = 3

    master = Tk()
    canvas = Canvas(master, width=0, height=0)
    font = Font(font=canvas.itemcget(canvas.create_text(0, 0, text=''), 'font'))
    canvas.font = font
    canvas._BUFFER = buffer

    size = drs.get_drawing_size(canvas)

    canvas = Canvas(master, width=size[0]+20, height=size[1]+20, bg='white')
    #canvas = Canvas(master, width=300, height=300)
    canvas.pack()
    canvas.font = font
    canvas._BUFFER = buffer
    return canvas

def expressions():
    return ['drs([x,y],[(sees x y)])',
            'drs([x],[(man x), (walks x)])',
            '\\x.drs([],[(man x), (walks x)])',
            '\\x y.drs([],[(sees x y)])',

            '(\\x.drs([],[(walks x)]) john)',
            '(\\R x.drs([],[(big x R)]) \\y.drs([],[(mouse y)]))',
            
#            '(drs([x],[(walks x)]) + drs([y],[(runs y)]))',
#            '(drs([x,y],[(walks x), (jumps y)]) + (drs([z],[(twos z)]) + drs([w],[(runs w)])))',
#            '((drs([],[(walks x)]) + drs([],[(twos x)])) + drs([],[(runs x)]))',
            '((drs([],[(walks x)]) + drs([],[(runs x)])) + (drs([],[(threes x)]) + drs([],[(fours x)])))',
#            '(drs([],[(walks x)]) + (runs x))',
#            '((walks x) + drs([],[(runs x)]))',
#            '((walks x) + (runs x))',

            '(drs([],[(walks x)]) implies drs([],[(runs x)]))',
#            '(drs([],[(walks x)]) implies (runs x))',
#            '((walks x) implies drs([],[(walks x)]))',
#            '((walks x) implies (runs x))'
            
            'drs([x],[(PRO x),(sees John x)])',
            'drs([x],[(man x), (not drs([],[(walks x)]))])',
            'drs([],[(drs([x],[(man x)]) implies drs([],[(walks x)]))])'
            ]

def demo(ex=-1, draw=False, catch_exception=True):
    exps = expressions()
    for (i, exp) in zip(range(len(exps)),exps):
        if i==ex or ex==-1:
            drs = Parser().parse(exp).simplify().infixify()
            if(not draw):
                print '[[[Example %s]]]: %s' % (i, exp)
                try:
                    print '  %s' % drs
                except Exception, (strerror):
                    if catch_exception:
                        print '  Error: %s' % strerror
                    else:
                        raise
                print ''
            else:
                canvas = init_canvas(drs)
                y_current = canvas._BUFFER
                canvas.create_text(canvas._BUFFER, y_current, anchor='nw', font=canvas.font, text='Example %s: %s' % (i, exp))
                try:
                    y_current += canvas.font.metrics("linespace")+canvas._BUFFER
                    size = drs.draw(canvas._BUFFER,y_current,canvas)
                    y_current += size[1]+canvas._BUFFER
                    drs.draw(canvas._BUFFER, y_current, canvas)
                except Exception, (strerror):
                    if catch_exception:
                        canvas.create_text(canvas._BUFFER, y_current, anchor='nw', font=canvas.font, text='  Error: %s' % strerror)
                    else:
                        raise
                
def testToFol():
    for t in expressions():
        p = Parser().parse(t)
        s = p.simplify()
        f = s.toFol();
        i = f.infixify()
        print i
        
def test():
    a = Parser().parse(r'\Q.(drs([x],[(dog x)]) + (Q x))')
    b = Parser().parse(r'\x2.drs([],[(drs([x],[(girl x)]) implies drs([],[(chases x x2)]))])')
    ab = a.applyto(b)
    print ab
    s = ab.simplify()
    print s
    
def test2():
    a = Parser().parse(r'\Q.(drs([x],[(x = john),(walks x)]) + Q)')
    b = Parser().parse(r'drs([x],[(PRO x),(leaves x)])')
    ab = a.applyto(b)
    print ab
    s = ab.simplify()
    print s
    
def test3():
    a = Parser().parse(r'\Q.drs([],[(drs([x],[(girl x)]) implies (Q x))])')
    b = Parser().parse(r'\x1.drs([x],[(dog x),(chases x1 x)])')
    ab = a.applyto(b)
    print ab
    s = ab.simplify()
    print s
    
def testAlpha():
    a = Parser().parse(r'\P Q.((drs([x],[(dog x)]) + (P x)) + (Q x))')
    print a
    x = Parser().parse(r'x')
    z = Parser().parse(r'z')
    print a.replace(x.variable, z, True)
    print a.replace(x.variable, z, False)
    print a.replace_unique(x.variable, None, True)
    
def testResolve_anaphora():
    print 'Test resolve_anaphora():'
    drs = Parser().parse(r'drs([x,y,z],[(dog x), (cat y), (walks z), (PRO z)])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(drs.simplify().resolve_anaphora().infixify()) + '\n'

    drs = Parser().parse(r'drs([],[(drs([x],[(dog x)]) implies drs([y],[(walks y), (PRO y)]))])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(drs.simplify().resolve_anaphora().infixify()) + '\n'

    drs = Parser().parse(r'drs([],[((drs([x],[]) + drs([],[(dog x)])) implies drs([y],[(walks y), (PRO y)]))])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(drs.simplify().resolve_anaphora().infixify()) + '\n'

    drs = Parser().parse(r'drs([x],[(walks x), (PRO x)])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(drs.simplify().resolve_anaphora().infixify()) + '\n'

def testTp_equals():
    a = Parser().parse(r'drs([x],[(man x), (walks x)])')
    b = Parser().parse(r'drs([x],[(walks x), (man x)])')
    print '%s == %s' % (a,b)
    print a.tp_equals(b)

if __name__ == '__main__':
    demo()
    print '\n'
    testResolve_anaphora()
    print '\n'
    testToFol()
