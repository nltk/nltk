
%% Notes:
%% - We should adjust the ``95%'' figure to something that is not trivial but
%%   that shouldn't take more than 15-20 minutes to find.
%% - Replace n with an appropriate value in ``pn''
%% - Rewrite ``contest'' section, depending on what we want to do.

\section{Chunk Parsing}
  % This problem is intended to reinforce the concepts behind
  % ChunkParsing, and to provide students with a chance to play with
  % different chunk parsing techniques.  It is intended to take 15-20
  % minutes to complete, once the student understands the basic
  % concepts.
  %
  % The problem also includes an optional contest, which gives the
  % students some incentive to go beyond the basics, and really get
  % some experience as to what works and what doesn't.

  The following code creates and tests a simple chunk parser for
  finding NP chunks.

\begin{verbatim}
from nltk.token import LineTokenizer
from nltk.chunkparser import ChunkedTaggedTokenizer, ChunkScore, unchunk
from nltk.rechunkparser import *

# Create the chunk parser.
rule1 = ChunkRule('<DT|JJ|NN>+', "Chunk sequences of DT, JJ, and NN")
chunkparser = REChunkParser( [rule1] )

# Read the test corpus.
text = open('testcorpus.txt').read()
sentences = LineTokenizer().tokenize(text)

# Test the chunk parser.
chunkscore = ChunkScore()
ctt = ChunkedTaggedTokenizer()
for sentence in sentences:
    correct = ctt.tokenize(sentence.type(), source=sentence.loc())
    unchunked = unchunk(correct)
    guess = chunkparser.parse(unchunked)
    chunkscore.score(correct, guess)

print chunkscore
\end{verbatim}

  Create and test a more advanced \texttt{REChunkParser} for finding
  NP chunks.  Your chunk parser should achieve an F-Measure value of
  at least 95\% on the example corpus.  Your parser can use any
  combination of rules (\texttt{ChunkRule}, \texttt{ChinkRule},
  \texttt{UnChunkRule}, \texttt{MergeRule}, \texttt{SplitRule}, and
  \texttt{REChunkParserRule}).

  Define a function \textit{pn}, which returns your parser.

% Do we want a contest?  If so, do we want prizes?
  \subsection*{Optional Contest}

    We will be testing your chunk parsers on an unpublished section of
    the Wall Street Journal.  The student whose parser gets the
    highest F-Measure score will be rewarded with fame and fortune.
    \emph{The performance of your chunk parser on the unpublished test
    corpus will have no effect on your grade.}
