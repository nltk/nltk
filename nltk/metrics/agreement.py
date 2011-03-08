# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Implementations of inter-annotator agreement coefficients surveyed by Artstein
and Poesio (2007), Inter-Coder Agreement for Computational Linguistics.

An agreement coefficient calculates the amount that annotators agreed on label 
assignments beyond what is expected by chance.

In defining the AnnotationTask class, we use naming conventions similar to the 
paper's terminology.  There are three types of objects in an annotation task: 

    the coders (variables "c" and "C")
    the items to be annotated (variables "i" and "I")
    the potential categories to be assigned (variables "k" and "K")

Additionally, it is often the case that we don't want to treat two different 
labels as complete disagreement, and so the AnnotationTask constructor can also
take a distance metric as a final argument.  Distance metrics are simply 
functions that take two arguments, and return a value between 0.0 and 1.0 
indicating the distance between them.  If not supplied, the default is binary 
comparison between the arguments.

The simplest way to initialize an AnnotationTask is with a list of equal-length 
lists, each containing a coder's assignments for all objects in the task:

    task = AnnotationTask([],[],[])

Alpha (Krippendorff 1980)
Kappa (Cohen 1960)
S (Bennet, Albert and Goldstein 1954)
Pi (Scott 1955)


TODO: Describe handling of multiple coders and missing data

Expected results from the Artstein and Poesio survey paper:

>>> t = AnnotationTask(data=[x.split() for x in open("%sartstein_poesio_example.txt" % (__file__.replace("__init__.py", "")))])
>>> t.avg_Ao()
0.88
>>> t.pi()
0.7995322418977614
>>> t.S()
0.81999999999999984
"""

import logging
from distance import *

class AnnotationTask:
    """Represents an annotation task, i.e. people assign labels to items.
    
    Notation tries to match notation in Artstein and Poesio (2007).

    In general, coders and items can be represented as any hashable object.
    Integers, for example, are fine, though strings are more readable.
    Labels must support the distance functions applied to them, so e.g.
    a string-edit-distance makes no sense if your labels are integers,
    whereas interval distance needs numeric values.  A notable case of this
    is the MASI metric, which requires Python sets.
    """

    def __init__(self, data=None, distance=binary_distance):
        """Initialize an empty annotation task.

        """
        self.distance = distance
        self.I = set()
        self.K = set()
        self.C = set()
        self.data = []
        if data != None:
            self.load_array(data)

    def __str__(self):
        return "\r\n".join(map(lambda x:"%s\t%s\t%s" %
                               (x['coder'], x['item'].replace('_', "\t"),
                                ",".join(x['labels'])), self.data))

    def load_array(self, array):
        """Load the results of annotation.
        
        The argument is a list of 3-tuples, each representing a coder's labeling of an item:
            (coder,item,label)
        """
        for coder, item, labels in array:
            self.C.add(coder)
            self.K.add(labels)
            self.I.add(item)
            self.data.append({'coder':coder, 'labels':labels, 'item':item})

    def agr(self, cA, cB, i):
        """Agreement between two coders on a given item

        """
        kA = filter(lambda x:x['coder']==cA and x['item']==i, self.data)[0]
        kB = filter(lambda x:x['coder']==cB and x['item']==i, self.data)[0]
        ret = 1.0 - float(self.distance(kA['labels'], kB['labels']))
        logging.debug("Observed agreement between %s and %s on %s: %f",
                      cA, cB, i, ret)
        logging.debug("Distance between \"%s\" and \"%s\": %f",
                      ",".join(kA['labels']), ",".join(kB['labels']), 1.0 - ret)
        return ret

    def N(self, k=None, i=None, c=None):
        """Implements the "n-notation" used in Artstein and Poesio (2007)

        """
        if k != None and i == None and c == None:
            ret = len(filter(lambda x:k == x['labels'], self.data))
        elif k != None and i != None and c == None:
            ret = len(filter(lambda x:k == x['labels'] and i == x['item'], self.data))
        elif k != None and c != None and i==None:
            ret = len(filter(lambda x:k == x['labels'] and c == x['coder'], self.data))
        else:
            print "You must pass either i or c, not both!"
        logging.debug("Count on N[%s,%s,%s]: %d", k, i, c, ret)
        return float(ret)

    def Ao(self, cA, cB):
        """Observed agreement between two coders on all items.

        """
        ret = float(sum(map(lambda x:self.agr(cA, cB, x), self.I))) / float(len(self.I))
        logging.debug("Observed agreement between %s and %s: %f", cA, cB, ret)
        return ret

    def avg_Ao(self):
        """Average observed agreement across all coders and items.

        """
        s = self.C.copy()
        counter = 0.0
        total = 0.0
        for cA in self.C:
            s.remove(cA)
            for cB in s:
                total += self.Ao(cA, cB)
                counter += 1.0
        ret = total / counter
        logging.debug("Average observed agreement: %f", ret)
        return ret

    #TODO: VERY slow, speed this up!
    def Do_alpha(self):
        """The observed disagreement for the alpha coefficient.

        The alpha coefficient, unlike the other metrics, uses this rather than
        observed agreement.
        """
        total = 0.0
        for i in self.I:
            for j in self.K:
                for l in self.K:
                    total += float(self.N(i = i, k = j) * self.N(i = i, k = l)) * self.distance(l, j)
        ret = (1.0 / float((len(self.I) * len(self.C) * (len(self.C) - 1)))) * total
        logging.debug("Observed disagreement: %f", ret)
        return ret

    def Do_Kw_pairwise(self,cA,cB,max_distance=1.0):
        """The observed disagreement for the weighted kappa coefficient.

        """
        total = 0.0
        for i in self.I:
            total += self.distance(filter(lambda x:x['coder']==cA and x['item']==i, self.data)[0]['labels'],
                                   filter(lambda x:x['coder']==cB and x['item']==i, self.data)[0]['labels'])
        ret = total / (len(self.I) * max_distance)
        logging.debug("Observed disagreement between %s and %s: %f", cA, cB, ret)
        return ret

    def Do_Kw(self, max_distance=1.0):
        """Averaged over all labelers
        
        """
        vals = {}
        for cA in self.C:
            for cB in self.C:
                if (not frozenset([cA,cB]) in vals.keys() and not cA == cB):
                    vals[frozenset([cA, cB])] = self.Do_Kw_pairwise(cA, cB, max_distance)
        ret = sum(vals.values()) / len(vals)
        logging.debug("Observed disagreement: %f", ret)
        return ret

    # Agreement Coefficients
    def S(self):
        """Bennett, Albert and Goldstein 1954

        """
        Ae = 1.0 / float(len(self.K))        
        ret = (self.avg_Ao() - Ae) / (1.0 - Ae)
        return ret

    def pi(self):
        """Scott 1955

        """
        total = 0.0
        for k in self.K:
            total += self.N(k=k) ** 2
        Ae = (1.0 / (4.0 * float(len(self.I) ** 2))) * total
        ret = (self.avg_Ao() - Ae) / (1 - Ae)
        return ret

    def pi_avg(self):
        pass

    def kappa_pairwise(self, cA, cB):
        """

        """
        Ae = 0.0
        for k in self.K:
            Ae += (float(self.N(c=cA, k=k)) / float(len(self.I))) * (float(self.N(c=cB, k=k)) / float(len(self.I)))
        ret = (self.Ao(cA, cB) - Ae) / (1.0 - Ae)
        logging.debug("Expected agreement between %s and %s: %f", cA, cB, Ae)
        logging.info("Kappa between %s and %s: %f", cA, cB, ret)
        return ret

    def kappa(self):
        """Cohen 1960

        """
        vals = {}
        for a in self.C:
            for b in self.C:
                if a == b or "%s%s" % (b, a) in vals:
                    continue
                vals["%s%s" % (a, b)] = self.kappa_pairwise(a, b)
        ret = sum(vals.values()) / float(len(vals))
        return ret

    def alpha(self):
        """Krippendorff 1980

        """
        De = 0.0
        for j in self.K:
            for l in self.K:
                De += float(self.N(k=j) * self.N(k=l)) * self.distance(j, l)
        De = (1.0 / (len(self.I) * len(self.C) * (len(self.I) * len(self.C) - 1))) * De
        logging.debug("Expected disagreement: %f", De)
        ret = 1.0 - (self.Do_alpha() / De)
        return ret

    def weighted_kappa_pairwise(self, cA, cB, max_distance=1.0):
        """Cohen 1968

        """
        total = 0.0
        for j in self.K:
            for l in self.K:
                total += self.N(c=cA, k=j) * self.N(c=cB, k=l) * self.distance(j, l)
        De = total / (max_distance * pow(len(self.I), 2))
        logging.debug("Expected disagreement between %s and %s: %f", cA, cB, De)
        Do = self.Do_Kw_pairwise(cA, cB)
        ret = 1.0 - (Do / De)
        logging.warning("Weighted kappa between %s and %s: %f", cA, cB, ret)
        return ret

    def weighted_kappa(self):
        """Cohen 1968

        """
        vals = {}
        for a in self.C:
            for b in self.C:
                if a == b or frozenset([a, b]) in vals:
                    continue
                vals[frozenset([a, b])] = self.weighted_kappa_pairwise(a, b)
        ret = sum(vals.values()) / float(len(vals))
        return ret


if __name__ == '__main__':

    import re
    import optparse
    import distance

    # process command-line arguments
    parser = optparse.OptionParser()
    parser.add_option("-d", "--distance", dest="distance", default="binary_distance",
                      help="distance metric to use")
    parser.add_option("-a", "--agreement", dest="agreement", default="kappa",
                      help="agreement coefficient to calculate")
    parser.add_option("-e", "--exclude", dest="exclude", action="append",
                      default=[], help="coder names to exclude (may be specified multiple times)")
    parser.add_option("-i", "--include", dest="include", action="append", default=[],
                      help="coder names to include, same format as exclude")
    parser.add_option("-f", "--file", dest="file",
                      help="file to read labelings from, each line with three columns: 'labeler item labels'")
    parser.add_option("-v", "--verbose", dest="verbose", default='0',
                      help="how much debugging to print on stderr (0-4)")
    parser.add_option("-c", "--columnsep", dest="columnsep", default="\t",
                      help="char/string that separates the three columns in the file, defaults to tab")
    parser.add_option("-l", "--labelsep", dest="labelsep", default=",",
                      help="char/string that separates labels (if labelers can assign more than one), defaults to comma")
    parser.add_option("-p", "--presence", dest="presence", default=None,
                      help="convert each labeling into 1 or 0, based on presence of LABEL")
    parser.add_option("-T", "--thorough", dest="thorough", default=False, action="store_true",
                      help="calculate agreement for every subset of the annotators")
    (options, remainder) = parser.parse_args()
    
    if not options.file:
        parser.print_help()
        exit()

    logging.basicConfig(level=50 - 10 * int(options.verbose))

    # read in data from the specified file
    data = []
    for l in open(options.file):
        toks = l.split(options.columnsep)
        coder, object, labels = toks[0], str(toks[1:-1]), frozenset(toks[-1].strip().split(options.labelsep))
        if ((options.include == options.exclude) or
            (len(options.include) > 0 and coder in options.include) or
            (len(options.exclude) > 0 and coder not in options.exclude)):
            data.append((coder, object, labels))

    if options.presence:
        task = AnnotationTask(data, getattr(distance, options.distance)(options.presence))
    else:
        task = AnnotationTask(data, getattr(distance, options.distance))

    if options.thorough:
        pass
    else:
        print getattr(task, options.agreement)()

    logging.shutdown()

