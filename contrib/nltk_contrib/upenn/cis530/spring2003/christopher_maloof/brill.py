"""
A transformation-based error-driven tagger.
"""

import nltk.tagger
import nltk.token
import nltk.corpus
import os           # for finding Tagged files
import pickle       # for storing/loading rule lists
import random       # for shuffling Tagged files
import sys          # for getting command-line arguments

class BrillTagger(nltk.tagger.TaggerI):
    """
    A transformation-based error-driven tagger.  Before a C{BrillTagger} can be
    used, it should be trained on a list of C{TaggedTokens}.  This will produce
    an ordered list of transformations that are used to tag unknown data.  A
    C{BrillTagger} also requires some other tagger to do an initial tagging
    before transformations can be applied.
    """

    def __init__(self, tagger, templates):
        """
        @param tagger: The initial tagger
        @type tagger: TaggerI
        @param templates: Templates for generating rules
        @type templates: list of TemplateI
        """
        self._initialTagger = tagger
        self._templates = templates
        self._rules = []

    # requires a list of Token with type TaggedType
    def train (self, correctTokens, maxRules = 200, minScore=2):
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

        if self._rules:
            print("WARNING: tagger previously trained, deleting old rules.")
            # Another option would be to keep the old rules at the start of the list.

        print("Checking tagged tokens")
        # Intern all tags for performance
        k=0
        for token in correctTokens:
            if not token.type().tag(): # the corpus isn't quite perfect...
                correctTokens.remove(token)
                k += 1
            else:
                intern(token.type().tag())
        #print("Found %i untagged tokens out of %i" %(k, len(correctTokens)+k))
        print("Doing initial tagging...")
        # Do the initial tagging of the training tokens
        tokens = nltk.tagger.untag(correctTokens)
        tokens = self._initialTagger.tag(tokens)
        print("Initial tagging done.")

        # loop and create list of rules here
        self._rules = []
        while len(self._rules) < maxRules:
            (rule, score) = self._bestRule(tokens, correctTokens)
            # We should eventually run out of useful rules
            if rule != None and score >= minScore:
                self._rules.append(rule)
                print "Applying rule..."
                k = rule.applyTo(tokens)  # not optimized (see tag())
                print "Rule changed %i locations." %len(k)
            else:
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
            raise UntrainedError("This BrillTagger has not been trained.")
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

    def tag (self, tokens):
        # Inherit documentation from TaggerI
        if not self._rules:
            raise UntrainedError("This BrillTagger has not been trained.")

        tokens = self._initialTagger.tag(tokens)

        positionDict = {}

        # Organize positions by tag 
        for i in range(len(tokens)):
            if not positionDict.has_key(tokens[i].type().tag()):
                positionDict[tokens[i].type().tag()] = {}
            positionDict[tokens[i].type().tag()][i] = None

        # Apply rule only at the positions that have its "original" tag
        for rule in self._rules:
            if positionDict.has_key(rule.getOriginal()):
                changed = rule.applyAt(tokens, positionDict[rule.getOriginal()])
                # Immediately update positions of tags
                for i in changed:
                    del positionDict[rule.getOriginal()][i]
                    if not positionDict.has_key(rule.getReplacement()):
                        positionDict[rule.getReplacement()] = {}
                    positionDict[rule.getReplacement()][i] = None

        return tokens

    # Finds the rule that makes the biggest net improvement in the corpus.
    # Returns a (rule, score) pair.
    def _bestRule (self, tokens, correctTokens):
        best = (0, None)
        print("\nFinding rule %i for %i tokens..."
              %(len(self._rules)+1, len(tokens)))
        print("  Organizing corpus...")

        errorIndices = [] #_errorPositions(tokens, correctTokens)
        
        # Collect lists of indices that are correct, sorted by their tags
        correctIndices = {}
        
        for i in range(len(tokens)):
            tag = tokens[i].type().tag()
            if tag == correctTokens[i].type().tag():
                if not correctIndices.has_key(tag):
                    correctIndices[tag] = []
                correctIndices[tag].append(i)
            else:
                errorIndices.append(i)

        # Make a set of useful rules, with counts of how many errors they fix
        goodRules = {}

        print("  Finding useful rules...")
        # Collect all rules that fix any errors, with their positive scores.
        for i in errorIndices:
            for template in self._templates:             
                # Find the templated rules that could fix the error.
                # ALERT: This is not quite right.  If one or more templates
                # return identical rules, they should only be counted once.
                # Maybe we could put all rules in a set, then increment goodRules.
                for rule in template.makeApplicableRules(tokens, i,
                                                    correctTokens[i].type().tag()):
                    if goodRules.has_key(rule):
                        goodRules[rule] += 1
                    else:
                        goodRules[rule] = 1
        
        print("  Found %i good rules for fixing %i errors."
              %(len(goodRules.keys()), len(errorIndices)))
        
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
        #
        # This is the most time-consuming part of the process.  The algorithm
        # might still work OK if we skipped it, actually.
        # OK, after adding one silly little line, it's not so long anymore.
        print("  Analyzing rules' negative effects...")
        best = (None, 0)

        for score in scores: # highest first
            for rule in sortedRules[score]:

                if best[1] >= score: # we can't beat that
                    print("%s (score: %i)" %(best[0], best[1]))
                    return best
            
                s = score
                # Even better would be: hold an index with each rule.  As soon
                # as *any* minus is found, mark the index and move the rule down
                # to the next score level.  Then try the next rule at the higher
                # level.  Start searching at the index kept with each rule.
                for i in correctIndices[rule.getOriginal()]: # the long part
                    if rule.applies(tokens, i):
                        s -= 1
                        if s <= best[1]: # not gonna help
                            break

                if s > best[1]:
                    best = (rule, s)

        print("%s (score: %i)" %(best[0], best[1]))
        return best


class TemplateI:
    """
    An interface for producing transformations that apply at given corpus positions.
    """
    def __init__(self):
        assert False, "TemplateI is an abstract interface"

    def makeApplicableRules(self, tokens, index, correctTag):
        """
        Constructs a list of zero or more transformations that would change
        the tag of C{tokens[index]} to C{correctTag}, given
        the context in C{tokens}.

        (If the tags are already identical, returns
        the empty list.)

        @param tokens: A corpus of tagged C{Token}s
        @type tokens: list of Token
        @param index: The index of C{tokens} to be corrected by returned rules
        @type index: int
        @param correctTag: The correct tag for C{tokens[index]}
        @type correctTag: any
        @return: A list of transformations that would correct the tag of
        C{tokens[index]}, or the empty list if the tag is correct already.
        @rtype: list of RuleI
        """
        assert False, "TemplateI is an abstract interface"

class ProximateTokensTemplateI(TemplateI):
    """
    For generating rules of the form 'If the M{n}th token is tagged C{A}, and any
    token between M{n+start} and M{n+end} has property C{B}, and ... , then change
    the tag of the M{n}th token from C{A} to C{C}.'  For example, M{start=end=-1}
    would refer to rules that check just the preceding token's tag.  Note that
    multiple tests may be included in a rule; the rule applies if they all hold.

    The return value of C{extractProperty} must represent a token property.
    The rules generated by this template check extracted properties for equality.
    For example, C{extractProperty} could be defined to pull out a token's tag or
    its base lexical item: see L{ProximateTagsTemplate} and
    L{ProximateWordsTemplate}.
    """
    
    # List of 2-tuples of ints.
    def __init__(self, boundaryList, proximateRuleType):
        """
        Constructs a template for generating rules.  C{boundaryList} is a list
        of 2-tuples of C{int}s, or a single such 2-tuple.  Each pair represents
        a part of the corpus which a condition of generated rules refers to,
        relative to the token affected.
        
        Using C{boundaryList=(-2,-1)} results in a template for rules which
        apply to token C{T} if either of the two tokens preceding C{T} has a particular
        property.  Using C{boundaryList=[(-2,-1), (1,1)]} produces rules which
        impose an additional requirement on the token following C{T}.

        The transformations produced are constructed by calling C{proximateRuleType}
        on appropriate arguments.  B{The return value of C{extractProperty} must
        equal the return value of the C{extractProperty} method of the object
        constructed by C{proximateRuleType}!}

        This constructor is abstract and should only be called by subclasses.

        @param boundaryList: Tuples representing how far from a token a rule
        may apply.
        @type boundaryList: 2-tuple of int, or list of 2-tuple of int
        @param proximateRuleType: A constructor for a subclass of ProximateRuleI.
        @type proximateRuleType: function
        """
        if len(boundaryList) == 2 and type(boundaryList[0]) == int \
                                  and type(boundaryList[1]) == int:
            self._boundaryList = [boundaryList]
        else:
            self._boundaryList = boundaryList[:]
        self._proximateRuleType = proximateRuleType

    # Returns a list of Rules that would make the right correction at
    # the indicated site.
    # All lists should be unique if the tuples in _boundaryList are unique.
    def makeApplicableRules (self, tokens, index, correctTag):
        """
        See L{TemplateI} for full specifications.

        @rtype: list of ProximateTokensRuleI
        """
        if tokens[index].type().tag() == correctTag:
            return []
        
        subruleSets = []
        for (start, end) in self._boundaryList:
            # Each Rule may have multiple subrule conditions for its application, each
            # one matching an element of boundaryList.
            # Collect the set of conditions that would satisfy this particular
            # (start,end) subrule.  (Not a list; we don't want repeats.)
            subrules = {}
            # A match anywhere in this range will suffice for this condition.
            for j in range(max(0, index+start), min(index+end+1, len(tokens))):
                subrules[ (start, end,
                           self.extractProperty(tokens[j])) ] = None

            subruleSets.append(subrules)

        # Now, cross the sets of subrules, as any combination would match this index
        # in the token list.  Obtain a list of lists of tuples.  Each list will
        # correspond to a Rule we generate, each tuple to a condition in that Rule.
        if len(subruleSets) != 1:
            tupleLists = reduce(_crossLists, map(dict.keys, subruleSets), [[]])
        else:
            # for speed in the common case
            tupleLists = [[r] for r in subruleSets[0].keys()]
            
        # Finally, translate the tuples into rules and return them.
        return [ self._proximateRuleType(x, tokens[index].type().tag(), correctTag)
                 for x in tupleLists ]
    
    # extractProperty is a function on tagged tokens that returns a value.
    # WARNING: The template and its rule type had better have the same implementation.
    # (Can't just pass the function to the rules, because that makes rules unpicklable.
    #  And Python lacks static methods, so can't call a rule function from here.)
    def extractProperty (self, token):
        """
        Returns some property characterizing this token, such as its base lexical
        item or its tag.

        Each implentation of this method should correspond to an implementation of
        the method with the same name in a subclass of L{ProximateTokensRuleI}.

        @param token: The token
        @type token: Token
        @return: The property
        @rtype: any
        """
        assert False, "ProximateTokensTemplateI is an abstract interface"


# Returns a much longer list of slightly longer lists.
# In particular, each element in listOfSingles is appended to each list in
# listOfLists, and the resulting big list is returned.
def _crossLists(listOfLists, listOfSingles):
    return [ j + [k] for j in listOfLists for k in listOfSingles ]    

class RuleI:
    """
    An interface for a transformation that can be applied to a tagged corpus.

    The transformation is of the form: For each token in the corpus tagged C{X},
    if I{condition}, then change the tag of the token to C{Y}.  C{X} and C{Y}
    are fixed for each C{RuleI}.  I{condition} may refer to the token and the
    remainder of the corpus.
    """
    def __init__(self):
        assert False, "RuleI is an abstract interface"
    
    def applyTo(self, tokens):
        """
        Applies the rule to the corpus.

        @param tokens: The tagged corpus
        @type tokens: list of Token
        @return: The indices of tokens whose tags were changed by this rule
        @rtype: list of int
        """
        return self.applyAt(tokens, range(len(tokens)))

    # Applies this rule at the given positions in the corpus
    # Returns the positions affected by the application
    def applyAt(self, tokens, positions):
        """
        Applies the rule to the indicated indices of the corpus.  (The rule's
        conditions are still tested.)

        @param tokens: The tagged corpus
        @type tokens: list of Token
        @param positions: The positions where the transformation is to be tried
        @return: The indices of tokens whose tags were changed by this rule
        @rtype: list of int
        """
        assert False, "RuleI is an abstract interface"

    # Returns 1 if the rule would apply at the given index in tokens
    def applies(self, tokens, index):
        """
        Indicates whether this rule would make a change at C{tokens[index]}.

        @param tokens: A tagged corpus
        @type tokens: list of Token
        @param index: The index to check
        @type index: int
        @return: True if the rule would change the tag of C{tokens[index]},
            False otherwise
        @rtype: Boolean
        """
        assert False, "RuleI is an abstract interface"
        
    def getOriginal(self):
        """
        Returns the tag C{X} which this C{RuleI} may cause to be replaced.

        @return: The tag targeted by this rule
        @rtype: any
        """
        assert False, "RuleI is an abstract interface"

    def getReplacement(self):
        """
        Returns the tag C{Y} with which this C{RuleI} may replace another tag.

        @return: The tag created by this rule
        @rtype: any
        """
        assert False, "RuleI is an abstract interface"

    # Rules must be comparable and hashable for the algorithm to work
    def __eq__(self):
        assert False, "RuleI is an abstract interface"

    def __hash__(self):
        assert False, "RuleI is an abstract interface"

class ProximateTokensRuleI (RuleI):
    """
    A rule of the form 'If the M{n}th token is tagged C{A}, and any token
    between M{n+start} and M{n+end} has property C{B}, and ... , then change the
    tag of the M{n}th token from C{A} to C{C}.'  For example, M{start=end=-1} would
    refer to rules that check just the property of the preceding token.  Note that
    multiple tests may be included in a rule; the rule applies if they all hold.

    A C{ProximateTokensRuleI} is determined by the values of C{A} and C{C} plus
    a list of C{(start, end, property)} triples.

    The return value of C{extractProperty} must represent a token property.
    For example, C{extractProperty} could be defined to return a
    token's tag or its base lexical item: see L{ProximateTagsTemplate} and
    L{ProximateWordsTemplate}.
    """
    def __init__(self, conditionList, original, replacement):
        """
        Constructs a new rule that changes the tag C{original} to the tag
        C{replacement} if all the properties in C{conditionList} hold.

        C{conditionList} is a single 3-tuple C{(start, end, property)} or a list
        of such 3-tuples.  Each tuple represents an interval relative to a token
        plus a property which must hold for at least one token in the interval
        in order for the rule to apply.  A C{ProximateTokensRuleI} constructed
        with C{conditionList=(-2,-1, "NN")} applies to a token C{T} only if
        C{extractProperty} returns "NN" when applied to one of the two tokens
        preceding C{T}.

        This constructor is abstract and should only be called by subclasses.
        """

        if len(conditionList) == 3 and type(conditionList[0]) == int \
                                   and type(conditionList[1]) == int \
                                   and type(conditionList[2]) == int:
            self._conditionList = (conditionList,)     # 1-tuple
        else:
            self._conditionList = tuple(conditionList) # tuple for hashability
        
        self._original = original
        self._replacement = replacement

    # extractProperty is a function on tagged tokens that returns a value.
    # WARNING: The template and its rule type had better have the same implementation.
    def extractProperty (self, token):
        """
        Returns some property characterizing this token, such as its base lexical
        item or its tag.

        Each implentation of this method should correspond to an implementation of
        the method with the same name in a subclass of L{ProximateTokensTemplateI}.

        @param token: The token
        @type token: Token
        @return: The property
        @rtype: any
        """
        assert False, "ProximateTokensRuleI is an abstract interface"

    def applyAt(self, tokens, positions):
        # Inherit docs from RuleI
        change = []
        for i in positions:
            if self.applies(tokens, i):
                change.append(i)

        for i in change:
            # replace the token with a similar one, except retagged
            tokens[i] = nltk.token.Token(
                    nltk.tagger.TaggedType(tokens[i].type().base(), self._replacement),
                    tokens[i].loc())
        
        return change

    def applies(self, tokens, index):
        # Inherit docs from RuleI
        # Does the target tag match this rule?
        if tokens[index].type().tag() != self._original:
            return False
        
        # Otherwise, check each condition separately
        for (start, end, T) in self._conditionList:
            conditionOK = False
            # Check each token that could satisfy the condition
            for j in range(max(0, index+start), min(index+end+1, len(tokens))):
                if self.extractProperty(tokens[j]) == T:
                    conditionOK = True
                    break
            if not conditionOK:  # all conditions must hold
                return False

        return True

    def getOriginal(self):
        # Inherit docs from RuleI
        return self._original

    def getReplacement(self):
        # Inherit docs from RuleI
        return self._replacement

    def __eq__(self, other):
        return (self._original == other._original and \
                self._replacement == other._replacement and \
                self._conditionList == other._conditionList)

    def __hash__(self):
        # Needs to include extractProperty in order to distinguish subclasses
        # A nicer way would be welcome.
        return hash( (self._original, self._replacement, self._conditionList,
                      self.extractProperty.func_code) )
    

class ProximateTagsTemplate(ProximateTokensTemplateI):
    """
    A template for generating L{ProximateTagsRule}s, which examine the tags of
    nearby tokens.  See superclass L{ProximateTokensTemplateI} for details.
    """
    
    def __init__ (self, boundaryList):
        """
        @param boundaryList: The intervals in which tags are checked, relative to
            the position of the token that a generated rule is testing
        @type boundaryList: 2-tuple of int, or list of 2-tuple of int
        """
        ProximateTokensTemplateI.__init__(self, boundaryList, ProximateTagsRule)

    def extractProperty (self, token):
        """
        Returns the tag of a token.

        @param token: The token
        @type token: Token
        @return: The tag
        @rtype: any
        """
        return token.type().tag()

class ProximateTagsRule (ProximateTokensRuleI):
    """
    A rule which examines the tags of nearby tokens.
    See superclass L{ProximateTokensRuleI} for details.

    See also L{ProximateTagsTemplate}, which generates these rules.
    """

    def extractProperty (self, token):
        """
        Returns the tag of a token.

        @param token: The token
        @type token: Token
        @return: The tag
        @rtype: any
        """
        return token.type().tag()

    def __str__(self):
        return "Replace %s with %s if %s" %(self._original, self._replacement,
                                    _strConditions(self._conditionList, "tagged "))

class ProximateWordsTemplate(ProximateTokensTemplateI):
    """
    A template for generating L{ProximateWordsRule}s, which examine the base types
    of nearby tokens.  See superclass L{ProximateTokensTemplateI} for details.
    """

    def __init__ (self, boundaryList):
        """
        @param boundaryList: The intervals in which base types are checked,
            relative to the position of the token that a generated rule is testing
        @type boundaryList: 2-tuple of int, or list of 2-tuple of int
        """
        ProximateTokensTemplateI.__init__(self, boundaryList, ProximateWordsRule)

    def extractProperty (self, token):
        """
        Returns the base type of a token.  For a corpus of tagged text, this
        corresponds to a word or lexical item.

        @param token: The token
        @type token: Token
        @return: The base type
        @rtype: any
        """
        return token.type().base()

# a lexical rule
class ProximateWordsRule (ProximateTokensRuleI):
    """
    A rule which examines the base types of nearby tokens.
    See superclass L{ProximateTokensRuleI} for details.

    See also L{ProximateWordsTemplate}, which generates these rules.
    """

    def extractProperty (self, token):
        """
        Returns the base type of a token.  For a corpus of tagged text, this
        corresponds to a word or lexical item.

        @param token: The token
        @type token: Token
        @return: The base type
        @rtype: any
        """
        return token.type().base()

    def __str__(self):
        return "Replace %s with %s if %s" %(self._original, self._replacement,
                                            _strConditions(self._conditionList, ""))

def _strConditions (conditionList, tagged):
    # tagged is just an ad hoc string that differs between Words and Tags rules
    if len(conditionList) == 0:
        return "the sun rises in the east" # no conditions, always applies
    else:
        base = _strCondition(conditionList[0], tagged)
        for c in conditionList[1:]:
            base += ", and " + _strCondition(c, tagged)

    return base

def _strCondition (cond, tagged):
    (start, end, T) = cond  # T is the property checked by the condition
    if start > end:
        return "pigs fly" # condition can't be fulfilled
    
    elif start == end:
        if start == -1:
            return "the preceding word is %s%s" %(tagged, T)
        elif start == 1:
            return "the following word is %s%s" %(tagged, T)
        elif start < -1:
            return "the word %i before is %s%s" %(0-start, tagged, T)
        else: # start = 0 or start > 1
            return "the word %i after is %s%s" %(start, tagged, T)
    else:
        if end < 0:
            return "one of the %i preceding words is %s%s" %(end-start+1, tagged, T)
        elif start > 0:
            return "one of the %i following words is %s%s" %(end-start+1, tagged, T)
        else: # start <= 0 but end >= 0 -- an odd rule
            return "this word, or one of the %i preceding words, or one of the \
                    %i following words, is %s%s" %(end, end, tagged, T)


class SymmetricProximateTokensTemplate(TemplateI):
    """
    Simulates two L{ProximateTokensTemplateI}s which are symmetric across the
    location of the token.  For rules of the form "If the M{n}th token is tagged
    C{A}, and any tag preceding B{or} following the M{n}th token by a distance
    between M{x} and M{y} is C{B}, and ... , then change the tag of the nth token
    from C{A} to C{C}."

    One C{ProximateTokensTemplateI} is formed by passing in the same arguments
    given to this class's constructor: tuples representing intervals in which
    a tag may be found.  The other C{ProximateTokensTemplateI} is constructed
    with the negative of all the arguments in reversed order.  For example, a
    C{SymmetricProximateTokensTemplate} using the pair (-2,-1) and the
    constructor C{ProximateTagsTemplate} generates the same rules as a
    C{ProximateTagsTemplate} using (-2,-1) plus a second C{ProximateTagsTemplate}
    using (1,2).

    This is useful because we typically don't want templates to specify only
    "following" or only "preceding"; we'd like our rules to be able to look in
    either direction.
    """

    def __init__(self, boundaryList, proximateTokensTemplate):
        """
        @param boundaryList: Tuples representing how far from a token a rule
            may apply.  Do not pass arguments like [(-2,-1), (1,2)] which
            include symmetric pairs already; this may cause the template to
            generate redundant rules.
        @type boundaryList: 2-tuple of int, or list of 2-tuple of int
        @param proximateTokensTemplate: A constructor for a subclass of
            C{ProximateTokensTemplateI}.
        @type proximateTokensTemplate: function
        """
        self._ppt1 = proximateTokensTemplate(boundaryList)
        if len(boundaryList) == 2 and type(boundaryList[0]) == int \
                                  and type(boundaryList[1]) == int:
            self._ppt2 = proximateTokensTemplate((-1*boundaryList[1],
                                                  -1*boundaryList[0]))
        else:
            self._ppt2 = proximateTokensTemplate([(-1*b, -1*a)
                                                  for (a,b) in boundaryList])

    # Generates lists of a subtype of ProximateTokensRuleI.
    def makeApplicableRules(self, tokens, index, correctTag):
        """
        See L{TemplateI} for full specifications.

        @rtype: list of ProximateTokensRuleI
        """
        return self._ppt1.makeApplicableRules(tokens, index, correctTag) \
               + self._ppt2.makeApplicableRules(tokens, index, correctTag)


def _errorPositions (tokens, correctTokens):
    return [i for i in range(len(tokens)) \
            if tokens[i].type().tag() != correctTokens[i].type().tag() ]


# returns a list of errors in string format
def errorList (tokens, correctTokens, radius=2):
    """
    Returns a list of human-readable strings indicating the errors in the
    given tagging of the corpus.

    @param tokens: The tagged corpus
    @type tokens: list of Token
    @param correctTokens: The correct tagging of the corpus
    @type correctTokens: list of Token
    @param radius: How many tokens on either side of a wrongly-tagged token
        to include in the error string.  For example, if C{radius}=2, each error
        string will show the incorrect token plus two tokens on either side.
    @type radius: int
    """
    errors = []
    indices = _errorPositions(tokens, correctTokens)
    for i in indices:
        ei = tokens[i].type().tag().rjust(3) + " <- " \
             + correctTokens[i].type().tag().rjust(3) + ":  "
        for j in range( max(i-radius, 0), min(i+radius+1, len(tokens)) ):
            if tokens[j].type().base() == tokens[j].type().tag():
                s = tokens[j].type().base() # don't print punctuation tags
            else:
                s = tokens[j].type().base() + "/" + tokens[j].type().tag()
                
            if j == i:
                ei += "**"+s+"** "
            else:
                ei += s + " "
        errors.append(ei)

    return errors

def tokenizeTaggedFile (taggedFile, tokenizer):
    """
    Parses a tagged file from the Penn Treebank Wall Street Journal Corpus
    using the given C{TaggedTokenizer} and returns the list of tagged
    C{Token}s that results.  Removes headers, brackets, slashes, and other
    extraneous text.

    @param taggedFile: an open file of the Tagged corpus
    @type taggedFile: file
    @param tokenizer: the tokenizer
    @type tokenizer: nltk.tagger.TaggedTokenizer
    """
    header = 0
    taggedTokens = []
    for line in taggedFile.readlines():
        if header and line[0] == '=':
            header = 0
        elif not header:
            s = line.strip(' []\n=')

            if len(s):
                # The Tagged corpus contains fractions, written as '3\/4/CD'.
                # The tokenizer thinks 4/CD is the tag part (a "slashed type").
                # We need to make the base 3\/4 and the tag CD.
                # Also, a few words/symbols are not tagged at all.  Drop these.
                for token in tokenizer.tokenize(s.strip()):
                    tag = token.type().tag()
                    if not tag:
                        continue
                    elif tag.count('/') > 0:
                        lastSlash = tag.rfind('/')
                        base = token.type().base() + '/' + tag[:lastSlash]
                        token = nltk.token.Token(
                            nltk.tagger.TaggedType(base, tag[lastSlash+1:]),
                                                 token.loc())
                    taggedTokens.append(token)
                #taggedTokens += tokenizer.tokenize(s.strip())

    return taggedTokens

# argument: number of files to check
def getTaggedFilenames (n, randomize = False):
    """
    Returns a list of up to M{n} locations of files in the Wall Street
    Journal corpus.  Only works on gradient.cis.upenn.edu, because the
    location of the corpus is hard-coded in.

    @param n: The maximum number of filenames to return.  (Fewer will be returned
        only if M{n} is larger than the number of files in the corpus, which is
        6058; in this case all filenames will be returned.)
    @type n: int
    @param randomize: C{False} means the filenames will be sorted in the obvious
        way, with the numeric directories checked in order and the filenames
        ordered within each directory.  The first M{n} files in the order are
        returned.  C{True} means a random set of filenames will be returned.
    @type randomize: int
    @return: The list of filenames
    @rtype: list of string
    """
    if n == 0:
        return []

    entries = nltk.corpus.brown.entries()
    if randomize:
        random.shuffle(entries)
        
    if len(entries) < n:
        print("Returning all %i files." %len(entries))
    entries = entries[:n] # no error, even if n is large

    return [nltk.corpus.brown.path(e) for e in entries]
    
#     nltk.corpus.brown
#     location = "/mnt/unagi/nldb2/cdrom-12-92/tagged/tagged/"
#     directories = os.listdir(location)

#     if randomize:
#         for directory in directories:
#             filenames = os.listdir(location+directory)
#             for filename in filenames:
#                 files.append(location+directory+"/"+filename)
#         random.shuffle(files)
#         if len(files) < n:
#             print("Returning all %i files." %len(files))
#         return files[:n] # no error, even if n is large
    
#     else:
#         directories.sort()
#         for directory in directories:
#             filenames = os.listdir(location+directory)
#             filenames.sort()
#             for filename in filenames:
#                 files.append(location+directory+"/"+filename)
#                 if len(files) == n:
#                     return files

#     print("Returning all %i files." %len(files))
#     return files

# argument: number of files to check
def getTaggedTokens (n, randomize = False):
    """
    Returns a list of the tagged C{Token}s in M{n} files of the Wall Street
    Journal corpus.  Only works on gradient.cis.upenn.edu, because the
    location of the corpus is hard-coded in.

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
    tokenizer = nltk.tagger.TaggedTokenizer()
    filenames = getTaggedFilenames(n, randomize)
    for filename in filenames:
        f = file(filename, 'r')
        taggedData += tokenizeTaggedFile(f, tokenizer)

    return taggedData

def test(numFiles=3, maxRules=200, minScore=2, ruleFile="dump.rules",
         errorOutput = "errors.out", ruleOutput="rules.out",
         randomize=False, train=.8):

    # train is the proportion of data used in training; the rest is reserved
    # for testing.

    taggedData = getTaggedTokens(numFiles, randomize)

    trainCutoff = int(len(taggedData)*train)
    trainingData = taggedData[0:trainCutoff]
    testingData = taggedData[trainCutoff:]

    print("Training unigram tagger...")
    u = nltk.tagger.UnigramTagger()
    u.train(trainingData)
    backoff = nltk.tagger.BackoffTagger([u, nltk.tagger.NN_CD_Tagger()])

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

    testTokens = nltk.tagger.untag(testingData)

    print("\nUnigram accuracy: %f"
          %nltk.tagger.accuracy(testingData, backoff.tag(testTokens)))
    btagged = b.tag(testTokens)
    print("Brill accuracy: %f" %nltk.tagger.accuracy(testingData, btagged))
    print("\nRules: ")
    printRules = file(ruleOutput, 'w')
    for rule in b.getRules():
        print(str(rule))
        printRules.write(str(rule)+"\n\n")
    b.saveRules(ruleFile)

    el = errorList(btagged, testingData)
    errorFile = file(errorOutput, 'w')

    for e in el:
        errorFile.write(e+"\n\n")
    errorFile.close()
    print("Done.")

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 0 or len(args) > 4:
        print "Usage: python brill.py n [randomize [maxRules [minScore]]]\n \
            n -> number of Tagged files to read\n \
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
