import unittest
from nltk import ConditionalFreqDist

class TestEmptyCondFreq(unittest.TestCase):
    def test_tabulate(self):
        empty = ConditionalFreqDist()
        self.assertEqual(empty.conditions(),[])
        try:
            empty.tabulate(conditions="BUG") # nonexistent keys shouldn't be added
        except:
            pass
        self.assertEqual(empty.conditions(), [])


    def test_plot(self):
        empty = ConditionalFreqDist()
        self.assertEqual(empty.conditions(),[])
        try:
            empty.plot(conditions="BUG") # nonexistent keys shouldn't be added
        except:
            pass
        self.assertEqual(empty.conditions(),[])
