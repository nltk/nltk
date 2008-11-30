# Natural Language Toolkit: Generating referring expressions
#
# Author: Margaret Mitchell <itallow@u.washington.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys
import re

class IncrementalAlgorithm:
    """ 
    An implementation of the Incremental Algorithm, introduced in:
    Dale, Robert and Reiter, Ehud. (1995). 
    "Computational Interpretations of the Gricean Maxims 
     in the Generation of Referring Expressions".
    Cognitive Science, 18, 233-263.
    """

    def __init__(self, KB, r, contrast_set, preferred_attrs):
        self.L = []
        self.KB = KB
        self.r = r
        self.C = contrast_set
        self.P = preferred_attrs
        self.RE = self.make_referring_expression()
        
    def make_referring_expression(self):
        """
        This returns a list of attribute-value pairs which
        specify a referring expression for the intended referent.
        The attributes are tried in the order specified in self.P,
        the preferred attributes list, and a value for 'type' is always
        included, even if 'type' has no discriminatory power.        
        """

        for attr in self.P:
            if attr in self.r:
                value = self.find_best_value(attr, \
                                       self.KB.basic_level_value(self.r, attr))
            else:
                continue
            rules_out_list = self.rules_out((attr, value))
            if rules_out_list != []:
                self.L += [(attr, value)]
                for distractor in rules_out_list:
                    self.C.remove(distractor)
            if self.C == []:
                head_noun = False
                # Catch-all to make sure that the head noun, 'type', 
                # is included.
                for attr_value in self.L:
                    if "type" == attr_value[0]:
                        head_noun = True
                if head_noun == False:
                    self.L = [("type", \
                           self.KB.basic_level_value(self.r, "type"))] + self.L
                else:
                    return self.L

    def find_best_value(self, attr, init_val):
        """
        Takes an attribute and an initial value; it returns a value 
        for that attribute that is subsumed by the initial value, 
        accurately describes the intended referent, rules out as many 
        distractors as possible, and, subject to these constraints, 
        is as close as possible in the taxonomy to the initial value.
        """

        if self.KB.user_knows(self.r, (attr, init_val)):
            value = init_val
        else:
            value = None

        more_specific_value = self.KB.more_specific_value(self.r, attr, value)
        if more_specific_value is not None:
            new_value = self.find_best_value(attr, more_specific_value)
            if new_value is not None and \
            self.rules_out((attr, new_value)) > self.rules_out((attr, value)):
                value = new_value
        return value

    def rules_out(self, attr_value_pair):
        """
        Takes an attribute-value pair and returns the elements of the
        set of remaining distractors that are ruled out by this
        attribute-value pair.
        """        
        
        attr = attr_value_pair[0]
        value = attr_value_pair[1]
        if value is None:
            return []
        rules_out_list = []
        for distractor in self.C:
            if self.KB.user_knows(distractor, (attr, value)) is False:
                rules_out_list += [distractor]
        return rules_out_list


class BackgroundKnowledge:
    """
    Interface functions required by the Incremental Algorithm.
    Although these functions are included for use here, 
    their nature varies depending on the program using them,
    and should in practice be created independently of this module.
    """

    def __init__(self, specificity_hash, user_knowledge=None):
        self.specificity_hash = specificity_hash
        self.user_knowledge = user_knowledge

        if user_knowledge is None:
            self.user_knowledge = specificity_hash

    def more_specific_value(self, entity, attr, value):
        """ 
        Returns a new value for 'attr' where that value is 
        more specific than 'value'.  If no more specific 
        value of 'attr' is known, returns None. 
        """
        
        if value in self.specificity_hash:
            spec_tuples = self.specificity_hash[value]
            val_list = []
            found_vals = self._recurse_values(spec_tuples, val_list)
            for found_val in found_vals:
                if found_val == entity[attr] or len(found_vals) == 1:
                    return found_val
        else:
            for basic_value in self.specificity_hash:
                spec_tuples = self.specificity_hash[basic_value]
                spec_val = self._find_more_specific_val(spec_tuples, value)
                if spec_val is not None:
                    return spec_val
        return None

    def _find_more_specific_val(self, spec_tuples, value):
        """
        Recursively searches for a more specific value for a given value.
        """

        x = 0
        while x < len(spec_tuples):
            spec_val = spec_tuples[x]
            if spec_val == value:
                new_val = spec_tuples[x + 1]
                if new_val == str(new_val):
                    return new_val
                elif spec_val == tuple(spec_val):
                    new_val = self._find_more_specific_val(spec_val, value)
                    if new_val is not None:
                        return new_val
            x += 1  
        return None

    def basic_level_value(self, entity, attr):
        """ 
        Returns the basic-level value of an attribute of an object. 
        """

        value = entity[attr]
        for basic_value in self.specificity_hash:
            spec_tuples = self.specificity_hash[basic_value]
            val_list = []
            found_vals = self._recurse_values(spec_tuples, val_list)
            for found_val in found_vals:
                if found_val == value:
                    value = basic_value
                    break
        return value

    def _recurse_values(self, spec_tuples, val_list):
        """
        Function used by basic_level_value to return a non-nested
        list of values under a basic level.  This is helpful when
        it doesn't matter how specific the value is, what matters
        is what its basic level value is.
        """

        for sub_val in spec_tuples:
            if sub_val == str(sub_val):
                val_list += [sub_val]
            if sub_val == tuple(sub_val):
                return self._recurse_values(sub_val, val_list)
        return val_list

    # For now, the user knowledge is the same as the specificity list.
    # This could be expanded to use wordnet as the wordnet modules expand.
    def user_knows(self, entity, attr_value_pair):
        """ 
        Returns true if the user knows or can easily determine
        that the attribute-value pair applies to the object;
        false if the user knows or can easily determine that the
        attribute-value pair does not apply to the object;
        and None otherwise.  
        """

        attr = attr_value_pair[0]
        value = attr_value_pair[1]
        if value == tuple(value):
            for spec_value in value:
                return self.user_knows(entity, (attr, spec_value))
        elif attr in entity:
            if value in entity[attr]:
                return True
            else:
                for gen_value in self.user_knowledge:
                    if gen_value == value:
                        spec_values = self.user_knowledge[gen_value]
                        for spec_value in spec_values:
                            if self.user_knows(entity, (attr, spec_value)):
                                return True
            return False
        return None
        
def demo():
    specificity_hash = {"dog" : (("chihuahua", "long-haired chihuahua"), "poodle"),
                        "cat" : ("siamese-cat", "tabby")}
    KB = BackgroundKnowledge(specificity_hash)
    Object1 = {"type":"chihuahua", "size":"small", "colour":"black"}
    Object2 = {"type":"chihuahua", "size":"large", "colour":"white"}
    Object3 = {"type":"siamese-cat", "size":"small", "colour":"black"}

    print "Given an entity defined as: "
    r = Object1
    print r
    preferred_attrs = ["type", "colour", "size"]
    print "In a set defined as: "
    contrast_set = [Object2, Object3]
    print contrast_set
    RE = IncrementalAlgorithm(KB, r, contrast_set, preferred_attrs).RE
    print "The referring expression created to uniquely identify",
    print "the referent is: "
    print RE
    RE_string = ""
    for attr, val in RE:
        RE_string = val + " " + RE_string
    RE_string = "The " + RE_string    
    print "This can be surface-realized as:"
    print RE_string

if __name__ == "__main__":
    demo()
