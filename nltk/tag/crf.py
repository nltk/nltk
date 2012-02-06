# Natural Language Toolkit: Conditional Random Fields
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
An interface to Mallet <http://mallet.cs.umass.edu/>'s Linear Chain
Conditional Random Field (LC-CRF) implementation.

A user-supplied feature detector function is used to convert each
token to a featureset.  Each feature/value pair is then encoded as a
single binary feature for Mallet.
"""

from tempfile import mkstemp
import textwrap
import re
import time
import subprocess
import sys
import zipfile
import pickle
from xml.etree import ElementTree

from nltk.classify import call_mallet

from nltk.tag.api import FeaturesetTaggerI

class MalletCRF(FeaturesetTaggerI):
    """
    A conditional random field tagger, which is trained and run by
    making external calls to Mallet.  Tokens are converted to
    featuresets using a feature detector function::

        feature_detector(tokens, index) -> featureset

    These featuresets are then encoded into feature vectors by
    converting each feature (name, value) pair to a unique binary
    feature.

    Ecah MalletCRF object is backed by a crf model file.  This
    model file is actually a zip file, and it contains one file for
    the serialized model ``crf-model.ser`` and one file for
    information about the structure of the CRF ``crf-info.xml``.

    Create a new MalletCRF.

    :param filename: The filename of the model file that backs this CRF.
    :param feature_detector: The feature detector function that is
        used to convert tokens to featuresets.  This parameter
        only needs to be given if the model file does not contain
        a pickled pointer to the feature detector (e.g., if the
        feature detector was a lambda function).
    """

    def __init__(self, filename, feature_detector=None):
        # Read the CRFInfo from the model file.
        zf = zipfile.ZipFile(filename)
        crf_info = CRFInfo.fromstring(zf.read('crf-info.xml'))
        zf.close()

        self.crf_info = crf_info
        """A CRFInfo object describing this CRF."""

        # Ensure that our crf_info object has a feature detector.
        if crf_info.feature_detector is not None:
            if (feature_detector is not None and
                self.crf_info.feature_detector != feature_detector):
                raise ValueError('Feature detector mismatch: %r vs %r' %
                       (feature_detector, self.crf_info.feature_detector))
        elif feature_detector is None:
            raise ValueError('Feature detector not found; supply it manually.')
        elif feature_detector.__name__ != crf_info.feature_detector_name:
            raise ValueError('Feature detector name mismatch: %r vs %r' %
                             (feature_detector.__name__,
                              crf_info.feature_detector_name))
        else:
            self.crf_info.feature_detector = feature_detector

    #/////////////////////////////////////////////////////////////////
    # Convenience accessors (info also available via self.crf_info)
    #/////////////////////////////////////////////////////////////////

    @property
    def filename(self):
        """
        The filename of the crf model file that backs this
        MalletCRF.  The crf model file is actually a zip file, and
        it contains one file for the serialized model
        ``crf-model.ser`` and one file for information about the
        structure of the CRF ``crf-info.xml``).
        """
        return self.crf_info.model_filename

    @property
    def feature_detector(self):
        """
        The feature detector function that is used to convert tokens
        to featuresets.  This function has the signature::

        feature_detector(tokens, index) -> featureset
        """
        return self.crf_info.model_feature_detector

    #/////////////////////////////////////////////////////////////////
    # Tagging
    #/////////////////////////////////////////////////////////////////

    #: The name of the java script used to run MalletCRFs.
    _RUN_CRF = "org.nltk.mallet.RunCRF"

    def batch_tag(self, sentences):
        # Write the test corpus to a temporary file
        (fd, test_file) = mkstemp('.txt', 'test')
        self.write_test_corpus(sentences, os.fdopen(fd, 'w'))

        try:
            # Run mallet on the test file.
            stdout, stderr = call_mallet([self._RUN_CRF,
                '--model-file', os.path.abspath(self.crf_info.model_filename),
                '--test-file', test_file], stdout='pipe')

            # Decode the output
            labels = self.parse_mallet_output(stdout)

            # strip __start__ and __end__
            if self.crf_info.add_start_state and self.crf_info.add_end_state:
                labels = [labs[1:-1] for labs in labels]
            elif self.crf_info.add_start_state:
                labels = [labs[1:] for labs in labels]
            elif self.crf_info.add_end_state:
                labels = [labs[:-1] for labs in labels]

            # Combine the labels and the original sentences.
            return [zip(sent, label) for (sent,label) in
                    zip(sentences, labels)]

        finally:
            os.remove(test_file)

    #/////////////////////////////////////////////////////////////////
    # Training
    #/////////////////////////////////////////////////////////////////

    #: The name of the java script used to train MalletCRFs.
    _TRAIN_CRF = "org.nltk.mallet.TrainCRF"

    @classmethod
    def train(cls, feature_detector, corpus, filename=None,
              weight_groups=None, gaussian_variance=1, default_label='O',
              transduction_type='VITERBI', max_iterations=500,
              add_start_state=True, add_end_state=True, trace=1):
        """
        Train a new linear chain CRF tagger based on the given corpus
        of training sequences.  This tagger will be backed by a crf
        model file, containing both a serialized Mallet model and
        information about the CRF's structure.  This crf model file
        will not be automatically deleted -- if you wish to delete
        it, you must delete it manually.  The filename of the model
        file for a MalletCRF crf is available as ``crf.filename()``.

        :type corpus: list(tuple(str, str))
        :param corpus: Training data, represented as a list of
            sentences, where each sentence is a list of (token, tag) tuples.
        :type filename: str
        :param filename: The filename that should be used for the crf
            model file that backs the new MalletCRF.  If no
            filename is given, then a new filename will be chosen
            automatically.
        :type weight_groups: list(CRFInfo.WeightGroup)
        :param weight_groups: Specifies how input-features should
            be mapped to joint-features.  See CRFInfo.WeightGroup
            for more information.
        :type gaussian_variance: float
        :param gaussian_variance: The gaussian variance of the prior
            that should be used to train the new CRF.
        :type default_label: str
        :param default_label: The "label for initial context and
            uninteresting tokens" (from Mallet's SimpleTagger.java.)
            It's unclear whether this currently has any effect.
        :type transduction_type: str
        :param transduction_type: The type of transduction used by
            the CRF.  Can be VITERBI, VITERBI_FBEAM, VITERBI_BBEAM,
            VITERBI_FBBEAM, or VITERBI_FBEAMKL.
        :type max_iterations: int
        :param max_iterations: The maximum number of iterations that
            should be used for training the CRF.
        :type add_start_state: bool
        :param add_start_state: If true, then NLTK will add a special
            start state, named '__start__'.  The initial cost for
            the start state will be set to 0; and the initial cost for
            all other states will be set to +inf.
        :type add_end_state: bool
        :param add_end_state: If true, then NLTK will add a special
            end state, named '__end__'.  The final cost for the end
            state will be set to 0; and the final cost for all other
            states will be set to +inf.
        :type trace: int
        :param trace: Controls the verbosity of trace output generated
            while training the CRF.  Higher numbers generate more verbose
            output.
        """
        t0 = time.time() # Record starting time.

        # If they did not supply a model filename, then choose one.
        if filename is None:
            (fd, filename) = mkstemp('.crf', 'model')
            os.fdopen(fd).close()

        # Ensure that the filename ends with '.zip'
        if not filename.endswith('.crf'):
            filename += '.crf'

        if trace >= 1:
            print '[MalletCRF] Training a new CRF: %s' % filename

        # Create crf-info object describing the new CRF.
        crf_info = MalletCRF._build_crf_info(
            corpus, gaussian_variance, default_label, max_iterations,
            transduction_type, weight_groups, add_start_state,
            add_end_state, filename, feature_detector)

        # Create a zipfile, and write crf-info to it.
        if trace >= 2:
            print '[MalletCRF] Adding crf-info.xml to %s' % filename
        zf = zipfile.ZipFile(filename, mode='w')
        zf.writestr('crf-info.xml', crf_info.toxml()+'\n')
        zf.close()

        # Create the CRF object.
        crf = MalletCRF(filename, feature_detector)

        # Write the Training corpus to a temporary file.
        if trace >= 2:
            print '[MalletCRF] Writing training corpus...'
        (fd, train_file) = mkstemp('.txt', 'train')
        crf.write_training_corpus(corpus, os.fdopen(fd, 'w'))

        try:
            if trace >= 1:
                print '[MalletCRF] Calling mallet to train CRF...'
            cmd = [MalletCRF._TRAIN_CRF,
                   '--model-file', os.path.abspath(filename),
                   '--train-file', train_file]
            if trace > 3:
                call_mallet(cmd)
            else:
                p = call_mallet(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                blocking=False)
                MalletCRF._filter_training_output(p, trace)
        finally:
            # Delete the temp file containing the training corpus.
            os.remove(train_file)

        if trace >= 1:
            print '[MalletCRF] Training complete.'
            print '[MalletCRF]   Model stored in: %s' % filename
        if trace >= 2:
            dt = time.time()-t0
            print '[MalletCRF]   Total training time: %d seconds' % dt

        # Return the completed CRF.
        return crf

    @staticmethod
    def _build_crf_info(corpus, gaussian_variance, default_label,
                        max_iterations, transduction_type, weight_groups,
                        add_start_state, add_end_state,
                        model_filename, feature_detector):
        """
        Construct a CRFInfo object describing a CRF with a given
        set of configuration parameters, and based on the contents of
        a given corpus.
        """
        state_info_list = []

        labels = set()
        if add_start_state:
            labels.add('__start__')
        if add_end_state:
            labels.add('__end__')
        transitions = set() # not necessary to find this?
        for sent in corpus:
            prevtag = default_label
            for (tok,tag) in sent:
                labels.add(tag)
                transitions.add( (prevtag, tag) )
                prevtag = tag
            if add_start_state:
                transitions.add( ('__start__', sent[0][1]) )
            if add_end_state:
                transitions.add( (sent[-1][1], '__end__') )
        labels = sorted(labels)

        # 0th order default:
        if weight_groups is None:
            weight_groups = [CRFInfo.WeightGroup(name=l, src='.*',
                                                 dst=re.escape(l))
                             for l in labels]

        # Check that weight group names are unique
        if len(weight_groups) != len(set(wg.name for wg in weight_groups)):
            raise ValueError("Weight group names must be unique")

        # Construct a list of state descriptions.  Currently, we make
        # these states fully-connected, with one parameter per
        # transition.
        for src in labels:
            if add_start_state:
                if src == '__start__':
                    initial_cost = 0
                else:
                    initial_cost = '+inf'
            if add_end_state:
                if src == '__end__':
                    final_cost = 0
                else:
                    final_cost = '+inf'
            state_info = CRFInfo.State(src, initial_cost, final_cost, [])
            for dst in labels:
                state_weight_groups = [wg.name for wg in weight_groups
                                       if wg.match(src, dst)]
                state_info.transitions.append(
                    CRFInfo.Transition(dst, dst, state_weight_groups))
            state_info_list.append(state_info)

        return CRFInfo(state_info_list, gaussian_variance,
                       default_label, max_iterations,
                       transduction_type, weight_groups,
                       add_start_state, add_end_state,
                       model_filename, feature_detector)

    #: A table used to filter the output that mallet generates during
    #: training.  By default, mallet generates very verbose output.
    #: This table is used to select which lines of output are actually
    #: worth displaying to the user, based on the level of the *trace*
    #: parameter.  Each entry of this table is a tuple
    #: (min_trace_level, regexp).  A line will be displayed only if
    #: trace>=min_trace_level and the line matches regexp for at
    #: least one table entry.
    _FILTER_TRAINING_OUTPUT = [
        (1, r'DEBUG:.*'),
        (1, r'Number of weights.*'),
        (1, r'CRF about to train.*'),
        (1, r'CRF finished.*'),
        (1, r'CRF training has converged.*'),
        (2, r'CRF weights.*'),
        (2, r'getValue\(\) \(loglikelihood\) .*'),
        ]

    @staticmethod
    def _filter_training_output(p, trace):
        """
        Filter the (very verbose) output that is generated by mallet,
        and only display the interesting lines.  The lines that are
        selected for display are determined by _FILTER_TRAINING_OUTPUT.
        """
        out = []
        while p.poll() is None:
            while True:
                line = p.stdout.readline()
                if not line: break
                out.append(line)
                for (t, regexp) in MalletCRF._FILTER_TRAINING_OUTPUT:
                    if t <= trace and re.match(regexp, line):
                        indent = '  '*t
                        print '[MalletCRF] %s%s' % (indent, line.rstrip())
                        break
        if p.returncode != 0:
            print "\nError encountered!  Mallet's most recent output:"
            print ''.join(out[-100:])
            raise OSError('Mallet command failed')


    #/////////////////////////////////////////////////////////////////
    # Communication w/ mallet
    #/////////////////////////////////////////////////////////////////

    def write_training_corpus(self, corpus, stream, close_stream=True):
        """
        Write a given training corpus to a given stream, in a format that
        can be read by the java script org.nltk.mallet.TrainCRF.
        """
        feature_detector = self.crf_info.feature_detector
        for sentence in corpus:
            if self.crf_info.add_start_state:
                stream.write('__start__ __start__\n')
            unlabeled_sent = [tok for (tok,tag) in sentence]
            for index in range(len(unlabeled_sent)):
                featureset = feature_detector(unlabeled_sent, index)
                for (fname, fval) in featureset.items():
                    stream.write(self._format_feature(fname, fval)+" ")
                stream.write(sentence[index][1]+'\n')
            if self.crf_info.add_end_state:
                stream.write('__end__ __end__\n')
            stream.write('\n')
        if close_stream: stream.close()

    def write_test_corpus(self, corpus, stream, close_stream=True):
        """
        Write a given test corpus to a given stream, in a format that
        can be read by the java script org.nltk.mallet.TestCRF.
        """
        feature_detector = self.crf_info.feature_detector
        for sentence in corpus:
            if self.crf_info.add_start_state:
                stream.write('__start__ __start__\n')
            for index in range(len(sentence)):
                featureset = feature_detector(sentence, index)
                for (fname, fval) in featureset.items():
                    stream.write(self._format_feature(fname, fval)+" ")
                stream.write('\n')
            if self.crf_info.add_end_state:
                stream.write('__end__ __end__\n')
            stream.write('\n')
        if close_stream: stream.close()

    def parse_mallet_output(self, s):
        """
        Parse the output that is generated by the java script
        org.nltk.mallet.TestCRF, and convert it to a labeled
        corpus.
        """
        if re.match(r'\s*<<start>>', s):
            assert 0, 'its a lattice'
        corpus = [[]]
        for line in s.split('\n'):
            line = line.strip()
            # Label with augmentations?
            if line:
                corpus[-1].append(line.strip())
            # Start of new instance?
            elif corpus[-1] != []:
                corpus.append([])
        if corpus[-1] == []: corpus.pop()
        return corpus

    _ESCAPE_RE = re.compile('[^a-zA-Z0-9]')
    @staticmethod
    def _escape_sub(m):
        return '%' + ('%02x' % ord(m.group()))

    @staticmethod
    def _format_feature(fname, fval):
        """
        Return a string name for a given feature (name, value) pair,
        appropriate for consumption by mallet.  We escape every
        character in fname or fval that's not a letter or a number,
        just to be conservative.
        """
        fname = MalletCRF._ESCAPE_RE.sub(MalletCRF._escape_sub, fname)
        if isinstance(fval, basestring):
            fval = "'%s'" % MalletCRF._ESCAPE_RE.sub(
                MalletCRF._escape_sub, fval)
        else:
            fval = MalletCRF._ESCAPE_RE.sub(MalletCRF._escape_sub, '%r'%fval)
        return fname+'='+fval

    #/////////////////////////////////////////////////////////////////
    # String Representation
    #/////////////////////////////////////////////////////////////////

    def __repr__(self):
        return 'MalletCRF(%r)' % self.crf_info.model_filename

###########################################################################
## Serializable CRF Information Object
###########################################################################

class CRFInfo(object):
    """
    An object used to record configuration information about a
    MalletCRF object.  This configuration information can be
    serialized to an XML file, which can then be read by NLTK's custom
    interface to Mallet's CRF.

    CRFInfo objects are typically created by the ``MalletCRF.train()``
    method.

    Advanced users may wish to directly create custom
    CRFInfo.WeightGroup objects and pass them to the
    ``MalletCRF.train()`` function.  See CRFInfo.WeightGroup for
    more information.
    """
    def __init__(self, states, gaussian_variance, default_label,
                 max_iterations, transduction_type, weight_groups,
                 add_start_state, add_end_state, model_filename,
                 feature_detector):
        self.gaussian_variance = float(gaussian_variance)
        self.default_label = default_label
        self.states = states
        self.max_iterations = max_iterations
        self.transduction_type = transduction_type
        self.weight_groups = weight_groups
        self.add_start_state = add_start_state
        self.add_end_state = add_end_state
        self.model_filename = model_filename
        if isinstance(feature_detector, basestring):
            self.feature_detector_name = feature_detector
            self.feature_detector = None
        else:
            self.feature_detector_name = feature_detector.__name__
            self.feature_detector = feature_detector

    _XML_TEMPLATE = (
        '<crf>\n'
        '  <modelFile>%(model_filename)s</modelFile>\n'
        '  <gaussianVariance>%(gaussian_variance)d</gaussianVariance>\n'
        '  <defaultLabel>%(default_label)s</defaultLabel>\n'
        '  <maxIterations>%(max_iterations)s</maxIterations>\n'
        '  <transductionType>%(transduction_type)s</transductionType>\n'
        '  <featureDetector name="%(feature_detector_name)s">\n'
        '    %(feature_detector)s\n'
        '  </featureDetector>\n'
        '  <addStartState>%(add_start_state)s</addStartState>\n'
        '  <addEndState>%(add_end_state)s</addEndState>\n'
        '  <states>\n'
        '%(states)s\n'
        '  </states>\n'
        '  <weightGroups>\n'
        '%(w_groups)s\n'
        '  </weightGroups>\n'
        '</crf>\n')

    def toxml(self):
        info = self.__dict__.copy()
        info['states'] = '\n'.join(state.toxml() for state in self.states)
        info['w_groups'] = '\n'.join(wg.toxml() for wg in self.weight_groups)
        info['feature_detector_name'] = (info['feature_detector_name']
                                         .replace('&', '&amp;')
                                         .replace('<', '&lt;'))
        try:
            fd = pickle.dumps(self.feature_detector)
            fd = fd.replace('&', '&amp;').replace('<', '&lt;')
            fd = fd.replace('\n', '&#10;') # put pickle data all on 1 line.
            info['feature_detector'] = '<pickle>%s</pickle>' % fd
        except pickle.PicklingError:
            info['feature_detector'] = ''
        return self._XML_TEMPLATE % info

    @staticmethod
    def fromstring(s):
        return CRFInfo._read(ElementTree.fromstring(s))

    @staticmethod
    def _read(etree):
        states = [CRFInfo.State._read(et) for et in
                  etree.findall('states/state')]
        weight_groups = [CRFInfo.WeightGroup._read(et) for et in
                         etree.findall('weightGroups/weightGroup')]
        fd = etree.find('featureDetector')
        feature_detector = fd.get('name')
        if fd.find('pickle') is not None:
            try: feature_detector = pickle.loads(fd.find('pickle').text)
            except pickle.PicklingError, e: pass # unable to unpickle it.

        return CRFInfo(states,
                       float(etree.find('gaussianVariance').text),
                       etree.find('defaultLabel').text,
                       int(etree.find('maxIterations').text),
                       etree.find('transductionType').text,
                       weight_groups,
                       bool(etree.find('addStartState').text),
                       bool(etree.find('addEndState').text),
                       etree.find('modelFile').text,
                       feature_detector)

    def write(self, filename):
        out = open(filename, 'w')
        out.write(self.toxml())
        out.write('\n')
        out.close()

    class State(object):
        """
        A description of a single CRF state.
        """
        def __init__(self, name, initial_cost, final_cost, transitions):
            if initial_cost != '+inf': initial_cost = float(initial_cost)
            if final_cost != '+inf': final_cost = float(final_cost)
            self.name = name
            self.initial_cost = initial_cost
            self.final_cost = final_cost
            self.transitions = transitions

        _XML_TEMPLATE = (
            '    <state name="%(name)s" initialCost="%(initial_cost)s" '
            'finalCost="%(final_cost)s">\n'
            '      <transitions>\n'
            '%(transitions)s\n'
            '      </transitions>\n'
            '    </state>\n')
        def toxml(self):
            info = self.__dict__.copy()
            info['transitions'] = '\n'.join(transition.toxml()
                                            for transition in self.transitions)
            return self._XML_TEMPLATE % info

        @staticmethod
        def _read(etree):
            transitions = [CRFInfo.Transition._read(et)
                           for et in etree.findall('transitions/transition')]
            return CRFInfo.State(etree.get('name'),
                                 etree.get('initialCost'),
                                 etree.get('finalCost'),
                                 transitions)

    class Transition(object):
        """
        A description of a single CRF transition.
        """
        def __init__(self, destination, label, weightgroups):
            """
            :param destination: The name of the state that this transition
                connects to.
            :param label: The tag that is generated when traversing this
                transition.
            :param weightgroups: A list of WeightGroup names, indicating
                which weight groups should be used to calculate the cost
                of traversing this transition.
            """
            self.destination = destination
            self.label = label
            self.weightgroups = weightgroups

        _XML_TEMPLATE = ('        <transition label="%(label)s" '
                         'destination="%(destination)s" '
                         'weightGroups="%(w_groups)s"/>')
        def toxml(self):
            info = self.__dict__
            info['w_groups'] = ' '.join(wg for wg in self.weightgroups)
            return self._XML_TEMPLATE % info

        @staticmethod
        def _read(etree):
            return CRFInfo.Transition(etree.get('destination'),
                                      etree.get('label'),
                                      etree.get('weightGroups').split())

    class WeightGroup(object):
        """
        A configuration object used by MalletCRF to specify how
        input-features (which are a function of only the input) should be
        mapped to joint-features (which are a function of both the input
        and the output tags).

        Each weight group specifies that a given set of input features
        should be paired with all transitions from a given set of source
        tags to a given set of destination tags.
        """
        def __init__(self, name, src, dst, features='.*'):
            """
            :param name: A unique name for this weight group.
            :param src: The set of source tags that should be used for
                this weight group, specified as either a list of state
                names or a regular expression.
            :param dst: The set of destination tags that should be used
                for this weight group, specified as either a list of state
                names or a regular expression.
            :param features: The set of input feature that should be used
                for this weight group, specified as either a list of
                feature names or a regular expression.  WARNING: currently,
                this regexp is passed streight to java -- i.e., it must
                be a java-style regexp!
            """
            if re.search('\s', name):
                raise ValueError('weight group name may not '
                                 'contain whitespace.')
            if re.search('"', name):
                raise ValueError('weight group name may not contain \'"\'.')
            self.name = name
            self.src = src
            self.dst = dst
            self.features = features
            self._src_match_cache = {}
            self._dst_match_cache = {}

        _XML_TEMPLATE = ('    <weightGroup name="%(name)s" src="%(src)s" '
                         'dst="%(dst)s" features="%(features)s" />')
        def toxml(self):
            return self._XML_TEMPLATE % self.__dict__

        @staticmethod
        def _read(etree):
            return CRFInfo.WeightGroup(etree.get('name'),
                                       etree.get('src'),
                                       etree.get('dst'),
                                       etree.get('features'))

        # [xx] feature name????
        def match(self, src, dst):
            # Check if the source matches
            src_match = self._src_match_cache.get(src)
            if src_match is None:
                if isinstance(self.src, basestring):
                    src_match = bool(re.match(self.src+'\Z', src))
                else:
                    src_match = src in self.src
                self._src_match_cache[src] = src_match

            # Check if the dest matches
            dst_match = self._dst_match_cache.get(dst)
            if dst_match is None:
                if isinstance(self.dst, basestring):
                    dst_match = bool(re.match(self.dst+'\Z', dst))
                else:
                    dst_match = dst in self.dst
                self._dst_match_cache[dst] = dst_match

            # Return true if both matched.
            return src_match and dst_match

###########################################################################
## Demonstration code
###########################################################################

def demo(train_size=100, test_size=100,
         java_home='/usr/local/jdk1.5.0/',
         mallet_home='/usr/local/mallet-0.4'):
    from nltk.corpus import brown
    import textwrap

    # Define a very simple feature detector
    def fd(sentence, index):
        word = sentence[index]
        return dict(word=word, suffix=word[-2:], len=len(word))

    # Let nltk know where java & mallet are.
    nltk.internals.config_java(java_home)
    nltk.classify.mallet.config_mallet(mallet_home)

    # Get the training & test corpus.  We simplify the tagset a little:
    # just the first 2 chars.
    def strip(corpus): return [[(w, t[:2]) for (w,t) in sent]
                               for sent in corpus]
    brown_train = strip(brown.tagged_sents(categories='news')[:train_size])
    brown_test = strip(brown.tagged_sents(categories='editorial')[:test_size])

    crf = MalletCRF.train(fd, brown_train, #'/tmp/crf-model',
                          transduction_type='VITERBI')
    sample_output = crf.tag([w for (w,t) in brown_test[5]])
    acc = nltk.tag.accuracy(crf, brown_test)
    print '\nAccuracy: %.1f%%' % (acc*100)
    print 'Sample output:'
    print textwrap.fill(' '.join('%s/%s' % w for w in sample_output),
                        initial_indent='  ', subsequent_indent='  ')+'\n'

    # Clean up
    print 'Clean-up: deleting', crf.filename
    os.remove(crf.filename)

    return crf


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
