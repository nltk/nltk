# Natural Language Toolkit: Probability and Statistics
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from chktype import chktype as _chktype

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
    C{__contains__()}, which tests whether a sample is a
    contained by the event.  However, when possible, events should
    also define the following methods:
        - C{__cmp__()}, which tests whether this event is
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
        - C{__len__()}, which returns the number of samples 
           contained by this event.
    
    Classes implementing the C{EventI} interface may choose
    to only support certain classes of samples, or may choose to only
    support certain types of events as arguments to the optional
    methods (C{__cmp__}, C{subset}, etc.).  If a
    method is unable to return a correct result because it is given an 
    unsupported type of sample or event, it should raise a
    NotImplementedError.  (?? is this the right exception? use
    NotSupportedError? ValueError? ??)
    """
    def __contains__(self, sample):
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
        raise AssertionError()
    
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
        return self.__contains__(sample) # Is this ok?????
    
    def __cmp__(self, other):
        # ok not to implement!
        """
        Return 0 if the given object is equal to the event.  Formally, 
        return 0 if and only if every sample contained by this event
        is also contained by C{other}, and every sample
        contained by C{other} is contained by this event.
        Otherwise, return some nonzero number.
        
        @param other: The object to compare this event to.
        @type other: Event
        @return: 0 if the given object is equal to this event.
        @rtype: int
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
        @return: true if this event is a superset of the given event.
        @rtype: boolean
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        @raise NotImplementedError: If C{other} is not a
               supported Event type.
        """
        # ok not to implement!
        raise NotImplementedError()
    
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

    def __len__(self):
        """
        Return the number of samples contained by this event.  If this 
        event contains an infinite number of samples, return None.  If 
        this event is unable to determine how many samples are
        contained, raise NotImplementedError.

        @return: The number of samples contained by this event.
        @rtype: int
        @raise NotImplementedError: If this method is not implemented
               by this Event class.
        """
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
    def __contains__(self, sample):
        # Inherit docs from EventI
        return sample == self._sample
    def contains(self, sample):
        # Inherit docs from EventI
        return sample == self._sample
    def __cmp__(self, other):
        # Inherit docs from EventI
        return self.samples() == other.samples()
    def subset(self, other):
        # Inherit docs from EventI
        return self._sample in other
    def superset(self, other):
        # Inherit docs from EventI
        if isinstance(other, SampleEvent):
            return self._sample == other._sample
        elif isinstance(other, SetEvent):
            return (len(other) == 0) or \
                   (len(other) == 1 and self._sample in other)
        else:
            raise NotImplementedError()
    def union(self, other): 
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return FuncEvent(f)
    def intersection(self, other):
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return FuncEvent(f)
    def samples(self):
        # Inherit docs from EventI
        return Set(self._sample)
    def __len__(self):
        # Inherit docs from EventI
        return 1
    def sample(self):
        """
        @return: The single sample contained by this
            C{SampleEvent}.
        @rtype: any
        """
        return self._sample
  
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
    def __contains__(self, sample):
        # Inherit docs from EventI
        return sample in self._set
    def contains(self, sample):
        # Inherit docs from EventI
        return sample in self._set
    def __cmp__(self, other):
        # Inherit docs from EventI
        return self.samples() == other.samples()
    def subset(self, other):
        # Inherit docs from EventI
        for elt in self._set.elements():
            if elt not in other: return 0
        return 1
    def superset(self, other):
        # Inherit docs from EventI
        if isinstance(other, SampleEvent):
            return other.sample() in self
        elif isinstance(other, SetEvent):
            return other.subset(self)
        else:
            raise NotImplementedError()
    def union(self, other): 
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return FuncEvent(f)
    def intersection(self, other):
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return FuncEvent(f)
    def samples(self):
        # Inherit docs from EventI
        # Make a copy -- it's safer.
        return self._set.copy()
    def __len__(self):
        # Inherit docs from EventI
        return len(self._set)

class FuncEvent(EventI):
    """
    An C{Event} whose samples are defined by a function.
    This function should return 1 for any samples contained in the
    C{Event}, and 0 for any samples not contained in the
    C{Event}.  C{FuncEvent}s are often created
    using C{lambda} expressions.  Examples, with their
    corresponding sets, are::

      e1 = FuncEvent(lambda x:x>3)            {x:x>3}
      e2 = FuncEvent(lambda x:x[0:2]=='hi')   {x:x[0:2]=='hi'}
    """
    def __init__(self, func):
        """
        Construct a new C{FuncEvent} from the given
        function.  The function should return 1 for any samples
        contained in the C{Event}, and 0 for any samples not 
        contained in the C{Event}.
        
        @param func: A function specifying what samples are in this
               C{Event}.
        @type func: Function or BuiltinFunction
        """
        self._func = func
    def __contains__(self, sample):
        return self._func(sample) != 0
    def contains(self, sample):
        return self._func(sample) != 0
    def __cmp__(self, other):
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
        # Inherit docs from EventI
        if isinstance(other, SampleEvent):
            return other.sample() in self
        elif isinstance(other, SetEvent):
            for elt in other.samples().elements():
                if elt not in self: return 0
            return 1
        else:
            raise NotImplementedError()
    def union(self, other): 
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return FuncEvent(f)
    def intersection(self, other):
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return FuncEvent(f)
    def samples(self):
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def __len__(self): 
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()

class NullEvent(EventI):
    """
    An event that contains no samples.
    """
    def __contains__(self, sample): return 0
    def contains(self, sample): return 0
    def __cmp__(self, other): return len(other)==0
    def subset(self, other): return 1
    def superset(self, other): return len(other)==0
    def union(self, other): return other
    def intersection(self, other): return self
    def samples(self): return Set()
    def __len__(self): return 0

class UniversalEvent(EventI):
    """
    An event that contains every sample.
    """
    def __contains__(self, sample): return 1
    def contains(self, sample): return 1
    def __cmp__(self, other):
        if isinstance(other, UniversalEvent): return 1
        else: raise NotImplementedError()
    def subset(self, other): return self==other
    def superset(self, other): return 1
    def union(self, other): return self
    def intersection(self, other): return other
    def samples(self): 
        """
        B{Not implemented by this Event class.}
        
        @rtype: None
        """
        raise NotImplementedError()
    def __len__(self): return None
        
##//////////////////////////////////////////////////////
##  Frequency Distribution
##//////////////////////////////////////////////////////

class FreqDistI:
    """
    A frequency distribution for the outcomes of an experiment.  A
    frequency distribution records the number of times each outcome of
    an experiment has occured.  For example, a frequency distribution
    could be used to record the frequency of each token in a document.
    Formally, a frequency distribution can be defined as a function
    mapping from samples to the number of times that sample occured as
    an outcome.

    Frequency distributions are generally constructed by running a
    number of experiments, and incrementing the count for a sample
    every time it is an outcome of an experiment.  For example, the
    following code will produce a frequency distribution that encodes
    how often each word occurs in a text::
    
      freqDist = SimpleFreqDist()
      for word in document:
          freqDist.inc(word)

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
    
    def N(self):
        """
        @return: The total number of sample outcomes that have been
          recorded by this C{FreqDist}.
        @rtype: int
        """
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
        @rtype: int
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
    def __init__(self):
        """
        Construct a new, empty, C{SimpleFreqDist}.
        """
        self._dict = {}
        self._N = 0

    def inc(self, sample):
        # Inherit docs from FreqDistI
        self._N += 1
        if self._dict.has_key(sample):
            self._dict[sample] += 1
        else:
            self._dict[sample] = 1

    def N(self):
        # Inherit docs from FreqDistI
        return self._N

    def count(self, sample_or_event):
        # Inherit docs from FreqDistI
        
        # If it's a sample, the answer is easy.
        if not isinstance(sample_or_event, EventI):
            if self._dict.has_key(sample_or_event):
                return self._dict[sample_or_event]
            else:
                return 0

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
            freq = self.cond_freq(sample, condition)
            if freq > max_freq:
                max_sample = sample
                max_freq = freq
        return max_sample

    def __str__(self):
        """
        Return the informal string representation of this
        C{SimpleFreqDist}.  The informal representation of a
        C{SimpleFreqDist} is the informal
        representation of its dictionary.
        
        @return: The informal string representation of this
            C{SimpleFreqDist}.
        @rtype: string
        """
        return str(self._dict)

  
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
    
    def __str__(self):
        """
        Return the informal string representation of this
        C{CFSample}.  The informal representation of a
        C{CFSample} has the form
        C{(I{context}, I{feature})}
        
        @return: The informal string representation of this
            C{CFSample}.
        @rtype: string
        """
        return '('+str(self._context)+', '+str(self._feature)+')'
    
    def __repr__(self):
        """
        Return the formal string representation of this
        C{CFSample}.  The formal representation of a
        C{CFSample} has the form
        C{CFSample(I{context}, I{feature})}
        
        @return: The formal string representation of this
            C{CFSample}.
        @rtype: string
        """
        return 'CFSample('+repr(self._context)+', '+\
               repr(self._feature)+')'
    
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
        @rtype: int
        """
        if not isinstance(other, CFSample): return -1000
        c = cmp(self._context, other._context)
        if c != 0: return c
        else: return cmp(self._feature, other._feature)

    def __hash__(self):
        """
        Compute a hash value for this C{CFSample}.  
        
        @return: The hash value for this C{CFSample}.
        @rtype: int
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
        
    def __contains__(self, sample):
        # Inherit docs from EventI
        if not isinstance(sample, CFSample): return 0
        return sample.context() == self._context
    
    def contains(self, sample):
        # Inherit docs from EventI
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

    A C{CFFreqDist} is implemented as a two-level
    dictionary.  The dictionaries are structured such that
    C{dict[I{context}][I{feature}]} gives the number
    of occurances of the sample
    C{CFSample(I{context}, I{feature})}.
    The C{CFFreqDist} also uses auxilliary variables to
    record the total number of samples, and the number of samples that 
    have a given condition, for each condition.
    """
    def __init__(self):
        """
        Construct a new, empty, C{CFFreqDist}.
        """
        self._dict = {}
        self._N = 0
        self._cond_N = {}

    def inc(self, sample):
        # Inherit docs from FreqDistI
        _chktype("CFFreqDist.inc", 1, sample, (CFSample,))
        self._N += 1
        if self._dict.has_key(sample.context()):
            self._cond_N[sample.context()] += 1
            if self._dict[sample.context()].has_key(sample.feature()):
                self._dict[sample.context()][sample.feature()] += 1
            else:
                self._dict[sample.context()][sample.feature()] = 1
        else:
            self._cond_N[sample.context()] = 1
            self._dict[sample.context()] = {sample.feature():1}

    def N(self):
        # Inherit docs from FreqDistI
        return self._N

    def count(self, sample_or_event):
        # Inherit docs from FreqDistI
        event = sample_or_event
        _chktype("CFFreqDist.count", 1, event, (CFSample, ContextEvent))
        if isinstance(event, CFSample):
            if self._dict.has_key(event.context()) and \
               self._dict[event.context()].has_key(event.feature()):
                return self._dict[event.context()][event.feature()]
            else:
                return 0
        else:
            if self._cond_N.has_key(event.context()):
                return self._cond_N[event.context()]
            else:
                return 0

    def cond_freq(self, sample_or_event, condition):
        # Inherit docs from FreqDistI, for now.  Eventually replace
        # them with docs that specify that event must be a CFSample
        # and condition must be a ContextEvent.
        sample = sample_or_event
        _chktype("CFFreqDist.cond_freq", 1, sample, (CFSample,))
        _chktype("CFFreqDist.cond_freq", 2, condition, (ContextEvent,))
        feature = sample.feature()
        context = condition.context()
        if not self._dict.has_key(context) or \
           not self._dict[context].has_key(feature):
            return 0.0
        return float(self._dict[context][feature]) / self._cond_N[context]

    def max(self):
        # Inherit docs from FreqDistI
        if self._N == 0: return None
        max = -1
        max_feature = max_context = None
        for (context, feature_dict) in self._dict.items():
            for (feature, n) in feature_dict.items():
                if n > max:
                    max = n
                    max_feature = feature
                    max_context = context
        return CFSample(max_context, max_feature)
    
    def cond_max(self, condition):
        # Inherit docs from FreqDistI
        _chktype("CFFreqDist.cond_max", 1, condition, (ContextEvent,))
        context = condition.context()
        if not self._dict.has_key(context): return None
        max_freq = -1
        max_feature = None
        for (feature, freq) in self._dict[context].items():
            if freq > max_freq:
                max_feature = feature
                max_freq = freq
        if max_feature == None: return None
        else: return CFSample(context, max_feature)

    def __str__(self):
        """
        Return the informal string representation of this
        C{CFFreqDist}.  The informal representation of a
        C{CFFreqDist} has the form
        C{(I{context}, I{feature})}
        
        @return: The informal string representation of this
            C{CFFreqDist}.
        @rtype: string
        """
        return repr(self._dict)
        
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
  
