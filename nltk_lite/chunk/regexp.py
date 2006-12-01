# Natural Language Toolkit: Regular Expression Chunkers
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.chunk import *
from nltk_lite.parse import AbstractParse

class RegexpChunkRule(object):
    """
    A rule specifying how to modify the chunking in a C{ChunkString},
    using a transformational regular expression.  The
    C{RegexpChunkRule} class itself can be used to implement any
    transformational rule based on regular expressions.  There are
    also a number of subclasses, which can be used to implement
    simpler types of rules, based on matching regular expressions.

    Each C{RegexpChunkRule} has a regular expression and a
    replacement expression.  When a C{RegexpChunkRule} is X{applied}
    to a C{ChunkString}, it searches the C{ChunkString} for any
    substring that matches the regular expression, and replaces it
    using the replacement expression.  This search/replace operation
    has the same semantics as C{re.sub}.

    Each C{RegexpChunkRule} also has a description string, which
    gives a short (typically less than 75 characters) description of
    the purpose of the rule.
    
    This transformation defined by this C{RegexpChunkRule} should
    only add and remove braces; it should I{not} modify the sequence
    of angle-bracket delimited tags.  Furthermore, this transformation
    may not result in nested or mismatched bracketing.
    """
    def __init__(self, regexp, repl, descr):
        """
        Construct a new RegexpChunkRule.
        
        @type regexp: C{regexp} or C{string}
        @param regexp: This C{RegexpChunkRule}'s regular expression.
            When this rule is applied to a C{ChunkString}, any
            substring that matches C{regexp} will be replaced using
            the replacement string C{repl}.  Note that this must be a
            normal regular expression, not a tag pattern.
        @type repl: C{string}
        @param repl: This C{RegexpChunkRule}'s replacement
            expression.  When this rule is applied to a
            C{ChunkString}, any substring that matches C{regexp} will
            be replaced using C{repl}.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        if type(regexp).__name__ == 'SRE_Pattern': regexp = regexp.pattern
        self._repl = repl
        self._descr = descr
        if type(regexp) == types.StringType:
            self._regexp = re.compile(regexp)
        else:
            self._regexp = regexp

    def apply(self, chunkstr):
        # Keep docstring generic so we can inherit it.
        """
        Apply this rule to the given C{ChunkString}.  See the
        class reference documentation for a description of what it
        means to apply a rule.
        
        @type chunkstr: C{ChunkString}
        @param chunkstr: The chunkstring to which this rule is
            applied. 
        @rtype: C{None}
        @raise ValueError: If this transformation generated an
            invalid chunkstring.
        """
        chunkstr.xform(self._regexp, self._repl)

    def descr(self):
        """
        @rtype: C{string}
        @return: a short description of the purpose and/or effect of
            this rule.
        """
        return self._descr

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <RegexpChunkRule: '{<IN|VB.*>}'->'<IN>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<RegexpChunkRule: '+`self._regexp.pattern`+
                '->'+`self._repl`+'>')
        
class ChunkRule(RegexpChunkRule):
    """
    A rule specifying how to add chunks to a C{ChunkString}, using a
    matching tag pattern.  When applied to a C{ChunkString}, it will
    find any substring that matches this tag pattern and that is not
    already part of a chunk, and create a new chunk containing that
    substring.
    """
    def __init__(self, tag_pattern, descr):

        """
        Construct a new C{ChunkRule}.
        
        @type tag_pattern: C{string}
        @param tag_pattern: This rule's tag pattern.  When
            applied to a C{ChunkString}, this rule will
            chunk any substring that matches this tag pattern and that
            is not already part of a chunk.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile('(?P<chunk>%s)%s' %
                            (tag_pattern2re_pattern(tag_pattern),
                             ChunkString.IN_CHINK_PATTERN))
        RegexpChunkRule.__init__(self, regexp, '{\g<chunk>}', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ChunkRule: '<IN|VB.*>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<ChunkRule: '+`self._pattern`+'>'

class ChinkRule(RegexpChunkRule):
    """
    A rule specifying how to remove chinks to a C{ChunkString},
    using a matching tag pattern.  When applied to a
    C{ChunkString}, it will find any substring that matches this
    tag pattern and that is contained in a chunk, and remove it
    from that chunk, thus creating two new chunks.
    """
    def __init__(self, tag_pattern, descr):
        """
        Construct a new C{ChinkRule}.
        
        @type tag_pattern: C{string}
        @param tag_pattern: This rule's tag pattern.  When
            applied to a C{ChunkString}, this rule will
            find any substring that matches this tag pattern and that
            is contained in a chunk, and remove it from that chunk,
            thus creating two new chunks.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile('(?P<chink>%s)%s' %
                            (tag_pattern2re_pattern(tag_pattern),
                             ChunkString.IN_CHUNK_PATTERN))
        RegexpChunkRule.__init__(self, regexp, '}\g<chink>{', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ChinkRule: '<IN|VB.*>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<ChinkRule: '+`self._pattern`+'>'

class UnChunkRule(RegexpChunkRule):
    """
    A rule specifying how to remove chunks to a C{ChunkString},
    using a matching tag pattern.  When applied to a
    C{ChunkString}, it will find any complete chunk that matches this
    tag pattern, and un-chunk it.
    """
    def __init__(self, tag_pattern, descr):
        """
        Construct a new C{UnChunkRule}.
        
        @type tag_pattern: C{string}
        @param tag_pattern: This rule's tag pattern.  When
            applied to a C{ChunkString}, this rule will
            find any complete chunk that matches this tag pattern,
            and un-chunk it.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile('\{(?P<chunk>%s)\}' %
                            tag_pattern2re_pattern(tag_pattern))
        RegexpChunkRule.__init__(self, regexp, '\g<chunk>', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <UnChunkRule: '<IN|VB.*>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<UnChunkRule: '+`self._pattern`+'>'

class MergeRule(RegexpChunkRule):
    """
    A rule specifying how to merge chunks in a C{ChunkString}, using
    two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk whose end
    matches left pattern, and immediately followed by a chunk whose
    beginning matches right pattern.  It will then merge those two
    chunks into a single chunk.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{MergeRule}.

        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            C{left_tag_pattern}, and immediately followed by a chunk
            whose beginning matches this pattern.  It will
            then merge those two chunks into a single chunk.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            this pattern, and immediately followed by a chunk
            whose beginning matches C{right_tag_pattern}.  It will
            then merge those two chunks into a single chunk.
            
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)}{(?=%s)' %
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, '\g<left>', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <MergeRule: '<NN|DT|JJ>', '<NN|JJ>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<MergeRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class SplitRule(RegexpChunkRule):
    """
    A rule specifying how to split chunks in a C{ChunkString}, using
    two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk that
    matches the left pattern followed by the right pattern.  It will
    then split the chunk into two new chunks, at the point between the
    two pattern matches.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{SplitRule}.
        
        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this rule will
            find any chunk containing a substring that matches
            C{left_tag_pattern} followed by this pattern.  It will
            then split the chunk into two new chunks at the point
            between these two matching patterns.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this rule will
            find any chunk containing a substring that matches this
            pattern followed by C{right_tag_pattern}.  It will then
            split the chunk into two new chunks at the point between
            these two matching patterns.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)(?=%s)' % 
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, r'\g<left>}{', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <SplitRule: '<NN>', '<DT>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<SplitRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class ExpandLeftRule(RegexpChunkRule):
    """
    A rule specifying how to expand chunks in a C{ChunkString} to the left,
    using two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk whose beginning
    matches right pattern, and immediately preceded by a chink whose
    end matches left pattern.  It will then expand the chunk to incorporate
    the new material on the left.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{ExpandRightRule}.

        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose beginning matches
            C{right_tag_pattern}, and immediately preceded by a chink
            whose end matches this pattern.  It will
            then merge those two chunks into a single chunk.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose beginning matches
            this pattern, and immediately preceded by a chink
            whose end matches C{left_tag_pattern}.  It will
            then expand the chunk to incorporate the new material on the left.
            
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)\{(?P<right>%s)' %
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, '{\g<left>\g<right>', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ExpandLeftRule: '<NN|DT|JJ>', '<NN|JJ>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<ExpandLeftRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class ExpandRightRule(RegexpChunkRule):
    """
    A rule specifying how to expand chunks in a C{ChunkString} to the right,
    using two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk whose end
    matches left pattern, and immediately followed by a chink whose
    beginning matches right pattern.  It will then expand the chunk to incorporate
    the new material on the right.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{ExpandRightRule}.

        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            C{left_tag_pattern}, and immediately followed by a chink
            whose beginning matches this pattern.  It will
            then merge those two chunks into a single chunk.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            this pattern, and immediately followed by a chink
            whose beginning matches C{right_tag_pattern}.  It will
            then expand the chunk to incorporate the new material on the right.
            
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)\}(?P<right>%s)' %
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, '\g<left>\g<right>}', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ExpandRightRule: '<NN|DT|JJ>', '<NN|JJ>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<ExpandRightRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

##//////////////////////////////////////////////////////
##  RegexpChunk
##//////////////////////////////////////////////////////

class RegexpChunk(ChunkParseI, AbstractParse):
    """
    A regular expression based chunk parser.  C{RegexpChunk} uses a
    sequence of X{rules} to find chunks of a single type within a
    text.  The chunking of the text is encoded using a C{ChunkString},
    and each rule acts by modifying the chunking in the
    C{ChunkString}.  The rules are all implemented using regular
    expression matching and substitution.

    The C{RegexpChunkRule} class and its subclasses (C{ChunkRule},
    C{ChinkRule}, C{UnChunkRule}, C{MergeRule}, and C{SplitRule})
    define the rules that are used by C{RegexpChunk}.  Each rule
    defines an C{apply} method, which modifies the chunking encoded
    by a given C{ChunkString}.

    @type _rules: C{list} of C{RegexpChunkRule}
    @ivar _rules: The list of rules that should be applied to a text.
    @type _trace: C{int}
    @ivar _trace: The default level of tracing.
        
    """
    def __init__(self, rules, chunk_node='CHUNK', top_node='TEXT', trace=0):
        """
        Construct a new C{RegexpChunk}.
        
        @type rules: C{list} of C{RegexpChunkRule}
        @param rules: The sequence of rules that should be used to
            generate the chunking for a tagged text.
        @type chunk_node: C{string}
        @param chunk_node: The node value that should be used for
            chunk subtrees.  This is typically a short string
            describing the type of information contained by the chunk,
            such as C{"NP"} for base noun phrases.
        @type top_node: C{string}
        @param top_node: The node value that should be used for the
            top node of the chunk structure.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            higher will generate verbose tracing output.
        """
        self._rules = rules
        self._trace = trace
        self._chunk_node = chunk_node
        self._top_node = top_node
        AbstractParse.__init__(self)

    def _trace_apply(self, chunkstr, verbose):
        """
        Apply each of this C{RegexpChunk}'s rules to C{chunkstr}, in
        turn.  Generate trace output between each rule.  If C{verbose}
        is true, then generate verbose output.

        @type chunkstr: C{ChunkString}
        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type verbose: C{boolean}
        @param verbose: Whether output should be verbose.
        @rtype: C{None}
        """
        print '# Input:'
        print chunkstr
        for rule in self._rules:
            rule.apply(chunkstr)
            if verbose:
                print '#', rule.descr()+' ('+`rule`+'):'
            else:
                print '#', rule.descr()+':'
            print chunkstr
        
    def _notrace_apply(self, chunkstr):
        """
        Apply each of this C{RegexpChunk}'s rules to C{chunkstr}, in
        turn.

        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type chunkstr: C{ChunkString}
        @rtype: C{None}
        """
        
        for rule in self._rules:
            rule.apply(chunkstr)
        
    def parse(self, tokens, trace=None):
        """
        @type chunk_struct: C{Tree}
        @param chunk_struct: the chunk structure to be (further) chunked
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor. 
        @rtype: C{Tree}
        @return: a chunk structure that encodes the chunks in a given
            tagged sentence.  A chunk is a non-overlapping linguistic
            group, such as a noun phrase.  The set of chunks
            identified in the chunk structure depends on the rules
            used to define this C{RegexpChunk}.
        """
        if len(tokens) == 0:
            print 'Warning: parsing empty text'
            return Tree(self._top_node, [])
        
        # Use the default trace value?
        if trace == None: trace = self._trace

        chunkstr = ChunkString(tokens)

        # Apply the sequence of rules to the chunkstring.
        if trace:
            verbose = (trace>1)
            self._trace_apply(chunkstr, verbose)
        else:
            self._notrace_apply(chunkstr)

        # Use the chunkstring to create a chunk structure.
        return chunkstr.to_chunkstruct(self._chunk_node)

    def rules(self):
        """
        @return: the sequence of rules used by C{RegexpChunk}.
        @rtype: C{list} of C{RegexpChunkRule}
        """
        return self._rules

    def __repr__(self):
        """
        @return: a concise string representation of this
            C{RegexpChunk}.
        @rtype: C{string}
        """
        return "<RegexpChunk with %d rules>" % len(self._rules)

    def __str__(self):
        """
        @return: a verbose string representation of this
            C{RegexpChunk}.
        @rtype: C{string}
        """
        s = "RegexpChunk with %d rules:\n" % len(self._rules)
        margin = 0
        for rule in self._rules:
            margin = max(margin, len(rule.descr()))
        if margin < 35:
            format = "    %" + `-(margin+3)` + "s%s\n"
        else:
            format = "    %s\n      %s\n"
        for rule in self._rules:
            s += format % (rule.descr(), `rule`)
        return s[:-1]
            
##//////////////////////////////////////////////////////
##  Chunk Grammar
##//////////////////////////////////////////////////////

class Regexp(ChunkParseI, AbstractParse):
    """
    A grammar based chunk parser.  C{chunk.Regexp} uses a set of
    regular expression patterns to specify the behavior of the parser.
    The chunking of the text is encoded using a C{ChunkString}, and
    each rule acts by modifying the chunking in the C{ChunkString}.
    The rules are all implemented using regular expression matching
    and substitution.

    A grammar contains one or more clauses in the following form:

    NP:
      {<DT|JJ>}          # chunk determiners and adjectives
      }<[\.VI].*>+{      # chink any tag beginning with V, I, or .
      <.*>}{<DT>         # split a chunk at a determiner
      <DT|JJ>{}<NN.*>    # merge chunk ending with det/adj with one starting with a noun

    The patterns of a clause are executed in order.  An earlier
    pattern may introduce a chunk boundary that prevents a later
    pattern from executing.  Sometimes an individual pattern will
    match on multiple, overlapping extents of the input.  As with
    regular expression substitution more generally, the chunker will
    identify the first match possible, then continue looking for matches
    after this one has ended.

    The clauses of a grammar are also executed in order.  A cascaded
    chunk parser is one having more than one clause.  The maximum depth
    of a parse tree created by this chunk parser is the same as the
    number of clauses in the grammar.

    When tracing is turned on, the comment portion of a line is displayed
    each time the corresponding pattern is applied.

    @type _start: C{string}
    @ivar _start: The start symbol of the grammar (the root node of resulting trees)
    @type _stages: C{int}
    @ivar _stages: The list of parsing stages corresponding to the grammar
        
    """
    def __init__(self, start, grammar, trace=0):
        """
        Create a new chunk parser, from the given start state
        and set of chunk patterns.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param grammar: The list of patterns that defines the grammar
        @type grammar: C{list} of C{string}
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            higher will generate verbose tracing output.
        """
        from nltk_lite import chunk
        self._start = start
        self._trace = trace
	self._stages = []
        self._grammar = grammar
	rules = []
        for line in grammar.split('\n'):
            # Process any comments
            line = re.sub(r'\\#', r'_HASH_', line)
            if '#' in line:
                line, comment = line.split('#')
            else:
                comment = ''
            line = re.sub(r'_HASH_', r'\\#', line)
            comment = comment.strip()

            # New stage begins
            if ':' in line:
	        if rules != []:
                    parser = RegexpChunk(rules, chunk_node=lhs, trace=trace)
                    self._stages.append(parser)
                lhs, line = line.split(":")
                lhs = lhs.strip()
	        rules = []

            line = line.strip()
            if not line: continue

            # Pattern bodies: chunk, chink, split, merge
            if line[0] == '{' and line[-1] == '}':
	        rules.append(ChunkRule(line[1:-1], comment))
            elif line[0] == '}' and line[-1] == '{':
	        rules.append(ChinkRule(line[1:-1], comment))
            elif '}{' in line:
	        left, right = line.split('}{')
	        rules.append(SplitRule(left, right, comment))
            elif '{}' in line:
	        left, right = line.split('{}')
	        rules.append(MergeRule(left, right, comment))
	    else:
	        raise ValueError, 'Illegal chunk pattern: %s' % line
        if rules != []:
            parser = RegexpChunk(rules, chunk_node=lhs, trace=trace)
            self._stages.append(parser)

    def parse(self, chunk_struct, trace=None):
        """
        Apply the chunk parser to this input.
        
        @type chunk_struct: C{Tree}
        @param chunk_struct: the chunk structure to be (further) chunked
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor. 
        """
        if trace == None: trace = self._trace
        for parser in self._stages:
            chunk_struct = parser.parse(chunk_struct, trace=trace)
        return chunk_struct

    def __repr__(self):
        """
        @return: a concise string representation of this C{chunk.Regexp}.
        @rtype: C{string}
        """
        return "<chunk.Regexp with %d stages>" % len(self._stages)

    def __str__(self):
        """
        @return: a verbose string representation of this
            C{RegexpChunk}.
        @rtype: C{string}
        """
        s = "chunk.Regexp with %d stages:\n" % len(self._stages)
        margin = 0
        for parser in self._stages:
            s += parser.__str__() + "\n"
        return s[:-1]

##//////////////////////////////////////////////////////
##  Demonstration code
##//////////////////////////////////////////////////////

def demo_eval(chunkparser, text):
    """
    Demonstration code for evaluating a chunk parser, using a
    C{ChunkScore}.  This function assumes that C{text} contains one
    sentence per line, and that each sentence has the form expected by
    C{tree.chunk}.  It runs the given chunk parser on each sentence in
    the text, and scores the result.  It prints the final score
    (precision, recall, and f-measure); and reports the set of chunks
    that were missed and the set of chunks that were incorrect.  (At
    most 10 missing chunks and 10 incorrect chunks are reported).

    @param chunkparser: The chunkparser to be tested
    @type chunkparser: C{ChunkParseI}
    @param text: The chunked tagged text that should be used for
        evaluation.
    @type text: C{string}
    """
    
    # Evaluate our chunk parser.
    chunkscore = ChunkScore()

    from nltk_lite.parse import tree
    
    for sentence in text.split('\n'):
        print sentence
        sentence = sentence.strip()
        if not sentence: continue
        gold = tree.chunk(sentence)
        tokens = gold.leaves()
        test = chunkparser.parse(tree.Tree('S', tokens), trace=1)
        chunkscore.score(gold, test)
        print

    print '/'+('='*75)+'\\'
    print 'Scoring', chunkparser
    print ('-'*77)
    print 'Precision: %5.1f%%' % (chunkscore.precision()*100), ' '*4,
    print 'Recall: %5.1f%%' % (chunkscore.recall()*100), ' '*6,
    print 'F-Measure: %5.1f%%' % (chunkscore.f_measure()*100)
    

    # Missed chunks.
    if chunkscore.missed():
        print 'Missed:'
        missed = chunkscore.missed()
        for chunk in missed[:10]:
            print '  ', chunk
        if len(chunkscore.missed()) > 10:
               print '  ...'

    # Incorrect chunks.
    if chunkscore.incorrect():
        print 'Incorrect:'
        incorrect = chunkscore.incorrect()
        for chunk in incorrect[:10]:
            print '  ', chunk
        if len(chunkscore.incorrect()) > 10:
               print '  ...'
    
    print '\\'+('='*75)+'/'
    print

def demo():
    """
    A demonstration for the C{RegexpChunk} class.  A single text is
    parsed with four different chunk parsers, using a variety of rules
    and strategies.
    """

    from nltk_lite import chunk
    from nltk_lite.tag import string2tags
    from nltk_lite.parse.tree import Tree

    text = """\
    [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
    [ John/NNP ] saw/VBD [the/DT cats/NNS] [the/DT dog/NN] chased/VBD ./.
    [ John/NNP ] thinks/VBZ [ Mary/NN ] saw/VBD [ the/DT cat/NN ] sit/VB on/IN [ the/DT mat/NN ]./.
    """

    print '*'*75
    print 'Evaluation text:'
    print text
    print '*'*75
    print

    grammar = r"""
    NP:                   # NP stage
      {<DT>?<JJ>*<NN>}    # chunk determiners, adjectives and nouns
      {<NNP>+}            # chunk proper nouns
    """
    cp = chunk.Regexp('S', grammar)
    chunk.demo_eval(cp, text)

    grammar = r"""
    NP:
      {<.*>}              # start by chunking each tag
      }<[\.VI].*>+{       # unchunk any verbs, prepositions or periods
      <DT|JJ>{}<NN.*>     # merge det/adj with nouns
    """
    cp = chunk.Regexp('S', grammar)
    chunk.demo_eval(cp, text)

    grammar = r"""
    NP: {<DT>?<JJ>*<NN>}    # chunk determiners, adjectives and nouns
    VP: {<TO>?<VB.*>}       # VP = verb words
    """
    cp = chunk.Regexp('S', grammar)
    chunk.demo_eval(cp, text)

    grammar = r"""
    NP: {<.*>*}             # start by chunking everything
        }<[\.VI].*>+{       # chink any verbs, prepositions or periods
        <.*>}{<DT>          # separate on determiners
    PP: {<IN><NP>}          # PP = preposition + noun phrase
    VP: {<VB.*><NP|PP>*}    # VP = verb words + NPs and PPs
    """
    cp = chunk.Regexp('S', grammar)
    chunk.demo_eval(cp, text)

# Evaluation

    from nltk_lite.corpora import conll2000

    print
    print "Demonstration of empty grammar:"
    
    cp = chunk.Regexp('S', "")
    print chunk.accuracy(cp, conll2000.chunked(files='test', chunk_types=('NP',)))

    print
    print "Demonstration of accuracy evaluation using CoNLL tags:"

    from itertools import islice

    grammar = r"""
    NP:
      {<.*>}              # start by chunking each tag
      }<[\.VI].*>+{       # unchunk any verbs, prepositions or periods
      <DT|JJ>{}<NN.*>     # merge det/adj with nouns
    """
    cp = chunk.Regexp('S', grammar)
    print chunk.accuracy(cp, islice(conll2000.chunked(chunk_types=('NP', 'PP', 'VP')), 0, 5))

if __name__ == '__main__':
    demo()

