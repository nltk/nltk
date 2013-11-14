# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

#one-feature templates (for backwards compatibility)
from nltk.tag.brill.nltk2 import ProximateWordsRule as Word1F
from nltk.tag.brill.nltk2 import ProximateTagsRule as Tag1F
from nltk.tag.brill.nltk2 import ProximateTokensTemplate as Template1F

#multi-feature templates (recommended)
from nltk.tag.brill.application.postagging import Word, Tag
from nltk.tag.brill.template import Template

def nltkdemo18old():
    """
    Return 18 templates, from the nltk2 demo, in the original
    single-feature syntax
    """
    return [
        Template1F(Tag1F, (-1, -1)),
        Template1F(Tag1F, ( 1, 1)),
        Template1F(Tag1F, (-2, -2)),
        Template1F(Tag1F, ( 2, 2)),
        Template1F(Tag1F, (-2, -1)),
        Template1F(Tag1F, ( 1, 2)),
        Template1F(Tag1F, (-3, -1)),
        Template1F(Tag1F, ( 1, 3)),
        Template1F(Tag1F, (-1, -1), (1, 1)),
        Template1F(Word1F, (-1, -1)),
        Template1F(Word1F, ( 1, 1)),
        Template1F(Word1F, (-2, -2)),
        Template1F(Word1F, ( 2, 2)),
        Template1F(Word1F, (-2, -1)),
        Template1F(Word1F, ( 1, 2)),
        Template1F(Word1F, (-3, -1)),
        Template1F(Word1F, ( 1, 3)),
        Template1F(Word1F, (-1, -1), (1, 1)),
    ]

def nltkdemo18():
    """
    Return 18 templates, from the original nltk demo, in multi-feature syntax
    """
    return [
        Template(Tag([-1])),
        Template(Tag([1])),
        Template(Tag([-2])),
        Template(Tag([2])),
        Template(Tag([-2, -1])),
        Template(Tag([1, 2])),
        Template(Tag([-3, -2, -1])),
        Template(Tag([1, 2, 3])),
        Template(Tag([-1]), Tag([1])),
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
    18 templates, from the original nltk demo, and additionally a few
    multi-feature ones (the motivation is easy comparison with nltkdemo18)
    """
    return nltkdemo18() + [
        Template(Word([-1]), Tag([1])),
        Template(Tag([-1]), Word([1])),
        Template(Word([-1]), Word([0]), Tag([1])),
        Template(Tag([-1]), Word([0]), Word([1])),
        Template(Tag([-1]), Word([0]), Tag([1])),
    ]

def fntbl37():
    """
    Return 37 templates[1] taken from the postagging task of the fntbl distribution
    http://www.cs.jhu.edu/~rflorian/fntbl/
    [1] after excluding a handful which do not condition on Tag[0];
    fntbl can do that but the current nltk implementation cannot
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
        Template(Word([0]), Tag([2])),
        Template(Word([0]), Tag([-2])),
        Template(Word([0]), Tag([1])),
        Template(Word([0]), Tag([-1])),
        Template(Word([0])),
        Template(Word([-2])),
        Template(Word([2])),
        Template(Word([1])),
        Template(Word([-1])),
        Template(Tag([-1]), Tag([1])),
        Template(Tag([1]), Tag([2])),
        Template(Tag([-1]), Tag([-2])),
        Template(Tag([1])),
        Template(Tag([-1])),
        Template(Tag([-2])),
        Template(Tag([2])),
        Template(Tag([1, 2, 3])),
        Template(Tag([1, 2])),
        Template(Tag([-3, -2, -1])),
        Template(Tag([-2, -1])),
        Template(Tag([1]), Word([0]), Word([1])),
        Template(Tag([1]), Word([0]), Word([-1])),
        Template(Tag([-1]), Word([-1]), Word([0])),
        Template(Tag([-1]), Word([0]), Word([1])),
        Template(Tag([-2]), Tag([-1])),
        Template(Tag([1]), Tag([2])),
        Template(Tag([1]), Tag([2]), Word([1]))
    ]

def brill24():
    """
    Return 24 templates of the seminal TBL paper, Brill (1995)
    """
    return [
        Template(Tag([-1])),
        Template(Tag([1])),
        Template(Tag([-2])),
        Template(Tag([2])),
        Template(Tag([-2, -1])),
        Template(Tag([1, 2])),
        Template(Tag([-3, -2, -1])),
        Template(Tag([1, 2, 3])),
        Template(Tag([-1]), Tag([1])),
        Template(Tag([-2]), Tag([-1])),
        Template(Tag([1]), Tag([2])),
        Template(Word([-1])),
        Template(Word([1])),
        Template(Word([-2])),
        Template(Word([2])),
        Template(Word([-2, -1])),
        Template(Word([1, 2])),
        Template(Word([-1, 0])),
        Template(Word([0, 1])),
        Template(Word([0])),
        Template(Word([-1]), Tag([-1])),
        Template(Word([1]), Tag([1])),
        Template(Word([0]), Word([-1]), Tag([-1])),
        Template(Word([0]), Word([1]), Tag([1])),
    ]


def wordfirst():
    """
    To investigate the impact of putting most specific condition first
    For the record: practically no gain
    """
    return [Template(Word([0]), Tag([-1]), Tag([-2]))]

def tagsfirst():
    """
    To investigate the impact of putting most specific condition last
    """
    return [Template(Tag([-1]), Tag([-2]), Word([0]))]



def describe_template_sets():
    """
    Print the available template sets in this demo, with a short description"
    """
    from nltk.tag.brill.demo import postagging_templates
    templatesets = [t for t in dir(postagging_templates) ]
    for t in templatesets:
        print(t.name, "\n  ", t.__doc__, "\n")


