# Natural Language Toolkit: Interface to Megam Classifier
#
# Copyright (C) 2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: naivebayes.py 2063 2004-07-17 21:02:24Z edloper $

"""
A set of functions used to interface with the external U{megam
<http://www.cs.utah.edu/~hal/megam/>} maxent optimization package.
Before C{megam} can be used, you should tell NLTK where it can find
the C{megam} binary, using the L{config_megam()} function.  Typical
usage:

    >>> import nltk
    >>> nltk.config_megam('.../path/to/megam')
    >>> classifier = nltk.MaxentClassifier.train(corpus, 'megam')

"""
__docformat__ = 'epytext en'

import numpy, os, os.path, subprocess

######################################################################
#{ Configuration
######################################################################

_megam_bin = None
def config_megam(bin=None):
    """
    Configure NLTK's interface to the C{megam} maxent optimization
    package.

    @param bin: The full path to the C{megam} binary.  If not specified,
        then nltk will search the system for a C{megam} binary; and if
        one is not found, it will raise a C{LookupError} exception.
    @type bin: C{string}
    """
    global _megam_bin

    BIN_NAMES = ['megam', 'megam_686', 'megam_i686.opt']

    # Set the binary
    if bin is not None:
        if not os.path.exists(bin):
            raise ValueError('Cound not find megam binary at %r' % bin)
        _megam_bin = bin

    # Check the MEGAM environment variable.
    for env_var in ['MEGAM',  'MEGAM_HOME']:
        if _megam_bin is None and env_var in os.environ:
            if os.path.isfile(os.environ[env_var]):
                _megam_bin = os.environ[env_var]
                print '[Found megam: %s]' % _megam_bin
            elif os.path.isdir(os.environ[env_var]):
                for bin in BIN_NAMES:
                    if os.path.isfile(os.path.join(os.environ[env_var], bin)):
                        _megam_bin = os.path.join(os.environ[env_var], bin)
                        print '[Found megam: %s]' % _megam_bin
                        break
                        
    # If we're on a POSIX system, try using the 'which' command to
    # find a megam binary.
    if _megam_bin is None and os.name == 'posix':
        for bin in BIN_NAMES:
            try:
                p = subprocess.Popen(['which', bin], stdout=subprocess.PIPE)
                stdout, stderr = p.communicate()
                path = stdout.strip()
                if path.endswith(bin) and os.path.exists(path):
                    _megam_bin = path
                print '[Found megam: %s]' % path
                break
            except:
                pass

    if _megam_bin is None:
        raise LookupError('Unable to find megam!  Use config_megam() '
                          'or set the MEGAMHOME environment variable.')

######################################################################
#{ Megam Interface Functions
######################################################################

def write_megam_file(train_toks, encoding, stream,
                     bernoulli=True, explicit=True):
    """
    Generate an input file for C{megam} based on the given corpus of
    classified tokens.

    @type train_toks: C{list} of C{tuples} of (C{dict}, C{str})
    @param train_toks: Training data, represented as a list of
        pairs, the first member of which is a feature dictionary,
        and the second of which is a classification label.

    @type encoding: L{MaxentFeatureEncodingI}
    @param encoding: A feature encoding, used to convert featuresets
        into feature vectors.

    @type stream: C{stream}
    @param stream: The stream to which the megam input file should be
        written.

    @param bernoulli: If true, then use the 'bernoulli' format.  I.e.,
        all joint features have binary values, and are listed iff they
        are true.  Otherwise, list feature values explicitly.  If
        C{bernoulli=False}, then you must call C{megam} with the
        C{-fvals} option.

    @param explicit: If true, then use the 'explicit' format.  I.e.,
        list the features that would fire for any of the possible
        labels, for each token.  If C{explicit=True}, then you must
        call C{megam} with the C{-explicit} option.
    """
    # Look up the set of labels.
    labels = encoding.labels()
    labelnum = dict([(label, i) for (i, label) in enumerate(labels)])

    # Write the file, which contains one line per instance.
    for featureset, label in train_toks:
        # First, the instance number.
        stream.write('%d' % labelnum[label])

        # For implicit file formats, just list the features that fire
        # for thie instance's actual label.
        if not explicit:
            _write_megam_features(encoding.encode(featureset, label),
                                  stream, bernoulli)

        # For explicit formats, list the features that would fire for
        # any of the possible labels.
        else:
            for l in labels:
                stream.write(' #')
                _write_megam_features(encoding.encode(featureset, l),
                                      stream, bernoulli)

        # End of the isntance.
        stream.write('\n')

def parse_megam_weights(s):
    """
    Given the stdout output generated by C{megam} when training a
    model, return a C{numpy} array containing the corresponding weight
    vector.  This function does not currently handle bias features.
    """
    lines = s.strip().split('\n')
    weights = numpy.zeros(len(lines), 'd')
    for line in s.split('\n'):
        if line.strip():
            fid, weight = line.split()
            weights[int(fid)] = float(weight)
    return weights

def _write_megam_features(vector, stream, bernoulli):
    for (fid, fval) in vector:
        if bernoulli:
            if fval == 1:
                stream.write(' %s' % fid)
            elif fval != 0:
                raise ValueError('If bernoulli=True, then all'
                                 'features must be binary.')
        else:
            stream.write(' %s %s' % (fid, fval))

def call_megam(args):
    """
    Call the C{megam} binary with the given arguments.
    """
    if isinstance(args, basestring):
        raise TypeError('args should be a list of strings')
    if _megam_bin is None:
        config_megam()

    # Call megam via a subprocess
    cmd = [_megam_bin] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    (stdout, stderr) = p.communicate()

    # Check the return code.
    if p.returncode != 0:
        print
        print stderr
        raise OSError('megam command failed!')

    return stdout
    
