# Natural Language Toolkit: Test Code for REChunkParser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.parser.chunk import *
from nltk.tagger import TaggedTokenizer
from nltk.token import LineTokenizer

import unittest

class ChunkStringTestCase(unittest.TestCase):
    """
    Unit test cases for C{nltk.rechunkparser.ChunkString}
    """
    def setUp(self): pass

    def _tok(self, str):
        return TaggedTokenizer().tokenize(str)

    def _ctok(self, str):
        return TreeToken('TEXT', *ChunkedTaggedTokenizer().tokenize(str))

    def testToChunkStruct(self):
        "nltk.rechunkparser.ChunkString.to_chunkstruct tests"
        toks = [self._tok(s) for s in
                ["A/A B/B C/C D/D",
                 "",
                 "A/. B/$ C/@ D/# E/! F/% G/^ H/& I/* J/( K/)",
                 "./A $/B @/C #/D !/E %/F ^/G &/H */I (/J )/K",
                 "A/1 B/2 C/3 D/4 E/5 F/6 G/7 H/8 I/9 J/0",
                 "1/A 2/B 3/C 4/D 5/E 6/F 7/G 8/H 9/I 0/J",
                 "this/is a/_test_"]]
        for tok in toks:
            self.failUnlessEqual(TreeToken('TEXT', *tok),
                                 ChunkString(tok).to_chunkstruct())

    def testXform(self):
        "nltk.rechunkparser.ChunkString.xform tests"
        # We could use more tests.  What's a more principled approach
        # to this?
        toks = self._tok("A/1 B/2 C/3 D/4 E/5 F/6 G/7 H/8 I/9 J/0")
        cs = ChunkString(toks)
        cs.xform(r"<2>", r"{<2>}")
        cs.xform(r"(<3>)", r"{\1}")
        cs.xform(r"((<[5670]>)+)", r"{\1}")
        cs.xform(r"((<[67]>)+)", r"}\1{")
        ctoks = self._ctok("A/1 [B/2] [C/3] D/4 [E/5] F/6 G/7 H/8 I/9 [J/0]")
        self.failUnlessEqual(ctoks, cs.to_chunkstruct())

        toks = self._tok("A/1 B/2 C/3 D/4 E/5 F/1 G/2 H/4 I/3 J/3")
        cs = ChunkString(toks)
        cs.xform_chink(r"((<(3|4)>)+)", r"{\1}")
        cs.xform_chink(r"((<(4|5)>)+)", r"{\1}")
        cs.xform_chink(r"(<2><3>)", r"{\1}")
        cs.xform_chunk(r"(<3>)(<3>)", r"\1}{\2")
        ctoks = self._ctok("A/1 B/2 [C/3 D/4] [E/5] F/1 G/2 [H/4 I/3][J/3]")
        self.failUnlessEqual(ctoks, cs.to_chunkstruct())

    def testVerify1(self):
        "nltk.rechunkparser.ChunkString._verify tests: debug levels"

        # No debugging.
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 0)
        cs.xform(r"<2>", r"{<2>")
        
        # Full debug on to_chunkstruct.
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 1)
        cs.xform(r"<2>", r"{<2>")
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.to_chunkstruct())
        
        # Partial debug on xform.
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.xform(r"<2>", r"{<2>"))
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.to_chunkstruct())
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        cs.xform(r"<2>", r"<3>")
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.to_chunkstruct())
        
        # Full debug on xform.
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 3)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.xform(r"<2>", r"{<2>"))
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.to_chunkstruct())
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 3)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.xform(r"<2>", r"<3>"))
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.to_chunkstruct())

    def testVerify2(self):
        "nltk.rechunkparser.ChunkString._verify tests: bad xforms"

        # Test various types of bad xformation
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.xform(r"<2>", r"{<2>"))
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.xform(r"<2>", r"<2>}"))
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs: cs.xform(r"<2>", r"{{<2>}}"))
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs:
                              cs.xform(r"<2><3><4>", r"{<2>{<3>}<4>}"))
        cs = ChunkString(self._tok("A/1 B/2 C/3 D/4 E/5 F/6"), 2)
        self.failUnlessRaises(ValueError,
                              lambda cs=cs:
                              cs.xform(r"<2><3><4>", r"}<2>{<3>}<4>{"))

class Tag2ReTestCase(unittest.TestCase):
    """
    Unit test cases for C{nltk.rechunkparser.tag_pattern2re_pattern}
    """
    def setUp(self): pass

    def testSpace(self):
        "nltk.rechunkparser.tag_pattern2re_pattern: space stripping test"
        tag2re = tag_pattern2re_pattern
        self.failUnlessEqual(tag2re("a b c"), "abc")
        self.failUnlessEqual(tag2re(" a b c "), "abc")
        self.failUnlessEqual(tag2re(" a   b\n\t  c  \n"), "abc")

    def testAngleParen(self):
        "nltk.rechunkparser.tag_pattern2re_pattern: <> paren tests"
        tag2re = tag_pattern2re_pattern
        self.failUnlessEqual(tag2re("<><><>"), "(<()>)(<()>)(<()>)")
        self.failUnlessEqual(tag2re("<x>+<y>"), "(<(x)>)+(<(y)>)")

    def testDot(self):
        "nltk.rechunkparser.tag_pattern2re_pattern: . repl tests"
        tag2re = tag_pattern2re_pattern
        self.failUnlessEqual(tag2re(r"a.b"), r'a[^\{\}<>]b')
        self.failUnlessEqual(tag2re(r".."), r'[^\{\}<>][^\{\}<>]')
        self.failUnlessEqual(tag2re(r"\..\."), r'\.[^\{\}<>]\.')
        self.failUnlessEqual(tag2re(r"\\..\."), r'\\[^\{\}<>][^\{\}<>]\.')
        self.failUnlessEqual(tag2re(r"\\\..\."), r'\\\.[^\{\}<>]\.')
        self.failUnlessEqual(tag2re(r".\\.\."), r'[^\{\}<>]\\[^\{\}<>]\.')

class REChunkParserTestCase(unittest.TestCase):
    """
    Unit test cases for C{nltk.rechunkparser.REChunkParser} and
    associated rules.
    """
    def _eval(self, chunkparser): 
        text = """
        [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
        [ The/DT cats/NNS ] ./.
        [ dog/NN ] ./.
        [ John/NNP ] saw/VBD [the/DT cat/NN] [the/DT dog/NN] liked/VBD ./.
        """
        chunkscore = ChunkScore()
        
        ctt = ChunkedTaggedTokenizer()
        for line in LineTokenizer().xtokenize(text):
            sentence = TreeToken('TEXT', *ctt.tokenize(line.type(),
                                                       source=line.loc()))
            guess = chunkparser.parse(sentence.leaves())
            chunkscore.score(sentence, guess)
        return chunkscore

    def testChunkRule(self):
        "nltk.rechunkparser.ChunkRule tests"
        rule1 = ChunkRule('<NN>', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1]))
        self.failUnlessEqual(int(1000*score.f_measure()), 166)
        
        rule1 = ChunkRule('<NN|DT>', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1]))
        self.failUnlessEqual(int(1000*score.f_measure()), 117)

        rule1 = ChunkRule('<NN|DT>+', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1]))
        self.failUnlessEqual(int(1000*score.f_measure()), 307)

        rule1 = ChunkRule('<NN|DT|JJ>+', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1]))
        self.failUnlessEqual(int(1000*score.f_measure()), 500)

        rule1 = ChunkRule('<DT>?<JJ>*<NN>+', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1]))
        self.failUnlessEqual(int(1000*score.f_measure()), 833)

        rule1 = ChunkRule('<DT>?<JJ>*<NN.*>', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1]))
        self.failUnlessEqual(int(1000*score.f_measure()), 1000)

        # Make sure we don't allow overlaps..
        rule1 = ChunkRule('<DT>?<JJ>*<NN.*>', 'Chunk NPs')
        rule2 = ChunkRule('<NN><.*>', 'Chunk NPs')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 1000)

    def testChinkRule(self):
        "nltk.rechunkparser.ChinkRule tests"
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN|VB.*>', 'Chink')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 285)
        
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN|VB.*>+', 'Chink')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 285)
        
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN>|<VB.*>', 'Chink')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 285)
        
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN|VB.*|\.>', 'Chink')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 769)
        
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN|VB.*|\.>+', 'Chink')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 769)
        
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN|VB.*|\.>|(?=<DT>)', 'Chink')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 1000)

    def testUnChunkRule(self):
        "nltk.rechunkparser.UnChunkRule tests"
        rule1 = ChunkRule('<.*>', 'Chunk Every token')
        rule2 = UnChunkRule('<IN|VB.*>', 'Unchunk')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 166)

        rule1 = ChunkRule('<.*>', 'Chunk Every token')
        rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
        score = self._eval(REChunkParser([rule1, rule2]))
        self.failUnlessEqual(int(1000*score.f_measure()), 200)

    def testMergeRule(self):
        "nltk.rechunkparser.UnChunkRule tests"
        rule1 = ChunkRule('<.*>', 'Chunk Every token')
        rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
        rule3 = MergeRule('<DT>', '<NN.*>', 'Merge')
        score = self._eval(REChunkParser([rule1, rule2, rule3]))
        self.failUnlessEqual(int(1000*score.f_measure()), 749)

        rule1 = ChunkRule('<.*>', 'Chunk Every token')
        rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
        rule3 = MergeRule('<DT|JJ>', '<NN.*>', 'Merge')
        score = self._eval(REChunkParser([rule1, rule2, rule3]))
        self.failUnlessEqual(int(1000*score.f_measure()), 800)

        rule1 = ChunkRule('<.*>', 'Chunk Every token')
        rule2 = UnChunkRule('<IN|VB.*|\.>', 'Unchunk')
        rule3 = MergeRule('<DT|JJ>', '<NN.*>', 'Merge')
        rule4 = MergeRule('<DT>', '<JJ.*>', 'Merge')
        score = self._eval(REChunkParser([rule1, rule2, rule3, rule4]))
        self.failUnlessEqual(int(1000*score.f_measure()), 1000)

    def testSplitRule(self):
        "nltk.rechunkparser.split tests"
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = ChinkRule('<IN|VB.*|\.>+', 'Chink')
        rule3 = SplitRule('', '<DT>', 'Split')
        score = self._eval(REChunkParser([rule1, rule2, rule3]))
        self.failUnlessEqual(int(1000*score.f_measure()), 1000)

        "nltk.rechunkparser.split tests"
        rule1 = ChunkRule('<.*>*', 'Chunk Everything')
        rule2 = SplitRule('<NN>', '<VBD>', 'Split')
        rule3 = SplitRule('<IN>', '<DT>', 'Split')
        rule4 = SplitRule('', '<\.>', 'Split')
        score = self._eval(REChunkParser([rule1, rule2, rule3, rule4]))
        self.failUnlessEqual(int(1000*score.f_measure()), 444)

def testsuite():
    """
    Return a PyUnit testsuite for the token module.
    """
    
    tests = unittest.TestSuite((
        unittest.makeSuite(ChunkStringTestCase, 'test'),
        unittest.makeSuite(Tag2ReTestCase, 'test'),
        unittest.makeSuite(REChunkParserTestCase, 'test'),
        ))

    return tests

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
