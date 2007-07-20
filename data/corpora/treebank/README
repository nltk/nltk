PENN TREEBANK SAMPLE
http://www.cis.upenn.edu/~treebank/home.html

This is a ~5% fragment of Penn Treebank, (C) LDC 1995.  It is made
available under fair use for the purposes of illustrating NLTK tools
for tokenizing, tagging, chunking and parsing.  This data is for
non-commercial use only.

Contents: raw, tagged, parsed and combined data from Wall Street
Journal for 1650 sentences (99 treebank files wsj_0001 .. wsj_0099).
For details about each of the four types, please see the other README
files included in the treebank sample directory.  Examples of the four
types are shown below:

----raw----
Pierre Vinken, 61 years old, will join the board as a nonexecutive
director Nov. 29.
----tagged----
[ Pierre/NNP Vinken/NNP ]
,/, 
[ 61/CD years/NNS ]
old/JJ ,/, will/MD join/VB 
[ the/DT board/NN ]
as/IN 
[ a/DT nonexecutive/JJ director/NN Nov./NNP 29/CD ]
./. 
----parsed----
( (S (NP-SBJ (NP Pierre Vinken)
             ,
             (ADJP (NP 61 years)
		   old)
             ,)
     (VP will
         (VP join
             (NP the board)
             (PP-CLR as
		     (NP a nonexecutive director))
	     (NP-TMP Nov. 29)))
     .))
----combined----
( (S 
    (NP-SBJ 
      (NP (NNP Pierre) (NNP Vinken) )
      (, ,) 
      (ADJP 
        (NP (CD 61) (NNS years) )
        (JJ old) )
      (, ,) )
    (VP (MD will) 
      (VP (VB join) 
        (NP (DT the) (NN board) )
        (PP-CLR (IN as) 
          (NP (DT a) (JJ nonexecutive) (NN director) ))
        (NP-TMP (NNP Nov.) (CD 29) )))
    (. .) ))
--------


-----------------------------------------------------------------------
README FROM ORIGINAL CDROM

This is the Penn Treebank Project: Release 2 CDROM, featuring a million
words of 1989 Wall Street Journal material annotated in Treebank II style.
This bracketing style, which is designed to allow the extraction of simple
predicate-argument structure, is described in doc/arpa94 and the new
bracketing style manual (in doc/manual/).  In addition, there is a small
sample of ATIS-3 material, also annotated in Treebank II style.  Finally,
there is a considerably cleaner version of the material released on the
previous Treebank CDROM (Preliminary Release, Version 0.5, December 1992),
annotated in Treebank I style.

There should also be a file of updates and further information available
via anonymous ftp from ftp.cis.upenn.edu, in pub/treebank/doc/update.cd2.
This file will also contain pointers to a gradually expanding body of
relatively technical suggestions on how to extract certain information from
the corpus.

We're also planning to create a mailing list for users to discuss the Penn
Treebank, focusing on this release.  We hope that the discussions will
include interesting research that people are doing with Treebank data, as
well as bugs in the corpus and suggested bug patches.  The mailing list is
tentatively named treebank-users@linc.cis.upenn.edu; send email to
treebank-users-request@linc.cis.upenn.edu to subscribe.

For questions that are not of general interest, please write to
treebank@unagi.cis.upenn.edu.


		      INVENTORY and DESCRIPTIONS

The directory structure of this release is similar to the previous release.

doc/                    --Documentation.
			This directory contains information about who
			the annotators of the Penn Treebank are and
			what they did as well as LaTeX files of the
			Penn Treebank's Guide to Parsing and Guide to
			Tagging. 

parsed/			--Parsed Corpora.
			These are skeletal parses, without part-of-speech
			tagging information.  To reflect the change in
			style from our last release, these files now have
			the extension of .prd.

  atis/  		--Air Travel Information System transcripts.
  April 1994		Approximately 5000 words of ATIS3 material.
			The material has a limited number of sentence
			types.  It was created by Don Hindle's Fidditch and
			corrected once by a human annotator (Grace Kim).

  wsj/			--1989 Wall Street Journal articles.
  November 1993		Most of this material was processed from our      
   -October 1994	previous release using tgrep "T" programs.
			However, the 21 files in the 08 directory and the
			file wsj_0010 were initially created using the
			FIDDITCH parser (partially as an experiment, and
			partly because the previous release of these files
			had significant technical problems).
			                                                  
			All of the material was hand-corrected at least
			once, and about half of it was revised and updated
			by a different annotator.  The revised files are
			likely to be more accurate, and there is some
			individual variation in accuracy.  The file
			doc/wsj.wha lists who did the correction and
			revision for each directory.


tagged/			--Tagged Corpora.

  atis/			--Air Travel Information System transcripts.
  April 1994		The part-of-speech tags were inserted by Ken
			Church's PARTS program and corrected once by a
			human annotator (Robert MacIntyre).
  
  wsj			--'88-'89 Wall Street Journal articles.
  Winter		These files have not been reannotated since the
   -Spring 1990		previous release.  However, a number of technical
			bugs have been fixed and a few tags have been
			corrected.  See tagged/README.pos for details.


combined/		--Combined Corpora.
			These corpora have been automatically created by
			inserting the part of speech tags from a tagged
			text file (.pos file) into a parsed text file (.prd
			file).  The tags are inserted as nodes immediately
			dominating the terminals.  See README.mrg for more
			details.


tgrepabl/		--Tgrepable Corpora.
			These are encoded corpora designed for use with
			version 2.0 of tgrep, included with this release.
			The (skeletally) parsed Treebank II WSJ material is
			in wsj_skel.crp, while the combined version, with
			part-of-speech tagging information included, is in
			wsj_mrg.crp.  See the README in tools/tgrep/ for
			more information.


raw/			--Rawtexts.
			These are source files for Treebank II annotated
			material.  Some buggy text has been changed or
			eliminated; tb1_075/ has the original versions.


tools/			--Source Code for Various Programs.
			This directory contains the "tgrep" tree-searching
			(and tree-changing) package, in a compressed tar
			archive.  It also contains the program used to make
			the combined files.  All programs are designed to
			be run on UNIX machines.


tb1_075/		--"Version 0.75" of Treebank I.
			This directory contains a substantially cleaner
			version of the Preliminary Release (Version 0.5).
			Combining errors and unbalanced parentheses should
			now be eliminated in the Brown and WSJ corpora, the
			tgrepable corpora are free of fatal errors, many
			technical errors in the POS-tagged files have been
			fixed, and some errors and omissions in the
			documentation have been corrected.  However, the
			material has NOT been reannotated since the
			previous release, with the exception of the WSJ
			parsed material, most of which has undergone
			substantial revision.


The new work in this release was funded by the Linguistic Data Consortium.
Previous versions of this data were primarily funded by DARPA and AFOSR
jointly under grant No. AFOSR-90-006, with additional support by DARPA
grant No. N0014-85-K0018 and by ARO grant No. DAAL 03-89-C0031 PRI.  Seed
money was provided by the General Electric Corporation under grant
No. J01746000.  We gratefully acknowledge this support.

Richard Pito deserves special thanks for providing the tgrep tool, which
proved invaluable both for preprocessing the parsed material and for
checking the final results.

We are also grateful to AT&T Bell Labs for permission to use Kenneth
Church's PARTS part-of-speech labeller and Donald Hindle's Fidditch parser.

Finally, we are very grateful to the exceptionally competent technical
support staff of the Computer and Information Science Department at the
University of Pennsylvania, including Mark-Jason Dominus, Mark Foster, and
Ira Winston.

-----------------------------------------------------------------------

				 COPYRIGHT

The following copyright applies to all datafiles on this CDROM:

              Copyright (C) 1995 University of Pennsylvania

      This release was annotated in Treebank II style by the Penn
      Treebank Project. We would appreciate if research using this
      corpus or based on it would acknowledge that fact.

The following articles are appropriate references for this release:

    Marcus, M., Kim, G., Marcinkiewicz, M.A., MacIntyre, R., Bies, A.,
    Ferguson, M., Katz, K. and Schasberger, B.  "The Penn Treebank:
    Annotating Predicate Argument Structure", in {\it Proceedings of the
    Human Language Technology Workshop}, Morgan Kaufmann Publishers Inc.,
    San Francisco, CA, March 1994.
    (This article gives an overview of the Treebank II bracketing scheme.
     A LaTeX version is included in this release, as doc/arpa94.tex.)

    Marcus, M., Santorini, B., Marcinkiewicz, M.A., 1993.
    Building a large annotated corpus of English: the Penn Treebank.
    {\it Computational Linguistics}, Vol 19.
    (This article describes the Penn Treebank in general terms.  A LaTeX
     version is included in this release, as doc/cl93.tex.)
