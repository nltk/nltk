"""
Examples of using the NLTK token architecture for speech segmentation.
The entire transcript is a single token, and each turn is a subtoken.
The temporal span of a turn is just the location of the subtoken.
"""

from nltk.token import *
from nltk.tokenizer import *
import re

class SignalLocation(SpanLocation):
    __slots__ = ()
    UNIT = 's' # seconds

# transcript from LDC Callhome
transcript = """
16.35 19.59 A: So tell me I mean it was	shocking for us and we just heard it.  
20.15 24.36 A: You know the night it happened on the news it was a little blip and &Paul and I were watching T V and we just  
25.15 27.10 A: looked at each other with our mouths open.  
27.56 28.88 B: uh-huh. I'm sure.  
27.98 28.72 A: You know so  
29.87 33.01 B: well you know what was really {lipsmack} it was really kind of weird  
34.05 35.02 B: %um {sigh}  
35.42 38.18 B: I mean when I heard he got shot I I wasn't really surprised  
38.15 38.69 A: mhm.  
38.60 41.25 B: But then when I heard he was dead I was really surprised  
41.17 41.56 A: yeah?  
42.35 48.35 B: You know because I thought okay so if he was shot you know he'll be okay [[whiney and drawn out]] like &Reagan when he was shot he was okay  
48.50 59.54 B: {breath} %um {lipsmack} but %um you know then it was like really not long after I heard that he was shot that I heard that he was dead it was kind of strange {breath}  
57.07 57.53 A: mhm  
59.66 64.02 B: So [[changes to higher pitch]] it was a very you know it's been a weird few days then we had
"""

token = Token(TEXT=transcript)
LineTokenizer().tokenize(token)
for t in token['SUBTOKENS']:
    r = re.match(r'(\d+\.\d+) (\d+\.\d+) ([AB]): (.*)', t['TEXT'])
    if r:
        (start, end, spkr, text) = r.group(1,2,3,4)
        print start, end, spkr, text
        t['TEXT'] = text.strip()
        t['LOC'] = SignalLocation(start, end)
        t['SPKR'] = spkr
print token

        
        
        
        



