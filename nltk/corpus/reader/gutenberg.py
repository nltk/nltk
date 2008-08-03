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
from nltk.data import FileSystemPathPointer

class GutenbergCorpusReader(PlaintextCorpusReader):
    class CorpusView(StreamBackedCorpusView):
        def __init__(self, filename, block_reader, encoding=None):
            startpos = 0
            
            # Search for a preamble.
            if isinstance(filename, PathPointer):
                stream = filename.open(encoding)
            else:
                stream = FileSystemPathPointer(filename).open(encoding)
            for i in range(300):
                line = stream.readline()
                if line == '':
                    break # No preamble found!
                if re.match(r'\*END\*?\s*THE\s*SMALL\s*PRINT', line):
                    startpos = stream.tell()
                    break # End of the preamble!
            stream.close()
    
            StreamBackedCorpusView.__init__(self, filename,
                                            block_reader, startpos,
                                            encoding=encoding)
    
