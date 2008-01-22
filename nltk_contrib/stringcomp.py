# Natural Language Toolkit
# String Comparison Module
# Author: Tiago Tresoldi <tresoldi@users.sf.net>

"""
String Comparison Module.

Author: Tiago Tresoldi <tresoldi@users.sf.net>
Based on previous work by Qi Xiao Yang, Sung Sam Yuan, Li Zhao, Lu Chun,
and Sung Peng.
"""

def stringcomp (fx, fy):
    """
    Return a number within C{0.0} and C{1.0} indicating the similarity between
    two strings. A perfect match is C{1.0}, not match at all is C{0.0}.

    This is an implementation of the string comparison algorithm (also known
    as "string similarity") published by Qi Xiao Yang, Sung Sam Yuan, Li Zhao,
    Lu Chun and Sun Peng in a paper called "Faster Algorithm of String
    Comparison" ( http://front.math.ucdavis.edu/0112.6022 ). Please note that,
    however, this implementation presents some relevant differences that
    will lead to different numerical results (read the comments for more
    details).
  
    @param fx: A C{string}.
    @param fy: A C{string}.
  
    @return: A float with the value of the comparision between C{fx} and C{fy}.
             C{1.0} indicates a perfect match, C{0.0} no match at all.
    @rtype: C{float}
    """

    # get the smaller of 'n' and 'm', and of 'fx' and 'fy'
    n, m = len(fx), len(fy)
    if m < n:
        (n, m) = (m, n)
        (fx, fy) = (fy, fx)

    # Sum of the Square of the Number of the same Characters
    ssnc = 0.

    # My implementation presents some relevant differences to the pseudo-code
    # presented in the paper by Yang et al., which in a number of cases will
    # lead to different numerical results (and, while no empirical tests have
    # been perfomed, I expect this to be slower than the original).
    # The differences are due to two specific characteristcs of the original
    # algorithm that I consider undesiderable for my purposes:
    #
    # 1. It does not takes into account the probable repetition of the same
    #    substring inside the strings to be compared (such as "you" in "where
    #    do you think that you are going?") because, as far as I was able to
    #    understand, it count only the first occurence of each substring
    #    found.
    # 2. It does not seem to consider the high probability of having more 
    #    than one pattern of the same length (for example, comparing between
    #    "abc1def" and "abc2def" seems to consider only one three-character
    #    pattern, "abc").
    #
    # Demonstrating the differences between the two algorithms (or, at least,
    # between my implementation of the original and the revised one):
    #
    # "abc1def" and "abc2def"
    #    Original: 0.534
    #    Current:  0.606
    for length in range(n, 0, -1):
        while True:
            length_prev_ssnc = ssnc
            for i in range(len(fx)-length+1):
                pattern = fx[i:i+length]
                pattern_prev_ssnc = ssnc
                fx_removed = False
                while True:
                    index = fy.find(pattern)
                    if index != -1:
                        ssnc += (2.*length)**2
                        if fx_removed == False:
                            fx = fx[:i] + fx[i+length:]
                            fx_removed = True
                        fy = fy[:index] + fy[index+length:]
                    else:
                        break
                if ssnc != pattern_prev_ssnc:
                    break
            if ssnc == length_prev_ssnc:
                break

    return (ssnc/((n+m)**2.))**0.5


def demo ():
    print "Comparison between 'python' and 'python': %.2f" % stringcomp("python", "python")
    print "Comparison between 'python' and 'Python': %.2f" % stringcomp("python", "Python")
    print "Comparison between 'NLTK' and 'NTLK': %.2f" % stringcomp("NLTK", "NTLK")
    print "Comparison between 'abc' and 'def': %.2f" % stringcomp("abc", "def")
  
    print "Word most similar to 'australia' in list ['canada', 'brazil', 'egypt', 'thailand', 'austria']:"
    max_score = 0.0 ; best_match = None
    for country in ["canada", "brazil", "egypt", "thailand", "austria"]:
        score = stringcomp("australia", country)
        if score > max_score:
            best_match = country
            max_score = score
        print "(comparison between 'australia' and '%s': %.2f)" % (country, score)
    print "Word most similar to 'australia' is '%s' (score: %.2f)" % (best_match, max_score)
  
if __name__ == "__main__":
    demo()
