# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
BrowServer is a server for browsing the NLTK Wordnet database It first
launches a browser client to be used for browsing and then starts
serving the requests of that and maybe other clients

Usage:
    browserver.py -h
    browserver.py [-s] [-p <port>]

Options:

    -h or --help
        Display this help message.

    -p <port> or --port <port>
        Run the web server on this TCP port, defaults to 8000.

    -s or --server-mode
        Do not start a web browser, and do not allow a user to
        shotdown the server through the web interface.
"""

import os
from sys import argv
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib import unquote_plus
import webbrowser
import datetime
import re
import threading
import time
import getopt

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

# True if we're not also running a web browser.  The value f server_mode
# gets set by demo().
server_mode = None 

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
        self.send_head()

    def do_GET(self):
        global page, word, firstClient
        global uc_to_pn, curr_page_num, viewed_pages
        sp = self.path[1:]
        if unquote_plus(sp) == 'SHUTDOWN THE SERVER':
            if server_mode:
                page = "Server must be killed with SIGTERM."
                type = "text/plain"
            else:
                print 'Server shutting down!'
                os._exit(0)

        elif sp == 'favicon.ico':
            type = 'image/x-icon'
            page = open(sp).read()
            
        elif sp == '': # First request.
            type = 'text/html'
            old_uc = uniq_cntr() # Trigger the update of old uc:s
            if not server_mode and firstClient:
                firstClient = False
                page = open('index.html').read()
            else:
                page = open('index_2.html').read()
            word = 'green'
        
        elif sp.endswith('.html'): # Trying to fetch a HTML file
            type = 'text/html'
            old_uc = uniq_cntr() # Trigger the update of old uc:s
            usp = unquote_plus(sp)
            if usp == 'NLTK Wordnet Browser Database Info.html':
                word = '* Database Info *'
                if os.path.isfile(usp):
                    page = open(usp).read()
                else:
                    page = (html_header % word) + \
                        '<p>The database info file:'\
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
        else:
            type = 'text/html'
            old_uc = uniq_cntr() # Trigger the update of old uc:s
            
            # Handle search queries.
            if sp.startswith("search"):
                parts = (sp.split("?")[1]).split("&")
                word = [p.split("=")[1] 
                          for p in parts if p.startswith("nextWord")][0]
                sp = "M%s%%23%d" % (word, 0)
            
            uc = get_unique_counter_from_url(sp)
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
        
        # Send result.
        self.send_head(type)
        self.wfile.write(page)


    def send_head(self, type=None):
        self.send_response(200)
        self.send_header('Content-type', type)
        self.end_headers()


def get_unique_counter_from_url(sp):
    """
    Extract the unique counter from the URL if it has one.  Otherwise return
    null.
    """
    pos = sp.rfind('%23')
    if pos != -1:
        return int(sp[(pos + 3):])
    else:
        return None


def demo(port=8000, runBrowser=True):
    """
    Run NLTK Wordnet Browser Server.
    
    @param port: The port number for the server to listen on, defaults to
                 8000
    @type  port: C{int}

    @param runBrowser: True to start a web browser and point it at the web
                       server.
    @type  runBrowser: C{boolean}
    """
    # The webbrowser module is unpredictable, typically it blocks if it uses
    # a console web browser, and doesn't block if it uses a GUI webbrowser,
    # so we need to force it to have a clear correct behaviour.
    # 
    # Normally the server should run for as long as the user wants. they
    # should idealy be able to control this from the UI by closing the
    # window or tab.  Second best would be clicking a button to say
    # 'Shutdown' that first shutsdown the server and closes the window or
    # tab, or exits the text-mode browser.  Both of these are unfreasable.
    #
    # The next best alternative is to start the server, have it close when
    # it receives SIGTERM (default), and run the browser as well.  The user
    # may have to shutdown both programs.
    #
    # Since webbrowser may block, and the webserver will block, we must run
    # them in seperate threads.
    #
    global server_mode
    server_mode = not runBrowser

    url = 'http://localhost:' + str(port)
    if runBrowser:
        server_ready = threading.Event()
        browser_thread = startBrowser(url, server_ready)

    server = HTTPServer(('', port), MyServerHandler)
    print 'NLTK Wordnet browser server running ... serving: ' + url
    if runBrowser:
        server_ready.set()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    
    if runBrowser:
        browser_thread.join()


def startBrowser(url, server_ready):
    def run():
        server_ready.wait()
        time.sleep(1) # Wait a little bit more, there's still the chance of
                      # a race condition.
        webbrowser.open(url, new = 2, autoraise = 1)
    t = threading.Thread(target=run)
    t.start()
    return t


def usage():
    """
    Display the command line help message.
    """
    print __doc__


if __name__ == '__main__':
    # Parse and interpret options.
    (opts, _) = getopt.getopt(argv[1:], "p:sh", ["port=", "server-mode", "help"])
    port = 8000
    server_mode = False
    help_mode = False
    for (opt, value) in opts:
        if (opt == "-p") or (opt == "--port"):
            port = int(value)
        elif (opt == "-s") or (opt == "--server-mode"):
            server_mode = True
        elif (opt == "-h") or (opt == "--help"):
            help_mode = True

    if help_mode:
        usage()
    else:
        demo(port, not server_mode)
