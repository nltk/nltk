# --------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   2 May 2005
# DESC:   This script is meant to print out a plain text
#         version of the dictionary file ROTRT.DIC
# --------------------------------------------------------

import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser

def handle_options() :
    parser = OptionParser()
    parser.add_option("-f",
                      "--filepath",
                      dest="filepath",
                      help="path to Shoebox dictionary file")
    (options, args) = parser.parse_args()
    if not options.filepath :
        sys.stderr.write("%s FILEPATH" % sys.argv[0])
        sys.exit(0)
    return options.filepath
    
def main() :
    filepath = handle_options()
    fp = StandardFormatFileParser(filepath)
    sff = fp.parse()
    print sff.getHeader()
    for e in sff.getEntries() :
        lex   = e.getHeadField()[1]
        pos   = e.getFieldValuesByFieldMarkerAsString("ps")
        gloss = e.getFieldValuesByFieldMarkerAsString("ge")
        eng   = e.getFieldValuesByFieldMarker("eng")
        if eng :
            print "%s (%s) ``%s''" % (lex, pos, ", ".join(eng))
        else :
            print "%s (%s) ``%s''" % (lex, pos, gloss)
    
main()
