import re

"""
A list of (regexp, repl) pairs applied in sequence.
The resulting string is split on whitespace.
(Adapted from the Punkt Word Tokenizer)
"""

_tokenize_regexps = [

    # uniform quotes
    (re.compile(r'\'\''), r'"'),
    (re.compile(r'\`\`'), r'"'),

    # Separate punctuation (except period) from words:
    (re.compile(r'(^|\s)(\')'), r'\1\2 '),
    (re.compile(r'(?=[\(\"\`{\[:;&\#\*@])(.)'), r'\1 '),
    
    (re.compile(r'(.)(?=[?!)\";}\]\*:@\'])'), r'\1 '),
    (re.compile(r'(?=[\)}\]])(.)'), r'\1 '),
    (re.compile(r'(.)(?=[({\[])'), r'\1 '),
    (re.compile(r'((^|\s)\-)(?=[^\-])'), r'\1 '),

    # Treat double-hyphen as one token:
    (re.compile(r'([^-])(\-\-+)([^-])'), r'\1 \2 \3'),
    (re.compile(r'(\s|^)(,)(?=(\S))'), r'\1\2 '),

    # Only separate comma if space follows:
    (re.compile(r'(.)(,)(\s|$)'), r'\1 \2\3'),

    # Combine dots separated by whitespace to be a single token:
    (re.compile(r'\.\s\.\s\.'), r'...'),

    # Separate "No.6"
    (re.compile(r'([A-Za-z]\.)(\d+)'), r'\1 \2'),
    
    # Separate words from ellipses
    (re.compile(r'([^\.]|^)(\.{2,})(.?)'), r'\1 \2 \3'),
    (re.compile(r'(^|\s)(\.{2,})([^\.\s])'), r'\1\2 \3'),
    (re.compile(r'([^\.\s])(\.{2,})($|\s)'), r'\1 \2\3'),

    ## adding a few things here:

    # fix %, $, &
    (re.compile(r'(\d)%'), r'\1 %'),
    (re.compile(r'\$(\.?\d)'), r'$ \1'),
    (re.compile(r'(\w)& (\w)'), r'\1&\2'),
    (re.compile(r'(\w\w+)&(\w\w+)'), r'\1 & \2'),

    # fix (n 't) --> ( n't)
    (re.compile(r'n \'t( |$)'), r" n't\1"),
    (re.compile(r'N \'T( |$)'), r" N'T\1"),

    # treebank tokenizer special words
    (re.compile(r'([Cc])annot'), r'\1an not'),

    (re.compile(r'\s+'), r' '),
    
    ]

def tokenize(s):
    """
    Tokenize a string using the rule above
    """
    for (regexp, repl) in _tokenize_regexps:
        s = regexp.sub(repl, s)
    return s

