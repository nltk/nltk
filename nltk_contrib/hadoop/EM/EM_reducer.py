from nltk.tag.hmm import _log_add, _NINF
from numpy import *


def reduce(key, values):
	name, i, j, value, lpk, N, M = values.strip().split()
	N = int (N)
	M = int (M)
	i = int(i)
	value = float(values)
	A_numer = B_numer = A_denom = B_denom = None

	# add these sums to the global A and B values
	if name = "A":
		j = int(j)
		if not A_numer:
			A_numer = ones((N, N), float64) * _NINF
		A_numer[i, j] = _log_add(A_numer[i, j],
				value - lpk)
	elif name = "B":
		j = int(j)
		if not B_numer:
			B_numer = ones((N, M), float64) * _NINF
		B_numer[i, k] = _log_add(B_numer[i, k],
				value - lpk)
	elif name = "A_denom":
		if not A_denom:
			A_denom = ones(N, float64) * _NINF
		A_denom[i] = _log_add(A_denom[i], value - lpk)
	elif name = "B_denom":
		if not B_denom:
			B_denom = ones(N, float64) * _NINF
		B_denom[i] = _log_add(B_denom[i], value - lpk)

	# use the calculated values to update the transition and output
	# probability values

	for i in range(N):
		si = self._states[i]
		for j in range(N):
			sj = self._states[j]
			model._transitions[si].update(sj, A_numer[i,j] -
					A_denom[i])
		for k in range(M):
			ok = self._symbols[k]
			model._outputs[si].update(ok, B_numer[i,k] - B_denom[i])
		# Rabiner says the priors don't need to be updated. I don't
		# believe him. FIXME

	# test for convergence
	if iteration > 0 and abs(logprob - last_logprob) < epsilon:
		converged = True
