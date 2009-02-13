# Natural Language Toolkit: Chatbots
#
# Copyright (C) 2001-2009 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# Based on an Eliza implementation by Joe Strout <joe@strout.net>,
# Jeff Epler <jepler@inetnebr.com> and Jez Higgins <jez@jezuk.co.uk>.

"""
A class for simple chatbots.  These perform simple pattern matching on sentences
typed by users, and respond with automatically generated sentences.

These chatbots may not work using the windows command line or the
windows IDLE GUI.
"""

from util import *
from eliza import eliza_chat
from iesha import iesha_chat
from rude import rude_chat
from suntsu import suntsu_chat
from zen import zen_chat

bots = [
    (eliza_chat,  'Eliza (psycho-babble)'),
    (iesha_chat,  'Iesha (teen anime junky)'),
    (rude_chat,   'Rude (abusive bot)'),
    (suntsu_chat, 'Suntsu (Chinese sayings)'),
    (zen_chat,    'Zen (gems of wisdom)')]

def chatbots():
    import sys
    print 'Which chatbot would you like to talk to?'
    botcount = len(bots)
    for i in range(botcount):
        print '  %d: %s' % (i+1, bots[i][1])
    print '\nPEnter a number in the range 1-%d: ' % botcount,
    choice = sys.stdin.readline().strip()
    print
    if not (choice.isdigit() and int(choice) in range(botcount)):
        print 'Bad chatbot number'
        return

    chatbot = bots[int(choice)-1][0]
    chatbot()
