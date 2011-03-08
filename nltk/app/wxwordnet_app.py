# Wordnet Interface: Graphical Wordnet Browser
# 
# Copyright (C) 2001-2011 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@students.csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Wordnet Interface: Graphical Wordnet Browser

    python wxbrowse.py
    
    This has a GUI programmed using wxPython and thus needs wxPython
    to be installed.

    Features of wxbrowse.py:

     - A short help display at the start
     - Notebook UI: tabsheets with independent search histories
     - Menu
     - File functions: page save&open, print&preview
     - Tabsheet functions: open&close; start word search in a new tabsheet
     - Page history: previous&next page
     - Font size adjustment: increase&decrease&normalize
     - Show Database Info:
       - counts of words/synsets/relations for every POS
       - example words as hyperlinks, 1 word for every relation&POS pair
     - Help
     - The position and size of the browser window and the font size
       chosen is remembered between sessions.
     - Possibility to give several words/collocations to be searched
       and displayed at the same time by separating them with a comma
       in search word(s) field
     - Tries to deduce the stems of the search word(s) given
     - Showing the parts of speech for a word typed in the search field
     - Showing the parts of speech for a word clicked in one of the
       synsets
     - Showing the relation names for a synset when S: is clicked and
       hiding them again at the second click.
     - Showing the synsets for a relation. This covers most of the
       relations for nouns and some relations for other POS's also.
"""

import os
import os.path
import sys
from time import sleep
import pickle
import platform
from urllib import quote_plus, unquote_plus
from itertools import groupby

import wx
import wx.html as  html
import wx.lib.wxpTag

from wordnet_app import page_from_word, new_word_and_body, show_page_and_word,\
     html_header, html_trailer, get_static_page_by_path,\
     explanation, pg  


#
# Comments within this code indicate future work.  These comments are
# marked with 'XXX'
#


# XXX: write these global constants in shouting case.
#
# Additionally, through-out this module docstrings should be entered.
#


frame_title = 'NLTK Wordnet Browser'
help_about = frame_title + __doc__

# This is used to save options in and to be pickled at exit
options_dict = {}

try:
    nltk_prefs_dir = os.path.join(os.environ['HOME'], ".nltk")
except KeyError:
    # XXX: This fallback may have problems on windows.
    nltk_prefs_dir = os.path.curdir
pickle_file_name = os.path.join(nltk_prefs_dir, 
                                (frame_title + os.path.extsep + 'pkl'))

### XXX: MUST find a standard location for the stats HTML page,
###      perhapsw in NLTK_DATA.

WORDNET_DB_INFO_FILEPATH = 'NLTK Wordnet Browser Database Info.html' 



class MyHtmlWindow(html.HtmlWindow):
    def __init__(self, parent, id):
        html.HtmlWindow.__init__(self, parent, id,
                                    style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        self.font_size = self.normal_font_size = \
                         options_dict['font_size']
        self.incr_decr_font_size(0) # Keep it as it is

    def OnLinkClicked(self, linkinfo):
        href = linkinfo.GetHref()
        tab_to_return_to = None
        word = self.parent.parent.search_word.GetValue()
        if linkinfo.Event.ControlDown():
            if linkinfo.Event.ShiftDown():
                self.parent.add_html_page(activate=True)
            else:
                tab_to_return_to = self.parent.current_page
                self.parent.add_html_page(activate=True)
        self.parent.SetPageText(self.parent.current_page, word)
        self.parent.parent.search_word.SetValue(word)
        page,word = page_from_word(word, href)
        if page:
            if word:
                self.parent.SetPageText(self.parent.current_page, word)
                self.parent.parent.show_page_and_word(page, word)
            else:
                self.show_msg('The word was not found!')
                self.parent.parent.show_page_and_word(page)
        else:
            self.show_msg('Relation "%s" is not implemented yet!' % rel_name)

        # XXX: MAY simplfy the if predicate. */
        if tab_to_return_to is not None:
            self.parent.switch_html_page(tab_to_return_to)

    def OnSetTitle(self, title):
        "no-op"
        pass

    def OnCellMouseHover(self, cell, x, y):
        "no-op"
        pass

    def OnOpeningURL(self, type, url):
        "no-op"
        pass

    def OnCellClicked(self, cell, x, y, evt):
        linkinfo = cell.GetLink()
        if linkinfo is not None:
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
        options_dict['font_size'] = self.font_size
        self.SetStandardFonts(size=self.font_size)
        self.SetPage(page_to_restore)

    def show_msg(self, msg):
        msg1 = '*'*8 + '   ' + msg + '   ' + '*'*8
        msg2 = '*'*100
        for i in range(5):
            for msg in [msg1, msg2]:
                self.parent.parent.statusbar.SetStatusText(msg)
                wx.Yield()
                sleep(0.2)
        self.parent.parent.statusbar.SetStatusText(' ')
        wx.Yield()

    def show_page(self, page):
        self.SetPage(page)


#----------------------------------------------------------------------------
class NB(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, -1, size=(21,21),
                             style=wx.BK_DEFAULT)

        self.parent = parent
        self.add_html_page()
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)

    def OnPageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        if old != new: #  and self.current_page != new:
            self.switch_html_page(new)
        event.Skip()

# XXX: MAY remove three statments with no effect. */
    def OnPageChanging(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()

    def switch_html_page(self, new_page):
        self.current_page = new_page
        self.ChangeSelection(new_page)
        self.h_w = self.GetPage(new_page)
        self.parent.prev_btn.Enable(self.h_w.prev_wp_list != [])
        self.parent.next_btn.Enable(self.h_w.next_wp_list != [])
        self.parent.search_word.SetValue(self.h_w.current_word)

    def add_html_page(self, tab_text='', activate=True):
        h_w = MyHtmlWindow(self, -1)
        if 'gtk2' in wx.PlatformInfo:
            h_w.SetStandardFonts()
        h_w.SetRelatedFrame(self.parent.frame, 
                            self.parent.titleBase + ' -- %s')
        h_w.SetRelatedStatusBar(0)
        h_w.current_word = ''
        # Init the word-page list for history browsing
        h_w.prev_wp_list = []
        h_w.next_wp_list = []
        self.AddPage(h_w, tab_text, activate)
        if activate:
            self.current_page = self.GetSelection()
            self.h_w = h_w
            if self.h_w.prev_wp_list == []:
                self.parent.prev_btn.Enable(False)
            if self.h_w.next_wp_list == []:
                self.parent.next_btn.Enable(False)
        return self.current_page


class HtmlPanel(wx.Panel):
    def __init__(self, frame):
        wx.Panel.__init__(self, frame, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.frame = frame
# XXX: MAY simplify setting self.cwdJust use os.getcwd(). */
        self.cwd = os.path.split(sys.argv[0])[0]

        if not self.cwd:
            self.cwd = os.getcwd()
        if frame:
            self.titleBase = frame.GetTitle()

        self.statusbar = self.frame.CreateStatusBar()

        self.printer = html.HtmlEasyPrinting(frame_title)

        self.box = wx.BoxSizer(wx.VERTICAL)

        subbox_1 = wx.BoxSizer(wx.HORIZONTAL)

        self.prev_btn = wx.Button(self, -1, 'Previous Page')
        self.Bind(wx.EVT_BUTTON, self.on_prev_page, self.prev_btn)
        subbox_1.Add(self.prev_btn, 5, wx.GROW | wx.ALL, 2)

        self.next_btn = wx.Button(self, -1, 'Next Page')
        self.Bind(wx.EVT_BUTTON, self.on_next_page, self.next_btn)
        subbox_1.Add(self.next_btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, 'Help')
        self.Bind(wx.EVT_BUTTON, self.on_help, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, 'Search the word(s)')
        self.Bind(wx.EVT_BUTTON, self.on_word_enter, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        lbl = wx.StaticText(self, -1, 'Word(s): ',
                            style=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        subbox_1.Add(lbl, 5, wx.GROW | wx.ALL, 2)

        self.search_word = wx.TextCtrl(self, -1, '', style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_word_enter, self.search_word)
        self.search_word.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        subbox_1.Add(self.search_word, 20, wx.GROW | wx.ALL, 2)

        self.box.Add(subbox_1, 0, wx.GROW)
        self.nb = NB(self)
        self.box.Add(self.nb, 1, wx.GROW)

        self.SetSizer(self.box)
        self.SetAutoLayout(True)

    def on_key_down(self, event):
        event.Skip()

    def on_key_up(self, event):
        event.Skip()

    def on_char(self, event):
        event.Skip()

    def on_mouse_up(self, event):
        self.search_word.SetSelection(-1, -1)
        event.Skip()

    def on_prev_page(self, event):
        if self.nb.h_w.prev_wp_list:
            # Save current word&page&viewStart
            page = self.nb.h_w.GetParser().GetSource()
            x,y = self.nb.h_w.GetViewStart()
            entry = (self.nb.h_w.current_word,page,(x,y))
            self.nb.h_w.next_wp_list = [entry] + self.nb.h_w.next_wp_list
            self.next_btn.Enable(True)
            # Restore previous word&page
            word,page,(x,y) = self.nb.h_w.prev_wp_list[-1]
            self.nb.h_w.prev_wp_list = self.nb.h_w.prev_wp_list[:-1]
            if self.nb.h_w.prev_wp_list == []:
                self.prev_btn.Enable(False)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
            self.search_word.SetValue(word)
            self.nb.h_w.SetPage(page)
            self.nb.h_w.Scroll(x, y)

    def on_next_page(self, event):
        if self.nb.h_w.next_wp_list:
            # Save current word&page&viewStart
            page = self.nb.h_w.GetParser().GetSource()
            x,y = self.nb.h_w.GetViewStart()
            entry = (self.nb.h_w.current_word,page,(x,y))
            self.nb.h_w.prev_wp_list.append(entry)
            self.prev_btn.Enable(True)
            # Restore next word&page
            word,page,(x,y) = self.nb.h_w.next_wp_list[0]
            self.nb.h_w.next_wp_list = self.nb.h_w.next_wp_list[1:]
            if self.nb.h_w.next_wp_list == []:
                self.next_btn.Enable(False)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
            self.search_word.SetValue(word)
            self.nb.h_w.SetPage(page)
            self.nb.h_w.Scroll(x, y)

    def on_help(self, event):
        self.frame.on_help_help(None)

    def on_word_change(self, event):
        word = self.search_word.GetValue()
        if word.isalnum(): return
        word_2 = ''.join([x for x in word if
                            x.isalnum() or x == ' ' or x == '-'])
        self.search_word.SetValue(word_2)
        event.Skip()

    def on_word_enter(self, event):
        if not self.nb.GetPageCount():
            self.frame.on_ssw_nt(None)
            return
        word = self.search_word.GetValue()
        word = word.strip()
        if word == '': return
        word,body = new_word_and_body(word)
        if word:
            self.show_page_and_word(pg(word, body), word)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
        else:
            self.nb.h_w.show_msg('The word was not found!')

    def show_page_and_word(self, page, word=None):
        if self.nb.h_w.current_word:
            # Save current word&page&viewStart
            curr_page = self.nb.h_w.GetParser().GetSource()
            x,y = self.nb.h_w.GetViewStart()
            entry = (self.nb.h_w.current_word,curr_page,(x,y))
            self.nb.h_w.prev_wp_list.append(entry)
            self.prev_btn.Enable(True)
            # Clear forward history
            self.nb.h_w.next_wp_list = []
            self.next_btn.Enable(False)
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
        o_f = menu_1.Append(-1, 'Open File...\tCtrl+O')
        s_a = menu_1.Append(-1, 'Save Page As...\tCtrl+S')
        menu_1.AppendSeparator()
        print_ = menu_1.Append(-1, 'Print...\tCtrl+P')
        preview = menu_1.Append(-1, 'Preview')
        menu_1.AppendSeparator()
        ex = menu_1.Append(-1, 'Exit')
        menu_bar.Append(menu_1, '&File')

        menu_1_2 = wx.Menu()
        nt = menu_1_2.Append(-1, 'New tabsheet\tCtrl+T')
        ct = menu_1_2.Append(-1, 'Close tabsheet\tCtrl+W')
        menu_1_2.AppendSeparator()
        ssw_nt = menu_1_2.Append(-1, 
                                 'Show search word in new tabsheet\tAlt+Enter')
        menu_bar.Append(menu_1_2, '&Tabsheets')

        menu_2 = wx.Menu()
        prev_p = menu_2.Append(-1, 'Previous\tCtrl+Left Arrow')
        next_p = menu_2.Append(-1, 'Next\tCtrl+Right Arrow')
        menu_bar.Append(menu_2, '&Page History')

        menu_3 = wx.Menu()
        i_f = menu_3.Append(-1,
                'Increase Font Size\tCtrl++ or Ctrl+Numpad+ or Ctrl+UpArrow')
        d_f = menu_3.Append(-1,
            'Decrease Font Size\tCtrl+-  or Ctrl+Numpad-  or Ctrl+DownArrow')
        n_f = menu_3.Append(-1, 'Normal Font Size\tCtrl+0')
        menu_3.AppendSeparator()
# The Database Info File is not supported in this version.
#        db_i = menu_3.Append(-1, 'Show Database Info')
#        menu_3.AppendSeparator()
        s_s = menu_3.Append(-1, 'Show HTML Source\tCtrl+U')
        menu_bar.Append(menu_3, '&View')

        menu_4 = wx.Menu()
        h_h = menu_4.Append(-1, 'Help')
        h_a = menu_4.Append(-1, 'About...')
        menu_bar.Append(menu_4, '&Help')

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
# The Database Info File is not supported in this version.
#        self.Bind(wx.EVT_MENU, self.on_db_info, db_i)
        self.Bind(wx.EVT_MENU, self.on_show_source, s_s)
        self.Bind(wx.EVT_MENU, self.on_help_help, h_h)
        self.Bind(wx.EVT_MENU, self.on_help_about, h_a)

        acceltbl = wx.AcceleratorTable([
                            (wx.ACCEL_CTRL,ord('O'),o_f.GetId()),
                            (wx.ACCEL_CTRL,ord('S'),s_a.GetId()),
                            (wx.ACCEL_CTRL,ord('P'),print_.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_ADD,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_NUMPAD_ADD,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_UP,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_SUBTRACT,d_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_NUMPAD_SUBTRACT,d_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_DOWN,d_f.GetId()),
                            (wx.ACCEL_CTRL,ord('0'),n_f.GetId()),
                            (wx.ACCEL_CTRL,ord('U'),s_s.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_LEFT,prev_p.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_LEFT,prev_p.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_RIGHT,next_p.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_RIGHT,next_p.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_RETURN,ssw_nt.GetId()),
                            ])

        self.SetAcceleratorTable(acceltbl)

        self.Bind(wx.EVT_SIZE, self.on_frame_resize)
        self.Bind(wx.EVT_MOVE, self.on_frame_move)
        self.Bind(wx.EVT_CLOSE, self.on_frame_close)

        self.panel = HtmlPanel(self)


    def on_key_down(self, event):
        event.Skip()

    def on_key_up(self, event):
        event.Skip()

    def on_frame_close(self, event):
        pos = self.GetPosition()
        size = self.GetSize()
        if pos == (-32000, -32000): # The frame is minimized, ignore pos
            pos = (0,0)
        options_dict['frame_pos'] = pos
        options_dict['frame_size'] = size
        if not os.access(nltk_prefs_dir, os.F_OK):
            os.mkdir(nltk_prefs_dir)
        pkl = open(pickle_file_name, 'wb')
        pickle.dump(options_dict, pkl, -1)
        pkl.close()
        event.Skip()

    def on_frame_resize(self, event):
        event.Skip()

    def on_frame_move(self, event):
        event.Skip()

    def on_open_file(self, event):
        self.load_file()

    def on_open_URL(self, event):
        self.load_url()

    def on_save_as(self, event):
        self.save_file()

    def on_print(self, event):
        self.print_()

    def on_preview(self, event):
        self.preview()

    def on_exit(self, event):
        self.Close()

    def on_new_tab(self, event):
        current_page = self.panel.nb.add_html_page()

    def on_close_tab(self, event):
        self.panel.nb.DeletePage(self.panel.nb.current_page)

    def on_ol_ut(self, event):
        pass

    def on_ol_ft(self, event):
        pass

    def on_ssw_nt(self, event):
        word = self.panel.search_word.GetValue()
        if word == '': return
        current_page = self.panel.nb.add_html_page()
        word,body = new_word_and_body(word)
        if word:
            self.panel.show_page_and_word(pg(word, body), word)
            self.panel.nb.h_w.current_word = word
            self.panel.nb.SetPageText(current_page, word)
        else:
            self.panel.nb.h_w.show_msg('The word was not found!')

    def on_prev_page(self, event):
        self.panel.on_prev_page(event)

    def on_next_page(self, event):
        self.panel.on_next_page(event)

    def on_incr_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size(+1)

    def on_decr_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size(-1)

    def on_norm_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size()

    def on_db_info(self, event):
        self.show_db_info()

    def on_show_source(self, event):
        self.show_source()

    def on_help_help(self, event):
        self.read_file('wx_help.html')

    def on_help_about(self, event):
        wx.MessageBox(help_about)

    def show_db_info(self):
        word = '* Database Info *'
        current_page = self.panel.nb.add_html_page()
        self.panel.nb.SetPageText(current_page,word)
        try:
            file = open(WORDNET_DB_INFO_FILEPATH)
            html = file.read()
            file.close()
        except IOError:
            # TODO: Should give instructions for using dbinfo_html.py
            html = (html_header % word) + '<p>The database info file:'\
                   '<p><b>%s</b>' % WORDNET_DB_INFO_FILEPATH + \
                   '<p>was not found. Run the <b>dbinfo_html.py</b> ' + \
                   'script to produce it.' + html_trailer
        self.panel.show_page_and_word(html, word)
        return

    # These files need to be placed in a known location.
    def read_file(self, path):
        try:
            if not path.endswith('.htm') and not path.endswith('.html'):
                path += '.html'
            page = get_static_page_by_path(path)
            if path == 'NLTK Wordnet Browser Help.html':
                word = '* Help *'
            else:
                txt = '<title>' + frame_title + ' display of: '
                ind_0 = page.find(txt)
                if ind_0 == -1:
                    err_mess = 'This file is not in NLTK Browser format!'
                    self.panel.nb.h_w.show_msg(err_mess)
                    return
                ind_1 = page.find('of: ') + len('of: ')
                ind_2 = page.find('</title>')
                word = page[ind_1:ind_2]
                page = page[:ind_0] + page[ind_2+len('</title>'):]
            current_page = self.panel.nb.add_html_page()
            self.panel.nb.SetPageText(current_page,word)
            self.panel.show_page_and_word(page, word)
            return current_page
        except:
            excpt = str(sys.exc_info())
            self.panel.nb.h_w.show_msg('Unexpected error; File: ' + \
                                                path + ' ; ' + excpt)

    def load_file(self):
        dlg = wx.FileDialog(self, wildcard = '*.htm*',
                            style=wx.OPEN|wx.CHANGE_DIR)
        if dlg.ShowModal():
            path = dlg.GetPath()
            if path == '': return
            self.read_file(path)
        dlg.Destroy()

    def save_file(self):
        dlg = wx.FileDialog(self, wildcard='*.html',
                            style=wx.SAVE|wx.CHANGE_DIR|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal():
            path = dlg.GetPath()
            if path == '':
                self.panel.nb.h_w.show_msg('Empty Filename!')
                return
            source = self.panel.nb.h_w.GetParser().GetSource()
            try:
                if not path.endswith('.htm') and not path.endswith('.html'):
                    path += '.html'
                f = open(path, 'w')
                f.write(source)
                f.close()
            except:
                excpt = str(sys.exc_info())
                self.panel.nb.h_w.show_msg('Unexpected error; File: ' + \
                                                    path + ' ; ' + excpt)
            dlg.Destroy()

    def load_url(self):
        dlg = wx.TextEntryDialog(self, 'Enter the URL')
        if dlg.ShowModal():
            url = dlg.GetValue()
            self.panel.nb.h_w.LoadPage(url)
        dlg.Destroy()

    def show_source(self):
        import  wx.lib.dialogs
        source = self.panel.nb.h_w.GetParser().GetSource()
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, source,
                                             'HTML Source', size=(1000, 800))
        dlg.ShowModal()
        dlg.Destroy()

    def print_(self):
        self.panel.printer.GetPrintData().SetFilename('unnamed')
        html = self.panel.nb.h_w.GetParser().GetSource()
        self.panel.printer.PrintText(html)

    def preview(self):
        html = self.panel.nb.h_w.GetParser().GetSource()
        self.panel.printer.PreviewText(html)

def _initalize_options():
    global options_dict
    if os.path.exists(pickle_file_name):
        pkl = open(pickle_file_name, 'rb')
        options_dict = pickle.load(pkl)
        pkl.close()
    else:
        options_dict = {}
    if 'font_size' not in options_dict:
        options_dict['font_size'] = 11
    if 'frame_pos' not in options_dict:
        options_dict['frame_pos'] = (-1,-1)
    if 'frame_size' not in options_dict:
        options_dict['frame_size'] = (-1,-1)

def _adjust_pos_and_size(frame):
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
    if options_dict['frame_pos'] == (-1,-1):
        return
    # Now let's try to assure we've got sane values
    x,y = options_dict['frame_pos']
    width,height = options_dict['frame_size']
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
    frame.Iconize(False)

def get_static_wx_help_page():
    """
    Return static WX help page.
    """
    return \
"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2011 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <http://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <head>
          <meta http-equiv='Content-Type' content='text/html; charset=us-ascii'>
          <title>NLTK Wordnet Browser display of: * Help *</title>
     </head>
<body bgcolor='#F5F5F5' text='#000000'>
<h2>NLTK Wordnet Browser Help</h2>
<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database. The NLTK Wordnet Browser has only a part of normal browser functionality and it is <b>not</b> an Internet browser.</p>
<p>For background information on Wordnet, see the Wordnet project home page: <b>http://wordnet.princeton.edu/</b>. For more information on the NLTK project, see the project home: <b>http://nltk.sourceforge.net/</b>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>
<h3>The User Interface</h3>
<p>The user interface is a so called <b>notebook</b> interface. This
is familiar nowadays for almost everyone from Internet browsers,
for example. It consists of one or more independent pages often
(and here also) called <b>tabsheets</b>.</p>
<p>Every tabsheet contains its own search history which can be
browsed back and forth at will. The result of a new word search
will be shown on the currently active tabsheet if nothing else is
wanted. It is also possible to open a new tabsheet for the search
word given.</p>
<p>The position and size of the browser window as well as font size can be adjusted and the selections are retained between sessions.</p>
<h3>Word search</h3>
<p>The word to be searched is typed into the <b>Word(s):</b> field and the search started with Enter or by clicking the <b>Search the word(s)</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>
<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions. Typing <b>fLIeS</b> as an obscure example gives one <a href="MfLIeS">this</a>. Click the previous link to see what this kind of search looks like and then come back to this page by clicking the <b>Previous Page</b> button.</p>
<p>The result of a search is a display of one or more
<b>synsets</b> for every part of speech in which a form of the
search word was found to occur. A synset is a set of words
having the same sense or meaning. Each word in a synset that is
underlined is a hyperlink which can be clicked to trigger an
automatic search for that word.</p>
<p>Every synset has a hyperlink <b>S:</b> at the start of its
display line. Clicking that symbol shows you the name of every
<b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again. Clicking another relation name on a line that has an opened relation closes the open relation and opens the clicked relation.</p>
<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma like this <a href="Mcheer up,clear up">cheer up,clear up</a>, for example. Click the previous link to see what this kind of search looks like and then come back to this page by clicking the <b>Previous Page</b> button. As you could see the search result includes the synsets found in the same order than the forms were given in the search field.</p>
<p>
There are also word level (lexical) relations recorded in the Wordnet database. Opening this kind of relation displays lines with a hyperlink <b>W:</b> at their beginning. Clicking this link shows more info on the word in question.</p>
<h3>Menu Structure</h3>
The browser has a menubar that you can use to invoke a set of
different operations. Most of the menu selections also have a
corresponding keyboard shortcut.
<h4>The File Menu</h4>
<p>Using the file menu you can <b>open</b> a previously saved NLTK
Wordnet Browser page. Note that only pages saved with this browser
can be read.</p>
<p>And as indicated above you can <b>save</b> a search page. The
resulting file is a normal HTML mode file which can be viewed,
printed etc. as any other HTML file.</p>
<p>You can also <b>print</b> a page and <b>preview</b> a page to be
printed. The selected printing settings are remembered during the
session.</p>
<h4>The Tabsheets Menu</h4>
<p>You can <b>open an empty tabsheet</b> and <b>close</b> the
currently active tabsheet.</p>
<p>When you enter a new search word in the search word field you
can make the search result be shown in a <b>new tabsheet</b>.</p>
<h4>Page History</h4>
You can browse the page history of the currently active tabsheet
either <b>forwards</b> or <b>backwards</b>. <b>Next Page</b>
browses towards the newer pages and <b>Previous Page</b> towards
the older pages.
<h4>The View Menu</h4>
<p>You can <b>increase</b>, <b>decrease</b> and <b>normalize</b>
the font size. The font size chosen is retained between
sessions.</p>
<p>You can choose <b>Show Database Info</b> to see the word, synset and relation counts by POS as well as one example word (as a hyperlink) for every relation&amp;POS pair occuring.</p>
<p>You can view the <b>HTML source</b> of a page if you are
curious.</p>
<h4>The Help Menu</h4>
You can view this <b>help text</b> as you already know. The
<b>about</b> selection tells you something about the program.
<h3>The Keyboard Shortcuts</h3>
<p>The following keyboard shortcuts can be used to quickly launch
the desired operation.</p>
<table border="1" cellpadding="1" cellspacing="1" summary="">
<col align="center">
<col align="center">
<tr>
<th>Keyboard Shortcut</th>
<th>Operation</th>
</tr>
<tr>
<td>Ctrl+O</td>
<td>Open a file</td>
</tr>
<tr>
<td>Ctrl+S</td>
<td>Save current page as</td>
</tr>
<tr>
<td>Ctrl+P</td>
<td>Print current page</td>
</tr>
<tr>
<td>Ctrl+T</td>
<td>Open a new (empty) tabsheet</td>
</tr>
<tr>
<td>Ctrl+W</td>
<td>Close the current tabsheet</td>
</tr>
<tr>
<td>Ctrl+LinkClick</td>
<td>Open the link in a new unfocused tabsheet</td>
</tr>
<tr>
<td>Ctrl+Shift+LinkClick</td>
<td>Opent the link in a new focused tabsheet</td>
</tr>
<tr>
<td>Alt+Enter (1)</td>
<td>Show the word in search word field in a new tabsheet</td>
</tr>
<tr>
<td>Alt+LeftArrow</td>
<td>Previous page in page history</td>
</tr>
<tr>
<td>Ctrl+LeftArrow (2)</td>
<td>Previous page in page history</td>
</tr>
<tr>
<td>Alt+RightArrow</td>
<td>Next page in page history</td>
</tr>
<tr>
<td>Ctlr+RightArrow (2)</td>
<td>Next page in page history</td>
</tr>
<tr>
<td>Ctrl++/Ctrl+Numpad+/Ctrl+UpArrow (3)</td>
<td>Increase font size</td>
</tr>
<tr>
<td>Ctrl+-/Ctrl+Numpad-/Ctrl+DownArrow (3)</td>
<td>Decrease font size</td>
</tr>
<tr>
<td>Ctrl+0 (4)</td>
<td>Normal font size</td>
</tr>
<tr>
<td>Ctrl+U</td>
<td>Show HTML source</td>
</tr>
</table>
<dl>
<dt>(1)</dt>
<dd>This works only when the search word field is active i.e. the
caret is in it.</dd>
<dt>(2)</dt>
<dd>These are nonstandard combinations, the usual ones being
Alt+LeftArrow and Alt+RightArrow. These are still functional because there used to be difficulties with the standard ones earlier in the life of this program. Use these if the standard combinations do not work properly for you.</dd>
<dt>(3)</dt>
<dd>There are so many of these combinations because the usual i.e.
Ctrl++/Ctrl+- combinations did not work on the author's laptop and
the Numpad combinations were cumbersome to use. Hopefully the first
ones work on the computers of others.</dd>
<dt>(4)</dt>
<dd>This combination Ctrl+0 is "Ctrl+zero" not "Ctrl+ou".</dd>
</dl>
</body>
</html>
"""

def app():
    global options_dict

    app = wx.PySimpleApp()
    _initalize_options()
    frm = MyHtmlFrame(None, frame_title) #, -1, -1)
    # Icon handling may not be portable - don't know
    # This succeeds in Windows, so let's make it conditional
    if platform.system() == 'Windows':
        ico = wx.Icon('favicon.ico', wx.BITMAP_TYPE_ICO)
        frm.SetIcon(ico)
    word,body = new_word_and_body('green')
    frm.panel.nb.SetPageText(0,word)
    frm.panel.nb.h_w.current_word  = word
    frm.panel.search_word.SetValue(word)
    body = explanation + body
    frm.panel.nb.h_w.show_page(pg('green', body))
    page = frm.panel.nb.h_w.GetParser().GetSource()
    page = frm.panel.nb.GetPage(0).GetParser().GetSource()
    frm.Show()
    frm.Maximize(True)
    _adjust_pos_and_size(frm)
    app.MainLoop()


if __name__ == '__main__':
    app()

__all__ = ['app']
