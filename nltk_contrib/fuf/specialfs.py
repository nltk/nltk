"""
Handling for special feature names during parsing
"""

from sexp import *

def parse_alt(sexpl):
    """
    Parse the I{alt} feature definition. 

    @param sexpl: An s-expression list that represents an I{alt} struture
    @type sexpl: C{sexp.SexpList} 
    @return: A tuple composed of ('alt', 'optional alt name', 'optional alt
    index', 'alt values')
    """

    feat, name, index, val = ('', '', '', '')

    # named alt
    if isinstance(sexpl[1], basestring):
        # alt with index
        if len(sexpl) == 4:
            feat, name, index, val = sexpl
        # alt without index
        if len(sexpl) == 3:
            feat, name, val = sexpl
    # alt without name
    elif isinstance(sexpl[1], SexpList):
        if len(sexpl) == 3:
            feat, index, val = sexpl
        if len(sexpl) == 2:
            feat, val = sexpl

    if all(i == "" for i in (feat, name, index, val)):
        return ValueError("Maformed alt: %s" % sexpl)
    return (feat, name, index, val)

def parse_opt(sexpl):
    """
    Parse the I{opt} structure

    @param sexpl: An s-expression list that represents an I{opt} structure
    @type sexpl: C{sexp.SexpList}
    @return: A tuple composed of ('opt', 'optional opt name', 'opt index', 'opt
    value')
    """
    feat, name, index, val = ('','','','')
    sexpl[0] = "alt"
    feat, name, index, val = parse_alt(sexpl)
    val.append(SexpList("(", ")"))
    return feat, name, index, val
