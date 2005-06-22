import sys
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser

def handle_options() :
    """ Obtains filepath to Shoebox dictionary as command-line option """
    parser = OptionParser()
    parser.add_option("-f",
                      "--filepath",
                      dest="filepath",
                      help="path to Shoebox dictionary file")
    (options, args) = parser.parse_args()
    if not options.filepath :
        sys.stderr.write("%s -f PATH.TO.SHOEBOX.FILE\n" % sys.argv[0])
        sys.exit(0)
    return options.filepath

def sort_by_value(d):
    """ Returns the keys of dictionary d sorted by their values """
    items=d.items()
    backitems=[ [v[1],v[0]] for v in items]
    backitems.sort()
    return [ backitems[i][1] for i in range(0,len(backitems))]

def get_entries(fn) :
    """ Parses Shoebox dictionary and returns entries """
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()
    return sff.getEntries()

def process_entries(entries) :
    """ Creates a dictionary with field marker counts from list of entries """
    counter = {}
    i = 0
    for e in entries :
        for fm in e.getFields() :
            try :
                counter[fm] = counter[fm] + 1 
            except :
                counter[fm] = 1
    return counter

def main() :
    filepath = handle_options()
    entries = get_entries(filepath)
    totalEntries = len(entries)

    counter = process_entries(entries)
    fieldMarkers = sort_by_value(counter)
    fieldMarkers.reverse()
    for fieldMarker in fieldMarkers :
        numEntries = counter[fieldMarker]
        pctEntries = ((1.0 * numEntries)/totalEntries) * 100.0
        print "\%s\t%i\t%i%%" % (fieldMarker, numEntries, pctEntries)
    print "%s\t%i\t%i%%" % ("TOTAL", 100, 100)
    
main()
