import Tkinter
import nltk.corpus

class CorpusFrame:
    """
    Tk widget that displays a corpus, allowing the user to select the group
    and item. When both are selected, it will display both the raw contents
    of the item and its tokenized form.

    TODO: make the tokenized form prettier - display each item of the
    sequence on a new line, maybe with colour? Also could synchronise
    scrolling of raw and tokenized panes, and have synchronised selection.
    Searching would be nice too!
    """
    def __init__(self, root, corpora):
	self._root = root
	self._corpora = corpora
	self._token_cache = {}
	self._current_item = None

	# Create a frame (window)
	frame = Tkinter.Frame(root)
	frame.pack(expand=1, fill='both')

	# Set up a grid of widgets
	fill = Tkinter.W + Tkinter.E + Tkinter.N + Tkinter.S

	Tkinter.Label(frame, text='groups:').grid(row=0, sticky=Tkinter.W)
	scrollbar = Tkinter.Scrollbar(frame, orient=Tkinter.VERTICAL)
	self._group_list = Tkinter.Listbox(frame, yscrollcommand=scrollbar.set)
	scrollbar.config(command=self._group_list.yview)
	scrollbar.grid(column=1, row=1, sticky=fill)
	self._group_list.grid(row=1, sticky=fill)
	
	Tkinter.Label(frame, text='items:').grid(row=2, sticky=Tkinter.W)
	scrollbar = Tkinter.Scrollbar(frame, orient=Tkinter.VERTICAL)
	self._item_list = Tkinter.Listbox(frame, yscrollcommand=scrollbar.set)
	scrollbar.config(command=self._item_list.yview)
	scrollbar.grid(column=1, row=3, sticky=fill)
	self._item_list.grid(row=3, sticky=fill)

	Tkinter.Label(frame, text='raw text:').grid(column=2, row=0,
						    sticky=Tkinter.W)
	self._rsb = Tkinter.Scrollbar(frame, orient=Tkinter.VERTICAL)
	self._raw_text = Tkinter.Text(frame, yscrollcommand=self._rsb.set)
        #self._rsb.config(command=self._raw_text.yview)
	self._rsb.config(command=self._raw_text_view)
	self._rsb.grid(column=3, row=1, sticky=fill)
	self._raw_text.grid(column=2, row=1, sticky=fill)

	Tkinter.Label(frame, text='tokens:').grid(column=2, row=2,
						  sticky=Tkinter.W)
	self._tsb = Tkinter.Scrollbar(frame, orient=Tkinter.VERTICAL)
	self._tokenized_text = Tkinter.Text(frame, yscrollcommand=self._tsb.set)
        #self._tsb.config(command=self._tokenized_text.yview)
	self._tsb.config(command=self._tokenized_text_view)
	self._tsb.grid(column=3, row=3, sticky=fill)
	self._tokenized_text.grid(column=2, row=3, sticky=fill)

	# Set up the menu
	menu = Tkinter.Menu(frame)
	root.config(menu=menu)
	corpus_menu = Tkinter.Menu(menu)
	menu.add_cascade(label='Corpus', menu=corpus_menu)
	for corpus in corpora:
	    corpus_menu.add_radiobutton(label=corpus.name(), 
				command=lambda c=corpus: self._change_corpus(c))
	corpus_menu.add_separator()
	corpus_menu.add_command(label='Exit', command=root.quit)

	# Register call-backs for selection in each list box
	self._group_list.bind('<Double-Button-1>', self._group_selected)
	self._item_list.bind('<Double-Button-1>', self._item_selected)

	# Default to the first corpus
	self._change_corpus(corpora[0])

    def _change_corpus(self, corpus):
	# Populate the group and item list boxes
	self._group_list.delete(0, Tkinter.END)
	self._group_list.insert(Tkinter.END, '<all groups>')
	for group in corpus.groups():
	    self._group_list.insert(Tkinter.END, group)
	self._group_list.activate(0)
	self._item_list.delete(0, Tkinter.END)
	for item in corpus.items():
	    self._item_list.insert(Tkinter.END, item)

	# Clear the raw/token displays
	self._current_item = None
	self._raw_text.delete(1.0, Tkinter.END)
	self._tokenized_text.delete(1.0, Tkinter.END)

	# Cache the corpus object and display its name as the window title
	self._corpus = corpus
	self._root.title('%s: NLTK corpus viewer' % corpus.name())

    def _group_selected(self, event):
	group_index = self._group_list.curselection()[0]
	if int(group_index) == 0:
	    group = None
	else:
	    group = self._group_list.get(group_index)

	# Repopulate the items
	self._item_list.delete(0, Tkinter.END)
	items = self._corpus.items(group)
	for item in items:
	    self._item_list.insert(Tkinter.END, item)

	if self._current_item not in items:
	    # Clear the raw/token displays
	    self._current_item = None
	    self._raw_text.delete(1.0, Tkinter.END)
	    self._tokenized_text.delete(1.0, Tkinter.END)

    def _item_selected(self, event):
	item_index = self._item_list.curselection()[0]
	item = self._item_list.get(item_index)

	# Clear the text widgets if item has changed
	if self._current_item != item:
	    self._current_item = item
	    self._raw_text.delete(1.0, Tkinter.END)
	    self._tokenized_text.delete(1.0, Tkinter.END)

	    # Repopulate
	    self._raw_text.insert(Tkinter.END, self._corpus.read(item))
	    if not self._token_cache.has_key(item):
		self._token_cache[item] = `self._corpus.read(item)`
	    self._tokenized_text.insert(Tkinter.END, self._token_cache[item])

    def _raw_text_view(self, *args):
        self._raw_text.yview(*args)
        low, high = self._rsb.get()
        self._tokenized_text.yview(Tkinter.MOVETO, str(low))

    def _tokenized_text_view(self, *args):
        self._tokenized_text.yview(*args)
        low, high = self._tsb.get()
        self._raw_text.yview(Tkinter.MOVETO, str(low))

def demo():
    root = Tkinter.Tk()
    cf = CorpusFrame(root, [nltk.corpus.stopwords,
			    nltk.corpus.brown,
			    nltk.corpus.chunking,
			    nltk.corpus.names,
			    nltk.corpus.treebank])
    return root.mainloop()

if __name__ == '__main__':
    demo()
