# -*- coding: utf-8 -*-
"""
@author: Raphael Brand
@author: Philipp Nahratow
@author: Leon Schröder
@author: Martin Gäbler
"""

import sqlite3
import os
from nltk.corpus.reader.api import CorpusReader

######################################################################
## Table of Contents
######################################################################
##    - Database Connector
##        - DBConnectionError
##        - SQLiteInterface
##    - Globals
##    - Data Classes
##        - GermaNetError
##        - Lemma
##        - Synset
##        - GermaNetCorpusReader

######################################################################
## Database Connector
######################################################################

class DBConnectionError(Exception):
    "An exception class for DBConnection-related errors."

class SQLiteInterface:
    """
    Interface to the database.
    @cvar TRUE: specifies how boolean values are stored into the database
    @cvar FALSE: specifies how boolean values are stored into the database
    @cvar AUTOINCREMENT: a boolean value that will tell the buildscript if the ids need to be calculated  
    """   
    
    TRUE = 1
    FALSE = 0
    AUTOINCREMENT = True    
    
    def __init__(self, DB_file, overwrite=False):
        """
        Database connection is established in the constructor
        @type DB_file: string
        @param DB_file: the path to germanet.db 
        @type overwrite: boolean
        @param overwrite: 
        """ 
        self._file = DB_file        
        if (not overwrite and not os.path.exists(self._file)):
            raise DBConnectionError(
            "DBCONNECTION FAILED - FILE DOES NOT EXIST: %s" % self._file)                
        if overwrite and os.path.exists(self._file):
            os.remove(self._file)                        
        self._connection = sqlite3.connect(self._file)
        self._connection.row_factory = sqlite3.Row
        self._connection.text_factory = str    
        self._cursor = self._connection.cursor()            
    
    def __del__(self):
        "Database connection is closed when object gets destroyed"
        self._cursor.close()
        self._connection.close()
            
    def execute(self, sqlstring, params=None):
        """
        Executes an SQL statement but does not return anything
        @type sqlstring: string
        @param sqlstring: SQL statement
        @type params: tupel
        @param params: the values which ought to be replaced in the sql-statement  
        """        
        try:
            if params is None:
                self._cursor.execute(sqlstring)
            else:
                self._cursor.execute(sqlstring,params)
        except Exception as inst:
            print type(inst)            
            print inst
            try:
                print "debug: execute failed, reconnecting to retry..."
                self.__init__(self._file, False)
                if params is None:
                    self._cursor.execute(sqlstring)
                else:
                    self._cursor.execute(sqlstring,params)                
            except:
                raise DBConnectionError("""COULDN'T EXECUTE STATEMENT:
                SQL-TEMPLATE: %s
                VALUES: %s""" % (sqlstring,params))        
                
        
    def fetchall(self):
        """
        @rtype: list
        @return: a list of all fetchable rows, a single row's column is accessible by row['columnname']         
        """
        return self._cursor.fetchall()
        
    def fetchone(self):        
        """
        @rtype: row
        @return: returns a single row, a single row's column is accessible by row['columnname']
        """
        return self._cursor.fetchone()

    def eval(self,expression):
        """
        This method converts a boolean value (as stored in the database) to a python boolean (True|False)
        @param expression: a boolean value as stored in the database        
        @rtype: boolean         
        """
        return (str(expression) == str(SQLiteInterface.TRUE))
    
    def commit(self):
        "Perform commit"
        self._connection.commit()
        
######################################################################
## Globals
######################################################################

# Positive infinity (for similarity functions)
_INF = 1e300

# Part-of-speech constants
POS_TO_WC = {"a":"adj","n":"nomen","v":"verben"}
WC_TO_POS = dict((v,k) for k,v in POS_TO_WC.iteritems())

ADJ, NOUN, VERB = 'adj', 'nomen', 'verben'
POS_LIST = [NOUN, VERB, ADJ]

######################################################################
## Data Classes
######################################################################

class GermaNetError(Exception):
    "An exception class for germanet-related errors."
    
    
class _GermaNetObject(object):
    "A common base class for lemmas and synsets."
    
    def hypernyms(self):
        "hypernyms are broader, generic for L{self}"
        return self._related('hyperonymy')

    def hyponyms(self):
        "hyponyms are narrower, specific for L{self}"
        return self._related('hyperonymy', inverse=True) 

    def holonyms(self):
        "holonyms are part of L{self}"
        return self._related('holonymy')
    
    def meronyms(self):
        "L{self} consists of meronyms"
        return self._related('meronymy')
    
    def entailments(self):
        "L{self} implicts entailments"
        return self._related("entailment")
    
    def entaileds(self):
        "entaileds implict L{self}"
        return self._related("entailment",inverse=True)
    
    def causes(self):
        "L{self} causes causes"
        return self._related("causation")
    
    def associations(self):
        "L{self} is associated with associations"
        return (self._related('association') 
                + self._related('association', inverse=True))
        
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

class lazy_property(object):
    "Decorator for lazy property loading"
    def __init__(self,func):
        self._func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
    def __get__(self,obj,obj_class):
        if obj is None:
            return obj
        obj.__dict__[self.__name__] = self._func(obj)
        return obj.__dict__[self.__name__]
   
    
class Lemma(_GermaNetObject):
    """
    The Lemma Object.
    @type id: number
    @ivar id: unique identifier 
    @type synset_id: number 
    @ivar synset_id: unique identifier of the synset, to which this lexical unit belongs
    @type name: string
    @ivar name: the orthographical form of this lexical unit
    @type orth_var: string
    @ivar orth_var: an orthographical variant
    @type old_orth_form: string
    @ivar old_orth_form: the orthographical form, which specifies a difference in the old german orthography; this is only set, if there was a second allowed variant in the old orthography
    @type old_orth_var: string 
    @ivar old_orth_var: an orthographical variant, which specifies a differing variant, which was allowed in the old german orthography; this is only set, if it is not allowed anymore in the new orthography
    @type is_named_entity: boolean
    @ivar is_named_entity: specifies whether this lexical unit is a named entity or not 
    @type is_artificial: boolean
    @ivar is_artificial: specifies whether this lexical unit is used to represent an artificial node in the graph
    @type is_style_marked: boolean
    @ivar is_style_marked: specifies whether the style of this lexical unit is marked
    @type synset: L{Synset}
    @ivar synset: the synset, to which this lexical unit belongs
    @type frames: list
    @ivar frames: a list of frames that belong to this lexical unit eg NN, NE, or NN.AN.Az
    @type examples: list
    @ivar examples: a list of example tuples (text,frame) where text is the example text and frame is the example frame
    @type identifier: string
    @ivar identifier: identifier string <synset>.<pos>.<sense>.<lemma>
    """    
    
    def __init__(self, id, DB, synset=None):
        """
        Constructor should only be called by L{GermaNetCorpusReader}
        @type DB: L{SQLiteInterface}
        @param DB: Instance of DB Connection (passed by GermaNetCorpusReader)
        @type synset: L{Synset}
        @param synset: the synset this lemma belongs to
        """        
        self._DB = DB
        
        # fetching most data fields for lemma object from lex_unit_table                
        self._DB.execute("SELECT * FROM lex_unit_table WHERE id=?" , (id,))
        row = self._DB.fetchone()
        if (row is None):
            raise GermaNetError('Lemma not found')
        self.id = id
        self.synset_id = row['synset_id']
        self.name = row['orth_form']
        self.is_named_entity = self._DB.eval(row['named_entity'])
        self.is_artificial = self._DB.eval(row['artificial'])
        self.is_style_marked = self._DB.eval(row['style_marking'])
        self.old_orth_form = row['old_orth_form']
        self.old_orth_var = row['old_orth_var']
        self.orth_var = row['orth_var']
        self._syn = synset
        
        # fetching frames        
        sqlstring, params = """SELECT frame FROM frame_type_table,frame_table
        WHERE ? = frame_table.lex_unit_id AND frame_table.frame_type_id = frame_type_table.id""" , (self.id,)
        self._DB.execute(sqlstring,params)
        self.frames = [row['frame'] for row in self._DB.fetchall()]
        
        # fetching examples. an example consists of a example text and an optional example frame       
        sqlstring, params = """SELECT text,frame FROM example_table, frame_type_table WHERE
        ? = example_table.lex_unit_id AND example_table.frame_type_id = frame_type_table.id""" , (self.id,)
        self._DB.execute(sqlstring,params)
        self.examples = [(row['text'],row['frame']) for row in self._DB.fetchall()]
        self.identifier = "%s.%s" % (self.synset.name, self.name)

    @lazy_property
    def synset(self):
        if self._syn is None:
            return Synset(self.synset_id,self._DB)
        else:
            return self._syn
        
    def _related(self, relation_name, inverse=False):
        """
        @type inverse: Boolean 
        @param inverse: specifies the direction
        @rtype: list 
        @return: A list of related L{Lemma} Objects 
        """
        # distinguish the relations direction with boolean variable inverse        
        if not inverse:
            sqlstring,params = """SELECT id FROM lex_unit_table WHERE synset_id IN
            (SELECT to_synset_id FROM con_rel_table WHERE from_synset_id =? 
            AND rel_type_id = (SELECT id FROM con_rel_type_table 
            WHERE name=?))""" , (self.synset_id, relation_name)
            self._DB.execute(sqlstring, params)
        else:
            # selecting only the lemma ids that match the relation            
            sqlstring, params = """SELECT id FROM lex_unit_table WHERE synset_id IN 
            (SELECT from_synset_id FROM con_rel_table WHERE to_synset_id =? 
            AND rel_type_id = (SELECT id FROM con_rel_type_table 
            WHERE name=?))""" , (self.synset_id, relation_name)
            self._DB.execute(sqlstring, params)       
                         
        # building a result array of lemma objects  
        return [Lemma(row['id'],self._DB) for row in self._DB.fetchall()]       
    
    def _lex_related(self, relation_name, inverse=False):
        """
        This method does the same as L{_related} but with tables explicit to lemmas
        @type inverse: Boolean 
        @param inverse: specifies the direction
        @rtype: list
        @return: A list of related L{Lemma} Objects 
        """
        if not inverse:
            sqlstring,params = """SELECT to_lex_unit_id FROM lex_rel_table WHERE 
            from_lex_unit_id =? AND rel_type_id = (SELECT id FROM 
            lex_rel_type_table WHERE name=?)""" , (self.id, relation_name)
            self._DB.execute(sqlstring, params)
            column = 'to_lex_unit_id'
        else:
            sqlstring, params = """SELECT from_lex_unit_id FROM lex_rel_table WHERE 
            to_lex_unit_id =? AND rel_type_id = (SELECT id FROM 
            lex_rel_type_table WHERE name=?)""" , (self.id, relation_name)
            self._DB.execute(sqlstring,params)
            column = 'from_lex_unit_id'
            
        # building a result array of lemma objects 
        return [Lemma(row[column],self._DB) for row in self._DB.fetchall()]
    
    def antonyms(self):
        """
        antonyms are opposite to L{self}
        @rtype: list
        """
        return (self._lex_related('antonymy') 
                + self._lex_related('antonymy', inverse=True))
    
    def pertonyms(self):
        """
        adj -> noun
        @rtype: list
        """
        return (self._lex_related('pertonymy'))
    
    def participles(self):
        """
        adj -> verb
        @rtype: list
        """        
        return (self._lex_related('participle'))
    
    def __repr__(self):
        tup = (type(self).__name__, self.identifier)
        return "%s('%s')" % tup


class Synset(_GermaNetObject):
    """
    The Synset Object.
    @type id: number
    @ivar id: unique identifier 
    @type definition: string
    @ivar definition: definition of this synset
    @type comment: string
    @ivar comment: comment about this synset
    @type orth_form: string
    @ivar orth_form: the orthographical form of this synset
    @type word_class: string
    @ivar word_class: specifies the word class of this synset, e.g. Bewegung, Geist, etc.
    @type word_category: string
    @ivar word_category: specifies the word class of this synset, e.g. adj, nomen, or verben
    @type sense: number
    @ivar sense: is counted up when there are several synsets with the same orthographical form
    @type lemmas: list
    @ivar lemmas: a list of lemmas this synset contains 
    @type lexname: string
    @ivar lexname: the lexical name is word_category.word_class
    @type name: string
    @ivar name: identifier string <name>.<pos>.<sense>
    """
    
    def __init__(self, id, DB, name=None, pos=None, sense=None):
        """
        Constructor should only be called by L{GermaNetCorpusReader}
        @type DB: L{SQLiteInterface}
        @param DB: Instance of DB Connection (passed by GermanetCorpusReader)
        """
        
        self._DB = DB
        
        # fetching data fields from synset_table
        self._DB.execute("SELECT * FROM synset_table WHERE id=?" , (id,))
        row = self._DB.fetchone()        
        if (row is None):
            raise GermaNetError('Synset not found')
        self.id = id
        self._word_class_id = row['word_class_id']        
        self._word_category_id = row['word_category_id']
        self.definition = row['paraphrase']
        self.comment = row['comment'] 
        
        # fetching lemma representing the synset     
        if name is None:   
            sqlstring, params = """SELECT orth_form FROM lex_unit_table 
            WHERE synset_id = ?""" , (self.id,)
            self._DB.execute(sqlstring, params)
            self.orth_form =  self._DB.fetchone()['orth_form']
        else:
            self.orth_form = name
        
        # word class
        sqlstring, params = """SELECT word_class FROM word_class_table 
        WHERE id = ?""" , (self._word_class_id,)
        self._DB.execute(sqlstring,params)
        row = self._DB.fetchone()
        self.word_class = row['word_class']
        
        if pos is None:
            sqlstring,params = """SELECT word_category FROM word_category_table
            WHERE id = ?""" , (self._word_category_id,)    
            self._DB.execute(sqlstring,params)    
            row = self._DB.fetchone()
            self.word_category = row['word_category']
            self.pos = WC_TO_POS[self.word_category]
        else:
            self.pos = pos            
            self.word_category = POS_TO_WC[pos]
        
        if sense is None:
            sqlstring, params = """SELECT DISTINCT synset_id 
            FROM lex_unit_table WHERE orth_form = ?""" , (self.orth_form,)
            self._DB.execute(sqlstring,params)
            self.sense = 0 
            for row in self._DB.fetchall():
                self.sense += 1
                if row['synset_id'] == self.id:
                    break
        else:
            self.sense = sense                
               
        sqlstring,params = """SELECT id FROM lex_unit_table 
        WHERE synset_id = ?""" , (self.id,)              
        self._DB.execute(sqlstring,params)
        self._lex_unit_ids = [row['id'] for row in self._DB.fetchall()]
        self.lexname = "%s.%s" % (self.word_category,self.word_class)
        self.name = "%s.%s.%s" % (self.orth_form,self.pos,self.sense)

    @lazy_property
    def lemmas(self):
        return [Lemma(lex_unit_id,self._DB,self) for lex_unit_id in self._lex_unit_ids] 
        
        
    def __repr__(self):
        tup = (type(self).__name__, self.name)
        return "%s('%s')" % tup

    def _related(self, relation_name, inverse=False):
        """
        @type inverse: Boolean 
        @param inverse: specifies the direction 
        @return: A list of related L{Synset} Objects 
        """
        if not inverse:            
            sqlstring,params = """SELECT to_synset_id FROM con_rel_table WHERE 
            from_synset_id=? AND rel_type_id=(SELECT id FROM 
            con_rel_type_table WHERE name=?)""" , (self.id, relation_name)
            self._DB.execute(sqlstring,params)
            column = 'to_synset_id'
        else:
            sqlstring,params = """SELECT from_synset_id from con_rel_table WHERE 
            to_synset_id=? AND rel_type_id=(SELECT id FROM 
            con_rel_type_table WHERE name=?)""" , (self.id, relation_name)
            self._DB.execute(sqlstring,params)
            column = 'from_synset_id'
        
        
        return [Synset(row[column], self._DB) for row in self._DB.fetchall()]
    
    # Returns the topmost hypernym(s) of this synset in GermaNet
    # Should be only 1 (usually GNROOT.n.1, except there's a cycle.
    def root_hypernyms(self):
        """Get the topmost hypernym(s) of this synset in GermaNet. Mostly GNROOT.n.1"""

        result = []
        seen = set()
        todo = [self]
        while todo:
            next_synset = todo.pop()
            if next_synset not in seen:
                seen.add(next_synset)
                next_hypernyms = next_synset.hypernyms()
                if not next_hypernyms:
                    result.append(next_synset)
                else:
                    todo.extend(next_hypernyms)
        return result
    
    # Returns the length of the longest hypernym path from this
    # synset to the root.
    def max_depth(self):
        """
        @return: The length of the longest hypernym path from this
        synset to the root.
        """

        if "_max_depth" not in self.__dict__:
            hypernyms = self.hypernyms()
            if not hypernyms:
                self._max_depth = 0
            else:
                self._max_depth = 1 + max(h.max_depth() for h in hypernyms)
        return self._max_depth
    
    # Returns the length of the shortest hypernym path from this
    # synset to the root.
    def min_depth(self):
        """
        @return: The length of the shortest hypernym path from this
        synset to the root.
        """

        if "_min_depth" not in self.__dict__:
            hypernyms = self.hypernyms()
            if not hypernyms:
                self._min_depth = 0
            else:
                self._min_depth = 1 + min(h.min_depth() for h in hypernyms)
        return self._min_depth
    
    # Get the path(s) from this synset to the root, where each path is a
    # list of the synset nodes traversed on the way to the root.
    def hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.

        @return: A list of lists, where each list gives the node sequence
           connecting the initial L{Synset} node and a root node.
        """
        paths = []

        hypernyms = self.hypernyms()
        if len(hypernyms) == 0:
            paths = [[self]]

        for hypernym in hypernyms:
            for ancestor_list in hypernym.hypernym_paths():
                ancestor_list.append(self)
                paths.append(ancestor_list)
        return paths
    
    #  Iterator
    def _iter_hypernym_lists(self):
        """
        @return: An iterator over L{Synset}s that are either proper
        hypernyms or instance of hypernyms of the synset.
        """
        todo = [self]
        seen = set()
        while todo:
            for synset in todo:
                seen.add(synset)
            yield todo
            todo = [hypernym
                    for synset in todo
                    for hypernym in synset.hypernyms()
                    if hypernym not in seen]
    
    def common_hypernyms(self, other):
        """
        Find all synsets that are hypernyms of this synset and the
        other synset.

        @type  other: L{Synset}
        @param other: other input synset.
        @return: The synsets that are hypernyms of both synsets.
        """
        self_synsets = set(self_synset
                           for self_synsets in self._iter_hypernym_lists()
                           for self_synset in self_synsets)
        other_synsets = set(other_synset
                           for other_synsets in other._iter_hypernym_lists()
                           for other_synset in other_synsets)
        return list(self_synsets.intersection(other_synsets))
    
    def lowest_common_hypernyms(self, other):
        """Get the lowest synset that both synsets have as a hypernym."""

        self_hypernyms = self._iter_hypernym_lists()
        other_hypernyms = other._iter_hypernym_lists()

        synsets = set(s for synsets in self_hypernyms for s in synsets)
        others = set(s for synsets in other_hypernyms for s in synsets)
        synsets.intersection_update(others)

        try:
            max_depth = max(s.min_depth() for s in synsets)
            return [s for s in synsets if s.min_depth() == max_depth]
        except ValueError:
            return []

    def hypernym_distances(self, distance=0):
        """
        Get the path(s) from this synset to the root, counting the distance
        of each node from the initial node on the way. A set of
        (synset, distance) tuples is returned.

        @type  distance: C{int}
        @param distance: the distance (number of edges) from this hypernym to
            the original hypernym L{Synset} on which this method was called.
        @return: A set of (L{Synset}, int) tuples where each L{Synset} is
           a hypernym of the first L{Synset}.
        """
        distances = set([(self, distance)])
        for hypernym in self.hypernyms():
            distances |= hypernym.hypernym_distances(distance+1)
        return distances
    
    def shortest_path_distance(self, other):
        """
        Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their
        distances are recorded and compared. The ancestor node common to both
        synsets that can be reached with the minimum number of traversals is
        used. If no ancestor nodes are common, None is returned. If a node is
        compared with itself 0 is returned.

        @type  other: L{Synset}
        @param other: The Synset to which the shortest path will be found.
        @return: The number of edges in the shortest path connecting the two
            nodes, or None if no path exists.
        """

        if self == other:
            return 0

        path_distance = None

        dist_list1 = self.hypernym_distances()
        dist_dict1 = {}

        dist_list2 = other.hypernym_distances()
        dist_dict2 = {}

        # Transform each distance list into a dictionary. In cases where
        # there are duplicate nodes in the list (due to there being multiple
        # paths to the root) the duplicate with the shortest distance from
        # the original node is entered.

        for (l, d) in [(dist_list1, dist_dict1), (dist_list2, dist_dict2)]:
            for (key, value) in l:
                if key in d:
                    if value < d[key]:
                        d[key] = value
                else:
                    d[key] = value

        # For each ancestor synset common to both subject synsets, find the
        # connecting path length. Return the shortest of these.

        for synset1 in dist_dict1.keys():
            for synset2 in dist_dict2.keys():
                if synset1 == synset2:
                    new_distance = dist_dict1[synset1] + dist_dict2[synset2]
                    if path_distance < 0 or new_distance < path_distance:
                        path_distance = new_distance

        return path_distance
    
    def tree(self, rel, depth=-1, cut_mark=None):
        """treefunction
        
        >>> from nltk.corpus import germanet
        >>> hand = germanet.synsets("Hand")[0]
        >>> hyp = lambda s:s.hypernyms()
        >>> from pprint import pprint
        >>> pprint(hand.tree(hyp))
        [Synset('Hand.n.1'),
         [Synset('Gliedmaße.n.1'),
          [Synset('Körperteil.n.1'),
           [Synset('Teil.n.5'),
            [Synset('Objekt.n.2'),
             [Synset('Entität.n.1'), [Synset('GNROOT.n.1')]]]]],
          [Synset('Glied.n.2'),
           [Synset('Teil.n.3'),
            [Synset('Ding.n.1'),
             [Synset('Objekt.n.2'),
              [Synset('Entität.n.1'), [Synset('GNROOT.n.1')]]]]]]],
         [Synset('Tastorgan.n.1'),
          [Synset('Sinnesorgan.n.1'),
           [Synset('Organ.n.2'),
            [Synset('Körperteil.n.1'),
             [Synset('Teil.n.5'),
              [Synset('Objekt.n.2'),
               [Synset('Entität.n.1'), [Synset('GNROOT.n.1')]]]]]]]]]
        """

        tree = [self]
        if depth != 0:
            tree += [x.tree(rel, depth-1, cut_mark) for x in rel(self)]
        elif cut_mark:
            tree += [cut_mark]
        return tree
    
    # interface to similarity methods
    def path_similarity(self, other, verbose=False):
        """
        Path Distance Similarity:
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses in the is-a (hypernym/hypnoym)
        taxonomy. The score is in the range 0 to 1, except in those cases where
        a path cannot be found (will only be true for verbs as there are many
        distinct verb taxonomies), in which case None is returned. A score of
        1 represents identity i.e. comparing a sense with itself will return 1.

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.

        @return: A score denoting the similarity of the two L{Synset}s,
            normally between 0 and 1. None is returned if no connecting path
            could be found. 1 is returned if a L{Synset} is compared with
            itself.
        """

        distance = self.shortest_path_distance(other)
        if distance >= 0:
            return 1.0 / (distance + 1)
        else:
            return None
        
        
    def wup_similarity(self, other, verbose=False):
        """
        Wu-Palmer Similarity:
        Return a score denoting how similar two word senses are, based on the
        depth of the two senses in the taxonomy and that of their Least Common
        Subsumer (most specific ancestor node). Note that at this time the
        scores given do _not_ always agree with those given by Pedersen's Perl
        implementation of WordNet Similarity.

        The LCS does not necessarily feature in the shortest path connecting
        the two senses, as it is by definition the common ancestor deepest in
        the taxonomy, not closest to the two senses. Typically, however, it
        will so feature. Where multiple candidates for the LCS exist, that
        whose shortest path to the root node is the longest will be selected.
        Where the LCS has multiple paths to the root, the longer path is used
        for the purposes of the calculation.

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @return: A float score denoting the similarity of the two L{Synset}s,
            normally greater than zero. If no connecting path between the two
            senses can be found, None is returned.
        """

        subsumers = self.lowest_common_hypernyms(other)

        # If no LCS was found return None
        if len(subsumers) == 0:
            return None

        subsumer = subsumers[0]

        # Get the longest path from the LCS to the root,
        # including two corrections:
        # - add one because the calculations include both the start and end
        #   nodes
        # - add one to non-nouns since they have an imaginary root node
        depth = subsumer.max_depth() + 1
        if subsumer.pos != NOUN:
            depth += 1

        # Get the shortest path from the LCS to each of the synsets it is
        # subsuming.  Add this to the LCS path length to get the path
        # length from each synset to the root.
        len1 = self.shortest_path_distance(subsumer)
        len2 = other.shortest_path_distance(subsumer)
        if len1 is None or len2 is None:
            return None
        len1 += depth
        len2 += depth
        return (2.0 * depth) / (len1 + len2)
    
    def closure(self, rel, depth=-1):
        """Return the transitive closure of source under the rel
        relationship, breadth-first.

        >>> from nltk.corpus import germanet
        >>> hand = germanet.synsets("Hand")[0]
        >>> hyp = lambda s:s.hypernyms()
        >>> print list(hand.closure(hyp))
        [Synset('Gliedmaße.n.1'), Synset('Tastorgan.n.1'), Synset('Körperteil.n.1'), 
        Synset('Glied.n.2'), Synset('Sinnesorgan.n.1'), Synset('Teil.n.5'), 
        Synset('Teil.n.3'), Synset('Organ.n.2'), Synset('Objekt.n.2'), 
        Synset('Ding.n.1'), Synset('Entität.n.1'), Synset('GNROOT.n.1')]
        
        """
        from nltk.util import breadth_first
        synset_ids = []
        for synset in breadth_first(self, rel, depth):            
            if synset.id != self.id:
                if synset.id not in synset_ids:                    
                    synset_ids.append(synset.id)
                    yield synset
    
class GermaNetCorpusReader(CorpusReader):
    _ENCODING = None
    _FILES = ()
    def __init__(self, root):
        CorpusReader.__init__(self, root, self._FILES, encoding=self._ENCODING)
        #!!!!!!!!!!!!!TODO LATE, USE nltk.data TO FETCH PATHS!!!!!!!!!
        from paths import germanet_db_path
        self._DB = SQLiteInterface(germanet_db_path)
        
    def synset(self, identifier):
        """
        @type identifier: string
        @param identifier: A synset identifier <synsetname>.<pos>.<sense>    
        @return: A Single L{Synset} Object corresponding to the identifier
        """        
        try:
            synset_name, pos, sense = identifier.rsplit('.',2)
        except ValueError:
            errorstring = """ INCORRECT IDENTIFIER FORMAT
            \t Synset = <synset_name>.<pos>.<sense>
            \t Lemma = <synset_name>.<pos>.<sense>.<lemma_name>
                          """
            print errorstring
            return None
        
        sqlstring,params = """SELECT DISTINCT synset_id 
        FROM lex_unit_table WHERE orth_form = ?""" , (synset_name,)
        self._DB.execute(sqlstring,params)
        rownumber = 0 
        synset_id = None
        sense = int(sense)
        for row in self._DB.fetchall():
            rownumber += 1
            if rownumber == sense:
                synset_id = row['synset_id']  
                      
        if rownumber == 0 or synset_id is None:
            raise GermaNetError("Synset not found")
        else:
            return Synset(synset_id,self._DB,synset_name,pos,sense)
            
        
            
    def synsets(self, name, pos=None):
        """
        @type name: string
        @param name: An actual word    
        @return: A list of all L{Synset} Objects that have lemmas with the orth_form <name>
        """
        sqlstring,params = """SELECT DISTINCT synset_id FROM lex_unit_table 
        WHERE orth_form=? OR old_orth_form = ? OR orth_var = ? OR old_orth_var = ?""" , (name,name,name,name)
        self._DB.execute(sqlstring,params)
        synsets = [Synset(row['synset_id'],self._DB) for row in self._DB.fetchall()]
        if pos is None:
            return synsets
        else:
            return [synset for synset in synsets if synset.pos == pos]
            
    def lemma(self, identifier):
        """
        @type identifier: string
        @param identifier: A synset identifier <synsetname>.<pos>.<sense>.<lemma>    
        @return: A Single L{Lemma} Object corresponding to the identifier
        """
        try:            
            synset_identifier, lemma_name = identifier.rsplit('.',1)
        except ValueError:
            errorstring = """ INCORRECT IDENTIFIER FORMAT
            \t Synset = <synset_name>.<pos>.<sense>
            \t Lemma = <synset_name>.<pos>.<sense>.<lemma_name>
                          """
            print errorstring
            return None
        
        for lemma in self.synset(synset_identifier).lemmas:
            if lemma_name == lemma.name:
                return lemma
            
        raise GermaNetError("Lemma not found")
            
    def lemmas(self, name, pos=None):
        """
        @type name: string
        @param name: An actual word    
        @return: A list of all L{Lemma} Objects with the orth_form <name>
        """   
        sqlstring, params = """SELECT id FROM lex_unit_table 
        WHERE orth_form=? OR old_orth_form=? OR orth_var=? OR old_orth_var=?""" , (name,name,name,name)
        self._DB.execute(sqlstring,params)
        lemmas = [Lemma(row['id'],self._DB) for row in self._DB.fetchall()]
        if pos is None:
            return lemmas
        else:
            return [lemma for lemma in lemmas if lemma.synset.pos == pos]
    
    def lemma_by_id(self,id):
        """        
        @type id: int
        @param id: a number representing a L{Lemma} (as stored in the germanet database)    
        @return: A single L{Lemma} Object
        """
        return Lemma(id,self._DB)
    
    def synset_by_id(self,id):
        """        
        @type id: int
        @param id: a number representing a L{Synset} (as stored in the germanet database)    
        @return: A single L{Synset} Object
        """
        return Synset(id,self._DB)
    
    def all_lemma_names(self, pos=None):
        """
        @type pos: string
        @param pos: part of speech constant  
        @return: a list of all lemma names with this pos. If pos is None it returns all lemma names.
        """
        if pos is None:        
            sqlstring = "SELECT orth_form FROM lex_unit_table"
            params = None
        else:
            sqlstring,params = """SELECT orth_form FROM lex_unit_table WHERE synset_id IN 
            (SELECT id FROM synset_table WHERE word_category_id =
            (SELECT id FROM word_category_table WHERE word_category = ? ))""" , (POS_TO_WC.get(pos,pos),)
        self._DB.execute(sqlstring,params)
        return [row['orth_form'] for row in self._DB.fetchall()]            
        
    def all_synsets(self, pos=None):
        """
        @type pos: string
        @param pos: part of speech constant
        @return: a list of all L{Synset} Objects with this pos. If pos is None it returns all Synsets.
        """
        if pos is None:
            sqlstring = "SELECT id FROM synset_table"
            params = None
        else:
            sqlstring,params = """SELECT id FROM synset_table WHERE word_category_id =
            (SELECT id FROM word_category_table WHERE word_category = ? )""" , (POS_TO_WC.get(pos,pos),)
        self._DB.execute(sqlstring,params)
        return [Synset(row['id'],self._DB) for row in self._DB.fetchall()]
    
    def path_similarity(self, synset1, synset2, verbose=False):
        return synset1.path_similarity(synset2, verbose)
    path_similarity.__doc__ = Synset.path_similarity.__doc__
    
    def wup_similarity(self, synset1, synset2, verbose=False):
        return synset1.wup_similarity(synset2, verbose)
    wup_similarity.__doc__ = Synset.wup_similarity.__doc__

