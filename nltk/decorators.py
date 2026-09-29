"""
Decorator module by Michele Simionato <michelesimionato@libero.it>
Copyright Michele Simionato, distributed under the terms of the BSD License (see below).
http://www.phyast.pitt.edu/~micheles/python/documentation.html

Included in NLTK for its support of a nice memoization decorator.
"""

__docformat__ = "restructuredtext en"

## The basic trick is to generate the source code for the decorated function
## with the right signature and to evaluate it.
## Uncomment the statement 'print >> sys.stderr, func_src'  in _decorator
## to understand what is going on.

__all__ = ["decorator", "new_wrapper", "getinfo"]

import sys

# Hack to keep NLTK's "tokenize" module from colliding with the "tokenize" in
# the Python standard library.
OLD_SYS_PATH = sys.path[:]
sys.path = [p for p in sys.path if p and "nltk" not in str(p)]
import inspect
import keyword
import unicodedata

sys.path = OLD_SYS_PATH

# The globals the generated lambdas call through (``_wrapper_`` in new_wrapper,
# ``_call_``/``_func_`` in decorator). A parameter of any kind named like one
# would shadow it inside the lambda, so every sink refuses the whole set.
_RESERVED_NAMES = frozenset({"_call_", "_func_", "_wrapper_"})


def _fenced_parameters(signature):
    """Parse a signature string into ``(name, kind)`` pairs, refusing anything
    the wrapper eval must never see (CVE-2026-14727).

    The eval is what makes ``inspect.getfullargspec`` report the true signature
    on every supported Python (older ones ignore ``__signature__``), so it stays,
    but only a comma-separated list of plain names, ``*args``/``**kwargs`` names
    and bare ``*`` or ``/`` markers may reach it: nothing that can carry an
    annotation, a default, a call, an attribute or other expression syntax.
    Each name is judged by ``str.isidentifier`` (every legal name, non-ASCII
    included), must not be a keyword and must already be NFKC-normalised, as
    the parser would make it; a ``str`` subclass is refused, since its
    ``__str__`` could inject source at the interpolation. The marker structure
    is checked as the parser would (one ``/`` before any ``*``, one ``*``, a
    keyword-only name after a bare ``*``, ``**name`` last, no duplicate), so
    the eval can only ever compile a well-formed parameter list.
    """

    def _refuse(why):
        raise ValueError(
            f"refusing to build a wrapper from a {why} signature: {signature!r}"
        )

    if type(signature) is not str:
        _refuse("non-str")
    if not signature.strip():
        return []
    tokens = []
    for token in signature.split(","):
        token = token.strip()
        if token in ("*", "/"):
            tokens.append((token, None))
            continue
        name = token
        for prefix in ("**", "*"):
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        if not name.isidentifier() or keyword.iskeyword(name):
            _refuse("non-identifier")
        # The parser NFKC-normalises identifiers, so a name not already in that
        # form would become a different name (a reserved global, say) in the eval.
        if unicodedata.normalize("NFKC", name) != name:
            _refuse("non-NFKC-normalised")
        tokens.append((token, name))

    params, seen = [], set()
    slash_at, star_seen, bare_star_open, var_keyword_seen = None, False, False, False
    for token, name in tokens:
        if var_keyword_seen:
            _refuse("malformed (parameter after **name)")
        if token == "/":
            if slash_at is not None or star_seen or not params:
                _refuse("malformed (misplaced /)")
            slash_at = len(params)
            continue
        if token == "*":
            if star_seen:
                _refuse("malformed (second *)")
            star_seen, bare_star_open = True, True
            continue
        if token.startswith("**"):
            if bare_star_open:
                _refuse("malformed (bare * without a keyword-only name)")
            kind, var_keyword_seen = inspect.Parameter.VAR_KEYWORD, True
        elif token.startswith("*"):
            if star_seen:
                _refuse("malformed (second *)")
            kind, star_seen = inspect.Parameter.VAR_POSITIONAL, True
        elif star_seen:
            kind, bare_star_open = inspect.Parameter.KEYWORD_ONLY, False
        else:
            kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
        if name in seen:
            _refuse("malformed (duplicate name)")
        seen.add(name)
        params.append((name, kind))
    if bare_star_open:
        _refuse("malformed (bare * without a keyword-only name)")
    if slash_at is not None:
        params[:slash_at] = [
            (name, inspect.Parameter.POSITIONAL_ONLY) for name, _ in params[:slash_at]
        ]
    return params


def _assert_safe_signature(signature):
    """Refuse a signature string :func:`_fenced_parameters` cannot fence."""
    _fenced_parameters(signature)


def __legacysignature(signature):
    """
    For retrocompatibility reasons, we don't use a standard Signature.
    Instead, we use the string generated by this method.
    Basically, from a Signature we create a string and remove the default values.
    """
    # Built from the parameter names and kinds, never by parsing the printed
    # signature: a default such as (1, 2) or an annotation would otherwise be
    # split on its comma and leave expression text in the wrapper source.
    parts, star_seen, positional_only = [], False, False
    for p in signature.parameters.values():
        if p.kind is inspect.Parameter.POSITIONAL_ONLY:
            parts.append(p.name)
            positional_only = True
            continue
        if positional_only:
            parts.append("/")
            positional_only = False
        if p.kind is inspect.Parameter.VAR_POSITIONAL:
            parts.append("*" + p.name)
            star_seen = True
        elif p.kind is inspect.Parameter.VAR_KEYWORD:
            parts.append("**" + p.name)
        elif p.kind is inspect.Parameter.KEYWORD_ONLY:
            if not star_seen:
                parts.append("*")
                star_seen = True
            parts.append(p.name)
        else:
            parts.append(p.name)
    if positional_only:
        parts.append("/")
    return ", ".join(parts)


def _refuse_reserved(signature):
    """Refuse a parameter of ANY kind named like a wrapper global: inside the
    generated lambda it would shadow that global, so a caller could hand in the
    callable the wrapper then invokes. A real check, not an assert (``-O``)."""
    names = {name for name, _ in _fenced_parameters(signature)}
    clash = sorted(names & _RESERVED_NAMES)
    if clash:
        raise ValueError(f"{', '.join(clash)} is a reserved argument name")


def _call_arguments_from_signature(signature):
    """The argument list to forward to the wrapped callable, built ONLY from
    the fenced ``signature`` string: a positional or positional-only parameter
    is forwarded by name, a keyword-only one as ``name=name``, ``*args`` and
    ``**kwargs`` are splatted, and the bare ``*`` and ``/`` markers are dropped."""
    parts = []
    for name, kind in _fenced_parameters(signature):
        if kind is inspect.Parameter.VAR_POSITIONAL:
            parts.append("*" + name)
        elif kind is inspect.Parameter.VAR_KEYWORD:
            parts.append("**" + name)
        elif kind is inspect.Parameter.KEYWORD_ONLY:
            parts.append(name + "=" + name)
        else:
            parts.append(name)
    return ", ".join(parts)


def _call_arguments(fullsignature, signature):
    """:func:`_call_arguments_from_signature` for a model that also carries a
    Signature object, which is cross-checked and never trusted: its parameters
    must be genuine :class:`inspect.Parameter` objects with plain ``str`` names
    that match the fenced names one for one, in order, each of the kind the
    fenced string says. A forged ``__signature__`` whose names are ``str``
    subclasses (lying ``isidentifier`` or ``__format__``), or whose names or
    kinds disagree with the fenced string, is refused, so no text of its own
    ever reaches the eval and the eval only sees a call the parser accepts.
    """
    fenced = _fenced_parameters(signature)
    params = list(fullsignature.parameters.values())
    if len(params) != len(fenced):
        raise ValueError(
            "refusing a signature object that does not match the fenced signature"
        )
    for p, (name, kind) in zip(params, fenced):
        if type(p) is not inspect.Parameter or type(p.name) is not str:
            raise ValueError(
                "refusing a non-standard or non-identifier parameter name: "
                f"{getattr(p, 'name', p)!r}"
            )
        if p.name != name:
            raise ValueError(
                f"refusing parameter {p.name!r}: the fenced signature names {name!r}"
            )
        if p.kind is not kind:
            raise ValueError(
                f"refusing parameter {name!r}: its kind {p.kind!s} disagrees "
                f"with the fenced signature ({kind!s})"
            )
    return _call_arguments_from_signature(signature)


def getinfo(func):
    """
    Returns an info dictionary containing:
    - name (the name of the function : str)
    - argnames (the names of the arguments : list)
    - defaults (the values of the default arguments : tuple)
    - signature (the signature : str)
    - fullsignature (the full signature : Signature)
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

    >>> info["fullsignature"]
    <Signature (self, x=1, y=2, *args, **kw)>
    """
    assert inspect.ismethod(func) or inspect.isfunction(func)
    argspec = inspect.getfullargspec(func)
    regargs, varargs, varkwargs = argspec[:3]
    argnames = list(regargs)
    if varargs:
        argnames.append(varargs)
    if varkwargs:
        argnames.append(varkwargs)
    fullsignature = inspect.signature(func)
    # Convert Signature to str
    signature = __legacysignature(fullsignature)

    # pypy compatibility
    if hasattr(func, "__closure__"):
        _closure = func.__closure__
        _globals = func.__globals__
    else:
        _closure = func.func_closure
        _globals = func.func_globals

    return dict(
        name=func.__name__,
        argnames=argnames,
        signature=signature,
        fullsignature=fullsignature,
        defaults=func.__defaults__,
        kwdefaults=getattr(func, "__kwdefaults__", None),
        doc=func.__doc__,
        module=func.__module__,
        dict=func.__dict__,
        globals=_globals,
        closure=_closure,
    )


def update_wrapper(wrapper, model, infodict=None):
    "akin to functools.update_wrapper"
    infodict = infodict or getinfo(model)
    wrapper.__name__ = infodict["name"]
    wrapper.__doc__ = infodict["doc"]
    wrapper.__module__ = infodict["module"]
    wrapper.__dict__.update(infodict["dict"])
    wrapper.__defaults__ = infodict["defaults"]
    # Carry keyword-only defaults too: the rebuilt lambda strips them from its
    # signature, so without this a ``def f(*, b=5)`` loses its default (.get keeps
    # legacy model dicts that predate this key working).
    wrapper.__kwdefaults__ = infodict.get("kwdefaults")
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
    else:  # assume model is a function
        infodict = getinfo(model)
    signature = infodict["signature"]
    _assert_safe_signature(signature)
    _refuse_reserved(signature)
    # Def params and call args both come from the fenced signature string; a
    # Signature object, when present, is only cross-checked against it.
    if infodict.get("fullsignature") is not None:
        callargs = _call_arguments(infodict["fullsignature"], signature)
    else:
        callargs = _call_arguments_from_signature(signature)
    src = f"lambda {signature}: _wrapper_({callargs})"
    funcopy = eval(
        src, dict(_wrapper_=wrapper)
    )  # bare-exec ok: _assert_safe_signature fenced src (CVE-2026-14727)
    return update_wrapper(funcopy, model, infodict)


# helper used in decorator_factory
def __call__(self, func):
    return new_wrapper(lambda *a, **k: self.call(func, *a, **k), func)


def decorator_factory(cls):
    """
    Take a class with a ``.caller`` method and return a callable decorator
    object. It works by adding a suitable __call__ method to the class;
    it raises a TypeError if the class already has a nontrivial __call__
    method.
    """
    attrs = set(dir(cls))
    if "__call__" in attrs:
        raise TypeError(
            "You cannot decorate a class with a nontrivial " "__call__ method"
        )
    if "call" not in attrs:
        raise TypeError("You cannot decorate a class without a " ".call method")
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
    ...     print("Calling %r" % f.__name__)
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

    def _decorator(func):  # the real meat is here
        infodict = getinfo(func)
        signature = infodict["signature"]
        _assert_safe_signature(signature)
        _refuse_reserved(signature)
        # Def params and call args both come from the fenced signature string.
        callargs = _call_arguments(infodict["fullsignature"], signature)
        src = f"lambda {signature}: _call_(_func_, {callargs})"
        # import sys; print >> sys.stderr, src # for debugging purposes
        dec_func = eval(
            src, dict(_func_=func, _call_=caller)
        )  # bare-exec ok: _assert_safe_signature fenced src (CVE-2026-14727)
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
    result = func(*args)
    dic[args] = result
    return result


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
