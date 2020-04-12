NLTK News
=========

2020
----

NLTK 3.5 release: April 2020
  Add support for Python 3.8, drop support for Python 2

2019
----

NLTK 3.4.5 release: August 2019
  Fixed security bug in downloader: Zip slip vulnerability - for the unlikely
  situation where a user configures their downloader to use a compromised server
  https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-14751)

NLTK 3.4.4 release: July 2019
  Fix bug in plot function (probability.py)
  Add improved PanLex Swadesh corpus reader  

NLTK 3.4.3 release: June 2019
  Add Text.generate(), QuadgramAssocMeasures
  Add SSP to tokenizers
  Return confidence of best tag from AveragedPerceptron
  Make plot methods return Axes objects
  Minor bug fixes
  Update installation instructions

NLTK 3.4.1 release: April 2019
  Add chomsky_normal_form for CFGs
  Add meteor score
  Add minimum edit/Levenshtein distance based alignment function
  Allow access to collocation list via text.collocation_list()
  Support corenlp server options
  Drop support for Python 3.4
  Other minor fixes

2018
----

NLTK 3.4 release: November 2018
  Support Python 3.7,
  New Language Modeling package,
  Cistem Stemmer for German,
  Support Russian National Corpus incl POS tag model,
  Krippendorf Alpha inter-rater reliability test,
  Comprehensive code clean-ups,
  Switch continuous integration from Jenkins to Travis

NLTK 3.3 release: May 2018
   Support Python 3.6,
   New interface to CoreNLP,
   Support synset retrieval by sense key,
   Minor fixes to CoNLL Corpus Reader, AlignedSent,
   Fixed minor inconsistencies in APIs and API documentation,
   Better conformance to PEP8,
   Drop Moses Tokenizer (incompatible license)

2017
----

NLTK 3.2.5 release: September 2017
   Arabic stemmers (ARLSTem, Snowball), 
   NIST MT evaluation metric and added NIST international_tokenize, 
   Moses tokenizer, 
   Document Russian tagger, 
   Fix to Stanford segmenter, 
   Improve treebank detokenizer, VerbNet, Vader, 
   Misc code and documentation cleanups, 
   Implement fixes suggested by LGTM 

NLTK 3.2.4 released: May 2017
   Remove load-time dependency on Python requests library,
   Add support for Arabic in StanfordSegmenter

NLTK 3.2.3 released: May 2017
   Interface to Stanford CoreNLP Web API, improved Lancaster stemmer,
   improved Treebank tokenizer, support custom tab files for extending WordNet,
   speed up TnT tagger, speed up FreqDist and ConditionalFreqDist,
   new corpus reader for MWA subset of PPDB; improvements to testing framework

2016
----

NLTK 3.2.2 released: December 2016
   Support for Aline, ChrF and GLEU MT evaluation metrics,
   Russian POS tagger model, Moses detokenizer,
   rewrite Porter Stemmer and FrameNet corpus reader,
   update FrameNet Corpus to version 1.7,
   fixes: stanford_segmenter.py, SentiText, CoNLL Corpus Reader,
   BLEU, naivebayes, Krippendorff's alpha, Punkt, Moses tokenizer,
   TweetTokenizer, ToktokTokenizer;
   improvements to testing framework

NLTK 3.2.1 released: April 2016
   Support for CCG semantics, Stanford segmenter, VADER lexicon;
   Fixes to BLEU score calculation, CHILDES corpus reader.

NLTK 3.2 released : March 2016
   Fixes for Python 3.5, code cleanups now Python 2.6 is no longer
   supported, support for PanLex, support for third party download
   locations for NLTK data, new support for RIBES score, BLEU
   smoothing, corpus-level BLEU, improvements to TweetTokenizer,
   updates for Stanford API, add mathematical operators to
   ConditionalFreqDist, fix bug in sentiwordnet for adjectives,
   improvements to documentation, code cleanups, consistent handling
   of file paths for cross-platform operation.

2015
----

NLTK 3.1 released : October 2015
   Add support for Python 3.5, drop support for Python 2.6,
   sentiment analysis package and several corpora,
   improved POS tagger, Twitter package,
   multi-word expression tokenizer,
   wrapper for Stanford Neural Dependency Parser,
   improved translation/alignment module including stack decoder,
   skipgram and everygram methods,
   Multext East Corpus and MTECorpusReader,
   minor bugfixes and enhancements

NLTK 3.0.5 released : September 2015
   New Twitter package; updates to IBM models 1-3, new models 4 and 5,
   minor bugfixes and enhancements

NLTK 3.0.4 released : July 2015
   Minor bugfixes and enhancements.

NLTK 3.0.3 released : June 2015
   PanLex Swadesh Corpus, tgrep tree search, minor bugfixes.

NLTK 3.0.2 released : March 2015
   Senna, BLLIP, python-crfsuite interfaces, transition-based dependency parsers,
   dependency graph visualization, NKJP corpus reader, minor bugfixes and clean-ups.

NLTK 3.0.1 released : January 2015
   Minor packaging update.

2014
----

NLTK 3.0.0 released : September 2014
   Minor bugfixes.

NLTK 3.0.0b2 released : August 2014
   Minor bugfixes and clean-ups.

NLTK Book Updates : July 2014
   The NLTK book is being updated for Python 3 and NLTK 3 `here <http://nltk.org/book>`_.
   The original Python 2 edition is still available `here <http://nltk.org/book_1ed>`_.

NLTK 3.0.0b1 released : July 2014
   FrameNet, SentiWordNet, universal tagset, misc efficiency improvements and bugfixes
   Several API changes, see https://github.com/nltk/nltk/wiki/Porting-your-code-to-NLTK-3.0

NLTK 3.0a4 released : June 2014
   FrameNet, universal tagset, misc efficiency improvements and bugfixes
   Several API changes, see https://github.com/nltk/nltk/wiki/Porting-your-code-to-NLTK-3.0
   For full details see:
   https://github.com/nltk/nltk/blob/develop/ChangeLog
   http://nltk.org/nltk3-alpha/

2013
----

NLTK Book Updates : October 2013
   We are updating the NLTK book for Python 3 and NLTK 3; please see
   http://nltk.org/book3/

NLTK 3.0a2 released : July 2013
   Misc efficiency improvements and bugfixes; for details see
   https://github.com/nltk/nltk/blob/develop/ChangeLog
   http://nltk.org/nltk3-alpha/

NLTK 3.0a1 released : February 2013
   This version adds support for NLTK's graphical user interfaces.
   http://nltk.org/nltk3-alpha/

NLTK 3.0a0 released : January 2013
   The first alpha release of NLTK 3.0 is now available for testing. This version of NLTK works with Python 2.6, 2.7, and Python 3.
   http://nltk.org/nltk3-alpha/

2012
----

Python Grant : November 2012
   The Python Software Foundation is sponsoring Mikhail Korobov's work on porting NLTK to Python 3.
   http://pyfound.blogspot.hu/2012/11/grants-to-assist-kivy-nltk-in-porting.html

NLTK 2.0.4 released : November 2012
    Minor fix to remove numpy dependency.

NLTK 2.0.3 released : September 2012
    This release contains minor improvements and bugfixes.  This is the final release compatible with Python 2.5.

NLTK 2.0.2 released : July 2012
    This release contains minor improvements and bugfixes.

NLTK 2.0.1 released : May 2012
    The final release of NLTK 2.

NLTK 2.0.1rc4 released : February 2012
    The fourth release candidate for NLTK 2.

NLTK 2.0.1rc3 released : January 2012
    The third release candidate for NLTK 2.

2011
----

NLTK 2.0.1rc2 released : December 2011
    The second release candidate for NLTK 2.  For full details see the ChangeLog.

NLTK development moved to GitHub : October 2011
    The development site for NLTK has moved from GoogleCode to GitHub: http://github.com/nltk

NLTK 2.0.1rc1 released : April 2011
    The first release candidate for NLTK 2.  For full details see the ChangeLog.

2010
----

Python Text Processing with NLTK 2.0 Cookbook : December 2010
    Jacob Perkins has written a 250-page cookbook full of great recipes for text processing using Python and NLTK, published by Packt Publishing.  Some of the royalties are being donated to the NLTK project.

Japanese translation of NLTK book : November 2010
    Masato Hagiwara has translated the NLTK book into Japanese, along with an extra chapter on particular issues with Japanese language process.  See http://www.oreilly.co.jp/books/9784873114705/.

NLTK 2.0b9 released : July 2010
    The last beta release before 2.0 final.  For full details see the ChangeLog.

NLTK in Ubuntu 10.4 (Lucid Lynx) : February 2010
    NLTK is now in the latest LTS version of Ubuntu, thanks to the efforts of Robin Munn.  See http://packages.ubuntu.com/lucid/python/python-nltk

NLTK 2.0b? released : June 2009 - February 2010
    Bugfix releases in preparation for 2.0 final.  For full details see the ChangeLog.

2009
----

NLTK Book in second printing : December 2009
    The second print run of Natural Language Processing with Python will go on sale in January.  We've taken the opportunity to make about 40 minor corrections.  The online version has been updated.

NLTK Book published : June 2009
    Natural Language Processing with Python, by Steven Bird, Ewan Klein and Edward Loper, has been published by O'Reilly Media Inc.  It can be purchased in hardcopy, ebook, PDF or for online access, at http://oreilly.com/catalog/9780596516499/.  For information about sellers and prices, see https://isbndb.com/d/book/natural_language_processing_with_python/prices.html.

Version 0.9.9 released : May 2009
    This version finalizes NLTK's API ahead of the 2.0 release and the publication of the NLTK book.  There have been dozens of minor enhancements and bugfixes.  Many names of the form nltk.foo.Bar are now available as nltk.Bar.  There is expanded functionality in the decision tree, collocations, and Toolbox modules.  A new translation toy nltk.misc.babelfish has been added.  A new module nltk.help gives access to tagset documentation.  Fixed imports so NLTK will build and install without Tkinter (for running on servers).  New data includes a maximum entropy chunker model and updated grammars.  NLTK Contrib includes updates to the coreference package (Joseph Frazee) and the ISRI Arabic stemmer (Hosam Algasaier).  The book has undergone substantial editorial corrections ahead of final publication.  For full details see the ChangeLog.

Version 0.9.8 released : February 2009
    This version contains a new off-the-shelf tokenizer, POS tagger, and named-entity tagger.  A new metrics package includes inter-annotator agreement scores and various distance and word association measures (Tom Lippincott and Joel Nothman).  There's a new collocations package (Joel Nothman).  There are many improvements to the WordNet package and browser (Steven Bethard, Jordan Boyd-Graber, Paul Bone), and to the semantics and inference packages (Dan Garrette).  The NLTK corpus collection now includes the PE08 Parser Evaluation data, and the CoNLL 2007 Basque and Catalan Dependency Treebanks.  We have added an interface for dependency treebanks.  Many chapters of the book have been revised in response to feedback from readers.  For full details see the ChangeLog.  NB some method names have been changed for consistency and simplicity.  Use of old names will generate deprecation warnings that indicate the correct name to use.

2008
----

Version 0.9.7 released : December 2008
    This version contains fixes to the corpus downloader (see instructions) enabling NLTK corpora to be released independently of the software, and to be stored in compressed format.  There are improvements in the grammars, chart parsers, probability distributions, sentence segmenter, text classifiers and RTE classifier.  There are many further improvements to the book.  For full details see the ChangeLog.

Version 0.9.6 released : December 2008
    This version has an incremental corpus downloader (see instructions) enabling NLTK corpora to be released independently of the software.  A new WordNet interface has been developed by Steven Bethard (details).   NLTK now has support for dependency parsing, developed by Jason Narad (sponsored by Google Summer of Code).  There are many enhancements to the semantics and inference packages, contributed by Dan Garrette.  The frequency distribution classes have new support for tabulation and plotting.  The Brown Corpus reader has human readable category labels instead of letters.  A new Swadesh Corpus containing comparative wordlists has been added.  NLTK-Contrib includes a TIGERSearch implementation for searching treebanks (Torsten Marek).  Most chapters of the book have been substantially revised.

The NLTK Project has moved : November 2008
    The NLTK project has moved to Google Sites, Google Code and Google Groups.  Content for users and the nltk.org domain is hosted on Google Sites.  The home of NLTK development is now Google Code.  All discussion lists are at Google Groups.  Our old site at nltk.sourceforge.net will continue to be available while we complete this transition.  Old releases are still available via our SourceForge release page.  We're grateful to SourceForge for hosting our project since its inception in 2001.

Version 0.9.5 released : August 2008
    This version contains several low-level changes to facilitate installation, plus updates to several NLTK-Contrib projects. A new text module gives easy access to text corpora for newcomers to NLP. For full details see the ChangeLog. 

Version 0.9.4 released : August 2008
    This version contains a substantially expanded semantics package contributed by Dan Garrette, improvements to the chunk, tag, wordnet, tree and feature-structure modules, Mallet interface, ngram language modeling, new GUI tools (WordNet? browser, chunking, POS-concordance). The data distribution includes the new NPS Chat Corpus. NLTK-Contrib includes the following new packages (still undergoing active development) NLG package (Petro Verkhogliad), dependency parsers (Jason Narad), coreference (Joseph Frazee), CCG parser (Graeme Gange), and a first order resolution theorem prover (Dan Garrette). For full details see the ChangeLog. 
NLTK presented at ACL conference : June 2008
    A paper on teaching courses using NLTK will be presented at the ACL conference: Multidisciplinary Instruction with the Natural Language Toolkit 

Version 0.9.3 released : June 2008
    This version contains an improved WordNet? similarity module using pre-built information content files (included in the corpus distribution), new/improved interfaces to Weka, MEGAM and Prover9/Mace4 toolkits, improved Unicode support for corpus readers, a BNC corpus reader, and a rewrite of the Punkt sentence segmenter contributed by Joel Nothman. NLTK-Contrib includes an implementation of incremental algorithm for generating referring expression contributed by Margaret Mitchell. For full details see the ChangeLog. 

NLTK presented at LinuxFest Northwest : April 2008
    Sean Boisen presented NLTK at LinuxFest Northwest, which took place in Bellingham, Washington. His presentation slides are available at: http://semanticbible.com/other/talks/2008/nltk/main.html 

NLTK in Google Summer of Code : April 2008
    Google Summer of Code will sponsor two NLTK projects. Jason Narad won funding for a project on dependency parsers in NLTK (mentored by Sebastian Riedel and Jason Baldridge).  Petro Verkhogliad won funding for a project on natural language generation in NLTK (mentored by Robert Dale and Edward Loper). 

Python Software Foundation adopts NLTK for Google Summer of Code application : March 2008
    The Python Software Foundation has listed NLTK projects for sponsorship from the 2008 Google Summer of Code program. For details please see http://wiki.python.org/moin/SummerOfCode. 

Version 0.9.2 released : March 2008
    This version contains a new inference module linked to the Prover9/Mace4 theorem-prover and model checker (Dan Garrette, Ewan Klein). It also includes the VerbNet? and PropBank? corpora along with corpus readers. A bug in the Reuters corpus reader has been fixed. NLTK-Contrib includes new work on the WordNet? browser (Jussi Salmela). For full details see the ChangeLog 

Youtube video about NLTK : January 2008
    The video from of the NLTK talk at the Bay Area Python Interest Group last July has been posted at http://www.youtube.com/watch?v=keXW_5-llD0 (1h15m) 

Version 0.9.1 released : January 2008
    This version contains new support for accessing text categorization corpora, along with several corpora categorized for topic, genre, question type, or sentiment. It includes several new corpora: Question classification data (Li & Roth), Reuters 21578 Corpus, Movie Reviews corpus (Pang & Lee), Recognising Textual Entailment (RTE) Challenges. NLTK-Contrib includes expanded support for semantics (Dan Garrette), readability scoring (Thomas Jakobsen, Thomas Skardal), and SIL Toolbox (Greg Aumann). The book contains many improvements in early chapters in response to reader feedback. For full details see the ChangeLog. 

2007
----

NLTK-Lite 0.9 released : October 2007
    This version is substantially revised and expanded from version 0.8. The entire toolkit can be accessed via a single import statement "import nltk", and there is a more convenient naming scheme. Calling deprecated functions generates messages that help programmers update their code. The corpus, tagger, and classifier modules have been redesigned. All functionality of the old NLTK 1.4.3 is now covered by NLTK-Lite 0.9. The book has been revised and expanded. A new data package incorporates the existing corpus collection and contains new sections for pre-specified grammars and pre-computed models. Several new corpora have been added, including treebanks for Portuguese, Spanish, Catalan and Dutch. A Macintosh distribution is provided. For full details see the ChangeLog. 

NLTK-Lite 0.9b2 released : September 2007
    This version is substantially revised and expanded from version 0.8. The entire toolkit can be accessed via a single import statement "import nltk", and many common NLP functions accessed directly, e.g. nltk.PorterStemmer?, nltk.ShiftReduceParser?. The corpus, tagger, and classifier modules have been redesigned. The book has been revised and expanded, and the chapters have been reordered. NLTK has a new data package incorporating the existing corpus collection and adding new sections for pre-specified grammars and pre-computed models. The Floresta Portuguese Treebank has been added. Release 0.9b2 fixes several minor problems with 0.9b1 and removes the numpy dependency. It includes a new corpus and corpus reader for Brazilian Portuguese news text (MacMorphy?) and an improved corpus reader for the Sinica Treebank, and a trained model for Portuguese sentence segmentation. 

NLTK-Lite 0.9b1 released : August 2007
    This version is substantially revised and expanded from version 0.8. The entire toolkit can be accessed via a single import statement "import nltk", and many common NLP functions accessed directly, e.g. nltk.PorterStemmer?, nltk.ShiftReduceParser?. The corpus, tagger, and classifier modules have been redesigned. The book has been revised and expanded, and the chapters have been reordered. NLTK has a new data package incorporating the existing corpus collection and adding new sections for pre-specified grammars and pre-computed models. The Floresta Portuguese Treebank has been added. For full details see the ChangeLog?. 

NLTK talks in São Paulo : August 2007
    Steven Bird will present NLTK in a series of talks at the First Brazilian School on Computational Linguistics, at the University of São Paulo in the first week of September. 

NLTK talk in Bay Area : July 2007
    Steven Bird, Ewan Klein, and Edward Loper will present NLTK at the Bay Area Python Interest Group, at Google on Thursday 12 July. 

NLTK-Lite 0.8 released : July 2007
    This version is substantially revised and expanded from version 0.7. The code now includes improved interfaces to corpora, chunkers, grammars, frequency distributions, full integration with WordNet? 3.0 and WordNet? similarity measures. The book contains substantial revision of Part I (tokenization, tagging, chunking) and Part II (grammars and parsing). NLTK has several new corpora including the Switchboard Telephone Speech Corpus transcript sample (Talkbank Project), CMU Problem Reports Corpus sample, CONLL2002 POS+NER data, Patient Information Leaflet corpus sample, Indian POS-Tagged data (Bangla, Hindi, Marathi, Telugu), Shakespeare XML corpus sample, and the Universal Declaration of Human Rights corpus with text samples in 300+ languages. 

NLTK features in Language Documentation and Conservation article : July 2007
    An article Managing Fieldwork Data with Toolbox and the Natural Language Toolkit by Stuart Robinson, Greg Aumann, and Steven Bird appears in the inaugural issue of ''Language Documentation and Conservation''. It discusses several small Python programs for manipulating field data. 

NLTK features in ACM Crossroads article : May 2007
    An article Getting Started on Natural Language Processing with Python by Nitin Madnani will appear in ''ACM Crossroads'', the ACM Student Journal. It discusses NLTK in detail, and provides several helpful examples including an entertaining free word association program. 

NLTK-Lite 0.7.5 released : May 2007
    This version contains improved interfaces for WordNet 3.0 and WordNet-Similarity, the Lancaster Stemmer (contributed by Steven Tomcavage), and several new corpora including the Switchboard Telephone Speech Corpus transcript sample (Talkbank Project), CMU Problem Reports Corpus sample, CONLL2002 POS+NER data, Patient Information Leaflet corpus sample and WordNet 3.0 data files. With this distribution WordNet no longer needs to be separately installed. 

NLTK-Lite 0.7.4 released : May 2007
    This release contains new corpora and corpus readers for Indian POS-Tagged data (Bangla, Hindi, Marathi, Telugu), and the Sinica Treebank, and substantial revision of Part II of the book on structured programming, grammars and parsing. 

NLTK-Lite 0.7.3 released : April 2007
    This release contains improved chunker and PCFG interfaces, the Shakespeare XML corpus sample and corpus reader, improved tutorials and improved formatting of code samples, and categorization of problem sets by difficulty. 

NLTK-Lite 0.7.2 released : March 2007
    This release contains new text classifiers (Cosine, NaiveBayes?, Spearman), contributed by Sam Huston, simple feature detectors, the UDHR corpus with text samples in 300+ languages and a corpus interface; improved tutorials (340 pages in total); additions to contrib area including Kimmo finite-state morphology system, Lambek calculus system, and a demonstration of text classifiers for language identification. 

NLTK-Lite 0.7.1 released : January 2007
    This release contains bugfixes in the WordNet? and HMM modules. 

2006
----

NLTK-Lite 0.7 released : December 2006
    This release contains: new semantic interpretation package (Ewan Klein), new support for SIL Toolbox format (Greg Aumann), new chunking package including cascaded chunking (Steven Bird), new interface to WordNet? 2.1 and Wordnet similarity measures (David Ormiston Smith), new support for Penn Treebank format (Yoav Goldberg), bringing the codebase to 48,000 lines; substantial new chapters on semantic interpretation and chunking, and substantial revisions to several other chapters, bringing the textbook documentation to 280 pages; 

NLTK-Lite 0.7b1 released : December 2006
    This release contains: new semantic interpretation package (Ewan Klein), new support for SIL Toolbox format (Greg Aumann), new chunking package including cascaded chunking, wordnet package updated for version 2.1 of Wordnet, and prototype wordnet similarity measures (David Ormiston Smith), bringing the codebase to 48,000 lines; substantial new chapters on semantic interpretation and chunking, and substantial revisions to several other chapters, bringing the textbook documentation to 270 pages; 

NLTK-Lite 0.6.6 released : October 2006
    This release contains bugfixes, improvements to Shoebox file format support, and expanded tutorial discussions of programming and feature-based grammars. 

NLTK-Lite 0.6.5 released : July 2006
    This release contains improvements to Shoebox file format support (by Stuart Robinson and Greg Aumann); an implementation of hole semantics (by Peter Wang); improvements to lambda calculus and semantic interpretation modules (by Ewan Klein); a new corpus (Sinica Treebank sample); and expanded tutorial discussions of trees, feature-based grammar, unification, PCFGs, and more exercises. 

NLTK-Lite passes 10k download milestone : May 2006
    We have now had 10,000 downloads of NLTK-Lite in the nine months since it was first released. 

NLTK-Lite 0.6.4 released : April 2006
    This release contains new corpora (Senseval 2, TIMIT sample), a clusterer, cascaded chunker, and several substantially revised tutorials. 

2005
----

NLTK 1.4 no longer supported : December 2005
    The main development has switched to NLTK-Lite. The latest version of NLTK can still be downloaded; see the installation page for instructions. 

NLTK-Lite 0.6 released : November 2005
    contains bug-fixes, PDF versions of tutorials, expanded fieldwork tutorial, PCFG grammar induction (by Nathan Bodenstab), and prototype concordance and paradigm display tools (by Peter Spiller and Will Hardy). 

NLTK-Lite 0.5 released : September 2005
    contains bug-fixes, improved tutorials, more project suggestions, and a pronunciation dictionary. 

NLTK-Lite 0.4 released : September 2005
    contains bug-fixes, improved tutorials, more project suggestions, and probabilistic parsers. 

NLTK-Lite 0.3 released : August 2005
    contains bug-fixes, documentation clean-up, project suggestions, and the chart parser demos including one for Earley parsing by Jean Mark Gawron. 

NLTK-Lite 0.2 released : July 2005
    contains bug-fixes, documentation clean-up, and some translations of tutorials into Brazilian Portuguese by Tiago Tresoldi. 

NLTK-Lite 0.1 released : July 2005
    substantially simplified and streamlined version of NLTK has been released 

Brazilian Portuguese Translation : April 2005
    top-level pages of this website have been translated into Brazilian Portuguese by Tiago Tresoldi; translations of the tutorials are in preparation http://hermes.sourceforge.net/nltk-br/ 

1.4.3 Release : February 2005
    NLTK 1.4.3 has been released; this is the first version which is compatible with Python 2.4. 
