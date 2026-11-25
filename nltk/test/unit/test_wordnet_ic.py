from unittest.mock import patch

import pytest

from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import lcs_ic


@pytest.fixture(scope="module")
def shared_direct_counts():
    """Parse cntlist.rev once for the test module."""
    return wn.get_direct_counts(pos=("n",))


@pytest.fixture(scope="module")
def shared_ic(shared_direct_counts):
    """Compute noun IC once for the test module."""
    return wn.compute_ic(direct_counts=shared_direct_counts, pos=("n",), smoothing=1)


class TestDynamicWordNetIC:

    def test_get_direct_counts_structure(self, shared_direct_counts):
        assert "n" in shared_direct_counts
        assert isinstance(shared_direct_counts["n"], dict)

    def test_compute_ic_root_and_total(self, shared_direct_counts, shared_ic):
        assert 0 in shared_ic["n"]
        expected_root = sum(shared_direct_counts["n"].values()) + 1
        assert shared_ic["n"][0] == expected_root

    def test_lcs_ic_valid_pair(self, shared_ic):
        dog = wn.synset("dog.n.01")
        cat = wn.synset("cat.n.01")
        lcs_node, lcs_score = lcs_ic(dog, cat, shared_ic)

        assert lcs_node is not None
        assert lcs_node in dog.common_hypernyms(cat)
        assert lcs_score > 0.0

    def test_lcs_ic_disjoint_returns_none(self, shared_ic):
        dog = wn.synset("dog.n.01")
        run = wn.synset("run.v.01")
        lcs_node, lcs_score = lcs_ic(dog, run, shared_ic)

        assert lcs_node is None
        assert lcs_score == 0.0

    def test_export_ic_dat_file_creation(self, shared_ic, tmp_path):
        export_file = tmp_path / "test_wordnet_ic.dat"
        wn.export_ic_dat(shared_ic, str(export_file))

        assert export_file.exists()
        assert export_file.read_text(encoding="utf-8").startswith("wnver::")

    def test_compute_ic_dag_closure_isolated(self):
        """Fast isolated test verifying topological closure propagation."""
        carnivore = wn.synset("carnivore.n.01")
        dog = wn.synset("dog.n.01")
        canine = wn.synset("canine.n.02")
        mock_direct = {"n": {dog: 5, canine: 10}}

        with patch.object(wn, "all_synsets", return_value=[carnivore, canine, dog]):
            ic = wn.compute_ic(direct_counts=mock_direct, pos=("n",), smoothing=0)

        descendants = set(carnivore.closure(lambda s: s._narrower()))
        descendants.add(carnivore)
        expected_count = sum(mock_direct["n"].get(d, 0) for d in descendants)

        assert ic["n"][carnivore.offset()] == expected_count
