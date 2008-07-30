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

class CategorySearchView:
    _BACKGROUND_COLOUR='#FFF'#white
    
    #Colour of highlighted results
    _HIGHLIGHT_COLOUR='#F00'#red
    _HIGHLIGHT_TAG='HL_TAG'
    
    #Number of characters before the position of search item
    _CHAR_BEFORE=35
    #Number of characters after the position of search item
    _CHAR_AFTER=45
    
    def __init__(self):
        self.model = CategorySearchModel()
        self.model.add_listener(self)
        self.top = Tk()
        self._init_top(self.top)
        self._init_widgets(self.top)
        self._bind_event_handlers()
        self.load_corpus(self.model.DEFAULT_CORPUS)
        
    def _init_top(self, top):
        top.geometry('+50+50')
        top.title('Category Search Demo')
        top.bind('<Control-q>', self.destroy)
        
    def _init_widgets(self, parent):
        self.main_frame = Frame(parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1))        
        self._init_corpus_select(self.main_frame)
        self._init_query_box(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill='both', expand=False)
                
    def _init_corpus_select(self, parent):
        self.var = StringVar(parent)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(parent, justify=LEFT, text=' Corpus: ', background=self._BACKGROUND_COLOUR, padx = 2, pady = 1, border = 0).grid(row=0, column = 0, sticky = W)
        other_corpora = self.model.CORPORA.keys().remove(self.model.DEFAULT_CORPUS)
        om = OptionMenu(parent, self.var, self.model.DEFAULT_CORPUS, command=self.corpus_selected, *self.model.non_default_corpora())
        om['borderwidth'] = 0
        om['highlightthickness'] = 1
        om.grid(row=0, column=0)
        
    def _init_status(self, parent):
        self.status = Label(parent, justify=LEFT, relief=SUNKEN, background=self._BACKGROUND_COLOUR, border=0, padx = 1, pady = 0)
        self.status.grid(row = 11, column= 0, columnspan=4, sticky=W)
    
    def _init_query_box(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        innerframe.grid(row=1, column=0, rowspan=5, columnspan=4)
        self.query_box = Entry(innerframe, width=40)
        self.query_box.grid(row=0, column = 0, padx=2, pady=20, sticky=E)
        self.search_button = Button(innerframe, text='Search', command=self.search, borderwidth=1, highlightthickness=1)
        self.search_button.grid(row=0, column = 1, padx=2, pady=20, sticky=W)
        self.query_box.bind('<KeyPress-Return>', self.search_enter_keypress_handler)
        
    def search_enter_keypress_handler(self, *event):
        self.search()
    
    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        innerframe.grid(row=6, column=0, rowspan=5, columnspan=4)
        scrollbar = Scrollbar(innerframe, borderwidth=1)
        scrollbar.grid(row=0, column=1, sticky='NSE')
        self.results_box = Text(innerframe, width=80, height=30, state='disabled', borderwidth=1, yscrollcommand=scrollbar.set)
        self.results_box.tag_config(self._HIGHLIGHT_TAG, foreground=self._HIGHLIGHT_COLOUR)
        self.results_box.grid(row=0, column=0)
        scrollbar.config(command=self.results_box.yview)
        
    def _bind_event_handlers(self):
        self.top.bind(CORPUS_LOADED_EVENT, self.handle_corpus_loaded)
        self.top.bind(SEARCH_TERMINATED_EVENT, self.handle_search_terminated)
        self.top.bind(SEARCH_ERROR_EVENT, self.handle_search_error)
        self.top.bind(ERROR_LOADING_CORPUS_EVENT, self.handle_error_loading_corpus)
        
    def handle_error_loading_corpus(self, event):
        self.status['text'] = 'Error in loading ' + self.var.get() + ' corpus'
        self.unfreeze_editable()
        self.clear_all()
        self.freeze_editable()
        
    def handle_corpus_loaded(self, event):
        self.status['text'] = self.var.get() + ' corpus is loaded'
        self.unfreeze_editable()
        self.clear_all()
        self.query_box.focus_set()
    
    def handle_search_terminated(self, event):
        self.write_results(self.model.results)
        self.status['text'] = ''
        if len(self.model.results) == 0:
            self.status['text'] = 'No results found for ' + self.model.query
        self.unfreeze_editable()
            
    def handle_search_error(self, event):
        self.status['text'] = 'Error in query ' + self.model.query
        self.unfreeze_editable()
        
    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status['text'] = 'Loading ' + selection + ' corpus...'
            self.freeze_editable()
            self.model.load_corpus(selection)

    def search(self):
        self.clear_results_box()
        query = self.query_box.get()
        if (len(query.strip()) == 0): return
        self.status['text']  = 'Searching for ' + query
        self.freeze_editable()
        self.model.search(query)
        
    def write_results(self, results):
        self.results_box['state'] = 'normal'
        row = 1
        for each in results:
            if len(each[0].strip()) != 0:
                self.results_box.insert(str(row) + '.0', each[0].strip()[each[1]-self._CHAR_BEFORE:each[1]+self._CHAR_AFTER] + '\n')
                self.results_box.tag_add(self._HIGHLIGHT_TAG, str(row) + '.' + str(self._CHAR_BEFORE), str(row) + '.' + str(each[2] - each[1] + self._CHAR_BEFORE))
                row += 1
        self.results_box['state'] = 'disabled'
                
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
        self.model.reset_results()
        
    def freeze_editable(self):
        self.query_box['state'] = 'disabled'
        self.search_button['state'] = 'disabled'
        
    def unfreeze_editable(self):
        self.query_box['state'] = 'normal'
        self.search_button['state'] = 'normal'
        
    def fire_event(self, event):
        #Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when='tail')
        
    def mainloop(self, *args, **kwargs):
        if in_idle(): return
        self.top.mainloop(*args, **kwargs)
        
class CategorySearchModel:
    def __init__(self):
        self.listeners = []
        self._BROWN_CORPUS = 'Brown'
        self.CORPORA = {self._BROWN_CORPUS:nltk.corpus.brown , 
                        'Indian':nltk.corpus.indian,
                        'YCOE':nltk.corpus.ycoe, 
                        'Treebank':nltk.corpus.treebank}
        self.DEFAULT_CORPUS = self._BROWN_CORPUS
        self.selected_corpus = None
        self.reset_query()
        self.reset_results()
        
    def non_default_corpora(self):
        copy = []
        copy.extend(self.CORPORA.keys())
        copy.remove(self.DEFAULT_CORPUS)
        return copy
    
    def load_corpus(self, name):
        self.selected_corpus = name
        self.tagged_sents = []
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()
        
    def search(self, query, num=50):
        self.query = query
        self.SearchCorpus(self, num).start()
    
    def add_listener(self, listener):
        self.listeners.append(listener)
        
    def notify_listeners(self, event):
        for each in self.listeners:
            each.fire_event(event)
            
    def reset_results(self):
        self.results = None
        
    def reset_query(self):
        self.query = None
        
    def set_results(self, results):
        self.results = results
            
    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            self.model, self.name = model, name
            threading.Thread.__init__(self)
            
        def run(self):
            try:
                ts = self.model.CORPORA[self.name].tagged_sents()
                self.model.tagged_sents = [join(w+'/'+t for (w,t) in sent) for sent in ts]
                self.model.notify_listeners(CORPUS_LOADED_EVENT)
            except:
                self.model.notify_listeners(ERROR_LOADING_CORPUS_EVENT)
            
    class SearchCorpus(threading.Thread):
        def __init__(self, model, num):
            self.model, self.num = model, num
            threading.Thread.__init__(self)
        
        def run(self):
            q = self.processed_query()
            sent_pos = []
            i = 0
            for sent in self.model.tagged_sents:
                try:
                    m = re.search(q, sent)
                except re.error:
                    self.model.reset_results()
                    self.model.notify_listeners(SEARCH_ERROR_EVENT)
                    return
                if m:
                    sent_pos.append((sent, m.start(), m.end()))
                    i += 1
                    if i > self.num: break
            self.model.set_results(sent_pos)
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
