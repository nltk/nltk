# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

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
    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret):
        self.handler = None
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)
        
    def register(self, handler):
        """
        Register a method of :py:class:`TweetHandler`                
        """
        self.handler = handler
        
    def on_success(self, data):
        """
        :param data: response from Twitter API
        """
        if self.handler is not None:
            if 'text' in data:
                self.handler(data)
        else:
            raise ValueError("No data handler has been registered.")
                              
    def on_error(self, status_code, data):
        """
        :param data: response from Twitter API
        """        
        print(status_code)


class Query:
    """
    Class for accessing the Twitter REST API.
    """
    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret):
        self.client = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
        
        
    def hydrate(self, infile):
        """
        Given a file containing a list of Tweet IDs, fetch the corresponding
        Tweets (if they haven't been deleted).
        
        :param infile: name of a file consisting of Tweet IDs, one to a line
        :return: iterable of Tweet objects
        """
        with open(infile) as f:
            ids = [line.rstrip() for line in f]
         
         # The Twitter endpoint takes lists of up to 100 ids, so we chunk the ids   
        id_chunks = [ids[i:i+100] for i in range(0, len(ids), 100)]
        listoflists = [self.client.post('statuses/lookup', {'id': chunk}) for chunk in id_chunks]
        return itertools.chain.from_iterable(listoflists)
       
        
class TweetHandler:
    """
    A group of methods for handling the Tweets returned by the Twitter API.
    
    The handler needs to be able to signal a disconnect to the client.
    """
    def __init__(self, client, limit=2000, repeat=False, fprefix='tweets', subdir='streamed_data', ):
        self.client = client
        self.limit = limit
        self.repeat = repeat
        self.counter = 0
        self.subdir = subdir
        self.fprefix = fprefix
        self.fname = self.timestamped_file()
        self.output  = open(self.fname, 'w')
        
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
        ts = datetime.datetime.now().strftime(fmt)
        outfile = '{0}.{1}.json'.format(fname, ts)
        return outfile    
        
    def render(self, data, encoding=None):
        """
        Print data to `sys.stdout`
        
        :param data: Tweet object returned by Twitter API
        """
        text = data['text']
        if encoding is None:            
            print(text)            
        else:
            print(text.encode(encoding))
        self.counter += 1
        if self.counter >= self.limit:
            self.client.disconnect()

        
    def dump(self, data, verbose=True):
        """
        Dump Twitter data as line-delimited JSON into one or more files.
        """
        json_data = json.dumps(data)
        self.output.write(json_data + "\n")        
        self.counter += 1
        if verbose:
            print('Writing to {}'.format(self.fname))           
            
        if self.counter >= self.limit:
            self.output.close()
            if not self.repeat:
                self.client.disconnect()
            else:
                self.output = open(self.timestamped_file(), 'w')               
                self.counter = 0
                if verbose:
                    print('Writing to new file {}'.format(self.fname))           
                         


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
    

def authenticate(creds_file=None):
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
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, 'credentials.txt')

    with open(creds_file) as f:
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

def streamtoscreen_demo(limit=20):
    oauth = authenticate('credentials1.txt') 
    client = Streamer(**oauth)        
    handler = TweetHandler(client, limit=limit)
    method = handler.render
    client.register(method)
    client.statuses.sample()
    
def streamtofile_demo(limit=20):
    oauth = authenticate('credentials1.txt') 
    client = Streamer(**oauth)
    handler = TweetHandler(client, limit=limit)    
    method = handler.dump    
    client.register(method)
    client.statuses.sample()    
    
def dehydrate_demo(outfile):
    infile = 'streamed_data/tweets.20140723-163436.json'
    ids = dehydrate(infile)
    with open(outfile, 'w') as f:
        for id_str in ids:
            print(id_str, file=f)
            

def hydrate_demo(infile, outfile):
    oauth = authenticate('credentials1.txt')
    client = Query(**oauth)
    tweets = client.hydrate(infile)
    with open(outfile, 'w') as f:
        for data in tweets:
            json_data = json.dumps(data)
            f.write(json_data + "\n")                    
       
        
def corpusreader_demo():
    from reader import TwitterCorpusReader
    root = 'streamed_data/'
    reader = TwitterCorpusReader(root, '.*\.json')
    for t in reader.tweets()[:10]:
        print(t)
        
    for t in reader.tokenised_tweets()[:10]:
        print(t)

    
        
    
demos = [0]

if __name__ == "__main__":

    if 0 in demos:
        streamtoscreen_demo()    
    if 1 in demos:
        streamtofile_demo()
    if 2 in demos:
        dehydrate_demo('ids.txt')
    if 3 in demos:
        hydrate_demo('ids.txt', 'tmp.json')
    if 4 in demos:
        corpusreader_demo()


    
 

    

        