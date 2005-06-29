# --------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   24 June 2005
# DESC:   This script extracts all vowel-final entries
# --------------------------------------------------------

import sys, re
from shoebox.standardformat import StandardFormatFileParser

def handle_options() :
    try :
        return sys.argv[1]
    except :
        print "Usage: %s <FILEPATH>" % sys.argv[0]
        sys.exit(0)

def main() :
    filepath = handle_options()
    sffp = StandardFormatFileParser(filepath)
    sff = sffp.parse()
    for e in sff.getEntries() :
        hf = e.getHeadField()
        lex = hf[1]
        gloss = "/".join(e.getFieldValuesByFieldMarker("ge"))
        pos = e.getFieldValuesByFieldMarkerAsString("ps")
        vowels = "(aa|ee|ii|oo|uu)$"
        if re.search(vowels, lex) and pos.startswith("N."):
            print "%s [%s] '%s'" % (lex, pos, gloss)

main()
