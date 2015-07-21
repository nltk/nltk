# Natural Language Toolkit: Product Reviews Corpus Reader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
CorpusReader for the Customer Review corpus.

- Customer Review Corpus information -
Annotated by: Minqing Hu and Bing Liu, 2004.
    Department of Computer Sicence
    University of Illinois at Chicago

Contact: Bing Liu, liub@cs.uic.edu
        http://www.cs.uic.edu/~liub

Distributed with permission.

The dataset contains annotated customer reviews of 5 products from amazon.com.

    1. digital camera: Canon G3
    2. digital camera: Nikon coolpix 4300
    3. celluar phone:  Nokia 6610
    4. mp3 player:     Creative Labs Nomad Jukebox Zen Xtra 40GB
    5. dvd player:     Apex AD2600 Progressive-scan DVD player

Related papers:
- Minqing Hu and Bing Liu. "Mining and summarizing customer reviews".
    Proceedings of the ACM SIGKDD International Conference on Knowledge
    Discovery & Data Mining (KDD-04), 2004.

- Minqing Hu and Bing Liu. "Mining Opinion Features in Customer Reviews."
    Proceedings of Nineteeth National Conference on Artificial Intelligence
    (AAAI-2004), 2004.

Symbols used in the annotated reviews:

    [t] : the title of the review: Each [t] tag starts a review.
    xxxx[+|-n]: xxxx is a product feature.
    [+n]: Positive opinion, n is the opinion strength: 3 strongest, and 1 weakest.
          Note that the strength is quite subjective.
          You may want ignore it, but only considering + and -
    [-n]: Negative opinion
    ##  : start of each sentence. Each line is a sentence.
    [u] : feature not appeared in the sentence.
    [p] : feature not appeared in the sentence. Pronoun resolution is needed.
    [s] : suggestion or recommendation.
    [cc]: comparison with a competing product from a different brand.
    [cs]: comparison with a competing product from the same brand.
"""
import re

from nltk.compat import string_types
from nltk.corpus.reader.api import *
from nltk.tokenize import *

TITLE    = re.compile(r'^\[t\](.*)$') # [t] Title
FEATURES = re.compile(r'((?:(?:\w+\s)+)?\w+)\[((?:\+|\-)\d)\]') # find 'feature' in feature[+3]
NOTES    = re.compile(r'\[(?!t)(p|u|s|cc|cs)\]') # find 'p' in camera[+2][p]
SENT     = re.compile(r'##(.*)$') # find tokenized sentence


@compat.python_2_unicode_compatible
class Review(object):
    def __init__(self, title=None, review_lines=None):
        self.title = title
        if review_lines is None:
            self.review_lines = []
        else:
            self.review_lines = review_lines

    def add_line(self, review_line):
        """
        Add a line (ReviewLine) to the review
        """
        assert type(review_line) == ReviewLine
        self.review_lines.append(review_line)

    def features(self):
        """
        :return: all features of the review as a list of tuples (feat, score)
        :rtype: list(tuple)
        """
        features = []
        for review_line in self.review_lines:
            features.extend(review_line.features)
        return features

    def sents(self):
        """
        :return: all sentences of the review as lists of tokens
        :rtype: list(list(str))
        """
        return [review_line.sent for review_line in self.review_lines]

    def __repr__(self):
        return ('Review(title=\"{}\", review_lines={})'.format(self.title, self.review_lines))


@compat.python_2_unicode_compatible
class ReviewLine(object):
    """
    A ReviewLine represents a sentence of the review, together with (optional)
    annotations of its features and notes about the reviewed product.
    """
    def __init__(self, sent, features=[], notes=[]):
        self.sent = sent
        self.features = features
        self.notes = notes

    def __repr__(self):
        return ('ReviewLine(features={}, notes={}, sent={})'.format(
            self.features, self.notes, self.sent))


class ProductReviewsCorpusReader(CorpusReader):
    """
    Reader for the Customer Review Data dataset by Hu, Liu (2004).
    Note: we are not applying any sentence tokenization at the moment, just word
    tokenization.

        >>> root = "/home/fievelk/nltk_data/corpora/product_reviews"
        >>> product_reviews = ProductReviewsCorpusReader(root, r'^(?!Readme).*.txt', encoding='utf8')
        >>> camera_reviews = product_reviews.reviews('Canon G3.txt')
        >>> review = camera_reviews[0]
        >>> review.sents()[0]
        ['i', 'recently', 'purchased', 'the', 'canon', 'powershot', 'g3', 'and', 'am',
        'extremely', 'satisfied', 'with', 'the', 'purchase', '.']
        >>> review.features()
        [('canon powershot g3', '+3'), ('use', '+2'), ('picture', '+2'),
        ('picture quality', '+1'), ('picture quality', '+1'), ('camera', '+2'),
        ('use', '+2'), ('feature', '+1'), ('picture quality', '+3'), ('use', '+1'),
        ('option', '+1')]

    We can also reach the same information directly from the stream:

        >>> product_reviews.features('Canon G3.txt')
        [('canon powershot g3', '+3'), ('use', '+2'), ...]

    We can compute stats for specific product features:

        >>> n_reviews = len([(feat,score) for (feat,score) in product_reviews.features('Canon G3.txt') if feat=='picture'])
        >>> tot = sum([int(score) for (feat,score) in product_reviews.features('Canon G3.txt') if feat=='picture'])
        >>> mean = tot/n_reviews
        >>> print(n_reviews, tot, mean)
        15 24 1.6
    """
    CorpusView = StreamBackedCorpusView

    def __init__(self, root, fileids,
                word_tokenizer=WordPunctTokenizer(),
                encoding='utf8'):

        CorpusReader.__init__(self, root, fileids, encoding)
        self._word_tokenizer = word_tokenizer

    def features(self, fileids=None):
        """
        :return: all features for the product(s) in the given file(s).
        :rtype: list(tuple)
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, string_types): fileids = [fileids]
        return concat([self.CorpusView(fileid, self._read_features,
                                              encoding=enc)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def raw(self, fileids=None):
        """
        :return: the given file(s) as a single string.
        :rtype: str
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, string_types): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def readme(self):
        """
        Return the contents of the corpus Readme.txt file.
        """
        return self.open("Readme.txt").read()

    def reviews(self, fileids=None):
        """
        :return: the given file(s) as a list of reviews.
        """
        if fileids is None: fileids = self._fileids
        return concat([self.CorpusView(fileid, self._read_review_block,
                                              encoding=enc)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def sents(self, fileids=None):
        """
        :return: the given file(s) as a list of sentences, each encoded as a
            list of word strings.
        :rtype: list(list(str))
        """
        return concat([self.CorpusView(path, self._read_sent_block, encoding=enc)
                       for (path, enc, fileid)
                       in self.abspaths(fileids, True, True)])

    def words(self, fileids=None):
        """
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        return concat([self.CorpusView(path, self._read_word_block, encoding=enc)
                       for (path, enc, fileid)
                       in self.abspaths(fileids, True, True)])

    def _read_features(self, stream):
        features = []
        for i in range(20):
            line = stream.readline()
            if not line: return features
            features.extend(re.findall(FEATURES, line))
        return features

    def _read_review_block(self, stream):
        while True:
            line = stream.readline()
            if not line: return [] # end of file.
            title_match = re.match(TITLE, line)
            if title_match:
                review = Review(title=title_match.group(1).strip()) # We create a new review
                break

        # Scan until we find another line matching the regexp, or EOF.
        while True:
            oldpos = stream.tell()
            line = stream.readline()
            # End of file:
            if not line:
                return [review]
            # Start of a new review: backup to just before it starts, and
            # return the review we've already collected.
            if re.match(TITLE, line):
                stream.seek(oldpos)
                return [review]
            # Anything else is part of the review line.
            feats = re.findall(FEATURES, line)
            notes = re.findall(NOTES, line)
            sent = re.findall(SENT, line)
            if sent:
                sent = self._word_tokenizer.tokenize(sent[0])
            review_line = ReviewLine(sent=sent, features=feats, notes=notes)
            review.add_line(review_line)

    def _read_sent_block(self, stream):
        sents = []
        for review in self._read_review_block(stream):
            sents.extend([sent for sent in review.sents()])
        return sents

    def _read_word_block(self, stream):
        words = []
        for i in range(20): # Read 20 lines at a time.
            line = stream.readline()
            sent = re.findall(SENT, line)
            if sent:
                words.extend(self._word_tokenizer.tokenize(sent[0]))
        return words
