# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Regression tests for `json2csv()` and `json2csv_entities()` in Twitter
package.

"""

import os
from nltk.compat import TemporaryDirectory
import unittest

from nltk.corpus import twitter_samples
from nltk.twitter.common import json2csv, json2csv_entities
from nltk.compat import izip


def are_files_identical(filename1, filename2, debug=False):
    """
    Compare two files, ignoring carriage returns.
    """
    with open(filename1, "rb") as fileA:
        with open(filename2, "rb") as fileB:
            result = True
            for lineA, lineB in izip(sorted(fileA.readlines()),
                                     sorted(fileB.readlines())):
                if lineA.strip() != lineB.strip():
                    if debug:
                        print("Error while comparing files. " +
                              "First difference at line below.")
                        print("=> Output file line: {0}".format(lineA))
                        print("=> Refer. file line: {0}".format(lineB))
                    result = False
                    break
            return result


class TestJSON2CSV(unittest.TestCase):

    def setUp(self):
        with open(twitter_samples.abspath("tweets.20150430-223406.json")) as infile:
            self.infile = [next(infile) for x in range(100)]
        infile.close()
        self.msg = "Test and reference files are not the same"
        self.subdir = os.path.join(os.path.dirname(__file__), 'files')

    def tearDown(self):
        return

    def test_textoutput(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.text.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.text.csv')
            json2csv(self.infile, outfn, ['text'], gzip_compress=False)
            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_metadata(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.tweet.csv.ref')
        fields = ['created_at', 'favorite_count', 'id',
                  'in_reply_to_status_id', 'in_reply_to_user_id', 'retweet_count',
                  'retweeted', 'text', 'truncated', 'user.id']

        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.tweet.csv')
            json2csv(self.infile, outfn, fields, gzip_compress=False)
            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_user_metadata(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.user.csv.ref')
        fields = ['id', 'text', 'user.id', 'user.followers_count', 'user.friends_count']

        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.user.csv')
            json2csv(self.infile, outfn, fields, gzip_compress=False)
            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_hashtag(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.hashtag.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.hashtag.csv')
            json2csv_entities(self.infile, outfn,
                              ['id', 'text'], 'hashtags', ['text'],
                              gzip_compress=False)
            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_usermention(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.usermention.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.usermention.csv')
            json2csv_entities(self.infile, outfn,
                              ['id', 'text'], 'user_mentions', ['id', 'screen_name'],
                              gzip_compress=False)
            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_media(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.media.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.media.csv')
            json2csv_entities(self.infile, outfn,
                              ['id'], 'media', ['media_url', 'url'],
                              gzip_compress=False)

            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_url(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.url.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.url.csv')
            json2csv_entities(self.infile, outfn,
                              ['id'], 'urls', ['url', 'expanded_url'],
                              gzip_compress=False)

            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_userurl(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.userurl.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.userurl.csv')
            json2csv_entities(self.infile, outfn, ['id', 'screen_name'],
                              'user.urls', ['url', 'expanded_url'],
                              gzip_compress=False)

            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_place(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.place.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.place.csv')
            json2csv_entities(self.infile, outfn,
                              ['id', 'text'], 'place', ['name', 'country'],
                              gzip_compress=False)

            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_tweet_place_boundingbox(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.placeboundingbox.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.placeboundingbox.csv')
            json2csv_entities(self.infile, outfn,
                              ['id', 'name'], 'place.bounding_box', ['coordinates'],
                              gzip_compress=False)

            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_retweet_original_tweet(self):
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.retweet.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.retweet.csv')
            json2csv_entities(self.infile, outfn, ['id'], 'retweeted_status',
                              ['created_at', 'favorite_count', 'id', 'in_reply_to_status_id',
                               'in_reply_to_user_id', 'retweet_count', 'text', 'truncated',
                               'user.id'],
                              gzip_compress=False)

            self.assertTrue(are_files_identical(outfn, ref_fn), msg=self.msg)


    def test_file_is_wrong(self):
        """
        Sanity check that file comparison is not giving false positives.
        """
        ref_fn = os.path.join(self.subdir, 'tweets.20150430-223406.retweet.csv.ref')
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.text.csv')
            json2csv(self.infile, outfn, ['text'], gzip_compress=False)
            self.assertFalse(are_files_identical(outfn, ref_fn), msg=self.msg)



if __name__ == "__main__":
    unittest.main()
