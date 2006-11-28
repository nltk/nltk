"""
This is a sample model to accompany U{sem2.cfg grammar}, and is
intended to be imported as a module.

It presupposes that the L{nltk_lite.semantics} module has already been
imported.
"""
import nltk_lite.semantics as semantics
from nltk_lite.semantics.chat_80 import val_load

val = val_load('chat')

dom = val.domain
#Bind C{dom} to the C{domain} property of C{val}."""

m = semantics.Model(dom, val)
#Initialize a model with parameters C{dom} and C{val}.

g = semantics.Assignment(dom)
#Initialize a variable assignment with parameter C{dom}."""
