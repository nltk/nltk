# Natural Language Toolkit: Dependency Trees
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tools for reading and writing dependency trees.
The input is assumed to be in U{Malt-TAB<http://w3.msi.vxu.se/~nivre/research/MaltXML.html>} format.

Currently only reads the first tree in a file.
"""

from nltk.parse import Tree
from pprint import pformat
import re


class DepGraph(object):
    """
    A container for the nodes and labelled edges of a dependency structure.
    """
    def __init__(self):
        """
        We place a dummy 'top' node in the first position 
        in the nodelist, since the root node is often assigned '0'
        as its head. This also means that the indexing of the nodelist
        corresponds directly to the Malt-TAB format, which starts at 1.
        """
        top = {'word':None, 'deps':[], 'rel': 'TOP'}
        self.nodelist = [top]
        self.root = None
        self.stream = None

    def __str__(self):
#        return '\n'.join([str(n) for n in self.nodelist])
        return '\n'.join([', '.join(['%s: %15s'%item for item in n.iteritems()]) for n in self.nodelist])
                        
    def load(self, file):
        """
        @param file: a file in Malt-TAB format
        """
        input = open(file).read()
        return self.read(input)
    
    def _normalize(self, line):
        """
        Deal with lines in which spaces are used rather than tabs.
        """
        import re
        SPC = re.compile(' +')
        return re.sub(SPC, '\t', line)

    def read(self, input):
        """
        @param input: a string in Malt-TAB format
        """
        lines = input.split('\n')
        count = 1
        temp = []
    
        for line in lines:
            line = self._normalize(line)
            node = {}
            try:
                (word, tag, head, rel) = line.split('\t')
                head = int(head)
                #not required, but useful for inspection
                node['address'] = count        
                node['word'] = word
                node['tag'] = tag
                node['head'] = head
                node['rel']= rel
                node['deps'] = []
                self.nodelist.append(node)
                
                for (dep, hd) in temp:
                    #check whether I'm the head for a node with address dep
                    if hd == count:
                        #add dep to my list of dependents
                        node['deps'].append(dep)
                try:
                    #try to add my address to my head's dependents list
                    self.nodelist[head]['deps'].append(count)
                except IndexError:
                    #my head hasn't been seen yet, so store the info
                    temp.append((count, head))
                            
                count += 1
                
            except ValueError:
                break
                
        root_address = self.nodelist[0]['deps'][0]
        self.root = self.nodelist[root_address]
        return self

    def _word(self, node, filter=True):
        w = node['word']
        if filter:
            if w != ',': return w
        return w

    def _deptree(self, i):
        """
        Recursive function for turning dependency graphs into
        NLTK trees.
        @type i: C{int}
        @param i: index of a node in C{nodelist}
        @return: either a word (if the indexed node 
        is a leaf) or a L{Tree}.
        """

        node = self.nodelist[i]
        word = node['word']
        deps = node['deps']

        if len(deps) == 0:
            return word
        else:
            return Tree(word, [self._deptree(j) for j in deps])

            
    def deptree(self):
        """
        Starting with the C{root} node, build a dependency tree using the NLTK 
        L{Tree} constructor. Dependency labels are omitted.
        """
        node = self.root
        word = node['word']
        deps = node['deps']

        return Tree(word, [self._deptree(i) for i in deps])
    
    def _hd(self, i):
        try:
            return self.nodelist[i]['head']
        except IndexError:
            return None
        
    def _rel(self, i):
        try:
            return self.nodelist[i]['rel']
        except IndexError:
            return None
    
    def nx_graph(self):
        """
        Convert the data in a C{nodelist} into a networkx 
        labeled directed graph.
        @rtype: C{XDigraph}
        """
        nx_nodelist = range(1, len(self.nodelist))
        nx_edgelist = [(n, self._hd(n), self._rel(n)) 
                        for n in nx_nodelist if self._hd(n)]
        self.nx_labels = {}
        for n in nx_nodelist:
            self.nx_labels[n] = self.nodelist[n]['word']
        
        g = NX.XDiGraph()
        g.add_nodes_from(nx_nodelist)
        g.add_edges_from(nx_edgelist)
        
        return g
        


def demo(nx=False):
    """
    A demonstration of the result of reading a dependency
    version of the first sentence of the Penn Treebank.
    """
    dg = DepGraph().read("""Pierre  NNP     2       NMOD
Vinken  NNP     8       SUB
,       ,       2       P
61      CD      5       NMOD
years   NNS     6       AMOD
old     JJ      2       NMOD
,       ,       2       P
will    MD      0       ROOT
join    VB      8       VC
the     DT      11      NMOD
board   NN      9       OBJ
as      IN      9       VMOD
a       DT      15      NMOD
nonexecutive    JJ      15      NMOD
director        NN      12      PMOD
Nov.    NNP     9       VMOD
29      CD      16      NMOD
.       .       9       VMOD
""")
    tree = dg.deptree()
    print tree.pprint()
    if nx:
        #currently doesn't work
        try:
            import networkx as NX
            import pylab as P
        except ImportError:
            raise
            g = dg.nx_graph()
        g.info()
        pos = NX.spring_layout(g, dim=1)
        NX.draw_networkx_nodes(g, pos, node_size=50)
        #NX.draw_networkx_edges(g, pos, edge_color='k', width=8)
        NX.draw_networkx_labels(g, pos, dg.nx_labels)
        P.xticks([])
        P.yticks([])
        P.savefig('deptree.png')
        P.show()

if __name__ == '__main__':
    demo()

    
