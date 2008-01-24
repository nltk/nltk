# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
import os
from sys import argv
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib import unquote_plus
import webbrowser

from browseutil import *

page = None
word = None
firstClient = True

def page_word(page, word, href):
        link_type = href[0]
        q_link = href[1:]
        u_link = unquote_plus(q_link)
        #print link_type, q_link, u_link
        if link_type == 'M' or link_type == 'N': # Search for this new word
            word,body = new_word_and_body(u_link)
            if word:
                return pg(word, body), word
            else:
                return pg(word, 'The word s%s" was not found!' % word), word
        elif link_type == 'R': # Relation links
            # A relation link looks like this:
            # word#synset_keys#relation_name#uniq_cntr
            #print 'u_link:', u_link
            word,synset_keys,rel_name,u_c = u_link.split('#')
            '''
            word = word.strip()
            synset_keys = synset_keys.strip()
            rel_name = rel_name.strip()
            u_c = u_c.strip()
            '''
            #print 'word,synset_keys,rel_name,u_c:',word,synset_keys,rel_name,u_c
            ind = page.find(q_link) + len(q_link) + 2
            #print page[ind:]
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                page = page[:ind] + '<i>' + rel_name + \
                        '</i>' + page[ind + len(rel_name) + 14:]
                return page, word
            else:
                # First check if another link is bold on the same line
                # and if it is, then remove boldness & close the section below
                end = page.find('\n', ind)
                start = page.rfind('\n', 0, ind)
                #print 'page[start:end]:', page[start:end]
                start = page.find('<b>', start, end)
                #print 'start:', start
                if start != -1:
                    page = ul_section_removed(page, ind)
                    end = page.find('</b>', start, end)
                    page = page[:start] + page[start+3:end] + page[end+4:]

                # Make this selection bold on page
                #
                if rel_name in implemented_rel_names:
                    ind = page.find(q_link) + len(q_link) + 2
                    ind_2 = ind + len(rel_name) + 7
                    #print 'page[:ind]:', page[:ind]
                    page = page[:ind] + bold(page[ind:ind_2]) + \
                           page[ind_2:]
                    # find the start of the next line
                    ind = page.find('\n', ind) + 1
                    section = \
                        relation_section(rel_name, word, synset_keys)
                    #print 'page[:ind]:', page[:ind]
                    page = page[:ind] + section + page[ind:]
                    return page, word
                else:
                    return None, None
        else:
            # A word link looks like this:
            # Wword#synset_key,prev_synset_key#link_counter
            # A synset link looks like this:
            # Sword#synset_key,prev_synset_key#link_counter
            l_t = link_type + ':'
            #print 'l_t, u_link:', l_t, u_link
            word,syns_keys,link_counter = u_link.split('#')
            #print 'word,syns_keys,link_counter:',word,syns_keys,link_counter
            #syns_key,prev_syns_key = syns_keys.split(',')
            ind = page.find(q_link) + len(q_link) + 2
            #print page[ind:]
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                #page = page[:ind] + 'S:' + page[ind + 9:]
                page = page[:ind] + l_t + page[ind + 9:]
                return page, word
            else: # The user wants to see the relation names
                # Make this link text bold on page
                #page = page[:ind] + bold('S:') + page[ind + 2:]
                page = page[:ind] + bold(l_t) + page[ind + 2:]
                # Insert the relation names
                ind = page.find('\n', ind) + 1
                # First remove the full_hyponym_cont_text if found here
                #print page[:ind+5] + '>>>>><<<<<' + page[ind+5:]
                if page[ind+5:].startswith(full_hyponym_cont_text):
                    page = page[0:ind+5] + \
                            page[ind+5+len(full_hyponym_cont_text):]
                #print page[:ind+5] + '>>>>><<<<<' + page[ind+5:]
                s_r = synset_relations(word, link_type, syns_keys)
                s_r = s_r.split('\n')[:-1]
                s_r = [li(sr) for sr in s_r]
                s_r = ul('\n' + '\n'.join(s_r) + '\n') + '\n'
                page = page[:ind] + s_r + page[ind:]
                return page, word


class MyServerHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        #print 'dh'
        self.send_head()
        #print 'dh2'

    def do_GET(self):
        global page, word, firstClient
        #print 'dg'
        sp = self.path[1:]
        #print 'path = ', sp
        #print 'headers = ', self.headers
        if sp == '':
            #print 'dg2'
            if firstClient:
                firstClient = False
                page = open('index.html').read()
            else:
                page = open('index_2.html').read()
            word = 'green'
        elif sp.endswith('.html'):
            #print 'dg3'
            page = open(unquote_plus(sp)).read()
            word = 'green'
        elif unquote_plus(sp) == 'SHUTDOWN THE SERVER':
            #print 'Server shutting down!'
            os._exit(0)
        else:
            #print 'dg4'
            page,word = page_word(page, word, sp)
        self.send_head('html')
        self.wfile.write(page)
        #print 'dg4'
        #print 'The request was: ' + sp

    def send_head(self, textType=None):
        #print 'sh'
        if textType == None:
            textType = 'plain'
        #print 'sh2'
        self.send_response(200)
        #print 'sh3'
        self.send_header('Content-type', 'text/' + textType)
        #print 'sh4'
        self.end_headers()

if len(argv) > 1:
    port = int(argv[1])
else:
    port = 8000
url = 'http://localhost:' + str(port)
webbrowser.open(url, new = 2, autoraise = 1)
server = HTTPServer(('', port), MyServerHandler)
print 'NLTK Wordnet browser server running ... serving: ' + url
server.serve_forever()
