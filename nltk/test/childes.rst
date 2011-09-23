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
    Version :  1.5.6
    Date :  1986-03-04
    Corpus :  valian
    Id :  01a

Printing information of participants of the corpus. The most common codes for 
the participants are 'CHI' (target child), 'MOT' (mother), and 'INV' (investigator).

    >>> corpus_participants = valian.participants(valian.fileids())
    >>> for this_corpus_participants in corpus_participants[:2]:
    ...     for key in this_corpus_participants.keys():
    ...        print key, ": ", this_corpus_participants[key] # doctest: +ELLIPSIS
    CHI :  defaultdict(<function dictOfDicts at 0x1021677d0>, {'group': 'normal', 'language': 'eng', 'age': 'P2Y1M3D', 'sex': 'female', 'role': 'Target_Child', 'id': 'CHI'})
    INV :  defaultdict(<function dictOfDicts at 0x1021677d0>, {'role': 'Investigator', 'id': 'INV', 'language': 'eng'})
    MOT :  defaultdict(<function dictOfDicts at 0x1021677d0>, {'role': 'Mother', 'id': 'MOT', 'language': 'eng'})
    CHI :  defaultdict(<function dictOfDicts at 0x1021241b8>, {'group': 'normal', 'language': 'eng', 'age': 'P2Y1M12D', 'sex': 'female', 'role': 'Target_Child', 'id': 'CHI'})
    INV :  defaultdict(<function dictOfDicts at 0x1021241b8>, {'role': 'Investigator', 'id': 'INV', 'language': 'eng'})
    MOT :  defaultdict(<function dictOfDicts at 0x1021241b8>, {'role': 'Mother', 'id': 'MOT', 'language': 'eng'})

printing words.

    >>> valian.words('Valian/01a.xml') # doctest: +ELLIPSIS
    ['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', ...

printing sentences.

    >>> valian.sents('Valian/01a.xml') # doctest: +ELLIPSIS
    [['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', 'and', 'it', 'is', 'March', 'fourth', 'I', 'believe', 'and', 'when', 'was', "Parent's", 'birthday'], ["Child's"], ['oh', "I'm", 'sorry'], ["that's", 'okay'], ...

You can specify the participants with the argument *speaker*.

    >>> valian.words('Valian/01a.xml',speaker=['INV']) # doctest: +ELLIPSIS
    ['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', ...
    >>> valian.words('Valian/01a.xml',speaker=['MOT']) # doctest: +ELLIPSIS
    ["Child's", "that's", 'okay', 'February', 'first', 'nineteen', ...
    >>> valian.words('Valian/01a.xml',speaker=['CHI']) # doctest: +ELLIPSIS
    ['tape', 'it', 'up', 'and', 'two', 'tape', 'players', 'have',...


tagged_words() and tagged_sents() return the usual (word,pos) tuple lists.
POS tags in the CHILDES are automatically assigned by MOR and POST programs
(MacWhinney, 2000).

    >>> valian.tagged_words('Valian/01a.xml')[:30] # doctest: +ELLIPSIS
    [('at', 'prep'), ('Parent', 'n'), ("Lastname's", 'n'), ('house', 'n'), ('with', 'prep'), ('Child', 'n'), ('Lastname', 'n'), ('and', 'conj'), ('it', 'pro'), ('is', 'v'), ('March', 'n'), ('fourth', 'adj'), ('I', 'pro'), ('believe', 'v'), ('and', 'conj'), ('when', 'adv'), ('was', 'v'), ("Parent's", 'n'), ('birthday', 'n'), ("Child's", 'n'), ('oh', 'co'), ("I'm", 'pro'), ('sorry', 'adj'), ("that's", 'pro'), ('okay', 'adj'), ('February', 'n'), ('first', 'adj'), ('nineteen', 'det'), ('eighty', 'det'), ('four', 'det')]

    >>> valian.tagged_sents('Valian/01a.xml')[:10] # doctest: +ELLIPSIS
    [[('at', 'prep'), ('Parent', 'n'), ("Lastname's", 'n'), ('house', 'n'), ('with', 'prep'), ('Child', 'n'), ('Lastname', 'n'), ('and', 'conj'), ('it', 'pro'), ('is', 'v'), ('March', 'n'), ('fourth', 'adj'), ('I', 'pro'), ('believe', 'v'), ('and', 'conj'), ('when', 'adv'), ('was', 'v'), ("Parent's", 'n'), ('birthday', 'n')], [("Child's", 'n')], [('oh', 'co'), ("I'm", 'pro'), ('sorry', 'adj')], [("that's", 'pro'), ('okay', 'adj')], [('February', 'n'), ('first', 'adj'), ('nineteen', 'det'), ('eighty', 'det'), ('four', 'det')], [('great', 'adj')], [('and', 'conj'), ("she's", 'pro'), ('two', 'det'), ('years', 'n'), ('old', 'adj')], [('correct', 'adj')], [('okay', 'co')], [('she', 'pro'), ('just', 'adv'), ('turned', 'part'), ('two', 'det'), ('a', 'det'), ('month', 'n'), ('ago', 'adv')]]

When the argument *stem* is true, the word stems (e.g., 'is' -> 'be-3PS') are
used instread of the original words.

    >>> valian.words('Valian/01a.xml')[:30] # doctest: +ELLIPSIS
    ['at', 'Parent', "Lastname's", 'house', 'with', 'Child', 'Lastname', 'and', 'it', 'is', ...
    >>> valian.words('Valian/01a.xml',stem=True)[:30] # doctest: +ELLIPSIS
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

    >>> valian.words('Valian/01a.xml',relation=True)[:10]  # doctest: +ELLIPSIS
    [[('at', 'prep', '1|9|COORD'), ('Parent', 'n', '2|5|NAME'), ('Lastname', 'n', '3|5|MOD'), ('s', 'poss', '4|5|MOD'), ('house', 'n', '5|1|POBJ'), ('with', 'prep', '6|9|COORD'), ('Child', 'n', '7|9|COORD'), ('Lastname', 'n', '8|9|COORD'), ('and', 'conj', '9|16|COORD'), ('it', 'pro', '10|11|SUBJ'), ('be-3S', 'v', '11|9|COORD'), ('March', 'n', '12|11|PRED'), ('fourth', 'adj', '13|16|COORD'), ('I', 'pro', '14|15|SUBJ'), ('believe', 'v', '15|16|COORD'), ('and', 'conj', '16|0|ROOT'), ('when', 'adv', '17|18|PRED'), ('be-PAST', 'v', '18|16|COORD'), ('Parent', 'n', '19|21|MOD'), ('s', 'poss', '20|21|MOD'), ('birthday', 'n', '21|18|SUBJ')], [('Child', 'n', '1|2|MOD'), ('s', 'poss', '2|0|ROOT')], [('oh', 'co', '1|3|COM'), ('I', 'pro', '2|3|SUBJ'), ('be', 'v', '3|0|ROOT'), ('sorry', 'adj', '4|3|PRED')], [('that', 'pro', '1|2|SUBJ'), ('be', 'v', '2|0|ROOT'), ('okay', 'adj', '3|2|PRED')], [('February', 'n', '1|5|VOC'), ('first', 'adj', '2|5|ENUM'), ('nineteen', 'det', '3|5|ENUM'), ('eighty', 'det', '4|5|ENUM'), ('four', 'det', '5|0|ROOT')], [('great', 'adj', '1|0|ROOT')], [('and', 'conj', '1|0|ROOT'), ('she', 'pro', '2|3|SUBJ'), ('be', 'v', '3|1|COORD'), ('two', 'det', '4|5|QUANT'), ('year-PL', 'n', '5|3|PRED'), ('old', 'adj', '6|3|PRED')], [('correct', 'adj', '1|0|ROOT')], [('okay', 'co', '1|0|ROOT')], [('she', 'pro', '1|3|SUBJ'), ('just', 'adv', '2|3|JCT'), ('turn-PERF', 'part', '3|0|ROOT'), ('two', 'det', '4|6|QUANT'), ('a', 'det', '5|6|DET'), ('month', 'n', '6|3|OBJ'), ('ago', 'adv', '7|3|JCT')]]

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
	[2.1545454545454548, 2.0403225806451615, 3.1714285714285713, 2.8190476190476192, 1.9606741573033708, 2.4303797468354431, 2.7692307692307692, 2.445086705202312, 3.8235294117647061, 2.8544600938967135, 2.7264150943396226, 3.1538461538461537, 3.751851851851852, 3.3680981595092025, 4.4093406593406597, 3.75, 4.3611111111111107, 4.4419889502762429, 3.1710526315789473, 3.5350000000000001, 3.9715909090909092, 5.0585365853658537, 5.0035087719298241, 4.5460992907801421, 5.5064935064935066, 4.6180904522613062, 3.9565217391304346, 4.659259259259259, 5.0108303249097474, 5.4645669291338583, 5.2642642642642645, 4.6881188118811883, 4.5390070921985819, 4.854166666666667, 4.8558139534883722, 5.6245487364620939, 5.427083333333333, 5.880281690140845, 4.6871508379888267, 6.5690789473684212, 6.3423423423423424, 6.6075949367088604, 4.0337078651685392]
    >>> valian.MLU('Valian/01a.xml')
    [2.1545454545454548]


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
