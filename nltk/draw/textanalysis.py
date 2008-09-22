# Natural Language Toolkit: Helper functions for analysing text
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
from nltk.draw import *
from Tkinter import *
from nltk.corpus import gutenberg
from nltk.text import Text
from nltk import FreqDist, bigrams
import matplotlib
matplotlib.use('TkAgg')
import pylab
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import sys

def plot_word_freq_dist(text):
    fd = text.vocab()
    samples = fd.sorted()[:50]
    values = [fd[sample] for sample in samples]
    values = [sum(values[:i+1]) * 100.0/fd.N() for i in range(len(values))]
    plot_values(samples, values)
    
def plot_values(samples, values):    
    v = PylabTkView(samples, values)
    v.mainloop()
    
class PylabTkView(object):
    
    def __init__(self, samples, values):
        self.top = Tk()
        self.top.geometry('550x450+50+50')
        self.top.title('NLTK Text Analysis')
        self.top.bind('<Control-q>', self.destroy)
        self.top.bind("<Destroy>", self.destroy)
        self.top.minsize(550,450)
        self.main_frame = Frame(self.top, dict(padx=1, pady=1, border=1))
        self.add_pylab_contents(samples, values)
        self.main_frame.pack(fill="both", expand=1)
        
    def add_pylab_contents(self, samples, values):
        f = Figure(figsize=(5,4), dpi=100)
        a = f.add_subplot(111)
        p = a.plot(values)
        a.add_axes(xlabel="Samples", ylabel="Cumulative Percentage")
        pylab.xticks(range(len(samples)), [str(s) for s in samples], rotation=90)
        
        canvas = FigureCanvasTkAgg(f, master=self.main_frame)
        canvas.show()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=1)
        toolbar = NavigationToolbar2TkAgg(canvas, self.main_frame)
        toolbar.update()
        canvas._tkcanvas.pack(side="top", fill="both", expand=1)
        
    def destroy(self, *e):
        sys.exit()        
        
    def mainloop(self, *args, **kwargs):
        if in_idle(): return
        self.top.mainloop(*args, **kwargs)

def demo():
    t1 = Text(gutenberg.words('melville-moby_dick.txt'))
    plot_word_freq_dist(t1)
    
if __name__ == '__main__':
    demo()
