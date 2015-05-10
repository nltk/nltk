# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Examples to demo the :py:mod:`twitterclient` code.

For documentation about the Twitter APIs, see `The Streaming APIs Overview
<https://dev.twitter.com/streaming/overview>`_ and `The REST APIs Overview
<https://dev.twitter.com/rest/public>`_.
"""

from functools import wraps
import json
import os

from nltk.twitter import Query, Streamer, Twitter, TweetViewer, TweetWriter,\
     credsfromfile, json2csv

SPACER = '###################################'

def verbose(func):
    """Decorator for demo functions"""
    @wraps(func)
    def with_formatting(*args, **kwargs):
        print()
        print(SPACER)
        print("Using %s" % (func.__name__))
        print(SPACER)
        return func(*args, **kwargs)
    return with_formatting



TWITTER = os.environ['TWITTER']
TWEETS = os.path.join(TWITTER, 'demo_tweets.json')
TWEETS = os.path.join(TWITTER, '1k_sample.json')
IDS = os.path.join(TWITTER, '1k_sample.csv')
FIELDS = ['id_str']
USERIDS = ['759251', '612473', '15108702', '6017542', '2673523800'] # UserIDs corresponding to\
#           @CNN,    @BBCNews, @ReutersLive, @BreakingNews, @AJELive
HYDRATED = os.path.join(TWITTER, 'rehydrated.json')
DATE = (2015, 4, 20, 16, 40)


@verbose
def twitterclass_demo():
    """
    Use the simplified :class:`Twitter` class to write some tweets to a file.
    """
    tw = Twitter()
    tw.tweets(keywords='love, hate', limit=10) #public stream
    print(SPACER)
    tw = Twitter()
    tw.tweets(keywords='love, hate', stream=False, limit=10) # search past tweets
    print(SPACER)
    tw = Twitter()
    tw.tweets(follow=['759251', '6017542'], stream=True, limit=10) #public stream


@verbose
def sampletoscreen_demo(limit=20):
    """
    Sample from the Streaming API and send output to terminal.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.sample()


@verbose
def tracktoscreen_demo(track="taylor swift", limit=10):
    """
    Track keywords from the public Streaming API and send output to terminal.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.filter(track=track)


@verbose
def search_demo(keywords='nltk'):
    """
    Using the REST API, search for past tweets containing a given keyword.
    """
    oauth = credsfromfile()
    client = Query(**oauth)
    for tweet in client.search_tweets(keywords=keywords, count=10):
        print(tweet['text'])


@verbose
def tweets_by_user_demo(user='NLTK_org', count=200):
    oauth = credsfromfile()
    client = Query(**oauth)
    client.register(TweetWriter())
    client.user_tweets(user, count)


@verbose
def lookup_by_userid_demo():
    """
    Use the REST API to convert a userID to a screen name.
    """
    oauth = credsfromfile()
    client = Query(**oauth)
    user_info = client.user_info_from_id(USERIDS)
    for info in user_info:
        name = info['screen_name']
        followers = info['followers_count']
        following = info['friends_count']
        print("{0}, followers: {1}, following: {2}".format(name, followers, following))


@verbose
def followtoscreen_demo(limit=10):
    """
    Using the Streaming API, select just the tweets from a specified list of
    userIDs.

    This is will only give results in a reasonable time if the users in
    question produce a high volume of tweets, and may even so show some delay.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.statuses.filter(follow=USERIDS)


@verbose
def streamtofile_demo(limit=20):
    """
    Write 20 tweets sampled from the public Streaming API to a file.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetWriter(limit=limit, repeat=False))
    client.statuses.sample()


@verbose
def limit_by_time_demo(limit=20, date_limit=DATE):
    """
    Sample from the Streaming API and send output to terminal.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetWriter(limit=limit, date_limit=date_limit))
    client.sample()


@verbose
def extract_tweetids_demo(infile = TWEETS, outfile = IDS):
    """
    Given a list of full tweets in a file (``infile``), write just the
    tweetIDs to a new file (`outfile`)
    """
    print("Reading from {0}".format(infile))
    json2csv(infile, outfile, FIELDS)
    print("Writing ids to {0}".format(outfile))


@verbose
def expand_tweetids_demo(infile = IDS, outfile = HYDRATED):
    """
    Given a list of tweetIDs in a file (``infile``), try to recover the full
    ('hydrated') tweets from the REST API and write the results to a new file (`outfile`).

    If any of the tweets corresponding to the tweetIDs have been deleted by
    their authors, :meth:`lookup` will return an empty result.
    """
    oauth = credsfromfile()
    client = Query(**oauth)
    client.lookup(infile, outfile)


@verbose
def corpusreader_demo():
    """
    Use :module:`TwitterCorpusReader` tp read a file of tweets, and print out

    * some full tweets in JSON format;
    * some raw strings from the tweets (i.e., the value of the `text` field); and
    * the result of tokenising the raw strings.

    """
    from nltk.corpus import tweets

    #reader = TwitterCorpusReader(root, '1k_sample.json')
    #reader = TwitterCorpusReader('twitter', 'tweets.20150417.json')
    print()
    print("Complete tweet documents")
    print(SPACER)
    for tweet in tweets.docs()[:1]:
        print(json.dumps(tweet, indent=1, sort_keys=True))

    print()
    print("Raw tweet strings:")
    print(SPACER)
    for text in tweets.strings()[:15]:
        print(text)

    print()
    print("Tokenized tweet strings:")
    print(SPACER)
    for toks in tweets.tokenized()[:15]:
        print(toks)


ALL = [twitterclass_demo, sampletoscreen_demo, tracktoscreen_demo,
         search_demo, tweets_by_user_demo, lookup_by_userid_demo, followtoscreen_demo,
         streamtofile_demo, limit_by_time_demo,
         extract_tweetids_demo, expand_tweetids_demo, corpusreader_demo]

DEMOS = ALL[11:]

if __name__ == "__main__":
    """Run selected demo functions."""

    for demo in DEMOS:
        demo()



