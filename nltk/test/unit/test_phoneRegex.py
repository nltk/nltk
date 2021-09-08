import unittest

from nltk.tokenize.casual import TweetTokenizer

tokenizer1 = TweetTokenizer(
    strip_handles=True, reduce_len=True, phone_number_regex=True
)
tokenizer2 = TweetTokenizer(strip_handles=True, reduce_len=True)
Testcase1 = "My text 0106404243030"
Testcase2 = "My ticket id is 1234543124123"
Testcase3 = "@remy: This is waaaaayyyy too much for you!!!!!! 01064042430"

expectedTestcase1_true = ["My", "text", "01064042430", "30"]
expectedTestcase2_true = ["My", "ticket", "id", "is", "12345431241", "23"]
expectedTestcase3_true = [
    ":",
    "This",
    "is",
    "waaayyy",
    "too",
    "much",
    "for",
    "you",
    "!",
    "!",
    "!",
    "01064042430",
]
expectedTestcase1_false = ["My", "text", "0106404243030"]
expectedTestcase2_false = ["My", "ticket", "id", "is", "1234543124123"]
expectedTestcase3_false = [
    ":",
    "This",
    "is",
    "waaayyy",
    "too",
    "much",
    "for",
    "you",
    "!",
    "!",
    "!",
    "01064042430",
]


class tweetTokenizer(unittest.TestCase):
    def test_truePhoneRegex(self):
        self.assertEqual(tokenizer1.tokenize(Testcase1), expectedTestcase1_true)
        self.assertEqual(tokenizer1.tokenize(Testcase2), expectedTestcase2_true)
        self.assertEqual(tokenizer1.tokenize(Testcase3), expectedTestcase3_true)

    def test_falsePhoneRegex(self):
        self.assertEqual(tokenizer2.tokenize(Testcase1), expectedTestcase1_false)
        self.assertEqual(tokenizer2.tokenize(Testcase2), expectedTestcase2_false)
        self.assertEqual(tokenizer2.tokenize(Testcase3), expectedTestcase3_false)


if __name__ == "__main__":
    unittest.main()
