# Natural Language Toolkit: Gutenberg Corpus Reader
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import re, codecs
from plaintext import PlaintextCorpusReader
from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *

class GutenbergCorpusReader(PlaintextCorpusReader):
    class CorpusView(StreamBackedCorpusView):
        def __init__(self, filename, block_reader, encoding=None):
            startpos = 0
            
            # Search for a preamble.
            self._open()
            for i in range(300):
                line = self._stream.readline()
                if line == '':
                    break # No preamble found!
                if re.match(r'\*END\*?\s*THE\s*SMALL\s*PRINT', line):
                    startpos = self._stream.tell()
                    break # End of the preamble!
            self.close()
    
            StreamBackedCorpusView.__init__(self, filename,
                                            block_reader, startpos,
                                            encoding=encoding)
    
