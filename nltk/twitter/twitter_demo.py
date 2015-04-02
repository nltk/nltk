import os

from nltk.twitter import *

################################
# Demos
################################

TWITTER = os.environ['TWITTER']
TWEETS = os.path.join(TWITTER, 'tweets.20140801-150110.json')
IDS = os.path.join(TWITTER, 'tweet_ids.txt')
IDS2 = os.path.join(TWITTER, 'tweet_ids2.txt')
REHYDE = os.path.join(TWITTER, 'rehydrated.json')

def sampletoscreen_demo(limit=20):
    oauth = credsfromfile()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    client.statuses.sample()

def tracktoscreen0_demo(limit=10):
    oauth = credsfromfile()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    keywords = "robin williams"
    client.statuses.filter(track=keywords)

def tracktoscreen1_demo(limit=50):
    oauth = credsfromfile()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    client.statuses.filter(follow='759251,612473,788524,15108530')

def streamtofile_demo(limit=20):
    oauth = credsfromfile()
    handler = TweetWriter(limit=limit, repeat=True)
    client = Streamer(handler, **oauth)
    client.statuses.sample()

def dehydrate_demo(infile, outfile):
    ids = dehydrate(infile)
    with open(outfile, 'w') as f:
        for id_str in ids:
            print(id_str, file=f)

def hydrate_demo(infile, outfile):
    oauth = credsfromfile()
    client = Query(**oauth)
    client.lookup(infile, outfile)

def corpusreader_demo():
    from nltk.corpus import TwitterCorpusReader
    root = os.environ['TWITTER']
    reader = TwitterCorpusReader(root, '.*\.json')
    for t in reader.docs()[:2]:
        print(t)

    for t in reader.strings()[:15]:
        print(t)

    for t in reader.tokenized()[:15]:
        print(t)


def search_demo():
    oauth = credsfromfile()
    client = Query(**oauth)
    for t in client.search(keywords='nltk', count=10):
        print(t['text'])


def twitterclass_demo():
    tw = Twitter()
    tw.tweets(keywords='love')
    tw.tofile(keywords='', track='', stream=True, limit=100)

def temp():
    from nltk.corpus import TwitterCorpusReader
    root = os.environ['TWITTER']
    root = os.path.join(root, 'robinwilliams')
    reader = TwitterCorpusReader(root, 'tweets.20140815-160831.json')
    #for t in reader.docs()[:1]:
        #print(json.dumps(t, sort_keys=True, indent=4))

    for t in reader.strings():
        print(t)




DEMOS = [0]

if __name__ == "__main__":
    #import doctest
    #doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

    if 0 in DEMOS:
        sampletoscreen_demo()
        #tracktoscreen0_demo()
    if 1 in DEMOS:
        streamtofile_demo()
    if 2 in DEMOS:
        dehydrate_demo(TWEETS, IDS)
    if 3 in DEMOS:
        hydrate_demo(IDS, REHYDE)
    if 4 in DEMOS:
        corpusreader_demo()
    if 5 in DEMOS:
        search_demo()
    if 6 in DEMOS:
        twitterclass_demo()

    else:
        temp()