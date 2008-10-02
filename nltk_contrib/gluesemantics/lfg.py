# Natural Language Toolkit: Lexical Functional Grammar 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.internals import Counter
from nltk import defaultdict

class FStructure(dict):
    def read_depgraph(depgraph):
        return FStructure._read_depgraph(depgraph.root, depgraph)
    
    read_depgraph = staticmethod(read_depgraph)
    
    def _read_depgraph(node, depgraph, label_counter=None, parent=None):
        if not label_counter:
            label_counter = Counter()
        
        if node['rel'].lower() in ['spec']:
            # the value of a 'spec' entry is a word, not an FStructure
            return (node['word'], node['tag'])
            
        else:
            self = FStructure()
            self.pred = None
            self.label = FStructure._make_label(label_counter.get())
    
            self.parent = parent
            
            (word, tag) = (node['word'], node['tag'])
            if tag[:2] == 'VB':
                if tag[2:3] == 'D':
                    self.safeappend('tense', ('PAST', 'tense'))
                self.pred = (word, tag[:2])

            if not self.pred:
                self.pred = (word, tag)
    
            children = [depgraph.nodelist[idx] for idx in node['deps']]
            for child in children:
                self.safeappend(child['rel'], FStructure._read_depgraph(child, depgraph, label_counter, self))

            return self

    _read_depgraph = staticmethod(_read_depgraph)
    
    
    def safeappend(self, key, item):
        if key not in self:
            self[key] = []
        self[key].append(item)
        
    
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
        
    _make_label = staticmethod(_make_label)



    def read_parsetree(pt, current_label=[0], parent=None):
        self = FStructure()
        
        try:
            from nltk.tree import Tree
            assert isinstance(pt, Tree)
        except AssertionError:
            print 'Error Tree: \n%s\nis of type %s' % (pt, type(pt))
            raise

        self.pred = None

        self.label = ['f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','a','b','c','d','e'][current_label[0]]
        current_label[0] += 1

        self.parent = parent
        
        if FStructure.head(pt.node) == 'S':
            if FStructure.head(pt[0].node) == 'NP': # S -> NP VP
                self['subj'] = FStructure.read_parsetree(pt[0], current_label, self)
                if FStructure.head(pt[1][0].node) == 'IV' or FStructure.head(pt[1][0].node) == 'TV' or \
                   FStructure.head(pt[1][0].node) == 'DTV'  or FStructure.head(pt[1][0].node) == 'EquiV' or \
                   FStructure.head(pt[1][0].node) == 'ObjEquiV' or FStructure.head(pt[1][0].node) == 'TVComp' or \
                   FStructure.head(pt[1][0].node) == 'RaisingV':
                    self.pred = (pt[1][0][0], pt[1][0].node['sem']) # the verb
                    if FStructure.head(pt[1][0].node) == 'TV' or FStructure.head(pt[1][0].node) == 'DTV' or \
                       FStructure.head(pt[1][0].node) == 'ObjEquiV':
                        # OBJ for TV, DTV, ObjEquiV
                        self['obj'] = FStructure.read_parsetree(pt[1][1], current_label, self)
                        if FStructure.head(pt[1][0].node) == 'DTV':
                            # THEME for VP -> DTV NP [NP]
                            self['theme'] = FStructure.read_parsetree(pt[1][2], current_label, self)
                        elif FStructure.head(pt[1][0].node) == 'ObjEquiV':
                            # XCOMP for VP -> ObjEquiV NP TO [VP]
                            self['xcomp'] = FStructure.read_parsetree(pt[1][3], current_label, self)
                            # subj of XCOMP is subj of whole
                            #   ie "John persuades David to go" = "John persaudes David that David goes"
                            self['xcomp']['subj'] = self['obj']
                    elif FStructure.head(pt[1][0].node) == 'TVComp':
                        # VP -> TVComp [S]
                        self['comp'] = FStructure.read_parsetree(pt[1][1], current_label, self)
                    elif FStructure.head(pt[1][0].node) == 'EquiV':
                        # VP -> EquiV TO [VP]
                        self['xcomp'] = FStructure.read_parsetree(pt[1][2], current_label, self)
                        # subj of XCOMP is subj of whole
                        #   ie "John tries to go" = "John tries that John goes"
                        self['xcomp']['subj'] = self['subj']
                    elif FStructure.head(pt[1][0].node) == 'RaisingV':
                        # VP -> RaisingV TO [VP]
                        self['xcomp'] = FStructure.read_parsetree(pt[1][2], current_label, self)
                        # subj of XCOMP is subj of whole
                        #   ie "John tries to go" = "John tries that John goes"
                        self['xcomp']['subj'] = self['subj']
##                elif FStructure.head(pt[1][0].node) == 'ADV':
##                    # VP -> ADV VP
##                    r = _get_v_and_adjs(pt[1], current_label)
##                    self.pred = r[0]
##                    if r[1] != []: self['adj'] = r[1]
                elif FStructure.head(pt[1][1].node) == 'CC':
                    # VP -> VP CC VP
                    self.pred = (pt[1][1][0], pt[1][1].node['sem']) # the CC
                    self['conjuncts'] = [FStructure.read_parsetree(pt[1][0], current_label, self)]
                    self['conjuncts'].append(FStructure.read_parsetree(pt[1][2], current_label, self))
                    # Both verbs have the same subject
                    
                    self['conjuncts'][0]['subj'] = FStructure.read_parsetree(pt[0], current_label, self)
                    self['conjuncts'][1]['subj'] = self['conjuncts'][0]['subj']
            elif FStructure.head(pt[1].node) == 'CC': # S -o S CC S
                self.pred = (pt[1][0], pt[1].node['sem']) # the CC
                self['conjuncts'] = [FStructure.read_parsetree(pt[0], current_label, self)]
                self['conjuncts'].append(FStructure.read_parsetree(pt[2], current_label, self))
             
        elif FStructure.head(pt.node) == 'NP':
            if FStructure.head(pt[0].node) == 'Det':
                # NP -> Det N
                r = FStructure._get_n_and_adjs(pt[1], current_label, self)
                self.pred = (r[0][0], r[0].node['sem'])
                if r[1] != []: self['adj'] = (r[1][0], r[1].node['sem'])
                self['spec'] = (pt[0][0][0], pt[0][0].node['sem']) # get the Det
            elif FStructure.head(pt[0].node) == 'PropN' or FStructure.head(pt[0].node) == 'Pro':
                # NP -> PropN | Pro
                self.pred = (pt[0][0], pt[0].node['sem'])
            elif FStructure.head(pt[0].node) == 'N':
                # NP -> N[num=pl]
                r = FStructure._get_n_and_adjs(pt[0], current_label, self)
                self.pred = (r[0][0], r[0].node['sem'])
                if r[1] != []: self['adj'] = (r[1][0], r[1].node['sem'])
            elif FStructure.head(pt[1].node) == 'CC': # NP -o NP CC NP
                self.pred = (pt[1][0], pt[1].node['sem']) # the CC
                self['conjuncts'] = [FStructure.read_parsetree(pt[0], current_label, self)]
                self['conjuncts'].append(FStructure.read_parsetree(pt[2], current_label, self))

        elif FStructure.head(pt.node) == 'VP':
            if FStructure.head(pt[0].node) == 'IV' or FStructure.head(pt[0].node) == 'TV' or \
               FStructure.head(pt[0].node) == 'DTV'  or FStructure.head(pt[0].node) == 'EquiV' or \
               FStructure.head(pt[0].node) == 'ObjEquiV' or FStructure.head(pt[0].node) == 'RaisingV' or \
               FStructure.head(pt[0].node) == 'TVComp':
                self.pred = (pt[0][0], pt[0].node['sem']) # the verb
                if FStructure.head(pt[0].node) == 'TV' or FStructure.head(pt[0].node) == 'DTV' or \
                   FStructure.head(pt[0].node) == 'ObjEquiV':
                    # OBJ for TV, DTV, ObjEquiV
                    self['obj'] = FStructure.read_parsetree(pt[1], current_label, self)
                    if FStructure.head(pt[0].node) == 'DTV':
                        # THEME for VP -o DTV NP [NP]
                        self['theme'] = FStructure.read_parsetree(pt[2], current_label, self)
                    elif FStructure.head(pt[0].node) == 'ObjEquiV':
                        # XCOMP for VP -o ObjEquiV NP TO [VP]
                        self['xcomp'] = FStructure.read_parsetree(pt[3], current_label, self)
                        # subj of XCOMP is obj of whole
                        #   ie "John persuades David to go" = "John persaudes David that David goes"
                        self['xcomp']['subj'] = self['obj']
                elif FStructure.head(pt[0].node) == 'TVComp':
                    # VP -> TVComp [S]
                    self['comp'] = FStructure.read_parsetree(pt[1], current_label, self)
                elif FStructure.head(pt[0].node) == 'EquiV':
                    # VP -> EquiV TO [VP]
                    self['xcomp'] = FStructure.read_parsetree(pt[2], current_label, self)
                    # subj of XCOMP is subj of whole
                    #   ie "John tries to go" = "John tries that John goes"
                    self['xcomp']['subj'] = self['subj']
                elif FStructure.head(pt[0].node) == 'RaisingV':
                    # VP -> RaisingV TO [VP]
                    self['xcomp'] = FStructure.read_parsetree(pt[2], current_label, self)
                    # subj of XCOMP is subj of whole
                    #   ie "John tries to go" = "John tries that John goes"
                    self['xcomp']['subj'] = self['subj']
##                elif FStructure.head(pt[0].node) == 'RB':
##                    # VP -> RB VP
##                    self.pred = pt[1] # the verb
##                    self['adj'] = [FStructure.read_parsetree(pt[0], current_label, self)]
            elif FStructure.head(pt[1].node) == 'CC':
                # VP -> VP CC VP
                self.pred = (pt[1][0], pt[1].node['sem']) # the CC
                self['conjuncts'] = [FStructure.read_parsetree(pt[0], current_label, self)]
                self['conjuncts'].append(FStructure.read_parsetree(pt[2], current_label, self))
                # Both verbs have the same subject
                self['conjuncts'][0]['subj'] = FStructure.read_parsetree(pt[0], current_label, self)
                self['conjuncts'][1]['subj'] = self['conjuncts'][0]['subj']

        elif FStructure.head(pt.node) == 'JJ':
            if isinstance(pt[0], str):
                ## JJ lexical entry
                self.pred = (pt[0], pt.node['sem'])
                
        elif FStructure.head(pt.node) == 'ADV':
            if isinstance(pt[0], str):
                ## ADV lexical entry
                self.pred = (pt[0], pt.node['sem'])

        if self.pred is None:
            raise RuntimeError, 'FStructure creation from\n%s\nwas unsuccessful.' % (pt)
        
        return self

    read_parsetree = staticmethod(read_parsetree)

    def _get_n_and_adjs(pt, current_label, parent):
        """ This function is here to deal with N -o JJ N rules
            since we don't know exactly where the noun is.
            Returns (noun_word, list_of_adj_fstructs) """
        if FStructure.head(pt.node) == 'N':
            if isinstance(pt[0], str):
                # N lexical entry
                return (pt, [])
            else: #if FStructure.head(self[0].node) == 'JJ':
                # N -o JJ N rule
                r = FStructure._get_n_and_adjs(pt[1], current_label, parent)
                jj_fstruct = FStructure.read_parsetree(pt[0], current_label, parent)
                r[1].append(jj_fstruct) # append the current node's JJ
                return (r[0], r[1])
            
        #if it doesn't match a pattern
        raise RuntimeError, '%s is not of a valid N rule.' % (pt[0])
    
    _get_n_and_adjs = staticmethod(_get_n_and_adjs)
    
    
    def to_glueformula_list(self, glue_pos_dict, labels_added=[], current_subj=None, verbose=False):
        from nltk.tree import Tree
        glueformulas = []

        if not current_subj:
            current_subj = self

        # lookup 'pred'
        sem = self.pred[1]
        lookup = glue_pos_dict.lookup(sem, self.pred[0], current_subj, self)
        glueformulas.extend(lookup)

        for feature in self:
            for item in self[feature]:
                if isinstance(item, FStructure):
                    if not item.label in labels_added:
                        glueformulas.extend(item.to_glueformula_list(glue_pos_dict, labels_added,self))
                        labels_added.append(item.label)
                elif isinstance(item, tuple):
                    glueformulas.extend(glue_pos_dict.lookup(item[1], item[0], None, self))
                elif isinstance(item, list):
                    for entry in item:
                        glueformulas.extend(entry.to_glueformula_list(glue_pos_dict, labels_added))
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
            if expression=='f':       return lbl
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
                raise KeyError('FStructure should only have one feature %s' % key)
        except KeyError:
            raise KeyError, "FStructure doesn't contain a feature %s" % key
        


    def head(node):
        for (fname, fval) in sorted(node.items()):
            display = getattr(fname, 'display', None)
            if display == 'prefix':
                  return fval
        return None 
    
    head = staticmethod(head)


    def __repr__(self):
        return str(self).replace('\n', '')

    def __str__(self, indent=3):
        try:
            accum = '%s:[' % self.label
        except NameError:
            accum = '['
        try:
            accum += 'pred \'%s\'' % self.pred[0]
        except NameError:
            pass

        for feature in self:
            for item in self[feature]:
                if isinstance(item, FStructure):
                    next_indent = indent+len(feature)+3+len(self.label)
                    accum += '\n%s%s %s' % (' '*(indent), feature, item.__str__(next_indent))
                elif isinstance(item, tuple):
                    accum += '\n%s%s \'%s\'' % (' '*(indent), feature, item[0])
                elif isinstance(item, list):
                    accum += '\n%s%s {%s}' % (' '*(indent), feature, ('\n%s' % (' '*(indent+len(feature)+2))).join(item))
                else: # ERROR
                    raise Exception, 'feature %s is not an FStruct, a list, or a tuple' % feature
        return accum+']'

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
        print FStructure.read_depgraph(dg)
        
def demo_depparse():
    from nltk_contrib.dependency import malt
    dg = malt.parse('John sees Mary', True)
    print FStructure.read_depgraph(dg)
        
if __name__ == '__main__':
    demo_read_depgraph()
    print '\n'
    demo_depparse()
