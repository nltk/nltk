% Author: syboo, aboxhall, jcwyang
% Date: October 2004
% Description:
%	This is just a small prototype to show how the first order
%	predicate logic produced by the semeanticProcessor.py can be used
%	in an answering system.


% This predicate is for further extension. 
% If question(yes), answer the question. 
% If question(no), add the predicates to the knowledgebase
question(_X).

% The information (predicates) currently exists in the the knowledgebase
cost(pizza, five_dollars).

% The predicate that will bind the variable with the atom
equal(X, X).

% To query the answering system for the cost of a pizza
run(X) :-
	question(yes), cost(Y, X), equal(X, Answer), equal(Y, pizza).

