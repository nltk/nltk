#
# An annotation-graph like extension of "new" tokens.
#

"""
1. Graph edges (annotations) are encoded with Tokens.
    - edge.fields => dir(tok)
    - edge.start => tok.loc().start_loc()
    - edge.end => tok.loc().end_loc()
2. Graph nodes are encoded with 0-length Locations.
3. A mapping between the indicies for each (unit,source)
   pair and a timeline could be maintained; but I won't
   bother for now.

Notes:
  - if two nodes are unordered, then they must have different units
    and/or sources


the 
"""


from nltk.token import Location

# New-style tokens:
class Token:
    def __init__(self, text, loc, **attributes):
        # Keep this for extend().
        self.__dict__['_attributes'] = attributes
        # Add all attributes as read-only instance variables.
        self.__dict__.update(attributes)
        # Add the text & loc as read-only instance variables.  These
        # override any values in "attributes".
        self.__dict__['text'] = text
        self.__dict__['loc'] = loc

    # Don't allow the user to modify instance variables.
    def __setattr__(self, name, value):
        raise ValueError('Tokens are immutable')

    # Don't allow the user to modify instance variables.
    def __delattr__(self, name, value):
        raise ValueError('Tokens are immutable')

    # Return a new token, with added attributes.
    def extend(self, attr=None, value=None, **attributes):
        # (This should probably have more error checking)
        if attr is None:
            tok = Token(self.text, self.loc, self._attributes)
            tok.__dict__.extend(attributes)
        else:
            tok.__dict__[attr] = value
        return tok
    
    # This is convenient if we only have the attribute as a string.
    def get(self, attribute):
        return self.__dict__[attribute]

    # Use hasattr instead??
    def has(self, attribute):
        return self.__dict__.has_key(attribute)

    def __repr__(self):
        return '%r%r' % (self.text, self.loc)


class AnnotationGraph:
    """
    An annotation-graph-like class, built out of tokens.

    @ivar _tokens: The tokens that make up the annotations.
    """
    def __init__(self):
        self._tokens = []

    def add(self, token):
        self._tokens.append(token)

    def join_locs(self, *offsets):
        pass # stub

    def __str__(self):
        return '\n'.join([`t` for t in self._tokens])


############################################################
## TIMIT Graph (figure 2)
############################################################
timit = AnnotationGraph()
# Phonetic Transcription
timit.add(Token('h#',   Location(0, 1, unit='p'), type='P'))
timit.add(Token('sh',   Location(1, 2, unit='p'), type='P'))
timit.add(Token('iy',   Location(2, 3, unit='p'), type='P'))
timit.add(Token('hv',   Location(3, 4, unit='p'), type='P'))
timit.add(Token('ae',   Location(4, 5, unit='p'), type='P'))
timit.add(Token('dcl',  Location(5, 6, unit='p'), type='P'))
timit.add(Token('y',    Location(6, 7, unit='p'), type='P'))
timit.add(Token('axr',  Location(7, 8, unit='p'), type='P'))
# Word transcription
timit.add(Token('she',  Location(1, 3, unit='p'), type='W'))
timit.add(Token('had',  Location(3, 6, unit='p'), type='W'))
timit.add(Token('your', Location(6, 8, unit='p'), type='W'))

print timit

############################################################
## Partitur Graph (figure 3)
############################################################
partitur = AnnotationGraph()
# Phonetic segments (MAU)
partitur.add(Token('j',     Location(0, 1,  unit='p'), type='M'))
partitur.add(Token('a',     Location(1, 2,  unit='p'), type='M'))
partitur.add(Token('S',     Location(2, 3,  unit='p'), type='M'))
partitur.add(Token('2',     Location(3, 4,  unit='p'), type='M'))
partitur.add(Token('n',     Location(4, 5,  unit='p'), type='M'))
partitur.add(Token('n',     Location(5, 6,  unit='p'), type='M'))
partitur.add(Token('<nib>', Location(6, 7,  unit='p'), type='M'))
partitur.add(Token('d',     Location(7, 8,  unit='p'), type='M'))
partitur.add(Token('a',     Location(8, 9,  unit='p'), type='M'))
partitur.add(Token('N',     Location(9, 10, unit='p'), type='M'))
# Orthography (ORT)
partitur.add(Token('ja',       Location(0, 2,  unit='p'), type='O'))
partitur.add(Token('sch"onen', Location(2, 6,  unit='p'), type='O'))
partitur.add(Token('Dang',     Location(7, 10, unit='p'), type='O'))
# Dialogue Acts (DAS)
partitur.add(Token('(@THANK_INIT BA)', Location(0, 10, unit='p'), type='D'))

print partitur

############################################################
## Childes Graph (figure 4a)
############################################################

childes_a = AnnotationGraph()
# Utterances
childes_a.add(Token('yahoo',
                Location(0, 1, unit='u'), type='W'))
childes_a.add(Token('you got a lot more to do # don\'t you',
                Location(1, 2, unit='u'), type='W'))
# Speakers
childes_a.add(Token('Ross',   Location(0, 1, unit='u'), type='S'))
childes_a.add(Token('Father', Location(1, 2, unit='u'), type='S'))
print childes_a

############################################################
## Childes Graph (figure 4b)
############################################################

childes_b = AnnotationGraph()
# Words
childes_b.add(Token('yahoo',  Location(0,  1,  unit='w'), type='W'))
childes_b.add(Token('.',      Location(1,  2,  unit='w'), type='W'))
childes_b.add(Token('you',    Location(2,  3,  unit='w'), type='W'))
childes_b.add(Token('got',    Location(3,  4,  unit='w'), type='W'))
childes_b.add(Token('a',      Location(4,  5,  unit='w'), type='W'))
childes_b.add(Token('lot',    Location(5,  6,  unit='w'), type='W'))
childes_b.add(Token('more',   Location(6,  7,  unit='w'), type='W'))
childes_b.add(Token('to',     Location(7,  8,  unit='w'), type='W'))
childes_b.add(Token('do',     Location(8,  9,  unit='w'), type='W'))
childes_b.add(Token('#',      Location(9,  10, unit='w'), type='W'))
childes_b.add(Token('don\'t', Location(10, 11, unit='w'), type='W'))
childes_b.add(Token('you',    Location(11, 12, unit='w'), type='W'))
childes_b.add(Token('?',      Location(12, 13, unit='w'), type='W'))
# Speakers
childes_b.add(Token('Ross',   Location(0, 2,  unit='w'), type='S'))
childes_b.add(Token('Father', Location(3, 14, unit='w'), type='S'))
print childes_b

############################################################
## LACITO Graph (figure 5)
############################################################

lacito = AnnotationGraph()
# Glosses & Punctuation
lacito.add(Token('deux',       Location(0, 1, unit='g'), type='G'))
lacito.add(Token('soeurs',     Location(1, 2, unit='g'), type='G'))
lacito.add(Token('bois',       Location(2, 3, unit='g'), type='G'))
lacito.add(Token('faire',      Location(3, 4, unit='g'), type='G'))
lacito.add(Token('allLrent',   Location(4, 5, unit='g'), type='G'))
lacito.add(Token('dit',        Location(5, 6, unit='g'), type='G'))
lacito.add(Token('on',         Location(6, 7, unit='g'), type='G'))
lacito.add(Token('.',          Location(7, 8, unit='g'), type='P'))
# Words
lacito.add(Token('nakpu',      Location(0, 1, unit='g'), type='W'))
lacito.add(Token('nonotso',    Location(1, 2, unit='g'), type='W'))
lacito.add(Token('siG',        Location(2, 3, unit='g'), type='W'))
lacito.add(Token('pa',         Location(3, 4, unit='g'), type='W'))
lacito.add(Token('la7natshem', Location(4, 5, unit='g'), type='W'))
lacito.add(Token('are',        Location(5, 7, unit='g'), type='W'))
# English translation
lacito.add(Token('they',       Location(0, 1, unit='wE'), type='E'))
lacito.add(Token('say',        Location(1, 2, unit='wE'), type='E'))
lacito.add(Token('that',       Location(2, 3, unit='wE'), type='E'))
lacito.add(Token('two',        Location(3, 4, unit='wE'), type='E'))
lacito.add(Token('sisters',    Location(4, 5, unit='wE'), type='E'))
lacito.add(Token('went',       Location(5, 6, unit='wE'), type='E'))
lacito.add(Token('to',         Location(6, 7, unit='wE'), type='E'))
lacito.add(Token('get',        Location(7, 8, unit='wE'), type='E'))
lacito.add(Token('firewood',   Location(8, 9, unit='wE'), type='E'))
# French translation
lacito.add(Token('they',       Location(0, 1, unit='wF'), type='F'))
lacito.add(Token('say',        Location(1, 2, unit='wF'), type='F'))
lacito.add(Token('that',       Location(2, 3, unit='wF'), type='F'))
lacito.add(Token('two',        Location(3, 4, unit='wF'), type='F'))
lacito.add(Token('sisters',    Location(4, 5, unit='wF'), type='F'))
lacito.add(Token('went',       Location(5, 6, unit='wF'), type='F'))
lacito.add(Token('to',         Location(6, 7, unit='wF'), type='F'))
lacito.add(Token('get',        Location(7, 8, unit='wF'), type='F'))
lacito.add(Token('firewood',   Location(8, 9, unit='wF'), type='F'))
# Linking between location types
lacito.join_locs(Location(0, 0, unit='g'),
                 Location(0, 0, unit='wE'),
                 Location(0, 0, unit='wF'))
lacito.join_locs(Location(8, 8, unit='g'),
                 Location(9, 9, unit='wE'),
                 Location(9, 9, unit='wE'))
