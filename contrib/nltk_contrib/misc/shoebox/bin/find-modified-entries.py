# ------------------------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   4 June 2005
# DESC:   This script takes a user-specified date range and prints out
#         all entries with date stamps that fall within the date range
# ------------------------------------------------------------------------

import datetime, time
import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser

FM_DATE           = "dt"
FM_PART_OF_SPEECH = "ps"
FM_GLOSS          = "ge"
FM_ENGLISH        = "eng"

def usage() :
    sys.stderr.write("Usage: %s -s <START DATE> -e <END DATE> -f <DATE FORMAT> <DICTIONARY>\n" % sys.argv[0])
    sys.exit(0)
    
def handle_options() :
    parser = OptionParser()
    parser.add_option("-s", "--start",
                      dest="start",
                      help="start date")
    parser.add_option("-e", "--end",
                      dest="end",
                      help="end date")
    parser.add_option("-f", "--format",
                      dest="format",
                      help="date format")
    (options, args) = parser.parse_args()
    if not options.start and not options.end :
        usage()
    try :
        return args[0], options.start, options.end, options.format
    except :
        usage()

def string_to_datetime(dateString, dateFormat) :
    if dateString and dateFormat :
        epochSecs = time.mktime(time.strptime(dateString, dateFormat)) 
        return datetime.datetime.fromtimestamp(epochSecs)
    else :
        return None

def in_time_range(startDate, endDate, modDate) :
    if ( startDate and endDate ) and ( modDate >= startDate and modDate <= endDate ) :
        return True
    elif ( startDate and not endDate ) and ( modDate >= startDate ) :
        return True
    elif ( endDate and not startDate ) and ( modDate <= endDate ) : 
        return True
    else :
        return False
    
def process_file(fn, startDate, endDate, dateFormat) :
    d = {}
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()
    for e in sff.getEntries() :
        lexeme = e.getHeadField()[1]
        modDateStr = e.getFieldValuesByFieldMarkerAsString(FM_DATE)
        modDate = string_to_datetime(modDateStr, dateFormat)
        if modDate and in_time_range(startDate, endDate, modDate) :
            d[lexeme] = e
    return d

def print_results(d) :
    for lx in d.keys() :
        e = d[lx]
        pos = e.getFieldValuesByFieldMarkerAsString(FM_PART_OF_SPEECH)
        gloss = e.getFieldValuesByFieldMarkerAsString(FM_GLOSS)
        eng = e.getFieldValuesByFieldMarkerAsString(FM_ENGLISH, "/")
        dt = e.getFieldValuesByFieldMarkerAsString(FM_DATE)
        if eng :
            trans = eng
        else :
            trans = gloss
        print "%s [%s] '%s' (%s)" % (lx, pos, trans, dt)
    return
        
def main() :
    fn, startDateStr, endDateStr, userDateFormat = handle_options()
    dateFormat = "%d/%b/%Y"
    if userDateFormat :
        dateFormat = userDateFormat
    startDate = string_to_datetime(startDateStr, dateFormat)
    endDate = string_to_datetime(endDateStr, dateFormat)
    d = process_file(fn, startDate, endDate, dateFormat)
    print_results(d)
    return

main()
