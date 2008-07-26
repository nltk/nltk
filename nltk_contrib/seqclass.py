from nltk.classify import iis
import yaml
import os

class SequentialClassifier(object):
    def __init__(self, left=2, right=0):
    #left = look back
    #right = look forward
        self._model = []
        self._left = left
        self._right = right
        self._leftcontext = [None] * (left)
        self._history = self._leftcontext
        self._rightcontext = [None] * (right)

    def size(self):
        return len(self._model)
    

    def classify(self, featuresets):
        if self.size() == 0:
            raise ValueError, 'Tagger is not trained'
        
        for i, featureset in enumerate(featuresets):

            #if i >= self._left:
                #self._leftcontext = sequence[i-self._left : i]
            #else:
                #self._leftcontext = sequence[:i]

                
            self._rightcontext = sequence[i+1 : i+1+self._right]
            
            label = self.classify_one(featureset)
            featureset['label'] = label
            
            del self._leftcontext[0]
            self._leftcontext.append(featureset)

            yield label

                
    def classify_one(self, featureset):
        """
        Classify a single featureset.
        """
        return self._model([featureset][0])

    def contexts(self, sequence):
        """
        Build a generator of triples (left context, item, right context).
    
        @param sequence: Input sequence
        @type sequence: C{list}
        @rtype: C{generator} of triples (left_context, token, right_contex)
                """
            
        for i in range(len(sequence)):
                if i >= self._left:
                        left_context = sequence[i - self._left:i]
                else:
                        left_context = sequence[:i]
        
                right_context = sequence[i+1 : i+1+self._right]
    
                yield (left_context, sequence[i], right_context)  
                    
                    
    def detect_features(self, context):
        from string import join

        left_context, item, right_context = context
        features = {}
        token = item['token']
        
        features['cur_token(%s)' % token] = True
        features['is_title'] = token.istitle()
        features['is_digit'] = token.isdigit()
        features['is_upper'] = token.isupper()
        features['POS(%s)' % item['POS']] = True
        
        if left_context == []:
            features['initword'] = True
        else:
            left_labels = join([item['label'] for item in left_context], '_')
            features['left_labels(%s)' % left_labels] = True
            
        return features
    
    def save_features(self, training_data, filename):
         
        stream = open(filename,'w')
        yaml.dump_all(training_data, stream)
        print "Saving features to %s" % os.path.abspath(filename)        
        stream.close()

    
    def corpus2training_data(self, training_corpus, model_name='default', save=False):
        
        dict_corpus = tabular2dict(training_corpus, KEYS)
        contexts = self.contexts(dict_corpus)
        
        print "Detecting features"
        training_data = [(self.detect_features(c), c[1]['label']) for c in contexts]
        
        if save:
            feature_file = model_name + '.yaml'
            self.save_features(training_data, feature_file)
            
        else:
            return training_data
        
        
        
        
    def train(self, training_corpus, classifier=iis):
        """
        Train a classifier.
        """
        if self.size() != 0:
            raise ValueError, 'Classifier is already trained'
        
        training_data = self.corpus2training_data(training_corpus)
        
        print "Training classifier"
        self._model = iis(training_data)
            
            



def tabular2dict(tabular, keys):
    """
    Utility function to turn tabular format CONLL data into a
    sequence of dictionaries.
    @param tabular: tabular input
    @param keys: a dictionary that maps field positions into feature names
    @rtype: C{list} of featuresets
    """
    tokendicts = []
    lines = tabular.splitlines()
    for line in lines:
        line = line.strip()
        line = line.split()
        if line:
            tokendict = {}
            for i in range(len(line)):
                key = keys[i]
                tokendict [key] = line[i]
            tokendicts.append(tokendict )
    return tokendicts

KEYS = {0: 'token', 1: 'POS', 2: 'label'}



def demo():
    
    tabtrain = \
        """Het Art O
        Hof N B-ORG
        van Prep I-ORG
        Cassatie N I-ORG
        verbrak V O
        het Art O
        arrest N O
        """
    
    tabtest = \
        """Het Art 
        Hof N 
        van Prep 
        Cassatie N 
        verbrak V
        het Art
        arrest N
        """
    
    test = tabular2dict(tabtest, KEYS)
    train = tabular2dict(tabtrain, KEYS)

    sc = SequentialClassifier(2, 0)
    
    sc.train(tabtrain)
    sc.classify(tabtest)




demo()
