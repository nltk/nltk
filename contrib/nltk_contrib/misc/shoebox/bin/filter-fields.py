# ---------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   4 June 2005
# DESC:   Filters out select fields from Shoebox dictionary
# ---------------------------------------------------------

import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser
from shoebox.standardformat import StandardFormatFile
from shoebox.standardformat import Entry

def usage() :
    sys.stderr.write("%s -m <FIELD> <FILE>\n" % sys.argv[0])
    sys.exit(0)
        
def handle_options() :
    parser = OptionParser()
    parser.add_option("-m", "--fieldmarker",
                      dest="fieldmarker",
                      help="field marker to filter out")
    (options, args) = parser.parse_args()
    if not options.fieldmarker :
        usage()
    try :
        return options.filepath, options.fieldmarker
    except :
        usage()
        
def main() :
    fn, field2Filter = handle_options()
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()
    print sff.getHeader()
    for e in sff.getEntries() :
        e.removeField(field2Filter)
        print e
    
main()
