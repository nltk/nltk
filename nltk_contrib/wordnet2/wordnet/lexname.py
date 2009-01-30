# Natural Language Toolkit: Wordnet Interface
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from util import *

# Lexname class

class Lexname(object):
   dict = {}
   lexnames = []
   
   def __init__(self, name, category):
       self.name = name
       self.category = category
       self.id = len(Lexname.dict)
       Lexname.dict[name] = self
       Lexname.lexnames.append(self)
   
   def __str__(self):
       return self.name

   __repr__ = __str__

# Create Lexname objects, originally sourced from the lexnames file available
# as a patch from the Pywordnet sourceforge site. This list may be updated by
# the creators of Wordnet at any time.
# It must remain in the given order:

Lexname("adj.all", ADJECTIVE)
Lexname("adj.pert", ADJECTIVE)
Lexname("adv.all", ADVERB)
Lexname("noun.Tops", NOUN)
Lexname("noun.act", NOUN)
Lexname("noun.animal", NOUN)
Lexname("noun.artifcact", NOUN)
Lexname("noun.attribute", NOUN)
Lexname("noun.body", NOUN)
Lexname("noun.cognition", NOUN)
Lexname("noun.communication", NOUN)
Lexname("noun.event", NOUN)
Lexname("noun.feeling", NOUN)
Lexname("noun.food", NOUN)
Lexname("noun.group", NOUN)
Lexname("noun.location", NOUN)
Lexname("noun.motive", NOUN)
Lexname("noun.object", NOUN)
Lexname("noun.person", NOUN)
Lexname("noun.phenomenon", NOUN)
Lexname("noun.plant", NOUN)
Lexname("noun.possession", NOUN)
Lexname("noun.process", NOUN)
Lexname("noun.quantity", NOUN)
Lexname("noun.relation", NOUN)
Lexname("noun.shape", NOUN)
Lexname("noun.state", NOUN)
Lexname("noun.substance", NOUN)
Lexname("noun.time", NOUN)
Lexname("verb.body", VERB)
Lexname("verb.change", VERB)
Lexname("verb.cognition", VERB)
Lexname("verb.communication", VERB)
Lexname("verb.competition", VERB)
Lexname("verb.consumption", VERB)
Lexname("verb.contact", VERB)
Lexname("verb.creation", VERB)
Lexname("verb.emotion", VERB)
Lexname("verb.motion", VERB)
Lexname("verb.perception", VERB)
Lexname("verb.possession", VERB)
Lexname("verb.social", VERB)
Lexname("verb.stative", VERB)
Lexname("verb.weather", VERB)
Lexname("adj.ppl", ADJECTIVE)
