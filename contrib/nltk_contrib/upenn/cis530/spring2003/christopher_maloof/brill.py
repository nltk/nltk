import nltk.tagger
import nltk.token
from nltk.corpus import treebank

import bisect       # for binary search through a subset of indices
import os           # for finding WSJ files
import pickle       # for storing/loading rule lists
import random       # for shuffling WSJ files
import sys          # for getting command-line arguments

class BrillTagger(nltk.tagger.TaggerI):
    """
    A transformation-based error-driven tagger.  Before a C{BrillTagger} can be
    used, it should be trained on a list of C{TaggedTokens}.  This will produce
    an ordered list of transformations that are used to tag unknown data.  A
    C{BrillTagger} also requires some other tagger to do an initial tagging
    before transformations can be applied.
    """

    def __init__(self, tagger, templates, **property_names):
        """
        @param tagger: The initial tagger
        @type tagger: TaggerI
        @param templates: Templates for generating rules
        @type templates: list of TemplateI
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        self._initialTagger = tagger
        self._templates = templates
        self._property_names = property_names
        self._rules = []

    def _initialTagging (self, myToken):
        if self._rules:
            print "WARNING: tagger previously trained, deleting old rules."
            # Another option would be to keep the old rules at the start of the list.
        self._initialTagger.tag(myToken)

    def fastTrain (self, correctToken, maxRules = 200, minScore=2):
        """
        Like train, but much more efficient.
        """
        # If TESTING is true, extra computation is done to determine whether
        # each "best" rule actually reduces net error by the score it received.
        TESTING = False
        
        # Basic idea: Keep track of the rules that apply at each position.
        # And keep track of the positions to which each rule applies.

        # The set of somewhere-useful rules that apply at each position
        rulesByPosition = []
        for i in range(len(correctToken['SUBTOKENS'])):
            rulesByPosition.append({})

        # Mapping somewhere-useful rules to the positions where they apply.
        # Then maps each position to the score change the rule generates there.
        # (always -1, 0, or 1)
        positionsByRule = {}

        # Map scores to sets of rules known to achieve *at most* that score.
        rulesByScore = {0:{}}
        # Conversely, map somewhere-useful rules to their minimal scores.
        ruleScores = {}

        tagIndices = {}   # Lists of indices, mapped to by their tags

        # Maps rules to the first index in the corpus where it may not be known
        # whether the rule applies.  (Rules can't be chosen for inclusion
        # unless this value = len(corpus).  But most rules are bad, and
        # we won't need to check the whole corpus to know that.)
        # Some indices past this may actually have been checked; it just isn't
        # guaranteed.
        firstUnknownIndex = {}

        # Make entries in the rule-mapping dictionaries.
        # Should be called before _updateRuleApplies.
        def _initRule (rule):
            positionsByRule[rule] = {}
            rulesByScore[0][rule] = None
            ruleScores[rule] = 0
            firstUnknownIndex[rule] = 0

        # Takes a somewhere-useful rule which applies at index i;
        # Updates all rule data to reflect that the rule so applies.
        def _updateRuleApplies (rule, i):

            # If the rule is already known to apply here, ignore.
            # (This only happens if the position's tag hasn't changed.)
            if positionsByRule[rule].has_key(i):
                return

            if rule.getReplacement() == correctToken['SUBTOKENS'][i]['TAG']:
                positionsByRule[rule][i] = 1
            elif rule.getOriginal() == correctToken['SUBTOKENS'][i]['TAG']:
                positionsByRule[rule][i] = -1
            else: # was wrong, remains wrong
                positionsByRule[rule][i] = 0

            # Update rules in the other dictionaries
            del rulesByScore[ruleScores[rule]][rule]
            ruleScores[rule] += positionsByRule[rule][i]
            if not rulesByScore.has_key(ruleScores[rule]):
                rulesByScore[ruleScores[rule]] = {}
            rulesByScore[ruleScores[rule]][rule] = None
            rulesByPosition[i][rule] = None

        # Takes a rule which no longer applies at index i;
        # Updates all rule data to reflect that the rule doesn't apply.
        def _updateRuleNotApplies (rule, i):
            del rulesByScore[ruleScores[rule]][rule]
            ruleScores[rule] -= positionsByRule[rule][i]
            if not rulesByScore.has_key(ruleScores[rule]):
                rulesByScore[ruleScores[rule]] = {}
            rulesByScore[ruleScores[rule]][rule] = None

            del positionsByRule[rule][i]
            del rulesByPosition[i][rule]
            # Optional addition: if the rule now applies nowhere, delete
            # all its dictionary entries.

        myToken = correctToken.exclude('TAG')
        self._initialTagging(myToken)

        # First sort the corpus by tag, and also note where the errors are.
        errorIndices = []  # only used in initialization
        for i in range(len(myToken['SUBTOKENS'])):
            tag = myToken['SUBTOKENS'][i]['TAG']
            if tag != correctToken['SUBTOKENS'][i]['TAG']:
                errorIndices.append(i)
            if not tagIndices.has_key(tag):
                tagIndices[tag] = []
            tagIndices[tag].append(i)

        print "Finding useful rules..."
        # Collect all rules that fix any errors, with their positive scores.
        for i in errorIndices:
            for template in self._templates:
                # Find the templated rules that could fix the error.
                for rule in template.makeApplicableRules(myToken['SUBTOKENS'], i,
                                                    correctToken['SUBTOKENS'][i]['TAG']):
                    if not positionsByRule.has_key(rule):
                        _initRule(rule)
                    _updateRuleApplies(rule, i)

        print "Done initializing %i useful rules." %len(positionsByRule)

        if TESTING:
            after = -1 # bug-check only

        # Each iteration through the loop tries a new maxScore.
        maxScore = max(rulesByScore.keys())
        while len(self._rules) < maxRules and maxScore >= minScore:

            # Find the next best rule.  This is done by repeatedly taking a rule with
            # the highest score and stepping through the corpus to see where it
            # applies.  When it makes an error (decreasing its score) it's bumped
            # down, and we try a new rule with the highest score.
            # When we find a rule which has the highest score AND which has been
            # tested against the entire corpus, we can conclude that it's the next
            # best rule.

            bestRule = None
            bestRules = rulesByScore[maxScore].keys()

            for rule in bestRules:
                # Find the first relevant index at or following the first
                # unknown index.  (Only check indices with the right tag.)
                ti = bisect.bisect_left(tagIndices[rule.getOriginal()],
                                        firstUnknownIndex[rule])
                for nextIndex in tagIndices[rule.getOriginal()][ti:]:
                    if rule.applies(myToken['SUBTOKENS'], nextIndex):
                        _updateRuleApplies(rule, nextIndex)
                        if ruleScores[rule] < maxScore:
                            firstUnknownIndex[rule] = nextIndex+1
                            break  # the _update demoted the rule

                # If we checked all remaining indices and found no more errors:
                if ruleScores[rule] == maxScore:
                    firstUnknownIndex[rule] = len(tokens) # i.e., we checked them all
                    print "%i) %s (score: %i)" %(len(self._rules)+1, rule, maxScore)
                    bestRule = rule
                    break
                
            if bestRule == None: # all rules dropped below maxScore
                del rulesByScore[maxScore]
                maxScore = max(rulesByScore.keys())
                continue  # with next-best rules

            # bug-check only
            if TESTING:
                before = len(_errorPositions(tokens, correctTokens))
                print "There are %i errors before applying this rule." %before
                assert after == -1 or before == after, \
                        "after=%i but before=%i" %(after,before)
                        
            print "Applying best rule at %i locations..." \
                    %len(positionsByRule[bestRule].keys())
            
            # If we reach this point, we've found a new best rule.
            # Apply the rule at the relevant sites.
            # (applyAt is a little inefficient here, since we know the rule applies
            #  and don't actually need to test it again.)
            self._rules.append(bestRule)
            bestRule.applyAt(tokens, positionsByRule[bestRule].keys())

            # Update the tag index accordingly.
            for i in positionsByRule[bestRule].keys(): # where it applied
                # Update positions of tags
                # First, find and delete the index for i from the old tag.
                oldIndex = bisect.bisect_left(tagIndices[bestRule.getOriginal()], i)
                del tagIndices[bestRule.getOriginal()][oldIndex]

                # Then, insert i into the index list of the new tag.
                if not tagIndices.has_key(bestRule.getReplacement()):
                    tagIndices[bestRule.getReplacement()] = []
                newIndex = bisect.bisect_left(tagIndices[bestRule.getReplacement()], i)
                tagIndices[bestRule.getReplacement()].insert(newIndex, i)

            # This part is tricky.
            # We need to know which sites might now require new rules -- that
            # is, which sites are close enough to the changed site so that
            # a template might now generate different rules for it.
            # Only the templates can know this.
            #
            # If a template now generates a different set of rules, we have
            # to update our indices to reflect that.
            print "Updating neighborhoods of changed sites.\n" 

            # First, collect all the indices that might get new rules.
            neighbors = {}
            for i in positionsByRule[bestRule].keys(): # sites changed
                for template in self._templates:
                    neighbors.update(template.getNeighborhood(myToken['SUBTOKENS'], i))

            # Then collect the new set of rules for each such index.
            c = d = e = 0
            for i in neighbors:
                siteRules = {}
                for template in self._templates:
                    # Get a set of the rules that the template now generates
                    siteRules.update(_listToSet(template.makeApplicableRules(
                                        myToken['SUBTOKENS'], i, correctToken['SUBTOKENS'][i]['TAG'])))

                # Update rules no longer generated here by any template
                for obsolete in _setDifference(rulesByPosition[i], siteRules):
                    c += 1
                    _updateRuleNotApplies(obsolete, i)

                # Update rules only now generated by this template
                for newRule in _setDifference(siteRules, rulesByPosition[i]):
                    d += 1
                    if not positionsByRule.has_key(newRule):
                        e += 1
                        _initRule(newRule) # make a new rule w/score=0
                    _updateRuleApplies(newRule, i) # increment score, etc.

            if TESTING:
                after = before - maxScore
            print "%i obsolete rule applications, %i new ones, " %(c,d)+ \
                    "using %i previously-unseen rules." %e        

            maxScore = max(rulesByScore.keys()) # may have gone up

    # requires a list of Token with type TaggedType
    def train (self, correctToken, maxRules = 200, minScore=2):
        """
        Trains the BrillTagger on the corpus C{correctTokens}, producing at
        most C{maxRules} transformations, each of which reduces the net number
        of errors in the corpus by at least C{minScore}.
        
        @param correctTokens: The corpus of tagged C{Tokens}
        @type correctTokens: list of Token
        @param maxRules: The maximum number of transformations to be created
        @type maxRules: int
        @param minScore: The minimum acceptable net error reduction that each
            transformation must produce in the corpus.
        """

        myToken = correctToken.exclude('TAG')
        self._initialTagging(myToken)

        print "Training Brill tagger on %d tokens..." % len(myToken['SUBTOKENS'])

        # loop and create list of rules here
        self._rules = []
        while len(self._rules) < maxRules:
            (rule, score) = self._bestRule(myToken, correctToken)
            print "  Found: \"%s\"" % rule
            # We should eventually run out of useful rules
            if rule != None and score >= minScore:
                self._rules.append(rule)
                print "  Apply:",
                k = rule.applyTo(myToken['SUBTOKENS'])  # not optimized (see tag())
                print "[changed %i tags: %i correct; %i incorrect]" % (
                    len(k), score, len(k)-score)
            else:
                print "[insufficient improvement; stopping]"
                break

    def getRules (self):
        """
        Returns the transformations learned by this tagger, if any.

        @return: The rules being used by this tagger
        @rtype: list of RuleI
        """
        return self._rules

    def saveRules (self, filename):
        """
        Pickles the list of transformations and saves them to a file at C{filename}.

        @param filename: Name of file to save to
        @type filename: string
        """
        if not self._rules:
            raise RuntimeError("This BrillTagger has not been trained.")
        pickle.dump(self._rules, file(filename, 'w'))

    # This replaces training.
    def loadRules (self, filename):
        """
        Causes the tagger to load a list of pickled rules from filename.
        These replace any previous transformations the tagger was using.

        @param filename: Name of file to load from
        @type filename: string
        """
        self._rules = pickle.load(file(filename, 'r'))

    def tag (self, myToken):
        # Inherit documentation from TaggerI
        if not self._rules:
            raise RuntimeError("This BrillTagger has not been trained.")

        self._initialTagger.tag(myToken)

        positionDict = {}

        # Organize positions by tag 
        for i in range(len(myToken['SUBTOKENS'])):
            if not positionDict.has_key(myToken['SUBTOKENS'][i]['TAG']):
                positionDict[myToken['SUBTOKENS'][i]['TAG']] = {}
            positionDict[myToken['SUBTOKENS'][i]['TAG']][i] = None

        # Apply rule only at the positions that have its "original" tag
        for rule in self._rules:
            if positionDict.has_key(rule.getOriginal()):
                changed = rule.applyAt(myToken['SUBTOKENS'], positionDict[rule.getOriginal()])
                # Immediately update positions of tags
                for i in changed:
                    del positionDict[rule.getOriginal()][i]
                    if not positionDict.has_key(rule.getReplacement()):
                        positionDict[rule.getReplacement()] = {}
                    positionDict[rule.getReplacement()][i] = None

    # Finds the rule that makes the biggest net improvement in the corpus.
    # Returns a (rule, score) pair.
    def _bestRule (self, myToken, correctToken):
        best = (0, None)
        print "\nIteration %i:" % (len(self._rules)+1),

        errorIndices = []
        
        # Collect lists of indices that are correct, sorted by their tags
        correctIndices = {}
        
        for i in range(len(myToken['SUBTOKENS'])):
            tag = myToken['SUBTOKENS'][i]['TAG']
            if tag == correctToken['SUBTOKENS'][i]['TAG']:
                if not correctIndices.has_key(tag):
                    correctIndices[tag] = []
                correctIndices[tag].append(i)
            else:
                errorIndices.append(i)

        # Make a set of useful rules, with counts of how many errors they fix
        goodRules = {}

        # Collect all rules that fix any errors, with their positive scores.
        for i in errorIndices:
            # If multiple templates return the same rule for the same location,
            # we only want to count it once, so put the rules in a set first.
            goodRulesHere = {} 
            for template in self._templates:
                # Find the templated rules that could fix the error.
                for rule in template.makeApplicableRules(myToken['SUBTOKENS'], i,
                                                    correctToken['SUBTOKENS'][i]['TAG']):
                    goodRulesHere[rule] = None

            for rule in goodRulesHere.keys():
                if goodRules.has_key(rule):
                    goodRules[rule] += 1
                else:
                    goodRules[rule] = 1
        
        print("%i errors; ranking %i rules;"
              %(len(errorIndices), len(goodRules.keys())))
        
        # Organize useful rules by their positive scores.
        # (Basically, reverse the dictionary so scores now map to rule lists.)
        scores = []
        sortedRules = {}
        while len(goodRules):
            (rule, score) = goodRules.popitem()
            if not sortedRules.has_key(score):
                sortedRules[score] = []
                scores.append(score)
            
            sortedRules[score].append(rule)

        scores.sort()
        scores.reverse()
        # Now, take into account the negative effects of rules -- their mistakes.
        # Start by checking rules with high scores.
        # If, after accounting for negatives, a rule still has a score as high
        # as the best unchecked rules, just return it.  (Side effect: This biases
        # the algorithm in favor of rules that make both positive and negative
        # changes.)

        best = (None, 0)

        for score in scores: # highest first
            for rule in sortedRules[score]:

                if best[1] >= score: # we can't beat that
                    return best
            
                s = score
                # Even better would be: hold an index with each rule.  As soon
                # as *any* minus is found, mark the index and move the rule down
                # to the next score level.  Then try the next rule at the higher
                # level.  Start searching at the index kept with each rule.
                for i in correctIndices[rule.getOriginal()]: # the long part
                    if rule.applies(myToken['SUBTOKENS'], i):
                        s -= 1
                        if s <= best[1]: # not gonna help
                            break

                if s > best[1]:
                    best = (rule, s)
        return best

# Takes a list, returns a dictionary mapping each unique element of the list
# to None
def _listToSet (ls):
    return dict(map(lambda x: (x, None), ls))

# returns r - s, where r and s are dictionaries whose keys represent sets
# return type is a dictionary whose keys map to None
def _setDifference (r, s):
    set = {}
    for k in r.keys():
        if not s.has_key(k):
            set[k] = None
    return set

def _errorPositions (correctToken, token):
    return [i for i in range(len(token['SUBTOKENS'])) \
            if token['SUBTOKENS'][i]['TAG'] != correctToken['SUBTOKENS'][i]['TAG'] ]


# returns a list of errors in string format
def errorList (correctToken, token, radius=2):
    """
    Returns a list of human-readable strings indicating the errors in the
    given tagging of the corpus.

    @param correctToken: The correct tagging of the corpus
    @type correctToken: Token
    @param tokens: The tagged corpus
    @type tokens: list of Token
    @param radius: How many tokens on either side of a wrongly-tagged token
        to include in the error string.  For example, if C{radius}=2, each error
        string will show the incorrect token plus two tokens on either side.
    @type radius: int
    """
    errors = []
    indices = _errorPositions(correctToken, token)
    tokenLen = len(token['SUBTOKENS'])
    for i in indices:
        ei = token['SUBTOKENS'][i]['TAG'].rjust(3) + " -> " \
             + correctToken['SUBTOKENS'][i]['TAG'].rjust(3) + ":  "
        for j in range( max(i-radius, 0), min(i+radius+1, tokenLen) ):
            if token['SUBTOKENS'][j]['TEXT'] == token['SUBTOKENS'][j]['TAG']:
                s = token['SUBTOKENS'][j]['TEXT'] # don't print punctuation tags
            else:
                s = token['SUBTOKENS'][j]['TEXT'] + "/" + token['SUBTOKENS'][j]['TAG']
                
            if j == i:
                ei += "**"+s+"** "
            else:
                ei += s + " "
        errors.append(ei)

    return errors

def getWSJTokens (n, randomize = False):
    """
    Returns a list of the tagged C{Token}s in M{n} files of the Wall Street
    Journal corpus.

    @param n: How many files to get C{Token}s from; if there are more than
        M{n} files in the corpus, all tokens are returned.
    @type n: int
    @param randomize: C{False} means the tokens are from the first M{n} files
        of the corpus.  C{True} means the tokens are from a random set of M{n}
        files.
    @type randomize: Boolean
    @return: The list of tagged tokens
    @rtype: list of C{Token}
    """
    taggedData = []
    items = treebank.items('tagged')
    if randomize:
        random.seed(len(items))
        random.shuffle(items)
    for item in items[:n]:
        taggedData += treebank.tokenize(item)['SUBTOKENS']
    taggedData = [taggedData[i] for i in range(len(taggedData))
                  if taggedData[i]['TEXT'][0] not in "[]="]
    return taggedData

def test(numFiles=100, maxRules=200, minScore=10, ruleFile="dump.rules",
         errorOutput = "errors.out", ruleOutput="rules.out",
         randomize=False, train=.8):

    NN_CD_tagger = nltk.tagger.RegexpTagger([(r'^[0-9]+(.[0-9]+)?$', 'CD'), (r'.*', 'NN')])

    # train is the proportion of data used in training; the rest is reserved
    # for testing.

    print "Loading tagged data..."
    taggedData = getWSJTokens(numFiles, randomize)

    trainCutoff = int(len(taggedData)*train)
    trainingData = nltk.token.Token(SUBTOKENS=taggedData[0:trainCutoff])
    goldData = nltk.token.Token(SUBTOKENS=taggedData[trainCutoff:])
    testingData = goldData.exclude('TAG')

    # Unigram tagger

    print "Training unigram tagger:",
    u = nltk.tagger.UnigramTagger()
    u.train(trainingData)
    backoff = nltk.tagger.BackoffTagger([u, NN_CD_tagger])
    print("[accuracy: %f]"
          %nltk.tagger.tagger_accuracy(backoff, [goldData]))

    # Brill tagger

    from rules import SymmetricProximateTokensTemplate
    from rules import ProximateTagsTemplate
    from rules import ProximateWordsTemplate
    templates = [ \
                  SymmetricProximateTokensTemplate((1,1), ProximateTagsTemplate),
                  SymmetricProximateTokensTemplate((2,2), ProximateTagsTemplate),
                  SymmetricProximateTokensTemplate((1,2), ProximateTagsTemplate),
                  SymmetricProximateTokensTemplate((1,3), ProximateTagsTemplate),
                  SymmetricProximateTokensTemplate((1,1), ProximateWordsTemplate),
                  SymmetricProximateTokensTemplate((2,2), ProximateWordsTemplate),
                  SymmetricProximateTokensTemplate((1,2), ProximateWordsTemplate),
                  SymmetricProximateTokensTemplate((1,3), ProximateWordsTemplate),

                  ProximateTagsTemplate([(-1,-1),  (1,1)]),
                  ProximateWordsTemplate([(-1,-1), (1,1)]) ]
    
    b = BrillTagger(backoff, templates) # use backoff for the initial tagging
    b.train(trainingData, maxRules, minScore)
    #b.fastTrain(trainingData, maxRules, minScore)

    print
    print("Brill accuracy: %f" %nltk.tagger.tagger_accuracy(b, [goldData]))

    print("\nRules: ")
    printRules = file(ruleOutput, 'w')
    for rule in b.getRules():
        print(str(rule))
        printRules.write(str(rule)+"\n\n")
    b.saveRules(ruleFile)

    b.tag(testingData)
    el = errorList(goldData, testingData)
    errorFile = file(errorOutput, 'w')

    for e in el:
        errorFile.write(e+"\n\n")
    errorFile.close()
    print("Done.")


if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 0 or len(args) > 4:
        print "Usage: python brill.py n [randomize [maxRules [minScore]]]\n \
            n -> number of WSJ files to read\n \
            randomize -> 0 (default) means read the first n files in the corpus, \
                          1 means read a random set of n files \n \
            maxRules -> (default 200) generate at most this many rules during \
                             training \n \
            minScore -> (default 2) only use rules which decrease the number of \
                           errors in the training corpus by at least this much"
    else:
        args = map(int, args)
        if len(args) == 1:
            print("Using the first %i files.\n" %args[0])
            test(numFiles = args[0])
        elif len(args) == 2:
            print("Using %i files, randomize=%i\n" %tuple(args[:2]) )
            test(numFiles = args[0], randomize = args[1])
        elif len(args) == 3:
            print("Using %i files, randomize=%i, maxRules=%i\n" %tuple(args[:3]) )
            test(numFiles = args[0], randomize = args[1], maxRules = args[2])
        elif len(args) == 4:
            print("Using %i files, randomize=%i, maxRules=%i, minScore=%i\n"
                  %tuple(args[:4]) )
            test(numFiles = args[0], randomize = args[1], maxRules = args[2],
                 minScore = args[3])

        print("\nCheck errors.out for a listing of errors in the training set, "+
              "and rules.out for a list of the rules above.")
