#!/bin/csh

## This script will build information content files for
## WordNet::Similarity. You need to have the corpora
## mentioned installed in a directory called $CORPORA.
## You also need to have a file of WordNet compounds,
## created by utils/compounds.pl. A stoplist is optional
## but a good idea. The following scripts presume that
## WNHOME has been set (if not, use --wnpath option).

## please note that as of version 2.01 of WordNet-Similarity
## the compfile option has been removed from the *Freq.pl
## programs, and compound identification is done automatically

set stop = stoplist.txt
set CORPORA = /space/tpederse/IC-Corpora

## Create information content for Brown Corpus.

## brownFreq.pl --outfile ic-brown.dat \
## --stopfile $stop $CORPORA/ICAME/TEXTS/BROWN1/*.TXT

brownFreq.pl --outfile ic-brown-add1.dat \
 --stopfile $stop  --smooth ADD1 $CORPORA/ICAME/TEXTS/BROWN1/*.TXT

brownFreq.pl --outfile ic-brown-resnik-add1.dat \
 --stopfile $stop  --smooth ADD1 --resnik $CORPORA/ICAME/TEXTS/BROWN1/*.TXT

brownFreq.pl --outfile ic-brown-resnik.dat \
 --stopfile $stop  --resnik $CORPORA/ICAME/TEXTS/BROWN1/*.TXT

## create information content for SemCor
## uses information from cntlist that comes with WordNet
## does not use CORPORA, stoplist, or compounds
## since this is actually counting concepts, there is no need to use
## --resnik counting.

## semCorFreq.pl --outfile ic-semcor.dat

## semCorFreq.pl --smooth ADD1 --outfile ic-semcor-add1.dat

## create information content for Semcor, ignoring sense tags (treat
## Semcor as raw text) version doesn't matter as we are ignoring tags

semCorRawFreq.pl --outfile ic-semcorraw.dat \
 --stopfile $stop --infile $CORPORA/semcor2.1/brown1/tagfiles

semCorRawFreq.pl --outfile ic-semcorraw-add1.dat \
 --stopfile $stop  --smooth ADD1 --infile $CORPORA/semcor2.1/brown1/tagfiles

semCorRawFreq.pl --outfile ic-semcorraw-resnik-add1.dat \
 --stopfile $stop  --smooth ADD1 --resnik --infile $CORPORA/semcor2.1/brown1/tagfiles

semCorRawFreq.pl --outfile ic-semcorraw-resnik.dat \
 --stopfile $stop  --resnik --infile $CORPORA/semcor2.1/brown1/tagfiles
 
## Create information content from raw/plain text corpus (Shakespeare)

##rawtextFreq.pl  --outfile ic-shaks.dat \
 --stopfile $stop  --infile $CORPORA/shaks12.txt

## rawtextFreq.pl  --outfile ic-shaks-add1.dat \
 --stopfile $stop  --smooth ADD1  --infile $CORPORA/shaks12.txt

rawtextFreq.pl  --outfile ic-shaks-resnink-add1.dat \
 --stopfile $stop  --smooth ADD1 --resnik  --infile $CORPORA/shaks12.txt

rawtextFreq.pl  --outfile ic-shaks-resnik.dat \
 --stopfile $stop --resnik  --infile $CORPORA/shaks12.txt

## Create information content from treebank

treebankFreq.pl --outfile ic-treebank.dat \
 --stopfile $stop $CORPORA/TreeBank-2/raw/wsj

treebankFreq.pl  --outfile ic-treebank-add1.dat \
 --stopfile $stop --smooth ADD1 $CORPORA/TreeBank-2/raw/wsj

treebankFreq.pl  --outfile ic-treebank-resnik-add1.dat \
 --stopfile $stop --smooth ADD1 --resnik $CORPORA/TreeBank-2/raw/wsj

treebankFreq.pl  --outfile ic-treebank-resnik.dat \
 --stopfile $stop  --resnik $CORPORA/TreeBank-2/raw/wsj

## Create information content from British National Corpus

## BNCFreq.pl --outfile ic-bnc.dat \
##  --stopfile $stop $CORPORA/BNC-World/Texts

BNCFreq.pl  --outfile ic-bnc-add1.dat \
 --stopfile $stop --smooth ADD1 $CORPORA/BNC-World/Texts

BNCFreq.pl  --outfile ic-bnc-resnik-add1.dat \
 --stopfile $stop --smooth ADD1 --resnik $CORPORA/BNC-World/Texts

BNCFreq.pl  --outfile ic-bnc-resnik.dat \
 --stopfile $stop  --resnik $CORPORA/BNC-World/Texts
