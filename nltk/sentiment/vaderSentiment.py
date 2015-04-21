#!/usr/bin/python
# coding: utf-8 
'''
Created on July 04, 2013
@author: C.J. Hutto

Citation Information

If you use any of the VADER sentiment analysis tools 
(VADER sentiment lexicon or Python code for rule-based sentiment 
analysis engine) in your work or research, please cite the paper. 
For example:

  Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model for 
  Sentiment Analysis of Social Media Text. Eighth International Conference on 
  Weblogs and Social Media (ICWSM-14). Ann Arbor, MI, June 2014.
'''

import os, math, re, sys, fnmatch, string 
reload(sys)

def make_lex_dict(f):
    return dict(map(lambda (w, m): (w, float(m)), [wmsr.strip().split('\t')[0:2] for wmsr in open(f) ]))
    
f = 'vader_sentiment_lexicon.txt' # empirically derived valence ratings for words, emoticons, slang, swear words, acronyms/initialisms
try:
    WORD_VALENCE_DICT = make_lex_dict(f)
except:
    f = os.path.join(os.path.dirname(__file__),'vader_sentiment_lexicon.txt')
    WORD_VALENCE_DICT = make_lex_dict(f)


##CONSTANTS#####

#(empirically derived mean sentiment intensity rating increase for booster words)
B_INCR = 0.293
B_DECR = -0.293

#(empirically derived mean sentiment intensity rating increase for using ALLCAPs to emphasize a word)
c_INCR = 0.733

# for removing punctuation
REGEX_REMOVE_PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))

PUNC_LIST = [".", "!", "?", ",", ";", ":", "-", "'", "\"",
                "!!", "!!!", "??", "???", "?!?", "!?!", "?!?!", "!?!?"]
NEGATE = ["aint", "arent", "cannot", "cant", "couldnt", "darent", "didnt", "doesnt",
              "ain't", "aren't", "can't", "couldn't", "daren't", "didn't", "doesn't",
              "dont", "hadnt", "hasnt", "havent", "isnt", "mightnt", "mustnt", "neither",
              "don't", "hadn't", "hasn't", "haven't", "isn't", "mightn't", "mustn't",
              "neednt", "needn't", "never", "none", "nope", "nor", "not", "nothing", "nowhere",
              "oughtnt", "shant", "shouldnt", "uhuh", "wasnt", "werent",
              "oughtn't", "shan't", "shouldn't", "uh-uh", "wasn't", "weren't",
              "without", "wont", "wouldnt", "won't", "wouldn't", "rarely", "seldom", "despite"]
# booster/dampener 'intensifiers' or 'degree adverbs' http://en.wiktionary.org/wiki/Category:English_degree_adverbs
BOOSTER_DICT = {"absolutely": B_INCR, "amazingly": B_INCR, "awfully": B_INCR, "completely": B_INCR, "considerably": B_INCR,
                "decidedly": B_INCR, "deeply": B_INCR, "effing": B_INCR, "enormously": B_INCR,
                "entirely": B_INCR, "especially": B_INCR, "exceptionally": B_INCR, "extremely": B_INCR,
                "fabulously": B_INCR, "flipping": B_INCR, "flippin": B_INCR,
                "fricking": B_INCR, "frickin": B_INCR, "frigging": B_INCR, "friggin": B_INCR, "fully": B_INCR, "fucking": B_INCR,
                "greatly": B_INCR, "hella": B_INCR, "highly": B_INCR, "hugely": B_INCR, "incredibly": B_INCR,
                "intensely": B_INCR, "majorly": B_INCR, "more": B_INCR, "most": B_INCR, "particularly": B_INCR,
                "purely": B_INCR, "quite": B_INCR, "really": B_INCR, "remarkably": B_INCR,
                "so": B_INCR,  "substantially": B_INCR,
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

def negated(list, nWords=[], includeNT=True):
    nWords.extend(NEGATE)
    for word in nWords:
        if word in list:
            return True
    if includeNT:
        for word in list:
            if "n't" in word:
                return True
    if "least" in list:
        i = list.index("least")
        if i > 0 and list[i-1] != "at":
            return True
    return False

def normalize(score, alpha=15):
    # normalize the score to be between -1 and 1 using an alpha that approximates the max expected value
    normScore = score/math.sqrt( ((score*score) + alpha) )
    return normScore

def wildCardMatch(patternWithWildcard, listOfStringsToMatchAgainst):
    listOfMatches = fnmatch.filter(listOfStringsToMatchAgainst, patternWithWildcard)
    return listOfMatches


def isALLCAP_differential(wordList):
    countALLCAPS= 0
    for w in wordList:
        if w.isupper():
            countALLCAPS += 1
    cap_differential = len(wordList) - countALLCAPS
    if cap_differential > 0 and cap_differential < len(wordList):
        isDiff = True
    else: isDiff = False
    return isDiff

#check if the preceding words increase, decrease, or negate/nullify the valence
def scalar_inc_dec(word, valence, isCap_diff):
    scalar = 0.0
    word_lower = word.lower()
    if word_lower in BOOSTER_DICT:
        scalar = BOOSTER_DICT[word_lower]
        if valence < 0: scalar *= -1
        #check if booster/dampener word is in ALLCAPS (while others aren't)
        if word.isupper() and isCap_diff:
            if valence > 0: scalar += c_INCR
            else:  scalar -= c_INCR
    return scalar

def sentiment(text):
    """
    Returns a float for sentiment strength based on the input text.
    Positive values are positive valence, negative value are negative valence.
    """
    if not isinstance(text, unicode) and not isinstance(text, str):
        text = str(text)

    wordsAndEmoticons = text.split() #doesn't separate words from adjacent punctuation (keeps emoticons & contractions)
    text_mod = REGEX_REMOVE_PUNCTUATION.sub('', text) # removes punctuation (but loses emoticons & contractions)
    wordsOnly = text_mod.split()
    # get rid of empty items or single letter "words" like 'a' and 'I' from wordsOnly
    for word in wordsOnly:
        if len(word) <= 1:
            wordsOnly.remove(word)    
    # now remove adjacent & redundant punctuation from [wordsAndEmoticons] while keeping emoticons and contractions

    for word in wordsOnly:
        for p in PUNC_LIST:
            pword = p + word
            x1 = wordsAndEmoticons.count(pword)
            while x1 > 0:
                i = wordsAndEmoticons.index(pword)
                wordsAndEmoticons.remove(pword)
                wordsAndEmoticons.insert(i, word)
                x1 = wordsAndEmoticons.count(pword)
            
            wordp = word + p
            x2 = wordsAndEmoticons.count(wordp)
            while x2 > 0:
                i = wordsAndEmoticons.index(wordp)
                wordsAndEmoticons.remove(wordp)
                wordsAndEmoticons.insert(i, word)
                x2 = wordsAndEmoticons.count(wordp)

    # get rid of residual empty items or single letter "words" like 'a' and 'I' from wordsAndEmoticons
    for word in wordsAndEmoticons:
        if len(word) <= 1:
            wordsAndEmoticons.remove(word)
    
    # remove stopwords from [wordsAndEmoticons]
    #stopwords = [str(word).strip() for word in open('stopwords.txt')]
    #for word in wordsAndEmoticons:
    #    if word in stopwords:
    #        wordsAndEmoticons.remove(word)
    
    # check for negation

    isCap_diff = isALLCAP_differential(wordsAndEmoticons)

    sentiments = []
    for item in wordsAndEmoticons:
        v = 0
        i = wordsAndEmoticons.index(item)
        if (i < len(wordsAndEmoticons)-1 and item.lower() == "kind" and \
           wordsAndEmoticons[i+1].lower() == "of") or item.lower() in BOOSTER_DICT:
            sentiments.append(v)
            continue
        item_lowercase = item.lower()
        if item_lowercase in WORD_VALENCE_DICT:
            #get the sentiment valence
            v = float(WORD_VALENCE_DICT[item_lowercase])
            
            #check if sentiment laden word is in ALLCAPS (while others aren't)
            
            if item.isupper() and isCap_diff:
                if v > 0: v += c_INCR
                else: v -= c_INCR


            n_scalar = -0.74
            if i > 0 and wordsAndEmoticons[i-1].lower() not in WORD_VALENCE_DICT:
                s1 = scalar_inc_dec(wordsAndEmoticons[i-1], v,isCap_diff)
                v = v+s1
                if negated([wordsAndEmoticons[i-1]]): v = v*n_scalar
            if i > 1 and wordsAndEmoticons[i-2].lower() not in WORD_VALENCE_DICT:
                s2 = scalar_inc_dec(wordsAndEmoticons[i-2], v,isCap_diff)
                if s2 != 0: s2 = s2*0.95
                v = v+s2
                # check for special use of 'never' as valence modifier instead of negation
                if wordsAndEmoticons[i-2] == "never" and (wordsAndEmoticons[i-1] == "so" or wordsAndEmoticons[i-1] == "this"): 
                    v = v*1.5                    
                # otherwise, check for negation/nullification
                elif negated([wordsAndEmoticons[i-2]]): v = v*n_scalar
            if i > 2 and wordsAndEmoticons[i-3].lower() not in WORD_VALENCE_DICT:
                s3 = scalar_inc_dec(wordsAndEmoticons[i-3], v,isCap_diff)
                if s3 != 0: s3 = s3*0.9
                v = v+s3
                # check for special use of 'never' as valence modifier instead of negation
                if wordsAndEmoticons[i-3] == "never" and \
                   (wordsAndEmoticons[i-2] == "so" or wordsAndEmoticons[i-2] == "this") or \
                   (wordsAndEmoticons[i-1] == "so" or wordsAndEmoticons[i-1] == "this"):
                    v = v*1.25
                # otherwise, check for negation/nullification
                elif negated([wordsAndEmoticons[i-3]]): v = v*n_scalar
                

                # future work: consider other sentiment-laden idioms
                #other_idioms = {"back handed": -2, "blow smoke": -2, "blowing smoke": -2, "upper hand": 1, "break a leg": 2, 
                #                "cooking with gas": 2, "in the black": 2, "in the red": -2, "on the ball": 2,"under the weather": -2}
            
                onezero = u"{} {}".format(wordsAndEmoticons[i-1], wordsAndEmoticons[i])
                twoonezero = u"{} {} {}".format(wordsAndEmoticons[i-2], wordsAndEmoticons[i-1], wordsAndEmoticons[i])
                twoone = u"{} {}".format(wordsAndEmoticons[i-2], wordsAndEmoticons[i-1])
                threetwoone = u"{} {} {}".format(wordsAndEmoticons[i-3], wordsAndEmoticons[i-2], wordsAndEmoticons[i-1])
                threetwo = u"{} {}".format(wordsAndEmoticons[i-3], wordsAndEmoticons[i-2])
                if onezero in SPECIAL_CASE_IDIOMS:
                    v = SPECIAL_CASE_IDIOMS[onezero]
                elif twoonezero in SPECIAL_CASE_IDIOMS:
                    v = SPECIAL_CASE_IDIOMS[twoonezero]
                elif twoone in SPECIAL_CASE_IDIOMS:
                    v = SPECIAL_CASE_IDIOMS[twoone]
                elif threetwoone in SPECIAL_CASE_IDIOMS:
                    v = SPECIAL_CASE_IDIOMS[threetwoone]
                elif threetwo in SPECIAL_CASE_IDIOMS:
                    v = SPECIAL_CASE_IDIOMS[threetwo]
                if len(wordsAndEmoticons)-1 > i:
                    zeroone = u"{} {}".format(wordsAndEmoticons[i], wordsAndEmoticons[i+1])
                    if zeroone in SPECIAL_CASE_IDIOMS:
                        v = SPECIAL_CASE_IDIOMS[zeroone]
                if len(wordsAndEmoticons)-1 > i+1:
                    zeroonetwo = u"{} {}".format(wordsAndEmoticons[i], wordsAndEmoticons[i+1], wordsAndEmoticons[i+2])
                    if zeroonetwo in SPECIAL_CASE_IDIOMS:
                        v = SPECIAL_CASE_IDIOMS[zeroonetwo]
                
                # check for booster/dampener bi-grams such as 'sort of' or 'kind of'
                if threetwo in BOOSTER_DICT or twoone in BOOSTER_DICT:
                    v = v+B_DECR
            
            # check for negation case using "least"
            if i > 1 and wordsAndEmoticons[i-1].lower() not in WORD_VALENCE_DICT \
                and wordsAndEmoticons[i-1].lower() == "least":
                if (wordsAndEmoticons[i-2].lower() != "at" and wordsAndEmoticons[i-2].lower() != "very"):
                    v = v*n_scalar
            elif i > 0 and wordsAndEmoticons[i-1].lower() not in WORD_VALENCE_DICT \
                and wordsAndEmoticons[i-1].lower() == "least":
                v = v*n_scalar
        sentiments.append(v) 
            
    # check for modification in sentiment due to contrastive conjunction 'but'
    if 'but' in wordsAndEmoticons or 'BUT' in wordsAndEmoticons:
        try: bi = wordsAndEmoticons.index('but')
        except: bi = wordsAndEmoticons.index('BUT')
        for s in sentiments:
            si = sentiments.index(s)
            if si < bi: 
                sentiments.pop(si)
                sentiments.insert(si, s*0.5)
            elif si > bi: 
                sentiments.pop(si)
                sentiments.insert(si, s*1.5) 
                
    if sentiments:                      
        sum_s = float(sum(sentiments))
        #print sentiments, sum_s
        
        # check for added emphasis resulting from exclamation points (up to 4 of them)
        ep_count = text.count("!")
        if ep_count > 4: ep_count = 4
        ep_amplifier = ep_count*0.292 #(empirically derived mean sentiment intensity rating increase for exclamation points)
        if sum_s > 0:  sum_s += ep_amplifier
        elif  sum_s < 0: sum_s -= ep_amplifier
        
        # check for added emphasis resulting from question marks (2 or 3+)
        qm_count = text.count("?")
        qm_amplifier = 0
        if qm_count > 1:
            if qm_count <= 3: qm_amplifier = qm_count*0.18
            else: qm_amplifier = 0.96
            if sum_s > 0:  sum_s += qm_amplifier
            elif  sum_s < 0: sum_s -= qm_amplifier

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
        
        if pos_sum > math.fabs(neg_sum): pos_sum += (ep_amplifier+qm_amplifier)
        elif pos_sum < math.fabs(neg_sum): neg_sum -= (ep_amplifier+qm_amplifier)
        
        total = pos_sum + math.fabs(neg_sum) + neu_count
        pos = math.fabs(pos_sum / total)
        neg = math.fabs(neg_sum / total)
        neu = math.fabs(neu_count / total)
        
    else:
        compound = 0.0; pos = 0.0; neg = 0.0; neu = 0.0
        
    s = {"neg" : round(neg, 3), 
         "neu" : round(neu, 3),
         "pos" : round(pos, 3),
         "compound" : round(compound, 4)}
    return s


if __name__ == '__main__':
    # --- examples -------
    sentences = [
                u"VADER is smart, handsome, and funny.",       # positive sentence example
                u"VADER is smart, handsome, and funny!",       # punctuation emphasis handled correctly (sentiment intensity adjusted)
                u"VADER is very smart, handsome, and funny.",  # booster words handled correctly (sentiment intensity adjusted)
                u"VADER is VERY SMART, handsome, and FUNNY.",  # emphasis for ALLCAPS handled
                u"VADER is VERY SMART, handsome, and FUNNY!!!",# combination of signals - VADER appropriately adjusts intensity
                u"VADER is VERY SMART, really handsome, and INCREDIBLY FUNNY!!!",# booster words & punctuation make this close to ceiling for score
                u"The book was good.",         # positive sentence
                u"The book was kind of good.", # qualified positive sentence is handled correctly (intensity adjusted)
                u"The plot was good, but the characters are uncompelling and the dialog is not great.", # mixed negation sentence
                u"A really bad, horrible book.",       # negative sentence with booster words
                u"At least it isn't a horrible book.", # negated negative sentence with contraction
                u":) and :D",     # emoticons handled
                u"",              # an empty string is correctly handled
                u"Today sux",     #  negative slang handled
                u"Today sux!",    #  negative slang with punctuation emphasis handled
                u"Today SUX!",    #  negative slang with capitalization emphasis
                u"Today kinda sux! But I'll get by, lol" # mixed sentiment example with slang and constrastive conjunction "but"
                 ]
    paragraph = "It was one of the worst movies I've seen, despite good reviews. \
    Unbelievably bad acting!! Poor direction. VERY poor production. \
    The movie was bad. Very bad movie. VERY bad movie. VERY BAD movie. VERY BAD movie!"
    
    from nltk import tokenize
    lines_list = tokenize.sent_tokenize(paragraph)
    sentences.extend(lines_list)
    
    tricky_sentences = [
                        "Most automated sentiment analysis tools are shit.",
                        "VADER sentiment analysis is the shit.",
                        "Sentiment analysis has never been good.",
                        "Sentiment analysis with VADER has never been this good.",
                        "Warren Beatty has never been so entertaining.",
                        "I won't say that the movie is astounding and I wouldn't claim that the movie is too banal either.",
                        "I like to hate Michael Bay films, but I couldn't fault this one",
                        "It's one thing to watch an Uwe Boll film, but another thing entirely to pay for it",
                        "The movie was too good",
                        "This movie was actually neither that funny, nor super witty.",
                        "This movie doesn't care about cleverness, wit or any other kind of intelligent humor.",
                        "Those who find ugly meanings in beautiful things are corrupt without being charming.",
                        "There are slow and repetitive parts, BUT it has just enough spice to keep it interesting.",
                        "The script is not fantastic, but the acting is decent and the cinematography is EXCELLENT!", 
                        "Roger Dodger is one of the most compelling variations on this theme.",
                        "Roger Dodger is one of the least compelling variations on this theme.",
                        "Roger Dodger is at least compelling as a variation on the theme.",
                        "they fall in love with the product",
                        "but then it breaks",
                        "usually around the time the 90 day warranty expires",
                        "the twin towers collapsed today",
                        "However, Mr. Carter solemnly argues, his client carried out the kidnapping under orders and in the ''least offensive way possible.''"
                        ]
    sentences.extend(tricky_sentences)
    for sentence in sentences:
        print sentence
        ss = sentiment(sentence)
        print "\t" + str(ss)
    
    print "\n\n Done!"
