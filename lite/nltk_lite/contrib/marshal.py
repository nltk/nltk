# Marshaling code, contributed by Tiago Tresoldi
# This saves/loads models to/from plain text files.
# Unlike Python's shelve and pickle utilities,
# this is useful for inspecting or tweaking the models.
# We may incorporate this as a marshal method in each model.

from itertools import islice
import re

import nltk_lite.tag as tag
from nltk_lite.corpora import brown

# marshal-classes
class MarshalUnigram (tag.Unigram):
    def marshal (self, filename):
        handler = file(filename, "w")
        
        for text, tag in self._model.iteritems():
            handler.write("%s:%s\n" % (text, tag))

        handler.close()
        
    def unmarshal (self, filename):
        handler = file(filename, "r")
        
        pattern = re.compile(r'^(.+):(.+?)$', re.UNICODE)
        for line in handler.readlines():
            m = re.match(pattern, line)
            text, tag = m.groups()
            self._model[text] = tag
        
        handler.close()

class MarshalAffix (tag.Affix):
    def marshal (self, filename):
        handler = file(filename, "w")
        
        handler.write("length %i\n" % self._length)
        handler.write("minlength %i\n" % self._minlength)
        
        for text, tag in self._model.iteritems():
            handler.write("%s:%s\n" % (text, tag))

        handler.close()

    def unmarshal (self, filename):
        handler = file(filename, "r")
        
        lines = handler.readlines()
        # will fail if "length " and "minlength " are not present
        self._length = int(lines[0].split("length ")[1])
        self._minlength = int(lines[1].split("minlength ")[1])
        
        pattern = re.compile(r'^(.+):(.+?)$', re.UNICODE)
        for line in lines[2:]:
            m = re.match(pattern, line)
            text, tag = m.groups()
            self._model[text] = tag
        
        handler.close()

class MarshalNgram (tag.Ngram):
    def marshal (self, filename):
        handler = file(filename, "w")
        
        handler.write("n %i\n" % self._n)

        for entry in self._model:
            context, text, tag = entry[0], entry[1], self._model[entry]
            
            try:
                entry_str = "[%s]:%s:%s\n" % (":".join(context), text, tag)
                handler.write(entry_str)
            except TypeError:
                # None found in 'context', pass silently
                pass
        
        handler.close()

    def unmarshal (self, filename):
        handler = file(filename, "r")
        
        lines = handler.readlines()
        # will fail if "n " is not present
        self._n = int(lines[0].split("n ")[1])
        
        
        pattern = re.compile(r'^\[(.+)\]:(.+):(.+?)$', re.UNICODE)
        
        # build 'context_pattern': having to deal with the possibility of
        # the field separation character (":") being used as a tag or text,
        # the correct regexp pattern is built accordingly to self._n
        context_pattern_str = r'^(.+?)%s$' % ( r':(.+?)' * (self._n-2) )
        context_pattern = re.compile(context_pattern_str, re.UNICODE)
        
        for line in lines[1:]:
            m = re.match(pattern, line)
            context, text, tag = m.groups()
            
            c_m = re.match(context_pattern, context)
            key = (c_m.groups(), text)
            self._model[key] = tag
        
        handler.close()

# load train corpus
train_sents = list(islice(brown.tagged(), 500))

# create taggers
tagger = MarshalNgram(3)

#tagger.train(train_sents)
#tagger.marshal("ngram.test")

tagger.unmarshal("ngram.test")
print tagger._model

