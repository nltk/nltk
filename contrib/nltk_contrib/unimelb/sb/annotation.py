"""
Annotations are represented as tokens.  We start with a tokenized token
minimally having the SUBTOKENS property, whose value is a list of Tokens.
We then add layers of annotation which reference the subtokens by their
location in the SUBTOKENS property.

(This approach can be used to represent connected, anchored, AGs that are
built on a chain of edges - i.e. a chart.  The AG notion of annotation "type"
survives as the property name).
"""

from nltk.token import *
from nltk.tokenizer import *

class TokenSpanLocation(SpanLocation):
    __slots__ = ()
    UNIT = 't'
    
    def select(self, token):
        """
        Given the token list over which this location is defined,
        return the slice specified by this token.
        """
        return token['SUBTOKENS'][self._start:self._end]

class AnnotationSet(dict):
    def __init__(self):
        super(dict, self).__init__()
        self._annotations = []
    def add(self, token):
        loc = token['LOC']
        if not isinstance(loc, TokenSpanLocation):
            raise TypeError('Annotations must have TokenSpanLocations')
        self[loc] = token
        self._annotations.append(token)
    def getByValue(self, property, value):
        return [tok for tok in self._annotations if tok[property] == value]
    def getByLoc(self, loc):
        return [tok for tok in self._annotations if tok['LOC'] == loc]
    def getNearLoc(self, loc, epsilon=0):
        return [tok for tok in self._annotations\
               if tok['LOC'].start() < loc.end() + epsilon\
               and tok['LOC'].end() > loc.start() - epsilon]
    def getTokensByLoc(self, loc, token):
        return loc.select(token)


########################################################################3

text = Token(TEXT="I live in twit village")
WhitespaceTokenizer().tokenize(text)
print text

loc1 = TokenSpanLocation(0,2)
loc2 = TokenSpanLocation(3,3)
loc3 = TokenSpanLocation(3,5)
loc4 = TokenSpanLocation(1,5)

text['CHUNKS'] = AnnotationSet()
text['CHUNKS'].add(Token(TAG='NP', LOC=loc3))
text['CHUNKS'].add(Token(TAG='VP', LOC=loc4))

print 'Get annotations having TAG=NP:',\
      text['CHUNKS'].getByValue('TAG','NP')

print 'Get annotations with LOC=(0,2):',\
      text['CHUNKS'].getByLoc(loc1)

print 'Get annotations overlapping LOC=(0,2):',\
      text['CHUNKS'].getNearLoc(loc1)

print 'Get tokens inside LOC=(0,2):',\
      text['CHUNKS'].getTokensByLoc(loc1, text)

print "########################################################################"

# now do speech segmentation using annotations

class SignalLocation(SpanLocation):
    __slots__ = ()
    UNIT = 's' # seconds

# transcript from LDC Callhome
transcript = """
So tell me I mean it was shocking for us and we just heard it.  
You know the night it happened on the news it was a little blip and &Paul and I were watching T V and we just  
looked at each other with our mouths open.
"""

loc1 = TokenSpanLocation(0,15)
loc2 = TokenSpanLocation(15,40)
loc3 = TokenSpanLocation(40,48)

token = Token(TEXT=transcript)
WhitespaceTokenizer().tokenize(token)

# hmm, not sure where these belong!
signal_loc1 = SignalLocation(16.35, 19.59)
signal_loc2 = SignalLocation(20.15, 24.36)
signal_loc3 = SignalLocation(25.15, 27.10)

token['SEGMENTS'] = AnnotationSet()
token['SEGMENTS'].add(Token(SEG=1, LOC=loc1, SIGNAL=signal_loc1))
token['SEGMENTS'].add(Token(SEG=2, LOC=loc2, SIGNAL=signal_loc2))
token['SEGMENTS'].add(Token(SEG=3, LOC=loc3, SIGNAL=signal_loc3))

print token
print token['SEGMENTS'].getTokensByLoc(loc1, token)
print token['SEGMENTS'].getTokensByLoc(loc2, token)
print token['SEGMENTS'].getTokensByLoc(loc3, token)

