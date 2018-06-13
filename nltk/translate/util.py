import numpy as np


def jacknifing(score_list, averaging=True):
        ''' This is a averaging function for calculating ROUGE score
    when multiple references are present. This technique has been
    referred to as the Jacknifing technique in the original paper.
    score_list = list of scores over which averaging occurs
    '''
        if(len(score_list) == 1):
            return np.mean(score_list)
        elif((len(score_list) > 1) and (averaging is False)):
            return score_list
        else:
            average = []
            for i in score_list:
                dummy = [j for j in score_list if i != j]
                average.append(max(dummy))
            return(np.mean(average))


def lcs(X, Y, m, n):
        '''This function returns the length of the
        longest common subsequence(LCS) between two
        given strings and also the LCS.
        X = list containing all the tokens of the first string
        Y = list containing all the tokens of the second string
        m = no. of tokens of the first string
        n = no.of tokens of the second string

        Note: Tokenization of the strings can be done at both
        character-level and word-level.
        '''
        L = [[0 for x in range(n+1)] for x in range(m+1)]
        for i in range(m+1):
            for j in range(n+1):
                if i == 0 or j == 0:
                    L[i][j] = 0
                elif X[i-1] == Y[j-1]:
                    L[i][j] = L[i-1][j-1] + 1
                else:
                    L[i][j] = max(L[i-1][j], L[i][j-1])
        index = L[m][n]
        lcs = [""] * (index+1)
        lcs[index] = ""
        i = m
        j = n
        while i > 0 and j > 0:
            if X[i-1] == Y[j-1]:
                lcs[index-1] = X[i-1]
                i -= 1
                j -= 1
                index -= 1
            elif L[i-1][j] > L[i][j-1]:
                i -= 1
            else:
                j -= 1
        s = " ".join(lcs)
        return(len(s.split()), s)


def demo():
    string_1 = 'police killed the gunman'
    string_2 = 'police kill the gunman'
    lcs_var = lcs(string_1.split(), string_2.split(),
                  len(string_1.split()), len(string_2.split()))
    print(" Length of the LCS btw string_1 and string_2 :", lcs_var[0])
    print(" LCS of string_1 and string_2 :", lcs_var[1])
    scores = [10, 20, 30, 40]
    print('Averaged value:', jacknifing(scores))
    print('Unaveraged value:', jacknifing(scores, averaging=False))


if __name__ == '__main__':
    demo()
