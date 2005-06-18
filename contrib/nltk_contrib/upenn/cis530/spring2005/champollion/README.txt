A Letter-Based Application of Transformation-Based Error-Driven Learning
*************************************************************************
README file for tblplus package
Author: Lucas Champollion (lucas@web.de), University of Pennsylvania
*************************************************************************

For a "Getting Started" guide, see at the end of the file.

*************************************************************************
- What is the point of this project?
*************************************************************************
Suppose you have two languages: one that is spoken by many people and has a lot of
computational resources available for it, and one that isn't spoken at all and
doesn't have any resources (corpora, taggers, parsers...) available for it, but is similar to the first
language. Perhaps the second language is a regional dialect of the first, or an extinct
precursor, or the two languages are identical but they are used in two
countries which have adopted a different spelling. 
Assuming that the two languages are related in an essentially regular way, a
transformation-based approach should be able to convert the one into the other
- or at least to make them look similar enough that the computational resources
can be applied to both languages without too much loss of accuracy.
This project grew out of the necessity to produce a morphological analysis for
Middle French, with the ultimate goal of contributing to the production of a
Middle French Treebank. Since morphological analyzers are readily available for
Modern French, I used transformation-based learning to convert the spelling of
Middle French texts to make them look as similar to Modern French as possible
with respect to morphology.
In principle, it should also work well for such tasks as converting German
texts written before about 1998, when a spelling reform took place, to a modern
appearance or vice versa, or similar tasks. 

*************************************************************************
- How is transformation-based learning applied to this problem?
*************************************************************************
The algorithm is applied as follows: First, assume that we have some
training data, consisting of a sample input to the system (such as "John
loves Mary") and a goldstandard (suppose it is "Jon likes Marry"). The goal is
to learn rules which, if applied to the input, will change it into the
goldstandard.
First, the two texts are globally aligned letter by letter using the diff tool.


J J 
o o 
h 
n n 
_ _ 
l l 
o i 
v k 
e e 
s s 
_ _ 
M M 
a a
  r 
r r 
y y 
. . 
_ _

This can be seen as a recording of changes that need to be made to the left-hand string in
order to change it into the right-hand string: substitution, insertions, and deletions.
Next, all changes are made to look like substitutions: insertions are made into
substitutions of the previous character by two or more characters, and
deletions are represented as substitutions by a special deletion sign that does
not occur elsewhere in the texts (here, '@'):

J J
o o 
h @ 
n n 
_ _ 
l l 
o i 
v k 
e e 
s s 
_ _ 
M M 
a ar 
r r 
y y 
. . 
_ _

Now the problem doesn't look too different any more from a more classical
application of transformation-based learning, POS tagging:

I	    P
saw	    V
the	    Det
man	    N
with	    PP
the	    Det
telescope   N
.	    PUNCT

In both cases, we have the input on the left side and a series of strings on
the right side that has to be assigned to the input. Generally speaking, this
is (one possible view of) a classification problem; in the case of POS tagging,
the classes are the tags, in our case, the classes are the characters used in
the text, plus the deletion character and a few character combinations to
simulate insertion.
The rest of the algorithm is similar to other instances of transformation-based
learning: we write some rule templates that define the feature space (in this
case, the original letter and its neighbors up to k characters to the left and
right); we provide the most likely class for each character (since we assume
that the two languages are very closely related, this is always the character
itself); we create a small parallel corpus and divide it into a training and a
testing part; we evaluate the algorithm using the edit distance between
its output and the gold standard (and as a baseline, the edit distance between
the input and the gold standard, which corresponds to doing nothing). Results
are described below.

*************************************************************************
What is the rationale for applying transformation-based learning to this problem?
*************************************************************************
As I've described above, any classifier could in fact be trained to achieve this
task. Transformation-based learning has been chosen for the following reasons:

- it has been applied to a vast range of classification tasks with promising results
- if the changes from one language to the other are mainly regular, they will
  be picked up more easily by the transformation-based classifier than by a
  stochastic classifier, while the residue of irregular changes can be picked
  up by a spellchecker (an implementation is provided, see below) or by more
  sophisticated methods such as stochastic classifiers
- it performs well even on small amounts of training data
- it outputs human-readable rules
- a fast implementation was available (fnTBL 1.1, available at http://nlp.cs.jhu.edu/~rflorian/fntbl/) 
- its principle was easy to understand :)

*************************************************************************
What are the components of the implementation?
*************************************************************************
The system has been built as a collection of python and shell scripts, on top of fnTBL
(see above) and a collection of unix tools, essentially diff. At present, it is
heavily system-dependent, meaning that several directories are hard-coded into
the scripts; these need to be edited should the system ever be moved to another
location. The rationale for this is that I wanted to realize a fast prototype
which is not likely to be actually moved to another location. Also, at this
point I don't know enough about Python or shell scripting to provide an
installation procedure in the configure/make/install style. 
I've organized the directory structure in the following way: 

-tblplus--+--Backup
          |
          +--Evaluation--+--Testing
          |              |
          |              +--Training
          |
          +--exec
          |
          +--Tbl-parameters



- The files in the Backup directory shouldn't be considered when you evaluate
  this project.
- The files in the Evaluation project are the following:

     COMMYN.txt	   transcription of an authentic manuscript by Philippe de
		   Commynes, a Middle French author (Copyright U of Ottawa)
    
     ancient.txt   an excerpt of the above file which corresponds to the size
		   of the gold standard (about 6000 characters)

     modern.txt    the gold standard for testing and training: a hand-written
		   word-by-word transcription of the file ancient.txt into
		   Modern French spelling

- Additionally, the last two files have been split in half and copied into the
  subdirectories Testing and Training, respectively. A simple non-interactive
  spellchecker (see below for a description) has been applied to the ancient
  versions of the text and the results have also been stored in the Testing and
  Training directory. This way, the system can be combined with one of the 
  spellcheckers in order to improve performance. Also, sample rules and sample 
  outputs have been stored inthe Training and Testing directories respectively. 


- The files in the exec directory are all executable python scripts or shell
  scripts. All of them return a short help message when called with no parameters.

     align	Takes two text files and aligns them letter by letter using
		diff, then edits the aligned file to conform to fnTBL's input
		format. (This shouldn't be called by the user.)

     apply      Applies the transformation rules learned by a previous
		application of fnTBL (e.g. via the 'learn' script) to a text file.
		usage: apply <rulefile> <textfile>
     
     evaluate   Simple evaluation tool based on global alignment. The two input
		files are compared both word-based and letter-based using diff. A result
		of 100% indicates that the files are identical.
		usage: evaluate <testdata> <goldstandard>

     inspect	Simple script that presents the rules output by fnTBL as called
		by this project in a more human-readable format. Note that this script is
		highly specific to the way fnTBL is used in this project and will not work
		on fnTBL-written rules in general.
		usage: inspect <rulefile>

     learn	Trains the fnTBL system letter-based, writes rules into
		rule_output (the threshold parameter is for fnTBL and indicates the
		minimal score a rule needs in order to be kept. Set it to zero if you do
		not know what to do)
		usage: learn <original> <goldstandard> <rule_output> <int:threshold>

     makeruletemplates
		This little script can be used to quickly generate the file
		"rules.templ" which tells fnTBL the templates after which rules
		are generated and tried out. The parameter 'windowsize' should
		be something like 1 to 20 or so (depending on your system) and
		indicates the maximal distance between two letters such that
		they will 'see' each other as features. Larger numbers slow
		down system performance and may result in overfitting; smaller
		numbers may result in failing to capture long-distance
		dependencies. It's the usual tradeoff, but fnTBL is VERY fast
		even with large window sizes, so try it out :)
		usage: makeruletemplates.py <int:windowsize> 
		(usually the output should be directed to
		Tbl-parameters/rules.templ)

     maketestfile
		This script brings a text file into suitable format for fnTBL,
		so that it can be used either as a test file or as a file on
		which fnTBL-generated rules are applied. It shouldn't be called
		directly by the user (use apply instead, followed by evaluate
		if you want to do testing)

     speller	Non-interactive spellchecker for French based on ispell /
		aspell. Replaces input by most likely word suggested by ispell resp. first
		suggestion by aspell. Attention: don't use this script for files that
		contain double quotes (")! This causes an error that will NOT be
		reported. At present I don't know how to fix this problem.

     For more information on the scripts, look at them directly, they've been
     extensively commented.:)
     For a "Getting Started" guide, see below.

- The files in the Tbl-parameters directory are needed by fnTBL and determine
  its behavior. 

     file.templ	This determines the format of fnTBL's input files and should
		not be changed.

     parameter-file.txt
		This determines the behavior of fnTBL. It should not be
		changed except if you know what you're doing. (You might want
		to add a few parameters to tweak the engine, for
		example. Please refer to the fnTBL manual at
		http://nlp.cs.jhu.edu/~rflorian/fntbl/tbl-toolkit/tbl-toolkit.html

     rules.templ
		This file contains templates for the transformational rules the
		system is supposed to pick up. You can edit this file by hand
		following the instructions in the fnTBL manual, or you can use
		the "makeruletemplates" script to write it for you (see above).

     training-file.txt.voc
                This file has been generated by fnTBL at some point and I don't
                know anymore if it's vital to the system, so I'll leave it in
                place although I don't know if it really has to sit there. :)

*************************************************************************
- Getting Started or: How can I use this package? 
  (also contains some basic evaluation)
*************************************************************************
At this point I can only provide a quick introduction, but you should get the
idea. First, make sure that the exec directory is in your path so that you can
type the following commands and so that the scripts work properly. You should
also make sure that fnTBL 1.1 is installed into the directory ~/fnTBL-1.1 (just
below your home directory) and that the directory ~/fnTBL-1.1/bin is in your
path. All these directories are in my path, 

source /home/champoll/.bashrc

and everything should be fine.

For the speller script, aspell and ispell need to be installed with French
dictionaries. This is the case on alpha. The speller script isn't required to
run the other scripts, though.

Applying this tool (just as applying transformation-based learning in general)
is done in three steps: training, testing and evaluating.

Training consists in learning a set of rules from an original file and a gold
standard. You can move to the tblplus/Evaluation/Training directory and you'll find
such files. Type:

[champoll@alpha Training]$ learn ancient_part1 modern_part1 /path/to/rules.txt 0

This should generate an output similar to the following:

Studying the data
Reading 11 sentences !indexes
Done reading data.
Generating the index
Overall running time: 2 seconds, 552 milliseconds (2552 milliseconds)

In addition, you'll have created a new file called rules.txt, which you can
open with a text editor. You'll find that it's not very easily readable,
though, so you can use the following tool to look at it:

[champoll@alpha Training]$ inspect /path/to/rules.txt | less

This tool is a filter and it leaves the rule file unchanged.

(If you see a line like this: 

GOOD:1 BAD:0 SCORE:1 RULE:  replace "ZZZZZZZZZZZZZZZZZZZZZZZZZZZ A" by
"ZZZZZZZZZZZZZZZZZZZZZZZZZZ A";

this is a bug and I haven't been able to determine if I'm causing it or
fnTBL. It shouldn't affect system performance, though.)

If you've got a problem generating the rules, you can use the file
sample_rules.txt in the training directory.

You're now ready to apply the rules to new text. If you want to apply them to
the file "hello_world.txt" in your home directory, just type:

[champoll@alpha Training]$ apply /path/to/rules.txt ~/hello_world.txt

If you want to test the performance of the system, you'll need to apply the
rules to some testing data and have a gold standard available for
comparison. Both of this is provided in the tblplus/Evaluation/Testing
directory.

[champoll@alpha Testing]$ apply /path/to/rules.txt ancient_part2.txt > /path/to/system_output.txt

If this doesn't work, you can use the file system_output_part2.txt in the
following.

Now that you've applied the rules, you'll want to evaluate the system by
comparing the result with the gold standard. One way to measure accuracy is the
following simple formula:

	  accuracy = 1 - (edit distance / text length)

where the edit distance is defined as usual (also called Levenshtein distance)
and is measured either over the words or over the characters of the two
texts. The "evaluate" script does both for you and returns the following
results:

[champoll@alpha Testing]$ evaluate system_output_part2 modern_part2 
Evaluation based on character:
Substitutions: 102 out of 3141 (3.2 %)
Insertions: 20 out of 3141 (0.6 %)
Deletions: 106 out of 3141 (3.4 %)
Accuracy: 92.7 %

Evaluation based on word:
Substitutions: 125 out of 618 (20.2 %)
Insertions: 0 out of 618 (0.0 %)
Deletions: 11 out of 618 (1.8 %)
Accuracy: 78.0 %

A baseline can be obtained by comparing the ancient (origninal) text directly
with the modern (goldstandard) text:

[champoll@alpha Testing]$ evaluate ancient_part2 modern_part2 
Evaluation based on character:
Substitutions: 122 out of 3183 (3.8 %)
Insertions: 12 out of 3183 (0.4 %)
Deletions: 148 out of 3183 (4.6 %)
Accuracy: 91.1 %

Evaluation based on word:
Substitutions: 144 out of 618 (23.3 %)
Insertions: 0 out of 618 (0.0 %)
Deletions: 11 out of 618 (1.8 %)
Accuracy: 74.9 %

These results aren't spectacular, but this is to be expected with only 3000
bytes of training data...

The performance can be boosted by applying a spell checker to the system
output and always picking the first suggestion, if applicable. This is done by
the following script:

[champoll@alpha Testing]$ speller my_system_output aspell > my_corrected_system_output

Sample outputs can be found in the Testing directory. Comparing one of them
with the gold standard yields the following results:

[champoll@alpha Testing]$ evaluate system_output_part2_spellchecked_ispell modern_part2 
Evaluation based on character:
Substitutions: 85 out of 3144 (2.7 %)
Insertions: 44 out of 3144 (1.4 %)
Deletions: 109 out of 3144 (3.5 %)
Accuracy: 92.4 %

Evaluation based on word:
Substitutions: 101 out of 618 (16.3 %)
Insertions: 0 out of 618 (0.0 %)
Deletions: 11 out of 618 (1.8 %)
Accuracy: 81.9 %

This is substantially better both than applying the transformation-based system
alone and applying only the spellchecker, respectively. The latter option
yields the following results:

[champoll@alpha Testing]$ evaluate ancient_part2_spellchecked_with_ispell
modern_part2 
Evaluation based on character:
Substitutions: 108 out of 3166 (3.4 %)
Insertions: 82 out of 3166 (2.6 %)
Deletions: 131 out of 3166 (4.1 %)
Accuracy: 89.9 %

Evaluation based on word:
Substitutions: 114 out of 618 (18.4 %)
Insertions: 1 out of 618 (0.2 %)
Deletions: 11 out of 618 (1.8 %)
Accuracy: 79.6 %


Note that the actual numbers obtained will depend of which rule template file
has been used at training time, as well as on other parameters.



For any additional questions, comments, bugs etc. send an email to me at
lucas@web.de 

Enjoy!

Lucas Champollion 
University of Pennsylvania
June 6th, 2005
