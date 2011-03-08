# -*- coding: utf-8 -*-

# Natural Language Toolkit: RSLP Stemmer
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Tiago Tresoldi <tresoldi@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# This code is based on the algorithm presented in the paper "A Stemming
# Algorithm for the Portuguese Language" by Viviane Moreira Orengo and
# Christian Huyck, which unfortunately I had no access to. The code is a
# Python version, with some minor modifications of mine, to the description
# presented at http://www.webcitation.org/5NnvdIzOb and to the C source code
# available at http://www.inf.ufrgs.br/~arcoelho/rslp/integrando_rslp.html.
# Please note that this stemmer is intended for demostration and educational
# purposes only. Feel free to write me for any comments, including the
# development of a different and/or better stemmer for Portuguese. I also
# suggest using NLTK's mailing list for Portuguese for any discussion.

# Este código é baseado no algoritmo apresentado no artigo "A Stemming
# Algorithm for the Portuguese Language" de Viviane Moreira Orengo e
# Christian Huyck, o qual infelizmente não tive a oportunidade de ler. O
# código é uma conversão para Python, com algumas pequenas modificações
# minhas, daquele apresentado em http://www.webcitation.org/5NnvdIzOb e do
# código para linguagem C disponível em
# http://www.inf.ufrgs.br/~arcoelho/rslp/integrando_rslp.html. Por favor,
# lembre-se de que este stemmer foi desenvolvido com finalidades unicamente
# de demonstração e didáticas. Sinta-se livre para me escrever para qualquer
# comentário, inclusive sobre o desenvolvimento de um stemmer diferente
# e/ou melhor para o português. Também sugiro utilizar-se a lista de discussão
# do NLTK para o português para qualquer debate.

import nltk.data

from api import *

class RSLPStemmer(StemmerI):
    """
    A stemmer for Portuguese.
    """
    def __init__ (self):
        self._model = []
    
        self._model.append( self.read_rule("step0.pt") )
        self._model.append( self.read_rule("step1.pt") )
        self._model.append( self.read_rule("step2.pt") )
        self._model.append( self.read_rule("step3.pt") )
        self._model.append( self.read_rule("step4.pt") )
        self._model.append( self.read_rule("step5.pt") )
        self._model.append( self.read_rule("step6.pt") )

    def read_rule (self, filename):
        rules = nltk.data.load('nltk:stemmers/rslp/' + filename, format='raw').decode("utf8")
        lines = rules.split("\n")
  
        lines = [line for line in lines if line != u""]     # remove blank lines
        lines = [line for line in lines if line[0] != "#"]  # remove comments
  
        # NOTE: a simple but ugly hack to make this parser happy with double '\t's
        lines = [line.replace("\t\t", "\t") for line in lines]

        # parse rules
        rules = []
        for line in lines:
            rule = []
            tokens = line.split("\t")
    
            # text to be searched for at the end of the string
            rule.append( tokens[0][1:-1] ) # remove quotes
    
            # minimum stem size to perform the replacement
            rule.append( int(tokens[1]) )
    
            # text to be replaced into
            rule.append( tokens[2][1:-1] ) # remove quotes
    
            # exceptions to this rule
            rule.append( [token[1:-1] for token in tokens[3].split(",")] )
    
            # append to the results
            rules.append(rule)
    
        return rules

    def stem(self, word):
        word = word.lower()
    
        # the word ends in 's'? apply rule for plural reduction
        if word[-1] == "s":
            word = self.apply_rule(word, 0)
      
        # the word ends in 'a'? apply rule for feminine reduction
        if word[-1] == "a":
            word = self.apply_rule(word, 1)
      
        # augmentative reduction
        word = self.apply_rule(word, 3)
    
        # adverb reduction
        word = self.apply_rule(word, 2)
    
        # noun reduction
        prev_word = word
        word = self.apply_rule(word, 4)
        if word == prev_word:
            # verb reduction
            prev_word = word
            word = self.apply_rule(word, 5)
            if word == prev_word:
                # vowel removal
                word = self.apply_rule(word, 6)
    
        return word
    
    def apply_rule(self, word, rule_index):
        rules = self._model[rule_index]
        for rule in rules:
            suffix_length = len(rule[0])
            if word[-suffix_length:] == rule[0]:       # if suffix matches
                if len(word) >= suffix_length + rule[1]: # if we have minimum size
                    if word not in rule[3]:                # if not an exception
                        word = word[:-suffix_length] + rule[2]
                        break
      
        return word

def demo():
    from nltk import stem
    stemmer = stem.RSLPStemmer() 

    # white-space tokenizer friendly text; text taken from the first paragraph
    # of Erico Verissimo's "Música ao Longe"
    text = u"""
Clarissa risca com giz no quadro-negro a paisagem que os alunos devem copiar .
Uma casinha de porta e janela , em cima duma coxilha . Um coqueiro do lado
( onde o nosso amor nasceu - pensa ela no momento mesmo em que risca o troco
longo e fino ) . Depois , uma estradinha que corre , ondulando como uma cobra
, e se perde longe no horizonte . Nuvens de fiz do céu preto , um sol redondo
e gordo , chispando raios , árvores , uma lagoa com marrecos nadando ...
"""

    tokens = text.split()
  
    for token in tokens:
        word = token
        stem = stemmer.stem(token)
    
        print "%16s - %16s" % (word, stem)
  
if __name__ == "__main__":
    demo()
