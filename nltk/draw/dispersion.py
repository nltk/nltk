# Natural Language Toolkit: Dispersion Plots
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A utility for displaying lexical dispersion.
"""

from Tkinter import Canvas

def plot(text, words, rowheight=15, rowwidth=800):
    """
    Generate a lexical dispersion plot.

    @param text: The source text
    @type text: C{list} or C{enum} of C{str}
    @param words: The target words
    @type words: C{list} of C{str}
    @param rowheight: Pixel height of a row
    @type rowheight: C{int}
    @param rowwidth: Pixel width of a row
    @type rowwidth: C{int}

    """
    canvas = Canvas(width=rowwidth, height=rowheight*len(words))
    text = list(text)
    scale = float(rowwidth)/len(text)
    position = 0
    for word in text:
        for i in range(len(words)):
            x = position * scale
            if word == words[i]:
                y = i * rowheight
                canvas.create_line(x, y, x, y+rowheight-1)
        position += 1
    canvas.pack()
    canvas.mainloop()

if __name__ == '__main__':
    from nltk.corpus import gutenberg
    from nltk.draw import dispersion
    words = ['Elinor', 'Marianne', 'Edward', 'Willoughby']
    dispersion.plot(gutenberg.words('austen-sense.txt'), words)
