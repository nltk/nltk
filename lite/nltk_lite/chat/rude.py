# Natural Language Toolkit: Zen Chatbot
#
# Copyright (C) 2005 University of Melbourne
# Author: Peter Spiller <pspiller@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from re import *
from nltk_lite.chat import *

pairs = (
    (r'We (.*)',
        ("What do you mean, 'we'?",
        "Don't include me in that!",
        "I wouldn't be so sure about that.")),

    (r'You should (.*)',
        ("Don't tell me what to do, buddy.",
        "Really? I should, should I?")),
 
    (r'You\'re(.*)',
        ("More like YOU'RE %1!",
        "Hah! Look who's talking.",
        "Come over here and tell me I'm %1.")),

    (r'You are(.*)',
        ("More like YOU'RE %1!",
        "Hah! Look who's talking.",
        "Come over here and tell me I'm %1.")),

    (r'I can\'t(.*)',
        ("You do sound like the type who can't %1.",
        "Hear that splashing sound? That's my heart bleeding for you.",
        "Tell somebody who might actually care.")),

    (r'I think (.*)',
        ("I wouldn't think too hard if I were you.",
        "You actually think? I'd never have guessed...")),

    (r'I (.*)',
        ("I'm getting a bit tired of hearing about you.",
        "How about we talk about me instead?",
        "Me, me, me... Frankly, I don't care.")),
                
    (r'How (.*)',
        ("How do you think?",
        "Take a wild guess.",
        "I'm not even going to dignify that with an answer.")),

    (r'What (.*)',
        ("Do I look like an encylopedia?",
        "Figure it out yourself.")),

    (r'Why (.*)',
        ("Why not?",
        "That's so obvious I thought even you'd have already figured it out.")),

    (r'(.*)shut up(.*)',
        ("Make me.",
        "Getting angry at a feeble NLP assignment? Somebody's losing it.",
        "Say that again, I dare you.")),

    (r'Shut up(.*)',
        ("Make me.",
        "Getting angry at a feeble NLP assignment? Somebody's losing it.",
        "Say that again, I dare you.")),

    (r'Hello(.*)',
        ("Oh good, somebody else to talk to. Joy.",
        "'Hello'? How original...")),
            
    (r'(.*)',
        ("I'm getting bored here. Become more interesting.",
        "Either become more thrilling or get lost, buddy.",
        "Change the subject before I die of fatal boredom."))
)

rude = Chat(pairs, reflections) 

def demo():    
    print "Unpleasant Chatbot (type 'quit' to exit)."
    print '='*72
    print "I suppose I should say hello."
    converse(rude)

if __name__ == "__main__":
    demo()
