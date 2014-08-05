# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Twitter client.
"""

import itertools
import json
import os
import datetime

from twython import Twython, TwythonStreamer


class Streamer(TwythonStreamer):
    """
    Retrieve data from the Twitter streaming API.

    The streaming API requires OAuth 1.0 authentication.
    """
    def __init__(self, handler, app_key, app_secret, oauth_token,
                 oauth_token_secret):
        self.handler = handler
        self.do_continue = True
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)

    def on_success(self, data):
        """
        :param data: response from Twitter API
        """
        if self.do_continue:
        #if self.handler is not None:
            if 'text' in data:
                self.do_continue = self.handler.handle(data)
        else:
            self.disconnect()
            #raise ValueError("No data handler has been registered.")

    def on_error(self, status_code, data):
        """
        :param data: response from Twitter API
        """
        print(status_code)



class Query(Twython):
    """
    Class for accessing the Twitter REST API.
    """


    def hydrate(self, infile):
        """
        Given a file containing a list of Tweet IDs, fetch the corresponding
        Tweets (if they haven't been deleted).

        :param infile: name of a file consisting of Tweet IDs, one to a line
        :return: iterable of Tweet objects
        """
        with open(infile) as f:
            ids = [line.rstrip() for line in f]
            # The Twitter endpoint takes lists of up to 100 ids, so we chunk
            # the ids
        id_chunks = [ids[i:i+100] for i in range(0, len(ids), 100)]
        listoflists = [self.post('statuses/lookup', {'id': chunk}) for chunk
                       in id_chunks]
        return itertools.chain.from_iterable(listoflists)


class TweetHandler:
    """
    Abstract class whose subclasses should implement a handle method that
    Twitter clients can delegate to.
    """
    def __init__(self, limit=20):
        """
        :param limit: number of data items to process in the current round of
        processing

        :param startingup: flag to indicate whether this is the first data
        item to be processed in the current round of processing.

        :param counter: keep track of number of data items processed

        """
        self.limit = limit
        self.startingup = True
        self.counter = 0

    def handle(self, data):
        raise NotImplementedError



class TweetViewer(TweetHandler):
    """
    Handle data by sending it to the terminal.
    """
    def handle(self, data):
        """
        Direct data to `sys.stdout`

        :return: return False if processing should cease, otherwise return
        True.
        :rtype: boolean
        :param data: Tweet object returned by Twitter API
        """
        text = data['text']
        print(text)
        self.counter += 1
        if self.counter >= self.limit:
            # Tell the client to disconnect
            return False
        return True


class TweetWriter(TweetHandler):
    """
    Handle data by writing it to a file.
    """
    def __init__(self, limit=2000, repeat=True, fprefix='tweets',
                 subdir='streamed_data'):
        """
        :param limit: number of data items to process in the current round of
        processing

        """
        self.repeat = repeat
        self.fprefix = fprefix
        self.subdir = subdir
        self.fname = self.timestamped_file()
        self.startingup = True
        super().__init__(limit)


    def timestamped_file(self):
        """
        :return: timestamped file name
        :rtype: str
        """
        subdir = self.subdir
        fprefix = self.fprefix
        if subdir:
            if not os.path.exists(subdir):
                os.mkdir(subdir)

        fname = os.path.join(subdir, fprefix)
        fmt = '%Y%m%d-%H%M%S'
        timestamp = datetime.datetime.now().strftime(fmt)
        outfile = '{0}.{1}.json'.format(fname, timestamp)
        return outfile


    def handle(self, data):
        """
        Write Twitter data as line-delimited JSON into one or more files.

        :return: return False if processing should cease, otherwise return True.
        :param data: Tweet object returned by Twitter API
        """
        if self.startingup:
            self.output = open(self.fname, 'w')
            print('Writing to {}'.format(self.fname))
        json_data = json.dumps(data)
        self.output.write(json_data + "\n")

        self.startingup = False
        self.counter += 1
        if self.counter < self.limit:
            return True
        else:
            print('Written {} tweets'.format(self.counter))
            self.output.close()
            if not self.repeat:
                # Tell the client to disconnect
                return False
            else:
                self.fname = self.timestamped_file()
                self.output = open(self.fname, 'w')
                self.counter = 0
                print('\nWriting to new file {}'.format(self.fname))
                return True





################################
# Utility functions
################################

def dehydrate(infile):
    """
    Transform a file of serialized Tweet objects into a file of corresponding
    Tweet IDs.
    """
    with open(infile) as tweets:
        ids = [json.loads(t)['id_str'] for t in tweets]
        return ids


def authenticate(creds_file=None, subdir=None):
    """
    Read OAuth credentials from a text file.

    File format for OAuth 1:
    ========================
    app_key=YOUR_APP_KEY
    app_secret=YOUR_APP_SECRET
    oauth_token=OAUTH_TOKEN
    oauth_token_secret=OAUTH_TOKEN_SECRET


    File format for OAuth 2
    =======================
    app_key=YOUR_APP_KEY
    app_secret=YOUR_APP_SECRET
    access_token=ACCESS_TOKEN

    :param file_name: File containing credentials. None (default) reads
    data from "./credentials.txt"
    """
    if subdir is None:
        try:
            subdir = os.environ['TWITTERHOME']
        except KeyError:
            print("""Supply a value to the 'subdir' parameter or set the
            environment variable TWITTERHOME""")
    if creds_file is None:
        creds_file = 'credentials.txt'

    creds_fullpath = os.path.normpath(os.path.join(subdir, creds_file))

    with open(creds_fullpath) as f:
        oauth = {}
        for line in f:
            if '=' in line:
                name, value = line.split('=', 1)
                oauth[name.strip()] = value.strip()
    return oauth


def add_access_token(creds_file=None):
    """
    For OAuth 2, retrieve an access token for an app and append it to a
    credentials file.
    """
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, 'credentials2.txt')
    oauth2 = authenticate(creds_file=creds_file)
    APP_KEY = oauth2['app_key']
    APP_SECRET = oauth2['app_secret']

    twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
    ACCESS_TOKEN = twitter.obtain_access_token()
    s = 'access_token={}\n'.format(ACCESS_TOKEN)
    with open(creds_file, 'a') as f:
        print(s, file=f)



################################
# Demos
################################

import os
TWITTERHOME = os.environ['TWITTERHOME']
CREDS = None
TWEETS = TWITTERHOME + 'tweets.20140801-150110.json'
IDS = TWITTERHOME + 'tweet_ids.txt'
REHYDE = TWITTERHOME + 'rehdrated.json'

def streamtoscreen_demo(limit=20):
    oauth = authenticate()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    client.statuses.sample()

def streamtofile_demo(limit=20):
    oauth = authenticate()
    handler = TweetWriter(limit=limit, repeat=True)
    client = Streamer(handler, **oauth)
    client.statuses.sample()

def dehydrate_demo(infile, outfile):
    ids = dehydrate(infile)
    with open(outfile, 'w') as f:
        for id_str in ids:
            print(id_str, file=f)


def hydrate_demo(infile, outfile):
    oauth = authenticate(CREDS)
    client = Query(**oauth)
    tweets = client.hydrate(infile)
    with open(outfile, 'w') as f:
        for data in tweets:
            json_data = json.dumps(data)
            f.write(json_data + "\n")


def corpusreader_demo():
    from nltk.corpus import TwitterCorpusReader
    root = os.environ['TWITTERHOME']
    reader = TwitterCorpusReader(root, '.*\.json')
    for t in reader.jsonlist()[:15]:
        print(t)

    #for t in reader.tweets()[:10]:
         #print(t)

    #for t in reader.tokenised_tweets()[:10]:
        #print(t)




DEMOS = [4]

if __name__ == "__main__":
    #import doctest
    #doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

    if 0 in DEMOS:
        streamtoscreen_demo()
    if 1 in DEMOS:
        streamtofile_demo()
    if 2 in DEMOS:
        dehydrate_demo(TWEETS, IDS)
    if 3 in DEMOS:
        hydrate_demo(IDS, REHYDE)
    if 4 in DEMOS:
        corpusreader_demo()





