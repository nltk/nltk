# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals
import inspect
import sys

import nltk
from nltk import tag

#multi-feature templates (recommended)
from nltk.tag.brill.task.postagging import Word, Pos
from nltk.tag.brill.template import Template

def nltkdemo18():
    """
    Return 18 templates, from the original nltk demo, in multi-feature syntax
    """
    return [
        Template(Pos([-1])),
        Template(Pos([1])),
        Template(Pos([-2])),
        Template(Pos([2])),
        Template(Pos([-2, -1])),
        Template(Pos([1, 2])),
        Template(Pos([-3, -2, -1])),
        Template(Pos([1, 2, 3])),
        Template(Pos([-1]), Pos([1])),
        Template(Word([-1])),
        Template(Word([1])),
        Template(Word([-2])),
        Template(Word([2])),
        Template(Word([-2, -1])),
        Template(Word([1, 2])),
        Template(Word([-3, -2, -1])),
        Template(Word([1, 2, 3])),
        Template(Word([-1]), Word([1])),
    ]

def nltkdemo18plus():
    """
    Return 18 templates, from the original nltk demo, and additionally a few
    multi-feature ones (the motivation is easy comparison with nltkdemo18)
    """
    return nltkdemo18() + [
        Template(Word([-1]), Pos([1])),
        Template(Pos([-1]), Word([1])),
        Template(Word([-1]), Word([0]), Pos([1])),
        Template(Pos([-1]), Word([0]), Word([1])),
        Template(Pos([-1]), Word([0]), Pos([1])),
    ]

def fntbl37():
    """
    Return 37 templates taken from the postagging task of the
    fntbl distribution http://www.cs.jhu.edu/~rflorian/fntbl/
    (37 is after excluding a handful which do not condition on Pos[0];
    fntbl can do that but the current nltk implementation cannot.)
    """
    return [
        Template(Word([0]), Word([1]), Word([2])),
        Template(Word([-1]), Word([0]), Word([1])),
        Template(Word([0]), Word([-1])),
        Template(Word([0]), Word([1])),
        Template(Word([0]), Word([2])),
        Template(Word([0]), Word([-2])),
        Template(Word([1, 2])),
        Template(Word([-2, -1])),
        Template(Word([1, 2, 3])),
        Template(Word([-3, -2, -1])),
        Template(Word([0]), Pos([2])),
        Template(Word([0]), Pos([-2])),
        Template(Word([0]), Pos([1])),
        Template(Word([0]), Pos([-1])),
        Template(Word([0])),
        Template(Word([-2])),
        Template(Word([2])),
        Template(Word([1])),
        Template(Word([-1])),
        Template(Pos([-1]), Pos([1])),
        Template(Pos([1]), Pos([2])),
        Template(Pos([-1]), Pos([-2])),
        Template(Pos([1])),
        Template(Pos([-1])),
        Template(Pos([-2])),
        Template(Pos([2])),
        Template(Pos([1, 2, 3])),
        Template(Pos([1, 2])),
        Template(Pos([-3, -2, -1])),
        Template(Pos([-2, -1])),
        Template(Pos([1]), Word([0]), Word([1])),
        Template(Pos([1]), Word([0]), Word([-1])),
        Template(Pos([-1]), Word([-1]), Word([0])),
        Template(Pos([-1]), Word([0]), Word([1])),
        Template(Pos([-2]), Pos([-1])),
        Template(Pos([1]), Pos([2])),
        Template(Pos([1]), Pos([2]), Word([1]))
    ]

def brill24():
    """
    Return 24 templates of the seminal TBL paper, Brill (1995)
    """
    return [
        Template(Pos([-1])),
        Template(Pos([1])),
        Template(Pos([-2])),
        Template(Pos([2])),
        Template(Pos([-2, -1])),
        Template(Pos([1, 2])),
        Template(Pos([-3, -2, -1])),
        Template(Pos([1, 2, 3])),
        Template(Pos([-1]), Pos([1])),
        Template(Pos([-2]), Pos([-1])),
        Template(Pos([1]), Pos([2])),
        Template(Word([-1])),
        Template(Word([1])),
        Template(Word([-2])),
        Template(Word([2])),
        Template(Word([-2, -1])),
        Template(Word([1, 2])),
        Template(Word([-1, 0])),
        Template(Word([0, 1])),
        Template(Word([0])),
        Template(Word([-1]), Pos([-1])),
        Template(Word([1]), Pos([1])),
        Template(Word([0]), Word([-1]), Pos([-1])),
        Template(Word([0]), Word([1]), Pos([1])),
    ]


def describe_template_sets():
    """
    Print the available template sets in this demo, with a short description"
    """
    #a bit of magic to get all functions in this module
    templatesets = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
    for (name, obj) in templatesets:
        if name == "describe_template_sets": continue
        print(name, obj.__doc__, "\n")

