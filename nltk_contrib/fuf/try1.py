"""
First try to produce the same unification result as FUF
"""

from nltk.featstruct import FeatStruct, FeatList, FeatDict

# the first thing is to build the structures

# build the input to the grammar
def build_input():
    input = FeatStruct("""
        [cat=s, 
            prot=[n=[lex=John]],
            verb=[v=[lex=like]],
            goal=[n=[lex=Mary]]]""")
    return input

# now build the grammar in pieces and then put it together

def build_first():
    """
    Returns the first alt part of the sample grammar
    """
    first = FeatStruct("""
        [cat=s, 
            prot=(1)[cat=np], 
            goal=(2)[cat=np], 
            verb=(3)[cat=vp]]""")
    return first

def build_second():
    """
    Returns the second alt part of the sample grammar
    """
    second = FeatStruct(""" 
        [cat=np, n=[cat=noun],
        alt=[1=[proper=yes, 
                pattern=n], 
             2=[proper=no, 
                pattern=[det=n], 
                det=[cat=article, lex=the]]]]
        """)
    return second

def build_third():
    """
    Returns the third alt part of the sample grammar
    """
    third = FeatStruct("""
        [cat=vp, pattern=v, v=[cat=verb]]""")
    return third

# put all the pieces of the grammar together
def build_main():
    """
    Returns the complete sample grammar
    """
    first = build_first()
    second = build_second()
    third = build_third()

    main_alt = FeatStruct()
    # this is one of the way we can build an alt structure
    # without introducing special definitions
    main_alt['alt'] = FeatStruct()
    main_alt['alt']['1'] = first
    main_alt['alt']['2'] = second
    main_alt['alt']['3'] = third
    main_alt['alt']['4'] = FeatStruct(cat='noun')
    main_alt['alt']['5'] = FeatStruct(cat='verb')
    main_alt['alt']['6'] = FeatStruct(cat='article')
    return main_alt

# this method unpacks the whole grammar and returns a list of 
# structures that can be used to do the unification with
def unpack_alt(grammar):
    # used to store the alternatives
    packs = list()

    # make a copy of everything without the alt
    fs = FeatStruct()
    for gkey, gvalue in grammar.items():
        if gkey != "alt":
            fs[gkey] = gvalue

    # unpacking the alt
    if not grammar.has_key('alt'):
        return grammar

    for key in grammar['alt'].keys():
        fscopy = fs.copy()
        for akey, avalue in grammar['alt'][key].items():
            fscopy[akey] = avalue
        packs.append(fscopy)
    
    # recursively try to unpack any
    # possible nested alts
    unpacked = list()
    while len(packs) > 0:
        pack = packs.pop(0)
        temp = unpack_alt(pack)
        if isinstance(temp, list):
            for i in temp:
                packs.append(i)
        else:
            unpacked.append(temp)
    return unpacked


def uni_helper2(input, grammar):
    for ikey, ivalue in input.items():
        if isinstance(ivalue, FeatStruct):
            for subgr in grammar:
                if ivalue.unify(subgr) is not None:
                    input[ikey] = ivalue.unify(subgr)
                    uni_helper2(input[ikey], grammar)
                    break

def uni(input, grammar):
    linput = input.copy()
    # this can generate a large list if the
    # grammar is very large. the fuf manual
    # has suggestions for improvements
    fslist = unpack_alt(grammar)

    # this assumes that the first part of the grammar is the 's' feature
    linput = linput.unify(fslist[0])

    # this call will modify the local copy of the input
    uni_helper2(linput, fslist)
    return linput
    
output = uni(build_input(), build_main())
print "OUTPUT"
print output
