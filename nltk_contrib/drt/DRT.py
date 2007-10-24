from nltk.utilities import Counter
from nltk.sem.logic import Expression
from nltk.sem.logic import Variable
from nltk.sem.logic import VariableExpression
from nltk.sem.logic import Constant
from nltk.sem.logic import ConstantExpression
from nltk.sem.logic import IndVariableExpression
from nltk.sem.logic import is_indvar
from nltk.sem.logic import Operator as FolOperator

from Tkinter import Canvas

class Error(Exception): pass

class AbstractDRS(Expression):
    """A Discourse Representation Structure."""
    def __add__(self, other):
        raise NotImplementedError
        
    def replace(self, variable, expression):
        raise NotImplementedError

    def replace_with_side_effect(self, variable, expression):
        raise NotImplementedError

    def free(self):
        raise NotImplementedError

    def get_refs(self):
        raise NotImplementedError

    def simplify(self):
        raise NotImplementedError
    
    def infixify(self):
        raise NotImplementedError
    
    def __repr__(self):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

    def draw(self, x=3, y=3, canvas=None, use_parens=None):
        raise NotImplementedError

    def get_drawing_size(self, canvas=None, use_parens=None):
        raise NotImplementedError

class DRS(AbstractDRS):
    # for generating "unique" variable names during alpha conversion.
    _counter = Counter()

    """A Discourse Representation Structure."""
    def __init__(self, refs, conds):
        self.refs = refs   # a list of Variables
        self.conds = conds # a list of Expressions, DRSs, and DRS_concs

    def __add__(self, other):
        """DRS Concatination"""
        assert isinstance(other, DRS)
        return ConcatinationDRS(ApplicationDRS(DrsOperator(Tokens.DRS_CONC), self), other)
        
    def replace(self, variable, expression):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        r_refs = [] #the list of refs after replacements
        r_conds = [cond for cond in self.conds]
        for ref in self.refs:
            if ref.variable in expression.free():
                v = Variable('z' + str(self._counter.get())) #get a new var name
                r_conds = [cond.replace(ref.variable, VariableExpression(v)) for cond in r_conds] #replace every instance of 'ref' with 'v' in every condition
                r_refs.append(VariableExpression(v)) #add the new ref ('v') to the list
            else:
                r_refs.append(ref) #no replacement needed; add the ref to the list
        r_conds = [cond.replace(variable, expression) for cond in r_conds] #replace 'variable' with 'expression' in each condition
        return DRS(r_refs, r_conds)

    def replace_with_side_effect(self, variable, expression):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        r_self = self.replace(variable, expression)
        self.refs = r_self.refs
        self.conds = r_self.conds

    def free(self):
        conds_free = set()
        for cond in self.conds:
            conds_free = conds_free.union(cond.free())
        refs_set = set([ref.variable for ref in self.refs])
        return conds_free.difference(refs_set)

    def get_refs(self):
        return self.refs

    def simplify(self):
        r_refs = [ref.simplify() for ref in self.refs]
        r_conds = [cond.simplify() for cond in self.conds]
        return DRS(r_refs, r_conds)
    
    def infixify(self):
        r_refs = [ref.infixify() for ref in self.refs]
        r_conds = [cond.infixify() for cond in self.conds]
        return DRS(r_refs, r_conds)
    
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
        canvas = init_canvas(canvas)
        text_height = canvas.font.metrics("linespace")
        x_current = x+canvas.BUFFER #indent the left side
        y_current = y+canvas.BUFFER #indent the top
        
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
        canvas.create_text(x_current, y_current, anchor='nw', text=text)
        max_width = canvas.font.measure(text)
        y_current += text_height+canvas.BUFFER
        horiz_line_y = y_current
        y_current += canvas.BUFFER

        ######################################
        # Draw Conditions
        ######################################
        for cond in self.conds:
            if isinstance(cond, AbstractDRS) or isinstance(cond, ApplicationExpression):
                bottom_right_corner = cond.draw(x_current, y_current, canvas)
                max_width = max(max_width, bottom_right_corner[0]-x_current)
                y_current = bottom_right_corner[1]+canvas.BUFFER
            else:
                text = str(cond)
                canvas.create_text(x_current, y_current, anchor='nw', text=text)
                max_width = max(max_width, canvas.font.measure(text))
                y_current += text_height+canvas.BUFFER

        ######################################
        # Draw Box
        ######################################
        x_current = x+max_width+canvas.BUFFER*2
        if (y_current - horiz_line_y) < text_height:
            y_current += text_height
        canvas.create_rectangle(x, y, x_current, y_current)
        canvas.create_line(x, horiz_line_y, x_current, horiz_line_y)

        return (x_current, y_current)

    def get_drawing_size(self, canvas=None, use_parens=None): 
        canvas = init_canvas(canvas)
        text_height = canvas.font.metrics("linespace")
        x_current = canvas.BUFFER #indent the left side
        y_current = canvas.BUFFER #indent the top
        
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
        y_current += text_height+canvas.BUFFER
        horiz_line_y = y_current
        y_current += canvas.BUFFER

        ######################################
        # Draw Conditions
        ######################################
        for cond in self.conds:
            if isinstance(cond, AbstractDRS) or isinstance(cond, ApplicationExpression):
                size = cond.get_drawing_size(canvas)
                max_width = max(max_width, size[0])
                y_current += size[1]+canvas.BUFFER
            else:
                text = str(cond)
                max_width = max(max_width, canvas.font.measure(text))
                y_current += text_height+canvas.BUFFER

        ######################################
        # Draw Box
        ######################################
        x_current = max_width+canvas.BUFFER*2
        if (y_current - horiz_line_y) < text_height:
            y_current += text_height

        return (x_current, y_current)

class DRSVariable(AbstractDRS):
    """A Variable DRS which consists solely of a variable."""
    def __init__(self, variable):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        self.variable = variable

    def equals(self, other):
        if isinstance(self, DRSVariable) and \
           isinstance(other, DRSVariable):
            return self.variable.equals(other.variable)
        else:
            return False

    def variables(self):
        return set([self.variable])

    def free(self):
        return set([self.variable])

    def subterms(self):
        return set([self])

    def replace(self, variable, expression):
        if self.variable == variable:
            return expression
        else:
            return self
        
    def replace_with_side_effect(self, variable, expression):
        r_self = self.replace(variable, expression)
        self.variable = r_self.variable

    def get_refs(self):
        return []

    def simplify(self):
        return self

    def infixify(self):
        return self

    def name(self):
        return self.__str__()

    def _skolemise(self, bound_vars, counter):
        return self

    def __str__(self): return '%s' % self.variable

    def __repr__(self): return "DRSVariable('%s')" % self.variable

    def __hash__(self): return hash(repr(self))

    def draw(self, x=3, y=3, canvas=None, use_parens=None): #args define the top-left corner of the box
        canvas = init_canvas(canvas)
        text_height = canvas.font.metrics("linespace")

        canvas.create_text(x, y, anchor='nw', text=self.variable)
        return (x+canvas.font.measure(self.variable), y+text_height)
       
    def get_drawing_size(self, canvas=None, use_parens=None): #args define the top-left corner of the box
        canvas = init_canvas(canvas)
        text_height = canvas.font.metrics("linespace")

        return (canvas.font.measure(self.variable), text_height)
       

class LambdaDRS(AbstractDRS):
    """A lambda expression: \\x.M."""
    PREFIX = '\\'

    def __init__(self, variable, term):
        assert isinstance(variable, Variable)
        assert isinstance(term, AbstractDRS)
        self.variable = variable
        self.term = term
        self.prefix = self.__class__.PREFIX.rstrip()
        self.binder = (self.prefix, self.variable.name)
        self.body = str(self.term)

    def equals(self, other):
        r"""
        Defines equality modulo alphabetic variance.

        If we are comparing \x.M  and \y.N, then
        check equality of M and N[x/y].
        """
        if self.__class__ == other.__class__:
            if self.variable == other.variable:
                return self.term == other.term
            else:
                # Comparing \x.M  and \y.N.
                # Relabel y in N with x and continue.
                relabeled = self._relabel(other)
                return self.term == relabeled
        else:
            return False

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

    def replace(self, variable, expression):
        if self.variable == variable:
            return self
        if self.variable in expression.free():
            v = 'z' + str(DRS._counter.get())
            self = self.alpha_convert(Variable(v))
        return self.__class__(self.variable, \
                              self.term.replace(variable, expression))

    def replace_with_side_effect(self, variable, expression):
        r_self = self.replace(variable, expression)
        self.variable = r_self.variable
        self.term = r_self.term

    def alpha_convert(self, newvar):
        """
        Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        """
        term = self.term.replace(self.variable, VariableExpression(newvar))
        return self.__class__(newvar, term)

    def get_refs(self):
        raise NotImplementedError

    def simplify(self):
        return self.__class__(self.variable, self.term.simplify())

    def infixify(self):
        return self.__class__(self.variable, self.term.infixify())

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
        canvas = init_canvas(canvas)
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
        canvas.create_text(x, y+(bottom_right_corner[1]-y)/2, anchor='w', text=text)

        return bottom_right_corner

    def get_drawing_size(self, canvas=None, use_parens=None): #args define the top-left corner of the box
        canvas = init_canvas(canvas)
        text_height = canvas.font.metrics("linespace")
        
        text = '%s%s' % (self.__class__.PREFIX, self.variable)
        drs = self.term
        while isinstance(drs, LambdaDRS):
            text += ' %s' % self.variable
            drs = drs.term
        text += Tokens.DOT
        variables_width = canvas.font.measure(text)

        size = drs.get_drawing_size(canvas)
        return (size[0]+variables_width, size[1])

class DrsOperator(AbstractDRS):
    """
    A boolean operator, such as 'not' or 'and', or the equality
    relation ('=').
    """
    def __init__(self, operator):
        assert operator in Tokens.DRS_OPS
        self.constant = operator
        self.operator = operator

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.constant == other.constant
        else:
            return False

    def replace(self, variable, expression):
        return self

    def replace_with_side_effect(self, variable, expression):
        return self.replace(variable, expression)

    def free(self):
        return set()

    def get_refs(self):
        raise NotImplementedError

    def simplify(self):
        return self

    def infixify(self):
        return self

    def __str__(self): return '%s' % self.operator

    def __repr__(self): return "DrsOperator('%s')" % self.operator

    def draw(self, x=3, y=3, canvas=None, use_parens=None): #args define the top-left corner of the box
        canvas = init_canvas(canvas)
        text_height = canvas.font.metrics("linespace")

        canvas.create_text(x, y, anchor='nw', text=self.operator)
        return (x+canvas.font.measure(self.operator), y+text_height)
       
    def get_drawing_size(self, canvas=None, use_parens=None): #args define the top-left corner of the box
        canvas = init_canvas(canvas)
        return (canvas.font.measure(self.operator), canvas.font.metrics("linespace"))
       
class ApplicationDRS(AbstractDRS):
    """An application expression: (M N)."""
    def __init__(self, first, second):
        first_simp = first.simplify()
        assert isinstance(first, AbstractDRS)
        if not (isinstance(first_simp, LambdaDRS) or isinstance(first_simp, DRSVariable)) :
            assert isinstance(second, AbstractDRS)
        self.first = first
        self.second = second

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.first.equals(other.first) and \
                   self.second.equals(other.second)
        else:
            return False

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

    def replace(self, variable, expression):
        return self.__class__(self.first.replace(variable, expression),\
                              self.second.replace(variable, expression))

    def get_refs(self):
        first = self.first.simplify()
        if isinstance(first, DrsOperator) and first.operator == Tokens.DRS_CONC:
            second = self.second.simplify()
            refs = second.get_refs()
            return refs
        else:
            return []

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
        canvas = init_canvas(canvas)

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

        x_current = x

        if use_parens:
            #Draw Open Paren
            y_current = y+(max_height-canvas.font.metrics("linespace"))/2
            canvas.create_text(x_current, y_current, anchor='nw', text=Tokens.OPEN_PAREN)
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
            canvas.create_text(x_current, y_current, anchor='nw', text=text)
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
            canvas.create_text(x_current, y_current, anchor='nw', text=self.second)
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        x_current = second_bottom_right_corner[0]

        if use_parens:
            canvas.create_text(x_current, y+(max_height-canvas.font.metrics("linespace"))/2, anchor='nw', text=Tokens.CLOSE_PAREN)
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, y+max_height)

    def get_drawing_size(self, canvas=None, use_parens=True): #args define the top-left corner of the box
        canvas = init_canvas(canvas)

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
            canvas.create_text(x_current, y_current, anchor='nw', text=Tokens.OPEN_PAREN)
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
            second_bottom_right_corner = self.second.get_drawing_size(canvas)
        else:
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        if use_parens:
            x_current = second_bottom_right_corner[0]
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, max_height)

class ConcatinationDRS(ApplicationDRS):
    """DRS of the form '(DRS + DRS)'"""
    def __init__(self, first, second):
        first_simp = first.simplify()
        second_simp = second.simplify()
        assert (isinstance(first, ApplicationDRS) and isinstance(first_simp.first, DrsOperator) and first_simp.first.operator == Tokens.DRS_CONC and isinstance(second, AbstractDRS)) or \
               (isinstance(first, ApplicationDRS) and isinstance(first_simp.second, DrsOperator) and first_simp.second.operator == Tokens.DRS_CONC and isinstance(second, AbstractDRS))
        self.first = first
        self.second = second

    def replace(self, variable, expression):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        first  = self.first.replace(variable, expression)
        second = self.second.replace(variable, expression)
        for ref in self.get_refs(): # for every ref, across the whole concatination sequence
            if ref.variable in expression.free():
                v = VariableExpression(Variable('z' + str(DRS._counter.get()))) #get a new var name
                first  = first.replace(ref.variable, v)
                second = second.replace(ref.variable, v)
        return self.__class__(first, second)

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

    def __repr__(self): return "ConcatinationDRS('%s', '%s')" % (self.first, self.second)

    def draw(self, x=3, y=3, canvas=None, use_parens=True): #args define the top-left corner of the box
        canvas = init_canvas(canvas)

        first_size = self.first.get_drawing_size(canvas)
        second_size = self.second.get_drawing_size(canvas)

        max_height = max(first_size[1], second_size[1])

        x_current = x
        
        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        if use_parens:
            canvas.create_text(x_current, y+(first_size[1]-canvas.font.metrics("linespace"))/2, anchor='nw', text=Tokens.OPEN_PAREN)
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        first_bottom_right_corner = self.first.draw(x_current, y + (max_height - first_size[1])/2, canvas, first_use_parens)
        x_current = first_bottom_right_corner[0] + canvas.font.measure(' ')
        second_bottom_right_corner = self.second.draw(x_current, y + (max_height - second_size[1])/2, canvas)
        x_current = second_bottom_right_corner[0]

        if use_parens:
            canvas.create_text(x_current, y+(first_size[1]-canvas.font.metrics("linespace"))/2, anchor='nw', text=Tokens.CLOSE_PAREN)
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, max(first_bottom_right_corner[1], second_bottom_right_corner[1]))

    def get_drawing_size(self, canvas=None, use_parens=True):
        canvas = init_canvas(canvas)

        first_size = self.first.get_drawing_size(canvas)
        second_size = self.second.get_drawing_size(canvas)

        max_height = max(first_size[1], second_size[1])

        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        x_current = 0
        
        if (isinstance(self.first, ApplicationDRS) or isinstance(self.first, ApplicationExpression)) and \
           not isinstance(self.second, DrsOperator):
            first_use_parens = False
        else:
            first_use_parens = True

        if use_parens:
            x_current += canvas.font.measure(Tokens.OPEN_PAREN)

        first_size = self.first.get_drawing_size(canvas, first_use_parens)
        x_current += first_size[0] + canvas.font.measure(' ')
        second_size = self.second.get_drawing_size(canvas)
        x_current += second_size[0]

        if use_parens:
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, max(first_size[1], second_size[1]))

class ApplicationExpression(Expression):
    """An application expression: (M N)."""
    def __init__(self, first, second):
        Expression.__init__(self)
        assert isinstance(first, Expression)
        assert isinstance(second, Expression)
        self.first = first
        self.second = second

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.first.equals(other.first) and \
                   self.second.equals(other.second)
        else:
            return False

    def variables(self):
        return self.first.variables().union(self.second.variables())

    def free(self):
        return self.first.free().union(self.second.free())

    def _functor(self):
        if isinstance(self.first, ApplicationExpression):
            return self.first._functor()
        else:
            return self.first

    fun = property(_functor,
                   doc="Every ApplicationExpression has a functor.")


    def _operator(self):
        functor = self._functor()
        if isinstance(functor, DrsOperator):
            return str(functor)
        else: 
            raise AttributeError

    op = property(_operator,
                  doc="Only some ApplicationExpressions have operators." )

    def _arglist(self):
        """Uncurry the argument list."""
        arglist = [str(self.second)]
        if isinstance(self.first, ApplicationExpression):
            arglist.extend(self.first._arglist())
        return arglist

    def _args(self):
        arglist = self._arglist()
        arglist.reverse()
        return arglist

    args = property(_args,
                   doc="Every ApplicationExpression has args.")

    def subterms(self):
        first = self.first.subterms()

        second = self.second.subterms()
        return first.union(second).union(set([self]))

    def replace(self, variable, expression):
        return self.__class__(self.first.replace(variable, expression),\
                              self.second.replace(variable, expression))

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
        if (isinstance(first, DrsOperator) or isinstance(first, FolOperator)) and not str(first) == 'not':
            return self.__class__(second, first)
        else:
            return self.__class__(first, second)    

    def _skolemise(self, bound_vars, counter):
        first = self.first._skolemise(bound_vars, counter)
        second = self.second._skolemise(bound_vars, counter)
        return self.__class__(first, second)

    def __str__(self):
        # Print ((M N) P) as (M N P).
        strFirst = str(self.first)
        if isinstance(self.first, ApplicationExpression):
            if not isinstance(self.second, DrsOperator):
                strFirst = strFirst[1:-1]
        return '(%s %s)' % (strFirst, self.second)

    def __repr__(self): return "ApplicationExpression('%s', '%s')" % (self.first, self.second)

    def __hash__(self): return hash(repr(self))

    def draw(self, x=3, y=3, canvas=None, use_parens=True): #args define the top-left corner of the box
        canvas = init_canvas(canvas)

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

        x_current = x

        if use_parens:
            #Draw Open Paren
            y_current = y+(max_height-canvas.font.metrics("linespace"))/2
            canvas.create_text(x_current, y_current, anchor='nw', text=Tokens.OPEN_PAREN)
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
            canvas.create_text(x_current, y_current, anchor='nw', text=text)
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
            canvas.create_text(x_current, y_current, anchor='nw', text=self.second)
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        x_current = second_bottom_right_corner[0]

        if use_parens:
            canvas.create_text(x_current, y+(max_height-canvas.font.metrics("linespace"))/2, anchor='nw', text=Tokens.CLOSE_PAREN)
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, y+max_height)

    def get_drawing_size(self, canvas=None, use_parens=True): #args define the top-left corner of the box
        canvas = init_canvas(canvas)

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
            second_bottom_right_corner = self.second.get_drawing_size(canvas)
        else:
            second_bottom_right_corner = (x_current+canvas.font.measure(self.second), y_current+canvas.font.metrics("linespace"))

        if use_parens:
            x_current = second_bottom_right_corner[0]
            x_current += canvas.font.measure(Tokens.CLOSE_PAREN)

        return (x_current, max_height)

class Tokens:
    DRS = 'drs'
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
    FOL_OPS = ['=']
    
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
        self.buffer = self.buffer.replace(Tokens.DOT, ' %s ' % Tokens.DOT)
        self.buffer = self.buffer.replace(Tokens.COMMA, ' %s ' % Tokens.COMMA)
        self.buffer = self.buffer.replace(Tokens.OPEN_PAREN, ' %s ' % Tokens.OPEN_PAREN)
        self.buffer = self.buffer.replace(Tokens.CLOSE_PAREN, ' %s ' % Tokens.CLOSE_PAREN)
        self.buffer = self.buffer.replace(Tokens.OPEN_BRACKET, ' %s ' % Tokens.OPEN_BRACKET)
        self.buffer = self.buffer.replace(Tokens.CLOSE_BRACKET, ' %s ' % Tokens.CLOSE_BRACKET)

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

        elif is_indvar(tok):
            # Expression is a boolean operator or the equality symbol
            return IndVariableExpression(Variable(tok))
        
        else:
            if self.isVariable(tok):
                if tok[0].isupper():
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
        if (isinstance(first, ApplicationDRS) and isinstance(first_simp.first, DrsOperator) and first_simp.first.operator == Tokens.DRS_CONC and isinstance(second, AbstractDRS)) or \
           (isinstance(second, ApplicationDRS) and isinstance(second_simp.first, DrsOperator) and second_simp.first.operator == Tokens.DRS_CONC and isinstance(first, AbstractDRS)):
            return ConcatinationDRS(first, second)
        elif isinstance(first, DrsOperator) or isinstance(first, AbstractDRS):
            return ApplicationDRS(first, second)
        else:
            return ApplicationExpression(first, second)


    def __repr__(self):
        return 'Next token: \'%s\'' % self.token(0)

    def __str__(self):
        return self.__repr__()

def init_canvas(canvas=None):
    if not canvas:
        from Tkinter import *
        from tkFont import Font

        master = Tk()
        canvas = Canvas(master, width=900, height=600)
        canvas.pack()
        canvas.font = Font(font=canvas.itemcget(canvas.create_text(0, 0, text=''), 'font'))
        canvas.BUFFER = 3
    return canvas

def expression():
    return ['drs([],[])',
            'drs([x],[(man x), (walks x)])',
            'drs([x,y],[(sees x y)])',
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
            
            'drs([x],[(x = (alpha x)),(sees John x)])'
            ]

def demo(ex=-1, draw=False, catch_exception=True):
    exps = expression()
    for (i, exp) in zip(range(len(exps)),exps):
        if i==ex or ex==-1:
            if(not draw):
                print '[[[Example %s]]]: %s' % (i, exp)
                try:
                    print '  %s' % Parser().parse(exp).simplify().infixify()
                except Exception, (strerror):
                    if catch_exception:
                        print '  Error: %s' % strerror
                    else:
                        raise
                print ''
            else:
                canvas = init_canvas()
                y_current = canvas.BUFFER
                canvas.create_text(canvas.BUFFER, y_current, anchor='nw', text='Example %s: %s' % (i, exp))
                try:
                    y_current += canvas.font.metrics("linespace")+canvas.BUFFER
                    size = Parser().parse(exp).infixify().draw(canvas.BUFFER,y_current,canvas)
                    y_current += size[1]+canvas.BUFFER
                    Parser().parse(exp).simplify().infixify().draw(canvas.BUFFER, y_current, canvas)
                except Exception, (strerror):
                    if catch_exception:
                        canvas.create_text(canvas.BUFFER, y_current, anchor='nw', text='  Error: %s' % strerror)
                    else:
                        raise
                
if __name__ == '__main__':
    pt = Parser().parse('drs([x],[(x = (alpha x)),(sees John x)])')
    simp = pt.simplify()
    inf = simp.infixify()
    print inf
