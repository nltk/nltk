"""
Decorator module by Michele Simionato <michelesimionato@libero.it>
Copyright Michele Simionato, distributed under the terms of the BSD License (see below).
http://www.phyast.pitt.edu/~micheles/python/documentation.html

Included in NLTK for its support of a nice memoization decorator.
"""
__docformat__ = 'restructuredtext en'

## The basic trick is to generate the source code for the decorated function
## with the right signature and to evaluate it.
## Uncomment the statement 'print >> sys.stderr, func_src'  in _decorator
## to understand what is going on.

__all__ = ["decorator", "new_wrapper", "getinfo"]

import inspect, sys

try:
    set
except NameError:
    from sets import Set as set

def getinfo(func):
    """
    Returns an info dictionary containing:
    - name (the name of the function : str)
    - argnames (the names of the arguments : list)
    - defaults (the values of the default arguments : tuple)
    - signature (the signature : str)
    - doc (the docstring : str)
    - module (the module name : str)
    - dict (the function __dict__ : str)
    
    >>> def f(self, x=1, y=2, *args, **kw): pass

    >>> info = getinfo(f)

    >>> info["name"]
    'f'
    >>> info["argnames"]
    ['self', 'x', 'y', 'args', 'kw']
    
    >>> info["defaults"]
    (1, 2)

    >>> info["signature"]
    'self, x, y, *args, **kw'
    """
    assert inspect.ismethod(func) or inspect.isfunction(func)
    regargs, varargs, varkwargs, defaults = inspect.getargspec(func)
    argnames = list(regargs)
    if varargs:
        argnames.append(varargs)
    if varkwargs:
        argnames.append(varkwargs)
    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")[1:-1]
    return dict(name=func.__name__, argnames=argnames, signature=signature,
                defaults = func.func_defaults, doc=func.__doc__,
                module=func.__module__, dict=func.__dict__,
                globals=func.func_globals, closure=func.func_closure)

# akin to functools.update_wrapper
def update_wrapper(wrapper, model, infodict=None):
    infodict = infodict or getinfo(model)
    try:
        wrapper.__name__ = infodict['name']
    except: # Python version < 2.4
        pass
    wrapper.__doc__ = infodict['doc']
    wrapper.__module__ = infodict['module']
    wrapper.__dict__.update(infodict['dict'])
    wrapper.func_defaults = infodict['defaults']
    wrapper.undecorated = model
    return wrapper

def new_wrapper(wrapper, model):
    """
    An improvement over functools.update_wrapper. The wrapper is a generic
    callable object. It works by generating a copy of the wrapper with the 
    right signature and by updating the copy, not the original.
    Moreovoer, 'model' can be a dictionary with keys 'name', 'doc', 'module',
    'dict', 'defaults'.
    """
    if isinstance(model, dict):
        infodict = model
    else: # assume model is a function
        infodict = getinfo(model)
    assert not '_wrapper_' in infodict["argnames"], (
        '"_wrapper_" is a reserved argument name!')
    src = "lambda %(signature)s: _wrapper_(%(signature)s)" % infodict
    funcopy = eval(src, dict(_wrapper_=wrapper))
    return update_wrapper(funcopy, model, infodict)

# helper used in decorator_factory
def __call__(self, func):
    return new_wrapper(lambda *a, **k : self.call(func, *a, **k), func)

def decorator_factory(cls):
    """
    Take a class with a ``.caller`` method and return a callable decorator
    object. It works by adding a suitable __call__ method to the class;
    it raises a TypeError if the class already has a nontrivial __call__
    method.
    """
    attrs = set(dir(cls))
    if '__call__' in attrs:
        raise TypeError('You cannot decorate a class with a nontrivial '
                        '__call__ method')
    if 'call' not in attrs:
        raise TypeError('You cannot decorate a class without a '
                        '.call method')
    cls.__call__ = __call__
    return cls

def decorator(caller):
    """
    General purpose decorator factory: takes a caller function as
    input and returns a decorator with the same attributes.
    A caller function is any function like this::

     def caller(func, *args, **kw):
         # do something
         return func(*args, **kw)
    
    Here is an example of usage:

    >>> @decorator
    ... def chatty(f, *args, **kw):
    ...     print "Calling %r" % f.__name__
    ...     return f(*args, **kw)

    >>> chatty.__name__
    'chatty'
    
    >>> @chatty
    ... def f(): pass
    ...
    >>> f()
    Calling 'f'

    decorator can also take in input a class with a .caller method; in this
    case it converts the class into a factory of callable decorator objects.
    See the documentation for an example.
    """
    if inspect.isclass(caller):
        return decorator_factory(caller)
    def _decorator(func): # the real meat is here
        infodict = getinfo(func)
        argnames = infodict['argnames']
        assert not ('_call_' in argnames or '_func_' in argnames), (
            'You cannot use _call_ or _func_ as argument names!')
        src = "lambda %(signature)s: _call_(_func_, %(signature)s)" % infodict
        # import sys; print >> sys.stderr, src # for debugging purposes
        dec_func = eval(src, dict(_func_=func, _call_=caller))
        return update_wrapper(dec_func, func, infodict)
    return update_wrapper(_decorator, caller)

def getattr_(obj, name, default_thunk):
    "Similar to .setdefault in dictionaries."
    try:
        return getattr(obj, name)
    except AttributeError:
        default = default_thunk()
        setattr(obj, name, default)
        return default

@decorator
def memoize(func, *args):
    dic = getattr_(func, "memoize_dic", dict)
    # memoize_dic is created at the first call
    if args in dic:
        return dic[args]
    else:
        result = func(*args)
        dic[args] = result
        return result

if __name__ == "__main__":
    import doctest; doctest.testmod()

##########################     LEGALESE    ###############################
      
##   Redistributions of source code must retain the above copyright 
##   notice, this list of conditions and the following disclaimer.
##   Redistributions in bytecode form must reproduce the above copyright
##   notice, this list of conditions and the following disclaimer in
##   the documentation and/or other materials provided with the
##   distribution. 

##   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
##   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
##   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
##   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
##   HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
##   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
##   BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
##   OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
##   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
##   TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
##   USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
##   DAMAGE.
