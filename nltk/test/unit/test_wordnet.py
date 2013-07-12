# -*- coding: utf-8 -*-
"""
Unit tests for nltk.corpus.wordnet. See also: nltk/test/wordnet.doctest
"""
from nltk.corpus import wordnet as wn

def test_lowest_common_hypernyms():
    """
    This tests wordnet's lowest_common_hypernyms method. It should

    a) Generally only return 1 result (although some are known to return 2+)
    b) Return the lowest result (depending on whether max_depth or min_depth) 
    is used
    """

    lch = wn.synset('kin.n.01').lowest_common_hypernyms(wn.synset('mother.n.01'))
    assert len(lch) == 1
    assert lch == [wn.synset('relative.n.01')]

    lch = wn.synset('kin.n.01').lowest_common_hypernyms(wn.synset('mother.n.01'), use_min_depth=True)
    assert len(lch) == 1
    assert lch == [wn.synset('organism.n.01')]

    lch = wn.synset('policeman.n.01').lowest_common_hypernyms(wn.synset('chef.n.01'))
    assert len(lch) == 1
    assert lch == [wn.synset('person.n.01')]

    lch = wn.synset('policeman.n.01').lowest_common_hypernyms(wn.synset('chef.n.01'), use_min_depth=True)
    assert len(lch) == 1
    assert lch == [wn.synset('organism.n.01')]

    lch = wn.synset('woman.n.01').lowest_common_hypernyms(wn.synset('girlfriend.n.02'))
    assert len(lch) == 1
    assert lch == [wn.synset('woman.n.01')]

    lch = wn.synset('woman.n.01').lowest_common_hypernyms(wn.synset('girlfriend.n.02'), use_min_depth=True)
    assert len(lch) == 1
    assert lch == [wn.synset('organism.n.01')]

    lch = wn.synset('agency.n.01').lowest_common_hypernyms(wn.synset('office.n.01'))
    assert len(lch) == 1
    assert lch == [wn.synset('entity.n.01')]

    lch =  wn.synset('agency.n.01').lowest_common_hypernyms(wn.synset('office.n.01'), use_min_depth=True)
    assert len(lch) == 1
    assert lch == [wn.synset('entity.n.01')]

    lch = wn.synset('day.n.10').lowest_common_hypernyms(wn.synset('service.n.07'))
    assert len(lch) == 1
    assert lch == [wn.synset('writer.n.01')]

    lch = wn.synset('day.n.10').lowest_common_hypernyms(wn.synset('service.n.07'), use_min_depth=True)
    assert len(lch) == 2
    assert lch == [wn.synset('organism.n.01'), wn.synset('writer.n.01')]

    lch = wn.synset('body.n.09').lowest_common_hypernyms(wn.synset('sidereal_day.n.01'))
    assert len(lch) == 2
    assert lch == [wn.synset('measure.n.02'), wn.synset('attribute.n.02')]

    lch = wn.synset('body.n.09').lowest_common_hypernyms(wn.synset('sidereal_day.n.01'), use_min_depth=True)
    assert len(lch) == 2
    assert lch == [wn.synset('measure.n.02'), wn.synset('attribute.n.02')]