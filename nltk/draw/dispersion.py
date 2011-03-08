# Natural Language Toolkit: Dispersion Plots
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A utility for displaying lexical dispersion.
"""

def dispersion_plot(text, words):
    """
    Generate a lexical dispersion plot.

    @param text: The source text
    @type text: C{list} or C{enum} of C{str}
    @param words: The target words
    @type words: C{list} of C{str}
    """

    try:
        import pylab
    except ImportError:
        raise ValueError('The plot function requires the matplotlib package (aka pylab).'
                     'See http://matplotlib.sourceforge.net/')

    text = list(text)
    words.reverse()
    points = [(x,y) for x in range(len(text))
                    for y in range(len(words))
                    if text[x] == words[y]]
    if points:
        x, y = zip(*points)
    else:
        x = y = ()
    pylab.plot(x, y, "b|", scalex=.1)
    pylab.yticks(range(len(words)), words, color="b")
    pylab.ylim(-1, len(words))
    pylab.title("Lexical Dispersion Plot")
    pylab.xlabel("Word Offset")
    pylab.show()

if __name__ == '__main__':
    from nltk.corpus import gutenberg
    words = ['Elinor', 'Marianne', 'Edward', 'Willoughby']
    dispersion_plot(gutenberg.words('austen-sense.txt'), words)
