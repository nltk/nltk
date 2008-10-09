# Natural Language Toolkit: Lexical Functional Grammar 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.internals import Counter
from nltk import defaultdict


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
        
    def to_glueformula_list(self, glue_dict, labels_added=[], current_subj=None, verbose=False):
        from nltk.tree import Tree
        glueformulas = []

        if not current_subj:
            current_subj = self

        # lookup 'pred'
        sem = self.pred[1]
        lookup = glue_dict.lookup(sem, self.pred[0], 'pred', current_subj, self)
        glueformulas.extend(lookup)

        for feature in self:
            for item in self[feature]:
                if isinstance(item, FStructure):
                    if not item.label in labels_added:
                        glueformulas.extend(item.to_glueformula_list(glue_dict, labels_added, self))
                        labels_added.append(item.label)
                elif isinstance(item, tuple):
                    glueformulas.extend(glue_dict.lookup(item[1], item[0], feature, None, self))
                elif isinstance(item, list):
                    for entry in item:
                        glueformulas.extend(entry.to_glueformula_list(glue_dict, labels_added))
                else:
                    raise Exception, 'feature %s is not an FStruct, a list, or a tuple' % feature

        return glueformulas

    def initialize_label(self, expression, counter=None):
        if not counter:
            counter = Counter()
        
        try:
            dot = expression.index('.')

            before_dot = expression[:dot]
            after_dot = expression[dot+1:]
            if before_dot=='super':
                return self.parent.initialize_label(after_dot)
            else:
                return self.lookup_unique(before_dot).initialize_label(after_dot)
        except ValueError:
            lbl = self.label
            if   expression=='f':     return lbl
            elif expression=='v':     return '%sv' % lbl
            elif expression=='r':     return '%sr' % lbl
            elif expression=='super': return self.parent.label
            elif expression=='var':   return '%s%s' % (self.label.upper(), counter.get())
            elif expression=='a':     return self['conjuncts'][0].label
            elif expression=='b':     return self['conjuncts'][1].label
            else:                     return self.lookup_unique(expression).label

    def lookup_unique(self, key):
        """
        Lookup 'key'.  There should be exactly one item in the associated list.
        """
        try:
            value = self[key]
            if len(value) == 1:
                return value[0]
            else:
                raise KeyError, 'FStructure should only have one feature %s' % key
        except KeyError:
            raise KeyError, "FStructure doesn't contain a feature %s" % key

    def __repr__(self):
        return str(self).replace('\n', '')

    def __str__(self, indent=3):
        try:
            accum = '%s:[' % self.label
        except NameError:
            accum = '['
        try:
            accum += 'pred \'%s(%s)\'' % (self.pred[0], self.pred[1])
        except NameError:
            pass

        for feature in self:
            for item in self[feature]:
                if isinstance(item, FStructure):
                    next_indent = indent+len(feature)+3+len(self.label)
                    accum += '\n%s%s %s' % (' '*(indent), feature, item.__str__(next_indent))
                elif isinstance(item, tuple):
                    accum += '\n%s%s \'%s(%s)\'' % (' '*(indent), feature, item[0], item[1])
                elif isinstance(item, list):
                    accum += '\n%s%s {%s}' % (' '*(indent), feature, ('\n%s' % (' '*(indent+len(feature)+2))).join(item))
                else: # ERROR
                    raise Exception, 'feature %s is not an FStruct, a list, or a tuple' % feature
        return accum+']'


def read_depgraph(depgraph):
    return _read_depgraph(depgraph.root, depgraph)

def _read_depgraph(node, depgraph, label_counter=None, parent=None):
    if not label_counter:
        label_counter = Counter()
    
    if node['rel'].lower() in ['spec', 'punct']:
        # the value of a 'spec' entry is a word, not an FStructure
        return (node['word'], node['tag'])
        
    else:
        self = FStructure()
        self.pred = None
        self.label = _make_label(label_counter.get())

        self.parent = parent
        
        word, tag = node['word'], node['tag']
        if tag[:2] == 'VB':
            if tag[2:3] == 'D':
                self.safeappend('tense', ('PAST', 'tense'))
            self.pred = (word, tag[:2])

        if not self.pred:
            self.pred = (word, tag)

        children = [depgraph.nodelist[idx] for idx in node['deps']]
        for child in children:
            self.safeappend(child['rel'], _read_depgraph(child, depgraph, label_counter, self))

        return self


def _make_label(value):
    """
    Pick an alphabetic character as identifier for an entity in the model.
    
    @parameter value: where to index into the list of characters
    @type value: C{int}
    """
    letter = ['f','g','h','i','j','k','l','m','n','o','p','q','r','s',
              't','u','v','w','x','y','z','a','b','c','d','e'][value-1]
    num = int(value) / 26
    if num > 0:
        return letter + str(num)
    else:
        return letter

        
def demo_read_depgraph():
    from nltk_contrib.dependency import DepGraph
    dg1 = DepGraph().read("""\
Esso       NNP     2       SUB
said    VBD     0       ROOT
the     DT      5       NMOD
Whiting NNP     5       NMOD
field   NN      6       SUB
started VBD     2       VMOD
production      NN      6       OBJ
Tuesday NNP     6       VMOD
""")
    dg2 = DepGraph().read("""\
John       NNP     2       SUB
sees    VBP     0       ROOT
Mary    NNP     2       OBJ
""")
    dg3 = DepGraph().read("""\
a  DT      2       SPEC
man     N       3       SUBJ
walks   IV      0       ROOT
""")
    dg4 = DepGraph().read("""\
every      DT      2       SPEC
girl    N       3       SUBJ
chases  TV      0       ROOT
a       DT      5       SPEC
dog     NNP     3       OBJ
""")

    depgraphs = [dg1,dg2,dg3,dg4]
    for dg in depgraphs:
        print read_depgraph(dg)
        
def demo_depparse():
    from nltk_contrib.dependency import malt
    dg = malt.parse('John sees Mary', True)
    print read_depgraph(dg)
        
if __name__ == '__main__':
    demo_read_depgraph()
    print '\n'
    demo_depparse()
