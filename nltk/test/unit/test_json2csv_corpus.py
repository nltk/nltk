'''
Created on 6 de may. de 2015

@author: lorenzorubio
'''
import unittest
import os
import filecmp
from nltk.twitter.util import guess_path, json2csv, json2csv_entities

class Test(unittest.TestCase):


    def setUp(self):
        from nltk.corpus import tweets
        self.inpf = tweets.abspath("tweets.20150430-223406.json")
        pass


    def tearDown(self):
        pass


    def testTextOutput(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.text.csv')
        json2csv(self.inpf, outf,
                 ['text'])

        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.text.csv.ref'), 'Error in csv file'

    def testTweetMetadata(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.tweet.csv')
        json2csv(self.inpf, outf,
                 ['created_at', 'favorite_count', 'id', 'in_reply_to_status_id', 
                 'in_reply_to_user_id', 'retweet_count', 'retweeted', 
                 'text', 'truncated', {'user' : {'id'}}])

        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.tweet.csv.ref'), 'Error in csv file'

    def testUserMetadata(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.user.csv')
        json2csv(self.inpf, outf,
                 ['id', 'text', {'user' : ['id', 'followers_count', 'friends_count']}])

        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.user.csv.ref'), 'Error in csv file'
                       
    def testTweetHashtag(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.hashtag.csv')
        json2csv_entities(self.inpf, outf,
                          ['id', 'text'], 'hashtags', ['text'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.hashtag.csv.ref'), 'Error in csv file'
                 
    def testTweetUserMention(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.usermention.csv')
        json2csv_entities(self.inpf, outf,
                          ['id', 'text'], 'user_mentions', ['id', 'screen_name'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.usermention.csv.ref'), 'Error in csv file'
                       
    def testTweetMedia(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.media.csv')
        json2csv_entities(self.inpf, outf,
                          ['id'], 'media', ['media_url', 'url'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.media.csv.ref'), 'Error in csv file'
                       
    def testTweetUrl(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.url.csv')
        json2csv_entities(self.inpf, outf,
                          ['id'], 'urls', ['url', 'expanded_url'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.url.csv.ref'), 'Error in csv file'

    def testUserUrl(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.userurl.csv')
        json2csv_entities(self.inpf, outf,
                          ['id', 'screen_name'], {'user' : 'urls'}, ['url', 'expanded_url'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.userurl.csv.ref'), 'Error in csv file'

    def testTweetPlace(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.place.csv')
        json2csv_entities(self.inpf, outf,
                          ['id', 'text'], 'place', ['name', 'country'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.place.csv.ref'), 'Error in csv file'

    def testTweetPlaceBoundingBox(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.placeboundingbox.csv')
        json2csv_entities(self.inpf, outf,
                          ['id', 'name'], {'place' : 'bounding_box'}, ['coordinates'])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.placeboundingbox.csv.ref'), 'Error in csv file'

    def testRetweetOriginalTweet(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.retweet.csv')
        json2csv_entities(self.inpf, outf,
                          ['id'], 'retweeted_status', ['created_at', 'favorite_count', 
                          'id', 'in_reply_to_status_id', 'in_reply_to_user_id', 'retweet_count',
                          'text', 'truncated', {'user' : {'id'}}])
                 
        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.retweet.csv.ref'), 'Error in csv file'

if __name__ == "__main__":
    unittest.main()