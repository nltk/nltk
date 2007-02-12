import Tkinter as tk
from morphology import KimmoMorphology

class GraphGUI(object):
    def __init__(self, ruleset, startTk=False):
        import Tkinter as tk
        if startTk: self._root = tk.Tk()
        else: self._root = tk.Toplevel()

        frame = tk.Frame(self._root)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        frame.pack(side=tk.LEFT, fill=tk.Y, expand=1)
        
        self.rules = ruleset.rules()
        self.lexicon = ruleset.morphology()
        
        self.listbox.insert(tk.END, 'Lexicon')
        for rule in self.rules:
            self.listbox.insert(tk.END, rule.name())
        
        self.rframe = tk.Frame(self._root)
        self.rframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        self.graph_widget = None
        self.listbox.bind("<ButtonRelease-1>", self.list_has_changed)
        
        self.widget_store = {}
        if startTk:
            tk.mainloop()

    def list_has_changed(self, value):
        values = self.listbox.curselection()
        if len(values) == 0: return
        index = int(values[0])
        self.draw_rule(index)

    def draw_rule(self, index):
        if self.graph_widget is not None:
            self.graph_widget.pack_forget()
        if index == 0: rule = self.lexicon
        else: rule = self.rules[index-1]
        if index in self.widget_store:
            self.graph, self.graph_widget = self.widget_store[index]
            self.graph_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        else:
            self.graph_widget = self.wrap_pygraph(rule)
            self.graph_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
            self.widget_store[index] = (self.graph, self.graph_widget)
    
    def wrap_pygraph(self, rule):
        if isinstance(rule, KimmoMorphology):
            title = 'Lexicon'
            labels = False
        else:
            title = rule.name()
            labels = True
        frame = tk.Frame(self.rframe)
        self.graph = rule.fsa().show_pygraph(title=title, labels=labels, root=frame)
        return frame
