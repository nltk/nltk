# Natural Language Toolkit: Linear Logic 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.internals import Counter

import glue
import drt_glue

class Error(Exception): pass

class UnificationError(Exception): pass

class Variable:
    """A variable, either free or bound."""
    
    def __init__(self, name):
        """
        Create a new C{Variable}.

        @type name: C{string}
        @param name: The name of the variable.
        """
        self.name = name

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):
        return not self.equals(other)

    def equals(self, other):
        """A comparison function."""
        assert isinstance(other, Variable)
        return self.name == other.name

    def can_unify_with(self, other, varbindings):
        """ Returns True if self and other are unifiable given
            the bindings already in varbindings.
        """
        if not (isinstance(other, Variable) and \
                varbindings.lookup_binding_of(self, True).name == \
                   varbindings.lookup_binding_of(other, True).name) and \
           not (isinstance(other, Constant) and \
                varbindings.lookup_binding_of(self, True).name == other.name):
               return varbindings.is_consistant_with(VariableBinding(self, other))
        else:
            return True
        
    def unify_with(self, other, varbindings):
        """ Tries to unify self with other.  If it can, then the
            necessary binding is added to varbindings as a side-effect.
        """
        if not (isinstance(other, Variable) and \
                varbindings.lookup_binding_of(self, True).name == \
                   varbindings.lookup_binding_of(other, True).name) and \
           not (isinstance(other, Constant) and \
                varbindings.lookup_binding_of(self, True).name == other.name):
            try:
                varbindings.append(VariableBinding(self, other))
            except VariableBindingException:
                raise UnificationError

    def __str__(self): return self.name

    def __repr__(self): return "Variable('%s')" % self.name

    def __hash__(self): return hash(repr(self))

class Constant:
    """A nonlogical constant."""
    
    def __init__(self, name):
        """
        Create a new C{Constant}.

        @type name: C{string}
        @param name: The name of the constant.
        """
        self.name = name

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):
        return not self.equals(other)

    def equals(self, other):
        """A comparison function."""
        assert isinstance(other, Constant)
        return self.name == other.name
        
    def can_unify_with(self, other, varbindings):
        if isinstance(other, Variable) and \
           not self.name == varbindings.lookup_binding_of(other, True).name:
            return varbindings.is_consistant_with(VariableBinding(other, self))
        elif isinstance(other, Constant) and self != other:
            return False
        else:
            return True

    def unify_with(self, other, varbindings):
        if isinstance(other, Variable) and \
           not self.name == varbindings.lookup_binding_of(other, True).name:
            try:
                varbindings.append(VariableBinding(other, self))
            except VariableBindingException:
                raise UnificationError
        elif isinstance(other, Constant) and self != other:
            raise UnificationError

    def __str__(self): return self.name

    def __repr__(self): return "Constant('%s')" % self.name

    def __hash__(self): return hash(repr(self))

class Expression:
    """The abstract class of a linear logic expression."""
    def __init__(self):
        if self.__class__ is Expression:
            raise NotImplementedError

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):
        return not self.equals(other)

    def equals(self, other):
        """Are the two expressions equal, modulo alpha conversion?"""
        return NotImplementedError

    def variables(self):
        """Set of all variables."""
        raise NotImplementedError

    def free(self):
        """Set of free variables."""
        raise NotImplementedError

    def subterms(self):
        """Set of all subterms (including self)."""
        raise NotImplementedError


    def replace(self, variable, expression):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        raise NotImplementedError

    def simplify(self, varbindings=[]):
        """Evaluate the form by repeatedly applying applications."""
        raise NotImplementedError

    def compile_pos(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        raise NotImplementedError

    def compile_neg(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        raise NotImplementedError

    def skolemise(self):
        """
        Perform a simple Skolemisation operation.  Existential quantifiers are
        simply dropped and all variables they introduce are renamed so that
        they are unique.
        """
        return self._skolemise(set(), Counter())

    def _skolemise(self, bound_vars, counter):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

class VariableExpression(Expression):
    """A variable expression which consists solely of a variable."""
    def __init__(self, variable, dependencies=[]):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        self.variable = variable
        self.dependencies = dependencies

    def can_unify_with(self, other, varbindings):
        if isinstance(other, VariableExpression):
            return self.variable.can_unify_with(other.variable, varbindings)
        elif isinstance(other, ConstantExpression):
            return self.variable.can_unify_with(other.constant, varbindings)

    def unify_with(self, other, varbindings):
        try:
            if isinstance(other, VariableExpression):
                self.variable.unify_with(other.variable, varbindings)
            elif isinstance(other, ConstantExpression):
                self.variable.unify_with(other.constant, varbindings)
        except UnificationError:
            raise

    def equals(self, other):
        if isinstance(self, VariableExpression) and \
           isinstance(other, VariableExpression):
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
        if self.variable.equals(variable):
            return expression
        else:
            return self
        
    def simplify(self, varbindings=[]):
        if varbindings:
            binding = varbindings.lookup_binding_of(self.variable, True)
            if isinstance(binding, Variable):
                return VariableExpression(binding, self.dependencies)
            elif isinstance(binding, Constant):
                return ConstantExpression(binding, self.dependencies)
            else:
                raise Exception, 'binding (%s) is not Variable or Constant' % binding
        else:
            return self

    def infixify(self):
        return self

    def name(self):
        return self.variable.name

    def compile_pos(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        self.dependencies = []
        return (self, [])

    def compile_neg(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        self.dependencies = []
        return (self, [])

    def _skolemise(self, bound_vars, counter):
        return self

    def __str__(self):
        accum = '%s' % self.variable
        if self.dependencies:
            accum += '%s' % self.dependencies
        return accum

    def __repr__(self):
        accum = "VariableExpression('%s')" % self.variable
        if self.dependencies:
            accum += '%s' % self.dependencies
        return accum

    def __hash__(self): return hash(repr(self))

class VariableBindingError(Exception): pass

class VariableBinding:
    def __init__(self, var, arg):
        # var must be a Variable
        if not isinstance(var, Variable):
            raise VariableBindingError, 'Cannot create tuple (%s, %s): first arg of tuple not a Variable' % (var, arg)
        
        # arg can be a Constant or Variable
        if not (isinstance(arg, Constant) or \
                isinstance(var, Variable)):
            raise VariableBindingError, 'Cannot create tuple (%s, %s): second arg of tuple not a Constant or a Variable' % (var, arg)

        if var.name == arg.name:
            raise VariableBindingException, 'Cannot bind Variable %s to itself' % var

        # else, it's ok
        self.var = var
        self.arg = arg

    def __repr__(self): return "VariableBinding('%s', '%s')" % (self.var, self.arg)

    def __str__(self): return "(%s, %s)" % (self.var, self.arg)

class VariableBindingsList(list):
    def append(self, vb):
        if self.is_consistant_with(vb):
            self += [vb]
        else:
            raise VariableBindingException, 'Variable of %s already bound to another value' % (vb)

    def is_consistant_with(self, vb):
        if not isinstance(vb, VariableBinding):
            raise RuntimeError, 'Attempting to check consistancy with non-VariableBinding %s' % (vb)

        # check if the variable of the binding is already in the list
        binding = self.lookup_binding_of(vb.var, False)

        ## TASK: ADD A CHECK TO ENSURE NEW VB WOULDN'T CAUSE A CYCLE

        if not binding:
            return True
        
        else:
            # if it doesn't conflict with the list, i.e. vb.var is already bound to vb.arg
            if binding.name == vb.arg.name:
                return True
            # else, it DOES conflict with the list
            else:
                return False
    
    def lookup_binding_of(self, var, return_var_if_no_match):
        if not isinstance(var, Variable):
            raise RuntimeError, 'Attempting to look up binding of non-Variable %s' % (var)
        
        for vb in self:
            # if vb has the var we are looking for
            if var == vb.var:
                # if the arg of the binding found is itself a variable
                if isinstance(vb.arg, Variable):
                    # return the binding of THAT variable, or itself if it's not bound
                    return self.lookup_binding_of(vb.arg, True)
                else:
                    # return the binding found since it is not a variable itself
                    return vb.arg
        # if no match is found in the list
        if return_var_if_no_match:
            return var
        else:
            return None

    def __add__(self, other):
        try:
            l = VariableBindingsList()
            for vb in self:
                l.append(vb)
            for vb in other:
                l.append(vb)
            return l
        except VariableBindingException:
            raise VariableBindingException, 'Attempting to add two contradicting VariableBindingsLists'

    def __str__(self):
        accum = '['
        first = True
        for vb in self:
            if first:
                first = False
            else:
                accum += ', '
            accum += vb.__str__()
        return accum + ']'

    def __repr__(self):
        return self.__str__()
            
                    
class VariableBindingException(Exception): pass
                
class ApplicationExpression(Expression):
    """An application expression: (M N)."""
    def __init__(self, first=None, second=None, seconds_indicies=set([])):
        Expression.__init__(self)

        if first:
            first_simp = first.simplify()
            second_simp = second.simplify()
            
            try:
                # create a NEW, combined variable bindings list
                self.varbindings = VariableBindingsList()

                # if first is a type that has a list of variable bindings
                if isinstance(first, ApplicationExpression):
                    for varbind in first.varbindings:
                        self.varbindings.append(varbind)

                # if second is a type that has a list of variable bindings
                if isinstance(second, ApplicationExpression):
                    for varbind in second.varbindings:
                        self.varbindings.append(varbind)
            
            except VariableBindingException:
                raise LinearLogicApplicationError, \
                      'Attempting to apply Linear Logic formula %s to %s' % \
                       (first_simp.infixify(), second_simp.infixify())

            try:
                if isinstance(first_simp, ApplicationExpression) and \
                   isinstance(first_simp.first, ApplicationExpression) and \
                   isinstance(first_simp.first.first, Operator) and \
                   first_simp.op == Parser.IMPLIES:
                        first_simp.first.second.unify_with(second_simp, self.varbindings)

                        # If you are running it on complied premises, more conditions apply
                        if seconds_indicies:
                            # A.dependencies of (A -o (B -o C)) must be a proper subset of seconds_indicies
                            if not set(first_simp.first.second.dependencies).issubset(seconds_indicies):
                                raise LinearLogicApplicationError, \
                                      'Dependencies unfulfilled when attempting to apply Linear Logic formula %s to %s' % (first_simp, second_simp)
                            if set(first_simp.first.second.dependencies) == seconds_indicies:
                                raise LinearLogicApplicationError, \
                                      'Dependencies not a proper subset of indicies when attempting to apply Linear Logic formula %s to %s' % (first_simp, second_simp)

            except UnificationError:
                # self is of the form is '(((-> A) B) C)' a.k.a. '((A -> B) C)'
                #   where A!=C, meaning that this is not a valid application
                raise LinearLogicApplicationError, \
                      'Attempting to apply Linear Logic formula %s to %s' % (first_simp, second_simp)

            # else, it's ok
            assert isinstance(first, Expression)
            assert isinstance(second, Expression)
            self.first = first
            self.second = second

    def can_unify_with(self, other, varbindings):
        if self.__class__ == other.__class__:
            return self.first.can_unify_with(other.first, varbindings) and \
                   self.second.can_unify_with(other.second, varbindings)
        else:
            return False

    def unify_with(self, other, varbindings):
        if self.__class__ == other.__class__:
            try:
                self.first.unify_with(other.first, varbindings)
                self.second.unify_with(other.second, varbindings)
            except UnificationError:
                raise
        else:
            raise UnificationError

    def applyto(self, arg, seconds_indicies=set([])):
        return ApplicationExpression(self, arg, seconds_indicies)

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
        if isinstance(functor, Operator):
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

    def initialize_labels(self, fstruct):
        if isinstance(self.first, ApplicationExpression):
            self.first.initialize_labels(fstruct)
        elif isinstance(self.first, ConstantExpression) and not isinstance(self.first, Operator):
            new_label = fstruct.initialize_label(self.first.constant.name.lower())
            if new_label[0].isupper():
                self.first = VariableExpression(Variable(new_label))
            else:
                self.first = ConstantExpression(Constant(new_label))
        elif isinstance(self.first, VariableExpression):
            new_label = fstruct.initialize_label(self.first.variable.name.lower())
            if new_label[0].isupper():
                self.first = VariableExpression(Variable(new_label))
            else:
                self.first = ConstantExpression(Constant(new_label))

        if isinstance(self.second, ApplicationExpression):
            self.second.initialize_labels(fstruct)
        elif isinstance(self.second, ConstantExpression):
            new_label = fstruct.initialize_label(self.second.constant.name.lower())
            if new_label[0].isupper():
                self.second = VariableExpression(Variable(new_label))
            else:
                self.second = ConstantExpression(Constant(new_label))
        elif isinstance(self.second, VariableExpression):
            new_label = fstruct.initialize_label(self.second.variable.name.lower())
            if new_label[0].isupper():
                self.second = VariableExpression(Variable(new_label))
            else:
                self.second = ConstantExpression(Constant(new_label))
                            
    def simplify(self, varbindings_input=None):
        if varbindings_input is None:
            first = self.first.simplify(self.varbindings)
            second = self.second.simplify(self.varbindings)
        else:
            first = self.first.simplify(varbindings_input)
            second = self.second.simplify(varbindings_input)

        # if first=(A -o B), then second=A (because of the processing in __init__)
        #   so, return B
        if isinstance(first, ApplicationExpression) and \
           isinstance(first.first, ApplicationExpression) and \
           first.op == Parser.IMPLIES:
            # Reduce Modus Ponens
            return first.second
        else:
            return self.__class__(first, second)

    def infixify(self):
        first = self.first.infixify()
        second = self.second.infixify()
        if isinstance(first, Operator):
            ret_val = self.__class__(second, first)
        else:
            ret_val = self.__class__()
            ret_val.first = first
            ret_val.second = second
        ret_val.varbindings = self.varbindings
        return ret_val

    def compile_pos(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        # ((-o A) B)
        assert isinstance(self.first, ApplicationExpression) and \
               self.first.op == Parser.IMPLIES
        second_clausified = self.second.compile_pos(fresh_index, drt)
        first_clausified  = self.first.second.compile_neg(fresh_index, drt)
        assert isinstance(first_clausified[0], ConstantExpression) or \
               isinstance(first_clausified[0], VariableExpression)
        return (ApplicationExpression(ApplicationExpression(Operator(Parser.IMPLIES),first_clausified[0]),second_clausified[0]), \
                first_clausified[1]+second_clausified[1])

    def compile_neg(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""

        # ((-o A) B)
        assert isinstance(self.first, ApplicationExpression) and \
               self.first.op == Parser.IMPLIES
        second_clausified = self.second.compile_neg(fresh_index, drt)
        assert isinstance(second_clausified[0], ConstantExpression) or \
               isinstance(second_clausified[0], VariableExpression)
        first_clausified  = self.first.second.compile_pos(fresh_index, drt)
        second_clausified[0].dependencies.append(fresh_index[0])

        if drt:
            new_gf = drt_glue.GlueFormula('v%s' % fresh_index[0], first_clausified[0], set([fresh_index[0]]))
        else:
            new_gf = glue.GlueFormula('v%s' % fresh_index[0], first_clausified[0], set([fresh_index[0]]))
        fresh_index[0]+=1
        return (second_clausified[0],
                [new_gf]+first_clausified[1]+second_clausified[1])

    def _skolemise(self, bound_vars, counter):
        first = self.first._skolemise(bound_vars, counter)
        second = self.second._skolemise(bound_vars, counter)
        return self.__class__(first, second)

    def __str__(self, print_varbindings=True):
        # Print ((M N) P) as (M N P).
        strFirst = str(self.first)
        if isinstance(self.first, ApplicationExpression):
            if not isinstance(self.second, Operator):
                strFirst = strFirst[1:-1]
        return_str = '(%s %s)' % (strFirst, self.second)
        if self.varbindings != []:
            return_str += ' ['
            first = True
            for varbind in self.varbindings:
                if first:
                    first = False
                else:
                    return_str += ', '
                return_str += varbind.__str__()
            return_str += ']'
        return return_str

    def __repr__(self): return "ApplicationExpression('%s', '%s') %s" % (self.first, self.second, self.varbindings)

    def __hash__(self): return hash(repr(self))

class ConstantExpression(Expression):
    """A constant expression, consisting solely of a constant."""
    def __init__(self, constant, dependencies=[]):
        Expression.__init__(self)
        assert isinstance(constant, Constant)
        self.constant = constant
        self.dependencies = dependencies

    def can_unify_with(self, other, varbindings):
        if isinstance(other, VariableExpression):
            return self.constant.can_unify_with(other.variable, varbindings)
        elif isinstance(other, ConstantExpression):
            return self.constant.can_unify_with(other.constant, varbindings)
        else:
            raise Exception, '%s is neither a VariableExpression or a ConstantExpression' % other.__repr__()

    def unify_with(self, other, varbindings):
        try:
            if isinstance(other, VariableExpression):
                self.constant.unify_with(other.variable, varbindings)
            elif isinstance(other, ConstantExpression):
                self.constant.unify_with(other.constant, varbindings)
            else:
                raise Exception, '%s is neither a VariableExpression or a ConstantExpression' % other.__repr__()
        except UnificationError:
            raise

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.constant.equals(other.constant)
        else:
            return False

    def variables(self):
        return set()

    def free(self):
        return set()

    def subterms(self):
        return set([self])

    def replace(self, variable, expression):
        return self
        
    def simplify(self, varbindings=[]):
        return self

    def infixify(self):
        return self

    def name(self):
        return self.constant.name

    def _skolemise(self, bound_vars, counter):
        return self

    def compile_pos(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        self.dependencies = []
        return (self, [])

    def compile_neg(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        self.dependencies = []
        return (self, [])

    def __str__(self):
        accum = '%s' % self.constant
        if self.dependencies:
            accum += '%s' % self.dependencies
        return accum

    def __repr__(self):
        accum = "ConstantExpression('%s')" % self.constant
        if self.dependencies:
            accum += '%s' % self.dependencies
        return accum

    def __hash__(self): return hash(repr(self))


class Operator(ConstantExpression):
    """
    A boolean operator, such as 'not' or 'and', or the equality
    relation ('=').
    """
    def __init__(self, operator):
        Expression.__init__(self)
        assert operator in Parser.OPS
        self.constant = operator
        self.operator = operator

    def can_unify_with(self, other, varbindings):
        return (isinstance(other, Operator) and self == other)

    def unify_with(self, other, varbindings):
        if not (isinstance(other, Operator) and self == other):
            raise UnificationError

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.constant == other.constant
        else:
            return False

    def simplify(self, varbindings=[]):
        return self

    def compile_pos(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        raise NotImplementedError

    def compile_neg(self, fresh_index, drt=False):
        """From Iddo Lev's PhD Dissertation p108-109"""
        raise NotImplementedError

    def __str__(self): return '%s' % self.operator

    def __repr__(self): return "Operator('%s')" % self.operator

class LinearLogicApplicationError(RuntimeError): pass

class Parser:
    """Linear Logic Expression Parser."""
    
    # Tokens.
    OPEN = '('
    CLOSE = ')'
    IMPLIES = '-o'
    BOOL = [IMPLIES]
    OPS = BOOL

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
        self.buffer = self.buffer.replace('(', ' ( ')
        self.buffer = self.buffer.replace(')', ' ) ')
        for op in Parser.OPS:
            self.buffer = self.buffer.replace(op, ' %s ' % op)

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

    def next(self):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
        
        if tok == Parser.OPEN:
            # Expression is an application expression: (M N)
            first = self.next()
            second = self.next()
            exps = []
            while self.token(0) != Parser.CLOSE:
                # Support expressions like: (M N P) == ((M N) P)
                exps.append(self.next())
            tok = self.token() # swallow the close token
            assert tok == Parser.CLOSE
            if isinstance(second, Operator):
                accum = self.make_ApplicationExpression(second, first)
            else:
                accum = self.make_ApplicationExpression(first, second)
            while exps:
                exp, exps = exps[0], exps[1:]
                accum = self.make_ApplicationExpression(accum, exp)
            return accum

        elif tok in self.constants:
            # Expression is a simple constant expression: a
            return ConstantExpression(Constant(tok))

        elif tok in Parser.OPS:
            # Expression is a boolean operator or the equality symbol
            return Operator(tok)

        else:
            # If the token is not punctuation or an operator
            if tok not in [Parser.OPEN, Parser.CLOSE] and \
               tok not in Parser.BOOL:
                if tok[0].isupper():
                    # A variable is a value that starts with a capital letter
                    return VariableExpression(Variable(tok))
                else:
                    # A constant is a value that starts with a lowercase letter
                    return ConstantExpression(Constant(tok))
            else:
                raise Error, "parse error, unexpected token: %s" % tok
    
    # This is intended to be overridden, so that you can derive a Parser class
    # that constructs expressions using your subclasses.  So far we only need
    # to overridde ApplicationExpression, but the same thing could be done for
    # other expression types.
    def make_ApplicationExpression(self, first, second):
        return ApplicationExpression(first, second)

def demo():
    llp = Parser()
    p = llp.parse('p')
    p_q = llp.parse('(p -o q)')
    print p_q
    print p_q.infixify()
    q = p_q.applyto(p)
    print q.__repr__()
    print q.simplify().infixify()
    
    print ''

    gf = llp.parse('(g -o f)')
    gGG = llp.parse('((g -o G) -o G)')
    f = gGG.applyto(gf)
    print f.__repr__()
    print f.simplify().infixify()
    HHG = llp.parse('(H -o (H -o G))')
    ff = HHG.applyto(f)
    print ff
    print ff.simplify().infixify()

if __name__ == '__main__':
    demo()

