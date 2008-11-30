# Natural Language Toolkit: Generating RDF Triples from NL Relations
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This code shows how relational information extracted from text 
can be converted into an RDF Graph.
"""

from nltk.sem.relextract import relextract, class_abbrev
from string import join
import re
from rdflib import Namespace, ConjunctiveGraph

BASE = "http://nltk.org/terms/"
RDFNS = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
RDFSNS = Namespace('http://www.w3.org/2000/01/rdf-schema#')

def make_rdf(ns, reldict, relsym=None, verbose=False):
    """
    Convert a reldict into an RDF triple.
    """
    subject = sym2uri(ns, reldict['subjclass'], reldict['subjsym'])
    predicate = sym2uri(ns, 'pred', relsym)
    object = sym2uri(ns, reldict['objclass'], reldict['objsym'])
    triple = (subject, predicate, object)
    if verbose:
        print triple
    return triple

def make_rdfs(ns, reldict):
    """
    Convert a reldict into a lst of RDFS type statements.
    """
    triples = []
    predicate = RDFNS.type
    i1 = sym2uri(ns, reldict['subjclass'], reldict['subjsym'])
    t1 = sym2uri(ns, 'class', reldict['subjclass'].title())
    i2 = sym2uri(ns, reldict['objclass'], reldict['objsym'])
    t2 = sym2uri(ns, 'class', reldict['objclass'].title())
    triples += [(i1, predicate, t1), (i2, predicate, t2)]
    return triples 
    
def sym2uri(base, rdfclass, sym):
    """
    Build a URI out of a base, a class term, and a symbol.
    """
    from urllib import quote
    from rdflib import Namespace
    rdfclass = class_abbrev(rdfclass)
    rdfclass = rdfclass.lower()
    ns = Namespace(base)
    sym = quote(sym)
    local = '%s#%s' % (rdfclass, sym)
    return ns[local]


def rels2rdf(ns, verbose=False):
    """
    Convert the reldicts derived from the IEER corpus in an RDF Graph.
    """
    graph = ConjunctiveGraph()
    graph.bind('nltk',BASE)
    graph.bind('org', "http://nltk.org/terms/org#")
    graph.bind('loc', "http://nltk.org/terms/loc#")
    graph.bind('pred', "http://nltk.org/terms/pred#")
    graph.bind('class', "http://nltk.org/terms/class#")
    in_uri = sym2uri(ns, 'pred', 'in')
    loc_uri = sym2uri(ns, 'class', 'Location')
    org_uri = sym2uri(ns, 'class', 'Organization')
    graph.add((in_uri, RDFNS.type, RDFSNS.Property))
    graph.add((loc_uri, RDFNS.type, RDFSNS.Class))
    graph.add((org_uri, RDFNS.type, RDFSNS.Class))
    graph.add((in_uri, RDFSNS.domain, org_uri))
    graph.add((in_uri, RDFSNS.range, loc_uri))
    from nltk.corpus import ieer
    IN = re.compile(r'.*\bin\b(?!\b.+ing\b)')
    for item in ieer.items:
        for doc in ieer.parsed_docs(item):
            for reldict in relextract('ORG', 'LOC', doc, pattern=IN):
                graph.add(make_rdf(ns, reldict, relsym='in'))
                for triple in make_rdfs(ns, reldict):
                    graph.add(triple)
    return graph

def demo():
    graph = rels2rdf(BASE)
    print graph.serialize(format='turtle')

if __name__ == '__main__':
    demo()




