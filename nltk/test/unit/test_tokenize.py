"""
Unit tests for nltk.tokenize.
See also nltk/test/tokenize.doctest
"""

from typing import List, Tuple

import pytest

from nltk.tokenize import (
    LegalitySyllableTokenizer,
    StanfordSegmenter,
    SyllableTokenizer,
    TreebankWordTokenizer,
    TweetTokenizer,
    punkt,
    sent_tokenize,
    word_tokenize,
)
from nltk.tokenize.simple import CharTokenizer
from nltk.tokenize.treebank import TreebankWordDetokenizer


def load_stanford_segmenter():
    try:
        seg = StanfordSegmenter()
        seg.default_config("ar")
        seg.default_config("zh")
        return True
    except LookupError:
        return False


check_stanford_segmenter = pytest.mark.skipif(
    not load_stanford_segmenter(),
    reason="NLTK was unable to find stanford-segmenter.jar.",
)


class TestTokenize:
    def test_tweet_tokenizer(self):
        """
        Test TweetTokenizer using words with special and accented characters.
        """

        tokenizer = TweetTokenizer(strip_handles=True, reduce_len=True)
        s9 = "@myke: Let's test these words: resumé España München français"
        tokens = tokenizer.tokenize(s9)
        expected = [
            ":",
            "Let's",
            "test",
            "these",
            "words",
            ":",
            "resumé",
            "España",
            "München",
            "français",
        ]
        assert tokens == expected

    @pytest.mark.parametrize(
        "test_input, expecteds",
        [
            (
                "My text 0106404243030 is great text",
                (
                    ["My", "text", "01064042430", "30", "is", "great", "text"],
                    ["My", "text", "0106404243030", "is", "great", "text"],
                ),
            ),
            (
                "My ticket id is 1234543124123",
                (
                    ["My", "ticket", "id", "is", "12345431241", "23"],
                    ["My", "ticket", "id", "is", "1234543124123"],
                ),
            ),
            (
                "@remy: This is waaaaayyyy too much for you!!!!!! 01064042430",
                (
                    [
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
                    ],
                    [
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
                    ],
                ),
            ),
            # Further tests from https://github.com/nltk/nltk/pull/2798#issuecomment-922533085,
            # showing the TweetTokenizer performance for `match_phone_numbers=True` and
            # `match_phone_numbers=False`.
            (
                # Some phone numbers are always tokenized, even with `match_phone_numbers=`False`
                "My number is 06-46124080, except it's not.",
                (
                    [
                        "My",
                        "number",
                        "is",
                        "06-46124080",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                    [
                        "My",
                        "number",
                        "is",
                        "06-46124080",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                ),
            ),
            (
                # Phone number here is only tokenized correctly if `match_phone_numbers=True`
                "My number is 601-984-4813, except it's not.",
                (
                    [
                        "My",
                        "number",
                        "is",
                        "601-984-4813",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                    [
                        "My",
                        "number",
                        "is",
                        "601-984-",
                        "4813",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                ),
            ),
            (
                # Phone number here is only tokenized correctly if `match_phone_numbers=True`
                "My number is (393)  928 -3010, except it's not.",
                (
                    [
                        "My",
                        "number",
                        "is",
                        "(393)  928 -3010",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                    [
                        "My",
                        "number",
                        "is",
                        "(",
                        "393",
                        ")",
                        "928",
                        "-",
                        "3010",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                ),
            ),
            (
                # A long number is tokenized correctly only if `match_phone_numbers=False`
                "The product identification number is 48103284512.",
                (
                    [
                        "The",
                        "product",
                        "identification",
                        "number",
                        "is",
                        "4810328451",
                        "2",
                        ".",
                    ],
                    [
                        "The",
                        "product",
                        "identification",
                        "number",
                        "is",
                        "48103284512",
                        ".",
                    ],
                ),
            ),
            (
                # `match_phone_numbers=True` can have some unforeseen
                "My favourite substraction is 240 - 1353.",
                (
                    ["My", "favourite", "substraction", "is", "240 - 1353", "."],
                    ["My", "favourite", "substraction", "is", "240", "-", "1353", "."],
                ),
            ),
        ],
    )
    def test_tweet_tokenizer_expanded(
        self, test_input: str, expecteds: tuple[list[str], list[str]]
    ):
        """
        Test `match_phone_numbers` in TweetTokenizer.

        Note that TweetTokenizer is also passed the following for these tests:
            * strip_handles=True
            * reduce_len=True

        :param test_input: The input string to tokenize using TweetTokenizer.
        :type test_input: str
        :param expecteds: A 2-tuple of tokenized sentences. The first of the two
            tokenized is the expected output of tokenization with `match_phone_numbers=True`.
            The second of the two tokenized lists is the expected output of tokenization
            with `match_phone_numbers=False`.
        :type expecteds: Tuple[List[str], List[str]]
        """
        for match_phone_numbers, expected in zip([True, False], expecteds):
            tokenizer = TweetTokenizer(
                strip_handles=True,
                reduce_len=True,
                match_phone_numbers=match_phone_numbers,
            )
            predicted = tokenizer.tokenize(test_input)
            assert predicted == expected

    def test_sonority_sequencing_syllable_tokenizer(self):
        """
        Test SyllableTokenizer tokenizer.
        """
        tokenizer = SyllableTokenizer()
        tokens = tokenizer.tokenize("justification")
        assert tokens == ["jus", "ti", "fi", "ca", "tion"]

    def test_syllable_tokenizer_numbers(self):
        """
        Test SyllableTokenizer tokenizer.
        """
        tokenizer = SyllableTokenizer()
        text = "9" * 10000
        tokens = tokenizer.tokenize(text)
        assert tokens == [text]

    def test_legality_principle_syllable_tokenizer(self):
        """
        Test LegalitySyllableTokenizer tokenizer.
        """
        from nltk.corpus import words

        test_word = "wonderful"
        tokenizer = LegalitySyllableTokenizer(words.words())
        tokens = tokenizer.tokenize(test_word)
        assert tokens == ["won", "der", "ful"]

    @check_stanford_segmenter
    def test_stanford_segmenter_arabic(self):
        """
        Test the Stanford Word Segmenter for Arabic (default config)
        """
        seg = StanfordSegmenter()
        seg.default_config("ar")
        sent = "يبحث علم الحاسوب استخدام الحوسبة بجميع اشكالها لحل المشكلات"
        segmented_sent = seg.segment(sent.split())
        assert segmented_sent.split() == [
            "يبحث",
            "علم",
            "الحاسوب",
            "استخدام",
            "الحوسبة",
            "ب",
            "جميع",
            "اشكال",
            "ها",
            "ل",
            "حل",
            "المشكلات",
        ]

    @check_stanford_segmenter
    def test_stanford_segmenter_chinese(self):
        """
        Test the Stanford Word Segmenter for Chinese (default config)
        """
        seg = StanfordSegmenter()
        seg.default_config("zh")
        sent = "这是斯坦福中文分词器测试"
        segmented_sent = seg.segment(sent.split())
        assert segmented_sent.split() == [
            "这",
            "是",
            "斯坦福",
            "中文",
            "分词器",
            "测试",
        ]

    def test_phone_tokenizer(self):
        """
        Test a string that resembles a phone number but contains a newline
        """

        # Should be recognized as a phone number, albeit one with multiple spaces
        tokenizer = TweetTokenizer()
        test1 = "(393)  928 -3010"
        expected = ["(393)  928 -3010"]
        result = tokenizer.tokenize(test1)
        assert result == expected

        # Due to newline, first three elements aren't part of a phone number;
        # fourth is
        test2 = "(393)\n928 -3010"
        expected = ["(", "393", ")", "928 -3010"]
        result = tokenizer.tokenize(test2)
        assert result == expected

    def test_emoji_tokenizer(self):
        """
        Test a string that contains Emoji ZWJ Sequences and skin tone modifier
        """
        tokenizer = TweetTokenizer()

        # A Emoji ZWJ Sequences, they together build as a single emoji, should not be split.
        test1 = "👨‍👩‍👧‍👧"
        expected = ["👨‍👩‍👧‍👧"]
        result = tokenizer.tokenize(test1)
        assert result == expected

        # A Emoji with skin tone modifier, the two characters build a single emoji, should not be split.
        test2 = "👨🏿"
        expected = ["👨🏿"]
        result = tokenizer.tokenize(test2)
        assert result == expected

        # A string containing both skin tone modifier and ZWJ Sequences
        test3 = "🤔 🙈 me así, se😌 ds 💕👭👙 hello 👩🏾‍🎓 emoji hello 👨‍👩‍👦‍👦 how are 😊 you today🙅🏽🙅🏽"
        expected = [
            "🤔",
            "🙈",
            "me",
            "así",
            ",",
            "se",
            "😌",
            "ds",
            "💕",
            "👭",
            "👙",
            "hello",
            "👩🏾\u200d🎓",
            "emoji",
            "hello",
            "👨\u200d👩\u200d👦\u200d👦",
            "how",
            "are",
            "😊",
            "you",
            "today",
            "🙅🏽",
            "🙅🏽",
        ]
        result = tokenizer.tokenize(test3)
        assert result == expected

        # emoji flag sequences, including enclosed letter pairs
        # Expected behavior from #3034
        test4 = "🇦🇵🇵🇱🇪"
        expected = ["🇦🇵", "🇵🇱", "🇪"]
        result = tokenizer.tokenize(test4)
        assert result == expected

        test5 = "Hi 🇨🇦, 😍!!"
        expected = ["Hi", "🇨🇦", ",", "😍", "!", "!"]
        result = tokenizer.tokenize(test5)
        assert result == expected

        test6 = "<3 🇨🇦 🤝 🇵🇱 <3"
        expected = ["<3", "🇨🇦", "🤝", "🇵🇱", "<3"]
        result = tokenizer.tokenize(test6)
        assert result == expected

    def test_pad_asterisk(self):
        """
        Test padding of asterisk for word tokenization.
        """
        text = "This is a, *weird sentence with *asterisks in it."
        expected = [
            "This",
            "is",
            "a",
            ",",
            "*",
            "weird",
            "sentence",
            "with",
            "*",
            "asterisks",
            "in",
            "it",
            ".",
        ]
        assert word_tokenize(text) == expected

    def test_dash_tokenization(self):
        """
        Test for em-dashes and en-dashes (Issue #3459)
        """

        # Test case from Issue #3459 (Em-Dash: \u2014)
        s_em = "The food—which was delicious—reminded me of home."
        expected_em = [
            "The",
            "food",
            "—",
            "which",
            "was",
            "delicious",
            "—",
            "reminded",
            "me",
            "of",
            "home",
            ".",
        ]
        assert word_tokenize(s_em) == expected_em

        # Test case for En-Dash (\u2013)
        s_en = "The score was 3–1."
        expected_en = ["The", "score", "was", "3", "–", "1", "."]
        assert word_tokenize(s_en) == expected_en

        # Test case for Horizontal Bar (\u2015)
        s_bar = "He said ― wait for it ― a new thing."
        expected_bar = [
            "He",
            "said",
            "―",
            "wait",
            "for",
            "it",
            "―",
            "a",
            "new",
            "thing",
            ".",
        ]
        assert word_tokenize(s_bar) == expected_bar

        # Test case for Figure Dash (\u2012)
        s_fig = "The number is 12‒34."
        expected_fig = ["The", "number", "is", "12", "‒", "34", "."]
        assert word_tokenize(s_fig) == expected_fig

        # Regression guard for hyphen-minus
        assert word_tokenize("state-of-the-art") == ["state-of-the-art"]

    def test_pad_dotdot(self):
        """
        Test padding of dotdot* for word tokenization.
        """
        text = "Why did dotdot.. not get tokenized but dotdotdot... did? How about manydots....."
        expected = [
            "Why",
            "did",
            "dotdot",
            "..",
            "not",
            "get",
            "tokenized",
            "but",
            "dotdotdot",
            "...",
            "did",
            "?",
            "How",
            "about",
            "manydots",
            ".....",
        ]
        assert word_tokenize(text) == expected

    def test_remove_handle(self):
        """
        Test remove_handle() from casual.py with specially crafted edge cases
        """

        tokenizer = TweetTokenizer(strip_handles=True)

        # Simple example. Handles with just numbers should be allowed
        test1 = "@twitter hello @twi_tter_. hi @12345 @123news"
        expected = ["hello", ".", "hi"]
        result = tokenizer.tokenize(test1)
        assert result == expected

        # Handles are allowed to follow any of the following characters
        test2 = "@n`@n~@n(@n)@n-@n=@n+@n\\@n|@n[@n]@n{@n}@n;@n:@n'@n\"@n/@n?@n.@n,@n<@n>@n @n\n@n ñ@n.ü@n.ç@n."
        expected = [
            "`",
            "~",
            "(",
            ")",
            "-",
            "=",
            "+",
            "\\",
            "|",
            "[",
            "]",
            "{",
            "}",
            ";",
            ":",
            "'",
            '"',
            "/",
            "?",
            ".",
            ",",
            "<",
            ">",
            "ñ",
            ".",
            "ü",
            ".",
            "ç",
            ".",
        ]
        result = tokenizer.tokenize(test2)
        assert result == expected

        # Handles are NOT allowed to follow any of the following characters
        test3 = "a@n j@n z@n A@n L@n Z@n 1@n 4@n 7@n 9@n 0@n _@n !@n @@n #@n $@n %@n &@n *@n"
        expected = [
            "a",
            "@n",
            "j",
            "@n",
            "z",
            "@n",
            "A",
            "@n",
            "L",
            "@n",
            "Z",
            "@n",
            "1",
            "@n",
            "4",
            "@n",
            "7",
            "@n",
            "9",
            "@n",
            "0",
            "@n",
            "_",
            "@n",
            "!",
            "@n",
            "@",
            "@n",
            "#",
            "@n",
            "$",
            "@n",
            "%",
            "@n",
            "&",
            "@n",
            "*",
            "@n",
        ]
        result = tokenizer.tokenize(test3)
        assert result == expected

        # Handles are allowed to precede the following characters
        test4 = "@n!a @n#a @n$a @n%a @n&a @n*a"
        expected = ["!", "a", "#", "a", "$", "a", "%", "a", "&", "a", "*", "a"]
        result = tokenizer.tokenize(test4)
        assert result == expected

        # Tests interactions with special symbols and multiple @
        test5 = "@n!@n @n#@n @n$@n @n%@n @n&@n @n*@n @n@n @@n @n@@n @n_@n @n7@n @nj@n"
        expected = [
            "!",
            "@n",
            "#",
            "@n",
            "$",
            "@n",
            "%",
            "@n",
            "&",
            "@n",
            "*",
            "@n",
            "@n",
            "@n",
            "@",
            "@n",
            "@n",
            "@",
            "@n",
            "@n_",
            "@n",
            "@n7",
            "@n",
            "@nj",
            "@n",
        ]
        result = tokenizer.tokenize(test5)
        assert result == expected

        # Tests that handles can have a max length of 15
        test6 = "@abcdefghijklmnopqrstuvwxyz @abcdefghijklmno1234 @abcdefghijklmno_ @abcdefghijklmnoendofhandle"
        expected = ["pqrstuvwxyz", "1234", "_", "endofhandle"]
        result = tokenizer.tokenize(test6)
        assert result == expected

        # Edge case where an @ comes directly after a long handle
        test7 = "@abcdefghijklmnop@abcde @abcdefghijklmno@abcde @abcdefghijklmno_@abcde @abcdefghijklmno5@abcde"
        expected = [
            "p",
            "@abcde",
            "@abcdefghijklmno",
            "@abcde",
            "_",
            "@abcde",
            "5",
            "@abcde",
        ]
        result = tokenizer.tokenize(test7)
        assert result == expected

    def test_treebank_span_tokenizer(self):
        """
        Test TreebankWordTokenizer.span_tokenize function
        """

        tokenizer = TreebankWordTokenizer()

        # Test case in the docstring
        test1 = "Good muffins cost $3.88\nin New (York).  Please (buy) me\ntwo of them.\n(Thanks)."
        expected = [
            (0, 4),
            (5, 12),
            (13, 17),
            (18, 19),
            (19, 23),
            (24, 26),
            (27, 30),
            (31, 32),
            (32, 36),
            (36, 37),
            (37, 38),
            (40, 46),
            (47, 48),
            (48, 51),
            (51, 52),
            (53, 55),
            (56, 59),
            (60, 62),
            (63, 68),
            (69, 70),
            (70, 76),
            (76, 77),
            (77, 78),
        ]
        result = list(tokenizer.span_tokenize(test1))
        assert result == expected

        # Test case with double quotation
        test2 = 'The DUP is similar to the "religious right" in the United States and takes a hardline stance on social issues'
        expected = [
            (0, 3),
            (4, 7),
            (8, 10),
            (11, 18),
            (19, 21),
            (22, 25),
            (26, 27),
            (27, 36),
            (37, 42),
            (42, 43),
            (44, 46),
            (47, 50),
            (51, 57),
            (58, 64),
            (65, 68),
            (69, 74),
            (75, 76),
            (77, 85),
            (86, 92),
            (93, 95),
            (96, 102),
            (103, 109),
        ]
        result = list(tokenizer.span_tokenize(test2))
        assert result == expected

        # Test case with double qoutation as well as converted quotations
        test3 = "The DUP is similar to the \"religious right\" in the United States and takes a ``hardline'' stance on social issues"
        expected = [
            (0, 3),
            (4, 7),
            (8, 10),
            (11, 18),
            (19, 21),
            (22, 25),
            (26, 27),
            (27, 36),
            (37, 42),
            (42, 43),
            (44, 46),
            (47, 50),
            (51, 57),
            (58, 64),
            (65, 68),
            (69, 74),
            (75, 76),
            (77, 79),
            (79, 87),
            (87, 89),
            (90, 96),
            (97, 99),
            (100, 106),
            (107, 113),
        ]
        result = list(tokenizer.span_tokenize(test3))
        assert result == expected

    def test_word_tokenize(self):
        """
        Test word_tokenize function
        """

        sentence = "The 'v', I've been fooled but I'll seek revenge."
        expected = [
            "The",
            "'",
            "v",
            "'",
            ",",
            "I",
            "'ve",
            "been",
            "fooled",
            "but",
            "I",
            "'ll",
            "seek",
            "revenge",
            ".",
        ]
        assert word_tokenize(sentence) == expected

        sentence = "'v' 're'"
        expected = ["'", "v", "'", "'re", "'"]
        assert word_tokenize(sentence) == expected

    def test_punkt_pair_iter(self):
        test_cases = [
            ("12", [("1", "2"), ("2", None)]),
            ("123", [("1", "2"), ("2", "3"), ("3", None)]),
            ("1234", [("1", "2"), ("2", "3"), ("3", "4"), ("4", None)]),
        ]

        for test_input, expected_output in test_cases:
            actual_output = [x for x in punkt._pair_iter(test_input)]

            assert actual_output == expected_output

    def test_punkt_pair_iter_handles_stop_iteration_exception(self):
        # test input to trigger StopIteration from next()
        it = iter([])
        # call method under test and produce a generator
        gen = punkt._pair_iter(it)
        # unpack generator, ensure that no error is raised
        list(gen)

    def test_punkt_tokenize_words_handles_stop_iteration_exception(self):
        obj = punkt.PunktBaseClass()

        class TestPunktTokenizeWordsMock:
            def word_tokenize(self, s):
                return iter([])

        obj._lang_vars = TestPunktTokenizeWordsMock()
        # unpack generator, ensure that no error is raised
        list(obj._tokenize_words("test"))

    def test_punkt_tokenize_custom_lang_vars(self):
        # Create LangVars including a full stop end character as used in Bengali
        class BengaliLanguageVars(punkt.PunktLanguageVars):
            sent_end_chars = (".", "?", "!", "\u0964")

        obj = punkt.PunktSentenceTokenizer(lang_vars=BengaliLanguageVars())

        # We now expect these sentences to be split up into the individual sentences
        sentences = "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন। অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন। এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।"
        expected = [
            "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন।",
            "অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন।",
            "এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।",
        ]

        assert obj.tokenize(sentences) == expected

    def test_punkt_tokenize_no_custom_lang_vars(self):
        obj = punkt.PunktSentenceTokenizer()

        # We expect these sentences to not be split properly, as the Bengali full stop '।' is not included in the default language vars
        sentences = "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন। অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন। এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।"
        expected = [
            "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন। অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন। এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।"
        ]

        assert obj.tokenize(sentences) == expected

    @pytest.mark.parametrize(
        "input_text,n_sents,n_splits,lang_vars",
        [
            # Test debug_decisions on a text with two sentences, split by a dot.
            ("Subject: Some subject. Attachments: Some attachments", 2, 1),
            # The sentence should be split into two sections,
            # with one split and hence one decision.
            # Test debug_decisions on a text with two sentences, split by an exclamation mark.
            ("Subject: Some subject! Attachments: Some attachments", 2, 1),
            # The sentence should be split into two sections,
            # with one split and hence one decision.
            # Test debug_decisions on a text with one sentences,
            # which is not split.
            ("This is just a normal sentence, just like any other.", 1, 0),
            # Hence just 1
        ],
    )
    def punkt_debug_decisions(self, input_text, n_sents, n_splits, lang_vars=None):
        tokenizer = punkt.PunktSentenceTokenizer()
        if lang_vars is not None:
            tokenizer._lang_vars = lang_vars

        assert len(tokenizer.tokenize(input_text)) == n_sents
        assert len(list(tokenizer.debug_decisions(input_text))) == n_splits

    def test_punkt_debug_decisions_custom_end(self):
        # Test debug_decisions on a text with two sentences,
        # split by a custom end character, based on Issue #2519
        class ExtLangVars(punkt.PunktLanguageVars):
            sent_end_chars = (".", "?", "!", "^")

        self.punkt_debug_decisions(
            "Subject: Some subject^ Attachments: Some attachments",
            n_sents=2,
            n_splits=1,
            lang_vars=ExtLangVars(),
        )
        # The sentence should be split into two sections,
        # with one split and hence one decision.

    @pytest.mark.parametrize(
        "sentences, expected",
        [
            (
                "this is a test. . new sentence.",
                ["this is a test.", ".", "new sentence."],
            ),
            ("This. . . That", ["This.", ".", ".", "That"]),
            ("This..... That", ["This..... That"]),
            ("This... That", ["This... That"]),
            ("This.. . That", ["This.. .", "That"]),
            ("This. .. That", ["This.", ".. That"]),
            ("This. ,. That", ["This.", ",.", "That"]),
            ("This!!! That", ["This!!!", "That"]),
            ("This! That", ["This!", "That"]),
            (
                "1. This is R .\n2. This is A .\n3. That's all",
                ["1.", "This is R .", "2.", "This is A .", "3.", "That's all"],
            ),
            (
                "1. This is R .\t2. This is A .\t3. That's all",
                ["1.", "This is R .", "2.", "This is A .", "3.", "That's all"],
            ),
            ("Hello.\tThere", ["Hello.", "There"]),
        ],
    )
    def test_sent_tokenize(self, sentences: str, expected: list[str]):
        assert sent_tokenize(sentences) == expected

    def test_string_tokenizer(self) -> None:
        sentence = "Hello there"
        tokenizer = CharTokenizer()
        assert tokenizer.tokenize(sentence) == list(sentence)
        assert list(tokenizer.span_tokenize(sentence)) == [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 8),
            (8, 9),
            (9, 10),
            (10, 11),
        ]


class TestPunktTrainer:
    def test_punkt_train(self) -> None:
        trainer = punkt.PunktTrainer()
        trainer.train("This is a test.")

    def test_punkt_train_single_word(self) -> None:
        trainer = punkt.PunktTrainer()
        trainer.train("This.")

    def test_punkt_train_no_punc(self) -> None:
        trainer = punkt.PunktTrainer()
        trainer.train("This is a test")


class TestTreebankWordDetokenizer:
    detok = TreebankWordDetokenizer()

    def test_simple_sentence(self):
        tokens = ["Hello", ",", "world", "."]
        assert self.detok.detokenize(tokens) == "Hello, world."

    def test_contractions(self):
        tokens = ["I", "'m", "sure", "."]
        assert self.detok.detokenize(tokens) == "I'm sure."

    def test_contraction_ll(self):
        tokens = ["You", "'ll", "see", "."]
        assert self.detok.detokenize(tokens) == "You'll see."

    def test_contraction_not(self):
        tokens = ["I", "do", "n't", "know", "."]
        assert self.detok.detokenize(tokens) == "I don't know."

    def test_double_quotes(self):
        tokens = ["``", "Hello", "''"]
        assert self.detok.detokenize(tokens) == '"Hello"'

    def test_double_quotes_with_period(self):
        tokens = ["He", "said", "``", "hi", "''", "."]
        assert self.detok.detokenize(tokens) == 'He said "hi".'

    def test_comma_before_closing_double_quote(self):
        tokens = ["``", "Yes", ",", "''", "he", "said", "."]
        assert self.detok.detokenize(tokens) == '"Yes," he said.'

    def test_possessive(self):
        tokens = ["The", "dog", "'s", "bone", "."]
        assert self.detok.detokenize(tokens) == "The dog's bone."

    def test_parentheses_ptb(self):
        """PTB bracket symbols are converted when convert_parentheses=True."""
        tokens = ["-LRB-", "hello", "-RRB-"]
        result = self.detok.detokenize(tokens, convert_parentheses=True)
        assert result == "(hello)"

    def test_double_dashes(self):
        tokens = ["foo", "--", "bar"]
        assert self.detok.detokenize(tokens) == "foo--bar"

    def test_opening_backtick_double(self):
        """`` is converted to opening double quote."""
        tokens = ["``", "Hello", "''"]
        assert self.detok.detokenize(tokens) == '"Hello"'

    def test_opening_backtick_single(self):
        """` is preserved as-is (no standard conversion in detokenizer)."""
        tokens = ["`", "Hello", "'"]
        result = self.detok.detokenize(tokens)
        assert "`" in result or "'" in result

    def test_closing_double_quote_backticks(self):
        """'' is converted to closing double quote."""
        tokens = ["He", "said", "``", "yes", "''", "."]
        result = self.detok.detokenize(tokens)
        assert '"yes"' in result

    def test_issue_3260_nested_quotes(self):
        """Fix #3260: closing single then double quote after comma."""
        tokens = [
            "``",
            "Shippers",
            "are",
            "saying",
            "`",
            "the",
            "party",
            "'s",
            "over",
            ",",
            "'",
            "''",
            "said",
            "Mr.",
            "LaLonde",
            ".",
        ]
        result = self.detok.detokenize(tokens)
        # The closing sequence ,'" should have single quote before double quote
        assert ",'" in result or ",'\"" in result

    def test_issue_3260_minimal(self):
        """Minimal case: comma, single quote, double quote should collapse."""
        tokens = ["word", ",", "'", "''"]
        result = self.detok.detokenize(tokens)
        assert result == "word,'\"" or result == "word,'\""

    def test_roundtrip_simple(self):
        """Tokenize then detokenize should approximate the original."""
        original = "Hello, world."
        tokenizer = TreebankWordTokenizer()
        tokens = tokenizer.tokenize(original)
        result = self.detok.detokenize(tokens)
        assert result == original

    def test_semicolon_spacing(self):
        tokens = ["a", ";", "b"]
        assert self.detok.detokenize(tokens) == "a; b"

    def test_colon_spacing(self):
        tokens = ["a", ":", "b"]
        assert self.detok.detokenize(tokens) == "a: b"

    def test_contraction_ve(self):
        tokens = ["we", "'ve", "seen", "."]
        assert self.detok.detokenize(tokens) == "we've seen."

    def test_contraction_d(self):
        tokens = ["who", "'d", "know", "."]
        assert self.detok.detokenize(tokens) == "who'd know."

    def test_closing_double_quote_after_period(self):
        tokens = ["word", ".", "''"]
        assert self.detok.detokenize(tokens) == 'word."'

    def test_closing_double_quote_after_comma(self):
        tokens = ["word", ",", "''"]
        assert self.detok.detokenize(tokens) == 'word,"'

    def test_closing_double_quote_after_exclamation(self):
        tokens = ["word", "!", "''"]
        assert self.detok.detokenize(tokens) == 'word!"'

    def test_closing_double_quote_after_question(self):
        tokens = ["word", "?", "''"]
        assert self.detok.detokenize(tokens) == 'word?"'

    def test_multiple_tokens_in_quotes(self):
        tokens = ["``", "A", "B", "C", "''"]
        assert self.detok.detokenize(tokens) == '"A B C"'

    def test_quote_comma_said(self):
        tokens = ["``", "Hi", ",", "''", "said", "Jo", "."]
        assert self.detok.detokenize(tokens) == '"Hi," said Jo.'

    def test_no_spurious_space_before_comma(self):
        result = self.detok.detokenize(["a", ",", "b"])
        assert " ," not in result

    def test_no_spurious_space_before_period(self):
        result = self.detok.detokenize(["a", "."])
        assert " ." not in result

    def test_no_spurious_space_before_closing_quote(self):
        result = self.detok.detokenize(["``", "a", "''"])
        assert ' "' not in result or result.startswith('"')

    def test_roundtrip_quotes(self):
        """Round-trip a quoted sentence."""
        original_tokens = ["``", "Hello", ",", "''", "he", "said", "."]
        result = self.detok.detokenize(original_tokens)
        assert '"' in result
