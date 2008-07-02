"""
Handling for special feature names
"""

from sexp import *

#def remove_specials(sexpll):
    #i = 0
    #if isinstance(sexpl, basestring): return sexpl
    #length = len(sexpl)
    #while i < length:
        #sublist = sexpl[i]
        #if isinstance(sublist[0], basestring):
            #if sublist[0] in (":demo", "trace") or "%" in sublist[0]:
                #print sexpl
                #sexpl.remove(sublist)
                #i -= 1
                #length -= 1
        #i += 1
    #return sexpl


def parse_alt(sexpl):
    """
    Convert the alt feature
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
    feat, name, index, val = ('','','','')
    sexpl[0] = "alt"
    feat, name, index, val = parse_alt(sexpl)
    val.append(SexpList("(", ")"))
    return feat, name, index, val
