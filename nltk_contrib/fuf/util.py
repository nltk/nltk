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
