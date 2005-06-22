# ------------------------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   4 June 2005
# DESC:   ???
# ------------------------------------------------------------------------

import datetime, time
import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser

FM_DATE     = "dt"
FM_LEXEME   = "lx"
DATE_FORMAT = "%d/%b/%Y"

def handle_options() :
    parser = OptionParser()
    parser.add_option("-f", "--filepath",
                      dest="filepath",
                      help="path to Shoebox dictionary file")
    parser.add_option("-s", "--start",
                      dest="start",
                      help="start date")
    parser.add_option("-e", "--end",
                      dest="end",
                      help="end date")
    (options, args) = parser.parse_args()
    if not options.filepath or ( not ( options.start or options.end ) ) :
        sys.stderr.write("%s -f FILE -s START.DATE -e END.DATE\n" % sys.argv[0])
        sys.exit(0)
    return options.filepath, options.start, options.end


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

    
def process_file(fn, startDate, endDate) :
    d = {}
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()
    for e in sff.getEntries() :
        lexeme = e.getFieldValuesByFieldMarkerAsString(FM_LEXEME)
        modDateStr = e.getFieldValuesByFieldMarkerAsString(FM_DATE)
        print "[%s][%s]" % (lexeme, modDateStr)
        modDate = string_to_datetime(modDateStr, DATE_FORMAT)
        if modDate and in_time_range(startDate, endDate, modDate) :
            d[lexeme] = e
    return d


def print_results(d) :
    for lx in d.keys() :
        print "[%s]" % lx
    return
        
def main() :
    fn, startDateStr, endDateStr = handle_options()
    startDate = string_to_datetime(startDateStr, DATE_FORMAT)
    endDate = string_to_datetime(endDateStr, DATE_FORMAT)
    d = process_file(fn, startDate, endDate)
    print_results(d)
    return

main()
