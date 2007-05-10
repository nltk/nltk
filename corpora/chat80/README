	The various files which make up the program Chat-80
	===================================================
 
 _________________________________________________________________________
|	Copyright (C) 1982						  |
|									  |
|	David Warren,							  |
|		SRI International, 333 Ravenswood Ave., Menlo Park,	  |
|		California 94025, USA;					  |
|									  |
|	Fernando Pereira,						  |
|		Dept. of Architecture, University of Edinburgh,		  |
|		20 Chambers St., Edinburgh EH1 1JZ, Scotland		  |
|									  |
|	This program may be used, copied, altered or included in other	  |
|	programs only for academic purposes and provided that the	  |
|	authorship of the initial program is aknowledged.		  |
|	Use for commercial purposes without the previous written 	  |
|	agreement of the authors is forbidden.				  |
|_________________________________________________________________________|
 
File	Purpose
====	=======
 
load.pl
	Compile this file to get a compiled Chat-80, interpret it
	to get an interpreted Chat-80.
 
clone.xg
lex.xg
	The XG which defines the syntax accepted by Chat-80

clotab.pl
	Table of normal form modifier attachments

xgproc.pl
	This is a preprocessor to translate XGs into Prolog.
	If needed, it should be compiled separately. It defines
	the following evaluable predicates:-
 
		+ File :	reads in File treating any grammar rules
				in it as XG rules;
		list(File) :	writes out to File the Prolog clauses for
				the XG files read in so far.
 
xgrun.pl
	Defines the run time support predicates for XGs (see XGs paper).
 
newg.pl
	The Chat-80 grammar after preprocessing. It was obtained by typing
	the following:-
 
		prolog
		[xgproc].
		+ 'clone.xg'.
		+ 'lex.xg'.
		list('newg.pl').
 
newdict.pl
	The syntactic dictionary. It defines both application-independent
	and application-dependent (world database) words.
 
slots.pl
	Determines what modifies what.
 
scopes.pl
	Determines the scopes of determiners and other operators, and produces
	an unsimplified query.
 
templa.pl
	Defines the meaning of the application-dependent words.
 
qplan.pl
	Optimises a simplified query.
 
talkr.pl
	Executes queries.
 
ndtabl.pl

	Gives statistical information about the predicates in the world
	database (and also some application-independent ones such as
	'average'). This is used by the query optimiser.
 
	A clause in ndtabl.pl has the form

	nd(Predicate,PredSize,Dom1Size,...,DomkSize).

	Predicate is the name of a database predicate of arity k.

	PredSize, Dom1Size, ..., DomKSize measure the sizes of the
	the predicate (number of solutions) and the sizes of the domains
	for each argument (the number of distict values that argument
	may take in a call to the predicate). we use a logarithmic
	size measure

		s = 10 * log10(n)

	where n is the actual size (number of solutions or number pf
	distinct values) of a predicate or argument domain.

	Thus

		nd(flows,19,16,22)

	indicates that the binary predicate "flows" has around 80
	solutions, and it is going to be called with its first
	argument taken from a set with around 40 elements (number
	of rivers in the database) and its second argument taken
	from a set with around 158 elements (number of countries
	in the database).


readin.pl
	Reads in sentences.
 
ptree.pl
	Prints out parse trees.
 
aggreg.pl
	Executes set operators such as 'average'.
 
world0.pl
rivers.pl
cities.pl
countries.pl
contain.pl
borders.pl
	The world database.
 
newtop.pl
	Top level of Chat-80 and query simplifier.
demo
	Sample queries. To run in batch mode, type

		hi(demo)

	to the Prolog toplevel after loading Chat-80.
log
	Output expected from `hi(demo).'
