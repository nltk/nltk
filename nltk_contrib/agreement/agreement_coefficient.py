# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
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

    def __init__(self,data=None,distance=binary,verbose=0):
        """Initialize an empty annotation task.

        """
        self.verbose = verbose
        self.distance = distance
        self.I = set()
        self.K = set()
        self.C = set()
        self.data = []
        if(data!=None):
            self.load_array(data)

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
        ret = 1.0 - float(self.distance(kA['labels'],kB['labels']))
        if(self.verbose>1):
            print "Observed agreement between %s and %s on %s: %f"%(cA,cB,i,ret)
            print "Distance between \"%s\" and \"%s\": %f"%(",".join(kA['labels']),",".join(kB['labels']),1.0 - ret)
        return ret

    def N(self,k="",i="",c=""):
        """Implements the "n-notation" used in Artstein and Poesio (2007)

        """
        if(k!="" and i=="" and c==""):
            ret = len(filter(lambda x:k==x['labels'],self.data))
        elif(k!="" and i!="" and c==""):
            ret = len(filter(lambda x:k==x['labels'] and i==x['item'],self.data))
        elif(k!="" and c!="" and i==""):
            ret = len(filter(lambda x:k==x['labels'] and c==x['coder'],self.data))
        else:
            print "You must pass either i or c, not both!"
        if(self.verbose>1):
            print "Count on N[%s,%s,%s]: %d"%(k,i,c,ret)
        return float(ret)

    def Ao(self,cA,cB):
        """Observed agreement between two coders on all items.

        """
        ret = float(sum(map(lambda x:self.agr(cA,cB,x),self.I)))/float(len(self.I))
        if(self.verbose>0):
            print "Observed agreement between %s and %s: %f"%(cA,cB,ret)
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
                total += self.Ao(cA,cB)
                counter += 1.0
        ret = total/counter
        if(self.verbose>0):
            print "Average observed agreement: %f"%(ret)
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
                    total += float(self.N(i=i,k=j)*self.N(i=i,k=l))*self.distance(l,j)
        ret = (1.0/float((len(self.I)*len(self.C)*(len(self.C)-1))))*total
        if(self.verbose>0):
            print "Observed disagreement: %f"%(ret)
        return ret

    def Do_Kw_pairwise(self,cA,cB,max_distance=1.0):
        """The observed disagreement for the weighted kappa coefficient.

        """
        total = 0.0
        for i in self.I:
            total += self.distance(filter(lambda x:x['coder']==cA and x['item']==i,self.data)[0]['labels'],filter(lambda x:x['coder']==cB and x['item']==i,self.data)[0]['labels'])
        ret = total/(len(self.I)*max_distance)
        if(self.verbose>0):
            print "Observed disagreement between %s and %s: %f"%(cA,cB,ret)
        return ret

    def Do_Kw(self,max_distance=1.0):
        """Averaged over all labelers
        
        """
        vals = {}
        for cA in self.C:
            for cB in self.C:
                if(not frozenset([cA,cB]) in vals.keys() and not cA==cB):
                    vals[frozenset([cA,cB])] = self.Do_Kw_pairwise(cA,cB,max_distance)
        ret = sum(vals.values())/len(vals)
        if(self.verbose>0):
            print "Observed disagreement: %f"%(ret)
        return ret

    # Agreement Coefficients
    def S(self):
        """Bennett, Albert and Goldstein 1954

        """
        Ae = 1.0/float(len(self.K))        
        ret = (self.avg_Ao() - Ae)/(1.0 - Ae)
        return ret

    def pi(self):
        """Scott 1955

        """
        total = 0.0
        for k in self.K:
            total += self.N(k=k)**2
        Ae = (1.0/(4.0*float(len(self.I)**2)))*total
        ret = (self.avg_Ao()-Ae)/(1-Ae)
        return ret

    def pi_avg(self):
        pass

    def kappa_pairwise(self,cA,cB):
        """

        """
        Ae = 0.0
        for k in self.K:
            Ae += (float(self.N(c=cA,k=k))/float(len(self.I))) * (float(self.N(c=cB,k=k))/float(len(self.I)))
        ret = (self.Ao(cA,cB)-Ae)/(1.0-Ae)
        if(self.verbose>0):
            print "Expected agreement between %s and %s: %f"%(cA,cB,Ae)
            print "Kappa between %s and %s: %f"%(cA,cB,ret)
        return ret

    def kappa(self):
        """Cohen 1960

        """
        vals = {}
        for a in self.C:
            for b in self.C:
                if(a==b or "%s%s"%(b,a) in vals):
                    continue
                vals["%s%s"%(a,b)] = self.kappa_pairwise(a,b)
        ret = sum(vals.values())/float(len(vals))
        return ret

    def alpha(self):
        """Krippendorff 1980

        """
        De = 0.0
        for j in self.K:
            for l in self.K:
                De += float(self.N(k=j)*self.N(k=l))*self.distance(j,l)
        De = (1.0/(len(self.I)*len(self.C)*(len(self.I)*len(self.C)-1)))*De
        if(self.verbose>0):
            print "Expected disagreement: %f"%(De)
        ret = 1.0 - (self.Do_alpha()/De)
        return ret

    def weighted_kappa_pairwise(self,cA,cB,max_distance=1.0):
        """Cohen 1968

        """
        total = 0.0
        for j in self.K:
            for l in self.K:
                total += self.N(c=cA,k=j)*self.N(c=cB,k=l)*self.distance(j,l)
        De = total/(max_distance*pow(len(self.I),2))
        Do = self.Do_Kw()
        return 1.0 - (Do/De)

    def weighted_kappa(self):
        """Cohen 1968

        """
        vals = {}
        for a in self.C:
            for b in self.C:
                if(a==b or "%s%s"%(b,a) in vals):
                    continue
                vals["%s%s"%(a,b)] = self.weighted_kappa_pairwise(a,b)
        ret = sum(vals.values())/float(len(vals))
        return ret

if(__name__=='__main__'):

    import re
    import optparse
    import distance_metric

    # process command-line arguments
    parser = optparse.OptionParser()
    parser.add_option("-d","--distance",dest="distance",default="binary",help="distance metric to use")
    parser.add_option("-a","--agreement",dest="agreement",default="kappa",help="agreement coefficient to calculate")
    parser.add_option("-e","--exclude",dest="exclude",action="append",default=[],help="coder names to exclude (comma-separated), e.g. jane,mike")
    parser.add_option("-i","--include",dest="include",action="append",default=[],help="coder names to include, same format as exclude")
    parser.add_option("-f","--file",dest="file",help="file to read labelings from, each line with three columns: 'labeler item labels'")
    parser.add_option("-v","--verbose",dest="verbose",default=0,help="print debugging to stderr?")
    parser.add_option("-c","--columnsep",dest="columnsep",default="\t",help="char/string that separates the three columns in the file, defaults to tab")
    parser.add_option("-l","--labelsep",dest="labelsep",default=",",help="char/string that separates labels (if labelers can assign more than one), defaults to comma")
    parser.add_option("-p","--presence",dest="presence",default=None,help="convert each labeling into 1 or 0, based on presence of LABEL")
    (options,remainder) = parser.parse_args()

    # read in data from the specified file
    data = []
    for l in open(options.file):
        toks = l.split(options.columnsep)
        coder,object,labels = toks[0],str(toks[1:-1]),frozenset(toks[-1].strip().split(options.labelsep))
        if((options.include==options.exclude) or (len(options.include)>0 and coder in options.include) or (len(options.exclude)>0 and coder not in options.exclude)):
            data.append((coder,object,labels))

    if(options.presence):
        task = AnnotationTask(data,getattr(distance_metric,options.distance)(options.presence),int(options.verbose))
    else:
        task = AnnotationTask(data,getattr(distance_metric,options.distance),int(options.verbose))
    print getattr(task,options.agreement)()
