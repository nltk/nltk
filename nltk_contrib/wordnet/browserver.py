# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# BrowServer is a server for browsing the NLTK Wordnet database
# It first launches a browser client to be used for browsing and
# then starts serving the requests of that and maybe other clients
#

import os
from sys import argv
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib import unquote_plus
import webbrowser
import datetime
import re

from browseutil import page_word, uniq_cntr

page = None
word = None
firstClient = True

# For storing the HTML pages
viewed_pages = {}
curr_page_num = 1
# For linking the unique counters to the numbers of the stored pages
uc_to_pn = {}

uc_pat = re.compile('(%23\d+">)')

def uc_updated_page(page, old_uc):
    '''
    Returns the page with old unique counters changeed to new ones
    '''
    page_parts = uc_pat.split(page)
    page = ''
    for part in page_parts:
        if part.startswith('%23') and part.endswith('">'):
            # Generate a new unique counter if this is an old counter
            if int(part[3:-2]) < old_uc:
                page += '%23' + str(uniq_cntr()) + '">'
            else:
                page += part
        else:
            page += part
    return page

class MyServerHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        #print 'dh'
        self.send_head()
        #print 'dh2'

    def do_GET(self):
        global page, word, firstClient
        global uc_to_pn, curr_page_num, viewed_pages
        #print 'path = ', self.path
        sp = self.path[1:]
        if unquote_plus(sp) == 'SHUTDOWN THE SERVER':
            print 'Server shutting down!'
            os._exit(0)

        if sp == 'favicon.ico':
            type = 'image/x-icon'
            page = open(sp).read()
        else:
            type = 'html'
            old_uc = uniq_cntr() # Trigger the update of old uc:s
            if sp == '': # We are starting
                if firstClient:
                    firstClient = False
                    page = open('index.html').read()
                else:
                    page = open('index_2.html').read()
                word = 'green'
            elif sp.endswith('.html'): # Trying to fetch a HTML file
                usp = unquote_plus(sp)
                if usp == 'NLTK Wordnet Browser Database Info.html':
                    word = '* Database Info *'
                    if os.path.isfile(usp):
                        page = open(usp).read()
                    else:
                        page = (html_header % word) + '<p>The database info file:'\
                            '<p><b>' + usp + '</b>' + \
                            '<p>was not found. Run this:' + \
                            '<p><b>python dbinfo_html.py</b>' + \
                               '<p>to produce it.' + html_trailer
                else:
                    if os.path.isfile(usp):
                        word = sp
                        page = open(usp).read()
                    else:
                        word = ''
                        page = (html_header % word) + '<p>The file:'\
                               '<p><b>' + usp + '</b>' + \
                               '<p>was not found.' + html_trailer
                        #self.send_error(404)
            else:
                #print '######################################################'
                #print 'SP==>', sp, '\n<==SP'
                #print '######################################################'
                # Grab the unique counter
                uc = int(sp[sp.rfind('%23') + 3:])
                # Page lookup needs not and cannot be done for the search words
                if uc:
                    if uc in uc_to_pn and uc_to_pn[uc] in viewed_pages:
                        page = viewed_pages[uc_to_pn[uc]]
                page,word = page_word(page, word, sp)
            page = uc_updated_page(page, old_uc)
            new_uc = uniq_cntr()
            for uc in range(old_uc, new_uc):
                uc_to_pn[uc] = curr_page_num
            viewed_pages[curr_page_num] = page
            curr_page_num += 1
        self.send_head(type)
        self.wfile.write(page)

    def send_head(self, textType=None):
        if textType == None:
            textType = 'plain'
        self.send_response(200)
        self.send_header('Content-type', 'text/' + textType)
        self.end_headers()

def demo():
    if len(argv) > 1:
        port = int(argv[1])
    else:
        port = 8000
    url = 'http://localhost:' + str(port)
    webbrowser.open(url, new = 2, autoraise = 1)
    server = HTTPServer(('', port), MyServerHandler)
    print 'NLTK Wordnet browser server running ... serving: ' + url
    server.serve_forever()


if __name__ == '__main__':
    demo()

