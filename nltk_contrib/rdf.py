# Natural Language Toolkit: Generating RDF Triples from NL Relations
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem.relextract import relextract, class_abbrev
from string import join
import re
from rdflib import Namespace, ConjunctiveGraph

NS = "http://nltk.org/terms/"

def make_rdf(ns, reldict, relsym=None, verbose=False):
    
    subject = urigen(ns, reldict['subjclass'], reldict['subjsym'])
    predicate = urigen(ns, 'preds', relsym)
    object = urigen(ns, reldict['objclass'], reldict['objsym'])
    triple = (subject, predicate, object)
    if verbose:
        print triple
    return triple
    
def urigen(base, rdfclass, sym):
    from urllib import quote
    from rdflib import Namespace
    rdfclass = class_abbrev(rdfclass)
    rdfclass = rdfclass.lower()
    ns = Namespace(base)
    sym = quote(sym.lower())
    local = '%s#%s' % (rdfclass, sym)
    return ns[local]


def rels2rdf(ns, verbose=False):
    graph = ConjunctiveGraph()
    graph.bind('nltk', NS)
    graph.bind('org', "http://nltk.org/terms/org#")
    graph.bind('loc', "http://nltk.org/terms/loc#")
    graph.bind('preds', "http://nltk.org/terms/preds#")
    
    from nltk.corpus import ieer
    IN = re.compile(r'.*\bin\b(?!\b.+ing\b)')
    for item in ieer.items:
        for doc in ieer.parsed_docs(item):
            for rel in relextract('ORG', 'LOC', doc, pattern=IN):
                graph.add(make_rdf(ns, rel, relsym='IN', verbose=verbose))
    return graph

def demo():
    graph = rels2rdf(NS)
    print graph.serialize(format='turtle')

if __name__ == '__main__':
    demo()




