from nltk.sem.chat80 import Concept


def test_concept_default_containers_are_independent():
    first = Concept("first", arity=1)
    second = Concept("second", arity=1)

    first.altLabels.append("alias")
    first.closures.append("symmetric")
    first.augment("one")

    assert second.altLabels == []
    assert second.closures == []
    assert second.augment("two") == {"two"}
