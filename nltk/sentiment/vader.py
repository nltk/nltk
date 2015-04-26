# coding: utf-8
# Natural Language Toolkit: vader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: C.J. Hutto <Clayton.Hutto@gtri.gatech.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
#
"""

If you use the VADER sentiment analysis tools, please cite:

Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model for
Sentiment Analysis of Social Media Text. Eighth International Conference on
Weblogs and Social Media (ICWSM-14). Ann Arbor, MI, June 2014.


>>> sentences = ["VADER is smart, handsome, and funny.", # positive sentence example
...    "VADER is smart, handsome, and funny!", # punctuation emphasis handled correctly (sentiment intensity adjusted)
...    "VADER is very smart, handsome, and funny.",  # booster words handled correctly (sentiment intensity adjusted)
...    "VADER is VERY SMART, handsome, and FUNNY.",  # emphasis for ALLCAPS handled
...    "VADER is VERY SMART, handsome, and FUNNY!!!",# combination of signals - VADER appropriately adjusts intensity
...    "VADER is VERY SMART, really handsome, and INCREDIBLY FUNNY!!!",# booster words & punctuation make this close to ceiling for score
...    "The book was good.",         # positive sentence
...    "The book was kind of good.", # qualified positive sentence is handled correctly (intensity adjusted)
...    "The plot was good, but the characters are uncompelling and the dialog is not great.", # mixed negation sentence
...    "A really bad, horrible book.",       # negative sentence with booster words
...    "At least it isn't a horrible book.", # negated negative sentence with contraction
...    ":) and :D",     # emoticons handled
...    "",              # an empty string is correctly handled
...    "Today sux",     #  negative slang handled
...    "Today sux!",    #  negative slang with punctuation emphasis handled
...    "Today SUX!",    #  negative slang with capitalization emphasis
...    "Today kinda sux! But I'll get by, lol" # mixed sentiment example with slang and constrastive conjunction "but"
... ]
>>> paragraph = "It was one of the worst movies I've seen, despite good reviews. \
... Unbelievably bad acting!! Poor direction. VERY poor production. \
... The movie was bad. Very bad movie. VERY bad movie. VERY BAD movie. VERY BAD movie!"

>>> from nltk import tokenize
>>> lines_list = tokenize.sent_tokenize(paragraph)
>>> sentences.extend(lines_list)

>>> tricky_sentences = [
...    "Most automated sentiment analysis tools are shit.",
...    "VADER sentiment analysis is the shit.",
...    "Sentiment analysis has never been good.",
...    "Sentiment analysis with VADER has never been this good.",
...    "Warren Beatty has never been so entertaining.",
...    "I won't say that the movie is astounding and I wouldn't claim that the movie is too banal either.",
...    "I like to hate Michael Bay films, but I couldn't fault this one",
...    "It's one thing to watch an Uwe Boll film, but another thing entirely to pay for it",
...    "The movie was too good",
...    "This movie was actually neither that funny, nor super witty.",
...    "This movie doesn't care about cleverness, wit or any other kind of intelligent humor.",
...    "Those who find ugly meanings in beautiful things are corrupt without being charming.",
...    "There are slow and repetitive parts, BUT it has just enough spice to keep it interesting.",
...    "The script is not fantastic, but the acting is decent and the cinematography is EXCELLENT!",
...    "Roger Dodger is one of the most compelling variations on this theme.",
...    "Roger Dodger is one of the least compelling variations on this theme.",
...    "Roger Dodger is at least compelling as a variation on the theme.",
...    "they fall in love with the product",
...    "but then it breaks",
...    "usually around the time the 90 day warranty expires",
...    "the twin towers collapsed today",
...    "However, Mr. Carter solemnly argues, his client carried out the kidnapping under orders and in the ''least offensive way possible.''"
... ]
>>> sentences.extend(tricky_sentences)
>>> sid = SentimentIntensityDetector()
>>> for sentence in sentences:
...     print(sentence)
...     ss = sid.sentiment(sentence)
...     for k in sorted(ss):
...         print('{0}: {1}, '.format(k, ss[k]), end='')
...     print()
VADER is smart, handsome, and funny.
compound: 0.8316, neg: 0.0, neu: 0.254, pos: 0.746,
VADER is smart, handsome, and funny!
compound: 0.8439, neg: 0.0, neu: 0.248, pos: 0.752,
VADER is very smart, handsome, and funny.
compound: 0.8545, neg: 0.0, neu: 0.299, pos: 0.701,
VADER is VERY SMART, handsome, and FUNNY.
compound: 0.9227, neg: 0.0, neu: 0.246, pos: 0.754,
VADER is VERY SMART, handsome, and FUNNY!!!
compound: 0.9342, neg: 0.0, neu: 0.233, pos: 0.767,
VADER is VERY SMART, really handsome, and INCREDIBLY FUNNY!!!
compound: 0.9469, neg: 0.0, neu: 0.294, pos: 0.706,
The book was good.
compound: 0.4404, neg: 0.0, neu: 0.508, pos: 0.492,
The book was kind of good.
compound: 0.3832, neg: 0.0, neu: 0.657, pos: 0.343,
The plot was good, but the characters are uncompelling and the dialog is not great.
compound: -0.7042, neg: 0.327, neu: 0.579, pos: 0.094,
A really bad, horrible book.
compound: -0.8211, neg: 0.791, neu: 0.209, pos: 0.0,
At least it isn't a horrible book.
compound: 0.431, neg: 0.0, neu: 0.637, pos: 0.363,
:) and :D
compound: 0.7925, neg: 0.0, neu: 0.124, pos: 0.876,
<BLANKLINE>
compound: 0.0, neg: 0.0, neu: 0.0, pos: 0.0,
Today sux
compound: -0.3612, neg: 0.714, neu: 0.286, pos: 0.0,
Today sux!
compound: -0.4199, neg: 0.736, neu: 0.264, pos: 0.0,
Today SUX!
compound: -0.5461, neg: 0.779, neu: 0.221, pos: 0.0,
Today kinda sux! But I'll get by, lol
compound: 0.2228, neg: 0.195, neu: 0.531, pos: 0.274,
It was one of the worst movies I've seen, despite good reviews.
compound: -0.7584, neg: 0.394, neu: 0.606, pos: 0.0,
... Unbelievably bad acting!!
compound: -0.6572, neg: 0.593, neu: 0.407, pos: 0.0,
Poor direction.
compound: -0.4767, neg: 0.756, neu: 0.244, pos: 0.0,
VERY poor production.
compound: -0.6281, neg: 0.674, neu: 0.326, pos: 0.0,
...
compound: 0.0, neg: 0.0, neu: 1.0, pos: 0.0,
The movie was bad.
compound: -0.5423, neg: 0.538, neu: 0.462, pos: 0.0,
Very bad movie.
compound: -0.5849, neg: 0.655, neu: 0.345, pos: 0.0,
VERY bad movie.
compound: -0.6732, neg: 0.694, neu: 0.306, pos: 0.0,
VERY BAD movie.
compound: -0.7398, neg: 0.724, neu: 0.276, pos: 0.0,
VERY BAD movie!
compound: -0.7616, neg: 0.735, neu: 0.265, pos: 0.0,
Most automated sentiment analysis tools are shit.
compound: -0.5574, neg: 0.375, neu: 0.625, pos: 0.0,
VADER sentiment analysis is the shit.
compound: 0.6124, neg: 0.0, neu: 0.556, pos: 0.444,
Sentiment analysis has never been good.
compound: -0.3412, neg: 0.325, neu: 0.675, pos: 0.0,
Sentiment analysis with VADER has never been this good.
compound: 0.5228, neg: 0.0, neu: 0.703, pos: 0.297,
Warren Beatty has never been so entertaining.
compound: 0.5777, neg: 0.0, neu: 0.616, pos: 0.384,
I won't say that the movie is astounding and I wouldn't claim that the movie is too banal either.
compound: 0.4215, neg: 0.0, neu: 0.851, pos: 0.149,
I like to hate Michael Bay films, but I couldn't fault this one
compound: 0.3153, neg: 0.157, neu: 0.534, pos: 0.309,
It's one thing to watch an Uwe Boll film, but another thing entirely to pay for it
compound: -0.2541, neg: 0.112, neu: 0.888, pos: 0.0,
The movie was too good
compound: 0.4404, neg: 0.0, neu: 0.58, pos: 0.42,
This movie was actually neither that funny, nor super witty.
compound: -0.6759, neg: 0.41, neu: 0.59, pos: 0.0,
This movie doesn't care about cleverness, wit or any other kind of intelligent humor.
compound: -0.1338, neg: 0.265, neu: 0.497, pos: 0.239,
Those who find ugly meanings in beautiful things are corrupt without being charming.
compound: -0.3553, neg: 0.314, neu: 0.493, pos: 0.192,
There are slow and repetitive parts, BUT it has just enough spice to keep it interesting.
compound: 0.4678, neg: 0.079, neu: 0.735, pos: 0.186,
The script is not fantastic, but the acting is decent and the cinematography is EXCELLENT!
compound: 0.7565, neg: 0.092, neu: 0.607, pos: 0.301,
Roger Dodger is one of the most compelling variations on this theme.
compound: 0.2944, neg: 0.0, neu: 0.834, pos: 0.166,
Roger Dodger is one of the least compelling variations on this theme.
compound: -0.1695, neg: 0.132, neu: 0.868, pos: 0.0,
Roger Dodger is at least compelling as a variation on the theme.
compound: 0.2263, neg: 0.0, neu: 0.84, pos: 0.16,
they fall in love with the product
compound: 0.6369, neg: 0.0, neu: 0.588, pos: 0.412,
but then it breaks
compound: 0.0, neg: 0.0, neu: 1.0, pos: 0.0,
usually around the time the 90 day warranty expires
compound: 0.0, neg: 0.0, neu: 1.0, pos: 0.0,
the twin towers collapsed today
compound: -0.2732, neg: 0.344, neu: 0.656, pos: 0.0,
However, Mr. Carter solemnly argues, his client carried out the kidnapping under orders and in the ''least offensive way possible.''
compound: -0.5859, neg: 0.23, neu: 0.697, pos: 0.074,

"""

import math
import re
import string


##Constants##

# (empirically derived mean sentiment intensity rating increase for booster words)
B_INCR = 0.293
B_DECR = -0.293

# (empirically derived mean sentiment intensity rating increase for using
# ALLCAPs to emphasize a word)
C_INCR = 0.733

N_SCALAR = -0.74

# for removing punctuation
REGEX_REMOVE_PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))

PUNC_LIST = [".", "!", "?", ",", ";", ":", "-", "'", "\"",
             "!!", "!!!", "??", "???", "?!?", "!?!", "?!?!", "!?!?"]
NEGATE = \
["aint", "arent", "cannot", "cant", "couldnt", "darent", "didnt", "doesnt",
 "ain't", "aren't", "can't", "couldn't", "daren't", "didn't", "doesn't",
 "dont", "hadnt", "hasnt", "havent", "isnt", "mightnt", "mustnt", "neither",
 "don't", "hadn't", "hasn't", "haven't", "isn't", "mightn't", "mustn't",
 "neednt", "needn't", "never", "none", "nope", "nor", "not", "nothing", "nowhere",
 "oughtnt", "shant", "shouldnt", "uhuh", "wasnt", "werent",
 "oughtn't", "shan't", "shouldn't", "uh-uh", "wasn't", "weren't",
 "without", "wont", "wouldnt", "won't", "wouldn't", "rarely", "seldom", "despite"]

# booster/dampener 'intensifiers' or 'degree adverbs'
# http://en.wiktionary.org/wiki/Category:English_degree_adverbs

BOOSTER_DICT = \
{"absolutely": B_INCR, "amazingly": B_INCR, "awfully": B_INCR, "completely": B_INCR, "considerably": B_INCR,
 "decidedly": B_INCR, "deeply": B_INCR, "effing": B_INCR, "enormously": B_INCR,
 "entirely": B_INCR, "especially": B_INCR, "exceptionally": B_INCR, "extremely": B_INCR,
 "fabulously": B_INCR, "flipping": B_INCR, "flippin": B_INCR,
 "fricking": B_INCR, "frickin": B_INCR, "frigging": B_INCR, "friggin": B_INCR, "fully": B_INCR, "fucking": B_INCR,
 "greatly": B_INCR, "hella": B_INCR, "highly": B_INCR, "hugely": B_INCR, "incredibly": B_INCR,
 "intensely": B_INCR, "majorly": B_INCR, "more": B_INCR, "most": B_INCR, "particularly": B_INCR,
 "purely": B_INCR, "quite": B_INCR, "really": B_INCR, "remarkably": B_INCR,
 "so": B_INCR, "substantially": B_INCR,
 "thoroughly": B_INCR, "totally": B_INCR, "tremendously": B_INCR,
 "uber": B_INCR, "unbelievably": B_INCR, "unusually": B_INCR, "utterly": B_INCR,
 "very": B_INCR,
 "almost": B_DECR, "barely": B_DECR, "hardly": B_DECR, "just enough": B_DECR,
 "kind of": B_DECR, "kinda": B_DECR, "kindof": B_DECR, "kind-of": B_DECR,
 "less": B_DECR, "little": B_DECR, "marginally": B_DECR, "occasionally": B_DECR, "partly": B_DECR,
 "scarcely": B_DECR, "slightly": B_DECR, "somewhat": B_DECR,
 "sort of": B_DECR, "sorta": B_DECR, "sortof": B_DECR, "sort-of": B_DECR}

# check for special case idioms using a sentiment-laden keyword known to SAGE
SPECIAL_CASE_IDIOMS = {"the shit": 3, "the bomb": 3, "bad ass": 1.5, "yeah right": -2,
                       "cut the mustard": 2, "kiss of death": -1.5, "hand to mouth": -2}


##Static methods##

def negated(input_words, include_nt=True):
    """
    Determine if input contains negation words
    """
    neg_words = []
    neg_words.extend(NEGATE)
    for word in neg_words:
        if word in input_words:
            return True
    if include_nt:
        for word in input_words:
            if "n't" in word:
                return True
    if "least" in input_words:
        i = input_words.index("least")
        if i > 0 and input_words[i-1] != "at":
            return True
    return False


def normalize(score, alpha=15):
    """
    Normalize the score to be between -1 and 1 using an alpha that
    approximates the max expected value
    """
    norm_score = score/math.sqrt(((score*score) + alpha))
    return norm_score



def allcap_differential(words):
    """
    Check whether just some words in in the input are ALL CAPS

    :param list words: The words to inspect
    :returns: `True` if some but not all items in `words` are ALL CAPS
    """
    is_different = False
    allcap_words = 0
    for w in words:
        if w.isupper():
            allcap_words += 1
    cap_differential = len(words) - allcap_words
    if cap_differential > 0 and cap_differential < len(words):
        is_different = True
    return is_different


def scalar_inc_dec(word, valence, is_cap_diff):
    """
    Check if the preceding words increase, decrease, or negate/nullify the
    valence
    """
    scalar = 0.0
    word_lower = word.lower()
    if word_lower in BOOSTER_DICT:
        scalar = BOOSTER_DICT[word_lower]
        if valence < 0:
            scalar *= -1
        #check if booster/dampener word is in ALLCAPS (while others aren't)
        if word.isupper() and is_cap_diff:
            if valence > 0:
                scalar += C_INCR
            else:  scalar -= C_INCR
    return scalar

#@python_2_unicode_compatible
class SentimentIntensityDetector(object):
    """
    Give a sentiment intensity score to sentences.
    """
    def __init__(self, lexicon_file="vader_sentiment_lexicon.txt"):
        self.lexicon_file = lexicon_file
        self.lexicon = self.make_lex_dict()

    def make_lex_dict(self):
        """
        Convert lexicon file to a dictionary
        """
        lex_dict = {}
        with open(self.lexicon_file, encoding='latin-1') as infile:
            for line in infile:
                (w, m) = line.strip().split('\t')[0:2]
                lex_dict[w] = float(m)
        return lex_dict



    def preprocess(self, text):
        """
        Identify sentiment-relevant string-level properties of input text.
        """
        if not isinstance(text, str):
            text = str(text)

        words_and_emoticons = text.split()
        # doesn't separate words from\
        # adjacent punctuation (keeps emoticons & contractions)
        text_mod = REGEX_REMOVE_PUNCTUATION.sub('', text)
        # removes punctuation (but loses emoticons & contractions)
        words_only = text_mod.split()
        # get rid of empty items or single letter "words" like 'a' and 'I'
        # from words_only
        for word in words_only:
            if len(word) <= 1:
                words_only.remove(word)
        # now remove adjacent & redundant punctuation from
        # [words_and_emoticons] while keeping emoticons and contractions

        for word in words_only:
            for p in PUNC_LIST:
                pword = p + word
                x1 = words_and_emoticons.count(pword)
                while x1 > 0:
                    i = words_and_emoticons.index(pword)
                    words_and_emoticons.remove(pword)
                    words_and_emoticons.insert(i, word)
                    x1 = words_and_emoticons.count(pword)

                wordp = word + p
                x2 = words_and_emoticons.count(wordp)
                while x2 > 0:
                    i = words_and_emoticons.index(wordp)
                    words_and_emoticons.remove(wordp)
                    words_and_emoticons.insert(i, word)
                    x2 = words_and_emoticons.count(wordp)

        # get rid of residual empty items or single letter "words" like 'a'
        # and 'I' from words_and_emoticons
        for word in words_and_emoticons:
            if len(word) <= 1:
                words_and_emoticons.remove(word)

        # remove stopwords from [words_and_emoticons]
        #stopwords = [str(word).strip() for word in open('stopwords.txt')]
        #for word in words_and_emoticons:
        #    if word in stopwords:
        #        words_and_emoticons.remove(word)

        # check for negation

        is_cap_diff = allcap_differential(words_and_emoticons)
        return text, words_and_emoticons, is_cap_diff

    def sentiment(self, text):
        """
        Returns a float for sentiment strength based on the input text.
        Positive values are positive valence, negative value are negative
        valence.
        """
        text, words_and_emoticons, is_cap_diff = self.preprocess(text)

        sentiments = []
        for item in words_and_emoticons:
            valence = 0
            i = words_and_emoticons.index(item)
            if (i < len(words_and_emoticons) - 1 and item.lower() == "kind" and \
                words_and_emoticons[i+1].lower() == "of") or \
                item.lower() in BOOSTER_DICT:
                sentiments.append(valence)
                continue
            item_lowercase = item.lower()
            if item_lowercase in self.lexicon:
                #get the sentiment valence
                valence = float(self.lexicon[item_lowercase])

                #check if sentiment laden word is in ALL CAPS (while others aren't)

                if item.isupper() and is_cap_diff:
                    if valence > 0:
                        valence += C_INCR
                    else:
                        valence -= C_INCR



                if i > 0 and words_and_emoticons[i-1].lower() not in self.lexicon:
                    s1 = scalar_inc_dec(words_and_emoticons[i-1], valence, is_cap_diff)
                    valence = valence+s1
                    if negated([words_and_emoticons[i-1]]):
                        valence = valence*N_SCALAR
                if i > 1 and words_and_emoticons[i-2].lower() not in self.lexicon:
                    s2 = scalar_inc_dec(words_and_emoticons[i-2], valence, is_cap_diff)
                    if s2 != 0:
                        s2 = s2*0.95
                    valence = valence+s2
                    # check for special use of 'never' as valence modifier
                    # instead of negation
                    if words_and_emoticons[i-2] == "never" and\
                       (words_and_emoticons[i-1] == "so" or
                        words_and_emoticons[i-1] == "this"):
                        valence = valence*1.5
                    # otherwise, check for negation/nullification
                    elif negated([words_and_emoticons[i-2]]):
                        valence = valence*N_SCALAR
                if i > 2 and words_and_emoticons[i-3].lower() not in self.lexicon:
                    s3 = scalar_inc_dec(words_and_emoticons[i-3], valence, is_cap_diff)
                    if s3 != 0:
                        s3 = s3*0.9
                    valence = valence+s3
                    # check for special use of 'never' as valence modifier instead of negation
                    if words_and_emoticons[i-3] == "never" and \
                       (words_and_emoticons[i-2] == "so" or words_and_emoticons[i-2] == "this") or \
                       (words_and_emoticons[i-1] == "so" or words_and_emoticons[i-1] == "this"):
                        valence = valence*1.25
                    # otherwise, check for negation/nullification
                    elif negated([words_and_emoticons[i-3]]):
                        valence = valence*N_SCALAR


                    # future work: consider other sentiment-laden idioms
                    # other_idioms =
                    # {"back handed": -2, "blow smoke": -2, "blowing smoke": -2,
                    #  "upper hand": 1, "break a leg": 2,
                    #  "cooking with gas": 2, "in the black": 2, "in the red": -2,
                    #  "on the ball": 2,"under the weather": -2}

                    onezero = "{} {}".format(words_and_emoticons[i-1], words_and_emoticons[i])

                    twoonezero = "{} {} {}".format(words_and_emoticons[i-2],
                                                   words_and_emoticons[i-1], words_and_emoticons[i])

                    twoone = "{} {}".format(words_and_emoticons[i-2], words_and_emoticons[i-1])

                    threetwoone = "{} {} {}".format(words_and_emoticons[i-3],
                                                    words_and_emoticons[i-2], words_and_emoticons[i-1])

                    threetwo = "{} {}".format(words_and_emoticons[i-3], words_and_emoticons[i-2])
                    if onezero in SPECIAL_CASE_IDIOMS:
                        valence = SPECIAL_CASE_IDIOMS[onezero]
                    elif twoonezero in SPECIAL_CASE_IDIOMS:
                        valence = SPECIAL_CASE_IDIOMS[twoonezero]
                    elif twoone in SPECIAL_CASE_IDIOMS:
                        valence = SPECIAL_CASE_IDIOMS[twoone]
                    elif threetwoone in SPECIAL_CASE_IDIOMS:
                        valence = SPECIAL_CASE_IDIOMS[threetwoone]
                    elif threetwo in SPECIAL_CASE_IDIOMS:
                        valence = SPECIAL_CASE_IDIOMS[threetwo]
                    if len(words_and_emoticons)-1 > i:
                        zeroone = "{} {}".format(words_and_emoticons[i], words_and_emoticons[i+1])
                        if zeroone in SPECIAL_CASE_IDIOMS:
                            valence = SPECIAL_CASE_IDIOMS[zeroone]
                    if len(words_and_emoticons)-1 > i+1:
                        zeroonetwo = "{} {} {}".format(words_and_emoticons[i], words_and_emoticons[i+1], words_and_emoticons[i+2])
                        if zeroonetwo in SPECIAL_CASE_IDIOMS:
                            valence = SPECIAL_CASE_IDIOMS[zeroonetwo]

                    # check for booster/dampener bi-grams such as 'sort of' or 'kind of'
                    if threetwo in BOOSTER_DICT or twoone in BOOSTER_DICT:
                        valence = valence+B_DECR

                # check for negation case using "least"
                if i > 1 and words_and_emoticons[i-1].lower() not in self.lexicon \
                   and words_and_emoticons[i-1].lower() == "least":
                    if words_and_emoticons[i-2].lower() != "at" and words_and_emoticons[i-2].lower() != "very":
                        valence = valence*N_SCALAR
                elif i > 0 and words_and_emoticons[i-1].lower() not in self.lexicon \
                     and words_and_emoticons[i-1].lower() == "least":
                    valence = valence*N_SCALAR
            sentiments.append(valence)

        sentiments = self._but_check(words_and_emoticons, sentiments)

        return self.score_valence(sentiments, text)

    def _but_check(self, words_and_emoticons, sentiments):
        # check for modification in sentiment due to contrastive conjunction 'but'
        if 'but' in words_and_emoticons or 'BUT' in words_and_emoticons:
            try:
                bi = words_and_emoticons.index('but')
            except ValueError:
                bi = words_and_emoticons.index('BUT')
            for sentiment in sentiments:
                si = sentiments.index(sentiment)
                if si < bi:
                    sentiments.pop(si)
                    sentiments.insert(si, sentiment*0.5)
                elif si > bi:
                    sentiments.pop(si)
                    sentiments.insert(si, sentiment*1.5)
        return sentiments

    def score_valence(self, sentiments, text):
        if sentiments:
            sum_s = float(sum(sentiments))
            #print sentiments, sum_s

            # check for added emphasis resulting from exclamation points (up to 4 of them)
            ep_count = text.count("!")
            if ep_count > 4:
                ep_count = 4
            ep_amplifier = ep_count*0.292
            # (empirically derived mean sentiment intensity rating increase
            # for exclamation points)
            if sum_s > 0:
                sum_s += ep_amplifier
            elif sum_s < 0:
                sum_s -= ep_amplifier

            # check for added emphasis resulting from question marks (2 or 3+)
            qm_count = text.count("?")
            qm_amplifier = 0
            if qm_count > 1:
                if qm_count <= 3:
                    qm_amplifier = qm_count*0.18
                else:
                    qm_amplifier = 0.96
                if sum_s > 0:
                    sum_s += qm_amplifier
                elif  sum_s < 0:
                    sum_s -= qm_amplifier

            compound = normalize(sum_s)

            # want separate positive versus negative sentiment scores
            pos_sum = 0.0
            neg_sum = 0.0
            neu_count = 0
            for sentiment_score in sentiments:
                if sentiment_score > 0:
                    pos_sum += (float(sentiment_score) +1) # compensates for neutral words that are counted as 1
                if sentiment_score < 0:
                    neg_sum += (float(sentiment_score) -1) # when used with math.fabs(), compensates for neutrals
                if sentiment_score == 0:
                    neu_count += 1

            if pos_sum > math.fabs(neg_sum):
                pos_sum += (ep_amplifier+qm_amplifier)
            elif pos_sum < math.fabs(neg_sum):
                neg_sum -= (ep_amplifier+qm_amplifier)

            total = pos_sum + math.fabs(neg_sum) + neu_count
            pos = math.fabs(pos_sum / total)
            neg = math.fabs(neg_sum / total)
            neu = math.fabs(neu_count / total)

        else:
            compound = 0.0; pos = 0.0; neg = 0.0; neu = 0.0

        sentiment_dict = \
            {"neg" : round(neg, 3),
             "neu" : round(neu, 3),
             "pos" : round(pos, 3),
             "compound" : round(compound, 4)}

        return sentiment_dict




def demo():
    text1 = "At least (I think...) it isn't a HORRIBLE :-) book!"
    text2 = "Today kinda sux! But I'll get by, lol"
    sid = SentimentIntensityDetector()
    ss1 = sid.sentiment(text1)
    print(text1)
    print(ss1)

    """
    text == "At least (I think...) it isn't a HORRIBLE :-) book!"
    text_mod == 'At least I think it isnt a HORRIBLE  book'
    is_cap_diff == True
    p == '!?!?'
    pword == '!?!?book'
    words_and_emoticons == ['At', 'least', '(I', 'think...)', 'it', "isn't", 'HORRIBLE', ':-)', 'book']
    words_only == ['At', 'least', 'think', 'it', 'isnt', 'HORRIBLE', 'book']
    """


    ss2 = sid.sentiment(text2)
    print(text2)
    print(ss2)

    """
    text == "Today kinda sux! But I'll get by, lol"
    text_mod == 'Today kinda sux But Ill get by lol'
    is_cap_diff == False
    p == '!?!?'
    pword == ''!?!?lol''
    words_and_emoticons == ['Today', 'kinda', 'sux', 'But', "I'll", 'get', 'by', 'lol']
    words_only == ['Today', 'kinda', 'sux', 'But', 'Ill', 'get', 'by', 'lol']
    """


DEMO = 0

if __name__ == '__main__':
    if DEMO:
        demo()
    else:
        import doctest
        doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)


