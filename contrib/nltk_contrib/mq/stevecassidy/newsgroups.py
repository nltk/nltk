"""A tokenizer for the 20 newsgroups corpus which splits the text
into sentences as well as finding word tokens.  Word tokens are marked
as being either HEADER, QUOTED or BODY via their TYPE attribute.

Author: Steve Cassidy <steve.cassidy@mq.edu.au>
Date: April 2004

Copyright (c) 2004, Steve Cassidy, Centre for Language Technology,
Macquarie University

For license information, see LICENSE.TXT

"""

from nltk.corpus import *
from nltk.tokenizer import *
import re
import string



class SentenceChunker:
    """A sentence chunker for tokens with a SUBTOKENS property.
    This class chunks the text into sentences setting the SENTENCES property
    of the token."""

    punctuation = ['.', '!', '?']

    def __init__(self, token):
        self.token = token
        self.__abbreviations()
        self.__chunk()


    def __chunk(self):
        """Group subtokens into sentences by looking for
        punctuation etc.
        Set the SENTENCES property of the input token.
        """
        result = []
        current = []
        sentences = []
        for i in range(len(self.token['SUBTOKENS'])):

            current.append(self.token['SUBTOKENS'][i])
                
            # uncomment the print statements to see the outcomes
            # of the sentence end detector
            if self.__sentence_end(i):
#                print "yes"
                if not current == []:
                    sentences.append(Token(SUBTOKENS=current, TEXT=self.jointoktext(current)))
                    current = []
            else:
#                print "no"
                pass
        # there could be material left over, just call it a sentence
        if not current == []:
            sentences.append(Token(SUBTOKENS=current, TEXT=self.jointoktext(current)))

        self.token['SENTENCES'] = sentences


    def jointoktext(self, toklist):
        """Join the text of a list of tokens into a new string"""
        result = ""
        for tok in toklist:
            result = result+" "+tok['TEXT']
        return result

    ## define some lists of abbreviations, these are all of the
    ## one word abbreviations found in the corpus which appear as
    ## abbrev. 
    onewordabbrevs = ['al', 'ie', 'Dr', 'Ph', 'pg', 'resp', 'viz', 'lit', 
                      'wrt', 'pro', 'St',
                      'Ls', 'ch', 'ff', 'Mr', 'TEMP', 'Ltd', 'fig', 'Corp', 
                      'IDENT', 'pa', 'aux']

    ## these are all of the multi word abbreviations which contain
    ## periods, e.g. i.e. etc.
    multiwordabbrevs = {'e': [['e', 'g']],
                        'i': [['i', 'e']],
                        'O': [['O', 'K']],
                        'c': [['c', 'f']],
                        'p': [['p', 'c'], ['p', 'b', 't']],
                        'U': [['U', 'S']],
                        'a': [['a', 'm']]}

    def __abbreviations(self):
        """Process subtokens looking for possible abbreviations
        which will occur as multiple tokens since we used a naive
        tokeniser splitting out every punctuation as a token. Combine
        any abbreviations into a single token. Modifies self.token."""
        newtoks = []
        i = 0
        while i < len(self.token['SUBTOKENS']):
            # matched will record how many tokens are matched against an
            # abbreviation
            matched = 0
            if i+1 < len(self.token['SUBTOKENS']) and \
                   self.__textof(i) in self.onewordabbrevs and \
               self.__textof(i+1) == '.':
                newtoks.append(Token(TEXT=self.__textof(i)+self.__textof(i+1),
                                     TYPE=self.__gettoken(i)['TYPE']))
                # we matched two tokens
                matched = 2
            elif i+1 < len(self.token['SUBTOKENS']) and \
                     self.__textof(i) in self.multiwordabbrevs.keys():
                # we've matched one token so far
                matched = 1
                # look for one of the sequences with periods
                for seq in self.multiwordabbrevs[self.__textof(i)]:
                    # nt is the new token we're creating
                    nt = self.__textof(i)
                    # look for the rest of the letters in the abbrev
                    # separated by periods
                    for j in range(1,len(seq)):
                        if i+(2*j)>=len(self.token['SUBTOKENS']) or \
                           not seq[j] == self.__textof(i+(2*j)) or\
                           not self.__textof(i+(2*j)-1) == '.':
                            # failed to match
                            matched = 0
                            break
                        else:
                            nt += '.'+self.__textof(i+(2*j))
                            matched += 2

                    if matched:
                        # we need to check for a final period, might be
                        # missing of course!
                        if self.__textof(i+matched) == '.':
                            nt += '.'
                            matched += 1
                        newtoks.append(Token(TEXT=nt, TYPE=self.__gettoken(i)['TYPE']))
                        break
                
            if matched:
                i += matched
            else:
                newtoks.append(self.token['SUBTOKENS'][i])
                i += 1
        self.token['SUBTOKENS'] = newtoks 

        
    def __capitalised_tok( self, i  ):
        "does the token at i begin with an uppercase letter" 
        if self.__textof(i)[0] in string.uppercase:
            return 1
        else:
            return 0

    def __textof(self,index):
        """retrieve the text of the index'th token"""
        return self.__gettoken(index)['TEXT']

    def __gettoken(self,index):
        """retrieve the index'th token"""
        return self.token['SUBTOKENS'][index]

    
    def __sentence_end(self,index):
        """a sentence end detector which looks for a sentence end
        at the location  index in the list of tokens.  Return  true
        if we  think it's a sentence boundary, false otherwise."""

        # Uncomment this to see what context is being used to make the
        # sentence boundary decision
#         print '[', self.__textof(index), ']',
#         for i in range(index+1, min(len(self.token['SUBTOKENS']),index+3)):
#             print self.__textof(i),
#         print "-->",

        # if we're close to the end, look at some cases
        if len(self.token['SUBTOKENS']) == index+1:
            # if we end in a punctuation mark, say yes
            if self.__textof(index) in self.punctuation:
                return 1
            else:
                return 0

        # otherwise we can try the rules
        if len(self.token['SUBTOKENS']) > index+3:
            # the case of .", the sentence ends here
            if self.__textof(index) in self.punctuation \
                   and self.__textof(index+1) == '"':
                return 1

            ## A header field name begins a sentence
            if len(self.token['SUBTOKENS']) >= index+1 and \
               self.__gettoken(index+1)['TYPE'] == 'HEADER' and\
               ( self.__textof(index+1) == 'Subject:' or
                 self.__textof(index+1) == 'From:'):
                return 1

            if self.__textof(index) in ['!', '?']:
                return 1

            ## look for initials, ie single letter sentences
            if self.__textof(index) == '.' \
                   and self.__capitalised_tok(index-1)\
                   and len(self.__textof(index-1)) == 1:
                return 0

            #  look for '. <capital>' or  '." <capital>' or '. "<capital>'
            #  or '. \n\n' 
            if self.__textof(index) == '.':
                if self.__capitalised_tok(index+1):
                    return 1
                if self.__textof(index+1) == "''" and \
                       self.__capitalised_tok(index+2):
                    return 1

            # look for a change of TYPE (eg. HEADER to BODY)
            if len(self.token['SUBTOKENS']) >= index+1 and \
                   self.__gettoken(index)['TYPE'] != \
                   self.__gettoken(index+1)['TYPE']:
                return 1



        ## if we get here,  it's not a sentence
        return 0


class my_twenty_tokenizer(AbstractTokenizer):

    # word regular expression:
    #  \w+@[\w.]+  -- email addr
    #  's     - genitive
    #  ^\w+:   -- header field name
    #  (\w+[-']?)+  -- one or more word chars plus - (eg. n-grams) and ' (can't)
    #  [0-9]+(.[0-9]+)?  -- numbers including a point
    # [.!?]   -- sentence end punctuation
    # :\n  -- line end colon, often delimits a quote prefix

    wordre = r"\w+@[\w.]+|'s|^\w+:|(\w+[-']?)+|[0-9]+(.[0-9]+)?|[.!?]|:\w*\n"

    retokenizer = RegexpTokenizer(wordre)

    linecats = {'HEADER' : re.compile(r'^\w+: .*'),
               'QUOTED' : re.compile(r'^>.*')}

    def linecategory(self, token):
        """Categorise a line of the newsgroup corpus"""
        for cat in self.linecats.keys():
            if self.linecats[cat].search(token['TEXT']):
                return cat
        return 'BODY'

    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        return [s for s in text.split('\n') if s.strip() != '']

    def tokenize(self, token, addlocs=False):
        # Delegate to self.raw_tokenize()
        assert chktype(1, token, Token)
        self._tokenize_from_raw(token, addlocs)
	# now we categorize the tokens and split them further
        wordtoks = []
        for tok in token['SUBTOKENS']:
            # categorise the line
            lc = self.linecategory(tok)
            # tokenise the line using the re tokeniser
            self.retokenizer.tokenize(tok)
            for word in tok['SUBTOKENS']:
                 wordtoks.append(Token(TEXT=word['TEXT'],TYPE=lc))
        # make the subtokens words instead of lines
        token['SUBTOKENS'] = wordtoks
            

def tokenize(doc):
    return twenty_newsgroups.tokenize(doc,tokenizer=my_twenty_tokenizer())


if __name__=='__main__':
    from nltk.corpus import *


    ######################################################
    ## Fix a bug in nltk.corpus where the pattern supplied
    ## for items in the newsgroups corpus is unix specific.
    ## The following definition overrides the definition
    ## in nltk.corpus and so should be placed _AFTER_ the
    ## 'from nltk.corpus import *' line in your code.
    ## 
    ######################################################
    ## 20 Newsgroups
    groups = [(ng, os.path.join(ng, '.*')) for ng in '''
        alt.atheism rec.autos sci.space comp.graphics rec.motorcycles
        soc.religion.christian comp.os.ms-windows.misc rec.sport.baseball
        talk.politics.guns comp.sys.ibm.pc.hardware rec.sport.hockey
        talk.politics.mideast comp.sys.mac.hardware sci.crypt
        talk.politics.misc comp.windows.x sci.electronics
        talk.religion.misc misc.forsale sci.med'''.split()]

    twenty_newsgroups = SimpleCorpusReader(
        '20_newsgroups', '20_newsgroups/', os.path.join('.*','.*'), groups,
        description_file='../20_newsgroups.readme')
    del groups # delete temporary variable
    ##
    ## end bug fix
    ######################################################

    # say where the corpora live
#    set_basedir('C:\\3_newsgroups')
    set_basedir('/home/steve/courses/comp348/web/assignments')

    docs = twenty_newsgroups.items('talk.politics.misc')


    for i in range(108,109):
        print "\n\nTokenise ", docs[i]
    
        token = tokenize(docs[i])

        # perform sentence chunking
        SentenceChunker(token)

        # print out the sentence tokens
        for t in token['SENTENCES']:
            print "\t",t['TEXT']

        # print out the text tokens and their type
        for t in token['SUBTOKENS']:
            print "\t",t['TEXT'],"\t", t['TYPE']

