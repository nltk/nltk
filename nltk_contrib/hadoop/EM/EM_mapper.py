from nltk import FreqDist, ConditionalFreqDist, ConditionalProbDist, \
	DictionaryProbDist, DictionaryConditionalProbDist, LidstoneProbDist, \
	MutableProbDist, MLEProbDist, UniformProbDist, HiddenMarkovModelTagger

from nltk.tag.hmm import _log_add

from numpy import *

# _NINF = float('-inf')  # won't work on Windows
_NINF = float('-1e300')

_TEXT = 0  # index of text in a tuple
_TAG = 1   # index of tag in a tuple

def pd(values, samples):
	d = {}
	for value, item in zip(values, samples):
		d[item] = value
	return DictionaryProbDist(d)

def cpd(array, conditions, samples):
	d = {}
	for values, condition in zip(array, conditions):
		d[condition] = pd(values, samples)
	return DictionaryConditionalProbDist(d)

def read_params():
	params = open("hmm_parameter", 'r')
	d = {}
	A = {}
	B = {}
	for line in params:
		words = line.strip().split()
		# ignore blank lines and comment lines
		if len(words) == 0 or line.strip()[0] == "#":
			continue
		if words[0] == "Pi":
			d[words[1]] = float(words[2])
		elif words[0] == "A":
			A[(words[1], words[2])] = float(words[3]) 
		elif words[0] == "B":
			B[(words[1], words[2])] = float(words[3]) 
		else:
			raise ValueError("Invalid parameter file format")
	params.close()

	# get initial state probability p (state)
	Pi = DictionaryProbDist(d)

	A_keys = A.keys()
	B_keys = B.keys()
	states = set()
	symbols = set()
	for e in A_keys:
		states.add(e[0])
		states.add(e[1])
	for e in B_keys:
		states.add(e[0])
		symbols.add(e[1])

	states = list(states)
	symbols = list(symbols)

	# get transition probability p(state | state)
	prob_matrix = []
	for condition in states:
		li = []
		for state in states:
			li.append(A.get((condition, state), 0))
		prob_matrix.append(li)
	A = cpd(array(prob_matrix, float64), states, states)

	# get emit probability p(symbol | state)
	prob_matrix = []
	for state in states:
		li = []
		for symbol in symbols:
			li.append(B.get((state, symbol), 0))
		prob_matrix.append(li)
	B = cpd(array(prob_matrix, float64), states, symbols)

	#print Pi.samples()
	#print states
	#print symbols

	#print "transitions:"
	#for e in  A.conditions():
	    #for e1 in A[e].samples():
		    #print e, e1, A[e].prob(e1)

	#print "emit:"
	#for e in  B.conditions():
	    #for e1 in B[e].samples():
		    #print e, e1, B[e].prob(e1)
	
	return symbols, states, A, B, Pi

def map(key, values):

	symbols = ['h', 't']
	states = ['0', '1']

	symbols, state, A, B, pi = read_params()
	N = len(states)
	M = len(symbols)
	symbol_dict = dict((symbols[i], i) for i in range(M))

	model = HiddenMarkovModelTagger(symbols=symbols, states=states, transitions=A, outputs=B, priors=pi)

	logprob = 0
	for sequence in values:
		sequence = list(sequence)
		if not sequence:
			continue

		# compute forward and backward probabilities
		alpha = model._forward_probability(sequence)
		beta = model._backward_probability(sequence)

		# find the log probability of the sequence
		T = len(sequence)
		lpk = _log_add(*alpha[T-1, :])
		logprob += lpk

		# now update A and B (transition and output probabilities)
		# using the alpha and beta values. Please refer to Rabiner's
		# paper for details, it's too hard to explain in comments
		local_A_numer = ones((N, N), float64) * _NINF
		local_B_numer = ones((N, M), float64) * _NINF
		local_A_denom = ones(N, float64) * _NINF
		local_B_denom = ones(N, float64) * _NINF

		#print local_A_numer
		#print local_B_numer

		# for each position, accumulate sums for A and B
		for t in range(T):
			x = sequence[t][_TEXT] #not found? FIXME
			if t < T - 1:
				xnext = sequence[t+1][_TEXT] #not found? FIXME
			xi = symbol_dict[x]
			for i in range(N):
				si = states[i]
				if t < T - 1:
					for j in range(N):
						sj = states[j]
						local_A_numer[i, j] =  \
							_log_add(local_A_numer[i, j],
									alpha[t, i] + 
									model._transitions[si].logprob(sj) + 
									model._outputs[sj].logprob(xnext) +
									beta[t+1, j])
						local_A_denom[i] = _log_add(local_A_denom[i],
									alpha[t, i] + beta[t, i])
				else:
					local_B_denom[i] = _log_add(local_A_denom[i],
							alpha[t, i] + beta[t, i])

					local_B_numer[i, xi] = _log_add(local_B_numer[i, xi],
							alpha[t, i] + beta[t, i])

		for i in range(N):
			for j in range(N):
				print 'A', i, j, local_A_numer[i, j], lpk

		for i in range(N):
			for j in range(N):
				print 'B', i, j, local_B_numer[i, j], lpk

		for i in range(N):
			print 'A_denom', i, 'null', local_A_denom[i], lpk

		for i in range(N):
			print 'B_denom', i, 'null', local_B_denom[i], lpk

if __name__ == "__main__":
	training = ["hhhhhthhthhhthhhhhhhhhhhhhhhhhhhththhhhhhhhhhhhhhhhhhthhhhthhhhhhhhhhhhhhhhhthhhhhhhhhhhhhhhthhhhhhhthththt"]
	map(None, training)
