import math
from nltk import PropertyIndirectionMixIn
from nltk.token import Token
from nltk.tokenizer import *
from nltk.feature import *

######################################################################
## Feature Detector
######################################################################
class DocumentFeatureDetector(AbstractFeatureDetector):
    """
    This feature detector inherits from nltk.feature.AbstractFeatureDetector,
    and does the job for extracting features (i.e. words) from a document.
    When a text token is passed as argument, it gets tokenized and stemmed,
    and the results are stored as bag-of-words.

    Example:
        detector = DocumentFeatureDetector(RegexpTokenizer(r'\w+'),
                                           PorterStemmer())
        t = Token(TEXT='This is a book.')
        detector.detect_features(t)
        print t['FEATURES']['BOW']

    As above, t would have a property FEATURES which is a dictionary with only
    one key BOW which maps to a list.
    """
    def __init__(self, tokenizer=WhitespaceTokenizer(), stemmer=None,
                 **property_names):
        """
        Constructs the feature detector. The tokenizer and the stemmer are
        passed in as arguments, so that caller can decide on tokenizing and
        stemming schemes.

        @param tokenizer: an object of type nltk.tokenizer.TokenizerI which
            does the job of tokenizing the text. Default is WhitespaceTokenizer
        @param stemmer: an object of type nltk.stemmer.StemmerI which does
            the job of stemming each subtoken. Default is None.
        """
        AbstractFeatureDetector.__init__(self, **property_names)
        self._tokenizer = tokenizer
        self._stemmer = stemmer
        
    def get_features(self, token):
        """
        Parse the text token, tokenize the text, stem each subtoken (if there's
        a stemmer), and append it to the bag of words.

        @param token: an object of type nltk.token.Token with the TEXT property
        @rtype: dict('BOW': list of string)
        @return: the stemmed tokens packed in a list in a dictionary
        """
        self._tokenizer.tokenize(token)
        bag_of_words = []
        for tok in token['SUBTOKENS']:
            t = tok['TEXT'].lower()
            if self._stemmer == None:
                bag_of_words.append(t)
            else:
                bag_of_words.append(self._stemmer.raw_stem(t))
            
        return {'BOW': bag_of_words}
    
    def features(self):
        return ['BOW']

######################################################################
## Feature Encoder
######################################################################
class TFIDFFeatureEncoder(BagValuedFeatureEncoder):
    """
    This feature encoder inherits from nltk.feature.BagValuedFeatureEncoder,
    which encodes a token with its features (i.e., bag-of-words) into a feature
    vector (represented using nltk.util.SparseList).
    However, unlike BagValuedFeatureEncoder which only counts term frequency,
    the encoding scheme follows the TF-IDF scheme. Each dimension from vector
    represents both the term frequency and inverted document frequency.

    Possible term-frequency scheme includes (t means term, d means document):
        nat (Natural)   -- tf(t, d)
        log (Logarithm) -- 1 + log(tf(t, d))
        aug (Augmented) -- 0.5 + 0.5 * tf(t, d) / max_t(tf(t, d))
    and possible inverted-document-frequency schemes includes:
        nat (Natural)   -- 1 / df(t)
        log (Logarithm) -- log(N / df(t))       (N is the number of documents)

    You can choose any combination of schemes upon initialization. Default
    schemes are natural scheme for both.

    Tokens need to have a FEATURE property which is a dictionary, and has an
    entry { 'BOW' : [word_list] }. It is strongly recommend to use
    DocumentFeatureDetector in this module to detect features from a token with
    TEXT property. After encoding, the token would have a FEATURE_VECTOR
    property which is a SpareList. The vector is normalized (i.e., the length
    of the vector is 1) in advance.

    Example:
        detector = DocumentFeatureDetector(RegexpTokenizer(r'\w+'),
                                           PorterStemmer())
        t = Token(TEXT='This is a book.')
        detector.detect_features(t)
        encoder = TFIDFFeatureEncoder([t])
        encoder.encode_features(t)
        print t['FEATURE_VECTOR']
    
    """
    def __init__(self, token_list, term_scheme='nat', doc_scheme='nat',
                 **property_names):
        """
        Constructs the feature encoder. The term frequency and inverted
        document frequency schemes can be given explicitly or use default.
        All subtokens in token_list would map to a dimension in the vector
        space.

        @param token_list: a list of nltk.token.Token objects with the FEATURES property
            which is a dictionary with one entry: 'BOW' maps to a string list.
        @param term_scheme: a string of 'nat', 'log' or 'aug'. Default is 'nat'
        @param doc_scheme: a string of 'nat' or 'log'. Default is 'nat'.
        """
        self._term_scheme = term_scheme
        self._doc_scheme = doc_scheme
        self._n = len(token_list)       # number of documents
        all_words = Set()               # all words in the documents, this is
                                        # used to build the word-index mapping
        self._document_freq = dict()    # document frequency: word map to int
        for tok in token_list:
            features = tok['FEATURES']['BOW']
            local_words = Set()         # use set so that each word in a single
                                        # document only counts once
            for w in features:
                local_words.add(w)
            all_words.union_update(local_words)
            for w in local_words:
                self._document_freq[w] = self._document_freq.get(w, 0) + 1

        # At the end, call BagValuedFeatureEncoder to get word-index mapping
        BagValuedFeatureEncoder.__init__(self, 'BOW', list(all_words),
                                         **property_names)

    def raw_encode_features(self, features):
        """
        This method encode the features (a list of subtokens) into the vector.
        First we use BagValuedFeatureEncoder to get the term frequency, and then
        modify the values depending on the schemes given.
        If one of the features (words) was not seen before by this encoder
        (i.e., not in the training list), that feature would be neglected.
        Other classes should not call this method directly; instead,
        encode_features() is preferred.

        @param features: a list of strings
        @rtype: nltk.util.SparseList
        @return: the feature vector in the form of SparseList
        """
        # first get term frequency from BagValuedFeatureEncoder
        fv = BagValuedFeatureEncoder.raw_encode_features(self, features)

        # fv[0] contains frequency for unseen word, we neglect this term because
        # we don't want this term to play a role at vector distance counting
        fv[0] = 0

        # find max term freq in augmented scheme 
        if self._term_scheme == 'aug':
            max_t = max([v for (_, v) in fv.assignments()])

        # modify the sparse list
        for (i, v) in fv.assignments():
            # get term-frequency
            if self._term_scheme == 'nat':      # natural
                tf = float(v)
            elif self._term_scheme == 'log':    # logarithm
                tf = 1.0 + math.log(float(v))
            elif self._term_scheme == 'aug':    # augmented
                tf = 0.5 + 0.5 * float(v) / float(max_t)
            # get document-frequency
            if self._doc_scheme == 'nat':       # natural
                idf = 1.0 / float(self._document_freq[self._index_to_val[i]])
            elif self._doc_scheme == 'log':     # logarithm
                idf = math.log(self._n) \
                    - math.log(float(self._document_freq[self._index_to_val[i]]))
            # vector is tf-idf
            fv[i] = tf * idf

        # normalize the vector by dividing each term with vector length
        length = math.sqrt(sum([v for (_, v) in fv.assignments()]))
        for (i, v) in fv.assignments():
            fv[i] = v / length;

        return fv
