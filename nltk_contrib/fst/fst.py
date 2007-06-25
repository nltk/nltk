"""
Finite state transducers.

A finite state trasducer, or FST, is a directed graph that is used to
encode a mapping from a set of I{input strings} to a set of I{output
strings}.  An X{input string} is a sequence of immutable values (such
as integers, characters, or strings) called X{input symbols}.
Similarly, an C{output string} is a sequence of immutable values
called X{output symbols}.  Collectively, input strings and output
strings are called X{symbol strings}, or simply X{strings} for short.
Note that this notion of I{string} is different from the python string
type -- symbol strings are always encoded as tuples of input or output
symbols, even if those symbols are characters.  Also, note that empty
sequences are valid symbol strings.

The nodes of an FST are called X{states}, and the edges are called
X{transition arcs} or simply X{arcs}.  States may be marked as
X{final}, and each final state is annotated with an output string,
called the X{finalizing string}.  Each arc is annotated with an input
string and an output string.  An arc with an empty input string is
called an I{epsilon-input arc}; and an arc with an empty output
string is called an I{epsilon-output arc}.

The set of mappings encoded by the FST are defined by the set of paths
through the graph, starting at a special state known as the X{initial
state}, and ending at a final state.  In particular, the FST maps an
input string X to an output string Y iff there exists a path from the
initial state to a final state such that:

  - The input string X is formed by concatenating the input strings
    of the arcs along the path (in order).
  - The output string Y is formed by concatenating the output strings
    of the arcs along the path (in order), plus the final state's
    output string.

The following list defines some terms that apply to finite state
transducers.

  - The X{transduction} defined by a FST is the mapping from input
    strings to output strings.
    
  - An FST X{encodes a deterministic transduction} if each input
    string maps to at most one output string.  An FST X{encodes a
    nondeterministic transduction} if any input string maps to more
    than one output string.

  - An FST is X{deterministic} if it every state contains at most one
    outgoing arc that is consistent with any input string; otherwise,
    the FST is X{nondeterministic}.  If an FST is deterministic, then
    it necessarily encodes a deterministic transduction; however, it
    is possible to define an FST that is nondeterministic but that
    encodes a deterministic transduction.

  - An FST is X{sequential} if each arc is labeled with exactly one
    input symbol, no two outgoing arcs from any state have the same
    input symbol, and all finalizing strings are empty.  (Sequential
    implies deterministic).

  - An FST is I{subsequential} if each arc is labeled with exactly
    one input symbol, and no two outgoing arcs from any state have
    the same input symbol.  (Finalizing strings may be non-empty.)

An FSA can be represented as an FST that generates no output symbols.

The current FST class does not provide support for:

  - Weighted arcs.  (However, weights can be used as, or included
    in, the output symbols.  The total weight of a path can then
    be found after transduction by combining the weights.  But
    there's no support for e.g., finding the path with the minimum
    weight.
    
  - Multiple initial states.
  
  - Initializing strings (an output string associated with the initial
    state, which is always generated when the FST begins).

Possible future changes:

  - Define several classes, in a class hierarchy?  E.g., FSA is a base
    class, FST inherits from it.  And maybe a further subclass to add
    finalizing sequences.  I would need to be more careful to only
    access the private variables when necessary, and to usually go
    through the accessor functions.
"""

import re, os, random, tempfile
from subprocess import Popen, PIPE
from nltk.draw import *
from nltk_contrib.fst.draw_graph import *

######################################################################
# CONTENTS
######################################################################
# 1. Finite State Transducer
#    - State information
#    - Transition Arc Information
#    - FST Information
#    - State Modification
#    - Transition Arc Modification
#    - Transformations
#    - Misc
#    - Transduction
# 2. AT&T fsmtools support
# 3. Graphical Display
#    - FSTDisplay
#    - FSTDemo
######################################################################

######################################################################
#{ Finite State Transducer
######################################################################

class FST(object):
    """
    A finite state transducer.  Each state is uniquely identified by a
    label, which is typically a string name or an integer id.  A
    state's label is used to access and modify the state.  Similarly,
    each arc is uniquely identified by a label, which is used to
    access and modify the arc.

    The set of arcs pointing away from a state are that state's
    I{outgoing} arcs.  The set of arcs pointing to a state are that
    state's I{incoming} arcs.  The state at which an arc originates is
    that arc's I{source} state (or C{src}), and the state at which it
    terminates is its I{destination} state (or C{dst}).

    It is possible to define an C{FST} object with no initial state.
    This is represented by assigning a value of C{None} to the
    C{initial_state} variable.  C{FST}s with no initial state are
    considered to encode an empty mapping.  I.e., transducing any
    string with such an C{FST} will result in failure.
    """
    def __init__(self, label):
        """
        Create a new finite state transducer, containing no states.
        """
        self.label = label
        """A label identifying this FST.  This is used for display &
        debugging purposes only."""

        #{ State Information
        self._initial_state = None
        """The label of the initial state, or C{None} if this FST
        does not have an initial state."""
        
        self._incoming = {}
        """A dictionary mapping state labels to lists of incoming
        transition arc labels."""

        self._outgoing = {}
        """A dictionary mapping state labels to lists of outgoing
        transition arc labels."""

        self._is_final = {}
        """A dictionary mapping state labels to boolean values,
        indicating whether the state is final."""

        self._finalizing_string = {}
        """A dictionary mapping state labels of final states to output
        strings.  This string should be added to the output
        if the FST terminates at this state."""

        self._state_descr = {}
        """A dictionary mapping state labels to (optional) state
        descriptions."""
        #}

        #{ Transition Arc Information
        self._src = {}
        """A dictionary mapping each transition arc label to the label of
        its source state."""

        self._dst = {}
        """A dictionary mapping each transition arc label to the label of
        its destination state."""

        self._in_string = {}
        """A dictionary mapping each transition arc label to its input
        string, a (possibly empty) tuple of input symbols."""

        self._out_string = {}
        """A dictionary mapping each transition arc label to its output
        string, a (possibly empty) tuple of input symbols."""

        self._arc_descr = {}
        """A dictionary mapping transition arc labels to (optional)
        arc descriptions."""
        #}
        
    #////////////////////////////////////////////////////////////
    #{ State Information
    #////////////////////////////////////////////////////////////

    def states(self):
        """Return an iterator that will generate the state label of
        each state in this FST."""
        return iter(self._incoming)

    def has_state(self, label):
        """Return true if this FST contains a state with the given
        label."""
        return label in self._incoming

    def _get_initial_state(self):
        return self._initial_state
    def _set_initial_state(self, label):
        if label is not None and label not in self._incoming:
            raise ValueError('Unknown state label %r' % label)
        self._initial_state = label
    initial_state = property(_get_initial_state, _set_initial_state,
                             doc="The label of the initial state (R/W).")

    def incoming(self, state):
        """Return an iterator that will generate the incoming
        transition arcs for the given state.  The effects of modifying
        the FST's state while iterating are undefined, so if you plan
        to modify the state, you should copy the incoming transition
        arcs into a list first."""
        return iter(self._incoming[state])

    def outgoing(self, state):
        """Return an iterator that will generate the outgoing
        transition arcs for the given state.  The effects of modifying
        the FST's state while iterating are undefined, so if you plan
        to modify the state, you should copy the outgoing transition
        arcs into a list first."""
        return iter(self._outgoing[state])

    def is_final(self, state):
        """Return true if the state with the given state label is
        final."""
        return self._is_final[state]

    def finalizing_string(self, state):
        """Return the output string associated with the given final
        state.  If the FST terminates at this state, then this string
        will be emitted."""
        #if not self._is_final[state]:
        #    raise ValueError('%s is not a final state' % state)
        return self._finalizing_string.get(state, ())

    def state_descr(self, state):
        """Return the description for the given state, if it has one;
        or None, otherwise."""
        return self._state_descr.get(state)

    #////////////////////////////////////////////////////////////
    #{ Transition Arc Information
    #////////////////////////////////////////////////////////////

    def arcs(self):
        """Return an iterator that will generate the arc label of
        each transition arc in this FST."""
        return iter(self._src)

    def src(self, arc):
        """Return the state label of this transition arc's source
        state."""
        return self._src[arc]

    def dst(self, arc):
        """Return the state label of this transition arc's destination
        state."""
        return self._dst[arc]

    def in_string(self, arc):
        """Return the given transition arc's input string, a (possibly
        empty) tuple of input symbols."""
        return self._in_string[arc]
    
    def out_string(self, arc):
        """Return the given transition arc's output string, a
        (possibly empty) tuple of output symbols."""
        return self._out_string[arc]
    
    def arc_descr(self, arc):
        """Return the description for the given transition arc, if it
        has one; or None, otherwise."""
        return self._arc_descr.get(arc)

    def arc_info(self, arc):
        """Return a tuple (src, dst, in_string, out_string) for the
        given arc, where:
          - C{src} is the label of the arc's source state.
          - C{dst} is the label of the arc's destination state.
          - C{in_string} is the arc's input string.
          - C{out_string} is the arc's output string.
        """
        return (self._src[arc], self._dst[arc],
                self._in_string[arc], self._out_string[arc])

    #////////////////////////////////////////////////////////////
    #{ FST Information
    #////////////////////////////////////////////////////////////

    def is_sequential(self):
        """
        Return true if this FST is sequential.
        """
        for state in self.states():
            if self.finalizing_string(state): return False
        return self.is_subsequential()

    def is_subsequential(self):
        """
        Return true if this FST is subsequential.
        """
        for state in self.states():
            out_syms = set()
            for arc in self.outgoing(state):
                out_string = self.out_string(arc)
                if len(out_string) != 1: return False
                if out_string[0] in out_syms: return False
                out_syms.add(out_string)
        return True

    #////////////////////////////////////////////////////////////
    #{ State Modification
    #////////////////////////////////////////////////////////////

    def add_state(self, label=None, is_final=False,
                  finalizing_string=(), descr=None):
        """
        Create a new state, and return its label.  The new state will
        have no incoming or outgoing arcs.  If C{label} is specified,
        then it will be used as the state's label; otherwise, a new
        unique label value will be chosen.  The new state will be
        final iff C{is_final} is true.  C{descr} is an optional
        description string for the new state.
        
        Arguments should be specified using keywords!
        """
        label = self._pick_label(label, 'state', self._incoming)
        
        # Add the state.
        self._incoming[label] = []
        self._outgoing[label] = []
        self._is_final[label] = is_final
        self._state_descr[label] = descr
        self._finalizing_string[label] = tuple(finalizing_string)
        
        # Return the new state's label.
        return label

    def del_state(self, label):
        """
        Delete the state with the given label.  This will
        automatically delete any incoming or outgoing arcs attached to
        the state.
        """
        if label not in self._incoming:
            raise ValueError('Unknown state label %r' % label)

        # Delete the incoming/outgoing arcs.
        for arc in self._incoming[label]:
            del (self._src[arc], self._dst[arc], self._in_string[arc],
                 self._out_string[arc], self._arc_descr[arc])
        for arc in self._outgoing[label]:
            del (self._src[arc], self._dst[arc], self._in_string[arc],
                 self._out_string[arc], self._arc_descr[arc])

        # Delete the state itself.
        del (self._incoming[label], self._otugoing[label],
             self._is_final[label], self._state_descr[label],
             self._finalizing_string[label])

        # Check if we just deleted the initial state.
        if label == self._initial_state:
            self._initial_state = None

    def set_final(self, state, is_final=True):
        """
        If C{is_final} is true, then make the state with the given
        label final; if C{is_final} is false, then make the state with
        the given label non-final.
        """
        if state not in self._incoming:
            raise ValueError('Unknown state label %r' % state)
        self._is_final[state] = is_final

    def set_finalizing_string(self, state, finalizing_string):
        """
        Set the given state's finalizing string.
        """
        if not self._is_final[state]:
            raise ValueError('%s is not a final state' % state)
        if state not in self._incoming:
            raise ValueError('Unknown state label %r' % state)
        self._finalizing_string[state] = tuple(finalizing_string)

    def set_descr(self, state, descr):
        """
        Set the given state's description string.
        """
        if state not in self._incoming:
            raise ValueError('Unknown state label %r' % state)
        self._state_descr[state] = descr

    def dup_state(self, orig_state, label=None):
        """
        Duplicate an existing state.  I.e., create a new state M{s}
        such that:
          - M{s} is final iff C{orig_state} is final.
          - If C{orig_state} is final, then M{s.finalizing_string}
            is copied from C{orig_state}
          - For each outgoing arc from C{orig_state}, M{s} has an
            outgoing arc with the same input string, output
            string, and destination state.

        Note that if C{orig_state} contained self-loop arcs, then the
        corresponding arcs in M{s} will point to C{orig_state} (i.e.,
        they will I{not} be self-loop arcs).

        The state description is I{not} copied.
            
        @param label: The label for the new state.  If not specified,
            a unique integer will be used.
        """
        if orig_state not in self._incoming: 
            raise ValueError('Unknown state label %r' % src)
        
        # Create a new state.
        new_state = self.add_state(label=label)

        # Copy finalization info.
        if self.is_final(orig_state):
            self.set_final(new_state)
            self.set_finalizing_string(new_state,
                                       self.finalizing_string(orig_state))

        # Copy the outgoing arcs.
        for arc in self._outgoing[orig_state]:
            self.add_arc(src=new_state, dst=self._dst[arc],
                         in_string=self._in_string[arc],
                         out_string=self._out_string[arc])

        return new_state

    #////////////////////////////////////////////////////////////
    #{ Transition Arc Modification
    #////////////////////////////////////////////////////////////

    def add_arc(self, src, dst, in_string, out_string,
                label=None, descr=None):
        """
        Create a new transition arc, and return its label.

        Arguments should be specified using keywords!
        
        @param src: The label of the source state.
        @param dst: The label of the destination state.
        @param in_string: The input string, a (possibly empty) tuple of
            input symbols.  Input symbols should be hashable
            immutable objects.
        @param out_string: The output string, a (possibly empty) tuple
            of output symbols.  Output symbols should be hashable
            immutable objects.
        """
        label = self._pick_label(label, 'arc', self._src)

        # Check that src/dst are valid labels.
        if src not in self._incoming:
            raise ValueError('Unknown state label %r' % src)
        if dst not in self._incoming:
            raise ValueError('Unknown state label %r' % dst)

        # Add the arc.
        self._src[label] = src
        self._dst[label] = dst
        self._in_string[label] = tuple(in_string)
        self._out_string[label] = tuple(out_string)
        self._arc_descr[label] = descr

        # Link the arc to its src/dst states.
        self._incoming[dst].append(label)
        self._outgoing[src].append(label)

        # Return the new arc's label.
        return label
            
    def del_arc(self, label):
        """
        Delete the transition arc with the given label.
        """
        if label not in self._src:
            raise ValueError('Unknown arc label %r' % src)

        # Disconnect the arc from its src/dst states.
        self._incoming[self._dst[label]].remove(label)
        self._outgoing[self._src[label]].remove(label)

        # Delete the arc itself.
        del (self._src[label], self._dst[label], self._in_string[label],
             self._out_string[label], self._arc_descr[label])

    #////////////////////////////////////////////////////////////
    #{ Transformations
    #////////////////////////////////////////////////////////////

    def inverted(self):
        """Swap all in_string/out_string pairs."""
        fst = self.copy()
        fst._in_string, fst._out_string = fst._out_string, fst._in_string
        return fst

    def reversed(self):
        """Reverse the direction of all transition arcs."""
        fst = self.copy()
        fst._incoming, fst._outgoing = fst._outgoing, fst._incoming
        fst._src, fst._dst = fst._dst, fst._src
        return fst

    def trimmed(self):
        fst = self.copy()
        
        if fst.initial_state is None:
            raise ValueError("No initial state!")

        # Determine whether there is a path from the initial node to
        # each node.
        queue = [fst.initial_state]
        path_from_init = set(queue)
        while queue:
            state = queue.pop()
            dsts = [fst.dst(arc) for arc in fst.outgoing(state)]
            queue += [s for s in dsts if s not in path_from_init]
            path_from_init.update(dsts)

        # Determine whether there is a path from each node to a final
        # node.
        queue = [s for s in fst.states() if fst.is_final(s)]
        path_to_final = set(queue)
        while queue:
            state = queue.pop()
            srcs = [fst.src(arc) for arc in fst.incoming(state)]
            queue += [s for s in srcs if s not in path_to_final]
            path_to_final.update(srcs)

        # Delete anything that's not on a path from the initial state
        # to a final state.
        for state in list(fst.states()):
            if not (state in path_from_init and state in path_to_final):
                fst.del_state(state)

        return fst
    
    def relabeled(self, label=None, relabel_states=True, relabel_arcs=True):
        """
        Return a new FST that is identical to this FST, except that
        all state and arc labels have been replaced with new labels.
        These new labels are consecutive integers, starting with zero.

        @param relabel_states: If false, then don't relabel the states.
        @param relabel_arcs: If false, then don't relabel the arcs.
        """
        if label is None: label = '%s (relabeled)' % self.label
        fst = FST(label)

        # This will ensure that the state relabelling is canonical, *if*
        # the FST is subsequential.
        state_ids = self._relabel_state_ids(self.initial_state, {})
        if len(state_ids) < len(self._outgoing):
            for state in self.states():
                if state not in state_ids:
                    state_ids[state] = len(state_ids)

        # This will ensure that the arc relabelling is canonical, *if*
        # the state labelling is canonical.
        arcs = sorted(self.arcs(), key=self.arc_info)
        arc_ids = dict([(a,i) for (i,a) in enumerate(arcs)])

        for state in self.states():
            if relabel_states: label = state_ids[state]
            else: label = state
            fst.add_state(label, is_final=self.is_final(state),
                          finalizing_string=self.finalizing_string(state),
                          descr=self.state_descr(state))

        for arc in self.arcs():
            if relabel_arcs: label = arc_ids[arc]
            else: label = arc
            src, dst, in_string, out_string = self.arc_info(arc)
            if relabel_states:
                src = state_ids[src]
                dst = state_ids[dst]
            fst.add_arc(src=src, dst=dst, in_string=in_string,
                        out_string=out_string,
                        label=label, descr=self.arc_descr(arc))

        if relabel_states:
            fst.initial_state = state_ids[self.initial_state]
        else:
            fst.initial_state = self.initial_state
            
        return fst

    def _relabel_state_ids(self, state, ids):
        """
        A helper function for L{relabel()}, which decides which new
        label should be assigned to each state.
        """
        if state in ids: return
        ids[state] = len(ids)
        for arc in sorted(self.outgoing(state),
                          key = lambda a:self.in_string(a)):
            self._relabel_state_ids(self.dst(arc), ids)
        return ids

    def determinized(self, label=None):
        """
        Return a new FST which defines the same mapping as this FST,
        but is determinized.

        The algorithm used is based on [...].

        @require: All arcs in this FST must have exactly one input
            symbol.
        @require: The mapping defined by this FST must be
            deterministic.
        @raise ValueError: If the determinization algorithm was unable
            to determinize this FST.  Typically, this happens because
            a precondition is not met.
        """
        # Check preconditions..
        for arc in self.arcs():
            if len(self.in_string(arc)) != 1:
                raise ValueError("All arcs must have exactly one "
                                 "input symbol.")
        
        # State labels have the form:
        #   frozenset((s1,w1),(s2,w2),...(sn,wn))
        # Where si is a state and wi is a string of output symbols.
        if label is None: label = '%s (determinized)' % self.label
        new_fst = FST(label)

        initial_state = frozenset( [(self.initial_state,())] )
        new_fst.add_state(initial_state)
        new_fst.initial_state = initial_state
                          
        queue = [initial_state]
        while queue:
            new_fst_state = queue.pop()

            # For each final state from the original FSM that's
            # contained in the new FST's state, compute the finalizing
            # string.  If there is at least one finalizing string,
            # then the new state is a final state.  However, if the
            # finalizing strings are not all identical, then the
            # transduction defined by this FST is nondeterministic, so
            # fail.
            finalizing_strings = [w+self.finalizing_string(s)
                                  for (s,w) in new_fst_state
                                  if self.is_final(s)]
            if len(set(finalizing_strings)) > 0:
                if not self._all_equal(finalizing_strings):
                    # multiple conflicting finalizing strings -> bad!
                    raise ValueError("Determinization failed")
                new_fst.set_final(new_fst_state)
                new_fst.set_finalizing_string(new_fst_state,
                                              finalizing_strings[0])

            # sym -> dst -> [residual]
            # nb: we checked above that len(in_string)==1 for all arcs.
            arc_table = {}
            for (s,w) in new_fst_state:
                for arc in self.outgoing(s):
                    sym = self.in_string(arc)[0]
                    dst = self.dst(arc)
                    residual = w + self.out_string(arc)
                    arc_table.setdefault(sym,{}).setdefault(dst,set())
                    arc_table[sym][dst].add(residual)

            # For each symbol in the arc table, we need to create a
            # single edge in the new FST.  This edge's input string
            # will be the input symbol; its output string will be the
            # shortest common prefix of strings that can be generated
            # by the original FST in response to the symbol; and its
            # destination state will encode the set of states that the
            # original FST can go to when it sees this symbol, paired
            # with the residual output strings that would have been
            # generated by the original FST, but have not yet been
            # generated by the new FST.
            for sym in arc_table:
                for dst in arc_table[sym]:
                    if len(arc_table[sym][dst]) > 1:
                        # two arcs w/ the same src, dst, and insym,
                        # but different residuals -> bad!
                        raise ValueError("Determinization failed")

                # Construct a list of (destination, residual) pairs.
                dst_residual_pairs = [(dst, arc_table[sym][dst].pop())
                                     for dst in arc_table[sym]]

                # Find the longest common prefix of all the residuals.
                # Note that it's ok if some of the residuals disagree,
                # but *only* if the states associated with those
                # residuals can never both reach a final state with a
                # single input string.
                residuals = [res for (dst, res) in dst_residual_pairs]
                prefix = self._common_prefix(residuals)

                # Construct the new arc's destination state.  The new
                # arc's output string will be `prefix`, so the new
                # destination state should be the set of all pairs
                # (dst, residual-prefix).
                new_arc_dst = frozenset([(dst, res[len(prefix):]) 
                                         for (dst,res) in dst_residual_pairs])

                # If the new arc's destination state isn't part of
                # the FST yet, then add it; and add it to the queue.
                if not new_fst.has_state(new_arc_dst):
                    new_fst.add_state(new_arc_dst)
                    queue.append(new_arc_dst)

                # Create the new arc.
                new_fst.add_arc(src=new_fst_state, dst=new_arc_dst,
                                in_string=(sym,), out_string=prefix)
        return new_fst

    def _all_equal(self, lst):
        """Return true if all elements in the list are equal"""
        for item in lst[1:]:
            if item != lst[0]: return False
        return True

    def _common_prefix(self, sequences):
        """Return the longest sequence that is a prefix of all of the
        given sequences."""
        prefix = sequences[0]
        for seq in sequences[1:]:
            # If the sequence is longer then the prefix, then truncate
            # the prefix to the length of the sequence.
            prefix = prefix[:len(seq)]
            # If the prefix doesn't match item i of the sequence, then
            # truncate the prefix to include everything up to (but not
            # including) element i.
            for i in range(len(prefix)):
                if seq[i] != prefix[i]:
                    prefix = prefix[:i]
                    break
        return prefix

    #////////////////////////////////////////////////////////////
    #{ Misc
    #////////////////////////////////////////////////////////////

    def copy(self, label=None):
        # Choose a label & create the FST.
        if label is None: label = '%s-copy' % self.label
        fst = FST(label)

        # Copy all state:
        fst._initial_state = self._initial_state
        fst._incoming = self._incoming.copy()
        fst._outgoing = self._outgoing.copy()
        fst._is_final = self._is_final.copy()
        fst._finalizing_string = self._finalizing_string.copy()
        fst._state_descr = self._state_descr.copy()
        fst._src = self._src.copy()
        fst._dst = self._dst.copy()
        fst._in_string = self._in_string.copy()
        fst._out_string = self._out_string.copy()
        fst._arc_descr = self._arc_descr.copy()
        return fst

    def __str__(self):
        lines = ['FST %s' % self.label]
        for state in sorted(self.states()):
            # State information.
            if state == self.initial_state:
                line = '-> %s' % state
                lines.append('  %-40s # Initial state' % line)
            if self.is_final(state):
                line = '%s ->' % state
                if self.finalizing_string(state):
                    line += ' [%s]' % ' '.join(self.finalizing_string(state))
                lines.append('  %-40s # Final state' % line)
            # List states that would otherwise not be listed.
            if (state != self.initial_state and not self.is_final(state)
                and not self.outgoing(state) and not self.incoming(state)):
                lines.append('  %-40s # State' % state)
        # Outgoing edge information.
        for arc in sorted(self.arcs()):
            src, dst, in_string, out_string = self.arc_info(arc)
            line = ('%s -> %s [%s:%s]' %
                    (src, dst, ' '.join(in_string), ' '.join(out_string)))
            lines.append('  %-40s # Arc' % line)
        return '\n'.join(lines)
            
    @staticmethod
    def load(filename):
        label = os.path.split(filename)[-1]
        return FST.parse(label, open(filename).read())

    @staticmethod
    def parse(label, s):
        fst = FST(label)
        prev_src = None
        lines = s.split('\n')[::-1]
        while lines:
            line = lines.pop().split('#')[0].strip() # strip comments
            if not line: continue

            # Initial state
            m = re.match(r'->\s*(\S+)$', line)
            if m:
                label = m.group(1)
                if not fst.has_state(label): fst.add_state(label)
                fst.initial_state = label
                continue

            # Final state
            m = re.match('(\S+)\s*->\s*(?:\[([^\]]*)\])?$', line)
            if m:
                label, finalizing_string = m.groups()
                if not fst.has_state(label): fst.add_state(label)
                fst.set_final(label)
                if finalizing_string is not None:
                    finalizing_string = finalizing_string.split()
                    fst.set_finalizing_string(label, finalizing_string)
                continue

            # State
            m = re.match('(\S+)$', line)
            if m:
                label = m.group(1)
                if not fst.has_state(label): fst.add_state(label)
                continue

            # State description
            m = re.match(r'descr\s+(\S+?):\s*(.*)$', line)
            if m:
                label, descr = m.groups()
                # Allow for multi-line descriptions:
                while lines and re.match(r'\s+\S', lines[-1]):
                    descr = descr.rstrip()+' '+lines.pop().lstrip()
                if not fst.has_state(label): fst.add_state(label)
                fst.set_descr(label, descr)
                continue

            # Transition arc
            m = re.match(r'(\S+)?\s*->\s*(\S+)\s*'
                         r'\[(.*?):(.*?)\]$', line)
            if m:
                src, dst, in_string, out_string = m.groups()
                if src is None: src = prev_src
                if src is None: raise ValueError("bad line: %r" % line)
                prev_src = src
                if not fst.has_state(src): fst.add_state(src)
                if not fst.has_state(dst): fst.add_state(dst)
                in_string = tuple(in_string.split())
                out_string = tuple(out_string.split())
                fst.add_arc(src, dst, in_string, out_string)
                continue
    
            raise ValueError("bad line: %r" % line)
    
        return fst

    def dotgraph(self):
        """
        Return an AT&T graphviz dot graph.
        """
        # [xx] mark initial node??
        lines = ['digraph %r {' % self.label,
                 'node [shape=ellipse]']
        state_id = dict([(s,i) for (i,s) in enumerate(self.states())])
        if self.initial_state is not None:
            lines.append('init [shape="plaintext" label=""]')
            lines.append('init -> %s' % state_id[self.initial_state])
        for state in self.states():
            if self.is_final(state):
                final_str = self.finalizing_string(state)
                if len(final_str)>0:
                    lines.append('%s [label="%s\\n%s", shape=doublecircle]' %
                                 (state_id[state], state, ' '.join(final_str)))
                else:
                    lines.append('%s [label="%s", shape=doublecircle]' %
                                 (state_id[state], state))
            else:
                lines.append('%s [label="%s"]' % (state_id[state], state))
        for arc in self.arcs():
            src, dst, in_str, out_str = self.arc_info(arc)
            lines.append('%s -> %s [label="%s:%s"]' %
                         (state_id[src], state_id[dst],
                          ' '.join(in_str), ' '.join(out_str)))
        lines.append('}')
        return '\n'.join(lines)
    
    #////////////////////////////////////////////////////////////
    #{ Transduction
    #////////////////////////////////////////////////////////////

    def transduce_subsequential(self, input, step=True):
        return self.step_transduce_subsequential(input, step=False).next()[1]
    
    def step_transduce_subsequential(self, input, step=True):
        """
        This is implemented as a generator, to make it easier to
        support stepping.
        """
        if not self.is_subsequential():
            raise ValueError('FST is not subsequential!')

        # Create a transition table that indicates what action we
        # should take at any state for a given input symbol.  In
        # paritcular, this table maps from (src, in) tuples to
        # (dst, out, arc) tuples.  (arc is only needed in case
        # we want to do stepping.)
        transitions = {}
        for arc in self.arcs():
            src, dst, in_string, out_string = self.arc_info(arc)
            assert len(in_string) == 1
            assert (src, in_string[0]) not in transitions
            transitions[src, in_string[0]] = (dst, out_string, arc)

        output = []
        state = self.initial_state
        try:
            for in_pos, in_sym in enumerate(input):
                (state, out_string, arc) = transitions[state, in_sym]
                if step: yield 'step', (arc, in_pos, output)
                output += out_string
            yield 'succeed', output
        except KeyError:
            yield 'fail', None

    def transduce(self, input):
        return self.step_transduce(input, step=False).next()[1]

    def step_transduce(self, input, step=True):
        """
        This is implemented as a generator, to make it easier to
        support stepping.
        """
        input = tuple(input)
        output = []
        in_pos = 0

        # 'frontier' is a stack used to keep track of which parts of
        # the search space we have yet to examine.  Each element has
        # the form (arc, in_pos, out_pos), and indicates that we
        # should try rolling the input position back to in_pos, the
        # output position back to out_pos, and applying arc.  Note
        # that the order that we check elements in is important, since
        # rolling the output position back involves discarding
        # generated output.
        frontier = []

        # Start in the initial state, and search for a valid
        # transduction path to a final state.
        state = self.initial_state
        while in_pos < len(input) or not self.is_final(state):
            # Get a list of arcs we can possibly take.
            arcs = self.outgoing(state)
    
            # Add the arcs to our backtracking stack.  (The if condition
            # could be eliminated if I used eliminate_multi_input_arcs;
            # but I'd like to retain the ability to trace what's going on
            # in the FST, as its specified.)
            for arc in arcs:
                in_string = self.in_string(arc)
                if input[in_pos:in_pos+len(in_string)] == in_string:
                    frontier.append( (arc, in_pos, len(output)) )
    
            # Get the top element of the frontiering stack.
            if len(frontier) == 0:
                yield 'fail', None

            # perform the operation from the top of the frontier.
            arc, in_pos, out_pos = frontier.pop()
            if step:
                yield 'step', (arc, in_pos, output[:out_pos])
            
            # update our state, input position, & output.
            state = self.dst(arc)
            assert out_pos <= len(output)
            in_pos = in_pos + len(self.in_string(arc))
            output = output[:out_pos]
            output.extend(self.out_string(arc))

        # If it's a subsequential transducer, add the final output for
        # the terminal state.
        output += self.finalizing_string(state)
    
        yield 'succeed', output
        

    #////////////////////////////////////////////////////////////
    #{ Helper Functions
    #////////////////////////////////////////////////////////////

    def _pick_label(self, label, typ, used_labels):
        """
        Helper function for L{add_state} and C{add_arc} that chooses a
        label for a new state or arc.
        """
        if label is not None and label in used_labels:
            raise ValueError("%s with label %r already exists" %
                             (typ, label))
        # If no label was specified, pick one.
        if label is not None:
            return label
        else:
            label = 1
            while '%s%d' % (typ[0], label) in used_labels: label += 1
            return '%s%d' % (typ[0], label)

######################################################################
#{ AT&T fsmtools Support
######################################################################

class FSMTools:
    """
    A class used to interface with the AT&T fsmtools package.  In
    particular, L{FSMTools.transduce} can be used to transduce an
    input string using any subsequential transducer where each input
    and output arc is labelled with at most one symbol.
    """
    EPSILON = object()
    """A special symbol object used to represent epsilon strings in
    the symbol<->id mapping (L{FSMTools._symbol_ids})."""

    def __init__(self, fsmtools_path=''):
        self.fsmtools_path = fsmtools_path
        """The path of the directory containing the fsmtools binaries."""

        self._symbol_ids = self.IDMapping(self.EPSILON)
        """A mapping from symbols to unique integer IDs.  We manage
        our own mapping, rather than using 'symbol files', since
        symbol files can't handle non-string symbols, symbols
        containing whitespace, unicode symbols, etc."""
        
        self._state_ids = self.IDMapping()
        """A mapping from state labels to unique integer IDs."""

    #////////////////////////////////////////////////////////////
    #{ Transduction
    #////////////////////////////////////////////////////////////

    def transduce(self, fst, input_string):
        try:
            # Create a temporary working directory for intermediate files.
            tempdir = tempfile.mkdtemp()
            def tmp(s): return os.path.join(tempdir, s+'.fsm')

            # Comile the FST & input file into binary fmstool format.
            self.compile_fst(fst, tmp('fst'))
            self.compile_string(input_string, tmp('in'))

            # Transduce the input using the FST.  We do this in two
            # steps: first, use fsmcompose to eliminate any paths that
            # are not consistent with the input string; and then use
            # fsmbestpath to choose a path through the FST.  If the
            # FST is nondeterministic, then the path chosen is
            # arbitrary.  Finally, print the result, so we can process
            # it and extract the output sequence.
            p1 = Popen([self._bin('fsmcompose'), tmp('in'), tmp('fst')],
                       stdout=PIPE)
            p2 = Popen([self._bin('fsmbestpath')],
                       stdin=p1.stdout, stdout=PIPE)
            p3 = Popen([self._bin('fsmprint')],
                       stdin=p2.stdout, stdout=PIPE)
            out_string_fsm = p3.communicate()[0]
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir, f))
            os.rmdir(tempdir)

        # If the empty string was returned, then the input was not
        # accepted by the FST; return None.
        if len(out_string_fsm) == 0:
            return None

        # Otherwise, the input was accepted, so extract the
        # corresponding output string.
        out_string = []
        final_state_id = 0
        for line in out_string_fsm.split('\n'):
            words = line.split()
            if len(words) == 5:
                out_string.append(self._symbol_ids.getval(words[3]))
                final_state_id += int(words[4])
            elif len(words) == 4:
                out_string.append(self._symbol_ids.getval(words[3]))
            elif len(words) == 2:
                final_state_id += int(words[1])
            elif len(words) != 0:
                raise ValueError("Bad output line: %r" % line)

        # Add on the finalizing string for the final state.
        final_state = self._state_ids.getval(final_state_id)
        out_string += fst.finalizing_string(final_state)
        return out_string

    #////////////////////////////////////////////////////////////
    #{ FSM Compilation
    #////////////////////////////////////////////////////////////

    def compile_fst(self, fst, outfile):
        """
        Compile the given FST to an fsmtools .fsm file, and write it
        to the given filename.
        """
        if fst.initial_state is None:
            raise ValueError("FST has no initial state!")
        if not (fst.is_final(fst.initial_state) or
                len(fst.outgoing(fst.initial_state)) > 0):
            raise ValueError("Initial state is nonfinal & "
                             "has no outgoing arcs")

        # Put the initial state first, since that's how fsmtools
        # decides which state is the initial state.
        states = [fst.initial_state] + [s for s in fst.states() if
                                        s != fst.initial_state]

        # Write the outgoing edge for each state, & mark final states.
        lines = []
        for state in states:
            for arc in fst.outgoing(state):
                src, dst, in_string, out_string = fst.arc_info(arc)
                lines.append('%d %d %d %d\n' %
                         (self._state_ids.getid(src),
                          self._state_ids.getid(dst),
                          self._string_id(in_string),
                          self._string_id(out_string)))
            if fst.is_final(state):
                lines.append('%d %d\n' % (self._state_ids.getid(state),
                                        self._state_ids.getid(state)))
                
        # Run fsmcompile to compile it.
        p = Popen([self._bin('fsmcompile'), '-F', outfile], stdin=PIPE)
        p.communicate(''.join(lines))

    def compile_string(self, sym_string, outfile):
        """
        Compile the given symbol string into an fsmtools .fsm file,
        and write it to the given filename.  This FSM will generate
        the given symbol string, and no other strings.
        """
        # Create the input for fsmcompile.
        lines = []
        for (i, sym) in enumerate(sym_string):
            lines.append('%d %d %d\n' % (i, i+1, self._symbol_ids.getid(sym)))
        lines.append('%d\n' % len(sym_string))
    
        # Run fsmcompile to compile it.
        p = Popen([self._bin('fsmcompile'), '-F', outfile], stdin=PIPE)
        p.communicate(''.join(lines))

    #////////////////////////////////////////////////////////////
    #{ Helpers
    #////////////////////////////////////////////////////////////

    def _bin(self, command):
        return os.path.join(self.fsmtools_path, command)

    def _string_id(self, sym_string):
        if len(sym_string) == 0:
            return self._symbol_ids.getid(self.EPSILON)
        elif len(sym_string) == 1:
            return self._symbol_ids.getid(sym_string[0])
        else:
            raise ValueError('fsmtools does not support multi-symbol '
                             'input or output strings on arcs.??')

    class IDMapping:
        def __init__(self, *values):
            self._id_to_val = list(values)
            self._val_to_id = dict([(v,i) for (i,v) in enumerate(values)])
            
        def getid(self, val):
            if val not in self._val_to_id:
                self._id_to_val.append(val)
                self._val_to_id[val] = len(self._id_to_val)-1
            return self._val_to_id[val]

        def getval(self, identifier):
            return self._id_to_val[int(identifier)]

######################################################################
#{ Graphical Display
######################################################################

class FSTWidget(GraphWidget):
    def __init__(self, canvas, fst, **attribs):
        GraphWidget.__init__(self, canvas, (), (), **attribs)
                             
        # Create a widget for each state.
        self.state_widgets = state_widgets = {}
        for state in fst.states():
            label = TextWidget(canvas, state)
            if fst.is_final(state) and fst.finalizing_string(state):
                fstr = fst.finalizing_string(state)
                label = StackWidget(canvas, label,
                              SequenceWidget(canvas,
                                       SymbolWidget(canvas, 'rightarrow'),
                                       TextWidget(canvas, fstr)))
            w = OvalWidget(canvas, label,
                           double=fst.is_final(state), margin=2,
                           fill='white')
            if state == fst.initial_state:
                w = SequenceWidget(canvas,
                                   SymbolWidget(canvas, 'rightarrow'), w)
            w['draggable'] = True
            state_widgets[state] = w
            self.add_node(w)
        
        # Create a widget for each arc.
        self.arc_widgets = arc_widgets = {}
        for arc in fst.arcs():
            label = TextWidget(canvas, ' '.join(fst.in_string(arc)) + ' : ' +
                               ' '.join(fst.out_string(arc)))
            w = GraphEdgeWidget(canvas, 0,0,0,0, label, color='cyan4')
            arc_widgets[arc] = w
            self.add_edge(state_widgets[fst.src(arc)],
                          state_widgets[fst.dst(arc)], w)

        # Arrange the graph.
        if fst.initial_state is not None:
            toplevel = [self.state_widgets[fst.initial_state]]
        else:
            toplevel = None
        self.arrange(toplevel=toplevel)

    def mark_state(self, state, color='green2'):
        oval = self.state_widgets[state]
        if isinstance(oval, SequenceWidget):
            oval = oval.child_widgets()[1]
        oval['fill'] = color
                      
    def unmark_state(self, state):
        oval = self.state_widgets[state]
        if isinstance(oval, SequenceWidget):
            oval = oval.child_widgets()[1]
        oval['fill'] = 'white'

    def mark_arc(self, arc):
        edge = self.arc_widgets[arc]
        edge['width'] = 2
        edge['color'] = 'blue'
                      
    def unmark_arc(self, arc):
        edge = self.arc_widgets[arc]
        edge['width'] = 1
        edge['color'] = 'cyan4'

class FSTDisplay:
    def __init__(self, *fsts):
        self.cf = CanvasFrame(width=580, height=600, background='#f0f0f0')
        self.cf._parent.geometry('+650+50') # hack..

        self.fst_widgets = {}
        for fst in fsts:
            self.add_fst(fst)

    def add_fst(self, fst):
        w = FSTWidget(self.cf.canvas(), fst, draggable=True,
                      xspace=130, yspace=100)
        self.fst_widgets[fst] = w
        self.cf.add_widget(w, x=20)

class FSTDemo:
    def __init__(self, fst):
        self.top = Tk()
        f1 = Frame(self.top)
        f2 = Frame(self.top)
        f3 = Frame(self.top)
        f4 = Frame(self.top)

        # The canvas for the FST itself.
        self.cf = CanvasFrame(f1, width=800, height=400,
                              background='#f0f0f0', 
                              relief="sunken", border="2")
        self.cf.pack(expand=True, fill='both')

        # The description of the current state.
        self.state_label = Label(f4, font=('bold', -16))
        self.state_label.pack(side='top', anchor='sw')
        self.state_descr = Text(f4, height=3, wrap='word', border="2",
                               relief="sunken", font='helvetica',
                               width=10)
        self.state_descr.pack(side='bottom', expand=True, fill='x')

        # The input string.
        font = ('courier', -16, 'bold')
        Label(f2,text=' Input:', font='courier').pack(side='left')
        self.in_text = in_text = Text(f2, height=1, wrap='none',
                                      font=font, background='#c0ffc0',
                                      #padx=0, pady=0,
                                      width=10,
                                      highlightcolor='green',
                                      highlightbackground='green',
                                      highlightthickness=1)
        in_text.tag_config('highlight', foreground='white',
                           background='green4')
        in_text.insert('end', 'r = reset; <space> = step')
        in_text.tag_add('read', '1.0', '1.4')
        in_text.pack(side='left', expand=True, fill="x")

        # The input string.
        Label(f3,text='Output:', font='courier').pack(side='left')
        self.out_text = out_text = Text(f3, height=1, wrap='none',
                                        font=font, background='#ffc0c0',
                                        #padx=0, pady=0,
                                        width=10,
                                        highlightcolor='red',
                                        highlightbackground='red',
                                        highlightthickness=1)
        out_text.tag_config('highlight', foreground='white',
                           background='red4')
        out_text.pack(side='left', expand=True, fill="x")
        
        f1.pack(expand=True, fill='both', side='top', padx=5, pady=5)
        f4.pack(expand=False, fill='x', side='bottom', padx=5, pady=5)
        f3.pack(expand=False, fill='x', side='bottom', padx=5, pady=5)
        f2.pack(expand=False, fill='x', side='bottom', padx=5, pady=5)

        self.top.title('FST')
        self.top.geometry('+650+50')
        self.top.bind('<Control-p>', lambda e: self.cf.print_to_file())
        self.top.bind('<Control-x>', self.destroy)
        self.top.bind('<Control-q>', self.destroy)
        self.top.bind('<space>', self.step)
        self.top.bind('r', lambda e: self.transduce(self.stepper_input))

        self.stepper = None

        self.graph = None
        self.set_fst(fst)

    def transduce(self, input):
        if self.fst.is_subsequential():
            self.stepper = self.fst.step_transduce_subsequential(input)
        else:
            self.stepper = self.fst.step_transduce(input)
        self.stepper_input = input
        # the following really duplicates code in step(), and should be
        # factored out.
        self.in_text.delete('1.0', 'end')
        self.out_text.delete('1.0', 'end')
        self.in_text.insert('1.0', ' '.join(self.stepper_input))
        for state in self.fst.states():
            self.graph.unmark_state(state)
        self.graph.mark_state(self.fst.initial_state)
        self.state_label['text'] = 'State = %s' % self.fst.initial_state
        self.state_descr.delete('1.0', 'end')
        state_descr = fst.state_descr(self.fst.initial_state)
        self.state_descr.insert('end', state_descr or '')
        
    def step(self, *e):
        if self.stepper is None: return

        # Perform one step.
        try: result, val = self.stepper.next()
        except StopIteration: return

        if result == 'fail':
            self.stepper = None
            self.out_text.insert('end', ' (Failed!)')
        elif result == 'succeed':
            self.stepper = None
            self.out_text.delete('1.0', 'end')
            self.out_text.insert('end', ' '.join(val))
            self.out_text.tag_add('highlight', '1.0', 'end-1c')
            self.out_text.insert('end', ' (Finished!)')
        elif result == 'backtrack':
            self.out_text.insert('end', ' (Backtrack)')
            for state, widget in self.graph.state_widgets.items():
                if state == val: self.graph.mark_state(state, '#f0b0b0')
                else: self.graph.unmark_state(state)
        else:
            (arc, in_pos, output) = val
            
            # Update in text display
            in_pos += len(fst.in_string(arc))
            output = list(output)+list(fst.out_string(arc))
            self.in_text.delete('1.0', 'end')
            self.in_text.insert('end', ' '.join(self.stepper_input[:in_pos]))
            self.in_text.tag_add('highlight', '1.0', 'end-1c')
            if in_pos > 0:
                self.in_text.insert('end', ' ')
            l,r= self.in_text.xview()
            if (r-l) < 1:
                self.in_text.xview_moveto(1.0-(r-l)/2)
            self.in_text.insert('end', ' '.join(self.stepper_input[in_pos:]))

            # Update out text display
            self.out_text.delete('1.0', 'end')
            self.out_text.insert('end', ' '.join(output))
            self.out_text.tag_add('highlight', '1.0', 'end-1c')

            # Update the state descr display
            self.state_label['text'] = 'State = %s' % fst.dst(arc)
            self.state_descr.delete('1.0', 'end')
            state_descr = fst.state_descr(fst.dst(arc))
            self.state_descr.insert('end', state_descr or '')

            # Highlight the new dst state.
            for state, widget in self.graph.state_widgets.items():
                if state == fst.dst(arc):
                    self.graph.mark_state(state, '#00ff00')
                elif state == fst.src(arc):
                    self.graph.mark_state(state, '#b0f0b0')
                else: self.graph.unmark_state(state)
        
            # Highlight the new arc.
            for a, widget in self.graph.arc_widgets.items():
                if a == arc: self.graph.mark_arc(a)
                else: self.graph.unmark_arc(a)

        # Make end of output visible..
        l,r= self.out_text.xview()
        if (r-l) < 1:
            self.out_text.xview_moveto(1.0-(r-l)/2)
            self.out_text.insert('end', ' '*100)

    def set_fst(self, fst):
        self.fst = fst
        c = self.cf.canvas()
        if self.graph is not None:
            self.cf.remove_widget(self.graph)
        self.graph = FSTWidget(c, self.fst, xspace=130, yspace=100)
        self.cf.add_widget(self.graph, 20, 20)

    def destroy(self, *e):
        if self.top is None: return
        self.top.destroy()
        self.top = None

    def mainloop(self, *args, **kwargs):
        self.top.mainloop(*args, **kwargs)

######################################################################
#{ Test Code
######################################################################

if __name__ == '__main__':
    # This is a very contrived example.  :)
    # Something phonetic might be better.
    fst = FST.parse("test", """
        -> start
        start -> vp [john:john]
        start -> vp [mary:mary]

        # Delay production of the determiner until we know the gender.
        start -> subj_noun [the:]
        subj_noun -> vp [dog:le chien]
        subj_noun -> vp [cow:la vache]

        vp -> obj [eats:mange]
        obj -> obj_noun [the:]
        obj -> obj_noun [:]
        obj_noun -> end [grass:de l'herbe]
        obj_noun -> end [bread:du pain]
        end ->
        """)

    print "john eats the bread ->"
    print '  '+ ' '.join(fst.transduce("john eats the bread".split()))
    rev = fst.inverted()
    print "la vache mange de l'herbe ->"
    print '  '+' '.join(rev.transduce("la vache mange de l'herbe".split()))

    demo = FSTDemo(fst)
    demo.transduce("the cow eats the bread".split())
    demo.mainloop()
