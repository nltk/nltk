"""
This module contains a couple of functions for better viewing of the 
FUF convesion/unification results
"""

def output_html(lst, header=[], style=""):
    s = " <table border=1 style='%s'> <tr> " % style
    for item in header:
        s += "<td><b>%s</b></td>" % item
    s += "</tr>"
    

    for item in lst:
        s += "<td><pre>%s</pre></td>" % item
    s += "</tr></table>"
    return s

def draw(fstruct, filename=None):
    """
    Draw graph representation of the feature structure using graphviz syntax
    """
    def draw_helper(output, fstruct, pcount, ccount):
        output += 'fs%d [label=" " style="filled" fillcolor="white"];\n' % (pcount)
        for fs, val in fstruct.items():
            if isinstance(val, nltk.FeatStruct):
                output +=  'fs%d -> fs%d [label="%s"];\n' % (pcount, ccount, fs)
                output, ccount = draw_helper(output, val, ccount,
                                                     ccount+1)
            else:
                output +=  'fs%d -> fs%d [label="%s"]; fs%d [label="%s" \
                style=filled fillcolor=grey];\n' % (pcount, ccount, fs,
                                                            ccount, val)
            ccount +=1 
        return output, ccount

    output, ccount = draw_helper("", fstruct, 0, 1)
    return "digraph fs {\n nodesep=1.0;\n" + output + "\n}";
