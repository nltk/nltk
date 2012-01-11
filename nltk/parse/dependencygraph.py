# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Jason Narad <jason.narad@gmail.com>
#         Steven Bird <sb@csse.unimelb.edu.au> (modifications)
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Tools for reading and writing dependency trees.
The input is assumed to be in Malt-TAB format
(http://w3.msi.vxu.se/~nivre/research/MaltXML.html).
Currently only reads the first tree in a file.
"""

from nltk.tree import Tree
from pprint import pformat
import re

#################################################################
# DependencyGraph Class
#################################################################

class DependencyGraph(object):
    """
    A container for the nodes and labelled edges of a dependency structure.
    """
    def __init__(self, tree_str=None):
        """
        We place a dummy 'top' node in the first position
        in the nodelist, since the root node is often assigned '0'
        as its head. This also means that the indexing of the nodelist
        corresponds directly to the Malt-TAB format, which starts at 1.
        """
        top = {'word':None, 'deps':[], 'rel': 'TOP', 'tag': 'TOP', 'address': 0}
        self.nodelist = [top]
        self.root = None
        self.stream = None
        if tree_str:
            self._parse(tree_str)

    def remove_by_address(self, address):
        """
        Removes the node with the given address.  References
        to this node in others will still exist.
        """
        node_index = len(self.nodelist) - 1
        while(node_index >= 0):
            node = self.nodelist[node_index]
            if node['address'] == address:
                self.nodelist.pop(node_index)
            node_index -= 1

    def redirect_arcs(self, originals, redirect):
        """
        Redirects arcs to any of the nodes in the originals list
        to the redirect node address.
        """
        for node in self.nodelist:
            new_deps = []
            for dep in node['deps']:
                if dep in originals:
                    new_deps.append(redirect)
                else:
                    new_deps.append(dep)
            node['deps'] = new_deps

    def add_arc(self, head_address, mod_address):
        """
        Adds an arc from the node specified by head_address to the
        node specified by the mod address.
        """
        for node in self.nodelist:
            if node['address'] == head_address and (mod_address not in node['deps']):
                node['deps'].append(mod_address)

    def connect_graph(self):
        """
        Fully connects all non-root nodes.  All nodes are set to be dependents
        of the root node.
        """
        for node1 in self.nodelist:
            for node2 in self.nodelist:
                if node1['address'] != node2['address'] and node2['rel'] != 'TOP':
                    node1['deps'].append(node2['address'])

    # fix error and return
    def get_by_address(self, node_address):
        """
        Returns the node with the given address.
        """
        for node in self.nodelist:
            if node['address'] == node_address:
                return node
        print 'THROW ERROR: address not found in -get_by_address-'
        return -1

    def contains_address(self, node_address):
        """
        Returns true if the graph contains a node with the given node
        address, false otherwise.
        """
        for node in self.nodelist:
            if node['address'] == node_address:
                return True
        return False

    def __str__(self):
        return pformat(self.nodelist)

    def __repr__(self):
        return "<DependencyGraph with %d nodes>" % len(self.nodelist)

    @staticmethod
    def load(file):
        """
        :param file: a file in Malt-TAB format
        """
        return DependencyGraph(open(file).read())

    @staticmethod
    def _normalize(line):
        """
        Deal with lines in which spaces are used rather than tabs.
        """
        SPC = re.compile(' +')
        return re.sub(SPC, '\t', line).strip()

    def left_children(self, node_index):
        """
        Returns the number of left children under the node specified
        by the given address.
        """
        children = self.nodelist[node_index]['deps']
        index = self.nodelist[node_index]['address']
        return sum(1 for c in children if c < index)

    def right_children(self, node_index):
        """
        Returns the number of right children under the node specified
        by the given address.
        """
        children = self.nodelist[node_index]['deps']
        index = self.nodelist[node_index]['address']
        return sum(1 for c in children if c > index)

    def add_node(self, node):
        if not self.contains_address(node['address']):
            self.nodelist.append(node)

    def _parse(self, input):
        lines = [DependencyGraph._normalize(line) for line in input.split('\n') if line.strip()]
        temp = []
        for index, line in enumerate(lines):
#           print line
            try:
                cells = line.split('\t')
                nrCells = len(cells)
                if nrCells == 3:
                    word, tag, head = cells
                    rel = ''
                elif nrCells == 4:
                    word, tag, head, rel = cells
                elif nrCells == 10:
                    _, word, _, _, tag, _, head, rel, _, _ = cells
                else:
                    raise ValueError('Number of tab-delimited fields (%d) not supported by CoNLL(10) or Malt-Tab(4) format' % (nrCells))

                head = int(head)
                self.nodelist.append({'address': index+1, 'word': word, 'tag': tag,
                                      'head': head, 'rel': rel,
                                      'deps': [d for (d,h) in temp if h == index+1]})

                try:
                    self.nodelist[head]['deps'].append(index+1)
                except IndexError:
                    temp.append((index+1, head))

            except ValueError:
                break

        root_address = self.nodelist[0]['deps'][0]
        self.root = self.nodelist[root_address]

    def _word(self, node, filter=True):
        w = node['word']
        if filter:
            if w != ',': return w
        return w

    def _tree(self, i):
        """
        Recursive function for turning dependency graphs into
        NLTK trees.
        :type i: int
        :param i: index of a node in ``nodelist``
        :return: either a word (if the indexed node
        is a leaf) or a ``Tree``.
        """

        node = self.get_by_address(i)
        word = node['word']
        deps = node['deps']

        if len(deps) == 0:
            return word
        else:
            return Tree(word, [self._tree(j) for j in deps])


    def tree(self):
        """
        Starting with the ``root`` node, build a dependency tree using the NLTK
        ``Tree`` constructor. Dependency labels are omitted.
        """
        node = self.root
        word = node['word']
        deps = node['deps']
        return Tree(word, [self._tree(i) for i in deps])

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

    # what's the return type?  Boolean or list?
    def contains_cycle(self):
        distances = {}
        for node in self.nodelist:
            for dep in node['deps']:
                key = tuple([node['address'], dep]) #'%d -> %d' % (node['address'], dep)
                distances[key] = 1
        window = 0
        for n in range(len(self.nodelist)):
            new_entries = {}
            for pair1 in distances:
                for pair2 in distances:
                    if pair1[1] == pair2[0]:
                        key = tuple([pair1[0], pair2[1]])
                        new_entries[key] = distances[pair1] + distances[pair2]
            for pair in new_entries:
                distances[pair] = new_entries[pair]
                if pair[0] == pair[1]:
                    print pair[0]
                    path = self.get_cycle_path(self.get_by_address(pair[0]), pair[0]) #self.nodelist[pair[0]], pair[0])
                    return path
        return False  # return []?


    def get_cycle_path(self, curr_node, goal_node_index):
        for dep in curr_node['deps']:
            if dep == goal_node_index:
                return [curr_node['address']]
        for dep in curr_node['deps']:
            path = self.get_cycle_path(self.get_by_address(dep), goal_node_index)#self.nodelist[dep], goal_node_index)
            if len(path) > 0:
                path.insert(0, curr_node['address'])
                return path
        return []

    def to_conll(self, style):
        """
        The dependency graph in CoNLL format.

        :param style: the style to use for the format (3, 4, 10 columns)
        :type style: int
        :rtype: str
        """

        lines = []
        for i, node in enumerate(self.nodelist[1:]):
            word, tag, head, rel = node['word'], node['tag'], node['head'], node['rel']
            if style == 3:
                lines.append('%s\t%s\t%s\n' % (word, tag, head))
            elif style == 4:
                lines.append('%s\t%s\t%s\t%s\n' % (word, tag, head, rel))
            elif style == 10:
                lines.append('%s\t%s\t_\t%s\t%s\t_\t%s\t%s\t_\t_\n' % (i+1, word, tag, tag, head, rel))
            else:
                raise ValueError('Number of tab-delimited fields (%d) not supported by CoNLL(10) or Malt-Tab(4) format' % (style))
        return ''.join(lines)


def nx_graph(self):
    """
    Convert the data in a ``nodelist`` into a networkx
    labeled directed graph.
    :rtype: XDigraph
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

def demo():
    malt_demo()
    conll_demo()
    conll_file_demo()
    cycle_finding_demo()

def malt_demo(nx=False):
    """
    A demonstration of the result of reading a dependency
    version of the first sentence of the Penn Treebank.
    """
    dg = DependencyGraph("""Pierre  NNP     2       NMOD
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
    tree = dg.tree()
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
        P.savefig('tree.png')
        P.show()


def conll_demo():
    """
    A demonstration of how to read a string representation of
    a CoNLL format dependency tree.
    """
    dg = DependencyGraph(conll_data1)
    tree = dg.tree()
    print tree.pprint()
    print dg
    print dg.to_conll(4)

def conll_file_demo():
    print 'Mass conll_read demo...'
    graphs = [DependencyGraph(entry)
              for entry in conll_data2.split('\n\n') if entry]
    for graph in graphs:
        tree = graph.tree()
        print '\n' + tree.pprint()

def cycle_finding_demo():
    dg = DependencyGraph(treebank_data)
    print dg.contains_cycle()
    cyclic_dg = DependencyGraph()
    top =    {'word':None, 'deps':[1], 'rel': 'TOP', 'address': 0}
    child1 = {'word':None, 'deps':[2], 'rel': 'NTOP', 'address': 1}
    child2 = {'word':None, 'deps':[4], 'rel': 'NTOP', 'address': 2}
    child3 = {'word':None, 'deps':[1], 'rel': 'NTOP', 'address': 3}
    child4 = {'word':None, 'deps':[3], 'rel': 'NTOP', 'address': 4}
    cyclic_dg.nodelist = [top, child1, child2, child3, child4]
    cyclic_dg.root = top
    print cyclic_dg.contains_cycle()

treebank_data = """Pierre  NNP     2       NMOD
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
"""

conll_data1 = """
1   Ze                ze                Pron  Pron  per|3|evofmv|nom                 2   su      _  _
2   had               heb               V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
3   met               met               Prep  Prep  voor                             8   mod     _  _
4   haar              haar              Pron  Pron  bez|3|ev|neut|attr               5   det     _  _
5   moeder            moeder            N     N     soort|ev|neut                    3   obj1    _  _
6   kunnen            kan               V     V     hulp|ott|1of2of3|mv              2   vc      _  _
7   gaan              ga                V     V     hulp|inf                         6   vc      _  _
8   winkelen          winkel            V     V     intrans|inf                      11  cnj     _  _
9   ,                 ,                 Punc  Punc  komma                            8   punct   _  _
10  zwemmen           zwem              V     V     intrans|inf                      11  cnj     _  _
11  of                of                Conj  Conj  neven                            7   vc      _  _
12  terrassen         terras            N     N     soort|mv|neut                    11  cnj     _  _
13  .                 .                 Punc  Punc  punt                             12  punct   _  _
"""

conll_data2 = """1   Cathy             Cathy             N     N     eigen|ev|neut                    2   su      _  _
2   zag               zie               V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
3   hen               hen               Pron  Pron  per|3|mv|datofacc                2   obj1    _  _
4   wild              wild              Adj   Adj   attr|stell|onverv                5   mod     _  _
5   zwaaien           zwaai             N     N     soort|mv|neut                    2   vc      _  _
6   .                 .                 Punc  Punc  punt                             5   punct   _  _

1   Ze                ze                Pron  Pron  per|3|evofmv|nom                 2   su      _  _
2   had               heb               V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
3   met               met               Prep  Prep  voor                             8   mod     _  _
4   haar              haar              Pron  Pron  bez|3|ev|neut|attr               5   det     _  _
5   moeder            moeder            N     N     soort|ev|neut                    3   obj1    _  _
6   kunnen            kan               V     V     hulp|ott|1of2of3|mv              2   vc      _  _
7   gaan              ga                V     V     hulp|inf                         6   vc      _  _
8   winkelen          winkel            V     V     intrans|inf                      11  cnj     _  _
9   ,                 ,                 Punc  Punc  komma                            8   punct   _  _
10  zwemmen           zwem              V     V     intrans|inf                      11  cnj     _  _
11  of                of                Conj  Conj  neven                            7   vc      _  _
12  terrassen         terras            N     N     soort|mv|neut                    11  cnj     _  _
13  .                 .                 Punc  Punc  punt                             12  punct   _  _

1   Dat               dat               Pron  Pron  aanw|neut|attr                   2   det     _  _
2   werkwoord         werkwoord         N     N     soort|ev|neut                    6   obj1    _  _
3   had               heb               V     V     hulp|ovt|1of2of3|ev              0   ROOT    _  _
4   ze                ze                Pron  Pron  per|3|evofmv|nom                 6   su      _  _
5   zelf              zelf              Pron  Pron  aanw|neut|attr|wzelf             3   predm   _  _
6   uitgevonden       vind              V     V     trans|verldw|onverv              3   vc      _  _
7   .                 .                 Punc  Punc  punt                             6   punct   _  _

1   Het               het               Pron  Pron  onbep|neut|zelfst                2   su      _  _
2   hoorde            hoor              V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
3   bij               bij               Prep  Prep  voor                             2   ld      _  _
4   de                de                Art   Art   bep|zijdofmv|neut                6   det     _  _
5   warme             warm              Adj   Adj   attr|stell|vervneut              6   mod     _  _
6   zomerdag          zomerdag          N     N     soort|ev|neut                    3   obj1    _  _
7   die               die               Pron  Pron  betr|neut|zelfst                 6   mod     _  _
8   ze                ze                Pron  Pron  per|3|evofmv|nom                 12  su      _  _
9   ginds             ginds             Adv   Adv   gew|aanw                         12  mod     _  _
10  achter            achter            Adv   Adv   gew|geenfunc|stell|onverv        12  svp     _  _
11  had               heb               V     V     hulp|ovt|1of2of3|ev              7   body    _  _
12  gelaten           laat              V     V     trans|verldw|onverv              11  vc      _  _
13  .                 .                 Punc  Punc  punt                             12  punct   _  _

1   Ze                ze                Pron  Pron  per|3|evofmv|nom                 2   su      _  _
2   hadden            heb               V     V     trans|ovt|1of2of3|mv             0   ROOT    _  _
3   languit           languit           Adv   Adv   gew|geenfunc|stell|onverv        11  mod     _  _
4   naast             naast             Prep  Prep  voor                             11  mod     _  _
5   elkaar            elkaar            Pron  Pron  rec|neut                         4   obj1    _  _
6   op                op                Prep  Prep  voor                             11  ld      _  _
7   de                de                Art   Art   bep|zijdofmv|neut                8   det     _  _
8   strandstoelen     strandstoel       N     N     soort|mv|neut                    6   obj1    _  _
9   kunnen            kan               V     V     hulp|inf                         2   vc      _  _
10  gaan              ga                V     V     hulp|inf                         9   vc      _  _
11  liggen            lig               V     V     intrans|inf                      10  vc      _  _
12  .                 .                 Punc  Punc  punt                             11  punct   _  _

1   Zij               zij               Pron  Pron  per|3|evofmv|nom                 2   su      _  _
2   zou               zal               V     V     hulp|ovt|1of2of3|ev              7   cnj     _  _
3   mams              mams              N     N     soort|ev|neut                    4   det     _  _
4   rug               rug               N     N     soort|ev|neut                    5   obj1    _  _
5   ingewreven        wrijf             V     V     trans|verldw|onverv              6   vc      _  _
6   hebben            heb               V     V     hulp|inf                         2   vc      _  _
7   en                en                Conj  Conj  neven                            0   ROOT    _  _
8   mam               mam               V     V     trans|ovt|1of2of3|ev             7   cnj     _  _
9   de                de                Art   Art   bep|zijdofmv|neut                10  det     _  _
10  hare              hare              Pron  Pron  bez|3|ev|neut|attr               8   obj1    _  _
11  .                 .                 Punc  Punc  punt                             10  punct   _  _

1   Of                of                Conj  Conj  onder|metfin                     0   ROOT    _  _
2   ze                ze                Pron  Pron  per|3|evofmv|nom                 3   su      _  _
3   had               heb               V     V     hulp|ovt|1of2of3|ev              0   ROOT    _  _
4   gewoon            gewoon            Adj   Adj   adv|stell|onverv                 10  mod     _  _
5   met               met               Prep  Prep  voor                             10  mod     _  _
6   haar              haar              Pron  Pron  bez|3|ev|neut|attr               7   det     _  _
7   vriendinnen       vriendin          N     N     soort|mv|neut                    5   obj1    _  _
8   rond              rond              Adv   Adv   deelv                            10  svp     _  _
9   kunnen            kan               V     V     hulp|inf                         3   vc      _  _
10  slenteren         slenter           V     V     intrans|inf                      9   vc      _  _
11  in                in                Prep  Prep  voor                             10  mod     _  _
12  de                de                Art   Art   bep|zijdofmv|neut                13  det     _  _
13  buurt             buurt             N     N     soort|ev|neut                    11  obj1    _  _
14  van               van               Prep  Prep  voor                             13  mod     _  _
15  Trafalgar_Square  Trafalgar_Square  MWU   N_N   eigen|ev|neut_eigen|ev|neut      14  obj1    _  _
16  .                 .                 Punc  Punc  punt                             15  punct   _  _
"""

if __name__ == '__main__':
    demo()
