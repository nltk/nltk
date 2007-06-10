import Tkinter as tk
from morphology import KimmoMorphology
from fsa import FSA

class KimmoGUI(object):
    def __init__(self, ruleset, startTk=False):
        import Tkinter as tk
        if startTk: self._root = tk.Tk()
        else: self._root = tk.Toplevel()
        
        self.ruleset = ruleset
        self.rules = ruleset.rules()
        self.lexicon = ruleset.morphology()

        frame = tk.Frame(self._root)
        tk.Label(frame, text='Rules').pack(side=tk.TOP)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
        exportselection=0)
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        frame2 = tk.Frame(self._root)
        tk.Label(frame2, text='Steps').pack(side=tk.TOP)
        scrollbar2 = tk.Scrollbar(frame2, orient=tk.VERTICAL)
        self.steplist = tk.Listbox(frame2, yscrollcommand=scrollbar2.set,
        font='Sans 10', width='40', exportselection=0)
        scrollbar2.config(command=self.steplist.yview)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        self.steplist.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        wordbar = tk.Frame(self._root)
        self.genbox = tk.Entry(wordbar, width=30, font="Courier 14")
        genbutton = tk.Button(wordbar, text="Generate ->",
        command=self.generate)
        recbutton = tk.Button(wordbar, text="<- Recognize",
        command=self.recognize)
        self.recbox = tk.Entry(wordbar, width=30, font="Courier 14")
        self.resultlabel = tk.Label(wordbar, justify=tk.CENTER, text='')
        
        self.genbox.pack(side=tk.LEFT)
        genbutton.pack(side=tk.LEFT)
        self.resultlabel.pack(side=tk.LEFT, fill=tk.X, expand=1)
        self.recbox.pack(side=tk.RIGHT)
        recbutton.pack(side=tk.RIGHT)
        wordbar.pack(side=tk.TOP, fill=tk.X, expand=1)
        frame.pack(side=tk.LEFT, fill=tk.Y, expand=1)
        frame2.pack(side=tk.LEFT, fill=tk.Y, expand=1)
        
        if self.lexicon: self.listbox.insert(tk.END, 'Lexicon')
        else: self.listbox.insert(tk.END, '(no lexicon)')
        for rule in self.rules:
            self.listbox.insert(tk.END, rule.name())
        
        self.rframe = tk.Frame(self._root)
        self.rframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        self.graph_widget = None
        self.listbox.bind("<ButtonRelease-1>", self.graph_selected)
        self.steplist.bind("<ButtonRelease-1>", self.step_selected)

        self._root.bind('<Up>', self.select_up)
        self._root.bind('<Down>', self.select_down)
        
        self.widget_store = {}
        self.steps = []
        for i in range(len(self.rules), -1, -1): # yes, including the last one.
            self.draw_rule(i)
        
        if startTk:
            tk.mainloop()

    def step_selected(self, event):
        values = self.steplist.curselection()
        if len(values) == 0: return
        index = int(values[0])
        self.highlight_states(self.steps[index][1], self.steps[index][2])
        #self.draw_rule(index)
        
    def graph_selected(self, event):
        values = self.listbox.curselection()
        if len(values) == 0: return
        index = int(values[0])
        self.draw_rule(index)

    def select_up(self, event):
        values = self.steplist.curselection()
        if len(values) == 0: values = [0]
        index = int(values[0])
        if index == 0: return
        self.steplist.selection_clear(0, tk.END)
        self.steplist.selection_set(index-1)
        self.step_selected(event)

    def select_down(self, event):
        values = self.steplist.curselection()
        if len(values) == 0: values = [0]
        index = int(values[0])
        if index == len(self.steps) - 1: return
        self.steplist.selection_clear(0, tk.END)
        self.steplist.selection_set(index+1)
        self.step_selected(event)

    def draw_rule(self, index):
        if index == 0:
            rule = self.lexicon
        else: rule = self.rules[index-1]
        if rule is None: return
        if self.graph_widget is not None:
            self.graph_widget.pack_forget()
        if index-1 in self.widget_store:
            self.graph, self.graph_widget = self.widget_store[index-1]
            self.graph_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        else:
            self.graph_widget = self.wrap_pygraph(rule)
            self.graph_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
            self.widget_store[index-1] = (self.graph, self.graph_widget)
    
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
    
    def highlight_states(self, states, morph):
        select = self.listbox.curselection() or 0
        self.listbox.delete(0, tk.END)
        for (index, stored) in self.widget_store.items():
            graph, widget = stored
            if index == -1: state = morph
            else: state = states[index]
            graph.deHighlightNodes()
            graph.HighlightNode(state, None)
        for index in range(-1, len(self.rules)):
            if index == -1:
                if self.lexicon:
                    state = morph
                    name = 'Lexicon'
                    text = '%s [%s]' % (name, state)
                else: text = '(no lexicon)'
            else:
                state = states[index]
                name = self.rules[index].name()
                text = '%s [%s]' % (name, state)
            self.listbox.insert(tk.END, text)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(select)
    
    def step(self, pairs, curr, rules, prev_states, states, morphology_state,
    word):
        lexical = ''.join(p.input() for p in pairs)
        surface = ''.join(p.output() for p in pairs)
        text = '%s<%s> | %s<%s>'%(lexical, curr.input(), surface, curr.output())
        blocked = []
        for rule, state in zip(rules, states):
            if str(state).lower() in ['0', 'reject']:
                blocked.append(rule.name())
        if blocked:
             text +=' [%s failed]' % (', '.join(blocked))
        self.steplist.insert(tk.END, text)
        self.steps.append((text, states, morphology_state, word))

    def generate(self):
        if not self.genbox.get(): return
        gentext = self.genbox.get().split()[0]
        result = " ".join(self.ruleset.generate(gentext, self))
        self.recbox.delete(0, tk.END)
        self.recbox.insert(0, result)

    def recognize(self):
        if not self.recbox.get(): return
        rectext = self.recbox.get().split()[0]
        result = ", ".join('%s (%s)' % (word, feat) for (word, feat) in
          self.ruleset.recognize(rectext, self))
        self.genbox.delete(0, tk.END)
        self.genbox.insert(0, result)

    def succeed(self, pairs):
        lexical = ''.join(p.input() for p in pairs)
        surface = ''.join(p.output() for p in pairs)
        self.steplist.insert(tk.END, 'SUCCESS: %s / %s' % (lexical, surface))
        self.num_results += 1
        if self.num_results == 1:
            self.resultlabel.configure(text='1 result')
        else:
            self.resultlabel.configure(text='%d results' % self.num_results)
        self.steps.append((lexical, [None]*len(self.rules), None, ''))
        
    def reset(self):
        self.steplist.delete(0, tk.END)
        self.num_results = 0
        self.steps = []
        self.resultlabel.configure(text='')

# vim:et:ts=4:sts=4:sw=4:
