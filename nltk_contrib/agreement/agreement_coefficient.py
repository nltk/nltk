# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
import sets
from distance_metric import *

class AnnotationTask():
    """Represents an annotation task, i.e. people assign labels to items.
    
    Notation tries to match notation in Artstein and Poesio (2007).

    In general, coders and items can be represented as any hashable object.
    Integers, for example, are fine, though strings are more readable.
    Labels must support the distance functions applied to them, so e.g.
    a string-edit-distance makes no sense if your labels are integers,
    whereas interval distance needs numeric values.  A notable case of this
    is the MASI metric, which requires Python sets.
    """

    def __init__(self,distance=binary):
        """Initialize an empty annotation task.

        """
        self.distance = distance
        self.I = sets.Set()
        self.K = sets.Set()
        self.C = sets.Set()
        self.data = []

    def __str__(self):
        return "\r\n".join(map(lambda x:"%s\t%s\t%s"%(x['coder'],x['item'].replace('_',"\t"),",".join(x['labels'])),self.data))

    def load_array(self,array):
        """Load the results of annotation.
        
        The argument is a list of 3-tuples, each representing a coder's labeling of an item:
            (coder,item,label)
        """
        for coder,item,labels in array:
            self.C.add(coder)
            self.K.add(labels)
            self.I.add(item)
            self.data.append({'coder':coder,'labels':labels,'item':item})

    def agr(self,cA,cB,i):
        """Agreement between two coders on a given item

        """
        kA = filter(lambda x:x['coder']==cA and x['item']==i,self.data)[0]
        kB = filter(lambda x:x['coder']==cB and x['item']==i,self.data)[0]
        return 1.0 - float(self.distance(kA['labels'],kB['labels']))

    def N(self,k="",i="",c=""):
        """Implements the "n-notation" used in Artstein and Poesio (2007)

        """
        if(k!="" and i=="" and c==""):
            return len(filter(lambda x:k==x['labels'],self.data))
        elif(k!="" and i!="" and c==""):
            return len(filter(lambda x:k==x['labels'] and i==x['item'],self.data))
        elif(k!="" and c!="" and i==""):
            return len(filter(lambda x:k==x['labels'] and c==x['coder'],self.data))
        else:
            print "You must pass either i or c, not both!"

    def Ao(self,cA,cB):
        """Observed agreement between two coders on all items.

        """
        return float(sum(map(lambda x:self.agr(cA,cB,x),self.I)))/float(len(self.I))

    def avg_Ao(self):
        """Average observed agreement across all coders and items.

        """
        s = self.C.copy()
        counter = 0.0
        total = 0.0
        for cA in self.C:
            s.remove(cA)
            for cB in s:
                total += self.Ao(cA,cB)
                counter += 1.0
        return total/counter

    def Do(self):
        """The observed disagreement.

        The alpha coefficient, unlike the other metrics, uses this rather than
        observed agreement.
        """
        total = 0.0
        for i in self.I:
            for j in self.K:
                for l in self.K:
                    total += float(self.N(i=i,k=j)*self.N(i=i,k=l))*self.distance(l,j)
        ret = (1.0/float((len(self.I)*len(self.C)*(len(self.C)-1))))*total
        return ret

    # Agreement Coefficients
    def S(self):
        """Bennett, Albert and Goldstein 1954

        """
        Ae = 1.0/float(len(self.K))        
        return (self.avg_Ao() - Ae)/(1.0 - Ae)

    def pi(self):
        """Scott 1955

        """
        total = 0.0
        for k in self.K:
            total += self.N(k=k)**2
        Ae = (1.0/(4.0*float(len(self.I)**2)))*total
        return (self.avg_Ao()-Ae)/(1-Ae)

    def pi_avg(self):
        pass

    def kappa(self,cA,cB):
        """Cohen 1960

        """
        Ae = 0.0
        for k in self.K:
            Ae += (float(self.N(c=cA,k=k))/float(len(self.I))) * (float(self.N(c=cB,k=k))/float(len(self.I)))
        ret = (self.Ao(cA,cB)-Ae)/(1.0-Ae)
        return ret

    def kappa_avg(self):
        vals = {}
        for a in self.C:
            for b in self.C:
                if(a==b or "%s%s"%(b,a) in vals):
                    continue
                vals["%s%s"%(a,b)] = self.kappa(a,b)
        return sum(vals.values())/float(len(vals))

    def alpha(self):
        """Krippendorff 1980

        """
        De = 0.0
        for j in self.K:
            for l in self.K:
                De += float(self.N(k=j)*self.N(k=l))*self.distance(j,l)
        De = (1.0/(len(self.I)*len(self.C)*(len(self.I)*len(self.C)-1)))*De
        ret = 1.0 - (self.Do()/De)
        return ret


if(__name__=='__main__'):

    import optparse

    # process command-line arguments
    parser = optparse.OptionParser()
    parser.add_option("-d","--distance",dest="distance",default="binary",help="distance metric to use")
    parser.add_option("-a","--agreement",dest="agreement",default="",help="agreement coefficient to calculate")
    parser.add_option("-e","--exclude",dest="exclude",default="",help="coder names to exclude (comma-separated), e.g. jane,mike")
    parser.add_option("-i","--include",dest="include",default="",help="coder names to include, same format as exclude")
    parser.add_option("-f","--file",dest="file",help="file to read labelings from, each line with three columns: 'labeler item labels'")
    parser.add_option("-c","--columnsep",dest="columnsep",default="\t",help="char/string that separates the three columns in the file, defaults to tab")
    parser.add_option("-l","--labelsep",dest="labelsep",default=",",help="char/string that separates labels (if labelers can assign more than one), defaults to comma")
    (options,remainder) = parser.parse_args()

    include = options.include.split(',')
    exclude = options.exclude.split(',')
