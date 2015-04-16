# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Twitter client.


If one of the methods below returns an integer, it is probably a `Twitter
error code <https://dev.twitter.com/overview/api/response-codes>`_. For
example, the response of '420' means that you have reached the limit of the
requests you can currently make to the Twitter API. Currently, `rate limits
for the search API <https://dev.twitter.com/rest/public/rate-limiting>`_ are
divided into 15 minute windows.
"""

import datetime
import itertools
import json
import os
import sys
import requests

try:
    from twython import Twython, TwythonStreamer, TwythonError
except ImportError as err:
    import textwrap
    MSG = """The NLTK twitterclient module requires the Twython package. See\
    https://twython.readthedocs.org/ for installation instructions."""
    err.msg = textwrap.fill(MSG)
    raise

from nltk.twitter.util import credsfromfile, guess_path
from nltk.twitter.api import TweetHandlerI



class Streamer(TwythonStreamer):
    """
    Retrieve data from the Twitter Streaming API.

    The streaming API requires `OAuth 1.0 <http://en.wikipedia.org/wiki/OAuth>`_ authentication.
    """
    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret):

        self.handler = None
        self.do_continue = True
        TwythonStreamer.__init__(self, app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
        """
        Register a method for handling tweets.

        :param TweetHandlerI handler: method for viewing
        """
        self.handler = handler

    def on_success(self, data):
        """
        :param data: response from Twitter API
        """
        if self.do_continue:
            if self.handler is not None:
                if 'text' in data:
                    self.do_continue = self.handler.handle(data)
            else:
                raise ValueError("No data handler has been registered.")
        else:
            self.disconnect()


    def on_error(self, status_code, data):
        """
        :param data: response from Twitter API
        """
        print(status_code)

    def sample(self):
        while self.do_continue:
            '''
            Stream in an endless loop until limit is reached
            see twython issue 288
                https://github.com/ryanmcgrath/twython/issues/288
                colditzjb commented on 9 Dec 2014
            '''
            try:
                self.statuses.sample()
            except requests.exceptions.ChunkedEncodingError as e:
                if e is not None:
                    print("Error (stream will continue): {}".format(e))
                continue

    def filter(self, track, follow):
        while self.do_continue:
            '''
            Stream in an endless loop until limit is reached
            see twython issue 288
                https://github.com/ryanmcgrath/twython/issues/288
                colditzjb commented on 9 Dec 2014
            '''
            try:
                self.statuses.filter(track=track, follow=follow)
            except requests.exceptions.ChunkedEncodingError as e:
                if e is not None:
                    print("Error (stream will continue): {}".format(e))
                continue




class Query(Twython):
    """
    Retrieve data from the Twitter REST API.
    """
    def __init__(self, app_key, app_secret, oauth_token,
                 oauth_token_secret):
        self.handler = None
        self.do_continue = True
        Twython.__init__(self, app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
        """
        Register a method for handling tweets.

        :param TweetHandlerI handler: method for viewing or writing tweets to a file.
        """
        self.handler = handler

    def _lookup(self, infile, verbose=True):
        """
        :param infile: name of a file consisting of Tweet IDs, one to a line
        :return: iterable of Tweet objects
        """
        with open(infile) as f:
            ids = [line.rstrip() for line in f]
        if verbose:
            print("Counted {} Tweet IDs in {}.".format(len(ids), infile))

        id_chunks = [ids[i:i+100] for i in range(0, len(ids), 100)]
        """
        The Twitter endpoint takes lists of up to 100 ids, so we chunk
        the ids.
        """

        listoflists = [self.post('statuses/lookup', {'id': chunk}) for chunk
                       in id_chunks]
        return itertools.chain.from_iterable(listoflists)


    def lookup(self, infile, outfile, verbose=True):
        """
        Given a file containing a list of tweetIDs, fetch the corresponding
        Tweets (if they haven't been deleted) and dump them in a file.

        :param str infile: Name of a file consisting of tweetIDs, one to a line
        :param str outfile: Name of file where JSON serialisations of fully\
        expanded Tweets will be written.
        """
        tweets = self._lookup(infile, verbose=verbose)
        count = 0

        if os.path.isfile(outfile):
            os.remove(outfile)

        with open(outfile, 'a') as f:
            for data in tweets:
                json.dump(data, f)
                f.write("\n")
                count += 1

        if verbose:
            print("""Written {} Tweets to file {} of length {}
            bytes""".format(count, outfile, os.path.getsize(outfile)))

    def search_tweets(self, keywords, count=100, lang='en'):
        """
        Call the REST API ``'search/tweets'`` endpoint with some plausible
        defaults. See `the Twitter search documentation
        <https://dev.twitter.com/rest/public/search>`_ for more information
        about admissable search parameters.

        :param str keywords: A list of query terms to search for, written as\
        a comma-separated string.
        :rtype: json
        """
        results = self.search(q=keywords, count=count, lang=lang)
        return results['statuses']

    def user_info_from_id(self, userids):
        """
        Convert a list of userIDs into a variety of information about the users.

        See <https://dev.twitter.com/rest/reference/get/users/show>.

        :param list userids: A list of integer strings corresponding to Twitter userIDs
        :rtype: list(json)
        """
        return [self.show_user(user_id=userid) for userid in userids]

    def user_tweets(self, user, count, include_rts='false'):
        """
        Return a collection of the most recent Tweets posted by the user

        :param user: A User ID or Screen Name
        """
        data = self.get_user_timeline(screen_name=user, count=count, include_rts=include_rts)
        #if handler:
        self.handler.handle(data)




class Twitter(object):
    """
    Wrapper class with restricted functionality.
    """
    def __init__(self):
        self._oauth = credsfromfile()
        self.streamer = Streamer(**self._oauth)
        self.query = Query(**self._oauth)


    def tweets(self, keywords='', follow='', to_screen=True, stream=True, limit=100):
        """
        Process some tweets in a simple manner.

        :param str keywords: Keywords to use for searching or filtering
        :param list follow: UserIDs to use for filtering tweets from the public stream
        :param bool to_screen: If ``True``, display the tweet texts on the screen,\
        otherwise print to a file
        :param bool stream: If ``True``, use the live public stream,\
        otherwise search past public tweets
        :param int limit: Number of tweets to process
        """
        if to_screen:
            handler = TweetViewer(limit=limit)
        else:
            handler = TweetWriter(limit=limit, repeat=False)

        if stream:
            self.streamer.register(handler)
            if keywords == '' and follow == '':
                self.streamer.sample()
            else:
                self.streamer.filter(track=keywords, follow=follow)            
        else:
            self.query.register(handler)
            if keywords == '':
                raise ValueError("Please supply at least one keyword to search for.")
            else:
                tweets = self.query.search_tweets(keywords, count=limit)
                for tweet in tweets:
                    print(tweet['text'])



class TweetViewer(TweetHandlerI):
    """
    Handle data by sending it to the terminal.
    """
    def handle(self, data):
        """
        Direct data to `sys.stdout`

        :return: return ``False`` if processing should cease, otherwise return ``True``.
        :rtype: bool
        :param data: Tweet object returned by Twitter API
        """
        text = data['text']
        print(text)
        self.counter += 1
        if self.counter >= self.limit:
            # Tell the client to disconnect
            return False
        return True


class TweetWriter(TweetHandlerI):
    """
    Handle data by writing it to a file.
    """
    def __init__(self, limit=2000, repeat=True, fprefix='tweets',
                 subdir='twitter-files'):
        """
        :param limit: number of data items to process in the current round of processing

        :param repeat: flag to determine whether multiple files should be\
        written. If ``True``, the length of each file will be set by the value\
        of ``limit``. See also :py:func:`handle`.

        """
        self.repeat = repeat
        self.fprefix = fprefix
        self.subdir = guess_path(subdir)
        self.fname = self.timestamped_file()
        self.startingup = True
        TweetHandlerI.__init__(self, limit)


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

        :return: return `False` if processing should cease, otherwise return `True`.
        :param data: tweet object returned by Twitter API
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
                "Tell the client to disconnect"
                return False
            else:
                self.fname = self.timestamped_file()
                self.output = open(self.fname, 'w')
                self.counter = 0
                print('\nWriting to new file {}'.format(self.fname))
                return True






