# Natural Language Toolkit: Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# To do:
#   - make sure variable names are used consistantly (fdlist, etc.)
#   - remove any confusions about the type of labels (string vs
#      immutable) 

"""
Classes and interfaces used to classify texts into categories.  A
X{category} is a coherent group of texts.  This module focuses on
X{single-category text classification}, in which:

    - There set of categories is known.
    - The number of categories is finite.
    - Each text belongs to exactly one category.

A X{classifier} choses the most likely category for a given text.
Classifiers can also be used to estimate the probability that a given
text belongs to a category.  This module defines the C{ClassifierI}
interface for creating classifiers.  Note that classifiers can operate
on any kind of text.  For example, classifiers can be used:

  - to group documents by topic
  - to group words by part of speech
  - to group acoustic signals by which phoneme they represent
  - to group sentences by their author

Each category is uniquely defined by a X{label}, such as C{'sports'}
or C{'news'}.  Labels are typically C{string}s or C{integer}s, but can
be any immutable type.  Classified texts are represented by C{Tokens}
whose types are C{LabeledText} objects.  A C{LabeledText} consists of
a label and a text.

C{ClassifierTrainerI} is a general interface for classes that build
classifiers from training data.
"""

from Numeric import array

##//////////////////////////////////////////////////////
##  Texts and Labels
##//////////////////////////////////////////////////////

# A text can be any object.  Texts are required to be immutable, since
# they are used as the type of a token.

# A label can be any immutable object.  Typically, labels are either
# integers or strings.

##//////////////////////////////////////////////////////
##  LabeledTexts
##//////////////////////////////////////////////////////

class LabeledText:
    """
    A type consisting of a text and a label.  A typical example would
    be a document labeled with a category, such as \"sports\".

    The text and the label are both required to be immutable.  Labels
    are ususally short strings or integers.

    @type _text: (immutable)
    @ivar _text: The C{LabeledText}'s text.
    @type _label: (immutable)
    @ivar _label: The text type's label.  This specifies which
        category the text belongs to.
    """
    def __init__(self, text, label):
        """
        Construct a new C{LabeledType}.

        @param text: The new C{LabeledType}'s text.
        @type text: (immutable)
        @param label: The new C{LabeledType}'s label.  This specifies
            which category the text belongs to.
        @type label: (immutable)
        """
        self._text = text
        self._label = label
        
    def text(self):
        """
        @return: this C{LabeledType}'s text.
        @rtype: (immutable)
        """
        return self._text
    
    def label(self):
        """
        @return: this C{LabeledType}'s label.
        @rtype: (immutable)
        """
        return self._label

    def __lt__(self, other):
        """
        Raise a C{TypeError}, since C{LabeledText} is not an ordered
        type.
        
        @raise TypeError: C{LabeledText} is not an ordered type.
        """
        raise TypeError("LabeledText is not an ordered type")
    
    def __le__(self, other):
        """
        Raise a C{TypeError}, since C{LabeledText} is not an ordered
        type.
        
        @raise TypeError: C{LabeledText} is not an ordered type.
        """
        raise TypeError("LabeledText is not an ordered type")
    
    def __gt__(self, other):
        """
        Raise a C{TypeError}, since C{LabeledText} is not an ordered
        type.
        
        @raise TypeError: C{LabeledText} is not an ordered type.
        """
        raise TypeError("LabeledText is not an ordered type")
    
    def __ge__(self, other):
        """
        Raise a C{TypeError}, since C{LabeledText} is not an ordered
        type.
        
        @raise TypeError: C{LabeledText} is not an ordered type.
        """
        raise TypeError("LabeledText is not an ordered type")
    
    def __cmp__(self, other):
        """
        @return: 0 if this C{LabeledType} is equal to C{other}.  In
            particular, return 0 iff C{other} is a C{LabeledType},
            C{self.text()==other.text()}, and
            C{self.label()==other.label()}; return a nonzero number
            otherwise. 
        @rtype: C{int}
        @param other: The C{LabeledText} to compare this
            C{LabeledText} with.
        @type other: C{LabeledText}
        """
        if not isinstance(other, LabeledText):
            return 0
        return not (self._text == other._text and
                    self._label == other._label)

    def __hash__(self):
        return hash( (self._text, self._label) )
    
    def __repr__(self):
        """
        @return: a string representation of this labeled text.
        @rtype: C{string}
        """
        return "%r/%r" % (self._text, self._label)


##//////////////////////////////////////////////////////
##  Classiifer Interface
##//////////////////////////////////////////////////////

class ClassifierI:
    """
    A processing interface for categorizing texts.  The set of
    categories used by a classifier must be fixed, and finite.  Each
    category is uniquely defined by a X{label}, such as C{'sports'} or
    C{'news'}.  Labels are typically C{string}s or C{integer}s, but
    can be any immutable type.  Classified texts are represented by
    C{Tokens} whose types are C{LabeledText} objects.

    Classifiers are required to implement two methods:

      - C{classify}: determines which label is most appropriate for a
        given text token, and returns a labeled text token with that
        label.
      - C{labels}: returns the list of category labels that are used
        by this classifier.

    Classifiers are also encouranged to implement the following
    methods:

      - C{distribution}: return a probability distribution that
        specifies M{P(label|text)} for a given text token.
      - C{prob}: returns M{P(label|text)} for a given labeled text
        token. 
      - C{distribution_dictionary}: Return a dictionary that maps from
        labels to probabilities.
      - C{distribution_list}: Return a sequence, specifying the
        probability of each label.

    
    Classes implementing the ClassifierI interface may choose to only
    support certain classes of tokens for input.  If a method is
    unable to return a correct result because it is given an
    unsupported class of token, then it should raise a
    NotImplementedError.

    Typically, classifier classes encode specific classifier models;
    but do not include the algorithms for training the classifiers.
    Instead, C{ClassifierTrainer}s are used to generate classifiers
    from training data.

    @see: C{ClassifierTrainerI}
    """
    def labels(self):
        """
        @return: the list of category labels used by this classifier.
        @rtype: C{list} of (immutable)
        """
        raise AssertionError()
    
    def classify(self, unlabeled_token):
        """
        Determine which label is most appropriate for the given text
        token, and return a C{LabeledText} token constructed from the
        given text token and the chosen label.
        
        @return: a C{LabeledText} token whose label is the most
            appropriate label for the given token; whose text is the
            given token's text; and whose location is the given
            token's location.
        @rtype: C{Token} with type C{LabeledText}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: C{Token}
        """
        raise AssertionError()

    def distribution(self, unlabeled_token):
        """
        Return a probability distribution indicating the likelihood
        that C{unlabeled_token} is a member of each category.
        
        @return: a probability distribution whose samples are
            tokens derived from C{unlabeled_token}.  The samples
            are C{LabeledText} tokens whose text is
            C{unlabeled_token}'s text; and whose location is
            C{unlabeled_token}'s location.  The probability of each
            sample indicates the likelihood that the unlabeled token
            belongs to each label's category.
        @rtype: C{ProbDistI}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: C{Token}
        """
        raise NotImplementedError()

    def prob(self, labeled_token):
        """
        @return: The probability that C{labeled_token}'s text belongs
           to the category indicated by C{labeled_token}'s label.
        @rtype: C{float}
        @param labeled_token: The labeled token for which to generate
            a probability estimate.
        @type labeled_token: C{Token} with type C{LabeledText}
        """
        raise NotImplementedError()

    def distribution_dictionary(self, unlabeled_token):
        """
        Return a dictionary indicating the likelihood that
        C{unlabeled_token} is a member of each category.
        
        @return: a dictionary that maps from each label to the
            probability that C{unlabeled_token} is a member of that
            label's category.
        @rtype: C{dictionary} from (immutable) to C{float}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: C{Token}
        """
        raise NotImplementedError()

    def distribution_list(self, unlabeled_token):
        """
        Return a list indicating the likelihood that
        C{unlabeled_token} is a member of each category.
        
        @return: a list of probabilities.  The M{i}th element of the
            list is the probability that C{unlabeled_text} belongs to
            C{labels()[M{i}]}'s category.
        @rtype: C{sequence} of C{float}
        @param unlabeled_token: The text to be classified.
        @type unlabeled_token: C{Token}
        """
        raise NotImplementedError()


##//////////////////////////////////////////////////////
##  Classiifer Trainer Interface
##//////////////////////////////////////////////////////

class ClassifierTrainerI:
    """
    A processing interface for constructing new classifiers, using
    training data.
    """
    def train(self, labeled_tokens, **kwargs):
        """
        Train a new classifier, using the given training samples.

        @type labeled_tokens: C{list} of (C{Token} with type C{LabeledText})
        @param labeled_tokens: A list of correctly labeled texts.
            These texts will be used as training samples to construct
            new classifiers.
        @param kwargs: Keyword arguments.
            - C{labels}: The set of possible labels.  If none is
              given, then the set of all labels attested in the
              training data will be used instead.  (type=C{list} of
              (immutable)).
        @return: A new classifier, trained from the given labeled
            tokens.
        @rtype: C{ClassifierI}
        """
        raise AssertionError()

def find_labels(labeled_tokens):
    """
    @return: A list of all labels that are attested in the given list
        of labeled tokens.
    @rtype: C{list} of (immutable)
    @param labeled_tokens: The list of labeled tokens from which to
        extract labels.
    @type labeled_tokens: C{list} of (C{Token} with type C{LabeledText})
    """
    labelmap = {}
    for token in labeled_tokens:
        labelmap[token.type().label()] = 1
    return labelmap.keys()

