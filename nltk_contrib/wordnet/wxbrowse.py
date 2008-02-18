# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

__version__ = '$Revision: 9 $'
# $Source$

import  os
import  os.path
import  sys
from time import sleep
import pickle
import platform
from urllib import quote_plus, unquote_plus
from itertools import groupby

import  wx
import  wx.html as  html
import  wx.lib.wxpTag

#from browseutil import page_word, new_word_and_body, explanation
import browseutil as bu

__all__ = ['demo']

#explanation_text = None
frame_title = 'NLTK Wordnet Browser'
help_about = frame_title + \
'''

Copyright (C) 2007 University of Pennsylvania

Author: Jussi Salmela <jtsalmela@users.sourceforge.net>

URL: <http://nltk.sf.net>

For license information, see LICENSE.TXT
'''

# This is used to save options in and to be pickled at exit
options_dict = {}
pickle_file_name = frame_title + '.pkl'


class MyHtmlWindow(html.HtmlWindow):
    def __init__(self, parent, id):
        html.HtmlWindow.__init__(self, parent, id,
                                    style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        #if 'gtk2' in wx.PlatformInfo:
        #self.SetStandardFonts()
        self.font_size = self.normal_font_size = \
                         options_dict['font_size']
        #print 'self.font_size:', self.font_size
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
        page,word = bu.page_word(self.GetParser().GetSource(), word, href)
        if page:
            if word:
                self.parent.SetPageText(self.parent.current_page, word)
                self.parent.parent.show_page_and_word(page, word)
            else:
                self.show_msg('The word was not found!')
                self.parent.parent.show_page_and_word(page)
        else:
            self.show_msg('Relation "%s" is not implemented yet!' % rel_name)
            #print 'Relation "%s" is not implemented yet!' % rel_name
        '''
        else:
            print 'We should be in a Help Window now! Are we?'
            super(MyHtmlWindow, self).OnLinkClicked(linkinfo)
        '''
        if tab_to_return_to is not None:
            self.parent.switch_html_page(tab_to_return_to)
            '''
            self.parent.current_page = tab_to_return_to
            self.parent.SetSelection(tab_to_return_to)
            self.parent.h_w = self.parent.GetPage(tab_to_return_to)
            if self.parent.h_w.prev_wp_list == []:
                self.parent.prev_btn.Enable(False)
            if self.parent.h_w.next_wp_list == []:
                self.parent.next_btn.Enable(False)
            '''

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
        options_dict['font_size'] = self.font_size
        # Font size behavior is very odd. This is a hack
        #self.SetFonts('times new roman', 'courier new', [self.font_size]*7)
        self.SetStandardFonts(size=self.font_size)
        self.SetPage(page_to_restore)

    #def show_body(self, word, body):
        #self.SetPage((html_header % word) + body + html_trailer)

    #def show_help(self):
    #    self.parent.parent.show_page_and_word(bu.explanation, 'green')

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
            self.switch_html_page(new)
        event.Skip()

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
        h_w.SetRelatedFrame(self.parent.frame, self.parent.titleBase + ' -- %s')
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
        #self.Bind(wx.EVT_TEXT, self.on_word_change, self.search_word)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_word_enter, self.search_word)
        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down, self.search_word)
        #self.Bind(wx.EVT_KEY_UP, self.on_key_up, self.search_word)
        #self.Bind(wx.EVT_CHAR, self.on_char, self.search_word)
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
        #else:
        #    self.nb.h_w.show_msg('At the start of page history already')

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
        #else:
        #    self.nb.h_w.show_msg('At the end of page history already!')

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
        word,body = bu.new_word_and_body(word)
        if word:
            self.show_page_and_word(bu.pg(word, body), word)
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
        ssw_nt = menu_1_2.Append(-1, 'Show search word in new tabsheet\tAlt+Enter')
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
        db_i = menu_3.Append(-1, 'Show Database Info')
        menu_3.AppendSeparator()
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
        self.Bind(wx.EVT_MENU, self.on_db_info, db_i)
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

        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        #self.Bind(wx.EVT_KEY_UP, self.on_key_up)

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
        word,body = bu.new_word_and_body(word)
        if word:
            self.panel.show_page_and_word(bu.pg(word, body), word)
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
        if os.path.isfile('NLTK Wordnet Browser Database Info.html'):
            html = open('NLTK Wordnet Browser Database Info.html').read()
        else:
            html = (html_header % word) + '<p>The database info file:'\
                   '<p><b>NLTK Wordnet Browser Database Info.html</b>' + \
                   '<p>was not found. Run this:<p><b>python dbinfo_html.py</b>' + \
                   '<p>to produce it.' + html_trailer
        self.panel.show_page_and_word(html, word)
        return

    def read_file(self, path):
        try:
            if not path.endswith('.htm') and not path.endswith('.html'):
                path += '.html'
            f = open(path)
            page = f.read()
            f.close()
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
                '''
                txt = '<title>' + frame_title + ' display of: ' + \
                      self.panel.nb.h_w.current_word  + '</title></head>'
                source = source.replace('</head>', txt)
                '''
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
        self.panel.printer.GetPrintData().SetFilename('onnaax ???')
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

def demo():
    #global explanation_text
    global options_dict

    app = wx.PySimpleApp()
    _initalize_options()
    frm = MyHtmlFrame(None, frame_title) #, -1, -1)
    # Icon handling may not be portable - don't know
    # This succeeds in Windows, so let's make it conditional
    if platform.system() == 'Windows':
        ico = wx.Icon('favicon.ico', wx.BITMAP_TYPE_ICO)
        # ??? tbi = wx.TaskBarIcon()
        # ??? tbi.SetIcon(ico, 'this is the tip, you know')
        frm.SetIcon(ico)
    word,body = bu.new_word_and_body('green')
    frm.panel.nb.SetPageText(0,word)
    frm.panel.nb.h_w.current_word  = word
    frm.panel.search_word.SetValue(word)
    body = bu.explanation + body
    frm.panel.nb.h_w.show_page(bu.pg('green', body))
    page = frm.panel.nb.h_w.GetParser().GetSource()
    page = frm.panel.nb.GetPage(0).GetParser().GetSource()
    #explanation_text = body
    frm.Show()
    frm.Maximize(True)
    _adjust_pos_and_size(frm)
    app.MainLoop()


if __name__ == '__main__':
    demo()

