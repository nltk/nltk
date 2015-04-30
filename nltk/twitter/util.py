# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility functions to accompany :module:`twitterclient`.
"""
from __future__ import print_function
import csv
import json
import os
import pprint
import nltk.compat as compat

from twython import Twython


def extract_fields(tweet, fields):
    """
    Extract field values from a full tweet and return them as a list

    :param json tweet: The tweet in JSON format
    :param list fields: The fields to be extracted from the tweet
    :rtype: list(str)
    """
    out = []
    for field in fields:
        try:
            _add_field_to_out(tweet, field, out)
        except TypeError:
            raise RuntimeError('Fatal error when extracting fields. Cannot find field ', field)
    return out


def _add_field_to_out(json, field, out):
    if isinstance(field, dict):
        for key, value in field.iteritems():
            _add_field_to_out(json[key], value, out)
    else:
        if isinstance(field, basestring):
            out += [json[field]]
        else:
            out += [json[value] for value in field]

def _get_entity_recursive(json, entity):
    if json == None:
        return None
    if isinstance(json, dict):
        for key, value in json.iteritems():
            if key == entity:
                return value
            candidate = _get_entity_recursive(value, entity)
            if candidate != None:
                return candidate
        return None
    elif isinstance(json, list):
        for item in json:
            candidate = _get_entity_recursive(item, entity)
            if candidate != None:
                return candidate
        return None
    else:
        return None

def json2csv(infile, outfile, fields, encoding='utf8', errors='replace'):
    """
    Extract selected fields from a file of line-separated JSON tweets and
    write to a file in CSV format.

    This utility function allows a file of full tweets to be easily converted
    to a CSV file for easier processing. For example, just tweetIDs or
    just the text content of the tweets can be extracted.

    Additionally, the function allows combinations of fields of other Twitter
    objects (mainly the users, see below).

    For Twitter entities (e.g. hashtags of a tweet), and for geolocation, see
    `json2csv_entities`

    :param str infile: The name of the file containing full tweets

    :param str outfile: The name of the text file where results should be\
    written

    :param list fields: The list of fields to be extracted. Useful examples\
    are 'id_str' for the tweetID and 'text' for the text of the tweet. See\
    <https://dev.twitter.com/overview/api/tweets> for a full list of fields.
    e. g.: ['id_str'], ['id', 'text', 'favorite_count', 'retweet_count']
    Addionally, it allows IDs from other Twitter objects, e. g.,\
    ['id', 'text', {'user' : ['id', 'followers_count', 'friends_count']}]


    :param error: Behaviour for encoding errors, see\
    https://docs.python.org/3/library/codecs.html#codec-base-classes
    """
    with open(infile) as inf:
        writer = get_outf_writer_compat(outfile, encoding, errors)
        for line in inf:
            tweet = json.loads(line)
            row = extract_fields(tweet, fields)
            writer.writerow(row)

def get_outf_writer_compat(outfile, encoding, errors):
    """
    Identify appropriate CSV writer given the Python version
    """
    if compat.PY3 == True:
        outf = open(outfile, 'w', encoding=encoding, errors=errors)
        writer = csv.writer(outf)
    else:
        outf = open(outfile, 'wb')
        writer = compat.UnicodeWriter(outf, encoding=encoding, errors=errors)
    return writer


def json2csv_entities(infile, outfile, main_fields, entity_name, entity_fields,
                      encoding='utf8', errors='replace'):
    """
    Extract selected fields from a file of line-separated JSON tweets and
    write to a file in CSV format.

    This utility function allows a file of full tweets to be easily converted
    to a CSV file for easier processing of Twitter entities. For example, the
    hashtags or media elements of a tweet can be extracted.

    :param str infile: The name of the file containing full tweets

    :param str outfile: The name of the text file where results should be\
    written

    :param list main_fields: The list of fields to be extracted from the main\
    object, usually the tweet. Useful examples: 'id_str' for the tweetID. See\
    <https://dev.twitter.com/overview/api/tweets> for a full list of fields.
    e. g.: ['id_str'], ['id', 'text', 'favorite_count', 'retweet_count']
    If entity_name is expressed as a dictionary, then it is list of fields\
    of the object that corresponds to the key of the dictionary (could be\
    the user object, or the place of a tweet object).

    :param list entity_name: The name of the entity: 'hashtags', 'media',\
    'urls' and 'user_mentions' for the tweet object. For the user object,\
    needs to be expressed as a dictionary: {'user' : 'urls'}. For the\
    bounding box of the place from which a tweet was twitted, as a dict\
    as well: {'place', 'bounding_box'}

    :param list entity_fields: The list of fields to be extracted from the\
    entity. E.g. ['text'] (of the hashtag)

    :param error: Behaviour for encoding errors, see\
    https://docs.python.org/3/library/codecs.html#codec-base-classes
    """
    with open(infile) as inf:
        writer = get_outf_writer_compat(outfile, encoding, errors)
        for line in inf:
            tweet = json.loads(line)
            if isinstance(entity_name, dict):
                for key, value in entity_name.iteritems():
                    object_json = _get_entity_recursive(tweet, key)
                    if object_json == None:
                        # can happen in the case of "place"
                        continue
                    object_fields = extract_fields(object_json, main_fields)
                    items = _get_entity_recursive(object_json, value)
                    _write_to_file(object_fields, items, entity_fields, writer)
            else:
                tweet_fields = extract_fields(tweet, main_fields)
                items = _get_entity_recursive(tweet, entity_name)
                _write_to_file(tweet_fields, items, entity_fields, writer)


def _write_to_file(object_fields, items, entity_fields, writer):
    if items == None:
        # it could be that the entity is just not present for the tweet
        # e.g. tweet hashtag is always present, even as [], however
        # tweet media may not be present
        return
    if isinstance(items, dict):
        # this happens for "place" of a tweet
        row = object_fields
        for key, value in items.iteritems():
            if key in entity_fields:
                if isinstance(value, list):
                    row += value
                else:
                    row += [value]
        writer.writerow(row)
        return
    # in general it is a list
    for item in items:
        row = object_fields + extract_fields(item, entity_fields)
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
    if creds_file is None:
        creds_file = 'credentials.txt'
    if not subdir:
        try:
            subdir = os.environ['TWITTER']
            creds_fullpath = os.path.normpath(os.path.join(subdir, creds_file))
            if not os.path.isfile(creds_fullpath):
                raise OSError('Cannot find file {}'.format(creds_fullpath))
        except KeyError:
            print("Supply a value to the 'subdir' parameter or set the \
            TWITTER environment variable.")
            raise FileNotFoundError from KeyError


    with open(creds_fullpath) as infile:
        if verbose:
            print('Reading credentials file {}'.format(creds_fullpath))
        oauth = {}
        for line in infile:
            if '=' in line:
                name, value = line.split('=', 1)
                oauth[name.strip()] = value.strip()

    _validate_creds_file(creds_file, oauth, verbose=verbose)

    return oauth

def _validate_creds_file(fname, oauth, verbose=False):
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
        msg = 'Missing or incorrect entries in {}\n'.format(fname)
        msg += pprint.pformat(oauth)
        raise ValueError(msg)
    elif verbose:
        print('Credentials file "{}" looks good'.format(fname))


def add_access_token(creds_file=None):
    """
    For OAuth 2, retrieve an access token for an app and append it to a
    credentials file.
    """
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, 'credentials2.txt')
    oauth2 = credsfromfile(creds_file=creds_file)
    app_key = oauth2['app_key']
    app_secret = oauth2['app_secret']

    twitter = Twython(app_key, app_secret, oauth_version=2)
    access_token = twitter.obtain_access_token()
    tok = 'access_token={}\n'.format(access_token)
    with open(creds_file, 'a') as infile:
        print(tok, file=infile)


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
