# ------------------------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   12 June 2005
# DESC:   Summarize date stamps in ascending chronological order
# ------------------------------------------------------------------------

import datetime, time
import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser

FM_DATE   = "dt"
FM_LEXEME = "lx"

def format_month(intMonth) :
    months = {  1 : "Jan",
                2 : "Feb",
                3 : "Mar",
                4 : "Apr",
                5 : "May",
                6 : "Jun",
                7 : "Jul",
                8 : "Aug",
                9 : "Sep",
               10 : "Oct",
               11 : "Nov",
               12 : "Dec",
               } 
    return months[intMonth]


def handle_options() :
    parser = OptionParser()
    parser.add_option("-f", "--filepath",
                      dest="filepath",
                      help="path to Shoebox dictionary file")
    (options, args) = parser.parse_args()
    if not options.filepath :
        sys.stderr.write("%s -f FILE\n" % sys.argv[0])
        sys.exit(0)
    return options.filepath


def process_file(fn) :
    d = {}
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()
    for e in sff.getEntries() :
        modDateStr = e.getFieldValuesByFieldMarkerAsString(FM_DATE)
        lexeme = e.getFieldValuesByFieldMarkerAsString(FM_LEXEME)
        if modDateStr :
            epochSecs = time.mktime(time.strptime(modDateStr, "%d/%b/%Y")) 
            modDate = datetime.datetime.fromtimestamp(epochSecs)
            if not d.has_key(modDate.year) :
                d[modDate.year] = {}
            if not d[modDate.year].has_key(modDate.month) :
                d[modDate.year][modDate.month] = []
            d[modDate.year][modDate.month].append(e)
    return d


def print_results(d) :
    print "YEAR MONTH COUNT"
    for yr in d.keys() :
        months = d[yr].keys()
        months.sort()
        for m in months :
            dateList = d[yr][m]
            count = len(dateList)
            print "%s %s %i" % (yr, format_month(m), count)


def main() :
    fn = handle_options()
    d = process_file(fn)
    print_results(d)


main()
