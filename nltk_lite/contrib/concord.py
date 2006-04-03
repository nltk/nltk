# Natural Language Toolkit: Concordance System
#
# Copyright (C) 2005 University of Melbourne
# Author: Peter Spiller
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.corpora import brown
from math import *
import re
from nltk_lite.probability import *

class SentencesIndex(object):
    """Class implementing an index of a collection of sentences.

    Given a list of sentences, where each sentence is a list of words,
    this class generates an index of the list. Each word should be a (word, POS
    tag) pair. The index is stored as a dictionary, with the hashable items as
    keys and a list of (sentence number, word number) tuples as values. This
    class also generates a list of sentence lengths. 
    """
    
    def __init__(self, sentences):
        """ Constructor. Takes the list of sentences to index.

        @type sentences:    list
        @param sentences:   List of sentences to index. Sentences should be
                            lists of (string, string) pairs.
        """

        sentenceCount = 0
        self.index = {}
        self.lengths = []

        # for each sentence:
        for sentence in sentences:
            # add the sentences length to the list of sentence lengths
            self.lengths.append(len(sentence))
            wordCount = 0
            for word in sentence:
                self.index[word] = self.index.get(word, []) + [(sentenceCount, wordCount)]
                wordCount += 1
            sentenceCount += 1

    def getIndex(self):
        """ Returns the index dictionary.

        @rtype:     dictionary
        @returns:   The dictionary containing the index.
        """
        return self.index

    def getSentenceLengths(self):
        """ Returns the list of sentence lengths.

        Element 0 is the length of the first sentence, element 1 the second,
        etc.

        @rtype:     list
        @returns:   List of lengths of sentences.
        """
        return self.lengths

class IndexConcordance(object):
    """ Class that generates concordances from a list of sentences.

    Uses an index for efficiency. If a SentencesIndex object is provided,
    it will be used, otherwise one will be constructed from the list of
    sentences. When generating a concordance, the supplied regular expression
    is used to filter the list of words in the index. Any that match are looked
    up in the index, and their lists of (sentence number, word number) pairs are
    used to extract the correct amount of context from the sentences.

    Although this class also allows regular expressions to be specified for the
    left and right context, they are not used on the index. If only left/right
    regexps are provided, the class will essentially generate a concordance for
    every word in the corpus, then filter it with the regexps. This will not be
    very efficient and requires very large amounts of memory.

    @cvar SORT_WORD:    Constant for sorting by target word.
    @cvar SORT_POS:     Constant for sorting by target word's POS tag.
    @cvar SORT_NUM:     Constant for sorting by sentence number.
    @cvar SORT_RIGHT_CONTEXT:    Constant for sorting by the first word of the
    right context.
    """

    # constants for different types of sort
    
    SORT_WORD = 0
    SORT_POS = 1
    SORT_NUM = 2
    SORT_RIGHT_CONTEXT = 3
    
    def __init__(self, sentences, index=None):
        """ Constructor.

        Arguments:
        @type sentences:    list
        @param sentences:   List of sentences to create a concordance for.
                            Sentences should be lists of (string, string) pairs.
        @type index:        SentencesIndex
        @param index:     SentencesIndex object to use as an index. If this is
                            not provided, one will be generated.
        """
        
        self.sentences = sentences
        self.index = index
        # generate an index if one wasn't provided
        if self.index == None:
            self.index = SentencesIndex(self.sentences)

    def formatted(self, leftRegexp=None, middleRegexp=".*", rightRegexp=None,
            leftContextLength=3, rightContextLength=3, contextInSentences=False,
            contextChars=50, maxKeyLength=0, showWord=True,
            sort=0, showPOS=True, flipWordAndPOS=False, verbose=False):
        """Generates and displays keyword-in-context formatted concordance data.

        This is a convenience method that combines raw() and display()'s
        options. Unless you need raw output, this is probably the most useful
        method.
        
        @type leftRegexp:       string
        @param leftRegexp:    Regular expression applied to the left context
                                to filter output. Defaults to None.
        @type middleRegexp:     string
        @param middleRegexp:  Regular expression applied to target word to
                                filter output. Defaults to ".*" (ie everything).
        @type rightRegexp:      string
        @param rightRegexp:   Regular expression applied to the right context
                                to filter output. Defaults to None.
        @type leftContextLength:        number
        @param leftContextLength:     Length of left context. Defaults to 3.
        @type rightContextLength:       number
        @param rightContextLength:    Length of right context. Defaults to 3.
        @type contextInSentences:       number
        @param contextInSentences:    Determines whether the context lengths
        arguments are in words or sentences. If false, the context lengths
        are in words - a rightContextLength argument of 2 results in two
        words of right context. If true, a rightContextLength argument of 2
        results in a right context consisting of the portion of the target
        word's sentence to the right of the target, plus the two sentences
        to the right of that sentence. Defaults to False.
        @type contextChars      number
        @param contextChars:  Amount of context to show. If set to less than
                                0, does not limit amount of context shown
                                (may look ugly). Defaults to 55.
        @type maxKeyLength:     number
        @param maxKeyLength:  Max number of characters to show for the
                                target word. If 0 or less, this value is
                                calculated so as to fully show all target
                                words. Defaults to 0.
        @type showWord:         boolean
        @param showWord:      Whether to show words. Defaults to True.
        @type sort:             integer
        @param sort: Should be set to one the provided SORT constants. If
        SORT_WORD, the output is sorted on the target word. If SORT_POS, the
        output is sorted on the target word's POS tag. If SORT_NUM, the
        output is sorted by sentence number. If SORT_RIGHT_CONTEXT, the
        output is sorted on the first word of the right context. Defaults to
        SORT_WORD.
        @type showPOS:          boolean
        @param showPOS:       Whether to show POS tags. Defaults to True.
        @type flipWordAndPOS:   boolean
        @param flipWordAndPOS: If true, displays POS tags first instead of
            words (ie prints 'cc/and' instead of 'and/cc'). Defaults to False.
        @type verbose:          boolean
        @param verbose:       Displays some extra status information. Defaults
                                to False.
        """
            
        self.format(self.raw(leftRegexp, middleRegexp, rightRegexp, leftContextLength,
                rightContextLength, contextInSentences, sort, verbose), contextChars,
                maxKeyLength, showWord, showPOS, flipWordAndPOS, verbose)

    def raw(self, leftRegexp=None, middleRegexp=".*", rightRegexp=None,
            leftContextLength=3, rightContextLength=3, contextInSentences=False,
            sort=0, verbose=False):
        """ Generates and returns raw concordance data.

        Regular expressions supplied are evaluated over the appropriate part of
        each line of the concordance. For the purposes of evaluating the regexps,
        the lists of (word, POS tag) tuples are flattened into a space-separated
        list of word/POS tokens (ie the word followed by '/' followed by the POS
        tag). A regexp like '^must/.*' matches the word 'must' with any POS tag,
        while one like '.*/nn$' matches any word with a POS tag of 'nn'. All
        regexps are evaluated over lowercase versions of the text.

        @type leftRegexp:       string
        @param leftRegexp:    Regular expression applied to the left context
                                to filter output. Defaults to None.
        @type middleRegexp:     string
        @param middleRegexp:  Regular expression applied to target word to
                                filter output. Defaults to ".*" (ie everything).
        @type rightRegexp:      string
        @param rightRegexp:   Regular expression applied to the right context
                                to filter output. Defaults to None.
        @type leftContextLength:        number
        @param leftContextLength:     Length of left context. Defaults to 3.
        @type rightContextLength:       number
        @param rightContextLength:    Length of right context. Defaults to 3.
        @type contextInSentences:       number
        @param contextInSentences:    Determines whether the context lengths
            arguments are in words or sentences. If false, the context lengths
            are in words - a rightContextLength argument of 2 results in two
            words of right context. If true, a rightContextLength argument of 2
            results in a right context consisting of the portion of the target
            word's sentence to the right of the target, plus the two sentences
            to the right of that sentence. Defaults to False.
        @type sort:             integer
        @param sort: Should be set to one the provided SORT constants. If
            SORT_WORD, the output is sorted on the target word. If SORT_POS, the
            output is sorted on the target word's POS tag. If SORT_NUM, the
            output is sorted by sentence number. If SORT_RIGHT_CONTEXT, the
            output is sorted on the first word of the right context. Defaults to
            SORT_WORD.
        @type verbose:          boolean
        @param verbose:       Displays some extra status information. Defaults
                                to False.
        @rtype:     list
        @return:    Raw concordance ouput. Returned as a list of
                    ([left context], target word, [right context], target word
                    sentence number) tuples.
        """
        # compile the middle regexp.
        reg = re.compile(middleRegexp)

        if verbose:
            print "Matching the following target words:"
        wordLocs = []
        # get list of (sentence, word) pairs to get context for
        for item in self.index.getIndex().iteritems():
            if reg.match("/".join([item[0][0].lower(), item[0][1]])):
                if verbose:
                    print "/".join(item[0])
                wordLocs.append(item[1])
                
        print ""

        items = []
        # if context lengths are specified in words:
        if contextInSentences == False:
            # for each list of (sentence, word offset in sentence) pairs:
            for wordList in wordLocs:
                # for each (sentence, word offset in sentence) pair:
                for sentenceNum, offset in wordList:
                    # set pointers to the left- and rightmost sentences to be
                    # looked at to the sentence the target word is in
                    leftCorpusIndex = sentenceNum
                    rightCorpusIndex = sentenceNum
                    # number of words to include in the left context is
                    # initially everything in the sentence up to the target
                    leftLength = offset
                    # number of words to include in the left context is
                    # initially everything in the sentence after the target
                    rightLength = self.index.getSentenceLengths()[sentenceNum] - offset - 1

                    # while the length of the left context is less than what we
                    # need, keep decreasing the left corpus index (ie adding
                    # sentences to the left context).
                    while leftLength < leftContextLength:
                        leftCorpusIndex -= 1
                        # if the new corpus index would fall off the end of the
                        # list, stop at 0
                        if(leftCorpusIndex < 0):
                            leftCorpusIndex = 0
                            break
                        # adjust length and offset
                        leftLength += self.index.getSentenceLengths()[leftCorpusIndex]
                        offset += self.index.getSentenceLengths()[leftCorpusIndex]

                    # while the length of the right context is less than what we
                    # need, keep increasing the right corpus index (ie adding
                    # sentences to the right context).
                    while rightLength < rightContextLength:
                        rightCorpusIndex += 1
                        try:
                            rightLength += self.index.getSentenceLengths()[rightCorpusIndex]
                        # if the new corpus index falls off the end of the list,
                        # stop at the end
                        except IndexError:
                            rightCorpusIndex -= 1
                            break

                    # grab all sentences from the left to right corpus indices,
                    # then flatten them into a single list of words
                    sents = self.sentences[leftCorpusIndex:rightCorpusIndex+1]
                    words = []
                    for sentence in sents:
                        for word in sentence:
                            words.append(word)

                    # select the appropriate sections of context from the list
                    # of words
                    left = words[offset-leftContextLength:offset]
                    target = words[offset]
                    right = words[offset+1:offset+1+rightContextLength]
                    items.append((left, target, right, sentenceNum))
        # if context lengths are specified in sentences:
        else:
            # for each list of (sentence, word offset in sentence) pairs:
            for wordList in wordLocs:
                # for each list of (sentence, word offset in sentence) pairs:
                for sentenceNum, offset in wordList:
                    # set pointers to the left- and rightmost sentences to be
                    # looked at to the sentence the target word is in
                    leftCorpusIndex = sentenceNum
                    rightCorpusIndex = sentenceNum
                    # number of words to include in the left context is
                    # initially everything in the sentence up to the target
                    leftLength = offset
                    # number of words to include in the left context is
                    # initially everything in the sentence after the target
                    rightLength = self.index.getSentenceLengths()[sentenceNum] - offset - 1
                    # keep track of the number of sentences included in the
                    # left/right context
                    leftSents = 0;
                    rightSents = 0;

                    # while we don't have enough sentences in the left context,
                    # keep decreasing the left corpus index
                    while leftSents < leftContextLength:
                        leftCorpusIndex -= 1
                        # if the new corpus index would fall off the end of the
                        # list, stop at 0
                        if(leftCorpusIndex < 0):
                            leftCorpusIndex = 0
                            break
                        leftLength += self.index.getSentenceLengths()[leftCorpusIndex]
                        offset += self.index.getSentenceLengths()[leftCorpusIndex]
                        leftSents += 1

                    # while we don't have enough sentences in the right context,
                    # keep increasing the right corpus index
                    while rightSents < rightContextLength:
                        rightCorpusIndex += 1
                        try:
                            rightLength += self.index.getSentenceLengths()[rightCorpusIndex]
                            rightSents += 1
                        # if the new corpus index falls off the end of the list,
                        # stop at the end
                        except IndexError:
                            rightCorpusIndex -= 1
                            break

                    # grab all sentences from the left to right corpus indices,
                    # then flatten them into a single list of words
                    sents = self.sentences[leftCorpusIndex:rightCorpusIndex+1]
                    words = []
                    for sentence in sents:
                        for word in sentence:
                            words.append(word)

                    # select the appropriate sections of context from the list
                    # of words
                    left = words[0:offset]
                    target = words[offset]
                    right = words[offset+1:]
                    items.append((left, target, right, sentenceNum))

        if verbose:
            print "Found %d matches for target word..." % len(items)

        # sort the concordance
        if sort == self.SORT_WORD:
            if verbose:
                print "Sorting by target word..."
            items.sort(key=lambda i:i[1][0].lower())
        elif sort == self.SORT_POS:
            if verbose:
                print "Sorting by target word POS tag..."
            items.sort(key=lambda i:i[1][1].lower())
        elif sort == self.SORT_NUM:
            if verbose:
                print "Sorting by sentence number..."
            items.sort(key=lambda i:i[3])
        elif sort == self.SORT_RIGHT_CONTEXT:
            if verbose:
                print "Sorting by first word of right context..."
            items.sort(key=lambda i:i[2][0][0])

        # if any regular expressions have been given for the context, filter
        # the concordance using them
        filtered = []
        filterBool = False
        if leftRegexp != None or rightRegexp != None:
            filterBool = True
        if filterBool:    

            leftRe=None
            rightRe=None
            if leftRegexp != None:
                if verbose:
                    print "Filtering on left context..."
                leftRe = re.compile(leftRegexp)
            if rightRegexp != None:
                if verbose:
                    print "Filtering on right context..."
                rightRe = re.compile(rightRegexp)
            
            for item in items:
                if self._matches(item, leftRe, rightRe):
                    filtered.append(item)
    
        if filterBool:
            source = filtered
        else:
            source = items

        return source

    def format(self, source, contextChars=55, maxKeyLength=0, showWord=True,
            showPOS=True, flipWordAndPOS=False, verbose=False):
        """Formats raw concordance output produced by raw().

        Displays a concordance in keyword-in-context style format.

        @type source:   list
        @param source:  Raw concordance output to format. Expects a list of
        ([left context], target word, [right context], target
        word sentence number) tuples.
        @type contextChars      number
        @param contextChars:  Amount of context to show. If set to less than
        0, does not limit amount of context shown (may look ugly). Defaults to 55.
        @type maxKeyLength:     number
        @param maxKeyLength:  Max number of characters to show for the
        target word. If 0 or less, this value is
        calculated so as to fully show all target
        words. Defaults to 0.
        @type showWord:         boolean
        @param showWord:      Whether to show words. Defaults to True.
        @type showPOS:          boolean
        @param showPOS:       Whether to show POS tags. Defaults to True.
        @type flipWordAndPOS:   boolean
        @param flipWordAndPOS: If true, displays POS tags first instead of
        words (ie prints 'cc/and' instead of 'and/cc'). Defaults to False.
        @type verbose:          boolean
        @param verbose:       Displays some extra status information. Defaults
        to False.
        """

        # flatten lists of tokens into strings
        lines = []
        maxMiddleLength = -1

        # generate intermediate list of string tuples        
        for line in source:
            # flatten left context tokens into a single string, joining words
            # and their POS tag with a '/' (if both are shown).
            left = ""
            for item in line[0]:
                if item[0] == "" and item[1] == "":
                    left = ""
                elif showWord and (not showPOS):
                    left += item[0] + " "
                elif (not showWord) and showPOS:
                    left += item[1] + " "
                elif flipWordAndPOS:
                    left += item[1] + "/" + item[0] + " "
                else:      
                    left += "/".join(item) + " "

            # flatten target word into a single string, joining the word and
            # its POS tag with a '/' (if both are shown).
            if showWord and (not showPOS):
                middle = line[1][0]
            elif (not showWord) and showPOS:
                middle = line[1][1]
            elif flipWordAndPOS:
                middle = line[1][1] + "/" + line[1][0] + " "
            else:      
                middle = "/".join(line[1])
            
            if len(middle) > maxMiddleLength:
                maxMiddleLength = len(middle)

            # flatten right context tokens into a single string, joining words
            # and their POS tag with a '/' (if both are shown).        
            right = ""
            for item in line[2]:
                if item[0] == "" and item[1] == "":
                    right = ""
                elif showWord and (not showPOS):
                    right += item[0] + " "
                elif (not showWord) and showPOS:
                    right += item[1] + " "
                elif flipWordAndPOS:
                    right += item[1] + "/" + item[0] + " "
                else:      
                    right += "/".join(item) + " "

            num = line[3]

            lines.append((middle, left, right, num))

        # crop and justify strings to generate KWIC-format output
        count = 0
        for middle, left, right, num in lines:
            # calculate amount of left padding needed
            leftPaddingLength = contextChars - len(left)
            if leftPaddingLength < 0:
                leftPaddingLength = 0
            if len(left) > contextChars and contextChars > -1:
                left = left[-contextChars:]
            left = " "*leftPaddingLength + left
            if contextChars > -1:
                right = right[0:contextChars]
            
            # add sentence numbers
            left = str(num) + ": " + left[len(str(num))+2 : ]

            # calculate amount of middle padding needed
            if maxKeyLength > 0:
                maxMiddleLength = maxKeyLength
            lPad = int(ceil(max(maxMiddleLength - len(middle), 0) / 2.0))
            rPad = int(floor(max(maxMiddleLength - len(middle), 0) / 2.0))
            middle = " "*lPad + middle + " "*rPad
            
            print left + "| " + middle + " | " + right + " "
            count += 1
        
        if verbose:    
            print "\n" + repr(count) + " lines"

    def _matches(self, item, leftRe, rightRe):
        """ Private method that runs the given regexps over a raw concordance
        item and returns whether they match it.
        """
        left = item[0]
        right = item[2]

        # flatten left and right contexts
        leftString = ""
        for token in left:
            leftString += "/".join(token) + " "
        rightString = ""
        for token in right:
            rightString += "/".join(token) + " "    

        # see if regexps match    
        ok = True
        if leftRe != None and leftRe.match(leftString) == None:
            ok = False
        if rightRe != None and rightRe.match(rightString) == None:
            ok = False
                       
        if ok:                
            return True
        else:
            return False

class Aggregator(object):
    """ Class for aggregating and summarising corpus concordance data.

    This class allows one or more sets of concordance data to be summarised and
    displayed. This is useful for corpus linguistic tasks like counting the
    number of occurences of a particular word and its different POS tags in a
    given corpus, or comparing these frequencies across different corpora. It
    creates a FreqDist for each set of concordance data, counting how often each
    unique entry appears in it.

    An example of how to use this class to show the frequency of the five most
    common digrams of the form "must/md X/Y" in the Brown Corpus sections a
    and g::
    
        concA = IndexConcordance(list(brown.tagged('a')))
        rawA = concA.raw(middleRegexp="^must/md$", leftContextLength=0, rightContextLength=1)
        concG = IndexConcordance(list(brown.tagged('g')))
        rawG = concG.raw(middleRegexp="^must/md$", leftContextLength=0, rightContextLength=1)
        agg = Aggregator()
        agg.add(rawA, "Brown Corpus A")
        agg.add(rawG, "Brown Corpus G")
        agg.formatted(showFirstX=5)

        Output:

        Brown Corpus A
        ------------------------------
         must/md be/be          17
         must/md have/hv        5
         must/md not/*          3
         must/md play/vb        2
         must/md ''/''          1

        Brown Corpus G
        ------------------------------
         must/md be/be          38
         must/md have/hv        21
         must/md ,/,            6
         must/md not/*          5
         must/md always/rb      3
    """

    # text for 'other' row in output tables
    _OTHER_TEXT = "<OTHER>"
    # text for 'total' row in output tables
    _TOTAL_TEXT = "<TOTAL>"
    
    def __init__(self, inputList=None):
        """ Constructor.

        @type inputList:    list
        @param inputList: List of (raw concordance data, name) tuples to be
                            entered into the aggregator. Defaults to None.
        """
        self._outputSets = []
        if inputList != None:
            for (item, n) in inputList:
                self.add(item, name=n)

    def add(self, raw, name):
        """ Adds the given set of raw concordance output to the aggregator.

        @type raw:  list
        @param raw: Raw concordance data (produced by IndexConcordance.raw()).
                    Expects a list of ([left context], target word,
                    [right context], target word sentence number) tuples.
        @type name:     string
        @param name:    Name to associate with the set of data.
        """
        self._outputSets.append((raw, name));

    def remove(self, name):
        """ Removes all sets of raw concordance output with the given name.

        @type name:     string
        @param name:    Name of data set to remove.
        """
        for item in self._outputSets:
            if item[1] == name:
                self._outputSets.remove(item)

    def formatted(self, useWord=True, usePOS=True, normalise=False,
                  threshold=-1, showFirstX=-1, decimalPlaces=4,
                  countOther=False, showTotal=False):
        """ Displays formatted concordance summary information.

        This is a convenience method that combines raw() and display()'s
        options. Unless you need raw output, this is probably the most useful
        method.

        @type useWord:      boolean
        @param useWord:   Include the words in the count. Defaults to True.
        @type usePOS:       boolean
        @param usePOS:    Include the POS tags in the count. Defaults to
                            False.
        @type normalise:    boolean
        @param normalise: If true, normalises the frequencies for each set
            of concordance output by dividing each key's frequency by the total
            number of samples in that concordances's FreqDist. Allows easier
            comparison of results between data sets.  Care must be taken when
            combining this option with the threshold option, as any threshold
            of 1 or more will prevent any output being displayed. Defaults to
            False.
        @type threshold:    number
        @param threshold: Frequency display threshold. Results below this
            frequency will not be displayed. If less than 0, everything will be
            displayed. Defaults to -1.
        @type showFirstX:       number
        @param showFirstX:    Only show this many results, starting with the
            most frequent. If less than 0, everything will be displayed.
            Defaults to -1.
        @type decimalPlaces:    integer
        @param decimalPlaces: Number of decimal places of accuracy to
            display. Used when displaying non-integers with the normalise
            option. Defaults to 4.
        @type countOther:       boolean
        @param countOther:    If true, any samples not shown (due to their
            frequency being below the given thershold or because they were
            after the number of results specified by the showFirstX argument)
            will be combined into one sample. This sample's frequency is the
            sum of all unshown sample's frequencies. Defaults to False.
        @type showTotal:    boolean
        @param showTotal: If true, prints the sum of all frequencies (of
            the entire FreqDist, not just of the samples displayed.) Defaults
            to False.
        """
        
        output, maxKeyLength = self.raw(useWord, usePOS)
        self.format(output, maxKeyLength, threshold, showFirstX,
                decimalPlaces, normalise, countOther, showTotal)

    def raw(self, useWord=True, usePOS=True):
        """ Generates raw summary information.

        Creates a FreqDist for each set of concordance output and uses it to
        count the frequency of each line in it. The concordance output is
        flattened from lists of tokens to strings, as lists cannot be hashed.
        The list of FreqDists is returned, as well as the length of the longest
        string (used for formatted display).

        @type useWord:      boolean
        @param useWord:   Include the words in the count. Defaults to True.
        @type usePOS:       boolean
        @param usePOS:    Include the POS tags in the count. Defaults to
                            False.
        @rtype:     list, number
        @returns:   A list of (FreqDist, name) pairs, and the length of the
                    longest key in all the FreqDists.
        """

        output = []
        maxKeyLength = 0

        # for each set of raw concordance data:
        for (rawConcOutput, name) in self._outputSets:
            # initialise a FreqDist
            dist = FreqDist()
            # for each item in the raw concordance output:
            for (left, middle, right, num) in rawConcOutput:
                # flatten the lists of tokens so they can be hashed in
                # the FreqDist
                leftList = []
                for word in left:
                    if usePOS == False and useWord == True:
                        leftList.append(word[0].lower())
                    elif usePOS == True and useWord == False:
                        leftList.append(word[1].lower())
                    else:
                        leftList.append(word[0].lower() + "/" + word[1].lower())
                try:
                    if usePOS == False and useWord == True:
                        midString = middle[0].lower()
                    elif usePOS == True and useWord == False:
                        midString = middle[1].lower()
                    else:
                        midString = middle[0].lower() + "/" + middle[1].lower()
                except IndexError:
                    midString = ""

                rightList = []
                for word in right:
                    if usePOS == False and useWord == True:
                        rightList.append(word[0].lower())
                    elif usePOS == True and useWord == False:
                        rightList.append(word[1].lower())
                    else:
                        rightList.append(word[0].lower() + "/" + word[1].lower())

                # join the tokens together to form a key string
                key = " ".join(leftList) + " " + midString + " " + " ".join(rightList)
                # keep track of the longest key length
                if len(key) > maxKeyLength:
                    maxKeyLength = len(key)
                # increment the FreqDist's count for this key
                dist.inc(key)

            # add this FreqDist and name to the output
            output.append((dist, name))

        # return the output and maximum key length
        return output, maxKeyLength

    def format(self, output, maxKeyLength=20, threshold=-1, showFirstX=-1,
                decimalPlaces=4, normalise=False, countOther=False,
                showTotal=False):
        """ Displays concordance summary information.

        Formats and displays information produced by raw().

        @type output:   list
        @param output:  List of (FreqDist, name) pairs (as produced by raw()).
        @type maxKeyLength:     number
        @param maxKeyLength:  Length of longest key. Defaults to 20.
        @type normalise:    boolean
        @param normalise: If true, normalises the frequencies for each set
            of concordance output by dividing each key's frequency by the total
            number of samples in that concordances's FreqDist. Allows easier
            comparison of results between data sets.  Care must be taken when
            combining this option with the threshold option, as any threshold
            of 1 or more will prevent any output being displayed. Defaults to
            False.
        @type threshold:    number
        @param threshold: Frequency display threshold. Results below this
            frequency will not be displayed. If less than 0, everything will be
            displayed. Defaults to -1.
        @type showFirstX:       number
        @param showFirstX:    Only show this many results, starting with the
            most frequent. If less than 0, everything will be displayed.
            Defaults to -1.
        @type decimalPlaces:    integer
        @param decimalPlaces: Number of decimal places of accuracy to
            display. Used when displaying non-integers with the normalise
            option. Defaults to 4.
        @type countOther:       boolean
        @param countOther:    If true, any samples not shown (due to their
            frequency being below the given thershold or because they were
            after the number of results specified by the showFirstX argument)
            will be combined into one sample. This sample's frequency is the
            sum of all unshown sample's frequencies. Defaults to False.
        @type showTotal:    boolean
        @param showTotal: If true, prints the sum of all frequencies (of
            the entire FreqDist, not just of the samples displayed.) Defaults
            to False.
        """

        # for each FreqDist:
        for (dist, name) in output:
            x = 0
            other = 0
            total = 0
            print name
            print "-"*(maxKeyLength + 7)
            # for each key:
            for key in dist.sorted_samples():
                # keep track of how many samples shown, if using the showFirstX
                # option
                #if showFirstX > 0 and x >= showFirstX:
                #   break

                # get and format the sample's frequency
                if normalise:
                    count = 1.0 * dist.count(key) / dist.N()
                    countString = str(count)[0:decimalPlaces + 2]
                else:
                    count = dist.count(key)
                    countString = str(count)

                total += count

                # if the count is less than the threshold value, or we've
                # already shown X samples, add this sample's frequency to the
                # 'other' bin
                if count < threshold or (showFirstX > 0 and x >= showFirstX):
                    other += count
                else:
                    print key + " "*(maxKeyLength - len(key) + 1) + countString
                x += 1

            if countOther:
                if normalise:
                    count = 1.0 * other
                    countString = str(count)[0:decimalPlaces + 2]
                else:
                    count = other
                    countString = str(count)
                print self._OTHER_TEXT + " "*(maxKeyLength - len(self._OTHER_TEXT) + 1) + countString
            if showTotal:
                if normalise:
                    count = 1.0 * total
                    countString = str(count)[0:decimalPlaces + 2]
                else:
                    count = total
                    countString = str(count)
                print self._TOTAL_TEXT + " "*(maxKeyLength - len(self._TOTAL_TEXT) + 1) + countString
            print ""
            
def demo():
    """
    Demonstrates how to use IndexConcordance and Aggregator.
    """
    print "Reading Brown Corpus into memory..."
    corpus = list(brown.tagged(('a','j')))
    print "Generating index..."
    ic = IndexConcordance(corpus)
    print "Showing all occurences of 'plasma' in the Brown Corpus..."
    ic.formatted(middleRegexp="^plasma/.*", verbose=True)

    print "Investigating the collocates of 'deal' and derivatives..."
    agg = Aggregator()
    agg.add(ic.raw(middleRegexp="^deal", leftContextLength=1, rightContextLength=0,
    leftRegexp="^(\w|\s|/)*$"), "Brown Corpus 'deal' left collocates")
    agg.add(ic.raw(middleRegexp="^deal", leftContextLength=0, rightContextLength=1,
    rightRegexp="^(\w|\s|/)*$"), "Brown Corpus 'deal' right collocates")
    agg.formatted(showFirstX=5, usePOS=False)

if __name__ == '__main__':
    demo()    
