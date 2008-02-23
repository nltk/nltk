# Natural Language Toolkit: Interface to Weka Classsifiers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: naivebayes.py 2063 2004-07-17 21:02:24Z edloper $

import time, tempfile, os, os.path, subprocess, re
from api import *
from nltk.probability import *
from nltk.internals import java, config_java

"""
Classifiers that make use of the external 'Weka' package.
"""

_weka_classpath = None
_weka_search = ['.',
                '/usr/share/weka',
                '/usr/local/share/weka',
                '/usr/lib/weka',
                '/usr/local/lib/weka',]
def config_weka(classpath=None):
    global _weka_classpath

    # Make sure java's configured first.
    config_java()
    
    if classpath is not None:
        _weka_classpath = classpath

    if _weka_classpath is None:
        searchpath = _weka_search
        if 'WEKAHOME' in os.environ:
            searchpath.insert(0, os.environ['WEKAHOME'])
        
        for path in searchpath:
            if os.path.exists(os.path.join(path, 'weka.jar')):
                _weka_classpath = os.path.join(path, 'weka.jar')
                print '[Found Weka: %s]' % _weka_classpath

    if _weka_classpath is None:
        raise LookupError('Unable to find weka.jar!  Use config_weka() '
                          'or set the WEKAHOME environment variable. '
                          'For more information about Weka, please see '
                          'http://www.cs.waikato.ac.nz/ml/weka/')

class WekaClassifier(ClassifierI):
    def __init__(self, formatter, model_filename):
        self._formatter = formatter
        self._model = model_filename

    def batch_prob_classify(self, featuresets):
        return self._batch_classify(featuresets, ['-p', '0', '-distribution'])
        
    def batch_classify(self, featuresets):
        return self._batch_classify(featuresets, ['-p', '0'])
        
    def _batch_classify(self, featuresets, options):
        # Make sure we can find java & weka.
        config_weka()
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Write the test data file.
            test_filename = os.path.join(temp_dir, 'test.arff')
            self._formatter.write(test_filename, featuresets)
            
            # Call weka to classify the data.
            cmd = ['weka.classifiers.bayes.NaiveBayes', 
                   '-l', self._model, '-T', test_filename] + options
            (stdout, stderr) = java(cmd, classpath=_weka_classpath,
                                    stdout=subprocess.PIPE)

            # Parse weka's output.
            return self.parse_weka_output(stdout.split('\n'))

        finally:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    def parse_weka_distribution(self, s):
        probs = [float(v) for v in re.split('[*,]+', s) if v.strip()]
        probs = dict(zip(self._formatter.labels(), probs))
        return DictionaryProbDist(probs)

    def parse_weka_output(self, lines):
        if lines[0].split() == ['inst#', 'actual', 'predicted',
                                'error', 'prediction']:
            return [line.split()[2].split(':')[1]
                    for line in lines[1:] if line.strip()]
        elif lines[0].split() == ['inst#', 'actual', 'predicted',
                                'error', 'distribution']:
            return [self.parse_weka_distribution(line.split()[-1])
                    for line in lines[1:] if line.strip()]
            
        else:
            for line in lines[:10]: print line
            raise ValueError('Unhandled output format -- your version '
                             'of weka may not be supported.\n'
                             '  Header: %s' % lines[0])
                                
    @staticmethod
    def train(model_filename, featuresets, quiet=True):
        # Make sure we can find java & weka.
        config_weka()
        
        # Build an ARFF formatter.
        formatter = ARFF_Formatter.from_train(featuresets)
    
        temp_dir = tempfile.mkdtemp()
        try:
            # Write the training data file.
            train_filename = os.path.join(temp_dir, 'train.arff')
            formatter.write(train_filename, featuresets)
    
            # Train the weka model.
            cmd = ['weka.classifiers.bayes.NaiveBayes',
                   '-d', model_filename, '-t', train_filename]
            if quiet: stdout = subprocess.PIPE
            else: stdout = None
            java(cmd, classpath=_weka_classpath, stdout=stdout)

            # Return the new classifier.
            return WekaClassifier(formatter, model_filename)
        
        finally:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)


class ARFF_Formatter:
    """
    Converts featuresets and labeled featuresets to ARFF-formatted
    strings, appropriate for input into Weka.
    """
    def __init__(self, labels, features):
        """
        @param labels: A list of all labels that can be generated.
        @param features: A list of feature specifications, where
            each feature specification is a tuple (fname, ftype);
            and ftype is an ARFF type string such as NUMERIC or
            STRING.
        """
        self._labels = labels
        self._features = features

    def format(self, tokens):
        return self.header_section() + self.data_section(tokens)

    def labels(self):
        return list(self._labels)

    def write(self, filename, tokens):
        f = open(filename, 'w')
        f.write(self.format(tokens))
        f.close()

    @staticmethod
    def from_train(tokens):
        # Find the set of all attested labels.
        labels = set(label for (tok,label) in tokens)
    
        # Determine the types of all features.
        features = {}
        for tok, label in tokens:
            for (fname, fval) in tok.items():
                if issubclass(type(fval), bool):
                    ftype = '{True, False}'
                elif issubclass(type(fval), (int, float, long, bool)):
                    ftype = 'NUMERIC'
                elif issubclass(type(fval), basestring):
                    ftype = 'STRING'
                elif fval is None:
                    continue # can't tell the type.
                else:
                    raise ValueError('Unsupported value type %r' % ftype)
    
                if features.get(fname, ftype) != ftype:
                    raise ValueError('Inconsistent type for %s' % fname)
                features[fname] = ftype
        features = sorted(features.items())
    
        return ARFF_Formatter(labels, features)

    def header_section(self):
        # Header comment.
        s = ('% Weka ARFF file\n' +
             '% Generated automatically by NLTK\n' +
             '%% %s\n\n' % time.ctime())
    
        # Relation name
        s += '@RELATION rel\n\n'
    
        # Input attribute specifications
        for fname, ftype in self._features:
            s += '@ATTRIBUTE %-30r %s\n' % (fname, ftype)
    
        # Label attribute specification
        s += '@ATTRIBUTE %-30r {%s}\n' % ('-label-', ','.join(self._labels))

        return s

    def data_section(self, tokens, labeled=None):
        """
        @param labeled: Indicates whether the given tokens are labeled
            or not.  If C{None}, then the tokens will be assumed to be
            labeled if the first token's value is a tuple or list.
        """
        # Check if the tokens are labeled or unlabeled.  If unlabeled,
        # then use 'None' 
        if labeled is None:
            labeled = tokens and isinstance(tokens[0], (tuple, list))
        if not labeled:
            tokens = [(tok, None) for tok in tokens]
    
        # Data section
        s = '\n@DATA\n'
        for (tok, label) in tokens:
            for fname, ftype in self._features:
                s += '%s,' % self._fmt_arff_val(tok.get(fname))
            s += '%s\n' % self._fmt_arff_val(label)
    
        return s

    def _fmt_arff_val(self, fval):
        if fval is None:
            return '?'
        elif isinstance(fval, (bool, int, long)):
            return '%s' % fval
        elif isinstance(fval, float):
            return '%r' % fval
        else:
            return '%r' % fval

if __name__ == '__main__':
    from nltk.classify.util import names_demo,binary_names_demo_features
    def make_classifier(featuresets):
        return WekaClassifier.train('/tmp/name.model', featuresets)
    classifier = names_demo(make_classifier,binary_names_demo_features)
