# coding=utf-8
import re
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader import PlaintextCorpusReader

#===============================================================================================

class SpanishPlaintextCorpusReader(PlaintextCorpusReader):
    
    """Plaintext Corpus reader customized for Spanish books digitized in the Project Gutenberg
    archive. Arguments are a root directory and a fileid. It is enhanced with a colection of 
    Spanish abbreviated words, special punctuation marks and non-ascii characters commonly written 
    in Spanish (e.g. ¿, ñ), and the conventions for writing numerals (e.g. commas for decimals, 
    periods for thousands). It recognizes a sequence of two dashes (--) as an m-dash, and a 
    sequence of three dots as a single token."""

    def __init__(self, *args, **kwargs):
        PlaintextCorpusReader.__init__(self, *args, **kwargs)
    
#===============================================================================================

#String variables used in regular expression matches within the block readers.
        
#Numerals follow the Spanish convention of separating decimals with commas and thousands with
#periods. A numeral is a sequence of at least one digit, possibly with periods in between, possibly
#with a $ sign at the beginning, which may end in a series of digits preceded by a comma. Note that
#a numeral never ends in a period (a digit will be split from a sentence-final period).
        
    numerals = u'\$*[\d\.]+,\d+|\$*[\d\.]*\d'

#Abbreviations are shortened words that end in a period. This includes any single character that is
#not a diacritic or a punctuation mark, and is followed by a period. Ellipses "..." are
#treated as an abbreviation. I have compiled a list of abbreviations found in the novels of the
#corpus of late 19th century Spanish literature, including common ones (Sres.), less common ones
#(Excsmo.), and older variants of some (Vd.). Some technical abbreviations, found in non-fiction
#and scientific texts, are also included.
    
    abbreviations = (u'\.\.\.|[^—✚§/#´<>+’=:$,“”»«";¿?¡!_\s.()\[\]{}*^-]\.|Arqueol\.|&c\.|Mme\.'
                     u'|Lib\.|Lic\.|Antrop\.|núm\.|Dres\.|Descrip\.|—tom\.|rs\.|lám\.|Sec\.|Liv\.'
                     u'|Introd\.|Excmo\.|Caps\.|Amer\.|oct\.|Antigs\.|Ses\.|Moderns\.|Moralíz\.'
                     u'|Esp\.|Lam\.|act\.|Europ\.|Geog\.|CC\.|Eneid\.|Nat\.|M\.|Crón\.|Ntra\.|men\.'
                     u'|Láms\.|Orth\.|Gam\.|tam\.|Arg\.|Op\.|caps\.|Agust\.|fol\.|Sr\.|Tam\.|Janr\.'
                     u'|MS\.|Bol\.|Mr\.|S.A.S\.|Núms\.|Civiliz\.|Figs\.|DR\.|Orígs\.|Vocabuls\.'
                     u'|cits\.|L.E\.|Dicc\.|paj\.|Amér\.|Lám\.|ESQ\.|op\.|Argent\.|NE\.|Sres\.'
                     u'|Esp\.|Lam\.|Exmo\.|Espagn\.|pag\.|Conq\.|Cont\.|Sr\.|SR\.|SO\.|Ind\.|ded\.'
                     u'|cuads\.|Oct\.|Psch\.|Ed\.|Sta\.|Fot\.|sec\.|Part\.|JUV\.|Arqueolog\.|Sto\.'
                     u'|pp\.|Antig\.|vol.Cod\.|Srta\.|Col\.|lib\.|Congr\.|lin\.|Colec\.|Instit\.'
                     u'|Cong\.|Cient\.|Mlle\.|Rev\.|LLOR\.|nat\.|gr\.|ROB\.|Ge\.|Ord\.|lec\.|FR\.'
                     u'|Fr\.|ILMO\.|Colecc\.|Pág\.|Tuc\.|Prov\.|EXCMO\.|Págs\.|p.m\.|sc\.|capits\.'
                     u'|Pl\.|PP\.|lug\.|Sra\.|a.m\.|Antich\.|Gen\.|Apénd\.|Cap\.|Bs\.|pags\.|MSS\.'
                     u'|cap\.|Vds\.|nos\.|tom\.|Lug\.|Dr\.|págs\.|id\.|pág\.|verb\.|Or\.|sigtes\.'
                     u'|SEB\.|Hist\.|Vd\.|ci\.|vol\.|cit\.|etc\.|Cía\.|Id\.|Nos\.|Ibid\.|LLO\.|Ud\.'
                     u'|Fig\.|Geográf\.|Internat\.|Sant\.|ps\.|part\.|Luxemburg\.')

#The punctuation and alphanumeric character sets are almost complementary. Punctuation includes
#the double dash "--" used in Project Gutenberg as an m-dash, and common Spanish marks like the
#opening question and exclamation marks. Underscores are used in PG to indicate emphasis, so they
#need to be treated as punctuation. Quotation marks before or after "whitespace" are considered a
#single mark with whitespace (necessary to aid in correct sentence splitting later on).
    
    punctuation = u'--|\s"|"\s|[—✚§/#´<>+’=:$,“”»«";¿?¡!_.()\[\]{}*^-]'
    alphanum = u'[^—✚§/#´<>+’=:$,“”»«";¿?¡!_\s.()\[\]{}*^-]'
    
#===============================================================================================

#The heart of the corpus reader is the block reader. I define two block readers that read
#one paragraph at a time. Paragraphs are separated by blank lines in PG texts.
#The par_word_reader uses regular expression matching to tokenize a paragraph into words. The
#par_sent_reader takes the output of that process and finds the sentence boundaries based
#on punctuation patterns. Doing tokenization before splitting is necessary to avoid pitfalls
#caused by abbreviations, numerals, etc.

#Block reader that reads an entire paragraph and returns a list of tokens separated by
#whitespace or newline.

    def par_word_reader(self, stream):
        paragraph = ''
        for line in stream:
            if re.match('^\n', line):          #stop at a blank line
                break
            else:
                paragraph = paragraph + line   #until then, keep fetching lines from file
                
    # Tokenize paragraph into words and return word list. Uses regular expression matching. A
    # token is a string of characters that matches a numeral expression, an abbreviation, a
    # punctuation mark, or a sequence of one or more alphanumeric characters.
    
        par_words = re.findall(u'{:s}|{:s}|{:s}|{:s}+'.format(self.numerals, self.abbreviations, 
                                self.punctuation, self.alphanum), paragraph, flags=re.U)
        return par_words
    
#===============================================================================================

#Block reader that reads an entire paragraph and returns a list of sentences.
#A sentence is a list of tokens separated by whitespace or newline. Sentences are separated
#by [.?!], or by the former followed by closing quotation marks `" ` (straight quotation marks 
#followed by whitespace).

#NOTE: hyphenated words are split, fix it in next version.

    def par_sent_reader(self, stream):
        paragraph = ''
        for line in stream:
            if re.match('^\n', line):          #stop at a blank line
                break
            else:
                paragraph = paragraph + line   #until then, keep fetching lines from file
                
    # Tokenize paragraph into words
    
        par_words = re.findall(u'{:s}|{:s}|{:s}|{:s}+'.format(self.numerals, self.abbreviations, 
                                self.punctuation, self.alphanum), paragraph, flags=re.U)        
        
    # Start grouping words into sentences, paying attention to tokens corresponding to punctuation
    # marks and the punctuation conventions of Spanish.
    
        sentence = []
        sentences = []
        eos_flag = False
        for i, wrd in enumerate(par_words):
            if eos_flag !=False:                # Define special behaviors after [.?!]
                if wrd in [u'»', u'”', u'" ', u'"/n']: # a [.?!] followed by » starts another sentence after »
                    sentence.append(wrd)
                    sentences.append(sentence)
                    sentence = []
                    eos_flag = False
                elif wrd in [u'.', u'?', u'!']: # Multiple [.?!] at eos are kept within same sentence
                    sentence.append(wrd)
                    eos_flag = True
                elif wrd in [u',', u';']:       # [?!] followed by [,;] do not start a new sentence 
                    sentence.append(wrd)
                    eos_flag = False
                else:
                    sentences.append(sentence)
                    sentence = []
                    sentence.append(wrd)
                    eos_flag = False
            else:        
                sentence.append(wrd)

        #Once the last word in the paragraph is reached, split a sentence regardless of the final
        #word.
        
                if i == len(par_words)-1:
                    sentences.append(sentence)
                
        #Signal to break sentences at [.?!]. If the eos mark is followed by another
        #token from (», ..., ?, !, ;, ,,), then special behavior is required. The eos_flag = Bool
        #will be checked at the beginning of the loop to see if special behavior is triggered.
        
                elif wrd in [u'.', u'?', u'!']:
                    eos_flag = True

        return(sentences)

#===============================================================================================

#Block reader that reads an entire paragraph and returns a paragraph.
#A paragraph is a list of tokenized sentences.

#NOTE: hyphenated words are split, fix it in next version.

    def par_para_reader(self, stream):
        paragraph = ''
        for line in stream:
            if re.match('^\n', line):          #stop at a blank line
                break
            else:
                paragraph = paragraph + line   #until then, keep fetching lines from file
                
    # Tokenize paragraph into words
    
        par_words = re.findall(u'{:s}|{:s}|{:s}|{:s}+'.format(self.numerals, self.abbreviations, 
                                self.punctuation, self.alphanum), paragraph, flags=re.U)        
        
    # Start grouping words into sentences, paying attention to tokens corresponding to punctuation
    # marks and the punctuation conventions of Spanish.
    
        sentence = []
        sentences = []
        eos_flag = False
        for i, wrd in enumerate(par_words):
            if eos_flag !=False:                # Define special behaviors after [.?!]
                if wrd in [u'»', u'”', u'" ', u'"/n']: # a [.?!] followed by » starts another sentence after »
                    sentence.append(wrd)
                    sentences.append(sentence)
                    sentence = []
                    eos_flag = False
                elif wrd in [u'.', u'?', u'!']: # Multiple [.?!] at eos are kept within same sentence
                    sentence.append(wrd)
                    eos_flag = True
                elif wrd in [u',', u';']:       # [?!] followed by [,;] do not start a new sentence 
                    sentence.append(wrd)
                    eos_flag = False
                else:
                    sentences.append(sentence)
                    sentence = []
                    sentence.append(wrd)
                    eos_flag = False
            else:        
                sentence.append(wrd)

        #Once the last word in the paragraph is reached, split a sentence regardless of the final
        #word.
        
                if i == len(par_words)-1:
                    sentences.append(sentence)
                
        #Signal to break sentences at [.?!]. If the eos mark is followed by another
        #token from (», ..., ?, !, ;, ,,), then special behavior is required. The eos_flag = Bool
        #will be checked at the beginning of the loop to see if special behavior is triggered.
        
                elif wrd in [u'.', u'?', u'!']:
                    eos_flag = True

        # We already have a list of tokenized sentences. A paragraph is a list that contains that
        # list of sentences as its only element.
        
        return([sentences])
    
#===============================================================================================

#Using the block readers defined in the previous sections, I define the usual methos to read
#the corpus into words or sentences. The `raw()` method is inherited from the parent class.
    
    #Methods for reading words, sentences, and paragraphs
    
    def words(self, fileids=None):
        return concat([StreamBackedCorpusView(fileid, block_reader=self.par_word_reader)
                        for fileid in self.abspaths(fileids)])
    
    def sents(self, fileids=None):
        return concat([StreamBackedCorpusView(fileid, block_reader=self.par_sent_reader)
                        for fileid in self.abspaths(fileids)])

    def paras(self, fileids=None):
        return concat([StreamBackedCorpusView(fileid, block_reader=self.par_para_reader)
                        for fileid in self.abspaths(fileids)])
