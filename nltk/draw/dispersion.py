# Natural Language Toolkit: Dispersion Plots
#
# Copyright (C) 2001-2022 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A utility for displaying lexical dispersion.
"""


def dispersion_plot(text, words, ignore_case=False, title="Lexical Dispersion Plot"):
    """
    Generate a lexical dispersion plot.

    :param text: The source text
    :type text: list(str) or enum(str)
    :param words: The target words
    :type words: list of str
    :param ignore_case: flag to set if case should be ignored when searching text
    :type ignore_case: bool
    """

    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ValueError(
            "The plot function requires matplotlib to be installed."
            "See https://matplotlib.org/"
        ) from e

    text = list(text)
    words.reverse()

    if ignore_case:
        words_to_comp = list(map(str.lower, words))
        text_to_comp = list(map(str.lower, text))
    else:
        words_to_comp = words
        text_to_comp = text

    points = [
        (x, y)
        for x in range(len(text_to_comp))
        for y in range(len(words_to_comp))
        if text_to_comp[x] == words_to_comp[y]
    ]
    if points:
        x, y = list(zip(*points))
    else:
        x = y = ()
    _, ax = plt.subplots()
    ax.plot(x, y, "b|")
    ax.set_yticks(list(range(len(words))), words, color="b")
    ax.set_ylim(-1, len(words))
    ax.set_title(title)
    ax.set_xlabel("Word Offset")
    return ax


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    from nltk.corpus import gutenberg

    words = ["Elinor", "Marianne", "Edward", "Willoughby"]
    dispersion_plot(gutenberg.words("austen-sense.txt"), words)
    plt.show()
