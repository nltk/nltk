# Natural Language Toolkit: Lexical Functional Grammar
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2014 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
from __future__ import print_function, division, unicode_literals

from nltk.internals import Counter
from nltk.compat import python_2_unicode_compatible

@python_2_unicode_compatible
class FStructure(dict):
    def safeappend(self, key, item):
        """
        Append 'item' to the list at 'key'.  If no list exists for 'key', then
        construct one.
        """
        if key not in self:
            self[key] = []
        self[key].append(item)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)

    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())

    def __contains__(self, key):
        return dict.__contains__(self, key.lower())

    def to_glueformula_list(self, glue_dict):
        depgraph = self.to_depgraph()
        return glue_dict.to_glueformula_list(depgraph)

    def to_depgraph(self, rel=None):
        from nltk.parse.dependencygraph import DependencyGraph
        depgraph = DependencyGraph()
        nodelist = depgraph.nodelist

        self._to_depgraph(nodelist, 0, 'ROOT')

        #Add all the dependencies for all the nodes
        for node_addr, node in enumerate(nodelist):
            for n2 in nodelist[1:]:
                if n2['head'] == node_addr:
                    node['deps'].append(n2['address'])

        depgraph.root = nodelist[1]

        return depgraph

    def _to_depgraph(self, nodelist, head, rel):
        index = len(nodelist)

        nodelist.append({'address': index,
                         'word': self.pred[0],
                         'tag': self.pred[1],
                         'head': head,
                         'rel': rel,
                         'deps': []})

        for feature in self:
            for item in self[feature]:
                if isinstance(item, FStructure):
                    item._to_depgraph(nodelist, index, feature)
                elif isinstance(item, tuple):
                    nodelist.append({'address': len(nodelist),
                                     'word': item[0],
                                     'tag': item[1],
                                     'head': index,
                                     'rel': feature,
                                     'deps': []})
                elif isinstance(item, list):
                    for n in item:
                        n._to_depgraph(nodelist, index, feature)
                else: # ERROR
                    raise Exception('feature %s is not an FStruct, a list, or a tuple' % feature)

    @staticmethod
    def read_depgraph(depgraph):
        return FStructure._read_depgraph(depgraph.root, depgraph)

    @staticmethod
    def _read_depgraph(node, depgraph, label_counter=None, parent=None):
        if not label_counter:
            label_counter = Counter()

        if node['rel'].lower() in ['spec', 'punct']:
            # the value of a 'spec' entry is a word, not an FStructure
            return (node['word'], node['tag'])

        else:
            fstruct = FStructure()
            fstruct.pred = None
            fstruct.label = FStructure._make_label(label_counter.get())

            fstruct.parent = parent

            word, tag = node['word'], node['tag']
            if tag[:2] == 'VB':
                if tag[2:3] == 'D':
                    fstruct.safeappend('tense', ('PAST', 'tense'))
                fstruct.pred = (word, tag[:2])

            if not fstruct.pred:
                fstruct.pred = (word, tag)

            children = [depgraph.nodelist[idx] for idx in node['deps']]
            for child in children:
                fstruct.safeappend(child['rel'], FStructure._read_depgraph(child, depgraph, label_counter, fstruct))

            return fstruct

    @staticmethod
    def _make_label(value):
        """
        Pick an alphabetic character as identifier for an entity in the model.

        :param value: where to index into the list of characters
        :type value: int
        """
        letter = ['f','g','h','i','j','k','l','m','n','o','p','q','r','s',
                  't','u','v','w','x','y','z','a','b','c','d','e'][value-1]
        num = int(value) // 26
        if num > 0:
            return letter + str(num)
        else:
            return letter

    def __repr__(self):
        return self.__unicode__().replace('\n', '')

    def __str__(self):
        return self.pprint()

    def pprint(self, indent=3):
        try:
            accum = '%s:[' % self.label
        except NameError:
            accum = '['
        try:
            accum += 'pred \'%s\'' % (self.pred[0])
        except NameError:
            pass

        for feature in sorted(self):
            for item in self[feature]:
                if isinstance(item, FStructure):
                    next_indent = indent+len(feature)+3+len(self.label)
                    accum += '\n%s%s %s' % (' '*(indent), feature, item.pprint(next_indent))
                elif isinstance(item, tuple):
                    accum += '\n%s%s \'%s\'' % (' '*(indent), feature, item[0])
                elif isinstance(item, list):
                    accum += '\n%s%s {%s}' % (' '*(indent), feature, ('\n%s' % (' '*(indent+len(feature)+2))).join(item))
                else: # ERROR
                    raise Exception('feature %s is not an FStruct, a list, or a tuple' % feature)
        return accum+']'



def demo_read_depgraph():
    from nltk.parse.dependencygraph import DependencyGraph
    dg1 = DependencyGraph("""\
Esso       NNP     2       SUB
said       VBD     0       ROOT
the        DT      5       NMOD
Whiting    NNP     5       NMOD
field      NN      6       SUB
started    VBD     2       VMOD
production NN      6       OBJ
Tuesday    NNP     6       VMOD
""")
    dg2 = DependencyGraph("""\
John    NNP     2       SUB
sees    VBP     0       ROOT
Mary    NNP     2       OBJ
""")
    dg3 = DependencyGraph("""\
a       DT      2       SPEC
man     NN      3       SUBJ
walks   VB      0       ROOT
""")
    dg4 = DependencyGraph("""\
every   DT      2       SPEC
girl    NN      3       SUBJ
chases  VB      0       ROOT
a       DT      5       SPEC
dog     NN      3       OBJ
""")

    depgraphs = [dg1,dg2,dg3,dg4]
    for dg in depgraphs:
        print(FStructure.read_depgraph(dg))

if __name__ == '__main__':
    demo_read_depgraph()

