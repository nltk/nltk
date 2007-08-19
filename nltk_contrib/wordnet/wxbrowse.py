# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

__version__ = "$Revision: 9 $"
# $Source$

import  os
import  os.path
import  sys
from time import sleep
from threading import Timer
import itertools as it
import  sys
from collections import defaultdict
from pprint import pprint
import pickle
import gc

import  wx
import  wx.html as  html
import  wx.lib.wxpTag

from util import *
from dictionary import *
from morphy import morphy

__all__ = ["demo"]

frame_title = "NLTK Wordnet Browser"
help_about = frame_title + \
"""

Copyright (C) 2007 University of Pennsylvania

Author: Jussi Salmela <jtsalmela@users.sourceforge.net>

URL: <http://nltk.sf.net>

For license information, see LICENSE.TXT
"""

# This is used to memorize the synsets handled
syns_mem = {}
# This is used to save options in and to be pickled at exit
options_dict = {}
pickle_file_name = frame_title + ".pkl"

implemented_rel_names = \
    ["direct hyponym", "full hyponym", "direct hypernym", "inherited hypernym",
     "verb group", "domain term category", "domain category", "domain region",
     "instance", "has instance", "part meronym", "member meronym",
     "member holonym", "part holonym", "attribute", "direct troponym",
     "full troponym"
    ]

# Relation names in the order they will displayed. The first item of a tuple
# is the internal i.e. DB name. The second item is the display name or if it
# contains parts separated by slashes, the parts are displayed as separate
# links.
rel_order = \
    [(HYPONYM,"direct hyponym/full hyponym"), #OK
     (HYPONYM,"direct troponym/full troponym"), #OK
     (PART_HOLONYM,PART_MERONYM), #OK
     (ATTRIBUTE,ATTRIBUTE), #OK
     #substance holo
     #substance mero
     (MEMBER_MERONYM,MEMBER_HOLONYM), #OK
     (MEMBER_HOLONYM,MEMBER_MERONYM), #OK
     (VERB_GROUP,VERB_GROUP), #OK
     #direct tropo/full tropo
     (CLASSIF_CATEGORY, CLASSIF_CATEGORY), #OK
     (INSTANCE_HYPONYM, "has instance"), #OK
     (CLASS_CATEGORY,"domain term category"), #OK
     (HYPERNYM,"direct hypernym/inherited hypernym/sister term"), #OK - (sister term)
     (CLASSIF_REGIONAL, CLASSIF_REGIONAL), #OK
     (PART_MERONYM,PART_HOLONYM), #OK
     (INSTANCE_HYPERNYM, "instance") #OK
     #cause
     #similar to
     #antonym
     #derivationally related form
     #sentence frame
     ]

def dispname_to_dbname(dispname):
    for dbn,dispn in rel_order:
        if dispname in dispn.split("/"):
            return dbn
    return None

def dbname_to_dispname(dbname):
    for dbn,dispn in rel_order:
        if dbn == dbname:
            return dispn
    return "???"

html_header = """
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
        <html>
        <head>
        <meta name="generator" content=
        "HTML Tidy for Windows (vers 14 February 2006), see www.w3.org">
        <meta http-equiv="Content-Type" content=
        "text/html; charset=us-ascii">
        </head>
        <body bgcolor="#F5F5F5" text="#000000">
        """


html_trailer = """
        </body>
        </html>
        """

explanation  = """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr width="100%">
"""

# HTML oriented functions

def b(txt): return "<b>%s</b>" % txt

def c(txt): return "<center>%s</center>" % txt

def h(n,txt): return "<h%d>%s</h%d>" % (n,txt,n)

def i(txt): return "<i>%s</i>" % txt

def li(txt): return "<li>%s</li>" % txt

def pg(body): return html_header + body + html_trailer

# abbc = asterisks, breaks, bold, center
def abbc(txt): return c(b("<br>"*10 + "*"*10 + " " + txt + " " + "*"*10))

# This counter function is used to guarantee unique counter values
uniq_cntr = it.count().next

def collect_one(word, synset):
    #descr = {"N":"n", "V":"v", "J":"adj", "R":"adv"}[pos_letter]
    u_c = uniq_cntr()
    syns_mem[u_c] = synset
    descr = synset.pos if synset.pos.startswith("ad") else synset.pos[0]
    s = '<li><a href="' + word + "#" + \
            str(u_c) + '">S:</a>' + " (" + descr + ") "
    for w in synset:
        w = w.replace("_", " ")
        if w.lower() == word:
            s+= b(w) + ", "
        else:
            s += '<a href="?' + w + '">' + w + "</a>, "
    s = s[:-2] + " ("
    # Format the gloss part
    gl = ""
    hyph_not_found = True
    for g in synset.gloss.split("; "):
        if not g.startswith('"'):
            if gl: gl += "; "
            gl += g
        else:
            if hyph_not_found:
                gl += ") <i>"
                hyph_not_found = False
            else:
                gl += "; "
            gl += g
    if hyph_not_found: gl += ")"
    if not hyph_not_found: gl += "</i>"
    return s + gl + "</li>\n"

def collect_all(word, pos):
    s = "<ul>"
    for synset in pos[word]:
        s += collect_one(word, synset)
    return s + "</ul>\n"

def rel_ref(word, synset_counter, rel):
    return '<a href="*' + word + "#" + str(synset_counter) + "#" + \
            rel + '"><i>' + rel + "</i></a>"

def synset_relations(word, synset_counter):
    synset = syns_mem[synset_counter]
    rel_keys = synset.relations().keys()

    html = ""
    for rel in rel_order:
        db_name,disp_name = rel
        print db_name, disp_name
        if db_name == HYPONYM:
            if synset.pos == "verb":
                if disp_name.find("tropo") == -1:
                    continue
            else:
                if disp_name.find("hypo") == -1:
                    continue
        if synset[db_name]:
            if len(rel) == 1:
                html += rel_ref(word, synset_counter, db_name)
            else:
                lst = [" <i>/</i> " + rel_ref(word, synset_counter, r)
                       for r in disp_name.split("/")]
                html += "".join(lst)[10:] # drop the extra " <i>/</i> "
            html += "\n"
            if db_name in rel_keys: rel_keys.remove(db_name)
    for rel in rel_keys:
        html += rel_ref(word, synset_counter, rel) + "\n"
    return html

def hyponym_ul_structure(word, tree):
    if tree == []: return ""
    head = tree[0]
    tail = tree[1:]
    htm = collect_one(word, head[0]) + "\n"
    if len(head) > 1:
        htm += "<ul>"
        htm += hyponym_ul_structure(word, head[1:])# + "</ul>\n"
        htm += "</ul>"
    htm += hyponym_ul_structure(word, tail)
    return htm

def hypernym_ul_structure(word, tree):
    htm = "<ul>\n" + collect_one(word, tree[0]) + "\n"
    if len(tree) > 1:
        tree = tree[1:]
        for t in tree: htm += hypernym_ul_structure(word, t)# + "</ul>\n"
        htm += "</ul>\n"
    return htm

def relation_section(rel_name, word, synset_cntr):
    synset = syns_mem[synset_cntr]
    if rel_name == "full hyponym":
        tree = synset.tree(HYPONYM)
        return "<ul>\n" + hyponym_ul_structure(word, tree[1:]) + "</ul>"
    elif rel_name == "inherited hypernym":
        tree = synset.tree(HYPERNYM)
        return hypernym_ul_structure(word, tree[1:][0]) + "</ul>"
    else:
        rel = dispname_to_dbname(rel_name)
        s = ""
        for x in synset[rel]:
            s += collect_one(word, x)
        return "<ul>" + s + "</ul>"

def new_word_and_body(word):
    word = word.lower().replace("_", " ")

    pos_forms = defaultdict(set)
    for pos_str in ["noun", "verb", "adj", "adv"]:
        for form in morphy(word, pos=pos_str):
            pos_forms[pos_str].add(form)
    body = ""
    for pos,pos_str,name in \
        ((N,"noun","Noun"), (V,"verb","Verb"),
         (ADJ,"adj","Adjective"), (ADV,"adv","Adverb")):
        if pos_str in pos_forms:
            body += h(3, name) + "\n"
            form_list = list(pos_forms[pos_str])
            if word in form_list:
                form_list.remove(word)
                form_list = [word] +  form_list
            for form in form_list:
                body += collect_all(form, pos)
    if not body:
        word = None
    return word,body

def ul_section_removed(page, index):
    """Removes the first string <ul>...stuff...</ul> from the html page.
    The search starts at index. Note: ...stuff... may contain embedded
    <ul>-</ul> pairs but the search continues to the </ul> that is the
    pair of the starting <ul>
    """
    ind = page.find("<ul>", index)
    if ind == -1: return page
    ul_count = 1
    ul_start = ind
    ind += 4
    while ul_count:
        ind = page.find("ul>", ind)
        if ind == -1: return page
        if page[ind - 1] == "/": # </ul> found
            ul_count -= 1
            ul_end = ind + 3
        else:
            ul_count += 1
        ind += 3
    return page[:ul_start] + page[ul_end:]


class MyHtmlWindow(html.HtmlWindow):
    def __init__(self, parent, id):
        html.HtmlWindow.__init__(self, parent, id,
                                    style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()
        self.font_size = self.normal_font_size = \
                         options_dict["font_size"]
        self.incr_decr_font_size(0) # Keep it as it is

    def OnLinkClicked(self, linkinfo):
        href = linkinfo.GetHref()
        tab_to_return_to = None
        if linkinfo.Event.ControlDown():
            if linkinfo.Event.ShiftDown():
                        self.parent.add_html_page(activate=True)
            else:
                tab_to_return_to = self.parent.current_page
                self.parent.add_html_page(activate=True)
        link_type = href[0]
        link = href[1:]
        if link_type == "?": # one of the words in a synset
            word,body = new_word_and_body(link)
            if word:
                self.parent.SetPageText(self.parent.current_page, word)
                self.parent.parent.show_page_and_word(pg(body), word)
            else:
                self.parent.parent.show_msg(abbc("The word was not found!"))
        elif link_type == "*": # Relation links
            # A relation link looks like this:
            # word#synset_num#relation_name#link_counter
            word,synset_cntr,rel_name = link.split("#")
            synset_cntr = int(synset_cntr)
            page = self.GetParser().GetSource()
            ind = page.find(link) + len(link) + 2
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == "<b>":
                page = ul_section_removed(page, ind)
                page = page[:ind] + "<i>" + rel_name + \
                        "</i>" + page[ind + len(rel_name) + 14:]
                self.parent.parent.show_page_and_word(page)
            else:
                # First check if another link is bold on the same line
                # and if it is, then remove boldness & close the section below
                end = page.find("\n", ind)
                start = page.rfind("\n",0,ind)
                start = page.find("<b>", start, end)
                if start != -1:
                    page = ul_section_removed(page, ind)
                    end = page.find("</b>", start, end)
                    page = page[:start] + page[start+3:end] + page[end+4:]

                # Make this selection bold on page
                #
                #print rel_name, implemented_rel_names
                if rel_name in implemented_rel_names:
                    ind = page.find(link) + len(link) + 2
                    ind_2 = ind + len(rel_name) + 7
                    page = page[:ind] + b(page[ind:ind_2]) + \
                           page[ind_2:]
                    # find the start of the next line
                    ind = page.find("\n", ind) + 1
                    section = \
                        relation_section(rel_name, word, synset_cntr)
                    page = page[:ind] + section + page[ind:]
                    self.parent.parent.show_page_and_word(page)
                else:
                    self.show_msg(abbc("Not implemented yet!"))
        else:
            # POS. A word link looks like this: word#synset_counter
            link = href
            word,syns_cntr = link.split("#")
            syns_cntr = int(syns_cntr)
            page = self.GetParser().GetSource()
            ind = page.find(link) + len(link) + 2
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == "<b>":
                page = ul_section_removed(page, ind)
                page = page[:ind] + "S:" + page[ind + 9:]
                self.parent.parent.show_page_and_word(page)
            else:
                # Make this "S:" bold on page
                page = page[:ind] + "<b>S:</b>" + page[ind + 2:]
                # Insert the relation names
                ind = page.find("\n", ind) + 1
                s_r = synset_relations(word, syns_cntr)
                s_r = s_r.split("\n")[:-1]
                s_r = ["<li>" + sr + "</li>" for sr in s_r]
                s_r = "<ul>\n" + "\n".join(s_r) + "</ul>\n"
                page = page[:ind] + s_r + page[ind:]
                self.parent.parent.show_page_and_word(page)
        """
        else:
            print "We should be in a Help Window now! Are we?"
            super(MyHtmlWindow, self).OnLinkClicked(linkinfo)
        """
        if tab_to_return_to is not None:
            self.parent.SetSelection(tab_to_return_to)

    def OnSetTitle(self, title):
        pass
        #super(MyHtmlWindow, self).OnSetTitle(title)

    def OnCellMouseHover(self, cell, x, y):
        #super(MyHtmlWindow, self).OnCellMouseHover(cell, x, y)
        pass

    def OnOpeningURL(self, type, url):
        #super(MyHtmlWindow, self).OnCellMouseHover(cell, x, y)
        pass

    def OnCellClicked(self, cell, x, y, evt):
        linkinfo = cell.GetLink()
        if linkinfo is not None:
            #html.HtmlCellEvent.SetLinkClicked(True)
            #evt.SetLinkClicked(True)
            pass
        else:
            pass
        super(MyHtmlWindow, self).OnCellClicked(cell, x, y, evt)

    def incr_decr_font_size(self, change=None):
        global options_dict
        page_to_restore = self.GetParser().GetSource()
        if change:
            self.font_size += change
            if self.font_size <= 0: self.font_size = 1
        else:
            self.font_size  = self.normal_font_size
        options_dict["font_size"] = self.font_size
        # Font size behavior is very odd. This is a hack
        self.SetFonts("times new roman", "courier new", [self.font_size]*7)
        self.SetPage(page_to_restore)

    def show_body(self, body):
        self.SetPage(html_header + body + html_trailer)

    def show_help(self):
        self.parent.parent.show_page_and_word(explanation, "green")

    def show_msg(self, msg):
        def clear_error_msg():
            self.SetPage(self.page_to_restore)
        self.page_to_restore = self.GetParser().GetSource()
        self.show_page(pg(c(msg)))
        t = Timer(2.0, clear_error_msg)
        t.start()

    def show_page(self, page):
        self.SetPage(page)


#----------------------------------------------------------------------------
class NB(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, -1, size=(21,21), style=
                             wx.BK_DEFAULT
                             #wx.BK_TOP
                             #wx.BK_BOTTOM
                             #wx.BK_LEFT
                             #wx.BK_RIGHT
                             # | wx.NB_MULTILINE
                             )
        self.parent = parent
        self.add_html_page()
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)

    def OnPageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        if old != new: #  and self.current_page != new:
            self.current_page = new
            self.ChangeSelection(new)
            self.h_w = self.GetPage(new)
            self.parent.search_word.SetValue(self.h_w.current_word)
        event.Skip()

    def OnPageChanging(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()

    def add_html_page(self, tab_text="", activate=True):
        h_w = MyHtmlWindow(self, -1)
        if "gtk2" in wx.PlatformInfo:
            h_w.SetStandardFonts()
        h_w.SetRelatedFrame(self.parent.frame, self.parent.titleBase + " -- %s")
        h_w.SetRelatedStatusBar(0)
        h_w.current_word = ""
        # Init the word-page list for history browsing
        h_w.prev_wp_list = []
        h_w.next_wp_list = []
        self.AddPage(h_w, tab_text, activate)
        if activate:
            self.current_page = self.GetSelection()
            self.h_w = h_w
        return self.current_page


class HtmlPanel(wx.Panel):
    def __init__(self, frame):
        wx.Panel.__init__(self, frame, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.frame = frame
        self.cwd = os.path.split(sys.argv[0])[0]

        if not self.cwd:
            self.cwd = os.getcwd()
        if frame:
            self.titleBase = frame.GetTitle()

        self.statusbar = self.frame.CreateStatusBar()

        self.printer = html.HtmlEasyPrinting(frame_title)

        self.box = wx.BoxSizer(wx.VERTICAL)

        subbox_1 = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, -1, "Previous Page")
        self.Bind(wx.EVT_BUTTON, self.on_prev_page, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Next Page")
        self.Bind(wx.EVT_BUTTON, self.on_next_page, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Help")
        self.Bind(wx.EVT_BUTTON, self.on_help, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, "Search the word")
        self.Bind(wx.EVT_BUTTON, self.on_word_enter, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        lbl = wx.StaticText(self, -1, "Word: ",
                            style=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        subbox_1.Add(lbl, 5, wx.GROW | wx.ALL, 2)

        self.search_word = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        #self.Bind(wx.EVT_TEXT, self.on_word_change, self.search_word)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_word_enter, self.search_word)
        self.search_word.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        subbox_1.Add(self.search_word, 20, wx.GROW | wx.ALL, 2)

        self.box.Add(subbox_1, 0, wx.GROW)
        self.nb = NB(self)
        self.box.Add(self.nb, 1, wx.GROW)
        
        self.SetSizer(self.box)
        self.SetAutoLayout(True)

    def on_prev_page(self, event):
        if self.nb.h_w.prev_wp_list:
            # Save current word&page
            page = self.nb.h_w.GetParser().GetSource()
            self.nb.h_w.next_wp_list = [(self.nb.h_w.current_word,page)] + \
                                        self.nb.h_w.next_wp_list
            # Restore previous word&page
            word,page = self.nb.h_w.prev_wp_list[-1]
            self.nb.h_w.prev_wp_list = self.nb.h_w.prev_wp_list[:-1]
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
            self.search_word.SetValue(word)
            self.nb.h_w.show_page(page)
        else:
            self.nb.h_w.show_msg(abbc("At the start of page history already"))

    def on_next_page(self, event):
        if self.nb.h_w.next_wp_list:
            # Save current word&page
            page = self.nb.h_w.GetParser().GetSource()
            self.nb.h_w.prev_wp_list.append((self.nb.h_w.current_word,page))
            # Restore next word&page
            word,page = self.nb.h_w.next_wp_list[0]
            self.nb.h_w.next_wp_list = self.nb.h_w.next_wp_list[1:]
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
            self.search_word.SetValue(word)
            self.nb.h_w.SetPage(page)
        else:
            self.nb.h_w.show_msg(abbc("At the end of page history already!"))

    def on_help(self, event):
        self.frame.on_help_help(None)

    def on_mouse_up(self, event):
        self.search_word.SetSelection(-1, -1)
        event.Skip()

    def on_word_change(self, event):
        word = self.search_word.GetValue()
        if word.isalnum(): return
        word_2 = "".join([x for x in word if
                            x.isalnum() or x == " " or x == "-"])
        self.search_word.SetValue(word_2)
        event.Skip()

    def on_word_enter(self, event):
        if not self.nb.GetPageCount():
            self.frame.on_ssw_nt(None)
            return
        word = self.search_word.GetValue()
        word = word.strip()
        if word == "": return
        word,body = new_word_and_body(word)
        if word:
            self.show_page_and_word(pg(body), word)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
        else:
            self.nb.h_w.show_msg(abbc("The word was not found!"))
            
    def update_history(self):
        if self.nb.h_w.current_word:
            # Save current word&page
            page = self.nb.h_w.GetParser().GetSource()
            self.nb.h_w.prev_wp_list.append((self.nb.h_w.current_word,page))
            # Clear forward history
            self.nb.h_w.next_wp_list = []

    def show_page_and_word(self, page, word=None):
        self.update_history()
        if not word: x,y = self.nb.h_w.GetViewStart()
        self.nb.h_w.SetPage(page)
        if not word: self.nb.h_w.Scroll(x, y)
        if word:
            self.search_word.SetValue(word)
            self.nb.h_w.current_word = word


class MyHtmlFrame(wx.Frame):
    def __init__(self, parent, title): #, pos, size)
        wx.Frame.__init__(self, parent, -1, title)#, pos, size)

        menu_bar = wx.MenuBar()

        menu_1 = wx.Menu()
        o_f = menu_1.Append(-1, "Open File...\tCtrl+O")
        s_a = menu_1.Append(-1, "Save Page As...\tCtrl+S")
        menu_1.AppendSeparator()
        print_ = menu_1.Append(-1, "Print...\tCtrl+P")
        preview = menu_1.Append(-1, "Preview")
        menu_1.AppendSeparator()
        ex = menu_1.Append(-1, "Exit")
        menu_bar.Append(menu_1, "&File")

        menu_1_2 = wx.Menu()
        nt = menu_1_2.Append(-1, "New tabsheet\tCtrl+T")
        ct = menu_1_2.Append(-1, "Close tabsheet\tCtrl+W")
        menu_1_2.AppendSeparator()
        ssw_nt = menu_1_2.Append(-1, "Show search word in new tabsheet\tAlt+Enter")
        menu_bar.Append(menu_1_2, "&Tabsheets")

        menu_2 = wx.Menu()
        prev_p = menu_2.Append(-1, "Previous\tCtrl+Left Arrow")
        next_p = menu_2.Append(-1, "Next\tCtrl+Right Arrow")
        menu_bar.Append(menu_2, "&Page History")

        menu_3 = wx.Menu()
        i_f = menu_3.Append(-1,
                "Increase Font Size\tCtrl++ or Ctrl+Numpad+ or Ctrl+UpArrow")
        d_f = menu_3.Append(-1,
            "Decrease Font Size\tCtrl+-  or Ctrl+Numpad-  or Ctrl+DownArrow")
        n_f = menu_3.Append(-1, "Normal Font Size\tCtrl+0")
        menu_3.AppendSeparator()
        s_s = menu_3.Append(-1, "Show HTML Source\tCtrl+U")
        menu_bar.Append(menu_3, "&View")

        menu_4 = wx.Menu()
        h_h = menu_4.Append(-1, "Help")
        h_a = menu_4.Append(-1, "About...")
        menu_bar.Append(menu_4, "&Help")

        self.SetMenuBar(menu_bar)

        self.Bind(wx.EVT_MENU, self.on_open_file, o_f)
        self.Bind(wx.EVT_MENU, self.on_save_as, s_a)
        self.Bind(wx.EVT_MENU, self.on_print, print_)
        self.Bind(wx.EVT_MENU, self.on_preview, preview)
        self.Bind(wx.EVT_MENU, self.on_exit, ex)
        self.Bind(wx.EVT_MENU, self.on_new_tab, nt)
        self.Bind(wx.EVT_MENU, self.on_close_tab, ct)
        self.Bind(wx.EVT_MENU, self.on_ssw_nt, ssw_nt)
        self.Bind(wx.EVT_MENU, self.on_prev_page, prev_p)
        self.Bind(wx.EVT_MENU, self.on_next_page, next_p)
        self.Bind(wx.EVT_MENU, self.on_incr_font, i_f)
        self.Bind(wx.EVT_MENU, self.on_decr_font, d_f)
        self.Bind(wx.EVT_MENU, self.on_norm_font, n_f)
        self.Bind(wx.EVT_MENU, self.on_show_source, s_s)
        self.Bind(wx.EVT_MENU, self.on_help_help, h_h)
        self.Bind(wx.EVT_MENU, self.on_help_about, h_a)

        acceltbl = wx.AcceleratorTable([
                            (wx.ACCEL_CTRL,ord("O"),o_f.GetId()),
                            (wx.ACCEL_CTRL,ord("S"),s_a.GetId()),
                            (wx.ACCEL_CTRL,ord("P"),print_.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_ADD,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_NUMPAD_ADD,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_UP,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_SUBTRACT,d_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_NUMPAD_SUBTRACT,d_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_DOWN,d_f.GetId()),
                            (wx.ACCEL_CTRL,ord("0"),n_f.GetId()),
                            (wx.ACCEL_CTRL,ord("U"),s_s.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_LEFT,prev_p.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_RIGHT,next_p.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_RETURN,ssw_nt.GetId()),
                            ])
        self.SetAcceleratorTable(acceltbl)

        self.Bind(wx.EVT_SIZE, self.on_frame_resize)
        self.Bind(wx.EVT_MOVE, self.on_frame_move)
        self.Bind(wx.EVT_CLOSE, self.on_frame_close)

        self.panel = HtmlPanel(self)

    def  on_frame_close(self, event):
        pos = self.GetPosition()
        size = self.GetSize()
        options_dict["frame_pos"] = pos
        options_dict["frame_size"] = size
        pkl = open(pickle_file_name, "wb")
        pickle.dump(options_dict, pkl, -1)
        pkl.close()
        event.Skip()

    def  on_frame_resize(self, event):
        event.Skip()

    def  on_frame_move(self, event):
        event.Skip()

    def  on_open_file(self, event):
        self.load_file()

    def  on_open_URL(self, event):
        self.load_url()

    def  on_save_as(self, event):
        self.save_file()

    def  on_print(self, event):
        self.print_()

    def  on_preview(self, event):
        self.preview()

    def  on_exit(self, event):
        self.Close()

    def  on_new_tab(self, event):
        current_page = self.panel.nb.add_html_page()

    def  on_close_tab(self, event):
        self.panel.nb.DeletePage(self.panel.nb.current_page)

    def  on_ol_ut(self, event):
        pass

    def  on_ol_ft(self, event):
        pass

    def  on_ssw_nt(self, event):
        word = self.panel.search_word.GetValue()
        if word == "": return
        current_page = self.panel.nb.add_html_page()
        word,body = new_word_and_body(word)
        if word:
            self.panel.show_page_and_word(pg(body), word)
            self.panel.nb.h_w.current_word = word
            self.panel.nb.SetPageText(current_page, word)
        else:
            self.panel.nb.h_w.show_msg(abbc("The word was not found!"))
            
    def  on_prev_page(self, event):
        self.panel.on_prev_page(event)

    def  on_next_page(self, event):
        self.panel.on_next_page(event)

    def  on_incr_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size(+1)

    def  on_decr_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size(-1)

    def  on_norm_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size()

    def  on_show_source(self, event):
        self.show_source()

    def  on_help_help(self, event):
        self.read_file("NLTK Wordnet Browser Help.html")
        
    def  on_help_about(self, event):
        wx.MessageBox(help_about)

    def read_file(self, path):
        try:
            if not path.endswith(".htm") and not path.endswith(".html"):
                path += ".html"
            f = open(path)
            page = f.read()
            f.close()
            if path == "NLTK Wordnet Browser Help.html":
                word = "* Help *"
            else:
                txt = "<title>" + frame_title + " display for the word: "
                ind_0 = page.find(txt)
                if ind_0 == -1:
                    err_mess = "This file is not in NLTK Browser format!"
                    self.panel.nb.h_w.show_msg(abbc(err_mess))
                    return
                ind_1 = page.find("word: ") + len("word: ")
                ind_2 = page.find("</title>")
                word = page[ind_1:ind_2]
                page = page[:ind_0] + page[ind_2+len("</title>"):]
            current_page = self.panel.nb.add_html_page()
            self.panel.nb.SetPageText(current_page,word)
            self.panel.show_page_and_word(page, word)
            return current_page
        except:
            excpt = str(sys.exc_info())
            self.panel.nb.h_w.show_msg(abbc("Unexpected error; File: " + \
                                                path + " ; " + excpt))

    def load_file(self):
        dlg = wx.FileDialog(self, wildcard = "*.htm*",
                            style=wx.OPEN|wx.CHANGE_DIR)
        if dlg.ShowModal():
            path = dlg.GetPath()
            if path == "": return
            self.read_file(path)
        dlg.Destroy()

    def save_file(self):
        dlg = wx.FileDialog(self, wildcard = "*.htm*",
                            style=wx.SAVE|wx.CHANGE_DIR|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal():
            path = dlg.GetPath()
            if path == "":
                self.panel.nb.h_w.show_msg(abbc("Empty Filename!"))
                return
            source = self.panel.nb.h_w.GetParser().GetSource()
            try:
                if not path.endswith(".htm") and not path.endswith(".html"):
                    path += ".html"
                f = open(path, "w")
                txt = "<title>" + frame_title + " display for the word: " + \
                      self.panel.nb.h_w.current_word  + "</title></head>"
                source = source.replace("</head>", txt)
                f.write(source)
                f.close()
            except:
                excpt = str(sys.exc_info())
                self.panel.nb.h_w.show_msg(abbc("Unexpected error; File: " + \
                                                    path + " ; " + excpt))
            dlg.Destroy()

    def load_url(self):
        dlg = wx.TextEntryDialog(self, "Enter the URL")
        if dlg.ShowModal():
            url = dlg.GetValue()
            self.panel.nb.h_w.LoadPage(url)
        dlg.Destroy()

    def show_source(self):
        import  wx.lib.dialogs
        source = self.panel.nb.h_w.GetParser().GetSource()
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, source,
                                             "HTML Source", size=(1000, 800))
        dlg.ShowModal()
        dlg.Destroy()

    def print_(self):
        self.panel.printer.GetPrintData().SetFilename("onnaax ???")
        html = self.panel.nb.h_w.GetParser().GetSource()
        self.panel.printer.PrintText(html)

    def preview(self):
        html = self.panel.nb.h_w.GetParser().GetSource()
        self.panel.printer.PreviewText(html)

def initalize_options():
    global options_dict
    if os.path.exists(pickle_file_name):
        pkl = open(pickle_file_name, "rb")
        options_dict = pickle.load(pkl)
        pkl.close()
    else:
        options_dict = {}
    if "font_size" not in options_dict:
        options_dict["font_size"] = 11
    if "frame_pos" not in options_dict:
        options_dict["frame_pos"] = (-1,-1)
    if "frame_size" not in options_dict:
        options_dict["frame_size"] = (-1,-1)

def adjust_pos_and_size(frame):
    # Try to catch the screen dimensions like this because no better
    # method is known i.e. start maximized, get the dims, adjust if
    # pickled info requires
    max_width,max_height = frame.GetSize()
    x,y = frame.GetPosition()
    # The following assumes that, as it seems, when wxPython frame
    # is created maximized, it is symmetrically oversized the same
    # amount of pixels. In my case (WinXP, wxPython 2.8) x==y==-4
    # and the width and  height are 8 pixels too large. In the
    # frame init it is not possible to give negative values except
    # (-1,-1) which has the special meaning of using the default!
    if x < 0:
        max_width += 2 * x
        x = 0
    if y < 0:
        max_height += 2 * y
        y = 0
    # If no pos_size_info was found pickled, we're OK
    if options_dict["frame_pos"] == (-1,-1):
        return
    # Now let's try to assure we've got sane values
    x,y = options_dict["frame_pos"]
    width,height = options_dict["frame_size"]
    if x < 0:
        width += x
        x = 0
    if y < 0:
        height += y
        y = 0
    width = min(width, max_width)
    height = min(height, max_height)
    if x + width > max_width:
        x -= x + width - max_width
        if x < 0:
            width += x
            width = min(width, max_width)
            x = 0
    if y + height > max_height:
        y -= y + height - max_height
        if y < 0:
            height += y
            height = min(height, max_height)
            y = 0
    frame.Maximize(False)
    frame.SetSize((width,height))
    frame.SetPosition((x,y))

def demo():
    global explanation
    global options_dict

    app = wx.PySimpleApp()
    initalize_options()
    frm = MyHtmlFrame(None, frame_title)#, -1, -1)
    word,body = new_word_and_body("green")
    frm.panel.nb.SetPageText(0,word)
    frm.panel.nb.h_w.current_word  = word
    frm.panel.search_word.SetValue(word)
    body = explanation + body
    frm.panel.nb.h_w.show_page(pg(body))
    page = frm.panel.nb.h_w.GetParser().GetSource()
    page = frm.panel.nb.GetPage(0).GetParser().GetSource()
    explanation = body
    frm.Show()
    frm.Maximize(True)
    frm.panel.nb.h_w.show_msg(abbc(" UNDER CONSTRUCTION! ") + \
                            abbc(" SOME PARTS ARE NOT IMPLEMENTED YET! "))
    adjust_pos_and_size(frm)
    app.MainLoop()


if __name__ == "__main__":
    demo()
