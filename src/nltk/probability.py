# Natural Language Toolkit: Probability and Statistics
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.chktype import chktype as _chktype
from types import IntType as _IntType
from nltk.set import Set

##//////////////////////////////////////////////////////
##  Sample
##//////////////////////////////////////////////////////
  
# A sample can be any Python object that is not an Event.  Typical
# examples are tokens, lists of tokens, sets of tokens.  Samples can't be 
# Functions, either.
# Every sample must define == correctly (and __hash__)
  
##//////////////////////////////////////////////////////
##  Event
##//////////////////////////////////////////////////////

class EventI:
    """
    A subset of the samples that compose some sample space.  Note that 
    this subset need not be finite.  Events are typically written as
    the set of samples they contain, or as a function in first order
    logic.  Examples are::
        {1,2,3}
        {x:x>0}

    The only method that events are required to implement is
    C{contains()}, which tests whether a sample is a
    contained by the event.  However, when possible, events should
    also define the following methods:
        - C{equals()}, which tests whether this event is
           equal to another event.
        - C{subset()}, which tests whether this event is a
           subset of another event.
        - C{superset()}, which tests whether this event is
           a superset of another event.
        - C{union()}, which returns an event containing the
           union of this event's samples and another event's samples.
        - C{intersection()}, which returns an event
           containing the intersection of this event's samples and
           another event's samples.
        - C{samples()}, which returns a C{Set}
           containing all of the samples that are contained by this
           event. 
        - C{len()}, which returns the number of samples 
           contained by this event.
    
    Classes implementing the C{EventI} interface may choose
    to only support certain classes of samples, or may choose to only
    support certain types of events as arguments to the optional
    methods (C{__cmp__}, C{subset}, etc.).  If a
    method is unable to return a correct result because it is given an 
    unsupported type of sample or event, it should raise a
    NotImplementedError.

    String representations for events should have the form::

        {Event ...}

    Some examples are:

        >>> SetEvent(Set(1, 2, 3))
        {Event 3, 2, 1}
        >>> NullEvent()
        {Event}
        >>> def even(x): x%2 == 0
        >>> PredEvent(even)
        {Event x: even(x)}
    """
    def contains(self, sample):
        """
        Return true if and only if the given sample is contained in
        this event.  Return false if C{sample} is not a
        supported type of sample for this C{Event} class.

        @param sample: The sample whose membership we are testing.
        @type sample: any
        @return: A true value if and only if the given sample is
            contained in this event.
        @rtype: boolean
        """
        raise AssertionError('Internal Error: Class failed to define contains')
    
    def __contains__(self, sample):
        return self.contains(sample)
    __contains__.__doc__ = contains.__doc__
    
    def equals(self, other):
        # ok not to implement!
        """
        Return 1 if the given object is equal to the event.  Formally, 
        return 1 if and only if every sample contained by this event
        is also contained by C{other}, and every sample
        contained by C{other} is contained by this event.
        Otherwise, return zero.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: 1 if the given object is equal to this event.
        @rtype: C{int}
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not an
               Event, or is not a supported Event type.
        """
        raise NotImplementedError()
    
    def subset(self, other):
        """
        Return true if this event is a subset of the given 
        event.  Formally, return true if and only if every sample
        contained by this event is contained by C{other}.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: true if this event is a subset of the given event.
        @rtype: boolean
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        # ok not to implement!
        raise NotImplementedError()
    
    def superset(self, other):
        """
        Return true if this event is a superset of the given 
        event.  Formally, return true if and only if every sample
        contained by C{other} is contained by this event.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: true if this event is a proper superset of the given event.
        @rtype: boolean
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        raise NotImplementedError()
    
    def __lt__(self, other):
        """
        Return true if this event is a proper subset of the given 
        event.  Formally, return true if and only if every sample
        contained by this event is contained by C{other}, and C{other} 
        contains at least one sample not contained by this event.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: true if this event is a proper subset of the given event.
        @rtype: boolean
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        return (self <= other) and (self != other)

    def __gt__(self, other):
        """
        Return true if this event is a proper superset of the given 
        event.  Formally, return true if and only if every sample
        contained by C{other} is contained by this event, and this
        event contains at least one sample not contained by C{other}.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: true if this event is a superset of the given event.
        @rtype: boolean
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        return (self >= other) and (self != other)

    def __eq__(self, other):
        return self.equals(other)
    __eq__.__doc__ = equals.__doc__

    def __ne__(self, other):
        """
        Return 1 if the given object is not equal to the event.
        Formally, return 1 if and only if C{self} contains a sample
        not contained in C{other}, or C{other} contains a sample not
        contained in C{self}.  Otherwise, return zero.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: 1 if the given object is equal to this event.
        @rtype: C{int}
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not an
               Event, or is not a supported Event type.
        """
        return not self.equals(other)

    def __ge__(self, other):
        try:
            return self.superset(other)
        except NotImplementedError:
            return other.subset(self)
    __ge__.__doc__ = superset.__doc__
    
    def __le__(self, other):
        try:
            return self.subset(other)
        except NotImplementedError:
            return other.superset(self)
    __le__.__doc__ = subset.__doc__
    
    def samples(self):
        """
        Return a C{Set} containing all of the samples
        contained by this event.  The effects of changes to this
        C{Set} on the C{Event} are undefined.  The 
        effects of changes to the C{Event} on this
        C{Set} are also undefined.
        
        @return: The set of samples contained in this event.
        @rtype: Set
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        """
        # ok not to implement!
        raise NotImplementedError()

    def len(self):
        """
        Return the number of samples contained by this event.  If this 
        event contains an infinite number of samples, return None.  If 
        this event is unable to determine how many samples are
        contained, raise NotImplementedError.

        @return: The number of samples contained by this event.
        @rtype: C{int}
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        """
        raise NotImplementedError()
        
    def __len__(self):
        return self.len()
    __len__.__doc__ = len.__doc__
        
    def union(self, other):
        """
        Return an event containing the union of this event's samples
        and another event's samples.  Formally, return an event that
        contains a sample if and only if either self or other contains 
        that sample.

        @param other: The C{Event} with which to union this
               C{Event}.
        @type other: Event
        @return: An event containing the union of this event's samples
                and another event's samples.
        @rtype: Event
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        raise NotImplementedError()
    
    def intersection(self, other):
        """
        Return an event containing the intersection of this event's
        samples and another event's samples.  Formally, return an
        event that contains a sample if and only if both self and
        other contains that sample.

        @param other: The C{Event} with which to intersection
               this C{Event}.               
        @type other: Event
        @return: An event containing the intersection of this event's
                samples and another event's samples.
        @rtype: Event
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        raise NotImplementedError()

    def difference(self, other):
        """
        Return an event containing the difference between this event's
        samples and another event's samples.  Formally, return an
        event that contains a sample if and only if it is contained in
        self, but not in other.

        @param other: The C{Event} which should be subtracted from
               this C{Event}.
        @type other: Event
        @return: An event containing the difference between this
                event's samples and another event's samples.
        @rtype: Event
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        raise NotImplementedError()
    
    def __add__(self, other):
        return self.union(other)
    __add__.__doc__ = union.__doc__
    
    def __mul__(self, other):
        return self.intersection(other)
    __mul__.__doc__ = intersection.__doc__
    
    def __sub__(self, other):
        return self.difference(other)
    __sub__.__doc__ = difference.__doc__

class SampleEvent(EventI):
    """
    An C{Event} containing a single sample.
    """
    def __init__(self, sample):
        """
        Construct a new C{SampleEvent}, containing only the
        given sample.
        
        @param sample: The sample that the new event should contain.
        @type sample: any
        """
        self._sample = sample
    def contains(self, sample):
        return sample == self._sample
    def equals(self, other):
        return self.samples() == other.samples()
    def subset(self, other):
        return self._sample in other
    def superset(self, other):
        if isinstance(other, SampleEvent):
            return self._sample == other._sample
        # This may raise NotImplementedError:
        elif len(other) == 0:
            return 1
        elif len(other) == 1:
            return self._sample in other
        else:
            raise NotImplementedError()
    def toSetEvent(self):
        """
        @return: A SetEvent containing this event's sample.
        @rtype: SetEvent
        """
        return SetEvent(Set(self._sample))
    def union(self, other):
        return self.toSetEvent().union(other)
    def intersection(self, other):
        return self.toSetEvent().intersection(other)
    def difference(self, other):
        return self.toSetEvent().difference(other)
    def samples(self):
        return Set(self._sample)
    def len(self):
        return 1
    def predicate_name(self):
        return 'x==%r' % self._sample
    def sample(self):
        """
        @return: The single sample contained by this
            C{SampleEvent}.
        @rtype: any
        """
        return self._sample
    def __repr__(self):
        return '{Event: '+repr(self._sample)+'}'
  
class SetEvent(EventI):
    """
    An C{Event} whose samples are defined by a Set.
    """
    def __init__(self, set):
        """
        Construct a new C{SetEvent}, whose samples are the
        elements of the given set.
        
        @param set: The set of samples that the new event should
               contain.
        @type set: Set
        """
        self._set = set
    def contains(self, sample):
        return sample in self._set
    def equals(self, other):
        # This may raise NotImplementedError:
        return self.samples() == other.samples()
    def subset(self, other):
        for elt in self._set.elements():
            if elt not in other: return 0
        return 1
    def superset(self, other):
        if isinstance(other, SampleEvent):
            return other.sample() in self
        elif isinstance(other, SetEvent):
            return other.subset(self)
        else:
            raise NotImplementedError()
    def union(self, other): 
        try:
            return SetEvent(self._set.union(other.samples()))
        except NotImplementedError:
            f = (lambda x, a=self, b=other:(x in a or x in b))
            if hasattr(other, 'predicate_name'):
                return PredEvent(f, '(%s) or (%s)' %
                                 (self.predicate_name(),
                                  other.predicate_name()))
            else:
                return PredEvent(f)
    def intersection(self, other):
        try:
            return SetEvent(self._set.intersection(other.samples()))
        except NotImplementedError:
            newset = Set()
            for elt in self._set.elements():
                if elt in other:
                    newset.insert(elt)
            return SetEvent(newset)
    def difference(self, other):
        try:
            return SetEvent(self._set.difference(other.samples()))
        except NotImplementedError:
            newset = Set()
            for elt in self._set.elements():
                if elt not in other:
                    newset.insert(elt)
            return SetEvent(newset)
    def samples(self):
        # Make a copy -- it's safer.
        return self._set.copy()
    def len(self):
        return len(self._set)
    def predicate_name(self):
        return 'x in %r' % self._set.elements()
    def __repr__(self):
        if len(self._set) == 0: return '{Event}'
        str = '{Event '
        for elt in self._set.elements():
            str += "%r, " % elt
        return str[:-2]+'}'
    def __str__(self):
        if len(self._set) == 0: return '{Event}'
        x = 7
        str = '{Event '
        for elt in self._set.elements()[:5]:
            substr = '%r, ' % elt
            if len(substr) + x > 75:
                str += "\n    "
                x = 4
            x += len(substr)
            str += substr
        return str[:-2]+'}'

class PredEvent(EventI):
    """
    An C{Event} whose samples are defined by a function.
    This function should return 1 for any samples contained in the
    C{Event}, and 0 for any samples not contained in the
    C{Event}.  C{PredEvent}s are often created
    using C{lambda} expressions.  Examples, with their
    corresponding sets, are::

      e1 = PredEvent(lambda x:x>3)            {x:x>3}
      e2 = PredEvent(lambda x:x[0:2]=='hi')   {x:x[0:2]=='hi'}
    """
    def __init__(self, predicate, name=None):
        """
        Construct a new C{PredEvent} from the given
        function.  The function should return 1 for any samples
        contained in the C{Event}, and 0 for any samples not 
        contained in the C{Event}.
        
        @param predicate: A function specifying what samples are in
             this C{Event}.
        @type predicate: C{Function} or C{BuiltinFunction}
        @param name: A descriptive name for the predicate function.
            This name is used when the event is printed.  It should be
            a .. hrm.
        @type name: C{string}
        """
        self._predicate = predicate
        if name is None:
            self._name = self._predicate.__name__+'(x)'
            if self._name == '<lambda>(x)':
                self._name = 'f(x)'
        else:
            self._name = name
    def contains(self, sample):
        return self._predicate(sample) != 0
    def equals(self, other):
        """
        B{Not implemented by this Event class.}
        
        @param other: -
        @type other: -
        @rtype: None
        """
        raise NotImplementedError()
    def subset(self, other): 
        """
        B{Not implemented by this Event class.}
        
        @param other: -
        @type other: -
        @rtype: None
        """
        raise NotImplementedError()
    def superset(self, other):
        if isinstance(other, SampleEvent):
            return other.sample() in self
        else:
            # This may raise NotImplementedError:
            for elt in other.samples().elements():
                if elt not in self: return 0
            return 1
    def union(self, other): 
        try:
            return SetEvent(other.samples()).union(self)
        except NotImplementedError:
            f = (lambda x, a=self, b=other:(x in a or x in b))
            if hasattr(other, 'predicate_name'):
                return PredEvent(f, '(%s) or (%s)' %
                                 (self.predicate_name(),
                                  other.predicate_name()))
            else:
                return PredEvent(f)
    def intersection(self, other):
        f = (lambda x, a=self, b=other:(x in a and x in b))
        if hasattr(other, 'predicate_name'):
            return PredEvent(f, '(%s) and (%s)' %
                             (self.predicate_name(),
                              other.predicate_name()))
        else:
            return PredEvent(f)
    def difference(self, other):
        f = (lambda x, a=self, b=other:(x in a and x not in b))
        if hasattr(other, 'predicate_name'):
            return PredEvent(f, '(%s) and not (%s)' %
                             (self.predicate_name(),
                              other.predicate_name()))
        else:
            return PredEvent(f)
    def samples(self):
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def len(self): 
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def predicate_name(self):
        """
        @return: a descriptive name for the predicate function.
        @rtype: C{string}
        """
        return self._name
    def __repr__(self):
        return '{Event x: %s}' % self.predicate_name()
    def predicate(self):
        """
        @return: The predicate that this event is based on.
        @rtype: C{Function} or C{BuiltinFunction}
        """
        return self._predicate
        
class NullEvent(EventI):
    """
    An event that contains no samples.
    """
    def contains(self, sample): return 0
    def equals(self, other): return len(other)==0
    def subset(self, other): return 1
    def superset(self, other): return len(other)==0
    def union(self, other): return other
    def intersection(self, other): return self
    def difference(self, other): return self
    def samples(self): return Set()
    def predicate_name(self): return "false"
    def len(self): return 0
    def __repr__(self): return '{Event}'

class UniversalEvent(EventI):
    """
    An event that contains every sample.
    """
    def contains(self, sample): return 1
    def equals(self, other):
        if isinstance(other, UniversalEvent): return 1
        else: raise NotImplementedError()
    def subset(self, other): return self==other
    def superset(self, other): return 1
    def union(self, other): return self
    def intersection(self, other): return other
    def difference(self, other):
        f = (lambda x, b=other:(x not in b))
        if hasattr(other, 'predicate_name'):
            return PredEvent(f, 'not (%s)' %
                             (other.predicate_name()))
        else:
            return PredEvent(f)
        
        return PredEvent(f)
        
    def samples(self): 
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def predicate_name(self): return "true"
    def len(self): return None
    def __repr__(self): return '{Event x}'
        
##//////////////////////////////////////////////////////
##  Frequency Distribution
##//////////////////////////////////////////////////////

class FreqDistI:
    """
    A frequency distribution for the outcomes of an experiment.  A
    frequency distribution records the number of times each outcome of
    an experiment has occured.  For example, a frequency distribution
    could be used to record the frequency of each word type in a
    document.  Formally, a frequency distribution can be defined as a
    function mapping from samples to the number of times that sample
    occured as an outcome.

    Frequency distributions are generally constructed by running a
    number of experiments, and incrementing the count for a sample
    every time it is an outcome of an experiment.  For example, the
    following code will produce a frequency distribution that encodes
    how often each word type occurs in a text::
    
      freqDist = SimpleFreqDist()
      for token in document:
          freqDist.inc(token.type())

    Classes implementing the C{FreqDistI} interface may
    choose to only support certain classes of samples or events.  If a
    method is unable to return a correct result because it is given an
    unsupported type of sample or event, it should raise a
    NotImplementedError.  (?? is this the right exception? use
    NotSupportedError? ValueError? ??)

    Since several methods defined by C{FreqDistI} can accept
    either events or samples, classes that implement the EventI
    interface should never be used as samples for a frequency
    distribution.

    Frequency distributions are required to implement the methods
    C{inc()}, C{N()}, C{count()}, C{freq()}, C{cond_freq()}, C{max()},
    and C{cond_max()}.  In the future, this list may be exapanded, and
    optional methods may be added.
    """
    def inc(self, sample):
        """
        Increment this C{FreqDist}'s count for the given
        sample.
        
        @param sample: The sample whose count should be incremented.
        @type sample: any
        @rtype: None
        @raise NotImplementedError: If C{sample} is not a
               supported sample type.
        """
        raise AssertionError()

    def samples(self):
        """
        @return: A list of all samples that have been recorded as
            outcomes by this frequency distribution.  Use C{count()}
            to determine the count for each sample.
        @rtype: C{list}
        """
        raise AssertionError()
    
    def cond_samples(self, condition):
        """
        @return: a list of all samples that have been recorded as
            outcomes by this frequency distribution and that 
            are contained by the given condition.
        @rtype: C{list}
        """
        raise AssertionError()
    
    def N(self):
        """
        @return: The total number of sample outcomes that have been
          recorded by this C{FreqDist}.  For the number of unique 
          I{samples} (or bins), see C{FreqDistI.B()}.
        @rtype: C{int}
        """
        raise AssertionError()

    def B(self):
        """
        @return: The total number of samples that have been recorded
          as outcomes by this this frequency distribution.  I.e.,
          return the number of X{bins} in this frequency
          distribution. 
        @rtype: C{int}
        """
        raise AssertionError()

    def bins(self, event):
        """
        @return: The number of bins represented by the given event.
        @rtype: C{int}
        """
        raise AssertionError()

    def Nr(self, r):
        """
        @return: The number of samples with frequency r.
        @rtype: C{int}
        """
        # What should we do for r=0??
        raise AssertionError()
    
    def freq(self, sample_or_event):
        """
        Return the frequency of a given sample or event.  The
        frequency of an event or a sample is defined as the count of
        that event or sample divided by the total number of sample
        outcomes that have been recorded by this
        C{FreqDist}.  The count of a sample is defined as
        the number of times that sample outcome was recorded by this
        C{FreqDist}.  The count of an event is the number of 
        times that a sample outcome contained by the given event was
        recorded by this C{FreqDist}.  Frequencies are
        always real numbers in the range [0, 1].
        
        @return: The frequency of a given sample or event.
        @rtype: float
        @param sample_or_event: the sample or event whose frequency
               should be returned.
        @type sample_or_event: EventI or any.
        @raise NotImplementedError: If C{sample_or_event} is
               not a supported sample type or event type.
        """
        raise AssertionError()
    
    def count(self, sample_or_event):
        """
        Return the count of a given sample or event.  The count of a
        sample is defined as the number of times that sample outcome
        was recorded by this C{FreqDist}.  The count of an
        event is the number of times that a sample outcome contained
        by the given event was recorded by this C{FreqDist}.
        Counts are non-negative integers.
        
        @return: The count of a given sample or event.
        @rtype: C{int}
        @param sample_or_event: the sample or event whose count
               should be returned.
        @type sample_or_event: EventI or any.
        @raise NotImplementedError: If C{sample_or_event} is
               not a supported sample type or event type.
        """
        raise AssertionError()

    def max(self):
        """
        Return the sample with the greatest number of outcomes in this
        frequency distribution.  If two or more samples have the same
        number of outcomes, return one of them; which sample is
        returned is undefined.  If no outcomes have occured in this
        frequency distribution, return C{None}.

        @return: The sample with the maximum number of outcomes in this
                frequency distribution.
        @rtype: any
        """
        raise AssertionError()

    def cond_max(self, condition):
        """
        Of the samples contained in the given condition, return the
        sample with the greatest number of outcomes in this frequency
        distribution.  If two or more samples have the same number of
        outcomes, return one of them; which sample is returned is
        undefined.  If no outcomes contained in the given condition
        have occured in this frequency distribution, return
        C{None}.

        @param condition: The condition within which to find the
               maximum frequency sample.
        @type condition: EventI
        @return: The sample with the maximum number of outcomes in this
                frequency distribution, of the samples contained in
                C{condition}. 
        @rtype: any
        @raise NotImplementedError: If C{condition} is
               not a supported event type.
        """
        raise AssertionError()
    
    def cond_freq(self, sample_or_event, condition):
        """
        Find the conditional frequency of the specified sample or
        event, given the specified condition.  The conditional
        frequency is defined as the number of times that a sample
        outcome is contained by both the event and the condition,
        divided by the number of times that a sample outcome is
        contained by the condition.  Assuming the condition event
        defines the C{union} member, then this definition
        can be written as::

          fd.cond_freq(e, c) == fd.count(c.union(e)) / fd.count(c)

        As a special case, if no sample outcome is contained by the
        condition, then the conditional frequency is defined as
        C{None}.  Conditional frequencies are
        always either real numbers in the range [0, 1] or the special
        value C{None}.
        
        Both C{sample_or_event} and C{condition}
        may be either samples or events.  
        
        @return: The conditional frequency of C{event} given
                C{condition}.
        @rtype: float or None
        @param sample_or_event: The event
        @type sample_or_event: EventI or any
        @param condition: The condition
        @type condition: EventI or any
        @raise NotImplementedError: If C{sample_or_event} or
               C{condition} are not a supported sample types
               or event types. 
        """
        raise AssertionError()

class SimpleFreqDist(FreqDistI):
    """
    A simple dictionary-based implementation of the
    C{FreqDist} interface.  A C{SimpleFreqDist}
    simply maintains a dictionary mapping samples to numbers of
    occurances.  C{SimpleFreqDist} supports all types of
    samples and events.

    Although this implementation allows for a full implementation of
    the C{FreqDist} interface, it can be quite inefficient when used
    to find frequencies of complex events, or to find conditional
    frequencies.  In particular, finding conditional frequencies can
    take M{O(s*e*c)}, where M{s} is the number of samples in the
    C{FreqDist}, M{e} is the number of samples in the event, and M{c}
    is the number of samples in the condition.  If you plan to perform
    a large number of conditional searches, you may want to consider
    using the C{CFFreqDist} class instead.

    @see: nltk.CFFreqDist CFFreqDist
    """
    def __init__(self, bins=None):
        """
        Construct a new, empty, C{SimpleFreqDist}.
        """
        self._dict = {}
        self._N = 0
        self._Nr_cache = None
        self._bins = bins

    def inc(self, sample):
        # Inherit docs from FreqDistI
        self._Nr_cache = None
        self._N += 1
        if self._dict.has_key(sample):
            self._dict[sample] += 1
        else:
            self._dict[sample] = 1

    def N(self):
        # Inherit docs from FreqDistI
        return self._N

    def B(self):
        # Inherit docs from FreqDistI
        if self._bins is not None: return self._bins
        else: return len(self._dict)

    def samples(self):
        # Inherit docs from FreqDistI
        return self._dict.keys()

    def cond_samples(self, condition):
        # Inherit docs from FreqDistI
        _chktype("SimpleFreqDist.cond_samples", 1, condition, (EventI,))
        return [sample for sample in self.samples() if (sample in condition)]
        
    def Nr(self, r):
        # Inherit docs from FreqDistI
        # We have to do a full search.  That's slow.  If they
        # ask for one Nr, they'll probably ask for others, so cache
        # the results.
        _chktype("SimpleFreqDist.Nr", 1, r, (_IntType,))
        if self._Nr_cache == None: 
            nr = [self.B()]
            for sample in self.samples():
                c = self.count(sample)
                if c >= len(nr):
                    nr += [0]*(c+1-len(nr))
                nr[c] += 1
                nr[0] -= 1
            self._Nr_cache = nr
        if r >= len(self._Nr_cache): return 0
        return self._Nr_cache[r]

    def count(self, sample_or_event):
        # Inherit docs from FreqDistI
        
        # If it's a sample, the answer is easy.
        if not isinstance(sample_or_event, EventI):
            return self._dict.get(sample_or_event, 0)

        # If it's a full-fledged event, do a search..  This is slow.
        count = 0
        for (key, c) in self._dict.items():
            if key in sample_or_event:
                count += c
        return count

    def freq(self, sample_or_event):
        # Inherit docs from FreqDistI
        return float(self.count(sample_or_event))/self.N()

    def cond_freq(self, sample_or_event, condition):
        # Inherit docs from FreqDistI

        # Convert samples to events.
        if not isinstance(sample_or_event, EventI):
            event = SampleEvent(sample_or_event)
        else: event = sample_or_event
        if not isinstance(condition, EventI):
            condition = SampleEvent(condition)

        e_count = 0   # self.count(c.union(e))
        c_count = 0   # self.count(c)
        for (sample, c) in self._dict.items():
            if sample in condition:
                c_count += c
                if sample in event:
                    e_count += c
        if c_count == 0: return None
        else: return float(e_count)/c_count

    def max(self):
        # Inherit docs from FreqDistI
        return self.cond_max(UniversalEvent())
        
    def cond_max(self, condition):
        # Inherit docs from FreqDistI
        max_freq = -1
        max_sample = None
        for sample in self._dict.keys():
            if (sample in condition) and (self.count(sample) > max_freq):
                max_sample = sample
                max_freq = self.count(sample)
        return max_sample

    def __repr__(self):
        """
        @rtype: string
        """
        str = '<SimpleFreqDist '
        for sample in self.samples():
            str += "%r:%r, " % (sample, self.count(sample))
        return str[:-2]+'>'
    
    def __str__(self):
        str = '<SimpleFreqDist\n    '
        x = 4
        for sample in self.samples():
            substr = "%r: %r, " % (sample, self.count(sample))
            if len(substr) + x > 75:
                str += "\n    "
                x = 4
            x += len(substr)
            str += substr
        return str[:-2]+'>'

##//////////////////////////////////////////////////////
##  Context-Feature Samples
##//////////////////////////////////////////////////////

class CFSample:
    """
    A sample consisting of a context and a feature.
    C{CFSample}s are intended to be used as samples
    for C{FreqDist}s.  The following code shows how
    C{CFSample}s could be used to train a frequency
    distribution, and then use that frequency distribution to tag new
    data::

      for (context, feature) in traing_samples:        # Train
          freqDist.inc( CFSample(context, feature) )
      for context in new_contexts:                     # Tag new data
          context_event = ContextEvent(context)
          print freqDist.cond_max(context_event).feature()

    @see: nltk.CFFreqDist CFFreqDist
    @see: nltk.ContextEvent ContextEvent
    """
    def __init__(self, context, feature):
        """
        Construct a new C{CFSample} with the given context
        and feature.
        
        @param context: The new C{CFSample}'s context.
        @type context: any
        @param feature: The new C{CFSample}'s feature.
        @type feature: any
        """
        self._context = context
        self._feature = feature
        
    def context(self):
        """
        Return this C{CFSample}'s context.
        
        @return: This C{CFSample}'s context.
        @rtype: any
        """
        return self._context

    def feature(self):
        """
        Return this C{CFSample}'s feature.
        
        @return: This C{CFSample}'s feature.
        @rtype: any
        """
        return self._feature
    
    def __repr__(self):
        """
        Return the string representation of this
        C{CFSample}.  The representation of a
        C{CFSample} has the form
        C{(I{context}, I{feature})}
        
        @return: The informal string representation of this
            C{CFSample}.
        @rtype: string
        """
        return '<CFSample '+repr(self._context)+', '+repr(self._feature)+'>'

    def __cmp__(self, other):
        """
        Return 0 if the given object is equal to this
        C{CFSample}.  Formally, return 0 if and only if
        C{self._context==other._context} and
        C{self._feature==other._feature}.  Otherwise, return 
        some nonzero number.
        
        @param other: The object to compare this C{CFSample}
               to. 
        @type other: any
        @return: 0 if the given object is equal to this
                C{CFSample}. 
        @rtype: C{int}
        """
        if not isinstance(other, CFSample): return -1000
        c = cmp(self._context, other._context)
        if c != 0: return c
        else: return cmp(self._feature, other._feature)

    def __hash__(self):
        """
        Compute a hash value for this C{CFSample}.  
        
        @return: The hash value for this C{CFSample}.
        @rtype: C{int}
        """
        return hash(self._context)/2+hash(self._feature)/2
  
class ContextEvent(EventI):
    """
    The event containing all C{CFSample}s whose context
    has a given value.  C{ContextEvent}s do not implement
    any of the optional C{Event} methods.
    
    @see: nltk.CFSample CFSample
    """
    def __init__(self, context):
        """
        Construct a new C{ContextEvent}, containing all
        samples whose context has the specified value.
        
        @param context: The context value for which this
               C{ContextEvent} contains all
               C{CFSample}s.
        @type context: any
        """
        self._context = context
        
    def contains(self, sample):
        if not isinstance(sample, CFSample): return 0
        return sample.context() == self._context
    
    def context(self):
        """
        Return the context on which this C{ContextEvent} is
        based.  This C{ContextEvent} contains all
        C{CFSample}s whose contexts are equal to this value.

        @return: The context on which this C{ContextEvent} is
                 based.
        @rtype: any
        """
        return self._context
    
    def equals(self, other):
        if isinstance(other, ContextEvent):
            return self._context == other._context
        else:
            raise NotImplementedError()
    
    def subset(self, other):
        return self.equals(other)
    
    def superset(self, other):
        return self.equals(other)

    def union(self, other): 
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return PredEvent(f)
    def intersection(self, other):
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return PredEvent(f)
    def difference(self, other):
        f = (lambda x, a=self, b=other:(x in a and x not in b))
        return PredEvent(f)
    def samples(self):
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def len(self):
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def __repr__(self):
        return '{Event x: <CFSample '+repr(self._context)+', x>}'
  
class CFFreqDist(FreqDistI):
    """
    An implementation of the C{FreqDist} interface that is
    optimized for finding conditional frequencies.  In particular, a
    C{CFFreqDist} can efficiently find the conditional
    frequency for a feature, given a context.  This can be useful for
    the task of predicting unknown feature values (also known as
    \"tagging\").

    The C{CFFreqDist} class requires that all of its samples
    be C{CFSample}.  A C{CFSample} is essentially
    (I{context}, I{feature}) pair.  Furthermore, the only
    event supported by the C{CFFreqDist} class is 
    C{ContextEvent}, which tests whether a
    C{CFSample}'s context has a given value.
    
    The following code shows how a C{CFFreqDist}s could be
    used to efficiently tag new data, given a training set::

      for (context, feature) in traing_samples:        # Train
          freqDist.inc( CFSample(context, feature) )
      for context in new_contexts:                     # Tag new data
          context_event = ContextEvent(context)
          print freqDist.cond_max(context_event).feature()

    Internal Implementation
    =======================
    A C{CFFreqDist} is implemented as a dictionary mapping contexts to
    C{SimpleFreqDist}s.  Each of these C{SimpleFreqDist}s maps
    features to counts.  Thus, if C{I{context_fdists}} is the internal
    dictionary representation then
    C{I{context_fdists}[I{context}].count(I{feature})} gives the
    number of occurances of the sample C{CFSample(I{context},
    I{feature})}.

    @ivar _dict: Internal representation of the frequency distribution. 
    @type _dict: C{dictionary} from context to C{dictionary} from
        feature to C{int}.
    """
    def __init__(self, bins=0):
        """
        Construct a new, empty, C{CFFreqDist}.
        """
        self._context_fdists = {}
        self._N = 0
        self._Nr_cache = None
        self._bins = bins

    def inc(self, sample):
        # Inherit docs from FreqDistI
        _chktype("CFFreqDist.inc", 1, sample, (CFSample,))
        self._Nr_cache = None
        self._N += 1
        (context, feature) = (sample.context(), sample.feature())
        if (not self._context_fdists.has_key(context)):
            self._context_fdists[context] = SimpleFreqDist()
            self._bins += 1
        elif self._context_fdists[context].freq(feature) == 0:
            self._bins += 1
        self._context_fdists[context].inc(feature)

    def N(self):
        # Inherit docs from FreqDistI
        return self._N

    def B(self):
        # Inherit docs from FreqDistI
        return self._bins

    def samples(self):
        # Inherit docs from FreqDistI
        samples = []
        for (context, context_fdist) in self._context_fdists.items():
            samples += [CFSample(context, feature) for feature
                        in context_fdist.samples()] 
        return samples

    def cond_samples(self, condition):
        # Inherit docs from FreqDistI
        _chktype("CFFreqDist.cond_samples", 1, condition, (EventI,))
        if isinstance(event, ContextEvent):
            return self._context_fdists[condition.context()].samples()
        else:
            return [sample for sample in self.samples() if (sample in condition)]
        
    def Nr(self, r):
        # Inherit docs from FreqDistI
        # We have to do a full search.  That's slow.  If they
        # ask for one Nr, they'll probably ask for others, so cache
        # the results.
        _chktype("CFFreqDist.Nr", 1, r, (_IntType,))
        if self._Nr_cache == None: 
            nr = []
            for sample in self.samples():
                c = self.count(sample)
                if c >= len(nr):
                    nr += [0]*(c+1-len(nr))
                nr[c] += 1
            self._Nr_cache = nr
        if r >= len(self._Nr_cache): return 0
        return self._Nr_cache[r]

    def count(self, sample_or_event):
        # Inherit docs from FreqDistI
        event = sample_or_event
        _chktype("CFFreqDist.count", 1, event, (CFSample, ContextEvent))
        if isinstance(event, CFSample):
            # CFSample
            if not self._context_fdists.has_key(event.context()):
                return 0
            return self._context_fdists[event.context()].count(event.feature())
        else:
            # ContextEvent
            if not self._context_fdists.has_key(event.context()):
                return 0
            else:
                return self._context_fdists[event.context()].N()

    def freq(self, sample_or_event):
        # Inherit docs from FreqDistI
        return float(self.count(sample_or_event))/self.N()

    def cond_freq(self, sample_or_event, condition):
        # Inherit docs from FreqDistI, for now.  Eventually replace
        # them with docs that specify that event must be a CFSample
        # and condition must be a ContextEvent.
        sample = sample_or_event
        _chktype("CFFreqDist.cond_freq", 1, sample, (CFSample,))
        _chktype("CFFreqDist.cond_freq", 2, condition, (ContextEvent,))
        feature = sample.feature()
        context = condition.context()
        if not self._context_fdists.has_key(context):
            return 0
        feature_count = self._context_fdists[context].count(feature)
        context_count = self._context_fdists[context].N()
        return float(feature_count)/context_count

    def max(self):
        # Inherit docs from FreqDistI
        if self._N == 0: return None
        max = -1
        max_feature = max_context = None
        for (context, context_fdist) in self._context_fdists.items():
            for feature in context_fdist.samples():
                n = context_fdist.count(feature)
                if n > max:
                    max = n
                    max_feature = feature
                    max_context = context
        return CFSample(max_context, max_feature)
    
    def cond_max(self, condition):
        # Inherit docs from FreqDistI
        _chktype("CFFreqDist.cond_max", 1, condition, (ContextEvent,))
        context = condition.context()
        if not self._context_fdists.has_key(context): return None
        max_count = -1
        max_feature = None
        for feature in self._context_fdists[context].samples():
            count = self._context_fdists[context].count(feature)
            if count > max_count:
                max_feature = feature
                max_count = count
        if max_feature == None: return None
        else: return CFSample(context, max_feature)

    def __repr__(self):
        """
        Return the informal string representation of this
        C{CFFreqDist}.  The informal representation of a
        C{CFFreqDist} has the form
        C{(I{context}, I{feature})}
        
        @return: The informal string representation of this
            C{CFFreqDist}.
        @rtype: string
        """
        str = '<CFFreqDist '
        for sample in self.samples():
            str += "%r:%r, " % (sample, self.count(sample))
        return str[:-1]+'>'

    def __str__(self):
        """
        Return a verbose string rep.
        """
        str = 'CFFreqDist:\n'

        # Find the list of known contexts.
        contexts = self._context_fdists.keys()

        # Find the list of known features.
        features = Set()
        for fdist in self._context_fdists.values():
            features = features.union(Set(*fdist.samples()))
        features = features.elements()

        # Sort!
        contexts.sort(lambda a,b: cmp(`a`, `b`))
        features.sort(lambda a,b: cmp(`a`, `b`))

        if not contexts or not features:
            return str + "   (no samples)\n"

        clen = max(*[len(`c`) for c in contexts])+1
        flen = max(*[len(`f`) for f in features])+1
        flen = max(flen, 6)
        clen = max(clen, 7) + 2

        # Header lines.
        str += ' '*(clen)+'|'
        str += (' '* (((flen * len(features) - 7) / 2)))
        str += "Feature\n"
        str += ' '*clen + '|'
        for f in features:
            str += ("%"+`flen`+"s") % `f`
        str += '\n'
        str += '  Context'+' '*(clen-9)+'+'
        str += ('-'*(flen*len(features))) + '-+\n'

        # Data lines.
        for c in contexts:
            str += ("%"+`clen`+"s|") % `c`
            for f in features:
                freq = self.freq(CFSample(c, f))
                str += ("%"+`flen`+".2f") % freq

            # Row total.
            str += (" |%"+`flen`+".2f") % self.freq(ContextEvent(c))
                    
            str += '\n'
        return str
        
##//////////////////////////////////////////////////////
##  Probability Distribution
##//////////////////////////////////////////////////////

class ProbDistI:
    """
    A probability distribution for the outcomes of an experiment.  A
    probability distribution specifies how likely it is that an
    experiment will have any given outcome.  For example, a
    probability distribution could be used to predict the probability
    that a given word will appear in a given context.  Formally, a
    probability distribution can be defined as a function mapping from
    samples to nonnegative real numbers, such that the sum of every
    number in the function's range is 1.0.  C{ProbDist}s are
    often used to model the probability distribution underlying a
    frequency distribution.

    Classes implementing the C{ProbDistI} interface may
    choose to only support certain classes of samples or events.  If a
    method is unable to return a correct result because it is given an
    unsupported type of sample or event, it should raise a
    NotImplementedError.  (?? is this the right exception? use
    NotSupportedError? ValueError? ??)

    Since several methods defined by C{ProbDistI} can accept
    either events or samples, classes that implement the EventI
    interface should never be used as samples for a probability
    distribution.

    Probability distributions are required to implement the methods
    C{prob()} and C{cond_prob()},
    C{max()}, and C{cond_max()}.  In the future,
    this list may be exapanded, and optional methods may be added.
    """
    def prob(self, sample_or_event):
        """
        Return the probability for a given sample or event.
        Probabilities are always real numbers in the range [0, 1]. 
        
        @return: The probability of a given sample or event.
        @rtype: float
        @param sample_or_event: the sample or event whose probability
               should be returned.
        @type sample_or_event: EventI or any.
        @raise NotImplementedError: If C{sample_or_event} is
               not a supported sample type or event type.
        """
        raise AssertionError()

    def max(self):
        """
        Return the sample with the greatest probability.  If two or
        more samples have the same probability, return one of them;
        which sample is returned is undefined.

        @return: The sample with the greatest probability.
        @rtype: any
        """
        raise AssertionError()
    
    def cond_max(self, condition):
        """        
        Of the samples contained in the given condition, return the
        sample with the greatest probability.  If two or more samples
        have the same probability, return one of them; which sample
        is returned is undefined.  If all samples in the given
        condition have probability 0, return C{None}.

        @param condition: The condition within which to find the
               maximum probability sample.
        @type condition: EventI
        @return: The sample with the maximum probability, out of all
                the samples contained in C{condition}. 
        @rtype: any
        @raise NotImplementedError: If C{condition} is
               not a supported event type.
        """
        raise AssertionError()
    
    def cond_prob(self, sample_or_event, condition):
        """
        Find the conditional probability of the specified sample or
        event, given the specified condition.  The conditional
        probability is defined as the probability that a sample will
        be in C{sample_or_event}, given the information that
        the sample is in C{condition}.  Assuming the
        condition event defines the C{union} member, then
        this definition can be written as::

          fd.cond_prob(e, c) == fd.prob(c.union(e)) / fd.prob(c)

        As a special case, if all samples in the given condition have
        probability 0, the conditional probability is defined as
        C{None}.  Conditional probabilities are always
        either real numbers in the range [0, 1] or the special value
        C{None}. 
        
        Both C{sample_or_event} and C{condition}
        may be either samples or events.  
        
        @return: The conditional probability of C{event} given
                C{condition}.
        @rtype: float or None
        @param sample_or_event: The event
        @type sample_or_event: EventI or any
        @param condition: The condition
        @type condition: EventI or any
        @raise NotImplementedError: If C{sample_or_event} or
               C{condition} are not a supported sample types
               or event types. 
        """
        raise AssertionError()

class MLEProbDist(ProbDistI):
    def __init__(self, freqdist):
        self._freqdist = freqdist
    def freqdist(self):
        return self._freqdist
    def prob(self, sample_or_event):
        return self._freqdist.freq(sample_or_event)
    def max(self):
        return self._freqdist.max()
    def cond_prob(self, sample_or_event, condition):
        return self._freqdist.cond_freq(sample_or_event, condition)
    def cond_max(self, condition):
        return self._freqdist.cond_max(condition)

class LidstoneProbDist(ProbDistI):
    """
    This still isn't quite right.  The question of what to do with the
    bin incrementing when events come in (conditions, or finding
    P(event) is slightly tricky.
    """
    def __init__(self, freqdist, l, bins=None):
        self._freqdist = freqdist
        if bins == None:
            self._bins = freqdist.B()
        else:
            self._bins = bins
        self._l = l
        self._N = self._freqdist.N()
        self._NBl = self._N + self._bins * l
        print self._NBl, self._N, self._bins, l

    def prob(self, sample_or_event):
        # The count for the given event.
        c = self._freqdist.count(sample_or_event)

        # The number of bins for the sample/event
        if isinstance(sample_or_event, EventI):
            b = self._freqdist.bins(sample_or_event)
        else:
            b = 1

        # Our probability estimate.
        return (c + b*self._l) / self._NBl
    
    def cond_prob(self, sample_or_event, condition):
        l = float(self._l)
        f = self._freqdist.cond_freq(sample_or_event, condition)
        if isinstance(sample_or_event, EventI):
            b1 = self._freqdist.bins(sample_or_event)
        else:
            b1 = 1
        b2 = self._freqdist.bins(condition)
        c2 = self._freqdist.count(condition)

        prob = (f * c2/(c2+l*b2)) + l*b1 / (c2+l*b2)
        return prob
    
    def cond_max(self, condition):
        return self._freqdist.cond_max(condition)
    def max(self):
        return self._freqdist.max()

class LaplaceProbDist(LidstoneProbDist):
    def __init__(self, freqdist, bins=None):
        LidstoneProbDist.__init__(self, freqdist, 1, bins)
        
class ELEProbDist(LidstoneProbDist):
    def __init__(self, freqdist, bins=None):
        LidstoneProbDist.__init__(self, freqdist, 0.5, bins)

class HeldOutProbDist(ProbDistI):
    """
    Base probability estimates on held-out data.
    Warning: don't modify the freq dists after you construct the
    probability distribution.

    Currently, assumes that the number of bins for the training data
    is set manually & correctly.
    """
    def __init__(self, training_dist, held_out_dist):
        self._training = training_dist
        self._heldout = held_out_dist

        # Calculate Tr
        self._Tr = [0]*(self._training.count(self._training.max())+1)
        samples = Set(*self._training.samples())
        samples = samples.union(Set(*self._heldout.samples()))
        for sample in samples.elements():
            tr_count = self._training.count(sample)
            ho_count = self._heldout.count(sample)
            self._Tr[tr_count] += ho_count

    def Tr(self, r):
        if 0 <= r < len(self._Tr): return self._Tr[r]
        else: return 0

    # Should N here be from heldout or training?  I assume heldout
    # because the P sums to one, but I should check that...
    def prob(self, sample_or_event):
        r = self._training.count(sample_or_event)
        if self._training.Nr(r) == 0: return 0
        return float(self._Tr[r])/(self._training.Nr(r)*self._heldout.N())

    def cond_prob(self, sample_or_event, condition):
        f = self._freqdist.cond_freq(sample_or_event, condition)
        r = f * self._freqdist.N()
        if self._training.Nr(r) == 0: return 0
        return float(self._Tr[r])/(self._training.Nr(r)*self._heldout.N())
    
    def cond_max(self, condition):
        return self._freqdist.cond_max(condition)
    
    def max(self):
        return self._freqdist.max()

class CrossValidationProbDist(ProbDistI):
    """
    Use cross-validation.  Currently, assumes that the number of bins
    for each freqdist is set manually & correctly.
    """
    def __init__(self, *training_data):
        self._training = training_data
        way = len(self._training)

        # Create an empty array of (way x way) entries.
        self._Tr = [[None for i in range(way)] for j in range(way)]
        self._N = 0
        for i in range(way):
            self._N += self._training[i].N()
            for j in range(way):
                if i == j: continue
                self._Tr[i][j] = self._find_Tr(i,j)

    def _find_Tr(self, i, j):
        """
        Find Tr with training set i and held out set j
        """
        training = self._training[i]
        heldout = self._training[j]
        
        Tr = [0]*(training.count(training.max())+1)
        samples = Set(*training.samples())
        samples = samples.union(Set(*heldout.samples()))
        for sample in samples.elements():
            tr_count = training.count(sample)
            ho_count = heldout.count(sample)
            Tr[tr_count] += ho_count
            
        return Tr

    def Tr(self, r):
        # Hack..
        return self._Tr[0][1][r]

    def prob(self, sample_or_event):
        top = 0
        bot = 0
        way = len(self._training)
        
        for i in range(way):
            r = self._training[i].count(sample_or_event)
            for j in range(0,way):

                if i == j: continue
                top += self._Tr[i][j][r]
            bot += (self._training[i].Nr(r) *
                    (self._N - self._training[i].N()))
        return float(top)/float(bot)

class GoodTuringProbDist(ProbDistI):
    """
    Use Good-Turing estimation for the probabilities.
    """
    pass
        
    
##//////////////////////////////////////////////////////
##  Probablistic Mix-in
##//////////////////////////////////////////////////////

class ProbablisticMixIn:
    """
    A mix-in class to associate probabilities with other classes
    (tokens, trees, rules, etc.).  To use the C{ProbablisticMixIn}
    class, define a new class that derives from an existing class and
    from ProbablisticMixIn.  You will need to define a new constructor 
    for the new class, which explicitly calls the constructors of both
    its parent classes.  For example:

        >>> class A:
        ...     def __init__(self, x, y): self.data = (x,y)
        ... 
        >>> class ProbablisticA(A, ProbablisticMixIn):
        ...     def __init__(self, p, x, y):
        ...         A.__init__(self, x, y)
        ...         ProbablisticMixIn.__init__(self, p)

    We suggest that you make C{p} the first argument for the new
    probablistic class, and keep all other arguments the same as they
    were.  This ensures that there will be no problems with
    constructors that expect varargs parameters.

    You should generally also redefine the string representation
    methods, the comparison methods, and the hashing method.
    (Others??)
    """
    def __init__(self, p):
        """
        Initialize this object's probability.  This initializer should
        be called by subclass constructors.  C{p} should generally be
        the first argument for those constructors.

        @param p: The probability associated with the object.
        @type p: C{float}
        """
        if not 0 <= p <= 1: raise ValueError('Bad probability: %s' % p)
        self._p = p

    def p(self):
        """
        @return: the probability associated with this object.
        @rtype: C{float}
        """
        return self._p

# import random
# f = SimpleFreqDist()
# for i in range(100):
#     x = random.randint(0,50)
#     f.inc(x)

# mle = MLEProbDist(f)
# laplace = LaplaceProbDist(f)
# for x in range(50):
#     print f.freq(x), mle.prob(x), laplace.prob(x)

def rand_fdist(numsamples, numoutcomes, bins=None):
    import random
    from math import sqrt
    fdist = SimpleFreqDist(bins)
    for x in range(numoutcomes):
        y = int(sqrt(random.randint(1, numsamples**2)))
        fdist.inc(y)
    return fdist

def testHeldOut():
    fdist1 = rand_fdist(10, 20, 11)
    fdist2 = rand_fdist(11, 10, 11)

    print
    print 'fdist1, fdist2'
    pdist = HeldOutProbDist(fdist1, fdist2)
    print 'Tr:', pdist._Tr
    print 'Sample  cnt1   cnt2   Tr  / ( Nr * N ) = P'
    p = 0
    for s in range(1,12):
        print "%4s %6d %6d %6.2f  %6.2f  %d     %s" % (
            s, fdist1.count(s), fdist2.count(s), 
            pdist.Tr(fdist1.count(s)),
            fdist1.Nr(fdist1.count(s)),
            fdist1.N(), pdist.prob(s))
        p += pdist.prob(s)
    print 'p total =', p
            

    print
    print 'fdist1, fdist1'
    pdist = HeldOutProbDist(fdist1, fdist1)
    print 'Tr:', pdist._Tr
    print 'Sample  cnt1   cnt2   Tr  / ( Nr * N ) = P'
    p = 0
    for s in range(1,12):
        print "%4s %6d %6d %6.2f  %6.2f  %d     %s" % (
            s, fdist1.count(s), fdist1.count(s), 
            pdist.Tr(fdist1.count(s)),
            fdist1.Nr(fdist1.count(s)),
            fdist1.N(), pdist.prob(s))
        p += pdist.prob(s)
    print 'p total =', p

def testXVal():
    fdist1 = rand_fdist(10, 20, 11)
    fdist2 = rand_fdist(11, 5, 11)
    fdist3 = rand_fdist(5, 10, 11)

    print
    print 'fdist1, fdist2, fdist3'
    pdist = CrossValidationProbDist(fdist1, fdist2, fdist3)
    print 'Tr:', pdist._Tr
    print 'Sample  cnt1   cnt2   cnt3   P'
    p = 0
    for s in range(1,12):
        print "%4s %6d %6d %6d   %s" % (
            s, fdist1.count(s), fdist2.count(s), fdist3.count(s),
            pdist.prob(s))
            
        p += pdist.prob(s)
    print 'p total =', p
            

    print
    print 'fdist1, fdist1'
    pdist = CrossValidationProbDist(fdist1, fdist1)
    print 'Tr:', pdist._Tr
    print 'Sample  cnt1   cnt2   P'
    p = 0
    for s in range(1,12):
        print "%4s %6d %6d   %s" % (
            s, fdist1.count(s), fdist1.count(s), pdist.prob(s))
        p += pdist.prob(s)
    print 'p total =', p

def testCFFreqDist():
    import random
    fdist = CFFreqDist()
    X=10
    Y=10
    # Contexts are ints, features are strings (just for fun)
    for x in range(100):
        context = random.randint(1,X-1)
        feature = str(random.randint(1,Y-1))
        fdist.inc(CFSample(context, feature))
    print fdist
        
    for context in range(1, X):
        for feature in range(1, Y):
            s=CFSample(context, str(feature))
            e=ContextEvent(context)
            print '    P('+`s`+'|'+`e`+') =', str(fdist.cond_freq(s,e))
        print '  max: ', fdist.cond_max(ContextEvent(context))
    print 'max:', fdist.max()
    print 'N:', fdist.N()
    print 'B:', fdist.B()
    print 'Nr:',
    for r in range(20):
        print fdist.Nr(r),
        
#if __name__ == '__main__':
    #testCFFreqDist()
    #testXVal()
if __name__ == '__main__':
    e1 = PredEvent(lambda x:x>20, 'x>20')
    e2 = PredEvent(lambda x:x<130, 'x<130')
    e3 = SampleEvent(30)
    e4 = SampleEvent(99)
    e5 = SampleEvent(500)
    print e1+e2, e1*e2, e1-e2
    print
    print e3+e4
    print
    print (e3+e4+e5) + (e1*e2)
    print (e3+e4+e5) * (e1*e2)
    print (e3+e4+e5) - (e1*e2)
    print
    print (e1*e2) + (e3+e4+e5) 
    print (e1*e2) * (e3+e4+e5) 
    print (e1*e2) - (e3+e4+e5)
    print
    print UniversalEvent() - e5

