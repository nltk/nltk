# Natural Language Toolkit: Discourse Representation Theory (DRT) 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.internals import Counter
from nltk.sem import logic
import drt_resolve_anaphora as RA

from Tkinter import Canvas
from Tkinter import Tk
from tkFont import Font
from nltk.draw import in_idle

class AbstractDrs:
    def __call__(self, other, *additional):
        accum = self.applyto(other)
        for a in additional:
            accum = accum.applyto(a)
        return accum
    
    def applyto(self, other):
        if not isinstance(other, list):
            other = [other]
        return DrtApplicationExpression(self, other)
    
    def __neg__(self):
        return DrtNegatedExpression(self)
    
    def negate(self):
        return -self
    
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
    
    def tp_equals(self, other, prover_name='tableau'):
        """Pass the expression (self <-> other) to the theorem prover.   
        If the prover says it is valid, then the self and other are equal."""
        assert isinstance(other, AbstractDrs)
        
        from nltk.inference import inference
        f1 = self.simplify().toFol();
        f2 = other.simplify().toFol();
        return f1.tp_equals(f2, prover_name)

    def __add__(self, other):
        return ConcatenationDRS(self, other)
    
    def get_pronoun_token(self):
        return Tokens.PRONOUN
    
    def get_EqualityExpression(self):
        return DrtEqualityExpression

    def unique_variable(self):
        return DrtIndividualVariableExpression('z' + str(logic._counter.get()))

    def draw(self):
        DrsDrawer(self).draw()

class DRS(AbstractDrs, logic.Expression, RA.DRS):
    """A Discourse Representation Structure."""
    def __init__(self, refs, conds):
        """
        @param refs: C{list} of C{DrtVariableExpression} for the discourse referents
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
                return DRS(self.refs[:i]+[expression]+self.refs[i+1:],
                           [cond.replace(variable, expression, True) for cond in self.conds])
        except ValueError:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.refs) & expression.free()):
                newvar = self.unique_variable()
                i = self.refs.index(ref)
                self = DRS(self.refs[:i]+[newvar]+self.refs[i+1:],
                           [cond.replace(ref, newvar, True) for cond in self.conds])
                
            #replace in the conditions
            return DRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds])

    def free(self):
        conds_free = set()
        for cond in self.conds:
            conds_free |= cond.free()
        refs_set = set(self.refs)
        return conds_free - refs_set

    def get_refs(self):
        return self.refs
    
    def simplify(self):
        r_refs = [ref.simplify() for ref in self.refs]
        r_conds = [cond.simplify() for cond in self.conds]
        return DRS(r_refs, r_conds)
    
    def toFol(self):
        accum = self.conds[-1].toFol()
        for cond in self.conds[::-1][1:]:
            accum = logic.AndExpression(cond.toFol(), accum) 
        for ref in self.refs[::-1]:
            accum = logic.ExistsExpression(ref, accum)
        return accum
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if self.__class__ == other.__class__:
            if len(self.refs) == len(other.refs):
                converted_other = other
                for (i,ref) in enumerate(self.refs):
                    other_ref = converted_other.refs[i]
                    converted_other = converted_other.replace(other_ref, ref, True)
                return self.conds == converted_other.conds
        return False
    
    def __str__(self):
        return Tokens.DRS + '([' + ','.join([str(ref) for ref in self.refs]) + \
               '],[' + ', '.join([str(cond) for cond in self.conds]) + '])'

class DrtVariableExpression(AbstractDrs, logic.VariableExpression, 
                            RA.VariableExpression):
    def toFol(self):
        return self
    
    def get_refs(self):
        return []

class DrtIndividualVariableExpression(DrtVariableExpression, 
                                      logic.IndividualVariableExpression, 
                                      RA.VariableExpression):
    def toFol(self):
        return self
    
    def get_refs(self):
        return []

class DrtNegatedExpression(AbstractDrs, logic.NegatedExpression, RA.NegatedExpression):
    def toFol(self):
        return logic.NegatedExpression(self.term.toFol())

class DrtLambdaExpression(AbstractDrs, logic.LambdaExpression, RA.LambdaExpression):
    def toFol(self):
        return logic.LambdaExpression(self.variable, self.term.toFol())

class DrtOrExpression(AbstractDrs, logic.ImpExpression):
    def toFol(self):
        return logic.OrExpression(self.first.toFol(), self.second.toFol())

class DrtImpExpression(AbstractDrs, logic.ImpExpression, RA.ImpExpression):
    def get_refs(self):
        return []

    def toFol(self):
        first_drs = self.first
        second_drs = self.second

        accum = first_drs.conds[-1].toFol()
        for cond in first_drs.conds[::-1][1:]:
            accum = logic.AndExpression(cond.toFol(), accum) 
   
        accum = logic.ImpExpression(accum, second_drs.toFol())
    
        for ref in first_drs.refs[::-1]:
            accum = logic.AllExpression(ref, accum)
            
        return accum

class DrtIffExpression(AbstractDrs, logic.IffExpression, RA.IffExpression):
    def toFol(self):
        return logic.IffExpression(self.first.toFol(), self.second.toFol())

class DrtEqualityExpression(AbstractDrs, logic.EqualityExpression, RA.EqualityExpression):
    def toFol(self):
        return logic.EqualityExpression(self.first.toFol(), self.second.toFol())

class ConcatenationDRS(AbstractDrs, logic.BooleanExpression, RA.ConcatenationDRS):
    """DRS of the form '(DRS + DRS)'"""
    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        first = self.first
        second = self.second

        # If variable is bound by both first and second 
        if isinstance(first, DRS) and isinstance(second, DRS) and \
           variable in (set(first.get_refs()) & set(second.get_refs())):
            first  = first.replace(variable, expression, True)
            second = second.replace(variable, expression, True)
            
        # If variable is bound by first
        elif isinstance(first, DRS) and variable in first.refs:
            if replace_bound: 
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        # If variable is boudn by second
        elif isinstance(second, DRS) and variable in second.refs:
            if replace_bound:
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        else:
            # alpha convert every ref that is free in 'expression'
            for ref in (set(self.get_refs()) & expression.free()): 
                v = self.unique_variable()
                first  = first.replace(ref, v, True)
                second = second.replace(ref, v, True)

            first  = first.replace(variable, expression, replace_bound)
            second = second.replace(variable, expression, replace_bound)
            
        return self.__class__(first, second)
    
    def get_refs(self):
        return self.first.get_refs() + self.second.get_refs()
            
    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()

        if isinstance(first, DRS) and isinstance(second, DRS):
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.refs) & set(second.refs)):
                # alpha convert the ref in 'second' to prevent collision
                second = second.replace(ref, self.unique_variable(), True)
            
            return DRS(first.refs + second.refs, first.conds + second.conds)
        else:
            return self.__class__(first,second)
        
    def getOp(self):
        return Tokens.DRS_CONC
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if self.__class__ == other.__class__:
            self_refs = self.get_refs()
            other_refs = other.get_refs()
            if len(self_refs) == len(other_refs):
                converted_other = other
                for (i,ref) in enumerate(self_refs):
                    other_ref = other_refs[i]
                    converted_other = converted_other.replace(other_ref, ref, True)
                return self.first == converted_other.first and \
                        self.second == converted_other.second
        return False
        
    def toFol(self):
        return logic.AndExpression(self.first.toFol(), self.second.toFol())

class DrtApplicationExpression(AbstractDrs, logic.ApplicationExpression, RA.ApplicationExpression):
    def toFol(self):
        return logic.ApplicationExpression(self.function.toFol(), 
                                           [arg.toFol() for arg in self.args])

    def get_refs(self):
        return []

    def __str__(self):
        function = str(self.function)

        if isinstance(self.function, DrtLambdaExpression):
            if isinstance(self.function.term, DrtApplicationExpression):
                if not isinstance(self.function.term.function, DrtVariableExpression):
                    function = Tokens.OPEN + function + Tokens.CLOSE
            elif not isinstance(self.function.term, logic.BooleanExpression) and \
                 not isinstance(self.function.term, DRS):
                function = Tokens.OPEN + function + Tokens.CLOSE
                
        return function + Tokens.OPEN + \
               ','.join([str(arg) for arg in self.args]) + Tokens.CLOSE


class DrsDrawer:
    BUFFER = 3
    
    def __init__(self, drs, size_canvas=True, canvas=None):
        """
        @param drs: C{AbstractDrs}, The DRS to be drawn
        @param size_canvas: C{boolean}, True if the canvas size should be the exact size of the DRS
        @param canvas: C{Canvas} The canvas on which to draw the DRS.  If none is given, create a new canvas. 
        """
        master = None
        if not canvas:
            master = Tk()
            master.title("DRT")
    
            font = Font(family='helvetica', size=12)
            
            if size_canvas:
                canvas = Canvas(master, width=0, height=0)
                canvas.font = font
                self.canvas = canvas
                (right, bottom) = self._visit(drs, self.BUFFER, self.BUFFER)
                canvas = Canvas(master, width=max(right, 100), height=bottom)#, bg='white')
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
        
    def draw(self, x=BUFFER, y=BUFFER):
        """Draw the DRS"""
        self._handle(self.drs, self._draw_command, x, y)

        if self.master and not in_idle():
            self.master.mainloop()
        else:
            return self._visit(self.drs, x, y)
        
    def _visit(self, expression, x, y):
        """
        Return the bottom-rightmost point without actually drawing the item
        
        @param item: the item to visit
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
        
        if isinstance(expression, DrtVariableExpression):
            factory = self._handle_VariableExpression
        elif isinstance(expression, DRS):
            factory = self._handle_DRS
        elif isinstance(expression, DrtNegatedExpression):
            factory = self._handle_NegatedExpression
        elif isinstance(expression, DrtLambdaExpression):
            factory = self._handle_LambdaExpression
        elif isinstance(expression, logic.BooleanExpression):
            factory = self._handle_BooleanExpression
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
        return command(str(expression), x, y)
       
    def _handle_NegatedExpression(self, expression, command, x, y):
        # Find the width of the negation symbol
        right = self._visit_command(Tokens.NOT[logic.n], x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        # Handle variables now that we know the y-coordinate
        command(Tokens.NOT[logic.n], x, self._get_centered_top(y, bottom - y, self._get_text_height()))

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
        # Get the max bottom of any element on the line
        function_bottom = self._visit(expression.function, x, y)[1]
        max_bottom = max([function_bottom] + [self._visit(arg, x, y)[1] for arg in expression.args])
            
        line_height = max_bottom - y
            
        # Handle 'function'
        function_drawing_top = self._get_centered_top(y, line_height, expression.function._drawing_height)
        right = self._handle(expression.function, command, x, function_drawing_top)[0]
        
        # Handle open paren
        centred_string_top = self._get_centered_top(y, line_height, self._get_text_height())
        right = command(Tokens.OPEN, right, centred_string_top)[0]
        
        # Handle each arg
        for (i,arg) in enumerate(expression.args):
            arg_drawing_top = self._get_centered_top(y, line_height, arg._drawing_height)
            right = self._handle(arg, command, right, arg_drawing_top)[0]
            
            if i+1 < len(expression.args):
                #since it's not the last arg, add a comma
                right = command(Tokens.COMMA + ' ', right, centred_string_top)[0]
        
        # Handle close paren
        right = command(Tokens.CLOSE, right, centred_string_top)[0]
        
        return (right, max_bottom)

    def _handle_LambdaExpression(self, expression, command, x, y):
        # Find the width of the lambda symbol and abstracted variables
        variables = Tokens.LAMBDA[logic.n] + str(expression.variable) + Tokens.DOT[logic.n]
        right = self._visit_command(variables, x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        # Handle variables now that we know the y-coordinate
        command(variables, x, self._get_centered_top(y, bottom - y, self._get_text_height()))

        return (right, bottom)

    def _handle_BooleanExpression(self, expression, command, x, y):
        # Get the full height of the line, based on the operands
        first_height = self._visit(expression.first, 0, 0)[1]
        second_height = self._visit(expression.second, 0, 0)[1]
        line_height = max(first_height, second_height)
        
        # Handle open paren
        centred_string_top = self._get_centered_top(y, line_height, self._get_text_height())
        right = command(Tokens.OPEN, x, centred_string_top)[0]
        
        # Handle the first operand
        first_height = expression.first._drawing_height
        (right, first_bottom) = self._handle(expression.first, command, right, self._get_centered_top(y, line_height, first_height))

        # Handle the operator
        right = command(' %s ' % expression.getOp(), right, centred_string_top)[0]
        
        # Handle the second operand
        second_height = expression.second._drawing_height
        (right, second_bottom) = self._handle(expression.second, command, right, self._get_centered_top(y, line_height, second_height))
        
        # Handle close paren
        right = command(Tokens.CLOSE, right, centred_string_top)[0]
        
        return (right, max(first_bottom, second_bottom))

    def _get_centered_top(self, top, full_height, item_height):
        """Get the y-coordinate of the point that a figure should start at if
        its height is 'item_height' and it needs to be centered in an area that
        starts at 'top' and is 'full_height' tall."""
        return top + (full_height - item_height) / 2


class Tokens(logic.Tokens):
    DRS = 'DRS'
    DRS_CONC = '+'
    PRONOUN = 'PRO'
    OPEN_BRACKET = '['
    CLOSE_BRACKET = ']'
    
    PUNCT = [DRS_CONC, OPEN_BRACKET, CLOSE_BRACKET]
    
    SYMBOLS = logic.Tokens.SYMBOLS + PUNCT
    
    TOKENS = logic.Tokens.TOKENS + [DRS] + PUNCT
    
class DrtParser(logic.LogicParser):
    """A lambda calculus expression parser."""
    
    def __init__(self):
        logic.LogicParser.__init__(self)

    def get_all_symbols(self):
        """This method exists to be overridden"""
        return Tokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in Tokens.TOKENS

    def handle(self, tok):
        """This method is intended to be overridden for logics that 
        use different operators or expressions"""
        if tok in Tokens.NOT:
            return self.handle_negation()
        
        elif tok in Tokens.LAMBDA:
            return self.handle_lambda(tok)
            
        elif tok == Tokens.OPEN:
            return self.handle_open(tok)
        
        elif tok.upper() == Tokens.DRS:
            return self.handle_DRS()

        elif self.isvariable(tok):
            return self.handle_variable(tok)

    def make_NegatedExpression(self, expression):
        return DrtNegatedExpression(expression)
        
    def handle_DRS(self):
        # a DRS
        self.assertToken(self.token(), Tokens.OPEN)
        self.assertToken(self.token(), Tokens.OPEN_BRACKET)
        refs = []
        while self.token(0) != Tokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x,y],C)
            if self.token(0) == Tokens.COMMA:
                self.token() # swallow the comma
            else:
                refs.append(self.make_VariableExpression(self.token()))
        self.token() # swallow the CLOSE_BRACKET token
        self.assertToken(self.token(), Tokens.COMMA)
        self.assertToken(self.token(), Tokens.OPEN_BRACKET)
        conds = []
        while self.token(0) != Tokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x, y],C)
            if self.token(0) == Tokens.COMMA:
                self.token() # swallow the comma
            else:
                conds.append(self.parse_Expression())
        self.token() # swallow the CLOSE_BRACKET token
        self.assertToken(self.token(), Tokens.CLOSE) 
        drs = DRS(refs, conds)
        return self.attempt_BooleanExpression(drs)

    def get_BooleanExpression_factory(self):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        factory = None
        op = self.token(0)
        if op == Tokens.DRS_CONC:
            factory = ConcatenationDRS
        elif op in Tokens.OR:
            factory = DrtOrExpression
        elif op in Tokens.IMP:
            factory = DrtImpExpression
        elif op in Tokens.IFF:
            factory = DrtIffExpression
        elif op in Tokens.EQ:
            factory = DrtEqualityExpression
        return factory

    def make_ApplicationExpression(self, function, args):
        return DrtApplicationExpression(function, args)
    
    def make_VariableExpression(self, name):
        if logic.is_indvar(name):
            return DrtIndividualVariableExpression(name)
        else:
            return DrtVariableExpression(name)
    
    def make_LambdaExpression(self, variables, term):
        return DrtLambdaExpression(variables, term)
    
def demo():
    n = Tokens.NEW_NLTK
    print '='*20 + 'TEST PARSE' + '='*20
    parser = DrtParser()
    print parser.parse(r'DRS([x,y],[sees(x,y)])')
    print parser.parse(r'DRS([x],[man(x), walks(x)])')
    print parser.parse(r'\x.\y.DRS([],[sees(x,y)])')
    print parser.parse(r'\x.DRS([],[walks(x)])(john)')
    print parser.parse(r'(DRS([x],[walks(x)]) + DRS([y],[runs(y)]))')
    print parser.parse(r'(DRS([],[walks(x)]) -> DRS([],[runs(x)]))')
    print parser.parse(r'DRS([x],[PRO(x), sees(John,x)])')
    print parser.parse(r'DRS([x],[man(x), -DRS([],[walks(x)])])')
    print parser.parse(r'DRS([],[(DRS([x],[man(x)]) -> DRS([],[walks(x)]))])')

    print '='*20 + 'Test toFol()' + '='*20
    print parser.parse(r'DRS([x,y],[sees(x,y)])').toFol()


    print '='*20 + 'Test alpha conversion and lambda expression equality' + '='*20
    e1 = parser.parse(r'\x.drs([],[P(x)])')
    print e1
    e2 = e1.alpha_convert(DrtVariableExpression('z'))
    print e2
    print e1 == e2

    print '='*20 + 'Test resolve_anaphora()' + '='*20
    print parser.parse(r'DRS([x,y,z],[dog(x), cat(y), walks(z), PRO(z)])').resolve_anaphora()
    print parser.parse(r'DRS([],[(DRS([x],[dog(x)]) -> DRS([y],[walks(y), PRO(y)]))])').resolve_anaphora()
    print parser.parse(r'(DRS([x,y],[]) + DRS([],[PRO(x)]))').resolve_anaphora()
    print parser.parse(r'DRS([x],[walks(x), PRO(x)])').resolve_anaphora()

    print '='*20 + 'Test tp_equals()' + '='*20
    a = parser.parse(r'DRS([x],[man(x), walks(x)])')
    b = parser.parse(r'DRS([x],[walks(x), man(x)])')
    print a.tp_equals(b)
    
        
def test_draw():
    expressions = [
            r'x',
            r'DRS([],[])',
            r'DRS([x],[])',
            r'DRS([x],[man(x)])',

            r'drs([x,y],[sees(x,y)])',
            r'drs([x],[man(x), walks(x)])',
            r'\x.drs([],[man(x), walks(x)])',
            r'\x y.drs([],[sees(x,y)])',
            r'drs([],[(drs([],[walks(x)]) + drs([],[runs(x)]))])',
            
            r'drs([x],[man(x), -drs([],[walks(x)])])',
            r'drs([],[(drs([x],[man(x)]) -> drs([],[walks(x)]))])'
            ]
    
    for e in expressions:
        d = DrtParser().parse(e)
        d.draw()

if __name__ == '__main__':
    demo()
