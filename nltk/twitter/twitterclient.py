# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Twitter client.
"""

import datetime
import itertools
import json
import os

try:
    from twython import Twython, TwythonStreamer, TwythonError
except ImportError as e:
    import textwrap
    msg = """The NLTK twitterclient module requires the Twython package. See\
    https://twython.readthedocs.org/ for installation instructions."""
    e.msg = textwrap.fill(msg)
    raise

from nltk.twitter.util import credsfromfile, guess_path
from nltk.twitter.api import TweetHandlerI



class Streamer(TwythonStreamer):
    """
    Retrieve data from the Twitter streaming API.

    The streaming API requires `OAuth 1.0 <http://en.wikipedia.org/wiki/OAuth>`_ authentication.
    """
    def __init__(self, app_key, app_secret, oauth_token,
                     oauth_token_secret):

        self.handler = None
        self.do_continue = True
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
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



class Query(Twython):
    """
    Class for accessing the Twitter REST API.
    """
    def __init__(self, app_key, app_secret, oauth_token,
                 oauth_token_secret, handler=None):
        self.handler = handler
        self.do_continue = True
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
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
        Given a file containing a list of Tweet IDs, fetch the corresponding
        Tweets (if they haven't been deleted) and dump them in a file.

        :param infile: name of a file consisting of Tweet IDs, one to a line

        :param outfile: name of file where JSON serialisations of fully hydrated Tweets will be written.
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
            bytes""".format(count, outfile, os.path.getsize( outfile)))

    def search(self, keywords, count=100, lang='en'):
        """
        Call the REST API ``'search/tweets'`` endpoint with some plausible defaults.
        """
        results = self.get('search/tweets', {'q': keywords, 'count': 100,
                                             'lang': 'en'})
        #results = self.search(q=keywords, count=100, lang='en')
        return results['statuses']

    def user_info_from_id(self, userids):
        results = []
        for userid in userids:
            handle = self.show_user(user_id=userid)
            results.append(handle)
        return results




class Twitter(object):
    """
    Wrapper class with restricted functionality.
    """
    def __init__(self):
        self._oauth = credsfromfile()
        self.streamer = Streamer(**self._oauth)
        self.query = Query(**self._oauth)


    def tweets(self, keywords='', follow='', to_screen=True, stream=True, limit=100):
        if to_screen:
            handler = TweetViewer(limit=limit)
        else:
            handler = TweetWriter(limit=limit, repeat=False)

        if stream:
            self.streamer.register(handler)
            if keywords=='' and follow=='':
                self.streamer.statuses.sample()
            else:
                self.streamer.statuses.filter(track=keywords, follow=follow)
        else:
            self.query.register(handler)
            if keywords == '':
                raise ValueError("Please supply at least one keyword to search for.")
            else:
                tweets = self.query.search(keywords)
                for t in tweets:
                    print(t['text'])



class TweetViewer(TweetHandlerI):
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


class TweetWriter(TweetHandlerI):
    """
    Handle data by writing it to a file.
    """
    def __init__(self, limit=2000, repeat=True, fprefix='tweets',
                 subdir='twitter'):
        """
        :param limit: number of data items to process in the current round of
        processing

        :param repeat: flag to determine whether multiple files should be
        written. If `True`, the length of each file will be set by the value
        of `limit`. See also :py:func:`handle`

        """
        self.repeat = repeat
        self.fprefix = fprefix
        self.subdir = guess_path(subdir)
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
                "Tell the client to disconnect"
                return False
            else:
                self.fname = self.timestamped_file()
                self.output = open(self.fname, 'w')
                self.counter = 0
                print('\nWriting to new file {}'.format(self.fname))
                return True




#if __name__ == "__main__":
    #pass
    #import doctest
    #doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)





