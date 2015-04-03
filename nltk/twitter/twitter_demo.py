# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Examples to demo the :py:mod:`twitterclient` code.
"""

from functools import wraps
import os

from twitterclient import *
from util import extract_tweetid

spacer = '###################################'

def logger(func):
    @wraps(func)
    def with_logging(*args, **kwargs):
        print()
        print(spacer)
        print("Using %s" % (func.__name__))
        print(spacer)
        return func(*args, **kwargs)
    return with_logging



TWITTER = os.environ['TWITTER']
TWEETS = os.path.join(TWITTER, 'tweets.20140801-150110.json')
IDS = os.path.join(TWITTER, 'tweet_ids.txt')
IDS2 = os.path.join(TWITTER, 'tweet_ids2.txt')
USERIDS = ['759251','612473','788524','15108530']
REHYDE = os.path.join(TWITTER, 'rehydrated.json')


@logger
def sampletoscreen_demo(limit=20):
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.statuses.sample()

@logger
def tracktoscreen0_demo(track="taylor swift", limit=10):
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.statuses.filter(track=track)

@logger
def lookup_by_userid_demo():
    oauth = credsfromfile()
    client = Query(**oauth)
    user_info = client.user_info_from_id(USERIDS)
    for info in user_info:
        sn = info['screen_name']
        followers = info['followers_count']
        following = info['friends_count']
        print("{}, followers: {}, following: {}".format(sn, followers, following))


@logger
def followtoscreen_demo(limit=10):
    """

    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.statuses.filter(follow=USERIDS)

@logger
def streamtofile_demo(limit=20):
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetWriter(limit=limit, repeat=False))
    client.statuses.sample()

@logger
def extract_tweetids_demo(infile, outfile):
    print("Reading from {}".format(infile))
    print()
    ids = extract_tweetid(infile)
    with open(outfile, 'w') as f:
        print("Writing ids to {}".format(outfile))
        print()
        for id_str in ids:
            print("Found id {}".format(id_str))
            print(id_str, file=f)

@logger
def expand_tweetids_demo(infile, outfile):
    oauth = credsfromfile()
    client = Query(**oauth)
    client.lookup(infile, outfile)

@logger
def corpusreader_demo():
    from nltk.corpus import TwitterCorpusReader
    root = os.environ['TWITTER']
    reader = TwitterCorpusReader(root, '.*\.json')
    fileid = 'rehydrated.json'
    print()
    print("Complete tweet documents")
    print(spacer)
    for t in reader.docs(fileid)[:1]:
        print(json.dumps(t, indent=1, sort_keys=True))

    print()
    print("Raw tweet strings:")
    print(spacer)
    for t in reader.strings(fileid)[:15]:
        print(t)

    print()
    print("Tokenized tweet strings:")
    print(spacer)
    for t in reader.tokenized(fileid)[:15]:
        print(t)

@logger
def search_demo(keywords='nltk'):
    oauth = credsfromfile()
    client = Query(**oauth)
    for t in client.search(keywords=keywords, count=10):
        print(t['text'])

@logger
def twitterclass_demo():
    tw = Twitter()
    tw.tweets(keywords='love', to_screen=False)


def temp():
    from nltk.corpus import TwitterCorpusReader
    root = os.environ['TWITTER']
    root = os.path.join(root, 'robinwilliams')
    reader = TwitterCorpusReader(root, 'tweets.20140815-160831.json')
    #for t in reader.docs()[:1]:
        #print(json.dumps(t, sort_keys=True, indent=4))

    for t in reader.strings():
        print(t)



all_demos = range(8)
DEMOS = all_demos
DEMOS = [6]

if __name__ == "__main__":

    if 0 in DEMOS:
        sampletoscreen_demo()
    if 1 in DEMOS:
        tracktoscreen0_demo()
    if 2 in DEMOS:
        followtoscreen_demo()
    if 3 in DEMOS:
        streamtofile_demo()
    if 4 in DEMOS:
        extract_tweetids_demo(TWEETS, IDS)
    if 5 in DEMOS:
        expand_tweetids_demo(IDS, REHYDE)
    if 6 in DEMOS:
        corpusreader_demo()
    if 7 in DEMOS:
        search_demo()
    if 8 in DEMOS:
        twitterclass_demo()

