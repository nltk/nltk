from unittest.mock import Mock

import pytest

from nltk.app.wordnet_app import Reference


@pytest.mark.parametrize("create_other_first", [False, True])
def test_reference_expansion_does_not_affect_other_lookups(create_other_first):
    expanded = Reference("dog")
    if create_other_first:
        other = Reference("cat")

    synset = Mock()
    synset.name.return_value = "dog.n.01"
    try:
        expanded.toggle_synset(synset)
        expanded.toggle_synset_relation(synset, "hypernyms")

        if not create_other_first:
            other = Reference("cat")

        restored = Reference.decode(other.encode())
        assert restored.word == "cat"
        assert restored.synset_relations == {}
        assert expanded.synset_relations == {"dog.n.01": {"hypernyms"}}
    finally:
        expanded.synset_relations.clear()


def test_references_toggle_the_same_synset_independently():
    first = Reference("dog")
    second = Reference("dog")
    synset = Mock()
    synset.name.return_value = "dog.n.01"

    first.toggle_synset(synset)
    second.toggle_synset(synset)

    assert first.synset_relations == {"dog.n.01": set()}
    assert second.synset_relations == {"dog.n.01": set()}

    first.toggle_synset(synset)

    assert first.synset_relations == {}
    assert second.synset_relations == {"dog.n.01": set()}


def test_reference_preserves_provided_relations():
    reference = Reference("dog", {"dog.n.01": {"hypernyms"}})
    synset = Mock()
    synset.name.return_value = "dog.n.01"

    reference.toggle_synset_relation(synset, "hyponyms")

    restored = Reference.decode(reference.encode())
    assert restored.word == "dog"
    assert restored.synset_relations == {"dog.n.01": {"hypernyms", "hyponyms"}}
