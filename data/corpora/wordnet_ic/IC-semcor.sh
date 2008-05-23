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

## create information content for SemCor
## uses information from cntlist that comes with WordNet
## does not use CORPORA, stoplist, or compounds
## since this is actually counting concepts, there is no need to use
## --resnik counting.

semCorFreq.pl --outfile ic-semcor.dat

semCorFreq.pl --smooth ADD1 --outfile ic-semcor-add1.dat

