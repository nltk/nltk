# Natural Language Toolkit: Lesk Algorithm
#
# Author: Liling Tan <alvations@gmail.com>
#
# Copyright (C) 2001-2014 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import string

from nltk import word_tokenize
from nltk.corpus import wordnet as wn

def compare_overlaps_greedy(context, synsets_signatures, pos):
  """
  Calculate overlaps between the context sentence and the synset_signature
  and returns the synset with the highest overlap.
  
  Note: Greedy algorithm only keeps the best sense, see http://goo.gl/OWSfOZ
  Keeping greedy algorithm for documentary sake because original_lesk is greedy.
  """
  max_overlaps = 0; lesk_sense = None
  for ss in synsets_signatures:
    if pos and str(ss.pos()) is not pos: # Skips different POS
      continue
    overlaps = set(synsets_signatures[ss]).intersection(context)
    if len(overlaps) > max_overlaps:
      lesk_sense = ss
      max_overlaps = len(overlaps)    
  return lesk_sense

def lesk(context_sentence, ambiguous_word, pos=None, dictionary=None):
  """
  This function is the implementation of the original Lesk algorithm (1986).
  It requires a dictionary which contains the definition of the different
  sense of each word. See http://goo.gl/8TB15w
  
  USAGE:
  >>> from nltk.sem import lesk
  >>> sent = "I went to the bank to deposit money."
  >>> word = "bank"; pos = "n"
  >>> lesk(sent, word, pos)
  Synset('depository_financial_institution.n.01')
  """
  if not dictionary:
    dictionary = {ss:ss.definition().split() \
                  for ss in wn.synsets(ambiguous_word)}
  best_sense = compare_overlaps_greedy(word_tokenize(context_sentence), \
                                       dictionary, pos)
  return best_sense