import unittest

from nltk.metrics import masi_distance
from nltk.metrics.agreement import AnnotationTask


class TestDisagreement(unittest.TestCase):
    """
    Class containing unit tests for nltk.metrics.agreement.Disagreement.
    """

    def test_easy(self):
        """
        Simple test, based on
        https://github.com/foolswood/krippendorffs_alpha/raw/master/krippendorff.pdf.
        """
        data = [
            ("coder1", "dress1", "YES"),
            ("coder2", "dress1", "NO"),
            ("coder3", "dress1", "NO"),
            ("coder1", "dress2", "YES"),
            ("coder2", "dress2", "NO"),
            ("coder3", "dress3", "NO"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), -0.3333333)

    def test_easy2(self):
        """
        Same simple test with 1 rating removed.
        Removal of that rating should not matter: K-Apha ignores items with
        only 1 rating.
        """
        data = [
            ("coder1", "dress1", "YES"),
            ("coder2", "dress1", "NO"),
            ("coder3", "dress1", "NO"),
            ("coder1", "dress2", "YES"),
            ("coder2", "dress2", "NO"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), -0.3333333)

    def test_easy3(self):
        """
        If expected disagreement is 0, K-Apha should be 1.
        """
        data = [
            ("coder1", "1", 1),
            ("coder2", "1", 1),
            ("coder1", "2", 2),
            ("coder2", "2", 2),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 1.0)

        data = [("coder1", "1", 1), ("coder2", "1", 1), ("coder1", "2", 2)]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 1.0)

    def test_perfect_agreement_coefficients(self):
        data = [
            ("coder1", "1", "YES"),
            ("coder2", "1", "YES"),
            ("coder1", "2", "YES"),
            ("coder2", "2", "YES"),
        ]
        annotation_task = AnnotationTask(data)

        self.assertAlmostEqual(annotation_task.S(), 1.0)
        self.assertAlmostEqual(annotation_task.pi(), 1.0)
        self.assertAlmostEqual(annotation_task.kappa(), 1.0)
        self.assertAlmostEqual(annotation_task.multi_kappa(), 1.0)

    def test_advanced(self):
        """
        More advanced test, based on
        http://www.agreestat.com/research_papers/onkrippendorffalpha.pdf
        """
        data = [
            ("A", "1", "1"),
            ("B", "1", "1"),
            ("D", "1", "1"),
            ("A", "2", "2"),
            ("B", "2", "2"),
            ("C", "2", "3"),
            ("D", "2", "2"),
            ("A", "3", "3"),
            ("B", "3", "3"),
            ("C", "3", "3"),
            ("D", "3", "3"),
            ("A", "4", "3"),
            ("B", "4", "3"),
            ("C", "4", "3"),
            ("D", "4", "3"),
            ("A", "5", "2"),
            ("B", "5", "2"),
            ("C", "5", "2"),
            ("D", "5", "2"),
            ("A", "6", "1"),
            ("B", "6", "2"),
            ("C", "6", "3"),
            ("D", "6", "4"),
            ("A", "7", "4"),
            ("B", "7", "4"),
            ("C", "7", "4"),
            ("D", "7", "4"),
            ("A", "8", "1"),
            ("B", "8", "1"),
            ("C", "8", "2"),
            ("D", "8", "1"),
            ("A", "9", "2"),
            ("B", "9", "2"),
            ("C", "9", "2"),
            ("D", "9", "2"),
            ("B", "10", "5"),
            ("C", "10", "5"),
            ("D", "10", "5"),
            ("C", "11", "1"),
            ("D", "11", "1"),
            ("C", "12", "3"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 0.743421052632)

    def test_advanced2(self):
        """
        Same more advanced example, but with 1 rating removed.
        Again, removal of that 1 rating should not matter.
        """
        data = [
            ("A", "1", "1"),
            ("B", "1", "1"),
            ("D", "1", "1"),
            ("A", "2", "2"),
            ("B", "2", "2"),
            ("C", "2", "3"),
            ("D", "2", "2"),
            ("A", "3", "3"),
            ("B", "3", "3"),
            ("C", "3", "3"),
            ("D", "3", "3"),
            ("A", "4", "3"),
            ("B", "4", "3"),
            ("C", "4", "3"),
            ("D", "4", "3"),
            ("A", "5", "2"),
            ("B", "5", "2"),
            ("C", "5", "2"),
            ("D", "5", "2"),
            ("A", "6", "1"),
            ("B", "6", "2"),
            ("C", "6", "3"),
            ("D", "6", "4"),
            ("A", "7", "4"),
            ("B", "7", "4"),
            ("C", "7", "4"),
            ("D", "7", "4"),
            ("A", "8", "1"),
            ("B", "8", "1"),
            ("C", "8", "2"),
            ("D", "8", "1"),
            ("A", "9", "2"),
            ("B", "9", "2"),
            ("C", "9", "2"),
            ("D", "9", "2"),
            ("B", "10", "5"),
            ("C", "10", "5"),
            ("D", "10", "5"),
            ("C", "11", "1"),
            ("D", "11", "1"),
            ("C", "12", "3"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 0.743421052632)


class TestMissingValues(unittest.TestCase):
    """Krippendorff's alpha with missing data (issues #2865, #2732).

    Missing data is represented by omitting the (coder, item, label) triple, or
    by declaring placeholder label values via ``missing_values``. A placeholder
    must not be counted as a real category.
    """

    #: Three coders, three items; every present rating agrees, some are missing.
    RATINGS = {"1": [1, 1, 2], "2": [1, 1, None], "3": [None, 1, 2]}

    def _task(self, sentinel="drop", **kwargs):
        data = [
            [coder, str(item), rating]
            for coder, ratings in self.RATINGS.items()
            for item, rating in enumerate(ratings)
            if not (sentinel == "drop" and rating is None)
        ]
        return AnnotationTask(data=data, **kwargs)

    def test_placeholder_counted_as_category_without_missing_values(self):
        # Backward compatible: None is a real label, so agreement drops.
        self.assertAlmostEqual(self._task(sentinel=None).alpha(), 0.33333333333333)

    def test_missing_values_recovers_full_agreement(self):
        # Declaring the placeholder as missing gives the expected alpha of 1.
        self.assertAlmostEqual(
            self._task(sentinel=None, missing_values=[None]).alpha(), 1.0
        )

    def test_omitting_triples_is_equivalent(self):
        # Omitting the missing triples entirely is the same as declaring them.
        self.assertAlmostEqual(self._task(sentinel="drop").alpha(), 1.0)

    def test_string_placeholder(self):
        # A caller that stringifies labels turns None into "None"; that string
        # can be declared missing too.
        data = [
            [coder, str(item), str(rating)]
            for coder, ratings in self.RATINGS.items()
            for item, rating in enumerate(ratings)
        ]
        self.assertAlmostEqual(
            AnnotationTask(data=data, missing_values=["None"]).alpha(), 1.0
        )

    def test_masi_multilabel_with_missing(self):
        # The #2732 use case: multi-label sets with the MASI distance.
        ratings = {
            "1": [frozenset(["a"]), frozenset(["a", "b"])],
            "2": [frozenset(["a"]), None],
            "3": [None, frozenset(["a", "b"])],
        }
        data = [
            [coder, i, rating]
            for coder, rs in ratings.items()
            for i, rating in enumerate(rs)
            if rating is not None
        ]
        task = AnnotationTask(data=data, distance=masi_distance)
        self.assertAlmostEqual(task.alpha(), 1.0)

    def test_missing_values_does_not_change_complete_data(self):
        # A no-op when nothing matches the placeholder: identical to no arg.
        data = [
            ("coder1", "dress1", "YES"),
            ("coder2", "dress1", "NO"),
            ("coder3", "dress1", "NO"),
            ("coder1", "dress2", "YES"),
            ("coder2", "dress2", "NO"),
            ("coder3", "dress3", "NO"),
        ]
        self.assertAlmostEqual(
            AnnotationTask(data, missing_values=[None]).alpha(),
            AnnotationTask(data).alpha(),
        )

    def test_all_missing_raises_cleanly(self):
        data = [("c1", "i1", None), ("c2", "i1", None)]
        with self.assertRaises(ValueError):
            AnnotationTask(data, missing_values=[None]).alpha()

    def test_unhashable_placeholder_rejected_at_construction(self):
        with self.assertRaises(TypeError):
            AnnotationTask(data=[], missing_values=[[1, 2]])
