''' UTILITY Functions for ROUGE score for Machine Translation'''


def jacknifing(score_list, averaging=True):
        ''' This is a averaging function for calculating ROUGE score
    when multiple references are present. In this technique, from a 
    given list of m values, m unique sets of m-1 elements is created.
    Then the maximum is calculated from each of this m sets. The 
    averaging is then performed on the m maximum values thus obtained.
    This technique has been referred to as the Jacknifing technique 
    in the original paper that introduces ROUGE-SCORE.


    param score_list : list of scores over which averaging occurs
    type (score_list) : list

    param averaging : Jacknifing occurs if averaging is True
    type (averaging) : boolean

    >>> scores=[10, 20, 30, 40]
    
    >>> jacknifing(scores, averaging=False)
    [10, 20, 30, 40]

    >>> jacknifing(scores, averaging=True)
    37.5

    >>> scores =[10]
    
    >>> jacknifing(scores)
    10.0


    '''
        if(len(score_list) == 1):
            return sum(score_list)/len(score_list)
        elif((len(score_list) > 1) and (averaging is False)):
            return score_list
        else:
            '''
            average : store the maximum scores
            from the m different sets of m-1 scores.
            such that m is the len(score_list)
            '''
            average = []
            for i in score_list:
                # dummy : list a particular combo of m-1 scores
                dummy = [j for j in score_list if i != j]
                average.append(max(dummy))
            return sum(average)/len(average)


def f(k,  alpha=2, inverse=True):
    '''Weighting function of the Longest-Common-Subsequence

    param k : parameter entered by user
    type (k) : float

    param alpha : parameter entered by user
    type(alpha) : float
    
    param inverse : parameter entered by user which decides whether 
                    to return the function or it's inverse
    type(inverse) : boolean                

    '''
    
    return k**(1/alpha) if inverse else k**alpha

        


def rouge_lcs(X, Y, weighted=False, return_string=False):
    '''This function returns the longest common subsequence
    of two strings using the dynamic programming algorithm.

    param X : first string or sequence in tokenized form
    type (X) : list

    param Y : second string or sequence in tokenized form
    type (Y) : list

    param weighted : Weighted LCS is done if weighted is True
    type (weighted) : Boolean

    >>> string1 = 'police killed the gunman'
    >>> string2 = 'police kill the gunman'
    
    >>> rouge_lcs(string1.split(' '), string2.split(' '), return_string=True)
    'police the gunman '

    >>> rouge_lcs(string1.split(' '), string2.split(' '))
    3

    >>> round(rouge_lcs(string1.split(' '), string2.split(' '), weighted=True), 3)
    2.414

    '''
    m, n = len(X), len(Y)

    # Initialize the c-table
    c_table = [[0]*(n+1) for i in range(m+1)]
    # Initialize the w-table
    w_table = [[0]*(n+1) for i in range(m+1)]

    for i in range(m+1):
        for j in range(n+1):
            if i == 0 or j == 0:
                continue
            # The length of consecutive matches at
            # position i-1 and j-1
            elif X[i-1] == Y[j-1]:
                # Increment would be +1 for normal LCS
                k = w_table[i-1][j-1]
                increment = f(k+1) - f(k) if weighted else 1
                # Add the increment
                c_table[i][j] = c_table[i-1][j-1] + increment
                w_table[i][j] = k + 1
            else:
                if c_table[i-1][j] > c_table[i][j-1]:
                    c_table[i][j] = c_table[i-1][j]
                    w_table[i][j] = 0  # no match at i,j
                else:
                    c_table[i][j] = c_table[i][j-1]
                    w_table[i][j] = 0  # no match at i,j
    lcs_length = c_table[m][n]
    if not return_string:
        return lcs_length
    lcs = [""] * (lcs_length+1)
    lcs[lcs_length] = ""
    i = m
    j = n
    while i > 0 and j > 0:
        if X[i-1] == Y[j-1]:
            lcs[lcs_length-1] = X[i-1]
            i -= 1
            j -= 1
            lcs_length -= 1
        elif c_table[i-1][j] > c_table[i][j-1]:
            i -= 1
        else:
            j -= 1
    return (" ".join(lcs))  # the lcs string
