# Natural Language Toolkit: Wordnet Similarity
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
import math

# Similarity metrics

# TODO: Add in the option to manually add a new root node; this will be
# useful for verb similarity as there exist multiple verb taxonomies.

# More information about the metrics is available at
# http://marimba.d.umn.edu/similarity/measures.html

def path_similarity(synset1, synset2, verbose=False):
    """
    Path Distance Similarity:
    Return a score denoting how similar two word senses are, based on the
    shortest path that connects the senses in the is-a (hypernym/hypnoym)
    taxonomy. The score is in the range 0 to 1, except in those cases
    where a path cannot be found (will only be true for verbs as there are
    many distinct verb taxonomies), in which case -1 is returned. A score of
    1 represents identity i.e. comparing a sense with itself will return 1.

    @type  synset2: L{Sense}
    @param synset2: The L{Sense} that this L{Sense} is being compared to.

    @return: A score denoting the similarity of the two L{Sense}s,
        normally between 0 and 1. -1 is returned if no connecting path
        could be found. 1 is returned if a L{Sense} is compared with
        itself.
    """

    distance = synset1.shortest_path_distance(synset2)
    if distance >= 0:
        return 1.0 / (distance + 1)
    else:
        return -1

def lch_similarity(synset1, synset2, verbose=False):
    """
    Leacock Chodorow Similarity:
    Return a score denoting how similar two word senses are, based on the
    shortest path that connects the senses (as above) and the maximum depth
    of the taxonomy in which the senses occur. The relationship is given as
    -log(p/2d) where p is the shortest path length and d is the taxonomy depth.

    @type  synset2: L{Sense}
    @param synset2: The L{Sense} that this L{Sense} is being compared to.

    @return: A score denoting the similarity of the two L{Sense}s,
        normally greater than 0. -1 is returned if no connecting path
        could be found. If a L{Synset} is compared with itself, the
        maximum score is returned, which varies depending on the taxonomy depth.
    """

    taxonomy_depths = {NOUN: 19, VERB: 13}
    if synset1.pos not in taxonomy_depths.keys():
        raise TypeError, "Can only calculate similarity for nouns or verbs"
    depth = taxonomy_depths[synset1.pos]

    distance = synset1.shortest_path_distance(synset2)
    if distance >= 0:
        return -math.log((distance + 1) / (2.0 * depth))
    else:
        return -1

def wup_similarity(synset1, synset2, verbose=False):
    """
    Wu-Palmer Similarity:
    Return a score denoting how similar two word senses are, based on the
    depth of the two senses in the taxonomy and that of their Least Common
    Subsumer (most specific ancestor node). Note that at this time the
    scores given do _not_ always agree with those given by Pedersen's Perl
    implementation of Wordnet Similarity.

    The LCS does not necessarily feature in the shortest path connecting the
    two senses, as it is by definition the common ancestor deepest in the
    taxonomy, not closest to the two senses. Typically, however, it will so
    feature. Where multiple candidates for the LCS exist, that whose
    shortest path to the root node is the longest will be selected. Where
    the LCS has multiple paths to the root, the longer path is used for
    the purposes of the calculation.

    @type  synset2: L{Sense}
    @param synset2: The L{Sense} that this L{Sense} is being compared to.
    @return: A float score denoting the similarity of the two L{Sense}s,
        normally greater than zero. If no connecting path between the two
        senses can be found, -1 is returned.
    """

    subsumer = _lcs_by_depth(synset1, synset2, verbose)

    # If no LCS was found return -1
    if subsumer == None:
        return -1

    # Get the longest path from the LCS to the root,
    # including two corrections:
    # - add one because the calculations include both the start and end nodes
    # - add one to non-nouns since they have an imaginary root node
    depth = subsumer.max_depth() + 1
    if subsumer.pos != NOUN:
        depth += 1

    # Get the shortest path from the LCS to each of the synsets it is subsuming.
    # Add this to the LCS path length to get the path length from each synset to the root.
    len1 = synset1.shortest_path_distance(subsumer) + depth
    len2 = synset2.shortest_path_distance(subsumer) + depth
    return (2.0 * depth) / (len1 + len2)

def res_similarity(synset1, synset2, datafile="", verbose=False):
    """
    Resnik Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node). Note that at this time the scores given do _not_
    always agree with those given by Pedersen's Perl implementation of
    Wordnet Similarity, although they are mostly very similar.

    The required IC values are precomputed and stored in a file, the name
    of which should be passed as the 'datafile' argument. For more
    information on how they are calculated, check brown_ic.py.

    @type  synset2: L{Sense}
    @param synset2: The L{Sense} that this L{Sense} is being compared to.
    @return: A float score denoting the similarity of the two L{Sense}s.
        Synsets whose LCS is the root node of the taxonomy will have a
        score of 0 (e.g. N['dog'][0] and N['table'][0]). If no path exists
        between the two synsets a score of -1 is returned.
    """

    _check_datafile(datafile)

    # TODO: Once this data has been loaded for the first time preserve it
    # in memory in some way to prevent unnecessary recomputation.
    (noun_freqs, verb_freqs) = _load_ic_data(datafile)

    if synset1.pos is NOUN:
        (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, noun_freqs)

    elif synset1.pos is VERB:
        (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, verb_freqs)

    return lcs_ic

def jcn_similarity(synset1, synset2, datafile="", verbose=False):
    """
    Jiang-Conrath Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node) and that of the two input Synsets. The relationship is
    given by the equation 1 / (IC(s1) + IC(s2) - 2 * IC(lcs)).

    Note that at this time the scores given do _not_ always agree with
    those given by Pedersen's Perl implementation of Wordnet Similarity,
    although they are mostly very similar.

    The required IC values are calculated using precomputed frequency
    counts, which are accessed from the 'datafile' file which is supplied
    as an argument. For more information on how they are calculated,
    check brown_ic.py.

    @type  synset2: L{Sense}
    @param synset2: The L{Sense} that this L{Sense} is being compared to.
    @return: A float score denoting the similarity of the two L{Sense}s.
        If no path exists between the two synsets a score of -1 is returned.
    """

    _check_datafile(datafile)

    if synset1 == synset2:
        return inf

    # TODO: Once this data has been loaded for the first time preserve it
    # in memory in some way to prevent unnecessary recomputation.
    (noun_freqs, verb_freqs) = _load_ic_data(datafile)

    # Get the correct frequency dict as dependent on the input synsets'
    # pos (Part of Speech) attribute.
    if synset1.pos is NOUN: freqs = noun_freqs
    elif synset1.pos is VERB: freqs = verb_freqs
    else: return -1

    ic1 = synset1.information_content(freqs)
    ic2 = synset2.information_content(freqs)
    (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, freqs)

    # If either of the input synsets are the root synset, or have a
    # frequency of 0 (sparse data problem), return 0.
    if ic1 is 0 or ic2 is 0: return 0

    return 1 / (ic1 + ic2 - 2 * lcs_ic)

def lin_similarity(synset1, synset2, datafile="", verbose=False):
    """
    Lin Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node) and that of the two input Synsets. The relationship is
    given by the equation 2 * IC(lcs) / (IC(s1) + IC(s2)).

    Note that at this time the scores given do _not_ always agree with
    those given by Pedersen's Perl implementation of Wordnet Similarity,
    although they are mostly very similar.

    The required IC values are calculated using precomputed frequency
    counts, which are accessed from the 'datafile' file which is supplied
    as an argument. For more information on how they are calculated,
    check brown_ic.py.

    @type  synset2: L{Sense}
    @param synset2: The L{Sense} that this L{Sense} is being compared to.
    @return: A float score denoting the similarity of the two L{Sense}s,
        in the range 0 to 1. If no path exists between the two synsets a
        score of -1 is returned.
    """

    _check_datafile(datafile)

    # TODO: Once this data has been loaded cache it to save unnecessary recomputation.
    (noun_freqs, verb_freqs) = _load_ic_data(datafile)

    if synset1.pos is NOUN: freqs = noun_freqs
    elif synset1.pos is VERB: freqs = verb_freqs
    else: return -1

    ic1 = synset1.information_content(freqs)
    ic2 = synset2.information_content(freqs)
    (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, freqs)

    return (2.0 * lcs_ic) / (ic1 + ic2)

# Utility functions

def _lcs_by_depth(synset1, synset2, verbose=False):
    """
    Finds the least common subsumer of two synsets in a Wordnet taxonomy,
    where the least common subsumer is defined as the ancestor node common
    to both input synsets whose shortest path to the root node is the longest.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.
    @return: The ancestor synset common to both input synsets which is also the LCS.
    """
    subsumer = None
    max_min_path_length = -1

    # can't use set operations here
    hypernyms1 = [synset1] + list(synset1.closure(HYPERNYM))
    hypernyms2 = [synset2] + list(synset2.closure(HYPERNYM))
    subsumers = [s for s in hypernyms1 if s in hypernyms2]
    
    if verbose:
        print "> Subsumers1:", subsumers

    # Eliminate those synsets which are ancestors of other synsets in the
    # set of subsumers.

    eliminated = set()
    for s1 in subsumers:
        for s2 in subsumers:
            if s2 in s1.closure(HYPERNYM):
                eliminated.add(s2)
    if verbose:
        print "> Eliminated:", eliminated
    
    subsumers = [s for s in subsumers if s not in eliminated]

    if verbose:
        print "> Subsumers2:", subsumers

    # Calculate the length of the shortest path to the root for each
    # subsumer. Select the subsumer with the longest of these.

    for candidate in subsumers:

        paths_to_root = candidate.hypernym_paths()
        min_path_length = -1

        for path in paths_to_root:
            if min_path_length < 0 or len(path) < min_path_length:
                min_path_length = len(path)

        if min_path_length > max_min_path_length:
            max_min_path_length = min_path_length
            subsumer = candidate

    if verbose:
        print "> LCS Subsumer by depth:", subsumer
    return subsumer

def _lcs_by_content(synset1, synset2, freqs, verbose=False):
    """
    Get the least common subsumer of the two input synsets, where the least
    common subsumer is defined as the ancestor synset common to both input
    synsets which has the highest information content (IC) value. The IC
    value is calculated by extracting the probability of an ancestor synset
    from a precomputed set.

    @type  synset1: L{Synset}
    @param synset1: First input synset.

    @type  synset2: L{Synset}
    @param synset2: Second input synset.

    @return: The ancestor synset common to both input synsets which is also
        the LCS.
    """
    subsumer = None
    subsumer_ic = -1

#    subsumers = set(synset1.closure(HYPERNYM)) & set(synset2.closure(HYPERNYM))  -- Broken

    subsumers = set()
    for s1 in synset1.closure(HYPERNYM):
        for s2 in synset2.closure(HYPERNYM):
            if s1 == s2:
                subsumers.add(s1)
    subsumers.add(synset1)
    subsumers.add(synset2)

    # For each candidate, calculate its IC value. Keep track of the candidate
    # with the highest score.
    for candidate in subsumers:
        ic = candidate.information_content(freqs)
        if (subsumer == None and ic > 0) or ic > subsumer_ic:
            subsumer = candidate
            subsumer_ic = ic

    if verbose:
        print "> LCS Subsumer by content:", subsumer, subsumer_ic
    
    return (subsumer, subsumer_ic)


