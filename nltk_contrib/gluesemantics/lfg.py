# Natural Language Toolkit: Lexical Functional Grammar 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

class FStructure(dict):
    def read_depgraph(depgraph):
        return FStructure._read_depgraph(depgraph.root, depgraph, [0])
    
    read_depgraph = staticmethod(read_depgraph)
    
    def _read_depgraph(node, depgraph, current_label=[0], parent=None):
        if node['rel'].lower() in ['spec']:
            # the value of a 'spec' entry is a word, not an FStructure
            return (node['word'], node['tag'])
            
        else:
            self = FStructure()
            self.pred = None
            self.label = ['f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','a','b','c','d','e'][current_label[0]]
            current_label[0] += 1
    
            self.parent = parent
            
            (word, tag) = (node['word'], node['tag'])
            if tag[:2] == 'VB':
                if tag[2:3] == 'D':
                    self['tense'] = ('PAST', 'tense')
                self.pred = (word, tag[:2])

            if not self.pred:
                self.pred = (word, tag)
    
            children = [depgraph.nodelist[idx] for idx in node['deps']]
            for child in children:
                self[child['rel']] = FStructure._read_depgraph(child, depgraph, current_label, self)
    
            return self

    _read_depgraph = staticmethod(_read_depgraph)
    
    
    
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
            if isinstance(self[feature], FStructure):
                if not self[feature].label in labels_added:
                    glueformulas.extend(self[feature].to_glueformula_list(glue_pos_dict, labels_added,self))
                    labels_added.append(self[feature].label)
            elif isinstance(self[feature], tuple):
                glueformulas.extend(glue_pos_dict.lookup(self[feature][1], self[feature][0], None, self))
            elif isinstance(self[feature], list):
                for entry in self[feature]:
                    glueformulas.extend(entry.to_glueformula_list(glue_pos_dict, labels_added))
            else:
                raise Exception, 'feature %s is not an FStruct, a list, or a tuple' % feature

        return glueformulas

    def initialize_label(self, expression, unique_var_id=[0]):
        try:
            dot = expression.index('.')

            before_dot = expression[:dot]
            after_dot = expression[dot+1:]
            if before_dot=='super':
                return self.parent.initialize_label(after_dot)
            else:
                try:
                    return self[before_dot].initialize_label(after_dot)
                except KeyError:
                    raise KeyError, 'FStructure doesn\'t contain a feature %s' % before_dot
        except ValueError:
            lbl = self.label
            if expression=='f':       return lbl
            elif expression=='v':     return '%sv' % lbl
            elif expression=='r':     return '%sr' % lbl
            elif expression=='super': return self.parent.label
            elif expression=='var':   return '%s%s' % (self.label.upper(), unique_var_id[0])
            elif expression=='a':     return self['conjuncts'][0].label
            elif expression=='b':     return self['conjuncts'][1].label
            else:                     return self[expression].label

    def head(node):
        for (fname, fval) in sorted(node.items()):
            display = getattr(fname, 'display', None)
            if display == 'prefix':
                  return fval
        return None 
    
    head = staticmethod(head)

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
    
    
    
    def __repr__(self):
        from nltk.tree import Tree
        try:
            accum = '%s:[' % self.label
        except NameError:
            accum = '['
        try:
            accum += 'pred \'%s\'' % self.pred[0]
        except NameError:
            pass

        for feature in self:
            if isinstance(self[feature], FStructure):
                accum += ' %s %s' % (feature, self[feature].__repr__())
            elif isinstance(self[feature], tuple):
                accum += ' %s \'%s\'' % (feature, self[feature][0])
            elif isinstance(self[feature], list):
                accum += ' %s {' % (feature)
                for entry in self[feature]:
                    accum += '%s' % entry
                accum += '}'
            else: # ERROR
                raise Exception, 'feature %s (%s) is not an FStruct, a list, or a tuple' % (feature, self[feature])
        return accum+']'

    def __str__(self, indent=3):
        from nltk.tree import Tree
        try:
            accum = '%s:[' % self.label
        except NameError:
            accum = '['
        try:
            accum += 'pred \'%s\'' % self.pred[0]
        except NameError:
            pass

        for feature in self:
            if isinstance(self[feature], FStructure):
                next_indent = indent+len(feature)+3+len(self.label)
                accum += '\n%s%s %s' % (' '*(indent), feature, self[feature].__str__(next_indent))
            elif isinstance(self[feature], tuple):
                accum += '\n%s%s \'%s\'' % (' '*(indent), feature, self[feature][0])
            elif isinstance(self[feature], list):
                accum += '\n%s%s {%s}' % (' '*(indent), feature, ('\n%s' % (' '*(indent+len(feature)+2))).join(self[feature]))
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

#    depgraphs = [dg1,dg2,dg3,dg4]
#    for dg in depgraphs:
#        print FStructure.read_depgraph(dg)

    print FStructure.read_depgraph(dg3)
        
def demo_depparse():
    from nltk_contrib.dependency import malt
    dg = malt.parse('John sees Mary', True)
    print FStructure.read_depgraph(dg)
        
if __name__ == '__main__':
    demo_read_depgraph()
    print '\n'
    demo_depparse()
