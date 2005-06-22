# --------------------------------------------------------
# AUTHOR: Steven Bird
# DATE:   14 June 2005 (Revised by Stuart Robinson)
# DESC:   Add a CV field to show the consonant-vowel
#         skeleton of the word in the 'fri' field
# --------------------------------------------------------

import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser, StandardFormatFile

def handle_options() :
    parser = OptionParser()
    parser.add_option("-f",
                      "--filepath",
                      dest="filepath",
                      help="path to Shoebox dictionary file")
    (options, args) = parser.parse_args()
    if not options.filepath :
        sys.stderr.write("%s -f <FILEPATH>\n" % sys.argv[0])
        sys.exit(0)
    return options.filepath

def cv(s):
    s = s.lower()
    s = re.sub(r'[^a-z]',     r'-', s)
    s = re.sub(r'[^aeiou\-]', r'C', s)
    s = re.sub(r'[aeiou]',    r'V', s)
    return (s)

def main() :
    filepath = handle_options()
    fp = StandardFormatFileParser(filepath)
    sff = fp.parse()
    print sff.getHeader()
    for entry in sff.getEntries() :
        headField = e.getHeadField()
        frisian = headField[1]
        entry.addField("cv", cv(frisian))
        print e
        
main()
