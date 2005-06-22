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

def handle_options() :
    parser = OptionParser()
    parser.add_option("-f", "--filepath",
                      dest="filepath",
                      help="path to Shoebox dictionary file")
    parser.add_option("-m", "--fieldmarker",
                      dest="fieldmarker",
                      help="field marker to filter out")
    (options, args) = parser.parse_args()
    if not options.filepath or not options.fieldmarker :
        sys.stderr.write("%s -f FILE -m FIELD\n" % sys.argv[0])
        sys.exit(0)
    return options.filepath, options.fieldmarker

def main() :
    fn, field2Filter = handle_options()
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()
    print sff.getHeader()
    for e in sff.getEntries() :
        e.removeField("dt")
        print e
    
main()
