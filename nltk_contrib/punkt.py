"""
Punkt -- Kiss & Strunk (2006)

Original Python port by Willy <willy@csse.unimelb.edu.au>
Reworked by Steven Bird <sb@csse.unimelb.edu.au>

Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
  Boundary Detection.  Computational Linguistics 32: 485-525.
"""

import sys, re

from nltk import tokenize

# Parameters

ABBREV = 0.3       # cut-off value whether a "token" is an abbreviation
ABBREV_BACKOFF = 5 # upper cut-off for Mikheev's(2002) abbreviation detection algorithm
COLLOCATION = 7.88 # minimal log-likelihood value that two tokens need to be considered as a collocation
CONTEXT_SIZE = 4   # window size of the tokens that appears around a period that is taken into account for classification
SENT_STARTER = 30  # minimal log-likelihood value that a token requires to be considered as a frequent sentence starter


# Corpus statistics

num_of_periods = 0      # the number of tokens that ends with a period in the corpus
num_of_noperiods = 0    # the number of tokens that does not end with a period
num_of_sentences = 0    # the number of sentences determined by the first stage of the algorithm (type-based classification)


# data structures that are needed to store the information of the corpus

abbs = {}                # all abbreviation candidates
abbreviations = {}       # all tokens that have been classified as abbreviations
rare_abbreviations = {}  # abbreviations detected by Mikheev's algorithm
collocations = {}        # all extracted collocations
orthography_data = {}    # orthographic data (lower and uppercase) of all tokens
orthography_context = {} # simpler orthographic statistics for Mikheev's algorithm
sentence_starters = {}   # tokens that frequently start a new sentence


def preprocess(input):
    for line in input:
        tokens = list(tokenize.pword(line))
        if tokens:
            for token in tokens:
                yield token
        yield "\n"

def count_tokens(input_tokens):
    return len([t for t in input_tokens if t != "\n"])

def count_types(input_tokens):
    types = {}
    for token in input_tokens:
        if token != "\n":
            token = token.lower()
            if token not in types:
                types[token] = 0
            types[token] += 1
    return types

def count_periods(input_tokens):
    return len([t for t in input_tokens if t.endswith(".")])

def count_numbers(input_tokens):
    return len([t for t in input_tokens if re.match(r'\d+\.?$', t)])

def get_abbreviation_data():
    """
    A function to:
    1. Generate a dictionary of abbreviation candidates to be stored in `abbs`
       The candidates are tokens that ever occur with a final period in the corpus
    2. Calculates the scaled log-likelihood for each candidate
    3. Classify all candidates which log-likelihood score is above ABBREV
       as abbreviations and store them in `abbreviations`
    """
    from operator import itemgetter
    import re, math
    print "\nProcessing abbreviations..."
    global types, abbs, abbreviations, num_of_periods, num_of_tokens, ABBREV
    for type in sorted(types):
        rule1 = re.search(r'[A-Za-z]', type)
        rule2 = re.search(r'^(?P<no_final_period>.+)\.$', type)
        rule3 = re.search(r'^\d+\.$', type)
        rule4 = re.search(r'^\.+$', type)
        if rule1 and rule2 and (not rule3) and (not rule4):
            type_no_final_period = rule2.group('no_final_period')
            (type_without_period, count_period) = re.subn('\.', '', type)

            """
            item0 is the number of times the unique token occured with a final period
            item1 is the number of times the unique token occured without a final period
            item2 is the number of all occurences of the unique token both with and without final period
            item3 is the log-likelihood score of the unique token
            """
            item0 = item1 = item2 = item3 = 0

            if type_no_final_period not in abbs:
                abbs[type_no_final_period] = []
            item0 = types[type]

            if type_no_final_period in types:
                item1 = types[type_no_final_period]
            else:
                item1 = 0

            item2 = item0 + item1
            item3 = log_likelihood(item2, num_of_periods, item0, num_of_tokens)
            item3 *= 1/math.exp(len(type_without_period))
            item3 *= count_period
            """
            Original implementation doesn't care about this, they use Perl's features which will generate
            inf (infinite) for a very large number. OverflowError will capture the case where denominator 
            is very big such as 2^253.
            """
            try:
                denominator = math.pow(len(type_without_period), item1)
                item3 = 1.0 * item3 / denominator
            except OverflowError:
                denominator = 0
                item3 = 0
            abbs[type_no_final_period] = [item0, item1, item2, item3]
            
    for (candidate, _) in sorted(abbs.items(), lambda x,y : cmp(y[1][3],x[1][3])):
        if abbs[candidate][3] >= ABBREV:
            abbreviations[candidate] = abbs[candidate][3]
            print candidate, "\t\t", abbreviations[candidate]

def log_likelihood(count_w1, count_w2, count_w12, N):
    """
    A function that calculates the modified Dunning log-likelihood scores for abbreviation candidates
    The details of how this works is available in the paper
    """
    import math

    p1 = 1.0 * count_w2 / N
    p2 = 0.99

    null_hypo = 1.0 * count_w12 * (math.log(p1)) + (count_w1 - count_w12) * (math.log(1.0 - p1))
    alt_hypo  = 1.0 * count_w12 * (math.log(p2)) + (count_w1 - count_w12) * (math.log(1.0 - p2))

    likelihood = null_hypo - alt_hypo

    return (-2.0 * likelihood)

def annotate():
    """
    Annotate the corpus with intermediate annotation.
    This is the first-stage type-based classification.
    """
    global input_tokens
    import re
    for (index, token) in zip(range(len(input_tokens)), input_tokens):
    #    rule1 = re.search(r'^(?P<no_final_period>.+)\.$', token)
    #    rule2 = re.search(r'\.{2,}$', token)
    #    if rule1 and (not rule2): 

        #If the token contains a final period and not ellipsis
        if token.endswith(".") and not token.endswith(".."):
            token_no_period = token[:-1].lower()
    #        token_no_period = rule1.group('no_final_period').lower()
            rule_no_hyphen = re.search(r'\-(?P<no_hyphen>[^-]+)$', token_no_period)
            
            #If the token has been classified as an abbreviation, annotate the period as <A>
            if token_no_period in abbreviations:
                token += "<A>"
            #If the token contains a hyphen and the part following hyphen is an abbreviation type..
            elif rule_no_hyphen:
                lastpart = rule_no_hyphen.group('no_hyphen')
                #annotate it as an abbreviation
                if lastpart in abbreviations:
                    token += "<A>"
                #annotate it as a sentence boundary marker
                else:
                    token += "<S>"
            #Anything else is sentence boundary marker
            else:
                token += "<S>"
        #Annotate single ?, !, . as sentence boundary marker
        elif ((token == "?") or (token == "!") or (token == ".")):
            token += "<S>"
        #Annotate tokens that consist only of periods as ellipsis
        elif re.search(r'^\.{2,}$', token):
            token += "<E>"
        input_tokens[index] = token

def normalize(token, flag):
    """
    Takes 2 arguments:
    token: the token that we're going to normalize
    flag: indication for clean_tags function (see clean_tags definition for details)

    Normalizes a token for the dictionary look up
    Removes final tag
    Converts to lowercase
    Converts all numeric types to generic '##number##'
    """
    import re
    token = clean_tags(token, flag)
    token = token.lower()
    if re.search(r'^\d+\.?$', token):
        token = '##number##'
    return token

def clean_tags(token, flag):
    """
    Takes 2 arguments:
    token: the token that we're going to strip off the annotation given
    flag: indication whether we should delete the period before <S>

    This function removes the tags given from the first-stage annotation stage
    """
    import re
    temp = re.search(r'(?P<tag>\<[AES\>\<]+\>)$', token)
    if (temp):
        tag = temp.group('tag')
    (token, count) = re.subn(r'(\<[AES\>\<]+\>)$', '', token)
    if count:
        if flag == False:
            if (tag == "<S>") and (token != ".") :
                if token[-1] == ".":
                    token = token[:-1]
            #    token = re.sub(r'\.$', '', token)
    
    return token


def get_orthography_data():
    """
    This is a function to get the orthographic data for each token in the corpus
    
    Warning from the original authors: "this function is somewhat inelegant and complicated,"
    I guess mine will be the same too!

    The original paper described this in page 11
    """
    print "Extracting capitalization data..."
    import re
    global input_tokens, orthography_data
    after_s = after_a = False
    n_seen = 0 

    #Go through all tokens in the corpus
    for token in input_tokens:
        if token == "\n":
            n_seen += 1 #Number of newlines seen so far, it will be reset later in the loop

            #Assume a preceding sentence boundary if we have 2 newlines in a row
            if (n_seen >= 2) and (after_a == False):
                after_s = True
            continue
        else:
            #Normalize the token..
            buf = normalize(token, False)
        
        #Initialized some values
        if buf not in orthography_data:
            orthography_data[buf] = [0, 0, 0, 0, 0, 0]

        upper = re.search(r'^[A-Z]', token)
        lower = re.search(r'^[a-z]', token)

        #Keep track of the occurrence of `buf` in both upper and lowercase
        if upper:
            orthography_data[buf][0] += 1
        elif lower:
            orthography_data[buf][1] += 1

        #If the current position follows a sentence boundary (according to the first stage classification)
        if after_s == True:
            #Keep track of the occurrence of `buf` in both upper and lowercase
            if upper:
                orthography_data[buf][2] += 1
            elif lower:
                orthography_data[buf][3] += 1
        #If the current position follows an abbreviation(according to the first stage classification)
        #Do not count for orthographic statistics
        elif after_a == True:
            #Do nothing!
            pass    
        #Tokens must be inside a sentence!
        else:
            if n_seen == 0:
                #Keep track of the occurrence of `buf` in both upper and lowercase
                if upper:
                    orthography_data[buf][4] += 1
                elif lower:
                    orthography_data[buf][5] += 1

        #If the current tokend is classified as sentence boundary marker
        if token.endswith("<S>"):
            #And it's not a number or potential initial (cannot be classified in the first stage)
            if (not re.search(r'^[0-9,\.-]+\.\<S\>$', token)) :
                if (not re.search(r'^[A-Za-z]\.\<S\>$', token)) :
                    #Assume that there is a sentence boundary after the current token
                    after_s = True
                else:
                    #Otherwise assume there is abbreviation after the current token 
                    #So that the next token will not be counted for orthographic statistics
                    after_a = True
            else:
                #Assume there is abbreviation after the current token 
                #So that the next token will not be counted for orthographic statistics
                after_a = True
        #Current token has been classified as either abbreviation or ellipsis, so we can be sure that there is
        #abbreviation after the current token and also there is no sentence boundary marker after this token
        elif token.endswith("<A>") or token.endswith("<E>"):
        #elif re.search(r'\<[AE]\>$', token):
            after_a = True
            after_s = False
        #Ignore empty tokens
        else:
            if token != "\n":
                after_a = False
                after_s = False

        #Reset the empty lines count if there was a token in the current line
        if token != "\n":
            n_seen = 0

def count_orthography_context(ngrams, extend):
    """
    Tries to find rare abbreviations with Mikheev's document centered approach

    This function will take 2 arguments:
    - ngrams is the window size of tokens
    - extend: if it is true, the beginning or end of the corpus is padded with ngrams-1 empty tokens
              if it is false, then we don't do anything
    """
    global input_tokens
    print "Trying to find rare abbreviations..."
    if extend:
        pad = [""] * (ngrams - 1)
        input_tokens = pad + input_tokens + pad
    
    #get n-grams
    for i in range(len(input_tokens) - ngrams):
        accum = []
        for j in range(ngrams):
            accum.append(input_tokens[i+j])
        get_orthography_count(accum)

    if extend:
        input_tokens = input_tokens[ (ngrams - 1) : (len(input_tokens) - ngrams + 1)]


def get_orthography_count(accum):
    """
    accum is the tokens that we're going to do collect our information from

    This is the function that implement's Mikheev's (2002) document centered approach. It also serves
    as orthographic back-off abbreviation detection method
    """
    import re
    global orthography_data, orthography_context

    #if a token contains a final period that has not been classified as an abbreviation
    temp = re.search(r'([A-Za-z]+)\.<S>$', accum[0])
    if temp:
        buf = normalize(temp.group(1), False)
        if buf not in orthography_context:
            orthography_context[buf] = 0

        #If the next token is a sentence-internal punctuation mark
        if re.search(r'^[,;:\.!?]', accum[1]):
            #Record the previous token is an abbreviation
            orthography_context[buf] += 1
        
        #If the next token starts with lowercase letter
        elif re.search(r'^[a-z]', accum[1]):
            buf2 = normalize(accum[1], False)
            #And it also sometimes occurs with uppercase letter and does not occur with a lowercase first letter
            #after a eentence boundary
            if (buf2 in orthography_data) and (orthography_data[buf2][2] > 0) and (orthography_data[buf2][4] == 0):
                #Record the previous token is an abbreviation
                orthography_context[buf] += 1

def get_rare_abbreviations():
    """
    Type-based backoff-method to find rare abbreviations based on the information
    collected from get_orthography_data and count_orthography_context

    Part of Mikheev's (2002) document centered approach algorithm.
    """
    from operator import itemgetter
    global abbs, orthography_context, rare_abbreviations, ABBREV, ABBREV_BACKOFF
    for (candidate, _) in sorted(abbs.items(), lambda x,y : cmp(y[1][3],x[1][3])):
        #If candidate has not been classified as an abbreviation by main algorithm
        if abbs[candidate][3] < ABBREV:
            #If it occurs rarely enough
            if abbs[candidate][2] < ABBREV_BACKOFF:
                #And there is orthographic evidence that it is an abbreviation
                #Classify the tokens as rare abbreviations and output them
                if (candidate in orthography_context) and (orthography_context[candidate] != 0):
                    rare_abbreviations[candidate] = 1
                    print "%s\t\t%s" % (candidate, rare_abbreviations[candidate])

def clear_count():
    """
    Adds the number of occurences of each unique token with and without final period
    to get a correct count
    """
    import re
    global types
    temp = {}
    for type in types:
        if type.endswith("."):
            token_no_final_period = type[:-1]
            temp[token_no_final_period] = types[type]
    
    for item in temp:
        if item not in types:
            types[item] = temp[item]
        else:
            types[item] += temp[item]

def col_log_l(count_w1, count_w2, count_w12, N):
    """
    A function that will just compute log-likelihood estimate, in the original paper it's decribed in
    algorithm 6 and 7.

    This *should* be the original Dunning log-likelihood values, unlike the previous log_l function where
    it used modified Dunning log-likelihood values
    """
    import math
    
    p = 1.0 * count_w2 / N
    p1 = 1.0 * count_w12 / count_w1
    p2 = 1.0 * (count_w2 - count_w12) / (N - count_w1)

    summand1 = count_w12 * (math.log(p)) + (count_w1 - count_w12) * (math.log(1.0 - p))

    if count_w1 == count_w12:
        summand3 = 0
    else:
        summand3 = count_w12 * (math.log(p1)) + (count_w1 - count_w12) * (math.log(1.0 - p1))

    summand2 = (count_w2 - count_w12) * (math.log(p)) + (N - count_w1 - count_w2 + count_w12) * (math.log(1.0 - p))

    if count_w2 == count_w12:
        summand4 = 0
    else:
        summand4 = (count_w2 - count_w12) * (math.log(p2)) + (N - count_w1 - count_w2 + count_w12) * (math.log(1.0 - p2))

    likelihood = summand1 + summand2 - summand3 - summand4

    return (-2.0 * likelihood)

def get_collocation_data():
    """
    Collect collocational data from the corpus for collocatoinal heuristic
    """
    global collocations, types, num_of_tokens, COLLOCATION
    print "Extracting collocation data..."

    #Collect the info first...
    count_collocations()

    #Calculate the non-modified Dunning log-likelihood values for the candidates
    for type1 in collocations.keys():
        for type2 in collocations[type1].keys():
            keep = 0
            if (types[type1] > 1) and (types[type2] > 1):
                prob = col_log_l(types[type1], types[type2], collocations[type1][type2], num_of_tokens)

                #Filter out the not-so-collocative
                if prob >= COLLOCATION:
                    if ( 1.0 * num_of_tokens / types[type1] ) > ( 1.0 * types[type2] / collocations[type1][type2] ):
                        keep = 1

            if keep == 1:
                collocations[type1][type2] = prob
            else:
                del collocations[type1][type2]

def count_collocations():
    """
    Builds a hash with cooccurring types in order to find collocations in the corpus
    """
    import re
    global input_tokens, collocations

    #Go through pairs of adjacent tokens in the corpus
    for i in range(len(input_tokens) - 1):
        (token1, token2) = input_tokens[i], input_tokens[i+1]

        #If two tokens surround a potential abbreviation period
        if token1.endswith("<A>") or re.search(r'^(\d+|[A-Za-z])\.\<S\>$', token1):
            #ignore the first newline
            if ((token2 == "\n") or (token2 == "")) and ( (i+2) < len(input_tokens) ) :
                token2 = input_tokens[i+2]
            #ignore the second newline
            if ((token2 == "\n") or (token2 == "")) and ( (i+3) < len(input_tokens) ) :
                token2 = input_tokens[i+3]
            #ignore the third newline
            if ((token2 == "\n") or (token2 == "")) and ( (i+4) < len(input_tokens) ) :
                token2 = input_tokens[i+4]
            #dont' care anymore, just go to the next token
            if (token2 == "\n") or (token2 == ""):
                continue

            token1 = normalize(token1, True)
            token2 = normalize(token2, False)

            #Keep track of the collocation statistics
            if token1 not in collocations:
                collocations[token1] = {}
                if token2 not in collocations[token1]:
                    collocations[token1][token2] = 0
            else:
                if token2 not in collocations[token1]:
                    collocations[token1][token2] = 0
            collocations[token1][token2] += 1

def get_sentence_starters(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed

    Collect the statistics of unique token that occurs after a sentence boundary
    """
    import re
    global sentence_starters, CONTEXT_SIZE, num_of_sentences
    center = CONTEXT_SIZE

    #If the current token is followed by a sentence boundary..
    if accum[center].endswith("<S>"):
        #And if not potential ordinal number and initial
        if not re.search(r'^[\d,\.-]+\.\<S\>$', accum[center]):
            if not re.search(r'^[A-Za-z]\.\<S\>$', accum[center]):
                #Add the number of sentences...
                num_of_sentences += 1
                token = normalize(accum[center+1], False)
                #ignore the first newline
                if (token == "\n") or (token == "") :
                    token = normalize(accum[center+2], False)
                #ignore the second newline
                if (token == "\n") or (token == "") :
                    token = normalize(accum[center+3], False)
                #ignore the third newline
                if (token == "\n") or (token == "") :
                    token = normalize(accum[center+4], False)

                #If the following token is alphabetic token, classify it as a sentence starter
                if not ((token == "\n") or (token == "")):
                    if re.search(r'^[A-Za-z]+$', token):
                        if token not in sentence_starters:
                            sentence_starters[token] = 0
                        sentence_starters[token] += 1


def count_sentence_starters(ngrams, extend):
    """
    Take 2 arguments:
    ngrams: the size of the windows in which the tokens will be considered
    extend: indication whether we should pad the beginning or end of the corpus with ngrams-1 empty tokens

    This function will produce dictionary of frequent sentence starters
    """
    print "Extracting frequent sentence starters..."
    global sentence_starters, types, num_of_sentences, num_of_tokens, SENT_STARTER, input_tokens

    #pad the input_tokens if necessary
    if extend:
        pad = [""] * (ngrams - 1)
        input_tokens = pad + input_tokens + pad

    #get n-grams
    for i in range(len(input_tokens) - ngrams):
        accum = []
        for j in range(ngrams):
            accum.append(input_tokens[i+j])
        #get the info first...
        get_sentence_starters(accum)

    #remove the padding if necessary
    if extend:
        input_tokens = input_tokens[ (ngrams - 1) : (len(input_tokens) - ngrams + 1)]
    
    #for each candidate, calculate the Dunning log likelihood
    for type in sorted(sentence_starters.keys()):
        if type in types:
            prob = col_log_l(num_of_sentences, types[type], sentence_starters[type], num_of_tokens)

            #filter out the not very likely candidates
            if prob >= SENT_STARTER:

                #only if the candidate occurs significantly more often than expected after a sentence boundary
                #and not significantly less often after a sentence boundary than expected
                if (1.0 * num_of_tokens / num_of_sentences) > (1.0 * types[type] / sentence_starters[type]):
                    #We'll keep it as sentence starters
                    sentence_starters[type] = prob
                #otherwise remove the candidates
                else:
                    del sentence_starters[type]
            #The rest are to be removed
            else:
                del sentence_starters[type]
    

def decide(ngrams, extend):
    """
    Take 2 arguments:
    ngrams: the size of the windows in which the tokens will be considered
    extend: indication whether we should pad the beginning or end of the corpus with ngrams-1 empty tokens

    This function acts as token-based classification stage where each token with a final period will be 
    reclassified if the evidence is supportive of the reclassification
    """
    import re
    global input_tokens, CONTEXT_SIZE
    print "Using collected data to decide remaining cases..."

    center = CONTEXT_SIZE

    #pad the input_tokens if necessary
    if extend:
        pad = [""] * (ngrams - 1)
        input_tokens = pad + input_tokens + pad

    #get n-grams
    for i in range(len(input_tokens) - ngrams):
        accum = []
        for j in range(ngrams):
            accum.append(input_tokens[i+j])
        
        #Reclassifying the tokens...
        if re.search(r'^[A-Za-z]\.\<[AS]\>$', accum[center]):
            accum = decide_initial(accum)                     #Reclassify potential initial
        elif accum[center].endswith("<A>"):
            accum = decide_abbreviation(accum)                #Determine whether abbreviation followed by sentence boundary
        elif re.search(r'^\.{2,}\<E\>$', accum[center]):
            accum = decide_ellipsis(accum)                    #Determine whether ellipsis followed by sentence boundary
        elif re.search(r'[A-Za-z]\.\<S\>$', accum[center]):
            accum = decide_sentence_period(accum)             #Reconsider a period classified as a sentence boundary marker
                                                              #by the first-classifiation stage
        #Write back to the original tokens
        for j in range(ngrams):
            input_tokens[i+j] = accum[j]

    #remove the paddings if necessary
    if extend:
        input_tokens = input_tokens[ (ngrams - 1) : (len(input_tokens) - ngrams + 1)]

def decide_initial(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`

    Reclassify potential initials.
    """
    import re
    global CONTEXT_SIZE, orthography_data, types
    center = CONTEXT_SIZE

    token = accum[center+1]

    #Ignore first empty line
    if (token == "") or (token == "\n") :
        token = accum[center+2]

    #Ignore second empty line
    if (token == "") or (token == "\n") :
        token = accum[center+3]

    #Ignore third empty line
    if (token == "") or (token == "\n") :
        token = accum[center+4]

    #If the potential initial has not been classified as an abbreviation..
    if accum[center].endswith("<S>"):
        #If the potential initial forms a collocation with the token following the period, e.g Johann S. Bach
        if (decide_collocational(accum) == True) :
            #And the following token is not a frequent sentence starter, reclassify it as abbreviation
            if (decide_sentence_starter(accum) == False) :
                accum[center] = re.sub(r'\<S\>$', '<A>', accum[center])

        #If the orthographic context indicates that there is no sentence boundary after the potential initial
        elif (decide_orthographic(accum) == False):
            #Reclassify potential initial as an abbreviation
            accum[center] = re.sub(r'\<S\>$', '<A>', accum[center])

        #If the orthographic heuristic returns undecided, i.e. not enough evidence 
        elif (decide_orthographic(accum) == "Undecided"):
            #And the following token starts with uppercase
            if re.search(r'^[A-Z]', token):
                normtoken = normalize(token, False)
                #And the token never occurs with a lowercase first letter in the corpus, 
                #reclassify the potential initial as an abbreviation
                if normtoken in orthography_data:
                    if (orthography_data[normtoken][0] == types[normtoken]):
                        accum[center] = re.sub(r'\<S\>$', '<A>', accum[center])
    
    return accum

def decide_abbreviation(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`

    Reclassification of ordinary abbreviations
    """
    global CONTEXT_SIZE
    center = CONTEXT_SIZE

    #If the orthographic heuristic indicates that there is a following sentence boundary
    if (decide_orthographic(accum) == True):
        #then add a sentence boundary tag on top of the abbreviation tag
        accum[center] += "<S>"

    #If the following token is a capitalized frequent sentence starter
    elif (decide_sentence_starter(accum) == True):
        #then add a sentence boundary tag on top of the abbreviation tag
        accum[center] += "<S>"

    return accum
    
def decide_ellipsis(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`

    Reclassification of ellipses (...)
    """
    global CONTEXT_SIZE
    center = CONTEXT_SIZE

    #If the orthographic heuristic indicates that there is a following sentence boundary
    if (decide_orthographic(accum) == True):
        #then add a sentence boundary tag on top of the ellipsis tag
        accum[center] += "<S>"
    #If the following token is a capitalized frequent sentence starter
    elif (decide_sentence_starter(accum) == True):
        #then add a sentence boundary tag on top of the ellipsis tag
        accum[center] += "<S>"

    return accum

def decide_sentence_period(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`
    
    Checking whether the token preceding the period marked as sentence boundary marker in the 
    first-stage classification is one of rare abbreviation
    or
    The preceding and the following tokens form a collocation which is evidence against a sentence
    boundary marker in the middle.
    """
    import re
    global CONTEXT_SIZE, rare_abbreviations
    center = CONTEXT_SIZE
    token = accum[center]

    if token.endswith("<S>"):
        buf = normalize(token[:-4], False)
        #Reclassify rare abbreviations
        if buf in rare_abbreviations:
            accum[center] = re.sub(r'\<S\>', '<A>', accum[center])
            #Check again whether token is also a sentence boundary marker
            accum =    decide_abbreviation(accum)
        #There is collocation between following and preceding tokens
        elif (decide_collocational(accum) == True):
            #Following token is not a frequent sentence starter
            if (decide_sentence_starter(accum) == False):
                #Reclassify the sentence boundary marker as abbreviation and assume no
                #following sentence boundary marker because of the collocation
                accum[center] = re.sub(r'\<S\>$', '<A>', accum[center])
    
    return accum

def decide_collocational(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`

    Decide whether there is a collocational evidence against an intervening sentence boundary
    """
    global CONTEXT_SIZE, collocations
    center = CONTEXT_SIZE

    token1 = normalize(accum[center], True)
    token2 = accum[center+1]
    
    #Ignores first new line
    if (token2 == "") or (token2 == "\n"):
        token2 = accum[center+2]

    #Ignores second new line
    if (token2 == "") or (token2 == "\n") :
        token2 = accum[center+3]

    #Ignores third new line
    if (token2 == "") or (token2 == "\n") :
        token2 = accum[center+4]

    token2 = normalize(token2, False)

    if token1 in collocations:
        #There is collocational evidence between these 2 tokens
        if token2 in collocations[token1]:
            return True
        #No collocational evidence between these 2 tokens
        else:
            return False
    
    #No collocational evidence between these 2 tokens
    else:
        return False

def decide_sentence_starter(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`

    Decide whether a token is a frequent sentence starter 
    """
    global CONTEXT_SIZE, sentence_starters
    center = CONTEXT_SIZE
    token = accum[center+1]

    #Ignore first empty line
    if (token == "") or (token == "\n") :
        token = accum[center+2]

    #Ignore second empty line
    if (token == "") or (token == "\n") :
        token = accum[center+3]

    #Ignore third empty line
    if (token == "") or (token == "\n") :
        token = accum[center+4]

    buf = normalize(token, False)

    if buf in sentence_starters:
        #If `buf` is frequent sentence starters and starts with uppercase letter
        #return True
        if re.search(r'^[A-Z]', token):
            return True
        #No evidence of frequent sentence starters
        else:
            return False
    #No evidence of frequent sentence starters
    else:
        return False

def decide_orthographic(accum):
    """
    accum is the n-grams sized windows of list of tokens to be analysed.
    N-grams size are given in function `decide`

    Look for orthographic evidence. Details of the algorithm can be found in 
    page 12, figure 3 of original paper
    """
    global CONTEXT_SIZE, orthography_data
    center = CONTEXT_SIZE
    token = accum[center+1]
    
    #Ignore first new line
    if (token == "") or (token == "\n") :
        token = accum[center+2]

    #Ignore second new line
    if (token == "") or (token == "\n") :
        token = accum[center+3]

    #Ignore third new line
    if (token == "") or (token == "\n") :
        token = accum[center+4]

    #If the token is punctuation mark, return false
    if re.search(r'^[;:,\.!?]$', token):
        return False
    #Refer to the algorithm described in the paper
    if re.search(r'^[A-Z]', token):
        buf = normalize(token, False)
        if buf in orthography_data:
            if orthography_data[buf][1] > 0:
                if orthography_data[buf][4] > 0:
                    return "Undecided"
                else:
                    return True
            else:
                return "Undecided"
        
    elif re.search(r'^[a-z]', token):
        buf = normalize(token, False)
        if buf in orthography_data:
            if (orthography_data[buf][3] > 0) and (orthography_data[buf][2] == 0):
                return "Undecided"
            else:
                return False
    
    else:
        return "Undecided"

def print_file(output, delimiter):
    """
    Take 2 arguments:
    output: The name of the output file
    delimiter: The string used to seperate between 2 tokens
    
    Output the result
    """
    global input_tokens
    for i in range(len(input_tokens) - 1):
        token = input_tokens[i]
        nexttoken = input_tokens[i+1]
        output.write(token)
        if (token != "\n") and (nexttoken != "\n"):
            output.write(delimiter)
    
    output.write("\n")

    output.close()

"""
The main function that calls all the required functions to perform the tasks.

The system can be run via:
python punkt.py input_file output_file

Output file will contain some tags:
<A> corresponds to a period being marked as abbreviations
<E> corresponds to a period being marked as ellipsis
<S> corresponds to a period being marked as sentence boundary
<A><S> corresponds to a period being marked as both abbreviations and sentence
boundary
<E><S> corresponds to a period being marked as both ellipsis and sentence
boundary
"""

if __name__ == '__main__':
    try:
        input = open(sys.argv[1], 'r');
        output = open(sys.argv[2], 'w');
    except IOError:
        print "File not found"
        sys.exit(1)
    except IndexError:
        print "python", sys.argv[0], "inputfile outputfile"
        sys.exit(1)

    input_tokens = list(preprocess(input))                # Tokenize the input lines

    num_of_tokens = count_tokens(input_tokens)
    types = count_types(input_tokens)
    num_of_types = len(types)
    num_of_periods = count_periods(input_tokens)
    types["##number##"] = count_numbers(input_tokens)

    get_abbreviation_data()                               # Determine which tokens are abbreviations
    annotate()                                            # The end of type-based(first stage) classification stage
    get_orthography_data()                                # Collect the orthography data of the corpus
    count_orthography_context(2, True)                    # Orthography heuristic
    get_rare_abbreviations()                              # Mikheev's algorithm as a backoff to get rare abbreviations
    clear_count()                                         # Normalize the count of each token
    get_collocation_data()                                # Extract collocation data from the corpus
    count_sentence_starters(CONTEXT_SIZE * 2 + 1, False)  # Frequent Sentence starter heuristic
    decide(CONTEXT_SIZE * 2 + 1, True)                    # Reclassify tokens if necessary, end of token-based stage
    print_file(output, " ")                               # Output all tokens to output file
