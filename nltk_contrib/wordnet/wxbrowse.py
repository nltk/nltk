# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au> (the original textual version)
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net> (the wxPython version)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

__version__ = "$Revision: 9 $"
# $Source$

from textwrap import TextWrapper
from random import randint
import  os
import  sys
from time import sleep
from threading import Timer
import itertools as it

import  wx
import  wx.html as  html
import  wx.lib.wxpTag

from util import *
from dictionary import *

# Relation names in the order they will displayed. The first item of a tuple
# is the internal i.e. DB name. The second item is the display name or if it
# contains parts separated by slashes,the parts are displayed as separate links.
rel_order = \
    [(HYPONYM,'direct hyponym/full hyponym'), (MEMBER_HOLONYM,MEMBER_HOLONYM),
     (PART_MERONYM,PART_MERONYM), (CLASS_CATEGORY,'domain term category'),
     (MEMBER_MERONYM,MEMBER_MERONYM),
     (HYPERNYM,'direct hypernym/inherited hypernym/sister term'),
     (PART_HOLONYM,PART_HOLONYM)]

def flatten(listOfLists):
    return list(it.chain(*listOfLists))

rel_disp_names = flatten([y.split('/') for x,y in rel_order])
#print rel_disp_names

def letter_to_pos(letter):
    return {'N':N, 'V':V, 'J':ADJ, 'R':ADV}[letter]

html_header = '''
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
        <html>
        <head>
        <meta name="generator" content=
        "HTML Tidy for Windows (vers 14 February 2006), see www.w3.org">
        <title></title>
        <meta http-equiv="Content-Type" content=
        "text/html; charset=us-ascii">
        </head>
        <body>
        '''

html_trailer = '''
        </body>
        </html>
        '''

explanation  = '''
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser shows you when you
enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b> i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links: word
links and others. Clicking a word link carries out a search for the word in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached to
that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
<li>Clicking on a relation name opens a section that displays the associated synsets.</li>
<li>Type a search word in the <b>Word</b> field and start the search by the <b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr width="100%">
'''

def b(txt): return '<b>%s</b>' % txt

def c(txt): return '<center>%s</center>' % txt

def h(n,txt): return '<h%d>%s</h%d>' % (n,txt,n)

def i(txt): return '<i>%s</i>' % txt

def li(txt): return '<li>%s</li>' % txt

def pg(body): return html_header + body + html_trailer

# abbc = asterisks, breaks, bold, center
def abbc(txt): return c(b('<br>'*10 + '*'*10 + ' ' + txt + ' ' + '*'*10))

# Link counter function is used to guarantee unique link refs
lnk_cnt = it.count().next

def collect_one(word, pos_letter, ind, synset):
    descr = {"N":"n", "V":"v", "J":"adj", "R":"adv"}[pos_letter]
    s = '<li><a href="' + pos_letter + word + '#' + str(ind)+ '#' + \
            str(lnk_cnt()) + '">S:</a>' + ' (' + descr + ') '
    for w in synset:
        if w.lower() == word:
            s+= b(w) + ', '
        else:
            s += '<a href="?' + w + '">' + w + '</a>, '
    s = s[:-2] + ' ('
    # Format the gloss part
    gl = ''
    hyph_not_found = True
    for g in synset.gloss.split('; '):
        if not g.startswith('"'):
            if gl: gl += '; '
            gl += g
        else:
            if hyph_not_found:
                gl += ') <i>'
                hyph_not_found = False
            else:
                gl += '; '
            gl += g
    if hyph_not_found: gl += ')'
    if not hyph_not_found: gl += '</i>'
    return s + gl + '</li>\n'

def collect_all(word, pos, pos_letter):
    s = '<ul>'
    for ind,synset in enumerate(pos[word]):
        s += collect_one(word, pos_letter, ind, synset)
    return s + '</ul>\n'

def rel_ref(link_type, word, synset_num, rel):
    return '<a href="*' + link_type + word + '#' + str(synset_num) + '#' + \
            rel + '#' + str(lnk_cnt()) + '"><i>' + rel + '</i></a>'

def synset_relations(link_type, word, synset_num):
    pos = letter_to_pos(link_type)
    synset = pos[word][synset_num]
    relations = synset.relations()
    #print relations
    
    html = ''
    for rel in rel_order:
        db_name,disp_name = rel
        if synset[db_name]:
            if len(rel) == 1:
                html += rel_ref(link_type, word, synset_num, db_name)
            else:
                lst = [' <i>/</i> ' + rel_ref(link_type, word, synset_num, r)
                       for r in disp_name.split('/')]
                html += ''.join(lst)[10:] # drop the extra ' <i>/</i> '
            html += '\n'
            del relations[db_name]
    for rel in relations.keys():
        html += rel_ref(link_type, word, synset_num, rel) + '\n'
    return html

def ul_structure(word, pos_letter, tree):
    #print 'IN, tree: ==>' + str(tree) + '<=='
    #htm = '<ul>\n<li>' + str(tree[0]) + '</li>\n'
    htm = '<ul>\n' + collect_one(word, pos_letter, 0, tree[0]) + '\n'
    if len(tree) == 2:
        #uls = ul_structure(word, pos_letter, tree[1:][0])
        #htm = htm[:-6] + uls + htm[-6:]
        htm += ul_structure(word, pos_letter, tree[1:][0])
        htm += '</ul>'
    elif len(tree) > 2:
        tree = tree[1:]
        #print 'HTM:', htm , '<=='; print 'TREE:', tree, '<=='
        for t in tree: htm += ul_structure(word, pos_letter, t) + '</ul>\n'
        htm += '</ul>'
        #print 'HTM:', htm , '<=='; print 'TREE:', tree, '<=='
    #print 'OUT, htm: ==>' + htm + '<=='
    return htm

def inherited_hypernym(word, pos_letter, synset_num):
    #print word
    #print synset_num
    #print N[word][synset_num]
    tree = N[word][synset_num].tree(HYPERNYM)
    return ul_structure(word, pos_letter, tree[1:][0]) + '</ul>'

def new_word_and_body(word='green'):
    #print '>' + word + '<'
    word = word.lower().replace('_', ' ')
    #print '>' + word + '<'
    body = ''
    name_dict = {"N":"Noun", "V":"Verb", "J":"Adjective", "R":"Adverb"}
    for pos,pos_ltr in ((N,"N"), (V,"V"), (ADJ,"J"), (ADV,"R")):
        if word in pos:
            body += h(5, name_dict[pos_ltr]) + '\n'
            body += collect_all(word, pos, pos_ltr)
    if not body:
        word = 'green'
        body = h(3, name_dict['N']) + '\n'
        body += collect_all(str(word), N, 'N')
    return word,body

def ul_section_removed(page, index):
    '''Removes from the html page the first string <ul>...stuff...</ul>.
    The search starts at index. Note: ...stuff... may contain embedded
    <ul>-</ul> pairs but the search continues to the </ul> that is the
    pair of the starting <ul>
    '''
    #print '==============>'+page[:index]+'################'+page[index:]
    ind = page.find('<ul>', index)
    #print '##'
    if ind == -1: return page
    #print '###'
    ul_count = 1
    ul_start = ind
    ind += 4
    while ul_count:
        #print '####',ul_count
        ind = page.find('ul>', ind)
        if ind == -1: return page
        if page[ind - 1] == '/': # </ul> found
            ul_count -= 1
            ul_end = ind + 3
        else:
            ul_count += 1
        ind += 3
    #print page[:ul_start] + '<\n' + '#'*50 + '\n>' + page[ul_start:ul_end] + \
    #        '<\n' + '#'*50 + '\n>' + page[ul_end:]
    return page[:ul_start] + page[ul_end:]


# This shows how to catch the OnLinkClicked non-event.  (It's a virtual
# method in the C++ code...)
class MyHtmlWindow(html.HtmlWindow):
    def __init__(self, parent, id):
        html.HtmlWindow.__init__(self, parent, id, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, linkinfo):
        href = linkinfo.GetHref()
        print 'OnLinkClicked: %s\n' % href
        link_type = href[0]
        link = href[1:]
        if link_type == '?': # one of the words in a synset
            word,body = new_word_and_body(link)
            self.parent.show_page_and_word(pg(body), word)
        elif link_type in 'VJR': # POS ;  like this until implemented
            self.show_msg(abbc('Not implemented yet!'))
            return
        elif link_type in 'NVJR': # POS
            # Word link looks like this:
            # word#synset_num#link_counter
            word,synset_num,cntr = link.split('#')
            synset_num = int(synset_num)
            page = self.GetParser().GetSource()
            ind = page.find(link) + len(link) + 2
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                page = page[:ind] + 'S:' + page[ind + 9:]
                self.parent.show_page_and_word(page)
            else:
                # Make this 'S:' bold on page
                page = page[:ind] + '<b>S:</b>' + page[ind + 2:]
                # Insert the relation names
                ind = page.find('\n', ind) + 1
                s_r = synset_relations(link_type, word, synset_num)
                s_r = s_r.split('\n')[:-1]
                s_r = ['<li>' + sr + '</li>' for sr in s_r]
                s_r = '<ul>\n' + '\n'.join(s_r) + '</ul>\n'
                #print 's_r:', s_r
                page = page[:ind] + s_r + page[ind:]
                self.parent.show_page_keep_position(page)
        elif link_type == '*': # Relation links
            # Relation link looks like this:
            # xword#synset_num#relation_name#link_counter where the first
            # position contains the pos. type letter i.e. one of N,V,J,R
            word,synset_num,rel_name,cntr = link.split('#')
            pos_letter = word[0]
            word = word[1:]
            synset_num = int(synset_num)
            if rel_name == 'inherited hypernym':
                page = self.GetParser().GetSource()
                ind = page.find(link) + len(link) + 2
                # If the link text is in bold, the user wants to
                # close the section beneath the link
                #print '******************'+page+'******************'
                #print page[ind:ind+3]
                if page[ind:ind+3] == '<b>':
                    page = ul_section_removed(page, ind)
                    #print '******************'+page+'******************'
                    page = page[:ind] + '<i>' + rel_name + \
                            '</i>' + page[ind + len(rel_name) + 14:]
                    #print '******************'+page+'******************'
                    self.parent.show_page_and_word(page)
                    #print '******************'+page+'******************'
                else:
                    # First we ought to do a check if another link
                    # is bold on the same line and if it is, then close the sect. ben.
                    # CHECK MISSING !!!!
                    # Make this selection bold on page
                    ind_2 = ind + len(rel_name) + 7
                    page = page[:ind] + b(page[ind:ind_2]) + \
                           page[ind_2:]
                    #print '===>', page
                    # find the start of the next line
                    ind = page.find('\n', ind) + 1
                    i_h = inherited_hypernym(word, pos_letter, synset_num)
                    #print 'page[:ind]======>' + page[:ind] + '<=====page[:ind]'
                    #print 'i_h======>' + i_h + '<=====i_h'
                    #print 'page[ind:]======>' + page[ind:] + '<=====page[ind:]'
                    page = page[:ind] + i_h + page[ind:]
                    self.parent.show_page_keep_position(page)
            else:
                self.show_msg(abbc('Not implemented yet!'))
                return
        else: # Very odd!
            self.show_msg(abbc('Not implemented yet!'))
        #super(MyHtmlWindow, self).OnLinkClicked(linkinfo)

    def OnSetTitle(self, title):
        pass
        #print 'OnSetTitle: %s\n' % title
        #super(MyHtmlWindow, self).OnSetTitle(title)

    def OnCellMouseHover(self, cell, x, y):
        #print 'OnCellMouseHover: %s, (%d %d)\n' % (cell, x, y)
        #super(MyHtmlWindow, self).OnCellMouseHover(cell, x, y)
        pass

    def OnCellClicked(self, cell, x, y, evt):
        '''
        print 'OnCellClicked: %s, (%d %d)\n' % (cell, x, y)
        if isinstance(cell, html.HtmlWordCell):
            sel = html.HtmlSelection()
            print '     %s\n' % cell.ConvertToText(sel)
        '''
        super(MyHtmlWindow, self).OnCellClicked(cell, x, y, evt)

    def show_body(self, body):
        self.SetPage(html_header + body + html_trailer)

    def show_page(self, page):
        self.SetPage(page)

    def show_help(self):
        self.parent.show_page_and_word(explanation, 'green')

    def show_msg(self, msg):
        def clear_error_msg():
            self.SetPage(self.page_to_restore)

        self.page_to_restore = self.GetParser().GetSource()
        self.show_page(pg(c(msg)))
        t = Timer(2.0, clear_error_msg)
        t.start()


# This filter doesn't really do anything but show how to use filters
class MyHtmlFilter(html.HtmlFilter):
    def __init__(self): 
        html.HtmlFilter.__init__(self)

    # This method decides if this filter is able to read the file
    def can_read(self, fsfile):
        print "can_read: %s\n" % fsfile.GetMimeType()
        return False

    # If CanRead returns True then this method is called to actually
    # read the file and return the contents.
    def read_file(self, fsfile):
        return ""


class HtmlPanel(wx.Panel):
    def __init__(self, frame):
        wx.Panel.__init__(self, frame, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.frame = frame
        self.cwd = os.path.split(sys.argv[0])[0]

        if not self.cwd:
            self.cwd = os.getcwd()
        if frame:
            self.titleBase = frame.GetTitle()

        html.HtmlWindow_AddFilter(MyHtmlFilter()) 

        self.html = MyHtmlWindow(self, -1)
        if "gtk2" in wx.PlatformInfo:
            self.html.SetStandardFonts()
        self.statusbar = self.frame.CreateStatusBar()
        self.html.SetRelatedFrame(frame, self.titleBase + " -- %s")
        self.html.SetRelatedStatusBar(0)
        # Init the word-page list for history browsing
        self.prev_wp_list = []
        self.next_wp_list = []
        #print '===========>', self.prev_wp_list

        self.printer = html.HtmlEasyPrinting()

        self.box = wx.BoxSizer(wx.VERTICAL)

        subbox_1 = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, -1, "Search the word")
        self.Bind(wx.EVT_BUTTON, self.on_search_word, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        lbl = wx.StaticText(self, -1, "Word: ", style=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        subbox_1.Add(lbl, 5, wx.GROW | wx.ALL, 2)

        self.search_word = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT, self.on_word_change, self.search_word)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_word_enter, self.search_word)
        self.search_word.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        subbox_1.Add(self.search_word, 20, wx.GROW | wx.ALL, 2)

        self.box.Add(subbox_1, 0, wx.GROW)
        self.box.Add(self.html, 1, wx.GROW)

        subbox_2 = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, -1, "Load File")
        self.Bind(wx.EVT_BUTTON, self.on_load_file, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Load URL")
        self.Bind(wx.EVT_BUTTON, self.on_load_url, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Help")
        self.Bind(wx.EVT_BUTTON, self.on_help, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Back")
        self.Bind(wx.EVT_BUTTON, self.on_back, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Forward")
        self.Bind(wx.EVT_BUTTON, self.on_forward, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Print")
        self.Bind(wx.EVT_BUTTON, self.on_print, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "View Source")
        self.Bind(wx.EVT_BUTTON, self.on_view_source, btn)
        subbox_2.Add(btn, 1, wx.GROW | wx.ALL, 2)

        self.box.Add(subbox_2, 0, wx.GROW)
        self.SetSizer(self.box)
        self.SetAutoLayout(True)

        #self.on_show_default(None)

    '''
    def on_show_default(self, event):
        name = os.path.join(self.cwd, opj('data/test.htm'))
        self.html.LoadPage(name)
    '''

    def on_load_file(self, event):
        self.html.show_msg(abbc('Not implemented yet!'))
        return
        dlg = wx.FileDialog(self, wildcard = '*.htm*', style=wx.OPEN)
        if dlg.ShowModal():
            path = dlg.GetPath()
            self.html.LoadPage(path)
        dlg.Destroy()

    def on_mouse_up(self, event):
        #print 'In on_mouse_up'
        self.search_word.SetSelection(-1, -1)
        event.Skip()

    def on_search_word(self, event):
        word,body = new_word_and_body(self.search_word.GetValue())
        self.show_page_and_word(pg(body), word)
        print 'In on_search_word: %s' % word

    def on_word_change(self, event):
        #print 'In on_word_change: %s' % self.search_word.GetValue()
        pass

    def on_word_enter(self, event):
        word,body = new_word_and_body(self.search_word.GetValue())
        self.show_page_and_word(pg(body), word)
        print 'In on_word_enter: %s' % word

    def on_load_url(self, event):
        self.html.show_msg(abbc('Not implemented yet!'))
        return
        dlg = wx.TextEntryDialog(self, "Enter a URL")
        if dlg.ShowModal():
            url = dlg.GetValue()
            self.html.LoadPage(url)
        dlg.Destroy()

    def on_help(self, event):
        self.html.show_help()

    def on_back(self, event):
        if self.prev_wp_list:
            # Save current word&page
            word = self.search_word.GetValue()
            page = self.html.GetParser().GetSource()
            self.next_wp_list = [(word,page)] + self.next_wp_list
            # Restore previous word&page
            word,page = self.prev_wp_list[-1]
            #print word, page
            self.search_word.SetValue(word)
            self.html.show_page(page)
            self.prev_wp_list = self.prev_wp_list[:-1]
        else:
            self.html.show_msg(abbc('At the start of page history already'))

    def on_forward(self, event):
        if self.next_wp_list:
            # Save current word&page
            word = self.search_word.GetValue()
            page = self.html.GetParser().GetSource()
            self.prev_wp_list = self.prev_wp_list + [(word,page)]
            # Restore next word&page
            word,page = self.next_wp_list[0]
            self.search_word.SetValue(word)
            self.html.SetPage(page)
            self.next_wp_list = self.next_wp_list[1:]
        else:
            self.html.show_msg(abbc('At the end of page history already!'))

    def on_view_source(self, event):
        import  wx.lib.dialogs
        source = self.html.GetParser().GetSource()
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, source, 'HTML Source', size=(1000, 800))
        dlg.ShowModal()
        dlg.Destroy()

    def on_print(self, event):
        self.printer.GetPrintData().SetPaperId(wx.PAPER_LETTER)
        self.printer.PrintFile(self.html.GetOpenedPage())

    def update_history(self):
        # Save current word&page
        w = self.search_word.GetValue()
        p = self.html.GetParser().GetSource()
        self.prev_wp_list = self.prev_wp_list + [(w,p)]
        # Clear forward history
        self.next_wp_list = []

    '''
        def show_page_and_word(self, page, word=None):
            # Save current word&page
            w = self.search_word.GetValue()
            p = self.html.GetParser().GetSource()
            self.prev_wp_list = self.prev_wp_list + [(w,p)]
            # Clear forward history
            self.next_wp_list = []
            # Show b&w
            self.html.show_page(page)
            if word: self.search_word.SetValue(word)
    '''

    def show_page_and_word(self, page, word=None):
        self.update_history()
        # Show p&w
        self.html.show_page(page)
        if word: self.search_word.SetValue(word)

    def show_page_keep_position(self, page):
        self.update_history()
        x,y = self.html.GetViewStart()
        self.html.SetPage(page)
        self.html.Scroll(x, y)


class MyHtmlFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title)
        self.panel = HtmlPanel(self)


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frm = MyHtmlFrame(None, "NLTK Wordnet Browser")
    word,body = new_word_and_body('green')
    frm.panel.search_word.SetValue(word)
    body = explanation + body
    frm.panel.html.show_page(pg(body))
    explanation = body
    frm.Show()
    frm.Maximize(True)
    frm.panel.html.show_msg(abbc(' UNDER CONSTRUCTION! ') + \
                            abbc(' SOME PARTS ARE NOT IMPLEMENTED YET! '))
    app.MainLoop()
