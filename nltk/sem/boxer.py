# Natural Language Toolkit: Interface to Boxer
# <http://svn.ask.it.usyd.edu.au/trac/candc/wiki/boxer>
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2011 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import subprocess
from optparse import OptionParser
import tempfile
import operator

import nltk
from nltk.sem.logic import *
from nltk.sem.drt import *

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
    This class is an interface to Johan Bos's program Boxer, a wide-coverage
    semantic parser that produces Discourse Representation Structures (DRSs).
    """

    def __init__(self, boxer_drs_interpreter=None, elimeq=False, bin_dir=None, verbose=False):
        """
        @param boxer_drs_interpreter: A class that converts from the 
        C{AbstractBoxerDrs} object hierarchy to a different object.  The 
        default is C{NltkDrtBoxerDrsInterpreter}, which converts to the NLTK 
        DRT hierarchy.
        @param elimeq: When set to true, Boxer removes all equalities from the 
        DRSs and discourse referents standing in the equality relation are 
        unified, but only if this can be done in a meaning-preserving manner. 
        """
        if boxer_drs_interpreter is None:
            boxer_drs_interpreter = NltkDrtBoxerDrsInterpreter()
        self._boxer_drs_interpreter = boxer_drs_interpreter
        
        self._elimeq = elimeq

        self.set_bin_dir(bin_dir, verbose)
        
    def set_bin_dir(self, bin_dir, verbose=False):
        self._candc_bin = self._find_binary('candc', bin_dir, verbose)
        self._candc_models_path = os.path.normpath(os.path.join(self._candc_bin[:-5], '../models'))
        self._boxer_bin = self._find_binary('boxer', bin_dir, verbose)            

    def interpret(self, input, discourse_id=None, question=False, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param input: C{str} Input sentence to parse
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_id: C{str} An identifier to be inserted to each occurrence-indexed predicate.
        @return: C{drt.AbstractDrs}
        """
        if discourse_id is not None:
            discourse_ids = [discourse_id]
        else:
            discourse_ids = None
        d, = self.batch_interpret_multisentence([[input]], discourse_ids, question, verbose)
        if not d:
            raise Exception('Unable to interpret: "%s"' % input)
        return d
    
    def interpret_multisentence(self, input, discourse_id=None, question=False, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param input: C{list} of C{str} Input sentences to parse as a single discourse
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_id: C{str} An identifier to be inserted to each occurrence-indexed predicate.
        @return: C{drt.AbstractDrs}
        """
        if discourse_id is not None:
            discourse_ids = [discourse_id]
        else:
            discourse_ids = None
        d, = self.batch_interpret_multisentence([input], discourse_ids, question, verbose)
        if not d:
            raise Exception('Unable to interpret: "%s"' % input)
        return d
        
    def batch_interpret(self, inputs, discourse_ids=None, question=False, verbose=False):
        """
        Use Boxer to give a first order representation.
        
        @param inputs: C{list} of C{str} Input sentences to parse as individual discourses
        @param occur_index: C{boolean} Should predicates be occurrence indexed?
        @param discourse_ids: C{list} of C{str} Identifiers to be inserted to each occurrence-indexed predicate.
        @return: C{list} of C{drt.AbstractDrs}
        """
        return self.batch_interpret_multisentence([[input] for input in inputs], discourse_ids, question, verbose)

    def batch_interpret_multisentence(self, inputs, discourse_ids=None, question=False, verbose=False):
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
            assert reduce(operator.and_, (id is not None for id in discourse_ids))
            use_disc_id = True
        else:
            discourse_ids = map(str, xrange(len(inputs)))
            use_disc_id = False
            
        candc_out = self._call_candc(inputs, discourse_ids, question, temp_filename, verbose=verbose)
        boxer_out = self._call_boxer(temp_filename, verbose=verbose)

        os.remove(temp_filename)

#        if 'ERROR: input file contains no ccg/2 terms.' in boxer_out:
#            raise UnparseableInputException('Could not parse with candc: "%s"' % input_str)

        drs_dict = self._parse_to_drs_dict(boxer_out, use_disc_id)
        return [drs_dict.get(id, None) for id in discourse_ids]
        
    def _call_candc(self, inputs, discourse_ids, question, filename, verbose=False):
        """
        Call the C{candc} binary with the given input.

        @param inputs: C{list} of C{list} of C{str} Input discourses to parse
        @param discourse_ids: C{list} of C{str} Identifiers to be inserted to each occurrence-indexed predicate.
        @param filename: C{str} A filename for the output file
        @return: stdout
        """
        args = ['--models', os.path.join(self._candc_models_path, ['boxer','questions'][question]), 
                '--output', filename,
                '--candc-printer', 'boxer']
        return self._call('\n'.join(sum((["<META>'%s'" % id] + d for d,id in zip(inputs,discourse_ids)), [])), self._candc_bin, args, verbose)

    def _call_boxer(self, filename, verbose=False):
        """
        Call the C{boxer} binary with the given input.
    
        @param filename: C{str} A filename for the input file
        @return: stdout
        """
        args = ['--box', 'false', 
                '--semantics', 'drs',
                '--flat', 'false',
                '--resolve', 'true',
                '--elimeq', ['false','true'][self._elimeq],
                '--format', 'prolog',
                '--instantiate', 'true',
                '--input', filename]

        return self._call(None, self._boxer_bin, args, verbose)

    def _find_binary(self, name, bin_dir, verbose=False):
        return nltk.internals.find_binary(name, 
            path_to_bin=bin_dir,
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
                i += 1
                line = lines[i]
                assert line.startswith('sem(%s,' % drs_id)
                
                i += 4
                line = lines[i]
                assert line.endswith(').')
                drs_input = line[:-2].strip()
                parsed = self._parse_drs(drs_input, discourse_id, use_disc_id)
                drs_dict[discourse_id] = self._boxer_drs_interpreter.interpret(parsed)
            i += 1
        return drs_dict
    
    def _parse_drs(self, drs_string, discourse_id, use_disc_id):
        return BoxerOutputDrsParser([None,discourse_id][use_disc_id]).parse(drs_string)


class BoxerOutputDrsParser(DrtParser):
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
        self._label_counter = Counter(-1)
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
            return self._handle_binary_expression(self._make_merge_expression)(None, [])
        
    def handle_condition(self, tok, indices):
        """
        Handle a DRS condition

        @param indices: C{list} of C{int}
        @return: C{list} of C{AbstractDrs}
        """
        if tok == 'not':
            return [self._handle_not()]
    
        if tok == 'or':
            conds = [self._handle_binary_expression(self._make_or_expression)]
        elif tok == 'imp':
            conds = [self._handle_binary_expression(self._make_imp_expression)]
        elif tok == 'eq':
            conds = [self._handle_eq()]
        elif tok == 'prop':
            conds = [self._handle_prop()]

        elif tok == 'pred':
            conds = [self._handle_pred()]
        elif tok == 'named':
            conds = [self._handle_named()]
        elif tok == 'rel':
            conds = [self._handle_rel()]
        elif tok == 'timex':
            conds = self._handle_timex()
        elif tok == 'card':
            conds = [self._handle_card()]

        elif tok == 'whq':
            conds = [self._handle_whq()]
        
        else:
            conds = []
            
        return sum([[cond(sent_index, word_indices) for cond in conds] for sent_index, word_indices in self._sent_and_word_indices(indices)], [])

    def _handle_not(self):
        self.assertToken(self.token(), '(')
        drs = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return BoxerNot(drs)
    
    def _handle_pred(self):
        #pred(_G3943, dog, n, 0)
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        name = self.token()
        self.assertToken(self.token(), ',')
        pos = self.token()
        self.assertToken(self.token(), ',')
        sense = int(self.token())
        self.assertToken(self.token(), ')')
        
        def _handle_pred_f(sent_index, word_indices):
            if name=='event' and sent_index is None and ((pos=='n' and sense==1) or (pos=='v' and sense==0)):
                return BoxerEvent(variable)
            else:
                return BoxerPred(self.discourse_id, sent_index, word_indices, variable, name, pos, sense)
        return _handle_pred_f
        
    def _handle_named(self):
        #named(x0, john, per, 0)
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        name = self.token()
        self.assertToken(self.token(), ',')
        type = self.token()
        self.assertToken(self.token(), ',')
        sense = int(self.token())
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: BoxerNamed(self.discourse_id, sent_index, word_indices, variable, name, type, sense)

    def _handle_rel(self):
        #rel(_G3993, _G3943, agent, 0)
        self.assertToken(self.token(), '(')
        var1 = self.parse_variable()
        self.assertToken(self.token(), ',')
        var2 = self.parse_variable()
        self.assertToken(self.token(), ',')
        rel = self.token()
        self.assertToken(self.token(), ',')
        sense = int(self.token())
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: BoxerRel(self.discourse_id, sent_index, word_indices, var1, var2, rel, sense)

    def _handle_timex(self):
        #timex(_G18322, date([]: (+), []:'XXXX', [1004]:'04', []:'XX'))
        self.assertToken(self.token(), '(')
        arg = self.parse_variable()
        self.assertToken(self.token(), ',')
        new_conds = self._handle_time_expression(arg)
        self.assertToken(self.token(), ')')
        return new_conds

    def _handle_time_expression(self, arg):
        #date([]: (+), []:'XXXX', [1004]:'04', []:'XX')
        tok = self.token()
        self.assertToken(self.token(), '(')
        if tok == 'date':
            conds = self._handle_date(arg)
        elif tok == 'time':
            conds = self._handle_time(arg)
        else:
            return None
        self.assertToken(self.token(), ')')
        return [lambda sent_index, word_indices: BoxerPred(self.discourse_id, sent_index, word_indices, arg, tok, 'n', 0)] + \
               [lambda sent_index, word_indices: cond for cond in conds]

    def _handle_date(self, arg):
        #[]: (+), []:'XXXX', [1004]:'04', []:'XX'
        conds = []
        (sent_index, word_indices), = self._sent_and_word_indices(self._parse_index_list())
        self.assertToken(self.token(), '(')
        pol = self.token()
        self.assertToken(self.token(), ')')
        conds.append(BoxerPred(self.discourse_id, sent_index, word_indices, arg, 'date_pol_%s' % (pol), 'a', 0))
        self.assertToken(self.token(), ',')

        (sent_index, word_indices), = self._sent_and_word_indices(self._parse_index_list())
        year = self.token()
        if year != 'XXXX':
            year = year.replace(':', '_')
            conds.append(BoxerPred(self.discourse_id, sent_index, word_indices, arg, 'date_year_%s' % (year), 'a', 0))
        self.assertToken(self.token(), ',')
        
        (sent_index, word_indices), = self._sent_and_word_indices(self._parse_index_list())
        month = self.token()
        if month != 'XX':
            conds.append(BoxerPred(self.discourse_id, sent_index, word_indices, arg, 'date_month_%s' % (month), 'a', 0))
        self.assertToken(self.token(), ',')

        (sent_index, word_indices), = self._sent_and_word_indices(self._parse_index_list())
        day = self.token()
        if day != 'XX':
            conds.append(BoxerPred(self.discourse_id, sent_index, word_indices, arg, 'date_day_%s' % (day), 'a', 0))

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

    def _handle_card(self):
        #card(_G18535, 28, ge)
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        value = self.token()
        self.assertToken(self.token(), ',')
        type = self.token()
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: BoxerCard(self.discourse_id, sent_index, word_indices, variable, value, type)

    def _handle_prop(self):
        #prop(_G15949, drs(...))
        self.assertToken(self.token(), '(')
        variable = self.parse_variable()
        self.assertToken(self.token(), ',')
        drs = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: BoxerProp(self.discourse_id, sent_index, word_indices, variable, drs)

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
        label = self._label_counter.get()
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
        return BoxerDrs(label, list(refs), conds)

    def _handle_binary_expression(self, make_callback):
        self.assertToken(self.token(), '(')
        drs1 = self.parse_Expression(None)
        self.assertToken(self.token(), ',')
        drs2 = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: make_callback(sent_index, word_indices, drs1, drs2)

    def _handle_eq(self):
        self.assertToken(self.token(), '(')
        var1 = self.parse_variable()
        self.assertToken(self.token(), ',')
        var2 = self.parse_variable()
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: BoxerEq(self.discourse_id, sent_index, word_indices, var1, var2)


    def _handle_whq(self):
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
        ref = self.parse_variable()
        self.assertToken(self.token(), ',')
        d2 = self.parse_Expression(None)
        self.assertToken(self.token(), ')')
        return lambda sent_index, word_indices: BoxerWhq(self.discourse_id, sent_index, word_indices, ans_types, d1, ref, d2)

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
        """
        @return: C{list} of (sent_index, word_indices) tuples
        """
        sent_indices = set((i / 1000)-1 for i in indices if i>=0)
        if sent_indices:
            pairs = []
            for sent_index in sent_indices:
                word_indices = [(i % 1000)-1 for i in indices if sent_index == (i / 1000)-1]
                pairs.append((sent_index, word_indices))
            return pairs
        else:
            word_indices = [(i % 1000)-1 for i in indices]
            return [(None, word_indices)]


class BoxerDrsParser(DrtParser):
    """
    Reparse the str form of subclasses of C{AbstractBoxerDrs}
    """
    def __init__(self, discourse_id=None):
        DrtParser.__init__(self)
        self.discourse_id = discourse_id

    def get_all_symbols(self):
        return [DrtTokens.OPEN, DrtTokens.CLOSE, DrtTokens.COMMA, DrtTokens.OPEN_BRACKET, DrtTokens.CLOSE_BRACKET]

    def attempt_adjuncts(self, expression, context):
        return expression

    def handle(self, tok, context):
        try:
            if tok == 'drs':
                self.assertNextToken(DrtTokens.OPEN)
                label = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                refs = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                conds = self.handle_conds(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerDrs(label, refs, conds)
            elif tok == 'pred':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                variable = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                name = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                pos = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                sense = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerPred(disc_id, sent_id, word_ids, variable, name, pos, sense)
            elif tok == 'named':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                variable = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                name = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                type = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                sense = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerNamed(disc_id, sent_id, word_ids, variable, name, type, sense)
            elif tok == 'rel':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                var1 = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                var2 = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                rel = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                sense = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerRel(disc_id, sent_id, word_ids, var1, var2, rel, sense)
            elif tok == 'event':
                self.assertNextToken(DrtTokens.OPEN)
                var = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerEvent(var)
            elif tok == 'prop':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                variable = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                drs = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerProp(disc_id, sent_id, word_ids, variable, drs)
            elif tok == 'not':
                self.assertNextToken(DrtTokens.OPEN)
                drs = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerNot(drs)
            elif tok == 'imp':
                self.assertNextToken(DrtTokens.OPEN)
                drs1 = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.COMMA)
                drs2 = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerDrs(drs1.label, drs1.refs, drs1.conds, drs2)
            elif tok == 'or':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                drs1 = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.COMMA)
                drs2 = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerOr(disc_id, sent_id, word_ids, drs1, drs2)
            elif tok == 'eq':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                var1 = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                var2 = int(self.token())
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerEq(disc_id, sent_id, word_ids, var1, var2)
            elif tok == 'card':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                var = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                value = self.token()
                self.assertNextToken(DrtTokens.COMMA)
                type = self.token()
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerCard(disc_id, sent_id, word_ids, var, value, type)
            elif tok == 'whq':
                self.assertNextToken(DrtTokens.OPEN)
                disc_id = (self.token(), self.discourse_id)[self.discourse_id is not None]
                self.assertNextToken(DrtTokens.COMMA)
                sent_id = self.nullableIntToken()
                self.assertNextToken(DrtTokens.COMMA)
                word_ids = map(int, self.handle_refs())
                self.assertNextToken(DrtTokens.COMMA)
                ans_types = self.handle_refs()
                self.assertNextToken(DrtTokens.COMMA)
                drs1 = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.COMMA)
                var = int(self.token())
                self.assertNextToken(DrtTokens.COMMA)
                drs2 = self.parse_Expression(None)
                self.assertNextToken(DrtTokens.CLOSE)
                return BoxerWhq(disc_id, sent_id, word_ids, ans_types, drs1, var, drs2)
        except Exception, e:
            raise ParseException(self._currentIndex, str(e))
        assert False, repr(tok)
        
    def nullableIntToken(self):
        t = self.token()
        return [None,int(t)][t != 'None']
    
    def get_next_token_variable(self, description):
        try:
            return self.token()
        except ExpectedMoreTokensException, e:
            raise ExpectedMoreTokensException(e.index, 'Variable expected.')

        

class AbstractBoxerDrs(object):
    def variables(self):
        """
        @return: (set<variables>, set<events>, set<propositions>)
        """
        variables, events, propositions = self._variables()
        return (variables - (events | propositions), events, propositions - events)
    
    def variable_types(self):
        vartypes = {}
        for t,vars in zip(('z','e','p'), self.variables()):
            for v in vars:
                vartypes[v] = t
        return vartypes
    
    def _variables(self):
        """
        @return: (set<variables>, set<events>, set<propositions>)
        """
        return (set(), set(), set())

    def atoms(self):
        return set()

    def clean(self):
        return self
    
    def _clean_name(self, name):
        return name.replace('-','_').replace("'", "_")
    
    def renumber_sentences(self, f):
        return self

    def __hash__(self):
        return hash(str(self))
    
class BoxerDrs(AbstractBoxerDrs):
    def __init__(self, label, refs, conds, consequent=None):
        AbstractBoxerDrs.__init__(self)
        self.label = label
        self.refs = refs
        self.conds = conds
        self.consequent = consequent

    def _variables(self):
        variables = (set(), set(), set())
        for cond in self.conds:
            for s,v in zip(variables, cond._variables()):
                s.update(v)
        if self.consequent is not None:
            for s,v in zip(variables, self.consequent._variables()):
                s.update(v)
        return variables
    
    def atoms(self):
        atoms = reduce(operator.or_, (cond.atoms() for cond in self.conds), set())
        if self.consequent is not None:
            atoms.update(self.consequent.atoms())
        return atoms
    
    def clean(self):
        if self.consequent:
            consequent = self.consequent.clean()
        else:
            consequent = None
        return BoxerDrs(self.label, self.refs, [c.clean() for c in self.conds], consequent)

    def renumber_sentences(self, f):
        if self.consequent:
            consequent = self.consequent.renumber_sentences(f)
        else:
            consequent = None
        return BoxerDrs(self.label, self.refs, [c.renumber_sentences(f) for c in self.conds], consequent)

    def __repr__(self):
        s = 'drs(%s, [%s], [%s])' % (self.label, 
                                        ', '.join(map(str, self.refs)), 
                                        ', '.join(map(str, self.conds)))
        if self.consequent is not None:
            s = 'imp(%s, %s)' % (s, self.consequent)
        return s
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.label == other.label and \
               self.refs == other.refs and \
               len(self.conds) == len(other.conds) and \
               reduce(operator.and_, (c1==c2 for c1,c2 in zip(self.conds, other.conds))) and \
               self.consequent == other.consequent
        
class BoxerNot(AbstractBoxerDrs):
    def __init__(self, drs):
        AbstractBoxerDrs.__init__(self)
        self.drs = drs

    def _variables(self):
        return self.drs._variables()
    
    def atoms(self):
        return self.drs.atoms()

    def clean(self):
        return BoxerNot(self.drs.clean())

    def renumber_sentences(self, f):
        return BoxerNot(self.drs.renumber_sentences(f))

    def __repr__(self):
        return 'not(%s)' % (self.drs)
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.drs == other.drs
        
class BoxerEvent(AbstractBoxerDrs):
    def __init__(self, var):
        AbstractBoxerDrs.__init__(self)
        self.var = var

    def _variables(self):
        return (set(), set([self.var]), set())

    def __repr__(self):
        return 'event(%s)' % (self.var)
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.var == other.var

class BoxerIndexed(AbstractBoxerDrs):
    def __init__(self, discourse_id, sent_index, word_indices):
        AbstractBoxerDrs.__init__(self)
        self.discourse_id = discourse_id
        self.sent_index = sent_index
        self.word_indices = word_indices

    def atoms(self):
        return set([self])
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.discourse_id == other.discourse_id and \
               self.sent_index == other.sent_index and \
               self.word_indices == other.word_indices and \
               reduce(operator.and_, (s==o for s,o in zip(self, other)))
    
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
        
    def _variables(self):
        return (set([self.var]), set(), set())
        
    def change_var(self, var):
        return BoxerPred(self.discourse_id, self.sent_index, self.word_indices, var, self.name, self.pos, self.sense)
        
    def clean(self):
        return BoxerPred(self.discourse_id, self.sent_index, self.word_indices, self.var, self._clean_name(self.name), self.pos, self.sense)

    def renumber_sentences(self, f):
        new_sent_index = f(self.sent_index)
        return BoxerPred(self.discourse_id, new_sent_index, self.word_indices, self.var, self.name, self.pos, self.sense)

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

    def _variables(self):
        return (set([self.var]), set(), set())
        
    def change_var(self, var):
        return BoxerNamed(self.discourse_id, self.sent_index, self.word_indices, var, self.name, self.type, self.sense)
        
    def clean(self):
        return BoxerNamed(self.discourse_id, self.sent_index, self.word_indices, self.var, self._clean_name(self.name), self.type, self.sense)
        
    def renumber_sentences(self, f):
        return BoxerNamed(self.discourse_id, f(self.sent_index), self.word_indices, self.var, self.name, self.type, self.sense)

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

    def _variables(self):
        return (set([self.var1, self.var2]), set(), set())
        
    def clean(self):
        return BoxerRel(self.discourse_id, self.sent_index, self.word_indices, self.var1, self.var2, self._clean_name(self.rel), self.sense)

    def renumber_sentences(self, f):
        return BoxerRel(self.discourse_id, f(self.sent_index), self.word_indices, self.var1, self.var2, self.rel, self.sense)

    def __iter__(self):
        return iter((self.var1, self.var2, self.rel, self.sense))
        
    def _pred(self):
        return 'rel'
        
class BoxerProp(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var, drs):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var = var
        self.drs = drs
        
    def _variables(self):
        return tuple(map(operator.or_, (set(), set(), set([self.var])), self.drs._variables()))
        
    def referenced_labels(self):
        return set([self.drs])

    def atoms(self):
        return self.drs.atoms()
    
    def clean(self):
        return BoxerProp(self.discourse_id, self.sent_index, self.word_indices, self.var, self.drs.clean())

    def renumber_sentences(self, f):
        return BoxerProp(self.discourse_id, f(self.sent_index), self.word_indices, self.var, self.drs.renumber_sentences(f))

    def __iter__(self):
        return iter((self.var, self.drs))
        
    def _pred(self):
        return 'prop'
        
class BoxerEq(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, var1, var2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.var1 = var1
        self.var2 = var2
        
    def _variables(self):
        return (set([self.var1, self.var2]), set(), set())
        
    def atoms(self):
        return set()

    def renumber_sentences(self, f):
        return BoxerEq(self.discourse_id, f(self.sent_index), self.word_indices, self.var1, self.var2)
        
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
        
    def _variables(self):
        return (set([self.var]), set(), set())
        
    def renumber_sentences(self, f):
        return BoxerCard(self.discourse_id, f(self.sent_index), self.word_indices, self.var, self.value, self.type)
        
    def __iter__(self):
        return iter((self.var, self.value, self.type))
        
    def _pred(self):
        return 'card'
    
class BoxerOr(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, drs1, drs2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.drs1 = drs1
        self.drs2 = drs2
        
    def _variables(self):
        return tuple(map(operator.or_, self.drs1._variables(), self.drs2._variables()))

    def atoms(self):
        return self.drs1.atoms() | self.drs2.atoms()

    def clean(self):
        return BoxerOr(self.discourse_id, self.sent_index, self.word_indices, self.drs1.clean(), self.drs2.clean())

    def renumber_sentences(self, f):
        return BoxerOr(self.discourse_id, f(self.sent_index), self.word_indices, self.drs1, self.drs2)
        
    def __iter__(self):
        return iter((self.drs1, self.drs2))
        
    def _pred(self):
        return 'or'
    
class BoxerWhq(BoxerIndexed):
    def __init__(self, discourse_id, sent_index, word_indices, ans_types, drs1, variable, drs2):
        BoxerIndexed.__init__(self, discourse_id, sent_index, word_indices)
        self.ans_types = ans_types
        self.drs1 = drs1
        self.variable = variable
        self.drs2 = drs2
        
    def _variables(self):
        return tuple(map(operator.or_, (set([self.variable]), set(), set()), self.drs1._variables(), self.drs2._variables()))

    def atoms(self):
        return self.drs1.atoms() | self.drs2.atoms()

    def clean(self):
        return BoxerWhq(self.discourse_id, self.sent_index, self.word_indices, self.ans_types, self.drs1.clean(), self.variable, self.drs2.clean())

    def renumber_sentences(self, f):
        return BoxerWhq(self.discourse_id, f(self.sent_index), self.word_indices, self.ans_types, self.drs1, self.variable, self.drs2)
        
    def __iter__(self):
        return iter(('['+','.join(self.ans_types)+']', self.drs1, self.variable, self.drs2))
        
    def _pred(self):
        return 'whq'
    


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
        if isinstance(ex, BoxerDrs):
            drs = DRS([Variable('x%d' % r) for r in ex.refs], map(self.interpret, ex.conds))
            if ex.label is not None:
                drs.label = Variable('x%d' % ex.label)
            if ex.consequent is not None:
                drs.consequent = self.interpret(ex.consequent)
            return drs
        elif isinstance(ex, BoxerNot):
            return DrtNegatedExpression(self.interpret(ex.drs))
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
            return DrtProposition(Variable('x%d' % ex.var), self.interpret(ex.drs))
        elif isinstance(ex, BoxerEq):
            return DrtEqualityExpression(DrtVariableExpression(Variable('x%d' % ex.var1)), 
                                         DrtVariableExpression(Variable('x%d' % ex.var2)))
        elif isinstance(ex, BoxerCard):
            pred = self._add_occur_indexing('card_%s_%s' % (ex.type, ex.value), ex)
            return self._make_atom(pred, 'x%d' % ex.var)
        elif isinstance(ex, BoxerOr):
            return DrtOrExpression(self.interpret(ex.drs1), self.interpret(ex.drs2))
        elif isinstance(ex, BoxerWhq):
            drs1 = self.interpret(ex.drs1)
            drs2 = self.interpret(ex.drs2)
            return DRS(drs1.refs + drs2.refs, drs1.conds + drs2.conds)
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
    opts.add_option("--question", "-q", help="input is a question", action="store_true", default=False, dest="question")
    opts.add_option("--occur", "-o", help="occurrence index", action="store_true", default=False, dest="occur_index")
    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error("incorrect number of arguments")

    interpreter = NltkDrtBoxerDrsInterpreter(occur_index=options.occur_index)
    drs = Boxer(interpreter).interpret_multisentence(args[0].split(r'\n'), question=options.question, verbose=options.verbose)
    if drs is None:
        print None
    else:
        drs = drs.simplify().eliminate_equality()
        if options.fol:
            print drs.fol().normalize()
        else:
            drs.normalize().pprint()
