#!/usr/bin/python
__author__ = "Ewan Klein"
__version__ = "$Revision$"
__date__ = "$Date$"

from pprint import pprint # pretty printing
import xmlrpclib
from optparse import OptionParser

meerkatURI = "http://www.oreillynet.com/meerkat/xml-rpc/server.php"
meerkatsvr = xmlrpclib.Server(meerkatURI)

def getitems(options):
    # This dictionary holds parameters that are then passed on in the
    # XML request to the server:
    params = {
        'channel': options.channel,
        'time_period': options.time,
        'dc': options.dc, #use Dublin Core
        }
    results = meerkatsvr.meerkat.getItems(params)
    if options.html:
        ## Example of how to iterate through the results and
        ## pull out chunks to stick into an HTML element
        for d in results:
            print "<A HREF=%s>%s</A>" % (d['link'],d['title'])
    else:
        pprint(results)

def main():
    usage = "usage: %prog [options] m(ethod)|ca(tegory)|ch(annel)|i(tem)"
    
    parser = OptionParser(usage)

    # define the command line options
    parser.add_option("-N", type="int", dest="category",
                      help="select the numeric ID of the category", metavar="NUM")
    parser.add_option("-n", type="int", dest="channel",
                      help="select the numeric ID of the channel", metavar="NUM")
    parser.add_option("-t", dest="time", default="10DAY",
                      help="choose a period of time (e.g. '1HOUR', '3DAY'); requires keyword 'item'")
    parser.add_option("-d", action="store_const", const="1", dest="dc", default="0",
                      help="use Dublin Core metadata; requires keyword 'item'")
    parser.add_option("-H", action="store_true", dest="html", default="",
                      help="produce HTML output; requires keyword 'item'")

    # parse the command line into options plus the keyword arg
    (options, args) = parser.parse_args()

    # no argument can be found
    if len(args) != 1: 
        parser.error("supply a keyword: 'method', 'category', 'channel' or 'item'")
    else:
        key = args[0]
    
        # key = "methods"
        if key.startswith("m"):
            pprint(meerkatsvr.system.listMethods())
        # key = "categories"
        elif key.startswith("ca"):
            pprint(meerkatsvr.meerkat.getCategories())
        # key = "channels"
        elif key.startswith("ch"):
            if options.category:
                pprint(meerkatsvr.meerkat.getChannelsByCategory(options.category))
            else:
                parser.error("supply a category number as -N NUM")
        # key = "items"
        elif key.startswith("i"):
           if options.channel:
               getitems(options)
           else:
                parser.error("supply a channel number as -n NUM")
        # we got an arg but didn't recognize it
        else:
            parser.error("use one of the following keywords: 'method', 'category', 'channel' or 'item'")


if __name__ == '__main__':
    main()

