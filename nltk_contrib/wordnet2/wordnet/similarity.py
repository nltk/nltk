import math
from nltk import defaultdict
from util import *
_INF = 1e300

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

    @type  synset2: L{Synset}
    @param synset2: The L{Synset} that this L{Synset} is being compared to.

    @return: A score denoting the similarity of the two L{Synset}s,
        normally between 0 and 1. -1 is returned if no connecting path
        could be found. 1 is returned if a L{Synset} is compared with
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

    @type  synset2: L{Synset}
    @param synset2: The L{Synset} that this L{Synset} is being compared to.

    @return: A score denoting the similarity of the two L{Synset}s,
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

    @type  synset2: L{Synset}
    @param synset2: The L{Synset} that this L{Synset} is being compared to.
    @return: A float score denoting the similarity of the two L{Synset}s,
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

def res_similarity(synset1, synset2, ic, verbose=False):
    """
    Resnik Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node).

    @type  synset1: L{Synset}
    @param synset1: The first synset being compared
    @type  synset2: L{Synset}
    @param synset2: The second synset being compared
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: A float score denoting the similarity of the two L{Synset}s.
        Synsets whose LCS is the root node of the taxonomy will have a
        score of 0 (e.g. N['dog'][0] and N['table'][0]). If no path exists
        between the two synsets a score of -1 is returned.
    """

    ic1, ic2, lcs_ic = _lcs_ic(synset1, synset2, ic)
    return lcs_ic

def jcn_similarity(synset1, synset2, ic, verbose=False):
    """
    Jiang-Conrath Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node) and that of the two input Synsets. The relationship is
    given by the equation 1 / (IC(s1) + IC(s2) - 2 * IC(lcs)).

    @type  synset1: L{Synset}
    @param synset1: The first synset being compared
    @type  synset2: L{Synset}
    @param synset2: The second synset being compared
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: A float score denoting the similarity of the two L{Synset}s.
        If no path exists between the two synsets a score of -1 is returned.
    """

    if synset1 == synset2:
        return _INF
    
    ic1, ic2, lcs_ic = _lcs_ic(synset1, synset2, ic)

    # If either of the input synsets are the root synset, or have a
    # frequency of 0 (sparse data problem), return 0.
    if ic1 == 0 or ic2 == 0:
        return 0

    return 1 / (ic1 + ic2 - 2 * lcs_ic)

def lin_similarity(synset1, synset2, ic, verbose=False):
    """
    Lin Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node) and that of the two input Synsets. The relationship is
    given by the equation 2 * IC(lcs) / (IC(s1) + IC(s2)).

    @type  synset1: L{Synset}
    @param synset1: The first synset being compared
    @type  synset2: L{Synset}
    @param synset2: The second synset being compared
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: A float score denoting the similarity of the two L{Synset}s,
        in the range 0 to 1. If no path exists between the two synsets a
        score of -1 is returned.
    """

    ic1, ic2, lcs_ic = _lcs_ic(synset1, synset2, ic)
    return (2.0 * lcs_ic) / (ic1 + ic2)

# Utility functions

def common_hypernyms(synset1, synset2):
    """
    Find all synsets that are hypernyms of both input synsets.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.
    @return: The synsets that are hypernyms of both synset1 and synset2.
    """

    # can't use set operations here
    hypernyms1 = [synset1] + list(synset1.closure(HYPERNYM))
    hypernyms2 = [synset2] + list(synset2.closure(HYPERNYM))
    return [s for s in hypernyms1 if s in hypernyms2]
    
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

    subsumers = common_hypernyms(synset1, synset2)
    
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

def _lcs_ic(synset1, synset2, ic, verbose=False):
    """
    Get the information content of the least common subsumer that has
    the highest information content value.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: The information content of the two synsets and their most informative subsumer
    """

    pos = synset1.pos
    ic1 = information_content(synset1, ic)
    ic2 = information_content(synset2, ic)
    subsumer_ic = max(information_content(s, ic) for s in common_hypernyms(synset1, synset2))

    if verbose:
        print "> LCS Subsumer by content:", subsumer_ic
    
    return ic1, ic2, subsumer_ic

# Utility functions

def information_content(synset, ic):
    pos = synset.pos
    return -math.log(ic[pos][synset.offset] / ic[pos][0])

# this load function would be more efficient if the data was pickled
# Note that we can't use NLTK's frequency distributions because
# synsets are overlapping (each instance of a synset also counts
# as an instance of its hypernyms)
def load_ic(icfile):
    """
    Load an information content file from the wordnet_ic corpus
    and return a dictionary.  This dictionary has just two keys,
    NOUN and VERB, whose values are dictionaries that map from
    synsets to information content values.

    @type  icfile: L{str}
    @param icfile: The name of the wordnet_ic file (e.g. "ic-brown.dat")
    @return: An information content dictionary
    """
    icfile = nltk.data.find('corpora/wordnet_ic/' + icfile)
    ic = {}
    ic[NOUN] = defaultdict(int)
    ic[VERB] = defaultdict(int)
    for num, line in enumerate(open(icfile)):
        if num == 0: # skip the header
            continue
        fields = line.split()
        offset = int(fields[0][:-1])
        value = float(fields[1])
        pos = _get_pos(fields[0])
        if num == 1: # store root count
            ic[pos][0] = value
        if value != 0:
            ic[pos][offset] = value
    return ic
 
# get the part of speech (NOUN or VERB) from the information content record
# (each identifier has a 'n' or 'v' suffix)
def _get_pos(field):
    if field[-1] == 'n':
        return NOUN
    elif field[-1] == 'v':
        return VERB
    else:
        raise ValueError, "Unidentified part of speech in WordNet Information Content file"

