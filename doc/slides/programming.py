# 2.1 Python the Calculator

3 + 2 * 5 - 1
3/3
1/3
1 +

### 2.2 Understanding the Basics: Strings and Variables

### 2.2.1 Representing Text

Hello World
'Hello World'
"Hello World"
'Hello' + 'World'
'Hi' + 'Hi' + 'Hi'
'Hi' * 3

### 2.2.2 Storing and reusing values

msg = 'Hello World'
msg

msg = 'Hi'
num = 3
msg * num

msg = msg * num
msg

### 2.2.3 Printing and inspecting strings

msg = 'Hello World'
msg

Now do this using IDLEs text editor

================================ RESTART ================================

print msg

msg2 = 'Goodbye'
print msg, msg2

msg = "I like NLP!"
msg = 'Hello World'

### 2.3 Slicing and Dicing

### 2.3.1 Accessing individual characters

msg[0]
msg[3]
msg[5]
msg[11]
len(msg)
msg[-1]
msg[-3]
msg[-6]

### 2.3.2 Accessing substrings

msg[1:4]
len(msg)
msg[0:11]
msg[0:-6]
msg[:3]
msg[6:]
msg[:-1]
msg[:]
msg[6:11:2]
msg[10:5:-2]

### 2.4 Strings, Sequences, and Sentences

sent = 'colorless green ideas sleep furiously'
sent[16:21]
len(sent)

### 2.4.1 Lists

phrase1 = ['colorless', 'green', 'ideas']
phrase1
len(phrase1)

phrase1[0]
phrase1[-1]
phrase1[-5]

phrase1[1:3]
phrase1[-2:]

phrase2 = phrase1 + ['sleep', 'furiously']
phrase2
phrase1

phrase1[0] = 'colorful'
phrase1

msg[0] = 'J'

phrase2.sort()
phrase2

phrase2.reverse()
phrase2

phrase2[::-1]
phrase2

phrase2.append('said')
phrase2.append('Chomsky')
phrase2

phrase2.index('green')

bat = ['bat', [[1, 'n', 'flying mammal'], [2, 'n', 'striking instrument']]]

### 2.4.2 Working on sequences one item at a time

for word in phrase2:
    print len(word), word

total = 0
for word in phrase2:
    total += len(word)

total / len(phrase2)

sent = 'colorless green ideas sleep furiously'
for char in sent:
    print char,

### 2.4.3 Tuples

t = ('walk', 'fem', 3)
t[0]

t[1:]

t[0] = 'run'

### 2.4.4 String Formatting

for word in phrase2:
    print word, '(', len(word), '),',

for word in phrase2:
    print "%s (%d)," % (word, len(word)),

for word in phrase2:
   print "Word = %s\nIndex = %s\n*****" % (word, phrase2.index(word))

str = ''
for word in phrase2:
   str += ' ' + word

str

### 2.4.5 Character encoding and Unicode


### 2.4.6 Converting between strings and lists

phrase3 = ' '.join(phrase2)
phrase3
' -> '.join(phrase2)
phrase3.split(' ')
phrase3.split('s')

### 2.5 Making Decisions

### 2.5.1 Making simple decisions

word = "cat"
if len(word) < 5:
  print 'word length is less than 5'

if len(word) >= 5:
  print 'word length is greater than or equal to 5'

if len(word) >= 5:
  print 'word length is greater than or equal to 5'
else:
  print 'word length is less than 5'

if len(word) < 3:
  print 'word length is less than three'
elif len(word) == 3:
  print 'word length is equal to three'
else:
  print 'word length is greater than three'

### 2.5.2 Conditional expressions

3 < 5
5 < 3
not 5 < 3

word = 'sovereignty'
'sovereign' in word
'gnt' in word
'pre' not in word
'Hello' in ['Hello', 'World']
'Hell' in ['Hello', 'World']

word.startswith('sovereign')
word.endswith('ty')


### 2.5.3 Iteration, items, and if

sentence = 'how now brown cow'
words = sentence.split()
words

for word in words:
    print word

'how'.endswith('ow')
'brown'.endswith('ow')

sentence = 'how now brown cow'
words = sentence.split()
for word in words:
    if word.endswith('ow'):
        print word

### 2.6 Getting organized

### 2.6.1 Accessing data with data

pos = {}
pos['colorless'] = 'adj'
pos['furiously'] = 'adv'
pos['ideas'] = 'n'

from nltk.utilities import SortedDict
pos = SortedDict(pos)

pos['ideas']
pos['colorless']
pos['missing']

'colorless' in pos
'missing' in pos

'missing' not in pos

for word in pos:
    print "%s (%s)" % (word, pos[word])
pos

pos = {'furiously': 'adv', 'ideas': 'n', 'colorless': 'adj'}
pos = SortedDict(pos)
pos.keys()
pos.values()
pos.items()

### 2.6.2 Counting with dictionaries

phrase = 'colorless green ideas sleep furiously'
count = {}
for letter in phrase:
    if letter not in count:
        count[letter] = 0
    count[letter] += 1
count

sorted(count.items())

### 2.6.3 Getting unique entries

sentence = "she sells sea shells by the sea shore".split()
words = []
for word in sentence:
    if word not in words:
        words.append(word)

sorted(words)

found = {}
for word in sentence:
    found[word] = 1

sorted(found)

set(sentence)

sentence = "she sells sea shells by the sea shore".split()
sorted(set(sentence))

### 2.6.4 Scaling it up

from nltk.corpora import gutenberg
count = {}                                        # initialize a dictionary
for word in gutenberg.raw('shakespeare-macbeth'): # tokenize Macbeth
    word = word.lower()                           # normalize to lowercase
    if word not in count:                         # seen this word before?
        count[word] = 0                           # if not, set count to zero
    count[word] += 1                              # increment the counter


count['scotland']
count['the']

### 2.7 Defining Functions

### 2.8 Regular Expressions

str = """Google Analytics is very very very nice (now)
By Jason Hoffman 18 August 06
Google Analytics, the result of Google's acquisition of the San
Diego-based Urchin Software Corporation, really really opened it's
doors to the world a couple of days ago, and it allows you to
track up to 10 sites within a single google account.
"""

text = str.split(' ')
for n in range(len(text)):
    if text[n] == 'very' and text[n+1] == 'very':
        print n, n+1

import re
from nltk.utilities import re_show
re_show('very very', str)
re_show('o+', str)
re_show('oo+', str)
re_show('(very\s)+', str)
re_show('l', sent)
re_show('green', sent)

str2 = "I'm very very\nvery happy"
re_show('very\s', str2)

re.findall('\d\d', str)
re.findall('\s\w\w\w\s', str)

re.findall(r'\b\w\w\w\b', str)
re_show('((very|really)\s)+', str)

sent = "colorless green ideas sleep furiously"
re.sub('l', 's', sent)

re.sub('green', 'red', sent)

re_show('(green|sleep)', sent)

re.findall('(green|sleep)', sent)

re_show('[^aeiou][aeiou]', sent)

re.findall('[^aeiou][aeiou]', sent)

### 2.8.1 Groupings

re.findall('\s(\w\w\w)\s', str)
re.findall('([^aeiou])[aeiou]', sent)
re.findall('([^aeiou])([aeiou])', sent)

str3 = """
<hart@vmd.cso.uiuc.edu>
Final editing was done by Martin Ward <Martin.Ward@uk.ac.durham>
Michael S. Hart <hart@pobox.com>
Prepared by David Price, email <ccx074@coventry.ac.uk>"""

re.findall(r'<(.+)@(.+)>', str3)
re.findall(r'(\w+\.)', str3)
re.findall('(G|g)oogle', str)
re.findall('(?:G|g)oogle', str)

