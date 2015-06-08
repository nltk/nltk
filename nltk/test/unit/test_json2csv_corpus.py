# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT


import os
from nltk.compat import TemporaryDirectory
import unittest

from nltk.corpus import tweets
from nltk.twitter.util import json2csv, json2csv_entities

from itertools import izip

'''
compare files ignoring carriage return
from: http://stackoverflow.com/questions/3280317/best-way-to-check-new-line-independent-identity-of-2-files-with-python
'''
def areFilesIdentical(filename1, filename2):
    with open(filename1, "rtU") as a:
        with open(filename2, "rtU") as b:
            # Note that "all" and "izip" are lazy
            # (will stop at the first line that's not identical)
            return all(lineA == lineB
                       for lineA, lineB in izip(a.xreadlines(), b.xreadlines()))
                           
class Test(unittest.TestCase):

    def setUp(self):
        with open(tweets.abspath("tweets.20150430-223406.json")) as infile:    
            self.infile = [next(infile) for x in xrange(100)]
        infile.close()


    def tearDown(self):
        return
        


    def test_textoutput(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.text.csv')
            json2csv(self.infile, outfn, ['text'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.text.csv.ref'),\
                              'Error in csv file'

    def test_tweet_metadata(self):
        fields = ['created_at', 'favorite_count', 'id',
                  'in_reply_to_status_id', 'in_reply_to_user_id', 'retweet_count',
                  'retweeted', 'text', 'truncated', {'user' : 'id'}]

        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.tweet.csv')
            json2csv(self.infile, outfn, fields)

            assert areFilesIdentical(outfn, 'tweets.20150430-223406.tweet.csv.ref'),\
                   'Error in csv file'

    def test_user_metadata(self):
        fields = ['id', 'text', {'user' : ['id', 'followers_count', 'friends_count']}]

        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.user.csv')
            json2csv(self.infile, outfn, fields)

            assert areFilesIdentical(outfn, 'tweets.20150430-223406.user.csv.ref'),\
                   'Error in csv file'

    def test_tweet_hashtag(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.hashtag.csv')   
            json2csv_entities(self.infile, outfn,
                                  ['id', 'text'], 'hashtags', ['text'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.hashtag.csv.ref'),\
                       'Error in csv file'

    def test_tweet_usermention(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.usermention.csv')
            json2csv_entities(self.infile, outfn,
                                  ['id', 'text'], 'user_mentions', ['id', 'screen_name'])
    
            assert areFilesIdentical(outfn,
                               'tweets.20150430-223406.usermention.csv.ref'), 'Error in csv file'

    def test_tweet_media(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.media.csv')
            json2csv_entities(self.infile, outfn,
                                  ['id'], 'media', ['media_url', 'url'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.media.csv.ref'),\
                       'Error in csv file'

    def test_tweet_url(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.url.csv')
            json2csv_entities(self.infile, outfn,
                                  ['id'], 'urls', ['url', 'expanded_url'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.url.csv.ref'),\
                       'Error in csv file'

    def test_userurl(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.userurl.csv')
            json2csv_entities(self.infile, outfn, ['id', 'screen_name'],
                                  {'user' : 'urls'}, ['url', 'expanded_url'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.userurl.csv.ref'),\
                       'Error in csv file'

    def test_tweet_place(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.place.csv')
            json2csv_entities(self.infile, outfn,
                                  ['id', 'text'], 'place', ['name', 'country'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.place.csv.ref'),\
                       'Error in csv file'

    def test_tweet_place_boundingbox(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.placeboundingbox.csv')  
            json2csv_entities(self.infile, outfn,
                                  ['id', 'name'], {'place' : 'bounding_box'}, ['coordinates'])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.placeboundingbox.csv.ref'),\
                   'Error in csv file'

    def test_retweet_original_tweet(self):
        with TemporaryDirectory() as tempdir:
            outfn = os.path.join(tempdir, 'tweets.20150430-223406.retweet.csv')  
            json2csv_entities(self.infile, outfn, ['id'], 'retweeted_status',
                                  ['created_at', 'favorite_count', 'id', 'in_reply_to_status_id',
                                   'in_reply_to_user_id', 'retweet_count', 'text', 'truncated',
                                   {'user' : ['id']}])
    
            assert areFilesIdentical(outfn, 'tweets.20150430-223406.retweet.csv.ref'),\
                       'Error in csv file'

if __name__ == "__main__":
    unittest.main()
