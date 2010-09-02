# Natural Language Toolkit: Interface to Boxer
# <http://svn.ask.it.usyd.edu.au/trac/candc/wiki/boxer>
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2010 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import with_statement
import os
import subprocess
import operator
from optparse import OptionParser
import tempfile

import nltk
from nltk.sem.logic import *
from nltk.sem.drt import *
from nltk.internals import Counter

"""
An interface to Boxer.

Usage:
  Set the environment variable CANDCHOME to the bin directory of your CandC installation.
  The models directory should be in the CandC root directory.
  For example:
     /path/to/candc/
        bin/
            candc
            boxer
        models/
            boxer/
"""

class Boxer(object):
    """
    This class is used to parse a sentence using Boxer into an NLTK DRS 
    object.  The BoxerDrsParser class is used for the actual conversion.
    """

    def __init__(self, boxer_drs_interpreter=None):
        if boxer_drs_interpreter is None:
            boxer_drs_interpreter = NltkDrtBoxerDrsInterpreter()
        self._boxer_drs_interpreter = boxer_drs_interpreter
    
        self._boxer_bin = None
        self._candc_bin = None
        self._candc_models_path = None

    def interpret(self, input, discourse_id=None, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param input: C{str} Input sentence to parse
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_id: C{str} An identifier to be inserted to each occurrence-indexed predicate.
        @return: C{drt.AbstractDrs}
        """
        discourse_ids = [discourse_id] if discourse_id is not None else None 
        return self.batch_interpret_multisentence([[input]], discourse_ids, verbose)[0]
    
    def interpret_multisentence(self, input, discourse_id=None, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param input: C{list} of C{str} Input sentences to parse as a single discourse
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_id: C{str} An identifier to be inserted to each occurrence-indexed predicate.
        @return: C{drt.AbstractDrs}
        """
        discourse_ids = [discourse_id] if discourse_id is not None else None
        return self.batch_interpret_multisentence([input], discourse_ids, verbose)[0]
        
    def batch_interpret(self, inputs, discourse_ids=None, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param inputs: C{list} of C{str} Input sentences to parse as individual discourses
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_ids: C{list} of C{str} Identifiers to be inserted to each occurrence-indexed predicate.
        @return: C{list} of C{drt.AbstractDrs}
        """
        return self.batch_interpret_multisentence([[input] for input in inputs], discourse_ids, verbose)

    def batch_interpret_multisentence(self, inputs, discourse_ids=None, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param inputs: C{list} of C{list} of C{str} Input discourses to parse
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_ids: C{list} of C{str} Identifiers to be inserted to each occurrence-indexed predicate.
        @return: C{drt.AbstractDrs}
        """
        _, temp_filename = tempfile.mkstemp(prefix='boxer-', suffix='.in', text=True)

        if discourse_ids is not None:
            assert len(inputs) == len(discourse_ids)
            assert all(id is not None for id in discourse_ids)
            use_disc_id = True
        else:
            discourse_ids = map(str, xrange(len(inputs)))
            use_disc_id = False
            
        candc_out = self._call_candc(inputs, discourse_ids, temp_filename, verbose=verbose)
        boxer_out = self._call_boxer(temp_filename, verbose=verbose)

        os.remove(temp_filename)

#        if 'ERROR: input file contains no ccg/2 terms.' in boxer_out:
#            raise UnparseableInputException('Could not parse with candc: "%s"' % input_str)

        drs_dict = self._parse_to_drs_dict(boxer_out, use_disc_id)
        return [drs_dict.get(id, None) for id in discourse_ids]
        
    def _call_candc(self, inputs, discourse_ids, filename, verbose=False):
        """
        Call the C{candc} binary with the given input.

        @param inputs: C{list} of C{list} of C{str} Input discourses to parse
        @param discourse_ids: C{list} of C{str} Identifiers to be inserted to each occurrence-indexed predicate.
        @param filename: C{str} A filename for the output file
        @return: stdout
        """
        if self._candc_bin is None:
            self._candc_bin = self._find_binary('candc', verbose)
        if self._candc_models_path is None:
            self._candc_models_path = os.path.normpath(os.path.join(self._candc_bin[:-5], '../models'))
        args = ['--models', os.path.join(self._candc_models_path, 'boxer'), 
                '--output', filename]

        return self._call('\n'.join(sum((["<META>'%s'" % id] + d for d,id in zip(inputs,discourse_ids)), [])), self._candc_bin, args, verbose)

    def _call_boxer(self, filename, verbose=False):
        """
        Call the C{boxer} binary with the given input.
    
        @param filename: C{str} A filename for the input file
        @return: stdout
        """
        if self._boxer_bin is None:
            self._boxer_bin = self._find_binary('boxer', verbose)
        args = ['--box', 'false', 
                '--semantics', 'drs',
                '--flat', 'false',
                '--resolve', 'true',
                '--elimeq', 'true',
                '--format', 'prolog',
                '--instantiate', 'true',
                '--input', filename]

        return self._call(None, self._boxer_bin, args, verbose)

    def _find_binary(self, name, verbose=False):
        return nltk.internals.find_binary(name, 
            env_vars=['CANDCHOME'],
            url='http://svn.ask.it.usyd.edu.au/trac/candc/',
            binary_names=[name, name + '.exe'],
            verbose=verbose)
    
    def _call(self, input_str, binary, args=[], verbose=False):
        """
        Call the binary with the given input.
    
        @param input_str: A string whose contents are used as stdin.
        @param binary: The location of the binary to call
        @param args: A list of command-line arguments.
        @return: stdout
        """
        if verbose:
            print 'Calling:', binary
            print 'Args:', args
            print 'Input:', input_str
            print 'Command:', binary + ' ' + ' '.join(args)
        
        # Call via a subprocess
        if input_str is None:
            cmd = [binary] + args
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            cmd = 'echo "%s" | %s %s' % (input_str, binary, ' '.join(args))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = p.communicate()
        
        if verbose:
            print 'Return code:', p.returncode
            if stdout: print 'stdout:\n', stdout, '\n'
            if stderr: print 'stderr:\n', stderr, '\n'
        if p.returncode != 0:
            raise Exception('ERROR CALLING: %s %s\nReturncode: %d\n%s' % (binary, ' '.join(args), p.returncode, stderr))
            
        return stdout

    def _parse_to_drs_dict(self, boxer_out, use_disc_id):
        lines = boxer_out.split('\n')
        drs_dict = {}
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('id('):
                comma_idx = line.index(',')
                discourse_id = line[3:comma_idx]
                if discourse_id[0] == "'" and discourse_id[-1] == "'":
                    discourse_id = discourse_id[1:-1]
                drs_id = line[comma_idx+1:line.index(')')]
                line = lines[i+4]
                assert line.startswith('sem(%s,' % drs_id)
                line = lines[i+8]
                assert line.endswith(').')
                drs_input = line[:-2].strip()
                parsed = self._parse_drs(drs_input, discourse_id, use_disc_id)
                drs_dict[discourse_id] = self._boxer_drs_interpreter.interpret(parsed)
                i += 8
            i += 1
        return drs_dict
    
    def _parse_drs(self, drs_string, discourse_id, use_disc_id):
        return BoxerDrsParser(discourse_id if use_disc_id else None).parse(drs_string)


class BoxerDrsParser(DrtParser):
    def __init__(self, discourse_id=None):
        """
        This class is used to parse the Prolog DRS output from Boxer into a
        hierarchy of python objects.
        """
        DrtParser.__init__(self)
        self.discourse_id = discourse_id
        self.sentence_id_offset = None
        self.quote_chars = [("'", "'", "\\", False)]
        self._label_counter = None
        
    def parse(self, data, signature=None):
        self._label_counter = Counter()
        return DrtParser.parse(self, data, signature)
    
    def get_all_symbols(self):
        return ['(', ')', ',', '[', ']',':']

    def handle(self, tok, context):
        return self.handle_drs(tok)
    
    def attempt_adjuncts(self, expression, context):
        return expression

    def parse_condition(self, indices):
        """
        Parse a DRS condition

        @return: C{list} of C{AbstractDrs}
        """
        tok = self.token()
        accum = self.handle_condition(tok, indices)
        if accum is None:
            raise UnexpectedTokenException(tok)
        return accum

    def handle_drs(self, tok):
        if tok == 'drs':
            return self.parse_drs()
        elif tok in ['merge', 'smerge']:
            return self._handle_binary_expression(None, [], self._make_merge_expression)
        
    def handle_condition(self, tok, indices):
        """
        Handle a DRS condition

        @param indices: C{list} of C{int}
        @return: C{list} of C{AbstractDrs}
        """
        sent_index, word_indices = self._sent_and_word_indices(indices)
        
        if tok == 'not':
            return [self._handle_not()]

        elif tok == 'or':
            return [self._handle_binary_expression(sent_index, word_indices, self._make_or_expression)]
        elif tok == 'imp':
            return [self._handle_binary_expression(sent_index, word_indices, self._make_imp_expression)]
        elif tok == 'eq':
            return [self._handle_eq(sent_index, word_indices)]
        elif tok == 'prop':
            return [self._handle_prop(sent_index, word_indices)]

        elif tok == 'pred':
            return [self._handle_pred(sent_index, word_indices)]
        elif tok == 'named':
            return [self._handle_named(sent_index, word_indices)]
        elif tok == 'rel':
            return [self._handle_rel(sent_index, word_indices)]
        elif tok == 'timex':
            return self._handle_timex(sent_index, word_indices)
        elif tok == 'card':
            return [self._handle_card(sent_index, word_indices)]

        elif tok == 'whq':
            return [self._handle_whq(sent_index, word_indices)]

    def _handle_not(self):
        self.assertToken(self.token(), '(')
        drs = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return BoxerNot(drs)
    
    def _handle_pred(self, sent_index, word_indices):
        #pred(_G3943, dog, n, 0)
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        name = self.token()
        self.assertToken(self.token(), ',')
        pos = self.token()
        self.assertToken(self.token(), ',')
        sense = self.token()
        self.assertToken(self.token(), ')')
        
        if name=='event' and sent_index is None and ((pos=='n' and sense=='1') or (pos=='v' and sense=='0')):
            return BoxerEvent(variable, name)
        else:
            return BoxerPred(self.discourse_id, sent_index, word_indices, variable, name, pos, sense)

    def _handle_named(self, sent_index, word_indices):
        #named(x0, john, per, 0)
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        name = self.token()
        self.assertToken(self.token(), ',')
        type = self.token()
        self.assertToken(self.token(), ',')
        sense = self.token()
        self.assertToken(self.token(), ')')
        return BoxerNamed(self.discourse_id, sent_index, word_indices, variable, name, type, sense)

    def _handle_rel(self, sent_index, word_indices):
        #rel(_G3993, _G3943, agent, 0)
        self.assertToken(self.token(), '(')
        var1 = self.parse_variable()
        self.assertToken(self.token(), ',')
        var2 = self.parse_variable()
        self.assertToken(self.token(), ',')
        rel = self.token()
        self.assertToken(self.token(), ',')
        sense = self.token()
        self.assertToken(self.token(), ')')
        return BoxerRel(self.discourse_id, sent_index, word_indices, var1, var2, rel, sense)

    def _handle_timex(self, sent_index, word_indices):
        #timex(_G18322, date([]: +, []:'XXXX', [1004]:'04', []:'XX'))
        self.assertToken(self.token(), '(')
        arg = self.parse_variable()
        self.assertToken(self.token(), ',')
        new_conds = self._handle_time_expression(sent_index, word_indices, arg)
        self.assertToken(self.token(), ')')
        return new_conds

    def _handle_time_expression(self, sent_index, word_indices, arg):
        #date([]: +, []:'XXXX', [1004]:'04', []:'XX')
        tok = self.token()
        self.assertToken(self.token(), '(')
        if tok == 'date':
            conds = self._handle_date(arg)
        elif tok == 'time':
            conds = self._handle_time(arg)
        else:
            return None
        self.assertToken(self.token(), ')')
        return [BoxerGeneric(self.discourse_id, sent_index, word_indices, tok, str(arg))] + conds

    def _handle_date(self, arg):
        #[]: +, []:'XXXX', [1004]:'04', []:'XX'
        conds = []
        sent_index, word_indices = self._sent_and_word_indices(self._parse_index_list())
        pol = self.token()
        conds.append(BoxerGeneric(self.discourse_id, sent_index, word_indices, 'pol', str(arg), pol))
        self.assertToken(self.token(), ',')

        sent_index, word_indices = self._sent_and_word_indices(self._parse_index_list())
        year = self.token()
        if year != 'XXXX':
            year = year.replace(':', '_')
            conds.append(BoxerGeneric(self.discourse_id, sent_index, word_indices, 'year', str(arg), year))
        self.assertToken(self.token(), ',')
        
        sent_index, word_indices = self._sent_and_word_indices(self._parse_index_list())
        month = self.token()
        if month != 'XX':
            conds.append(BoxerGeneric(self.discourse_id, sent_index, word_indices, 'month', str(arg), month))
        self.assertToken(self.token(), ',')

        sent_index, word_indices = self._sent_and_word_indices(self._parse_index_list())
        day = self.token()
        if day != 'XX':
            conds.append(BoxerGeneric(self.discourse_id, sent_index, word_indices, 'day', str(arg), day))

        return conds

    def _handle_time(self, arg):
        #time([1018]:'18', []:'XX', []:'XX')
        conds = []
        self._parse_index_list()
        hour = self.token()
        if hour != 'XX':
            conds.append(self._make_atom('r_hour_2',arg,hour))
        self.assertToken(self.token(), ',')

        self._parse_index_list()
        min = self.token()
        if min != 'XX':
            conds.append(self._make_atom('r_min_2',arg,min))
        self.assertToken(self.token(), ',')

        self._parse_index_list()
        sec = self.token()
        if sec != 'XX':
            conds.append(self._make_atom('r_sec_2',arg,sec))

        return conds

    def _handle_card(self, sent_index, word_indices):
        #card(_G18535, 28, ge)
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        value = self.token()
        self.assertToken(self.token(), ',')
        type = self.token()
        self.assertToken(self.token(), ')')
        return BoxerCard(self.discourse_id, sent_index, word_indices, variable, value, type)

    def _handle_prop(self, sent_index, word_indices):
        #prop(_G15949, drs(...))
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        drs = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return BoxerProp(self.discourse_id, sent_index, word_indices, variable, drs)

    def _parse_index_list(self):
        #[1001,1002]:
        indices = []
        self.assertToken(self.token(), '[')
        while self.token(0) != ']':
            indices.append(self.parse_index())
            if self.token(0) == ',':
                self.token() #swallow ','
        self.token() #swallow ']'
        self.assertToken(self.token(), ':')
        return indices
    
    def parse_drs(self):
        #drs([[1001]:_G3943], 
        #    [[1002]:pred(_G3943, dog, n, 0)]
        #   )
        self.assertToken(self.token(), '(')
        self.assertToken(self.token(), '[')
        refs = set()
        while self.token(0) != ']':
            indices = self._parse_index_list()
            refs.add(self.parse_variable())
            if self.token(0) == ',':
                self.token() #swallow ','
        self.token() #swallow ']'
        self.assertToken(self.token(), ',')
        self.assertToken(self.token(), '[')
        conds = []
        while self.token(0) != ']':
            indices = self._parse_index_list()
            conds.extend(self.parse_condition(indices))
            if self.token(0) == ',':
                self.token() #swallow ','
        self.token() #swallow ']'
        self.assertToken(self.token(), ')')
        return BoxerDrs(self._label_counter.get(), list(refs), conds)

    def _handle_binary_expression(self, sent_index, word_indices, make_callback):
        self.assertToken(self.token(), '(')
        drs1 = self.parse_Expression(None)
        self.assertToken(self.token(), ',')
        drs2 = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return make_callback(sent_index, word_indices, drs1, drs2)

    def _handle_eq(self, sent_index, word_indices):
        self.assertToken(self.token(), '(')
        var1 = self.parse_variable()
        self.assertToken(self.token(), ',')
        var2 = self.parse_variable()
        self.assertToken(self.token(), ')')
        return BoxerEq(self.discourse_id, sent_index, word_indices, var1, var2)

    def _handle_whq(self, indices):
        self.assertToken(self.token(), '(')
        self.assertToken(self.token(), '[')
        ans_types = []
        while self.token(0) != ']':
            cat = self.token()
            self.assertToken(self.token(), ':')
            if cat == 'des':
                ans_types.append(self.token())
            elif cat == 'num':
                ans_types.append('number')
                typ = self.token()
                if typ == 'cou':
                    ans_types.append('count')
                else:
                    ans_types.append(typ)
            else:
                ans_types.append(self.token())
        self.token() #swallow the ']'
        self.assertToken(self.token(), ',')
        d1 = self.parse_Expression(None)
        self.assertToken(self.token(), ',')
        ref = DrtVariableExpression(self.parse_variable())
        self.assertToken(self.token(), ',')
        d2 = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        d3 = DRS([],[self._make_atom(self._make_pred('n', f_name, [], 1), ref) for f_name in ans_types])
        return DrtConcatenation(d3,DrtConcatenation(d1,d2))

    def _make_merge_expression(self, sent_index, word_indices, drs1, drs2):
        return BoxerDrs(drs1.label, drs1.refs + drs2.refs, drs1.conds + drs2.conds)

    def _make_or_expression(self, sent_index, word_indices, drs1, drs2):
        return BoxerOr(self.discourse_id, sent_index, word_indices, drs1, drs2)

    def _make_imp_expression(self, sent_index, word_indices, drs1, drs2):
        return BoxerDrs(drs1.label, drs1.refs, drs1.conds, drs2)

    def parse_variable(self):
        var = self.token()
        assert re.match('^x\d+$', var)
        return int(var[1:])
        
    def parse_index(self):
        return int(self.token())
    
    def _sent_and_word_indices(self, indices):
        sent_index, = set((i / 1000)-1 for i in indices if i>=0) if indices else (None,)
        word_indices = [(i % 1000)-1 for i in indices]
        return sent_index, word_indices
        

class AbstractBoxerDrs(object):
    def all_events(self):
        return set()
    
    def atoms(self):
        return set()

    def __hash__(self):
        return hash(str(self))
               
class BoxerDrs(AbstractBoxerDrs):
    def __init__(self, label, refs, conds, consequent=None):
        AbstractBoxerDrs.__init__(self)
        self.label = label
        self.refs = refs
        self.conds = conds
        self.consequent = consequent

    def all_events(self):
        events = reduce(operator.or_, (cond.all_events() for cond in self.conds), set())
        if self.consequent is not None:
            events.update(self.consequent.all_events())
        return events
    
    def atoms(self):
        atoms = reduce(operator.or_, (cond.atoms() for cond in self.conds), set())
        if self.consequent is not None:
            atoms.update(self.consequent.atoms())
        return atoms

    def __repr__(self):
        s = 'drs(%s, [%s], [%s])' % (self.label, 
                                        ', '.join(map(str, self.refs)), 
                                        ', '.join(map(str, self.conds)))
        if self.consequent is not None:
            s = 'imp(%s, %s)' % (s, self.consequent)
        return s
        
class BoxerNot(AbstractBoxerDrs):
    def __init__(self, drs):
        AbstractBoxerDrs.__init__(self)
        self.drs = drs

    def all_events(self):
        return self.drs.all_events()
    
    def atoms(self):
        return self.drs.atoms()

    def __repr__(self):
        return 'not(%s)' % (self.drs)
        
class BoxerEvent(AbstractBoxerDrs):
    def __init__(self, var, name):
        AbstractBoxerDrs.__init__(self)
        self.var = var
        self.name = name

    def all_events(self):
        return set([self.var])

    def __repr__(self):
        return 'event(%s)' % (self.var)

class BoxerIndexed(AbstractBoxerDrs):
    def __init__(self, discourse_id, sent_index, word_indices):
        AbstractBoxerDrs.__init__(self)
        self.discourse_id = discourse_id
        self.sent_index = sent_index
        self.word_indices = word_indices

    def __eq__(self, other):
        return self.__class__ == other.__class__ and all(s==o for s,o in zip(self, other))
    
    def atoms(self):
        return set([self])
    
    def __repr__(self):
        s = '%s(%s, %s, [%s]' % (self._pred(), self.discourse_id, self.sent_index, ', '.join(map(str, self.word_indices)))
        for v in self:
            s += ', %s' % v
        return s + ')'

class BoxerPred(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, name, pos, sense):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.name = name
        self.pos = pos
        self.sense = sense
        
    def change_var(self, var):
        return BoxerPred(self.discourse_id, self.sent_index, self.word_indices, var, self.name, self.pos, self.sense)
        
    def __iter__(self):
        return iter((self.var, self.name, self.pos, self.sense))
    
    def _pred(self):
        return 'pred'

class BoxerNamed(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, name, type, sense):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.name = name
        self.type = type
        self.sense = sense

    def change_var(self, var):
        return BoxerNamed(self.discourse_id, self.sent_index, self.word_indices, var, self.name, self.type, self.sense)
        
    def __iter__(self):
        return iter((self.var, self.name, self.type, self.sense))

    def _pred(self):
        return 'named'

class BoxerRel(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var1, var2, rel, sense):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var1 = var1
        self.var2 = var2
        self.rel = rel
        self.sense = sense

    def __iter__(self):
        return iter((self.var1, self.var2, self.rel, self.sense))
        
    def _pred(self):
        return 'rel'
        
class BoxerProp(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, drs):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.drs = drs
        
    def all_events(self):
        return self.drs.all_events()

    def referenced_labels(self):
        return set([self.drs])

    def atoms(self):
        return self.drs.atoms()

    def __iter__(self):
        return iter((self.var, self.drs))
        
    def _pred(self):
        return 'prop'
        
class BoxerEq(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var1, var2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var1 = var1
        self.var2 = var2
        
    def __iter__(self):
        return iter((self.var1, self.var2))
        
    def _pred(self):
        return 'eq'

class BoxerCard(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, value, type):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.value = value
        self.type = type
        
    def __iter__(self):
        return iter((self.var, self.value, self.type))
        
    def _pred(self):
        return 'card'
    
class BoxerOr(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, drs1, drs2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.drs1 = drs1
        self.drs2 = drs2
        
    def __iter__(self):
        return iter((self.drs1, self.drs2))
        
    def _pred(self):
        return 'or'
    
class BoxerGeneric(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, pred, *args):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.pred = pred
        self.args = args
        
    def __iter__(self):
        return iter((self.args))
        
    def _pred(self):
        return self.pred
    


class PassthroughBoxerDrsInterpreter(object):
    def interpret(self, ex):
        return ex
    

class NltkDrtBoxerDrsInterpreter(object):
    def __init__(self, occur_index=False):
        self._occur_index = occur_index
    
    def interpret(self, ex):
        """
        @param ex: C{AbstractBoxerDrs}
        @return: C{AbstractDrs}
        """
        return self._interpret(ex)

    def _interpret(self, ex):
        if isinstance(ex, BoxerDrs):
            drs = DRS([Variable('x%d' % r) for r in ex.refs], map(self._interpret, ex.conds))
            if ex.label is not None:
                drs.label = Variable('x%d' % ex.label)
            if ex.consequent is not None:
                drs.consequent = self._interpret(ex.consequent)
            return drs
        elif isinstance(ex, BoxerNot):
            return DrtNegatedExpression(self._interpret(ex.drs))
        elif isinstance(ex, BoxerEvent):
            return self._make_atom('event', 'x%d' % ex.var)
        elif isinstance(ex, BoxerPred):
            pred = self._add_occur_indexing('%s_%s' % (ex.pos, ex.name), ex)
            return self._make_atom(pred, 'x%d' % ex.var)
        elif isinstance(ex, BoxerNamed):
            pred = self._add_occur_indexing('ne_%s_%s' % (ex.type, ex.name), ex)
            return self._make_atom(pred, 'x%d' % ex.var)
        elif isinstance(ex, BoxerRel):
            pred = self._add_occur_indexing('%s' % (ex.rel), ex)
            return self._make_atom(pred, 'x%d' % ex.var1, 'x%d' % ex.var2)
        elif isinstance(ex, BoxerProp):
            return DrtProposition(Variable('x%d' % ex.var), self._interpret(ex.drs))
        elif isinstance(ex, BoxerEq):
            return DrtEqualityExpression(DrtVariableExpression(Variable('x%d' % ex.var1)), 
                                         DrtVariableExpression(Variable('x%d' % ex.var2)))
        elif isinstance(ex, BoxerCard):
            pred = self._add_occur_indexing('card_%s_%s' % (ex.type, ex.value), ex)
            return self._make_atom(pred, 'x%d' % ex.var)
        elif isinstance(ex, BoxerOr):
            return DrtOrExpression(self._interpret(ex.drs1), self._interpret(ex.drs2))
        elif isinstance(ex, BoxerGeneric):
            return self._make_atom(ex.pred, *ex.args)
        assert False, '%s: %s' % (ex.__class__.__name__, ex)

    def _make_atom(self, pred, *args):
        accum = DrtVariableExpression(Variable(pred))
        for arg in args:
            accum = DrtApplicationExpression(accum, DrtVariableExpression(Variable(arg)))
        return accum

    def _add_occur_indexing(self, base, ex):
        if self._occur_index and ex.sent_index is not None:
            if ex.discourse_id:
                base += '_%s'  % ex.discourse_id
            base += '_s%s' % ex.sent_index
            base += '_w%s' % sorted(ex.word_indices)[0]
        return base


class UnparseableInputException(Exception):
    pass


if __name__ == '__main__':
    opts = OptionParser("usage: %prog TEXT [options]")
    opts.add_option("--verbose", "-v", help="display verbose logs", action="store_true", default=False, dest="verbose")
    opts.add_option("--fol", "-f", help="output FOL", action="store_true", default=False, dest="fol")
    opts.add_option("--occur", "-o", help="occurrence index", action="store_true", default=False, dest="occur_index")
    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error("incorrect number of arguments")

    interpreter = NltkDrtBoxerDrsInterpreter(occur_index=options.occur_index)
    drs = Boxer(interpreter).interpret_multisentence(args[0].split('\n'), verbose=options.verbose)
    if drs is None:
        print None
    else:
        drs = drs.simplify().eliminate_equality()
        if options.fol:
            print drs.fol().normalize()
        else:
            drs.normalize().pprint()
