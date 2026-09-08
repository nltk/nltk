from nltk.parse.dependencygraph import DependencyGraph


def test_contains_cycle_follows_relation_mapped_dependencies():
    graph = DependencyGraph("a N 0 ROOT\n" "b N 3 dep\n" "c N 2 dep\n")

    assert graph.contains_cycle() == [2, 3]
