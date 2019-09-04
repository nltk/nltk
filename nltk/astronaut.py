# -*- coding: utf-8 -*-
# Natural Language Toolkit: Spacy wrapper
#
# Copyright (C) 2001-2019 NLTK Project
# Authors:
# Contributors:
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
This is SpaCy wrapper that overrides the existing NLTK functions:
    - word_tokenize
    - pos_tag
It'll emulate the NLTK API to the NLP functions,
but uses the `en_core_web_sm` models from SpaCy (https://spacy.io/models)
"""

import sys

try: # Try importing SpaCy if it's installed.
    import spacy
    import en_core_web_sm
    nlp = en_core_web_sm.load()

    module = sys.modules['nltk']

    def spacy_pos_tag(input):
        if all(isinstance(item, str) for item in input):
            input = " ".join(input)
        return [(token.text, token.tag_) for token in nlp(input)]

    module.word_tokenize = lambda input: [token.text for token in nlp(input)]
    module.pos_tag = lambda input: spacy_pos_tag(input)
except ImportError:
    pass
