# Natural Language Toolkit: Recursive Descent Parser Demo
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
# $Id: concordance.py 6121 2008-07-11 02:10:33Z stevenbird $

import re
import nltk.corpus
from Tkinter import *
from nltk.draw import *
from string import join
import threading

WORD_OR_TAG = '[^/ ]+'
BOUNDARY = r'\b'

CORPUS_LOADED_EVENT = '<<CL_EVENT>>'
SEARCH_TERMINATED_EVENT = '<<ST_EVENT>>'
SEARCH_ERROR_EVENT = '<<SE_EVENT>>'
ERROR_LOADING_CORPUS_EVENT = '<<ELC_EVENT>>'

# NB All corpora must be specified in a lambda expression so as not to be
# loaded when the module is imported.

_DEFAULT = 'English: Brown Corpus (Humor, simplified)'
_CORPORA = {
            'Catalan: CESS-CAT Corpus (simplified)':
                lambda: nltk.corpus.cess_cat.tagged_sents(simplify_tags=True),
            'English: Brown Corpus':
                lambda: nltk.corpus.brown.tagged_sents(),
            'English: Brown Corpus (simplified)':
                lambda: nltk.corpus.brown.tagged_sents(simplify_tags=True),
            'English: Brown Corpus (Press, simplified)':
                lambda: nltk.corpus.brown.tagged_sents(categories='abc', simplify_tags=True),
            'English: Brown Corpus (Religion, simplified)':
                lambda: nltk.corpus.brown.tagged_sents(categories='d', simplify_tags=True),
            'English: Brown Corpus (Learned, simplified)':
                lambda: nltk.corpus.brown.tagged_sents(categories='j', simplify_tags=True),
            'English: Brown Corpus (Science Fiction, simplified)':
                lambda: nltk.corpus.brown.tagged_sents(categories='m', simplify_tags=True),
            'English: Brown Corpus (Romance, simplified)':
                lambda: nltk.corpus.brown.tagged_sents(categories='p', simplify_tags=True),
            'English: Brown Corpus (Humor, simplified)':
                lambda: nltk.corpus.brown.tagged_sents(categories='r', simplify_tags=True),
            'English: NPS Chat Corpus':
                lambda: nltk.corpus.nps_chat.tagged_posts(),
            'English: NPS Chat Corpus (simplified)':
                lambda: nltk.corpus.nps_chat.tagged_posts(simplify_tags=True),
            'English: Wall Street Journal Corpus':
                lambda: nltk.corpus.treebank.tagged_sents(),
            'English: Wall Street Journal Corpus (simplified)':
                lambda: nltk.corpus.treebank.tagged_sents(simplify_tags=True),
            'Chinese: Sinica Corpus':
                lambda: nltk.corpus.sinica_treebank.tagged_sents(),
            'Chinese: Sinica Corpus (simplified)':
                lambda: nltk.corpus.sinica_treebank.tagged_sents(simplify_tags=True),
            'Dutch: Alpino Corpus':
                lambda: nltk.corpus.alpino.tagged_sents(),
            'Dutch: Alpino Corpus (simplified)':
                lambda: nltk.corpus.alpino.tagged_sents(simplify_tags=True),
            'Hindi: Indian Languages Corpus':
                lambda: nltk.corpus.indian.tagged_sents(files='hindi.pos'),
            'Hindi: Indian Languages Corpus (simplified)':
                lambda: nltk.corpus.indian.tagged_sents(files='hindi.pos', simplify_tags=True),
            'Portuguese: Floresta Corpus (Portugal)':
                lambda: nltk.corpus.floresta.tagged_sents(),
            'Portuguese: Floresta Corpus (Portugal, simplified)':
                lambda: nltk.corpus.floresta.tagged_sents(simplify_tags=True),
            'Portuguese: MAC-MORPHO Corpus (Brazil)':
                lambda: nltk.corpus.mac_morpho.tagged_sents(),
            'Portuguese: MAC-MORPHO Corpus (Brazil, simplified)':
                lambda: nltk.corpus.mac_morpho.tagged_sents(simplify_tags=True),
            'Spanish: CESS-ESP Corpus (simplified)':
                lambda: nltk.corpus.cess_esp.tagged_sents(simplify_tags=True),
           }

class CategorySearchView(object):
    _BACKGROUND_COLOUR='#FFF' #white
    
    #Colour of highlighted results
    _HIGHLIGHT_WORD_COLOUR='#F00' #red
    _HIGHLIGHT_WORD_TAG='HL_WRD_TAG'
    
    _HIGHLIGHT_LABEL_COLOUR='#0FF'
    _HIGHLIGHT_LABEL_TAG='HL_LBL_TAG'
    
    
    #Percentage of text left of the scrollbar position
    _FRACTION_LEFT_TEXT=0.30
    
    #Number of characters before the position of search item
    _CHAR_BEFORE=75
    #Number of characters after the position of search item
    _CHAR_AFTER=85
    
    def __init__(self):
        self.model = CategorySearchModel()
        self.model.add_listener(self)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self._bind_event_handlers()
        self.load_corpus(self.model.DEFAULT_CORPUS)
        
    def _init_top(self, top):
        top.geometry('950x680+50+50')
        top.title('NLTK Concordance Search')
        top.bind('<Control-q>', self.destroy)
        top.minsize(950,680)
        
    def _init_widgets(self, parent):
        self.main_frame = Frame(parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1))        
        self._init_corpus_select(self.main_frame)
        self._init_query_box(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill='both', expand=True)

    def _init_menubar(self):
		menubar = Menu(self.top)
		
		filemenu = Menu(menubar, tearoff=0, borderwidth=0)
		filemenu.add_command(label='Exit', underline=1,
							 command=self.destroy, accelerator='Ctrl-q')
		menubar.add_cascade(label='File', underline=0, menu=filemenu)

		helpmenu = Menu(menubar, tearoff=0)
		helpmenu.add_command(label='About', underline=0,
							 command=self.about)
		menubar.add_cascade(label='Help', underline=0, menu=helpmenu)
		
		self.top.config(menu=menubar)
		
    def _init_corpus_select(self, parent):
    	innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(innerframe, justify=LEFT, text=' Corpus: ', background=self._BACKGROUND_COLOUR, padx = 2, pady = 1, border = 0).pack(side='left')
        
        other_corpora = self.model.CORPORA.keys().remove(self.model.DEFAULT_CORPUS)
        om = OptionMenu(innerframe, self.var, self.model.DEFAULT_CORPUS, command=self.corpus_selected, *self.model.non_default_corpora())
        om['borderwidth'] = 0
        om['highlightthickness'] = 1
        om.pack(side='left')
        innerframe.pack(side='top', fill='x', anchor='n')
        
    def _init_status(self, parent):
        self.status = Label(parent, justify=LEFT, relief=SUNKEN, background=self._BACKGROUND_COLOUR, border=0, padx = 1, pady = 0)
        self.status.pack(side='top', anchor='sw')
    
    def _init_query_box(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        another = Frame(innerframe, background=self._BACKGROUND_COLOUR)
        self.query_box = Entry(another, width=60)
        self.query_box.pack(side='left', fill='x', pady=25, anchor='center')
        self.search_button = Button(another, text='Search', command=self.search, borderwidth=1, highlightthickness=1)
        self.search_button.pack(side='left', fill='x', pady=25, anchor='center')
        self.query_box.bind('<KeyPress-Return>', self.search_enter_keypress_handler)
        another.pack()
        innerframe.pack(side='top', fill='x', anchor='n')
        
    def search_enter_keypress_handler(self, *event):
        self.search()
    
    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient='horiz')
        self.results_box = Text(i1,
                                font=tkFont.Font(family='courier', size='16'),
                                state='disabled', borderwidth=1, 
							    yscrollcommand=vscrollbar.set,
                                xscrollcommand=hscrollbar.set, wrap='none', width='40', height = '20')
        self.results_box.pack(side='left', fill='both', expand=True)
        self.results_box.tag_config(self._HIGHLIGHT_WORD_TAG, foreground=self._HIGHLIGHT_WORD_COLOUR)
        self.results_box.tag_config(self._HIGHLIGHT_LABEL_TAG, foreground=self._HIGHLIGHT_LABEL_COLOUR)
        vscrollbar.pack(side='left', fill='y', anchor='e')
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side='left', fill='x', expand=True, anchor='w')
        hscrollbar.config(command=self.results_box.xview)
        #there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text='   ', background=self._BACKGROUND_COLOUR).pack(side='left', anchor='e')
        i1.pack(side='top', fill='both', expand=True, anchor='n')
        i2.pack(side='bottom', fill='x', anchor='s')
        innerframe.pack(side='top', fill='both', expand=True)
        
    def _init_paging(self, parent):
    	innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
    	self.prev = prev = Button(innerframe, text='Previous', command=self.previous, width='10', borderwidth=1, highlightthickness=1, state='disabled')
    	prev.pack(side='left', anchor='center')
    	self.next = next = Button(innerframe, text='Next', command=self.next, width='10', borderwidth=1, highlightthickness=1, state='disabled')
    	next.pack(side='right', anchor='center')
    	innerframe.pack(side='top', fill='y')
        self.current_page = 0
    	
    def previous(self):
        self.clear_results_box()
        self.freeze_editable()    	
        self.model.prev(self.current_page - 1)
    
    def next(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.next(self.current_page + 1)        
        
    def about(self, *e):
		ABOUT = ("NLTK Concordance Search Demo\n")
		TITLE = 'About: NLTK Concordance Search Demo'
		try:
			from tkMessageBox import Message
			Message(message=ABOUT, title=TITLE, parent=self.main_frame).show()
		except:
			ShowText(self.top, TITLE, ABOUT)
        
    def _bind_event_handlers(self):
        self.top.bind(CORPUS_LOADED_EVENT, self.handle_corpus_loaded)
        self.top.bind(SEARCH_TERMINATED_EVENT, self.handle_search_terminated)
        self.top.bind(SEARCH_ERROR_EVENT, self.handle_search_error)
        self.top.bind(ERROR_LOADING_CORPUS_EVENT, self.handle_error_loading_corpus)
        
    def handle_error_loading_corpus(self, event):
        self.status['text'] = 'Error in loading ' + self.var.get()
        self.unfreeze_editable()
        self.clear_all()
        self.freeze_editable()
        
    def handle_corpus_loaded(self, event):
        self.status['text'] = self.var.get() + ' is loaded'
        self.unfreeze_editable()
        self.clear_all()
        self.query_box.focus_set()
    
    def handle_search_terminated(self, event):
	    #todo: refactor the model such that it is less state sensitive
        results = self.model.get_results()
        self.write_results(results)
        self.status['text'] = ''
        if len(results) == 0:
            self.status['text'] = 'No results found for ' + self.model.query
        else:
        	self.current_page = self.model.last_requested_page
        self.unfreeze_editable()
        self.results_box.xview_moveto(self._FRACTION_LEFT_TEXT)
        

    def handle_search_error(self, event):
        self.status['text'] = 'Error in query ' + self.model.query
        self.unfreeze_editable()
        
    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status['text'] = 'Loading ' + selection + '...'
            self.freeze_editable()
            self.model.load_corpus(selection)

    def search(self):
        self.current_page = 0
        self.clear_results_box()
        self.model.reset_results()
        query = self.query_box.get()
        if (len(query.strip()) == 0): return
        self.status['text']  = 'Searching for ' + query
        self.freeze_editable()
        self.model.search(query, self.current_page + 1)
        

    def write_results(self, results):
        self.results_box['state'] = 'normal'
        row = 1
        for each in results:
            sent, pos1, pos2 = each[0].strip(), each[1], each[2]
            if len(sent) != 0:
                if (pos1 < self._CHAR_BEFORE):
                    sent, pos1, pos2 = self.pad(sent, pos1, pos2)
                self.results_box.insert(str(row) + '.0',
                    sent[pos1-self._CHAR_BEFORE:pos1+self._CHAR_AFTER] + '\n')
                self.results_box.tag_add(self._HIGHLIGHT_WORD_TAG,
                    str(row) + '.' + str(self._CHAR_BEFORE),
                    str(row) + '.' + str(pos2 - pos1 + self._CHAR_BEFORE))
                row += 1
        self.results_box['state'] = 'disabled'

    def pad(self, sent, hstart, hend):
        if hstart >= self._CHAR_BEFORE:
            return sent, hstart, hend
        d = self._CHAR_BEFORE - hstart
        sent = ''.join([' '] * d) + sent
        return sent, hstart + d, hend + d
    
    def destroy(self, *e):
        if self.top is None: return
        self.top.destroy()
        self.top = None
        
    def clear_all(self):
        self.query_box.delete(0, END)
        self.model.reset_query()
        self.clear_results_box()
        
    def clear_results_box(self):
        self.results_box['state'] = 'normal'
        self.results_box.delete("1.0", END)
        self.results_box['state'] = 'disabled'   
        
    def freeze_editable(self):
        self.query_box['state'] = 'disabled'
        self.search_button['state'] = 'disabled'
        self.prev['state'] = 'disabled'
        self.next['state'] = 'disabled'
        
    def unfreeze_editable(self):
        self.query_box['state'] = 'normal'
        self.search_button['state'] = 'normal'
        self.set_paging_button_states()
        
    def set_paging_button_states(self):
    	if self.current_page == 0 or self.current_page == 1:
    		self.prev['state'] = 'disabled'
    	else:
    		self.prev['state'] = 'normal'
        if self.model.has_more_pages(self.current_page):
            self.next['state'] = 'normal'
        else:
            self.next['state'] = 'disabled'
        
    def fire_event(self, event):
        #Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when='tail')
        
    def mainloop(self, *args, **kwargs):
        if in_idle(): return
        self.top.mainloop(*args, **kwargs)
        
class CategorySearchModel(object):
    def __init__(self):
        self.listeners = []
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.selected_corpus = None
        self.reset_query()
        self.reset_results()
        
    def non_default_corpora(self):
        copy = []
        copy.extend(self.CORPORA.keys())
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy
    
    def load_corpus(self, name):
        self.selected_corpus = name
        self.tagged_sents = []
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()
        
    def search(self, query, page, count=50):
        self.query = query
    	self.last_requested_page = page
        self.SearchCorpus(self, page, count).start()        
        
    def next(self, page):
    	self.last_requested_page = page
    	if len(self.results) < page:
    		self.search(self.query, page)
    	else:
    		self.notify_listeners(SEARCH_TERMINATED_EVENT)    		
    
    def prev(self, page):
    	self.last_requested_page = page
    	self.notify_listeners(SEARCH_TERMINATED_EVENT)
    
    def add_listener(self, listener):
        self.listeners.append(listener)
        
    def notify_listeners(self, event):
        for each in self.listeners:
            each.fire_event(event)
            
    def reset_results(self):
        self.results = []
        self.last_page = None        
        
    def reset_query(self):
        self.query = None
        
    def set_results(self, page, resultset):
        self.results.insert(page - 1, resultset)

    def get_results(self):
        return self.results[self.last_requested_page - 1]
    
    def has_more_pages(self, page):
    	if self.results == [] or self.results[0] == []:
	    	return False
        if self.last_page == None:
	    	return True
        return page < self.last_page
    	
    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            self.model, self.name = model, name
            threading.Thread.__init__(self)
            
        def run(self):
            try:
                ts = self.model.CORPORA[self.name]()
                self.model.tagged_sents = [join(w+'/'+t for (w,t) in sent) for sent in ts]
                self.model.notify_listeners(CORPUS_LOADED_EVENT)
            except:
                self.model.notify_listeners(ERROR_LOADING_CORPUS_EVENT)
            
    class SearchCorpus(threading.Thread):
        def __init__(self, model, page, count):
            self.model, self.count, self.page = model, count, page
            threading.Thread.__init__(self)
        
        def run(self):
            q = self.processed_query()
            sent_pos = []
            i = 0
            for sent in self.model.tagged_sents[(self.page - 1) * self.count:]:
                try:
                    m = re.search(q, sent)
                except re.error:
                    self.model.reset_results()
                    self.model.notify_listeners(SEARCH_ERROR_EVENT)
                    return
                if m:
                    sent_pos.append((sent, m.start(), m.end()))
                    i += 1
                    if i > self.count + 1: break
            if (self.count >= len(sent_pos)): self.model.last_page = self.page
            self.model.set_results(self.page, sent_pos[:-1])
            self.model.notify_listeners(SEARCH_TERMINATED_EVENT)            
            
        def processed_query(self):
            new = []
            for term in self.model.query.split():
                term = re.sub(r'\.', r'[^/ ]', term)
                if re.match('[A-Z]+$', term):
                    new.append(BOUNDARY + WORD_OR_TAG + '/' + term + BOUNDARY)
                elif '/' in term:
                    new.append(BOUNDARY + term + BOUNDARY)
                else:
                    new.append(BOUNDARY + term + '/' + WORD_OR_TAG + BOUNDARY)
            return join(new)
        
def pos_concordance():
    d = CategorySearchView()
    d.mainloop()
        
if __name__ == '__main__':
    pos_concordance()
