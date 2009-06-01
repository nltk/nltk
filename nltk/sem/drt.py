# Natural Language Toolkit: Discourse Representation Theory (DRT) 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import operator

from logic import *
import drt_resolve_anaphora as RA

# Import Tkinter-based modules if they are available
try:
    from Tkinter import Canvas
    from Tkinter import Tk
    from tkFont import Font
    from nltk.util import in_idle

except ImportError:
    # No need to print a warning here, nltk.draw has already printed one.
    pass

class DrtTokens(Tokens):
    DRS = 'DRS'
    DRS_CONC = '+'
    PRONOUN = 'PRO'
    OPEN_BRACKET = '['
    CLOSE_BRACKET = ']'
    
    PUNCT = [DRS_CONC, OPEN_BRACKET, CLOSE_BRACKET]
    
    SYMBOLS = Tokens.SYMBOLS + PUNCT
    
    TOKENS = Tokens.TOKENS + [DRS] + PUNCT
    

class AbstractDrs(object):
    """
    This is the base abstract DRT Expression from which every DRT 
    Expression extends.
    """

    def applyto(self, other):
        return DrtApplicationExpression(self, other)
    
    def __neg__(self):
        return DrtNegatedExpression(self)
    
    def __and__(self, other):
        raise NotImplementedError()
    
    def __or__(self, other):
        assert isinstance(other, AbstractDrs)
        return DrtOrExpression(self, other)
    
    def __gt__(self, other):
        assert isinstance(other, AbstractDrs)
        return DrtImpExpression(self, other)
    
    def __lt__(self, other):
        assert isinstance(other, AbstractDrs)
        return DrtIffExpression(self, other)
    
    def tp_equals(self, other, prover=None):
        """
        Pass the expression (self <-> other) to the theorem prover.   
        If the prover says it is valid, then the self and other are equal.
        
        @param other: an C{AbstractDrs} to check equality against
        @param prover: a C{nltk.inference.api.Prover}
        """
        assert isinstance(other, AbstractDrs)
        
        f1 = self.simplify().fol();
        f2 = other.simplify().fol();
        return f1.tp_equals(f2, prover)
    
    def _get_type(self):
        raise AttributeError("'%s' object has no attribute 'type'" % 
                             self.__class__.__name__)
    type = property(_get_type)

    def typecheck(self, signature=None):
        raise NotImplementedError()
    
    def __add__(self, other):
        return ConcatenationDRS(self, other)
    
    def get_refs(self, recursive=False):
        """
        Return the set of discourse referents in this DRS.
        @param recursive: C{boolean} Also find discourse referents in subterms?
        @return: C{list} of C{Variable}s 
        """
        raise NotImplementedError()
    
    def is_pronoun_function(self):
        """ Is self of the form "PRO(x)"? """
        return isinstance(self, DrtApplicationExpression) and \
               isinstance(self.function, DrtAbstractVariableExpression) and \
               self.function.variable.name == DrtTokens.PRONOUN and \
               isinstance(self.argument, DrtIndividualVariableExpression)
    
    def make_EqualityExpression(self, first, second):
        return DrtEqualityExpression(first, second)

    def make_VariableExpression(self, variable):
        return DrtVariableExpression(variable)

    def draw(self):
        DrsDrawer(self).draw()
        

class DRS(AbstractDrs, Expression, RA.DRS):
    """A Discourse Representation Structure."""
    def __init__(self, refs, conds):
        """
        @param refs: C{list} of C{DrtIndividualVariableExpression} for the 
        discourse referents
        @param conds: C{list} of C{Expression} for the conditions
        """ 
        self.refs = refs
        self.conds = conds

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        try:
            #if a bound variable is the thing being replaced
            i = self.refs.index(variable)
            if not replace_bound:
                return self
            else: 
                return DRS(self.refs[:i]+[expression.variable]+self.refs[i+1:],
                           [cond.replace(variable, expression, True) for cond in self.conds])
        except ValueError:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.refs) & expression.free()):
                newvar = unique_variable(ref) 
                newvarex = DrtVariableExpression(newvar)
                i = self.refs.index(ref)
                self = DRS(self.refs[:i]+[newvar]+self.refs[i+1:],
                           [cond.replace(ref, newvarex, True) 
                            for cond in self.conds])
                
            #replace in the conditions
            return DRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds])

    def variables(self):
        """@see: Expression.variables()"""
        conds_vars = reduce(operator.or_, 
                            [c.variables() for c in self.conds], set())
        return conds_vars - set(self.refs)
    
    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        conds_free = reduce(operator.or_, 
                            [c.free(indvar_only) for c in self.conds], set())
        return conds_free - set(self.refs)

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            cond_refs = reduce(operator.add, 
                               [c.get_refs(True) for c in self.conds], [])
            return self.refs + cond_refs
        else:
            return self.refs
        
    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return reduce(combinator, 
                      [function(e) for e in self.refs + self.conds], default)
    
    def simplify(self):
        return DRS(self.refs, [cond.simplify() for cond in self.conds])
    
    def fol(self):
        if not self.conds:
            raise Exception("Cannot convert DRS with no conditions to FOL.")
        accum = reduce(AndExpression, [c.fol() for c in self.conds])
        for ref in self.refs[::-1]:
            accum = ExistsExpression(ref, accum)
        return accum
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(other, DRS):
            if len(self.refs) == len(other.refs):
                converted_other = other
                for (r1, r2) in zip(self.refs, converted_other.refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                return self.conds == converted_other.conds
        return False
    
    def str(self, syntax=DrtTokens.NLTK):
        if syntax == DrtTokens.PROVER9:
            return self.fol().str(syntax)
        else:
            return '([%s],[%s])' % (','.join([str(r) for r in self.refs]),
                                    ', '.join([c.str(syntax) for c in self.conds]))

def DrtVariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of 
    C{DrtAbstractVariableExpression} appropriate for the given variable.
    """
    if is_indvar(variable.name):
        return DrtIndividualVariableExpression(variable)
    elif is_funcvar(variable.name):
        return DrtFunctionVariableExpression(variable)
    elif is_eventvar(variable.name):
        return DrtEventVariableExpression(variable)
    else:
        return DrtConstantExpression(variable)
    

class DrtAbstractVariableExpression(AbstractDrs, 
                                    AbstractVariableExpression, 
                                    RA.AbstractVariableExpression):
    def fol(self):
        return self
    
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []
    
class DrtIndividualVariableExpression(DrtAbstractVariableExpression, 
                                      IndividualVariableExpression, 
                                      RA.AbstractVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, 
                                    FunctionVariableExpression, 
                                    RA.AbstractVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, 
                                 EventVariableExpression, 
                                 RA.AbstractVariableExpression):
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, 
                            ConstantExpression, 
                            RA.AbstractVariableExpression):
    pass

class DrtNegatedExpression(AbstractDrs, NegatedExpression, 
                           RA.NegatedExpression):
    def fol(self):
        return NegatedExpression(self.term.fol())

class DrtLambdaExpression(AbstractDrs, LambdaExpression, 
                          RA.LambdaExpression):
    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        @param newvar: C{Variable}, for the new variable
        """
        return self.__class__(newvar, self.term.replace(self.variable, 
                          DrtVariableExpression(newvar), True))

    def fol(self):
        return LambdaExpression(self.variable, self.term.fol())

class DrtBooleanExpression(AbstractDrs, BooleanExpression):
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.first.get_refs(True) + self.second.get_refs(True)
        else:
            return []

class DrtOrExpression(DrtBooleanExpression, OrExpression, RA.OrExpression):
    def fol(self):
        return OrExpression(self.first.fol(), self.second.fol())

class DrtImpExpression(DrtBooleanExpression, ImpExpression, RA.ImpExpression):
    def fol(self):
        first_drs = self.first
        second_drs = self.second

        accum = None
        if first_drs.conds:
            accum = reduce(AndExpression, 
                           [c.fol() for c in first_drs.conds])
   
        if accum:
            accum = ImpExpression(accum, second_drs.fol())
        else:
            accum = second_drs.fol()
    
        for ref in first_drs.refs[::-1]:
            accum = AllExpression(ref, accum)
            
        return accum

class DrtIffExpression(DrtBooleanExpression, IffExpression, 
                       RA.IffExpression):
    def fol(self):
        return IffExpression(self.first.fol(), self.second.fol())

class DrtEqualityExpression(AbstractDrs, EqualityExpression, 
                            RA.EqualityExpression):
    def fol(self):
        return EqualityExpression(self.first.fol(), self.second.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.first.get_refs(True) + self.second.get_refs(True)
        else:
            return []

class ConcatenationDRS(DrtBooleanExpression, RA.ConcatenationDRS):
    """DRS of the form '(DRS + DRS)'"""
    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        first = self.first
        second = self.second

        # If variable is bound by both first and second 
        if isinstance(first, DRS) and isinstance(second, DRS) and \
           variable in (set(first.get_refs(True)) & set(second.get_refs(True))):
            first  = first.replace(variable, expression, True)
            second = second.replace(variable, expression, True)
            
        # If variable is bound by first
        elif isinstance(first, DRS) and variable in first.refs:
            if replace_bound: 
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        # If variable is bound by second
        elif isinstance(second, DRS) and variable in second.refs:
            if replace_bound:
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        else:
            # alpha convert every ref that is free in 'expression'
            for ref in (set(self.get_refs(True)) & expression.free()): 
                v = DrtVariableExpression(unique_variable(ref))
                first  = first.replace(ref, v, True)
                second = second.replace(ref, v, True)

            first  = first.replace(variable, expression, replace_bound)
            second = second.replace(variable, expression, replace_bound)
            
        return self.__class__(first, second)
    
    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()

        if isinstance(first, DRS) and isinstance(second, DRS):
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)
            
            return DRS(first.refs + second.refs, first.conds + second.conds)
        else:
            return self.__class__(first,second)
        
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return self.first.get_refs(recursive) + self.second.get_refs(recursive)

    def getOp(self, syntax=DrtTokens.NLTK):
        return DrtTokens.DRS_CONC
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(other, ConcatenationDRS):
            self_refs = self.get_refs()
            other_refs = other.get_refs()
            if len(self_refs) == len(other_refs):
                converted_other = other
                for (r1,r2) in zip(self_refs, other_refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                return self.first == converted_other.first and \
                        self.second == converted_other.second
        return False
        
    def fol(self):
        return AndExpression(self.first.fol(), self.second.fol())

class DrtApplicationExpression(AbstractDrs, ApplicationExpression, 
                               RA.ApplicationExpression):
    def fol(self):
        return ApplicationExpression(self.function.fol(), 
                                           self.argument.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.function.get_refs(True) + self.argument.get_refs(True)
        else:
            return []

class DrsDrawer(object):
    BUFFER = 3     #Space between elements
    TOPSPACE = 10  #Space above whole DRS
    OUTERSPACE = 6 #Space to the left, right, and bottom of the whle DRS
    
    def __init__(self, drs, size_canvas=True, canvas=None):
        """
        @param drs: C{AbstractDrs}, The DRS to be drawn
        @param size_canvas: C{boolean}, True if the canvas size should be the exact size of the DRS
        @param canvas: C{Canvas} The canvas on which to draw the DRS.  If none is given, create a new canvas. 
        """
        self.syntax = DrtTokens.NLTK

        master = None
        if not canvas:
            master = Tk()
            master.title("DRT")
    
            font = Font(family='helvetica', size=12)
            
            if size_canvas:
                canvas = Canvas(master, width=0, height=0)
                canvas.font = font
                self.canvas = canvas
                (right, bottom) = self._visit(drs, self.OUTERSPACE, self.TOPSPACE)
                
                width = max(right+self.OUTERSPACE, 100)
                height = bottom+self.OUTERSPACE
                canvas = Canvas(master, width=width, height=height)#, bg='white')
            else:
                canvas = Canvas(master, width=300, height=300)
                
            canvas.pack()
            canvas.font = font

        self.canvas = canvas
        self.drs = drs
        self.master = master
        
    def _get_text_height(self):
        """Get the height of a line of text"""
        return self.canvas.font.metrics("linespace")
        
    def draw(self, x=OUTERSPACE, y=TOPSPACE):
        """Draw the DRS"""
        self._handle(self.drs, self._draw_command, x, y)

        if self.master and not in_idle():
            self.master.mainloop()
        else:
            return self._visit(self.drs, x, y)
        
    def _visit(self, expression, x, y):
        """
        Return the bottom-rightmost point without actually drawing the item
        
        @param expression: the item to visit
        @param x: the top of the current drawing area
        @param y: the left side of the current drawing area
        @return: the bottom-rightmost point
        """
        return self._handle(expression, self._visit_command, x, y)

    def _draw_command(self, item, x, y):
        """
        Draw the given item at the given location
        
        @param item: the item to draw
        @param x: the top of the current drawing area
        @param y: the left side of the current drawing area
        @return: the bottom-rightmost point 
        """
        if isinstance(item, str):
            self.canvas.create_text(x, y, anchor='nw', font=self.canvas.font, text=item)
        elif isinstance(item, tuple):
            # item is the lower-right of a box
            (right, bottom) = item
            self.canvas.create_rectangle(x, y, right, bottom)
            horiz_line_y = y + self._get_text_height() + (self.BUFFER * 2) #the line separating refs from conds
            self.canvas.create_line(x, horiz_line_y, right, horiz_line_y)
            
        return self._visit_command(item, x, y)
        
    def _visit_command(self, item, x, y):
        """
        Return the bottom-rightmost point without actually drawing the item
        
        @param item: the item to visit
        @param x: the top of the current drawing area
        @param y: the left side of the current drawing area
        @return: the bottom-rightmost point
        """
        if isinstance(item, str):
            return (x + self.canvas.font.measure(item), y + self._get_text_height())
        elif isinstance(item, tuple):
            return item
    
    def _handle(self, expression, command, x=0, y=0):
        """
        @param expression: the expression to handle
        @param command: the function to apply, either _draw_command or _visit_command
        @param x: the top of the current drawing area
        @param y: the left side of the current drawing area
        @return: the bottom-rightmost point
        """
        if command == self._visit_command:
            #if we don't need to draw the item, then we can use the cached values
            try:
                #attempt to retrieve cached values
                right = expression._drawing_width + x
                bottom = expression._drawing_height + y
                return (right, bottom)
            except AttributeError:
                #the values have not been cached yet, so compute them
                pass
        
        if isinstance(expression, DrtAbstractVariableExpression):
            factory = self._handle_VariableExpression
        elif isinstance(expression, DRS):
            factory = self._handle_DRS
        elif isinstance(expression, DrtNegatedExpression):
            factory = self._handle_NegatedExpression
        elif isinstance(expression, DrtLambdaExpression):
            factory = self._handle_LambdaExpression
        elif isinstance(expression, BinaryExpression):
            factory = self._handle_BinaryExpression
        elif isinstance(expression, DrtApplicationExpression):
            factory = self._handle_ApplicationExpression
        elif isinstance(expression, RA.PossibleAntecedents):
            factory = self._handle_VariableExpression
        else:
            raise Exception, expression.__class__.__name__
            
        (right, bottom) = factory(expression, command, x, y)
        
        #cache the values
        expression._drawing_width = right - x
        expression._drawing_height = bottom - y
            
        return (right, bottom)

    def _handle_VariableExpression(self, expression, command, x, y):
        return command(expression.str(self.syntax), x, y)
       
    def _handle_NegatedExpression(self, expression, command, x, y):
        # Find the width of the negation symbol
        right = self._visit_command(DrtTokens.NOT[self.syntax], x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        # Handle variables now that we know the y-coordinate
        command(DrtTokens.NOT[self.syntax], x, self._get_centered_top(y, bottom - y, self._get_text_height()))

        return (right, bottom)
       
    def _handle_DRS(self, expression, command, x, y): 
        left = x + self.BUFFER #indent the left side
        bottom = y + self.BUFFER #indent the top
        
        # Handle Discourse Referents
        if expression.refs:
            refs = ' '.join([str(ref) for ref in expression.refs])
        else:
            refs = '     '
        (max_right, bottom) = command(refs, left, bottom)
        bottom += (self.BUFFER * 2)

        # Handle Conditions
        if expression.conds:
            for cond in expression.conds:
                (right, bottom) = self._handle(cond, command, left, bottom)
                max_right = max(max_right, right)
                bottom += self.BUFFER
        else:
            bottom += self._get_text_height() + self.BUFFER

        # Handle Box
        max_right += self.BUFFER
        return command((max_right, bottom), x, y)

    def _handle_ApplicationExpression(self, expression, command, x, y):
        function, args = expression.uncurry()
        if not isinstance(function, DrtAbstractVariableExpression):
            #It's not a predicate expression ("P(x,y)"), so leave arguments curried
            function = expression.function
            args = [expression.argument]
        
        # Get the max bottom of any element on the line
        function_bottom = self._visit(function, x, y)[1]
        max_bottom = max([function_bottom] + [self._visit(arg, x, y)[1] for arg in args])
            
        line_height = max_bottom - y
            
        # Handle 'function'
        function_drawing_top = self._get_centered_top(y, line_height, function._drawing_height)
        right = self._handle(function, command, x, function_drawing_top)[0]
        
        # Handle open paren
        centred_string_top = self._get_centered_top(y, line_height, self._get_text_height())
        right = command(DrtTokens.OPEN, right, centred_string_top)[0]
        
        # Handle each arg
        for (i,arg) in enumerate(args):
            arg_drawing_top = self._get_centered_top(y, line_height, arg._drawing_height)
            right = self._handle(arg, command, right, arg_drawing_top)[0]
            
            if i+1 < len(args):
                #since it's not the last arg, add a comma
                right = command(DrtTokens.COMMA + ' ', right, centred_string_top)[0]
        
        # Handle close paren
        right = command(DrtTokens.CLOSE, right, centred_string_top)[0]
        
        return (right, max_bottom)

    def _handle_LambdaExpression(self, expression, command, x, y):
        # Find the width of the lambda symbol and abstracted variables
        variables = DrtTokens.LAMBDA[self.syntax] + str(expression.variable) + DrtTokens.DOT[self.syntax]
        right = self._visit_command(variables, x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        # Handle variables now that we know the y-coordinate
        command(variables, x, self._get_centered_top(y, bottom - y, self._get_text_height()))

        return (right, bottom)

    def _handle_BinaryExpression(self, expression, command, x, y):
        # Get the full height of the line, based on the operands
        first_height = self._visit(expression.first, 0, 0)[1]
        second_height = self._visit(expression.second, 0, 0)[1]
        line_height = max(first_height, second_height)
        
        # Handle open paren
        centred_string_top = self._get_centered_top(y, line_height, self._get_text_height())
        right = command(DrtTokens.OPEN, x, centred_string_top)[0]
        
        # Handle the first operand
        first_height = expression.first._drawing_height
        (right, first_bottom) = self._handle(expression.first, command, right, self._get_centered_top(y, line_height, first_height))

        # Handle the operator
        right = command(' %s ' % expression.getOp(self.syntax), right, centred_string_top)[0]
        
        # Handle the second operand
        second_height = expression.second._drawing_height
        (right, second_bottom) = self._handle(expression.second, command, right, self._get_centered_top(y, line_height, second_height))
        
        # Handle close paren
        right = command(DrtTokens.CLOSE, right, centred_string_top)[0]
        
        return (right, max(first_bottom, second_bottom))

    def _get_centered_top(self, top, full_height, item_height):
        """Get the y-coordinate of the point that a figure should start at if
        its height is 'item_height' and it needs to be centered in an area that
        starts at 'top' and is 'full_height' tall."""
        return top + (full_height - item_height) / 2


class DrtParser(LogicParser):
    """A lambda calculus expression parser."""
    def __init__(self):
        LogicParser.__init__(self)
    
    def get_all_symbols(self):
        """This method exists to be overridden"""
        return DrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in DrtTokens.TOKENS

    def handle(self, tok):
        """This method is intended to be overridden for logics that 
        use different operators or expressions"""
        if tok in DrtTokens.NOT:
            return self.handle_negation()
        
        elif tok in DrtTokens.LAMBDA:
            return self.handle_lambda(tok)
            
        elif tok == DrtTokens.OPEN:
            if self.token(0) == DrtTokens.OPEN_BRACKET:
                return self.handle_DRS()
            else:
                return self.handle_open(tok)
        
        elif tok.upper() == DrtTokens.DRS:
            self.assertToken(self.token(), DrtTokens.OPEN)
            return self.handle_DRS()

        elif self.isvariable(tok):
            return self.handle_variable(tok)

    def make_NegatedExpression(self, expression):
        return DrtNegatedExpression(expression)
        
    def handle_DRS(self):
        # a DRS
        self.assertToken(self.token(), DrtTokens.OPEN_BRACKET)
        refs = []
        while self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x,y],C)
            if self.token(0) == DrtTokens.COMMA:
                self.token() # swallow the comma
            else:
                refs.append(Variable(self.token()))
        self.token() # swallow the CLOSE_BRACKET token
        
        if self.token(0) == DrtTokens.COMMA: #if there is a comma (it's optional)
            self.token() # swallow the comma
            
        self.assertToken(self.token(), DrtTokens.OPEN_BRACKET)
        conds = []
        while self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x, y],C)
            if self.token(0) == DrtTokens.COMMA:
                self.token() # swallow the comma
            else:
                conds.append(self.parse_Expression())
        self.token() # swallow the CLOSE_BRACKET token
        self.assertToken(self.token(), DrtTokens.CLOSE)
         
        return DRS(refs, conds)

    def make_EqualityExpression(self, first, second):
        """This method serves as a hook for other logic parsers that
        have different equality expression classes"""
        return DrtEqualityExpression(first, second)

    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        if tok == DrtTokens.DRS_CONC:
            return ConcatenationDRS
        elif tok in DrtTokens.OR:
            return DrtOrExpression
        elif tok in DrtTokens.IMP:
            return DrtImpExpression
        elif tok in DrtTokens.IFF:
            return DrtIffExpression
        else:
            return None

    def make_BooleanExpression(self, factory, first, second):
        return factory(first, second)
    
    def make_ApplicationExpression(self, function, argument):
        return DrtApplicationExpression(function, argument)
    
    def make_VariableExpression(self, name):
        return DrtVariableExpression(Variable(name))
    
    def make_LambdaExpression(self, variables, term):
        return DrtLambdaExpression(variables, term)

    
def demo():
    print '='*20 + 'TEST PARSE' + '='*20
    parser = DrtParser()
    print parser.parse(r'([x,y],[sees(x,y)])')
    print parser.parse(r'([x],[man(x), walks(x)])')
    print parser.parse(r'\x.\y.([],[sees(x,y)])')
    print parser.parse(r'\x.([],[walks(x)])(john)')
    print parser.parse(r'(([x],[walks(x)]) + ([y],[runs(y)]))')
    print parser.parse(r'(([],[walks(x)]) -> ([],[runs(x)]))')
    print parser.parse(r'([x],[PRO(x), sees(John,x)])')
    print parser.parse(r'([x],[man(x), -([],[walks(x)])])')
    print parser.parse(r'([],[(([x],[man(x)]) -> ([],[walks(x)]))])')

    print '='*20 + 'Test fol()' + '='*20
    print parser.parse(r'([x,y],[sees(x,y)])').fol()

    print '='*20 + 'Test alpha conversion and lambda expression equality' + '='*20
    e1 = parser.parse(r'\x.([],[P(x)])')
    print e1
    e2 = e1.alpha_convert(Variable('z'))
    print e2
    print e1 == e2

    print '='*20 + 'Test resolve_anaphora()' + '='*20
    print parser.parse(r'([x,y,z],[dog(x), cat(y), walks(z), PRO(z)])').resolve_anaphora()
    print parser.parse(r'([],[(([x],[dog(x)]) -> ([y],[walks(y), PRO(y)]))])').resolve_anaphora()
    print parser.parse(r'(([x,y],[]) + ([],[PRO(x)]))').resolve_anaphora()

        
def test_draw():
    expressions = [
            r'x',
            r'([],[])',
            r'([x],[])',
            r'([x],[man(x)])',

            r'([x,y],[sees(x,y)])',
            r'([x],[man(x), walks(x)])',
            r'\x.([],[man(x), walks(x)])',
            r'\x y.([],[sees(x,y)])',
            r'([],[(([],[walks(x)]) + ([],[runs(x)]))])',
            
            r'([x],[man(x), -([],[walks(x)])])',
            r'([],[(([x],[man(x)]) -> ([],[walks(x)]))])'
            ]
    
    for e in expressions:
        d = DrtParser().parse(e)
        d.draw()

if __name__ == '__main__':
    demo()
