# Natural Language Toolkit: Collocations Demo 
# Much of the GUI code is imported from concordance.py; We intend to merge these tools together
# Copyright (C) 2001-2008 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
import nltk
from nltk.draw import *
from Tkinter import *
from nltk.text import Text as TextDomain
from nltk.probability import FreqDist
import threading

CORPUS_LOADED_EVENT = '<<CL_EVENT>>'
ERROR_LOADING_CORPUS_EVENT = '<<ELC_EVENT>>'

_DEFAULT = 'English: Brown Corpus (Humor)'
_CORPORA = {
            'Catalan: CESS-CAT Corpus':
                lambda: nltk.corpus.cess_cat.words(),
            'English: Brown Corpus':
                lambda: nltk.corpus.brown.words(),
            'English: Brown Corpus (Press)':
                lambda: nltk.corpus.brown.words(categories='abc'),
            'English: Brown Corpus (Religion)':
                lambda: nltk.corpus.brown.words(categories='d'),
            'English: Brown Corpus (Learned)':
                lambda: nltk.corpus.brown.words(categories='j'),
            'English: Brown Corpus (Science Fiction)':
                lambda: nltk.corpus.brown.words(categories='m'),
            'English: Brown Corpus (Romance)':
                lambda: nltk.corpus.brown.words(categories='p'),
            'English: Brown Corpus (Humor)':
                lambda: nltk.corpus.brown.words(categories='r'),
            'English: NPS Chat Corpus':
                lambda: nltk.corpus.nps_chat.words(),
            'English: Wall Street Journal Corpus':
                lambda: nltk.corpus.treebank.words(),
            'Chinese: Sinica Corpus':
                lambda: nltk.corpus.sinica_treebank.words(),
            'Dutch: Alpino Corpus':
                lambda: nltk.corpus.alpino.words(),
            'Hindi: Indian Languages Corpus':
                lambda: nltk.corpus.indian.words(files='hindi.pos'),
            'Portuguese: Floresta Corpus (Portugal)':
                lambda: nltk.corpus.floresta.words(),
            'Portuguese: MAC-MORPHO Corpus (Brazil)':
                lambda: nltk.corpus.mac_morpho.words(),
            'Spanish: CESS-ESP Corpus':
                lambda: nltk.corpus.cess_esp.words(),
           }

class CollocationsView:
	_BACKGROUND_COLOUR='#FFF' #white	
	
	def __init__(self):
		self.model = CollocationsModel()
		self.model.add_listener(self)
		self.top = Tk()
		self._init_top(self.top)
		self._init_menubar()
		self._init_widgets(self.top)
		self._bind_event_handlers()
		self.load_corpus(self.model.DEFAULT_CORPUS)

	def _init_top(self, top):
		top.geometry('550x650+50+50')
		top.title('NLTK Collocations List')
		top.bind('<Control-q>', self.destroy)
		top.minsize(550,650)
		
	def _init_widgets(self, parent):
		self.main_frame = Frame(parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1))		
		self._init_corpus_select(self.main_frame)
		self._init_results_box(self.main_frame)
		self._init_paging(self.main_frame)
		self._init_status(self.main_frame)
		self.main_frame.pack(fill='both', expand=True)
		
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

	def _init_menubar(self):
		self._result_size = IntVar(self.top)
		menubar = Menu(self.top)
		
		filemenu = Menu(menubar, tearoff=0, borderwidth=0)
		filemenu.add_command(label='Exit', underline=1,
							 command=self.destroy, accelerator='Ctrl-q')
		menubar.add_cascade(label='File', underline=0, menu=filemenu)

		editmenu = Menu(menubar, tearoff=0)
		rescntmenu = Menu(editmenu, tearoff=0)
		rescntmenu.add_radiobutton(label='20', variable=self._result_size,
								 underline=0, value=20, command=self.set_result_size)
		rescntmenu.add_radiobutton(label='50', variable=self._result_size,
								 underline=0, value=50, command=self.set_result_size)
		rescntmenu.add_radiobutton(label='100', variable=self._result_size,
								 underline=0, value=100, command=self.set_result_size)
		rescntmenu.invoke(1)
		editmenu.add_cascade(label='Result Count', underline=0, menu=rescntmenu)
		self.top.config(menu=menubar)		

	def set_result_size(self, **kwargs):
		self.model.result_count = self._result_size.get()

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
								xscrollcommand=hscrollbar.set, wrap='none', width='40', height = '20', exportselection=1)
		self.results_box.pack(side='left', fill='both', expand=True)
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
		
	def _bind_event_handlers(self):
		self.top.bind(CORPUS_LOADED_EVENT, self.handle_corpus_loaded)
		self.top.bind(ERROR_LOADING_CORPUS_EVENT, self.handle_error_loading_corpus)
		
	def handle_error_loading_corpus(self, event):
		self.status['text'] = 'Error in loading ' + self.var.get()
		self.unfreeze_editable()
		self.clear_results_box()
		self.freeze_editable()
		
	def handle_corpus_loaded(self, event):
		self.status['text'] = self.var.get() + ' is loaded'
		self.unfreeze_editable()
		self.clear_results_box()
		
	def corpus_selected(self, *args):
		new_selection = self.var.get()
		self.load_corpus(new_selection)

	def previous(self):
		self.model.prev(self.current_page - 1)
		self.current_page= self.current_page - 1
	
	def next(self):
		self.model.next(self.current_page + 1)		
		
	def load_corpus(self, selection):
		if self.model.selected_corpus != selection:
			self.status['text'] = 'Loading ' + selection + '...'
			self.freeze_editable()
			self.model.load_corpus(selection)		
			
	def freeze_editable(self):
		self.prev['state'] = 'disabled'
		self.next['state'] = 'disabled'			
		
	def clear_results_box(self):
		self.results_box['state'] = 'normal'
		self.results_box.delete("1.0", END)
		self.results_box['state'] = 'disabled'   
		
	def fire_event(self, event):
		#Firing an event so that rendering of widgets happen in the mainloop thread
		self.top.event_generate(event, when='tail')

	def destroy(self, *e):
		if self.top is None: return
		self.top.destroy()
		self.top = None
		
	def mainloop(self, *args, **kwargs):
		if in_idle(): return
		self.top.mainloop(*args, **kwargs)
	
	def unfreeze_editable(self):
		self.set_paging_button_states()
		
	def set_paging_button_states(self):
		if self.current_page == 0 or self.current_page == 1:
			self.prev['state'] = 'disabled'
		else:
			self.prev['state'] = 'normal'
		if self.model.is_last_page(self.current_page):
			self.next['state'] = 'disabled'
		else:
			self.next['state'] = 'normal'

class CollocationsModel:
	def __init__(self):
		self.listeners = []
		self.result_count = None
		self.selected_corpus = None
		self.collocations = None
		self.CORPORA = _CORPORA
		self.DEFAULT_CORPUS = _DEFAULT
	
	def add_listener(self, listener):
		self.listeners.append(listener)
		
	def notify_listeners(self, event):
		for each in self.listeners:
			each.fire_event(event)
			
	def load_corpus(self, name):
		self.selected_corpus = name
		self.collocations = None
		runner_thread = self.LoadCorpus(name, self)
		runner_thread.start()

	def non_default_corpora(self):
		copy = []
		copy.extend(self.CORPORA.keys())
		copy.remove(self.DEFAULT_CORPUS)
		copy.sort()
		return copy
	
	def is_last_page(self, number):
		return False
	
	class LoadCorpus(threading.Thread):
		def __init__(self, name, model):
			self.model, self.name = model, name
			threading.Thread.__init__(self)
			
		def run(self):
			try:
				words = self.model.CORPORA[self.name]()
				print "got words " + str(len(words))
				from operator import itemgetter
				text = filter(lambda w: len(w) > 2, words)
				fd = FreqDist(tuple(text[i:i+2]) for i in range(len(text)-1))
				print "creating scored"
				scored = [((w1,w2), fd[(w1,w2)] ** 3 / float(self.vocab()[w1] * self.vocab()[w2])) for w1, w2 in fd]
				print "got scored"
				scored.sort(key=itemgetter(1), reverse=True)
				print "sorted scored"
				self.model.collocations = map(itemgetter(0), scored)
				print "calling listener"
				self.model.notify_listeners(CORPUS_LOADED_EVENT)
			except Exception, e:
				print e 
				self.model.notify_listeners(ERROR_LOADING_CORPUS_EVENT)

		def vocab(self):
			if "_vocab" not in self.__dict__:
				print "Building vocabulary index..."
				self._vocab = FreqDist()
			return self._vocab


def collocations():

	colloc_strings = [w1 + ' ' + w2 for w1, w2 in self._collocations[:num]]

def launch_view():
    c = CollocationsView()
    c.mainloop()
        
def demo():
    launch_view()

if __name__ == '__main__':
    demo()
