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

from browseutil import *

__all__ = ['demo']

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
        link_type = href[0]
        q_link = href[1:]
        u_link = unquote_plus(q_link)
        #print link_type, q_link, u_link
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
        if link_type == 'M': # Member of the words in a synset
            word,body = new_word_and_body(u_link)
            if word:
                self.parent.SetPageText(self.parent.current_page, word)
                self.parent.parent.show_page_and_word(pg(word, body), word)
            else:
                self.show_msg('The word was not found!')
        elif link_type == 'R': # Relation links
            # A relation link looks like this:
            # word#synset_keys#relation_name#uniq_cntr  (OLD FORM !!!)
            # word#synset_keys#relation_name#uniq_cntr
            #print 'u_link:', u_link
            word,synset_keys,rel_name,u_c = u_link.split('#')
            word = word.strip()
            synset_keys = synset_keys.strip()
            rel_name = rel_name.strip()
            u_c = u_c.strip()
            #print 'word,synset_keys,rel_name,u_c:',word,synset_keys,rel_name,u_c
            page = self.GetParser().GetSource()
            ind = page.find(q_link) + len(q_link) + 2
            #print page[ind:]
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                page = page[:ind] + '<i>' + rel_name + \
                        '</i>' + page[ind + len(rel_name) + 14:]
                self.parent.parent.show_page_and_word(page)
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
                    self.parent.parent.show_page_and_word(page)
                else:
                    self.show_msg('Relation "%s" is not implemented yet!' % rel_name)
                    #print 'Relation "%s" is not implemented yet!' % rel_name
        else:
            # A word link looks like this:
            # Wword#synset_key,prev_synset_key#link_counter  (OLD FORM !!!)
            # Wword#synset_key,prev_synset_key#link_counter
            # A synset link looks like this:
            # Sword#synset_key,prev_synset_key#link_counter  (OLD FORM !!!)
            # Sword#synset_key,prev_synset_key#link_counter
            l_t = link_type + ':'
            #print 'l_t, u_link:', l_t, u_link
            word,syns_keys,link_counter = u_link.split('#')
            #print 'word,syns_keys,link_counter:',word,syns_keys,link_counter
            #syns_key,prev_syns_key = syns_keys.split(',')
            page = self.GetParser().GetSource()
            ind = page.find(q_link) + len(q_link) + 2
            #print page[ind:]
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                #page = page[:ind] + 'S:' + page[ind + 9:]
                page = page[:ind] + l_t + page[ind + 9:]
                self.parent.parent.show_page_and_word(page)
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
                self.parent.parent.show_page_and_word(page)
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

    def show_help(self):
        self.parent.parent.show_page_and_word(explanation, 'green')

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
        self.read_file('help.html')

    def on_help_about(self, event):
        wx.MessageBox(help_about)

    def show_db_info(self):
        word = '* Database Info *'
        current_page = self.panel.nb.add_html_page()
        self.panel.nb.SetPageText(current_page,word)
        html = (html_header % '* Database Info *') + \
        '''
        <h2>Database information is being gathered!</h2>
        <p>Producing this summary information may,
        depending on your computer, take a minute or two.</p>
        <p>Please be patient! If this operation seems to last too long,
        it might be a good idea to save the resulting page on disk for possible
        later viewings.</p>
        '''
        self.panel.show_page_and_word(html + html_trailer, word)
        wx.Yield()
        all_pos = ['noun', 'verb', 'adj', 'adv']
        data_path = os.environ['NLTK_DATA'] + '\\corpora\\wordnet\\'
        display_names = [('forms','Word forms'), ('simple','--- simple words'),
            ('collo','--- collocations'), ('syns','Synsets'),
            ('w_s_pairs','Word-Sense Pairs'),
            ('monos','Monosemous Words and Senses'),
            ('poly_words','Polysemous Words'),
            ('poly_senses','Polysemous Senses'),
            ('apimw','Average Polysemy Including Monosemous Words'),
            ('apemw','Average Polysemy Excluding Monosemous Words'),
            ('rels','Relations')]

        col_heads = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Total']
        #counts = [[0] * len(col_heads)] * len(display_names)
        counts = [[0 for i in range(len(col_heads))] for j in range(len(display_names))]
        rel_counts = defaultdict(int)
        rel_words = {}
        unique_beginners = defaultdict(list)

        for n_pos,pos in enumerate(all_pos): #all_pos): ['adj', 'adv']):
            html += '<br><br>Starting the summary for POS: %s' % col_heads[n_pos]
            self.panel.show_page_and_word(html + html_trailer, word)
            wx.Yield()
            d = defaultdict(int)
            # Word counts
            for ind in open(data_path + 'index.' + pos):
                if ind.startswith('  '):
                    continue
                ind_parts = ind.split()
                syn_count = int(ind_parts[2])
                d['w_s_pairs'] += syn_count
                if syn_count == 1:
                    d['monos'] += 1
                else:
                    d['poly_words'] += 1
                    d['poly_senses'] += syn_count
                w = ind_parts[0]
                d['forms'] += 1
                if w.find('_') != -1:
                    d['simple'] += 1
                else:
                    d['collo'] += 1
            d['apimw'] = 1.0 * (d['monos'] + d['poly_senses']) / \
                               (d['monos'] + d['poly_words'])
            d['apemw'] = 1.0 * d['poly_senses'] / d['poly_words']

            # Synsets and relations
            for syns in open(data_path + 'data.' + pos):
                if syns.startswith('  '):
                    continue
                d['syns'] += 1
                synset = getSynset(pos,int(syns[:8]))
                syn_rel = synset.relations_2()
                if HYPERNYM not in syn_rel and 'hypernym (instance)' not in syn_rel:
                    unique_beginners[n_pos].append(synset)
                d['rels'] += len(syn_rel)
                for sr in syn_rel:
                    rel_counts[(sr,n_pos)] += 1
                    rel_words[(sr,n_pos)] = synset.words[0]

            # Prepare counts for displaying
            nd = {}
            for n,(x,y) in enumerate(display_names):
                nd[x] = n
                if x in d:
                    counts[n][n_pos] = d[x]
                    counts[n][4] += d[x]
                if x == 'apimw' or x == 'apemw':
                    m_c = counts[nd['monos']][4]
                    m_ps = counts[nd['poly_senses']][4]
                    m_pw = counts[nd['poly_words']][4]
                    if x == 'apimw':
                        counts[n][4] = 1.0 * (m_c + m_ps) / (m_c + m_pw)
                    else:
                        counts[n][4] = 1.0 * m_ps /  m_pw

        # Format the counts
        html += '<br><br>Starting the construction of result tables'
        self.panel.show_page_and_word(html + html_trailer, word)
        wx.Yield()
        html = (html_header % '* Database Info *') + hlev(2, 'Word, synset and relation counts by POS')
        html += '''
        <table border="1" cellpadding="1" cellspacing="1"
        summary="">
        <col align="left"><col align="right"><col align="right">
        <col align="right"><col align="right"><col align="right">
        <tr><th></th><th align="center">Noun</th><th align="center">Verb</th>
        <th align="center">Adjective</th><th align="center">Adverb</th>
        <th align="center">Total</th></tr>
        '''
        for n,(x,y) in enumerate(display_names):
            if x == 'rels':
                html += '<tr><th align="left"> </th>'
                html += ''.join('<td align="right"> </td>' for c in counts[n]) \
                        + '</tr>'
            html += '<tr><th align="left">' + '%s' % y + '</th>'
            if  x == 'apimw' or x == 'apemw':
                html += ''.join('<td align="right">' + '%6.2f ' % c + '</td>' \
                                                for c in counts[n]) + '</tr>'
            else:
                html += ''.join('<td align="right">' + '%6d ' % c + '</td>' \
                                                for c in counts[n]) + '</tr>'

        # Format the relation counts
        r_counts = [0 for i in range(len(col_heads))]
        for rk in groupby(sorted(rel_counts.keys()),key=lambda x:x[0]):
            for i in range(len(col_heads)):
                r_counts[i] = 0
            dn = dbname_to_dispname(rk[0]).split('/')
            if dn[0] == '???':
                dn = rk[0] + '(???)'
            else:
                dn = dn[0]
            html += '<tr><th align="left">' + '%s' % ('--- ' + dn) + '</th>'
            for y in rk[1]:
                r_counts[y[1]] = rel_counts[y]
            r_counts[len(col_heads) - 1] = sum(r_counts)
            html += ''.join('<td align="right">' + '%6d ' % rc + '</td>'
                             for rc in r_counts) + '</tr>'
        html += '</table>'

        html += '<br><br>' + hlev(2, 'Example words for relations, 1 per POS')

        # Format the example words for relations
        html += '''
        <table border="1" cellpadding="1" cellspacing="1"
        summary="">
        <caption></caption>
        <col align="center"><col align="center"><col align="center">
        <col align="center"><col align="center">
        <tr><th>Relation</th><th>Noun</th><th>Verb</th><th>Adjective</th><th>Adverb</th></tr>
        '''

        for rk in groupby(sorted(rel_counts.keys()),key=lambda x:x[0]):
            dn = dbname_to_dispname(rk[0]).split('/')
            if dn[0] == '???':
                dn = rk[0] + '(???)'
            else:
                dn = dn[0]
            #html += '<tr><th align="center">' + '%s' % (dn) + '</th>'
            html += '<tr><th align="center">' + dn + '</th>'
            rel_word_examples = [''] * 4
            for y in rk[1]:
                rel_word_examples[y[1]] = rel_words[y]
            hlp = ''.join('<td align="center"><a href="M' + x + '">' + x.replace('_', ' ') +
                            '</a></td>' for x in rel_word_examples)
            hlp = hlp.replace('<a href="M"></a>','-')
            html += hlp + '</tr>'
        html += '</table>' + html_trailer

        '''
        display
        for ch in col_heads:
            display '%20.20s' % ch,
        display
        #display ' ' * 16,
        for i in range(4):
            display '%20d' % len(unique_beginners[i]),
        display 'Unique beginners',
        for ch in col_heads:
            display '%20.20s' % ch,
        ub = []
        for i in range(4):
            ub.append(unique_beginners[i])
        for i in range(4):
            ub[i].sort()
        max_count = min(max(len(x) for x in ub), 100)
        for count in range(max_count):
            display ('%5.5d' + ' '* 11) % count,
            for i in range(4):
                if count < len(ub[i]):
                    display ub[i][count],
                else:
                    display ' ' * 19,
            display
        '''
        self.panel.show_page_and_word(html, word)
        return current_page

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

def initalize_options():
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
    global explanation
    global options_dict

    app = wx.PySimpleApp()
    initalize_options()
    frm = MyHtmlFrame(None, frame_title) #, -1, -1)
    # Icon handling may not be portable - don't know
    # This succeeds in Windows, so let's make it conditional
    if platform.system() == 'Windows':
        ico = wx.Icon('favicon.ico', wx.BITMAP_TYPE_ICO)
        # ??? tbi = wx.TaskBarIcon()
        # ??? tbi.SetIcon(ico, 'this is the tip, you know')
        frm.SetIcon(ico)
    word,body = new_word_and_body('green')
    frm.panel.nb.SetPageText(0,word)
    frm.panel.nb.h_w.current_word  = word
    frm.panel.search_word.SetValue(word)
    body = explanation + body
    frm.panel.nb.h_w.show_page(pg('green', body))
    page = frm.panel.nb.h_w.GetParser().GetSource()
    page = frm.panel.nb.GetPage(0).GetParser().GetSource()
    explanation = body
    frm.Show()
    frm.Maximize(True)
    adjust_pos_and_size(frm)
    app.MainLoop()


if __name__ == '__main__':
    demo()

