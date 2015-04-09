# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility functions to accompany :module:`twitterclient`.
"""

import csv
import json
import os
import pprint
from twython import Twython


def extract_fields(tweet, fields):
    """
    Extract field values from a full tweet and return them as a list

    :param json tweet: The tweet in JSON format
    :param list fields: The fields to be extracted from the tweet
    :rtype: list(str)
    """
    return [tweet[field] for field in fields]


def json2csv(infile, outfile, fields, encoding='utf8'):
    """
    Extract selected fields from a file of line-separated JSON tweets and
    write to a file in CSV format.

    This utility function allows a file of full tweets to be easily converted
    to a CSV file for easier processing. For example, just tweetIDs or
    just the text content of the tweets can be extracted.

    :param str infile: The name of the file containing full tweets

    :param str outfile: The name of the text file where results should be\
    written

    :param list fields: The list of fields to be extracted. Useful examples\
    are 'id_str' for the tweetID and 'text' for the text of the tweet. See\
    <https://dev.twitter.com/overview/api/tweets> for a full list of fields.
    """
    with open(outfile, 'w', encoding=encoding) as outf, open(infile) as inf:
        for line in inf:
            tweet = json.loads(line)
            row = extract_fields(tweet, fields)
            writer = csv.writer(outf)
            writer.writerow(row)

def credsfromfile(creds_file=None, subdir=None, verbose=False):
    """
    Read OAuth credentials from a text file.

    ::
       File format for OAuth 1
       =======================
       app_key=YOUR_APP_KEY
       app_secret=YOUR_APP_SECRET
       oauth_token=OAUTH_TOKEN
       oauth_token_secret=OAUTH_TOKEN_SECRET



    ::
       File format for OAuth 2
       =======================

       app_key=YOUR_APP_KEY
       app_secret=YOUR_APP_SECRET
       access_token=ACCESS_TOKEN

    :param str file_name: File containing credentials. ``None`` (default) reads\
    data from `TWITTER/'credentials.txt'`
    """
    if subdir is None:
        try:
            subdir = os.environ['TWITTER']
        except KeyError:
            print("""Supply a value to the 'subdir' parameter or set the
            environment variable TWITTER""")
    if creds_file is None:
        creds_file = 'credentials.txt'

    creds_fullpath = os.path.normpath(os.path.join(subdir, creds_file))
    if not os.path.isfile(creds_fullpath):
        raise OSError('Cannot find file {}'.format(creds_fullpath))

    with open(creds_fullpath) as f:
        if verbose:
            print('Reading credentials file {}'.format(creds_fullpath))
        oauth = {}
        for line in f:
            if '=' in line:
                name, value = line.split('=', 1)
                oauth[name.strip()] = value.strip()

    _validate_creds_file(creds_file, oauth, verbose=verbose)

    return oauth

def _validate_creds_file(fn, oauth, verbose=False):
    """Check validity of a credentials file."""
    oauth1 = False
    oauth1_keys = ['app_key', 'app_secret', 'oauth_token', 'oauth_token_secret']
    oauth2 = False
    oauth2_keys = ['app_key', 'app_secret', 'access_token']
    if all(k in oauth for k in oauth1_keys):
        oauth1 = True
    elif all(k in oauth for k in oauth2_keys):
        oauth2 = True

    if not (oauth1 or oauth2):
        msg = 'Missing or incorrect entries in {}\n'.format(fn)
        msg += pprint.pformat(oauth)
        raise ValueError(msg)
    elif verbose:
        print('Credentials file "{}" looks good'.format(fn))


def add_access_token(creds_file=None):
    """
    For OAuth 2, retrieve an access token for an app and append it to a
    credentials file.
    """
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, 'credentials2.txt')
    oauth2 = credsfromfile(creds_file=creds_file)
    APP_KEY = oauth2['app_key']
    APP_SECRET = oauth2['app_secret']

    twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
    ACCESS_TOKEN = twitter.obtain_access_token()
    tok = 'access_token={}\n'.format(ACCESS_TOKEN)
    with open(creds_file, 'a') as f:
        print(tok, file=f)


def guess_path(pth):
    """
    If the path is not absolute, guess that it is a subdirectory of the
    user's home directory.

    :param str pth: The pathname of the directory where files of tweets should be written
    """
    if os.path.isabs(pth):
        return pth
    else:
        return os.path.expanduser(os.path.join("~", pth))


