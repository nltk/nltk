# Natural Language Toolkit: Treebank Tagged Tokenizer
#
# Copyright (C) 2004 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

Single tokenizer class for loading part-of-speech tagged data from the Penn
Treebank. This extends the L{TaggedTokenizer} to support the additional markup
present in these files.

@group Tokenizers: TreebankTaggedTokenizer
"""

from nltk.tagger import TaggedTokenizer
from nltk.chktype import chktype
from nltk.token import Token, SentIndexLocation, ParaIndexLocation
import re

class TreebankTaggedTokenizer(TaggedTokenizer):
    """
    A tokenizer that divides a string of tagged words into subtokens.
    Words should be separated by whitespace, and each word should have
    the form C{I{text}/I{tag}}, where C{I{text}} specifies the word's
    C{TEXT} property, and C{I{tag}} specifies its C{TAG} property.
    Words that do not contain a slash are assigned a C{tag} of C{None},
    except those special words [, ], and a line of = characters. These
    words are removed from the source.

    This tokenizer uses the lines of = characters to separate paragraphs
    and empty lines which follow a line ending with a word tagged with a 
    period to determine the end of each sentence. The output of the
    tokenization is stored in the SUBTOKENS with locations indicating the
    paragraph and sentence for each token.
    
    @inprop: C{TEXT}: The input token's text content.
    @inprop: C{LOC}: The input token's location.  I{(optional)}
    @outprop: C{SUBTOKENS}: The list of tokenized subtokens.
    @outprop: C{TEXT}: The subtokens' text contents.
    @outprop: C{TAG}: The subtokens' tags.
    @outprop: C{LOC}: The subtokens' locations.
    """
    def __init__(self, **property_names):
        TaggedTokenizer.__init__(self, **property_names)

    def tokenize(self, token, addlocs=False, addcontexts=False):
        # inherit doco
        assert chktype(1, token, Token)

        # useful property names
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        TEXT = self._property_names.get('TEXT', 'TEXT')
        LOC = self._property_names.get('LOC', 'LOC')

        # get the token's initial location
        if addlocs:
            if token.has(LOC):
                source = token[LOC].source()
            else:
                source = None
            para = sent = 1
            para_loc = ParaIndexLocation(para, source)
            sent_loc = SentIndexLocation(sent, para_loc)

        # remove the [ and ] NP chunk markers
        text = re.sub(r'[\[\]]', '', token[TEXT])

        # split the text into sections for each paragraph
        token[SUBTOKENS] = []
        paragraphs = re.split(r'(?m)^=+$', text)
        for pg_text in paragraphs:
            seen_text = False
            sent_text = ''

            # split each line within the paragraph
            for s_text in re.split(r'\n', pg_text):
                # if the line ends with a '.' tag, it is most likely (always?)
                # the end of a sentence. We have to rely on this rather than
                # new lines in the text file as there are spurious new lines
                # inside the sentences in the treebank data.
                if re.search(r'[^\s]', s_text):
                    sent_text += s_text
                    # if line ends in a full stop, then process sentence text
                    if re.search(r'/\.\s*$', s_text):
                        # create a token
                        s_token = Token(TEXT=sent_text)
                        if addlocs:
                            s_token[LOC] = sent_loc
                        # tokenize
                        TaggedTokenizer.tokenize(self, s_token,
                                                 addlocs, addcontexts)
                        token[SUBTOKENS].extend(s_token[SUBTOKENS])
                        # update sentence locations
                        if addlocs:
                            sent += 1
                            sent_loc = SentIndexLocation(sent, para_loc)
                        seen_text = True
                        sent_text = ''

            # update paragraph and sentence locations
            if seen_text and addlocs:
                para += 1
                para_loc = ParaIndexLocation(para, source)
                sent = 1
                sent_loc = SentIndexLocation(sent, para_loc)
