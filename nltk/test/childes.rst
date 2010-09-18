=======================
 CHILDES Corpus Readers
=======================

Read the XML version of the CHILDES corpus.

How to use CHILDESCorpusReader
==============================

Read the CHILDESCorpusReader class and read the CHILDES corpus saved in
the nltk_data directory.

    >>> import nltk
    >>> from nltk.corpus.reader import CHILDESCorpusReader
    >>> corpus_root = nltk.data.find('corpora/childes/data-xml/Eng-USA/')

Reading files in the Valian corpus (Valian, 1991).

    >>> valian = CHILDESCorpusReader(corpus_root, u'Valian/.*.xml')
    >>> valian.fileids() # doctest: +ELLIPSIS
    ['Valian/01a.xml', 'Valian/01b.xml', 'Valian/02a.xml', 'Valian/02b.xml',...

Count the number of files

    >>> len(valian.fileids())
    43

Printing properties of the corpus files.

    >>> corpus_data = valian.corpus(valian.fileids())
    >>> print corpus_data[0] # doctest: +ELLIPSIS
    {'Lang': 'eng', '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation':...
    >>> for key in corpus_data[0].keys():
    ...    print key, ": ", corpus_data[0][key] # doctest: +ELLIPSIS
    Lang :  eng
    {http://www.w3.org/2001/XMLSchema-instance}schemaLocation :  http://www.talkbank.org/ns/talkbank http://talkbank.org/software/talkbank.xsd
    Version :  1.6.1
    Date :  1986-03-04
    Corpus :  valian
    Id :  01a

Printing information of participants of the corpus. The most common codes for 
the participants are 'CHI' (target child), 'MOT' (mother), and 'INV' (investigator).

    >>> corpus_participants = valian.participants(valian.fileids())
    >>> for this_corpus_participants in corpus_participants[:2]:
    ...     for key in this_corpus_participants.keys():
    ...        print key, ": ", this_corpus_participants[key] # doctest: +ELLIPSIS
    CHI :  defaultdict(<function dictOfDicts at 0x102050c08>, ...
    INV :  defaultdict(<function dictOfDicts at 0x102050c08>, ...
    MOT :  defaultdict(<function dictOfDicts at 0x102050c08>, ...
    CHI :  defaultdict(<function dictOfDicts at 0x1020ff0c8>, ...
    INV :  defaultdict(<function dictOfDicts at 0x1020ff0c8>, ...
    MOT :  defaultdict(<function dictOfDicts at 0x1020ff0c8>, ...

printing words.

    >>> valian.words('Valian/01a.xml') # doctest: +ELLIPSIS
    ['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', ...

printing sentences.

    >>> valian.sents('Valian/01a.xml') # doctest: +ELLIPSIS
    [['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', 'and', 'it', 'is', 'March', 'fourth', 'I', 'believe', 'and', 'when', 'was', "Parent's", 'birthday'], ["Child's"], ['oh', "I'm", 'sorry'], ["that's", 'okay'], ...

You can specify the participants with the argument *speaker*.

    >>> valian.words('Valian/01a.xml',speaker='INV') # doctest: +ELLIPSIS
    ['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', ...
    >>> valian.words('Valian/01a.xml',speaker='MOT') # doctest: +ELLIPSIS
    ["Child's", "that's", 'okay', 'February', 'first', 'nineteen', ...
    >>> valian.words('Valian/01a.xml',speaker='CHI') # doctest: +ELLIPSIS
    ['tape', 'it', 'up', 'and', 'two', 'tape', 'players', 'have',...


When the argument *pos* is true, the part-of-speech information is returned.
POS tags in the CHILDES are automatically assigned by MOR and POST programs
(MacWhinney, 2000).

    >>> valian.words('Valian/01a.xml', pos=True) # doctest: +ELLIPSIS
    ['at/prep', 'Parent/n', "Lastname's/n", 'house/n', 'with/prep', 'Child/n', ...

When the argument *stem* is true, the word stems (e.g., 'is' -> 'be-3PS') are
used instread of the original words.

    >>> valian.words('Valian/01a.xml') # doctest: +ELLIPSIS
    ['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', 'and', 'it', 'is', ...
    >>> valian.words('Valian/01a.xml',stem=True) # doctest: +ELLIPSIS
    ['at', 'Parent', 'Lastname', 's', 'house', 'with', 'Child', 'Lastname', 'and', 'it', 'be-3S', ...

When the argument *replace* is true, the replaced words are used instread of
the original words.

    >>> valian.words('Valian/01a.xml',speaker='CHI')[247]
    'tikteat'
    >>> valian.words('Valian/01a.xml',speaker='CHI',replace=True)[247]
    'trick'

When the argument *relation* is true, the relational relationships in the 
sentence are returned. See Sagae et al. (2010) for details of the relational
structure adopted in the CHILDES.

    >>> valian.words('Valian/01a.xml',relation=True)  # doctest: +ELLIPSIS
    [[('at', '1|9|COORD'), ('Parent', '2|5|NAME'), ('Lastname', '3|5|MOD'), ('s', '4|5|MOD'), ('house', '5|1|POBJ'), ('with', '6|9|COORD'), ('Child', '7|9|COORD'), ('Lastname', '8|9|COORD'), ('and', '9|16|COORD'), ('it', '10|11|SUBJ'), ('be-3S', '11|9|COORD'), ('March', '12|11|PRED'), ('fourth', '13|16|COORD'), ('I', '14|15|SUBJ'), ('believe', '15|16|COORD'), ('and', '16|0|ROOT'), ('when', '17|18|PRED'), ('be-PAST', '18|16|COORD'), ('Parent', '19|21|MOD'), ('s', '20|21|MOD'), ('birthday', '21|18|SUBJ')], ...

Printing age. When the argument *month* is true, the age information in
the CHILDES format is converted into the number of months.

    >>> valian.age() # doctest: +ELLIPSIS
    ['P2Y1M3D', 'P2Y1M12D', 'P1Y9M21D', 'P1Y9M28D', 'P2Y1M23D', ...
    >>> valian.age('Valian/01a.xml')
    ['P2Y1M3D']
    >>> valian.age('Valian/01a.xml',month=True)
    [25]
    
Printing MLU. The criteria for the MLU computation is broadly based on 
Brown (1973).

    >>> valian.MLU() # doctest: +ELLIPSIS
    [1.8798283261802575, 1.9375, 2.6983240223463687, 2.3945945945945946, ...
    >>> valian.MLU('Valian/01a.xml')
    [1.8798283261802575]


Basic stuff
==============================

Count the number of words and sentences of each file.

    >>> valian = CHILDESCorpusReader(corpus_root, u'Valian/.*.xml')
    >>> for this_file in valian.fileids()[:6]:
    ...     print valian.corpus(this_file)[0]['Corpus'], valian.corpus(this_file)[0]['Id']
    ...     print "num of words: %i" % len(valian.words(this_file))
    ...     print "num of sents: %i" % len(valian.sents(this_file))
    valian 01a
    num of words: 3609
    num of sents: 1027
    valian 01b
    num of words: 4381
    num of sents: 1275
    valian 02a
    num of words: 2675
    num of sents: 801
    valian 02b
    num of words: 5026
    num of sents: 1584
    valian 03a
    num of words: 2748
    num of sents: 988
    valian 03b
    num of words: 4421
    num of sents: 1397
