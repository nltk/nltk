# CIS-530 Course Project : Stemmer Module for NLTK
# Name: Chen-Fu Chiang, Jinyoung Choi
# Email: cchiang@seas.upenn.edu, choi3@babel.ling.upenn.edu

"""
An implmentation of the Porter stemming algorithm in python.
The main idea followed the stemmer ANSI C code closely. Some
structures of the code followed Edward Loper's token & tagger classes
in his natural language tool kit(NLTK).

In the Stemmer class, instead of processing the complete context or
article, I simply assume users have been learning NLTK and this
stemming process will only suffix-strip the input token.You can call
the function stem_token from the Stemmer class from this module. The
return unit would be the suffix-stripped token and all the letters of
the word would be in lower case.

If you want to stem the whole text file, you can use fucntion
stem_file("filename") from this module, but the format of the file
would change.  It would print out a list of stemmed tokens.

Reference:
  1. Porter, 1980, An algorithm for suffix stripping, Program, Vol. 14,
     no. 3, pp 130-137,

  2. NLTK by Edward Loper, http://nltk.sourceforge.net/

  3. http://www.python.org

Release 0.0: April 28, 2003
"""
import sys
import re 
from nltk.token import *
TRUE = 1
FALSE = 0

##############################
# alphabetical letter checking
##############################
def isalphabet(char):
    """
    A simple function that checks if a given char is an alphabetical letter.  This function
    would be used later in Stemmer().stem_token.

    """
    # getting the ascii number of the char
    asc_num = ord(char)

    # in A-Z or in a-z
    if((asc_num>65 and asc_num<91) or (asc_num>96 and asc_num<123)):
        return TRUE

    # not in A-Z nor in a-z
    else:
        return FALSE


########################
# The Stemmer Class 
########################
class Stemmer:
    def __init__(self):

        """
        Constructor of the Stemmer class; 
        b: buffer to hold the toknized item's type to be stemmed.
        The letters are in b[k0], b[k0+1] ... ending at b[k]. In fact k0 = 0
        in this demo program. k is readjusted downwards as the stemming progresses.
        Zero termination is not in fact used in the algorithm.
        
        """
        self.b = ""  # the buffer
        self.k = 0   # index to the last element of the buffer, intially set to 0
        self.k0 = 0  # index to the first element of the buffer
        self.j = 0   # a general offset into the string


    def consonant(self, c):
        
        """
        verify the letter to see if it is consonant, if yes, return TRUE else return FALSE
        Since word is buffered in Stemmer.b, then we need to check the letters of current
        word buffered in Stemmer.b

        A consonant in a word is a letter other than A, E, I, O or U, and other than Y preceded
        by a consonant.
        
        """
        # if a, e, i, o, u then not consonant
        if (self.b[c] == 'a' or self.b[c] == 'e' or self.b[c] == 'i' or self.b[c] == 'o'
        or self.b[c] == 'u'):
            return 0

        # if it is "y", check its previous letter, if prev is a consonant, then return 0,
        # otherwise, return 1. 

        if (self.b[c] == 'y'):

            # no preceeding letter, then this "y" is a consonant 
            if (c == self.k0):
                return 1

            else:
                return (not self.consonant(c - 1))

        return 1
    

    def m(self):
        """
        m() counts the number of occurrence of vc in a word, i.e. the sequences
        between k0 and kj. "v" stands for vowel and c stands for consonant. A word
        can be seen as in the following form:  <c>(vc)^m<v> where c in the bracket means
        consonants can "consecutively" occur for 0 or more times. Once it encounters a vowel,
        then it should start to count the occurence of vc. 
  
        Example:
        <c><v>       gives 0  such as: TR-,  -EE,  TR-EE,(no "c" follows EE)  Y,  BY.
        <c>vc<v>     gives 1  such as: TR-OUBL-E,  -OA-TS,  TR-EES-,  -IV-Y.
        <c>vcvc<v>   gives 2  such as: TR-OUBL-ES-,  PR-IV-AT-E,  -OAT-EN-,  -ORR-ER-Y.
           
        """
        occur = 0
        index = self.k0

        # checking the beginning of the word to see if it is started by bunches of consonants
        # stop the while loop when it encounter a vowel, i.e. the end of <c> but the start for
        # couting the occurence of vc

        while 1: # the only way to get outta this loop is either outta range or a "v" is found
            # out of range already 
            if (index > self.j):
                return occur

            # started by a vowel, then should exit the while loop and start to count occurence
            # of vc ; end of <c>

            if (not self.consonant(index)):
                break

            # current self.b[index] is still a consonant, then proceed to next one. 
            if (self.consonant(index)):
                index = index + 1

        # termination of first while loop and go check next letter, i.e. <c> part is done        
        index = index + 1


        # start counting occurence of vc 
        while 1:# the only way to get outta this look is either outta range 

            # checking till find a "c" or out of range
            while 1:
                if (index > self.j):
                    return occur

                if (self.consonant(index)):
                    break

                if (not self.consonant(index)):
                    index = index + 1
                    
            index = index + 1
            occur = occur + 1

            while 1:
                if (index > self.j):
                    return occur

                # find another "v", means previous "vc" ends
                if (not self.consonant(index)):
                    break

                if (self.consonant(index)):
                    index = index + 1

            index=index+1
            #occur=occur + 1



    def vowelinstem(self):
        """
        vowelinstem() is TRUE iff at least one vowel in the buffer (self.b)
        This fuction calls consonant to check from self.b[k0], if finds any vowel
        in the buffer, return 1 immediately. If no vowel, keep checking till end of buff. 
        
        """
         
        for t in range(self.k0, self.j+1):
            if not self.consonant(t):
                return 1
        return 0


    def doublec(self, j):
        """
        doublec(j) is TRUE iff j,(j-1) contain a double consonant.
        
        """

        if j < (self.k0 + 1):
            return 0

        if (self.b[j] != self.b[j-1]):
            return 0

        return self.consonant(j)



    def cvc(self, i):
        """
        cvc(i) is TRUE iff i-2,i-1,i has the form consonant - vowel - consonant
        and also if the second c is not w,x or y. this is used when trying to
        restore an e at the end of a short e.g.
        cav(e), lov(e), hop(e), crim(e), but  snow, box, tray.
           
        """

        if ((i < (self.k0 + 2)) or (not self.consonant(i)) or (self.consonant(i-1)) or (not self.consonant(i-2))):
            return 0

        ch = self.b[i]

        if ch == 'w' or ch == 'x' or ch == 'y':
            return 0

        return 1



    def ends(self, s):
        """
        ends(s) is TRUE iff k0,...k ends with the string s. This can be used for later suffix stripping.
                
        """
        length = len(s)

        if s[length - 1] != self.b[self.k]: # tiny speed-up
            return 0

        if length > (self.k - self.k0 + 1):
            return 0
        
        if self.b[self.k-length+1:self.k+1] != s:
            return 0

        self.j = self.k - length

        return 1



    def setto(self, s):
        """
        setto(s) sets (j+1),...k to the characters in the string s, re-adjusting k.
        
        """

        length = len(s)
        self.b = self.b[:self.j+1] + s + self.b[self.j+length+1:]
        self.k = self.j + length



    def r(self, s):

        """
        r(s) is used further down.
        
        """

        if (self.m() > 0):
            self.setto(s)


    ###################
    # Stemming Rule 1
    ###################
    def step1ab(self):
        """
        step1ab() gets rid of plurals and -ed or -ing. e.g.
        caresses  ->  caress       ponies    ->  poni         ties      ->  ti
        caress    ->  caress       cats      ->  cat

        feed      ->  feed         agreed    ->  agree        disabled  ->  disable

        matting   ->  mat          mating    ->  mate         meeting   ->  meet
        milling   ->  mill         messing   ->  mess

        meetings  ->  meet

        """
        # the plural case 
        if self.b[self.k] == 's':

            if self.ends("sses"):
                self.k = self.k - 2

            elif self.ends("ies"):
                self.setto("i")


            elif self.b[self.k - 1] != 's':
                self.k = self.k - 1

        # the eed case         
        if self.ends("eed"):
            if self.m() > 0:
                self.k = self.k - 1

        # ed case or (ing case with vowel in in the word
        elif ((self.ends("ed")) or ((self.ends("ing"))and(self.vowelinstem()))):

            self.k = self.j

            # restore the eliminated "e" becauae it is necesarry in the following cases
            if self.ends("at"):   self.setto("ate")

            elif self.ends("bl"): self.setto("ble")

            elif self.ends("iz"): self.setto("ize")

            elif self.doublec(self.k):
                self.k = self.k - 1
                ch = self.b[self.k]

                if ch == 'l' or ch == 's' or ch == 'z':
                    self.k = self.k + 1

            elif (self.m() == 1 and self.cvc(self.k)):
                self.setto("e")



    def step1c(self):
        """
        step1c() turns terminal "y" to "i" when there is another vowel in the stem.
        Hence: happy->happi  sky->sky
        
        """

        if (self.ends("y") and self.vowelinstem()):
            self.b = self.b[:self.k] + 'i' + self.b[self.k+1:]


    ##################
    # Stemming Rule 2
    ##################
    def step2(self):
        """
        step2() maps double suffices to single ones.
        so -ization ( = -ize plus -ation) maps to -ize etc. note that the
        string before the suffix must give m() > 0.
        
        """
        # cases for ending is "ational" or "tional" 
        if self.b[self.k - 1] == 'a':

            # ational->ate
            if self.ends("ational"):
                self.r("ate")

            # tional->tion
            elif self.ends("tional"):
                self.r("tion")

        # cases for ending is "enci" or "ence" 
        elif self.b[self.k - 1] == 'c':

            # enci->ence
            if self.ends("enci"):
                self.r("ence")

            #anci->ance             
            elif self.ends("anci"):
                self.r("ance")

        # cases for ending is "izer" 
        elif self.b[self.k - 1] == 'e':

            # izer->ize
            if self.ends("izer"):
                self.r("ize")

        # cases for ending is "bli" or "alli" or "entli" or "eli" or "ousli"
        elif self.b[self.k - 1] == 'l':

            # bli->ble
            if self.ends("bli"):
                self.r("ble") # -- DEPARTURE; annotated in the .c file --

            # To match the published algorithm, replace this phrase with  if self.ends("abli"):   self.r("able")

            # alli->al
            elif self.ends("alli"):
                self.r("al")

            # entli->ent
            elif self.ends("entli"):
                self.r("ent")

            # eli->e
            elif self.ends("eli"):
                self.r("e")

            # ousli->ous
            elif self.ends("ousli"):
                self.r("ous")

        # cases for ending is "ization" or "ation" or "ator" 
        elif self.b[self.k - 1] == 'o':

            # ization->ize
            if self.ends("ization"):
                self.r("ize")

            # ation->ate
            elif self.ends("ation"):
                self.r("ate")

            # ator->ate
            elif self.ends("ator"):
                self.r("ate")

        # cases for ending is "alism" or  "iveness" or "fulness"
        elif self.b[self.k - 1] == 's':

            # alism->al 
            if self.ends("alism"):
                self.r("al")

            # iveness->ive
            elif self.ends("iveness"):
                self.r("ive")

            # fulness->ful
            elif self.ends("fulness"):
                self.r("ful")

            # ousness->ous
            elif self.ends("ousness"):
                self.r("ous")

        # cases for ending is "aliti" or "iviti" or "biliti"        
        elif self.b[self.k - 1] == 't':

            # aliti->al
            if self.ends("aliti"):
                self.r("al")

            # iviti->ive
            elif self.ends("iviti"):
                self.r("ive")

            # biliti->ble
            elif self.ends("biliti"):
                self.r("ble")

        # cases for ending is "logi"
        elif self.b[self.k - 1] == 'g': # --DEPARTURE, as annotated in the .c file--

            # logi->log
            if self.ends("logi"):
                self.r("log")

       
    ##################
    # Stemming Rule 3
    ##################
    def step3(self):
        """
        step3() dels with -ic-, -full, -ness etc. similar strategy to step2.
        
        """
        
        if self.b[self.k] == 'e':
            """
            cases with ending with "e", then according to the subcases to to the stripping.
            icate->ic; ative-> ; alize->al
            
            """
            if self.ends("icate"):
                self.r("ic")

            elif self.ends("ative"):
                self.r("")

            elif self.ends("alize"):
                self.r("al")

        elif self.b[self.k] == 'i':
            """
            cases with ending with "i", then according to the subcases to to the stripping.
            iciti->ic;
            
            """
            if self.ends("iciti"):
                self.r("ic")

        elif self.b[self.k] == 'l':
            """
            cases with ending with "l", then according to the subcases to to the stripping.
            ical->ic; ful-> ;

            """
            if self.ends("ical"):
                self.r("ic")

            elif self.ends("ful"):
                self.r("")

        elif self.b[self.k] == 's':
            """
            cases with ending with "s", then according to the subcases to to the stripping.
            ness-> ;

            """
            if self.ends("ness"):
                self.r("")


    ##################
    # Stemming Rule 4
    ##################
    def step4(self):
        """
        step4() takes off -ant, -ence etc., in context <c>vcvc<v>.
        
        """
        # case: 2nd to the last letter is 'a' 
        if self.b[self.k - 1] == 'a':

            if self.ends("al"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'c'
        elif self.b[self.k - 1] == 'c':

            if self.ends("ance"):
                pass

            elif self.ends("ence"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'e'      
        elif self.b[self.k - 1] == 'e':

            if self.ends("er"):
                pass

            else: return

        # case: 2nd to the last letter is 'i'
        elif self.b[self.k - 1] == 'i':

            if self.ends("ic"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'l'
        elif self.b[self.k - 1] == 'l':

            if self.ends("able"):
                pass

            elif self.ends("ible"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'n'
        elif self.b[self.k - 1] == 'n':

            if self.ends("ant"):
                pass

            elif self.ends("ement"):
                pass

            elif self.ends("ment"):
                pass

            elif self.ends("ent"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'o'
        elif self.b[self.k - 1] == 'o':

            if (self.ends("ion") and (self.b[self.j] == 's' or self.b[self.j] == 't')):
                pass

            elif self.ends("ou"):
                pass

            else:
                return

        # case: 2nd to the last letter is 's'
        elif self.b[self.k - 1] == 's':

            if self.ends("ism"):
                pass

            else:
                return

        # case: 2nd to the last letter is 't'
        elif self.b[self.k - 1] == 't':

            if self.ends("ate"):
                pass

            elif self.ends("iti"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'u'
        elif self.b[self.k - 1] == 'u':

            if self.ends("ous"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'v'
        elif self.b[self.k - 1] == 'v':

            if self.ends("ive"):
                pass

            else:
                return

        # case: 2nd to the last letter is 'z'
        elif self.b[self.k - 1] == 'z':

            if self.ends("ize"):
                pass

            else:
                return

        else:
            return

        if self.m() > 1:
            self.k = self.j


    ##################
    # Stemming Rule 5
    #################
    def step5(self):
        """
        step5() removes a final -e if m() > 1, and changes -ll to -l if m() > 1.
        
        """

        self.j = self.k

        if self.b[self.k] == 'e':
            a = self.m()

            if (a > 1 or (a == 1 and not self.cvc(self.k-1))):
                self.k=self.k - 1

        if (self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1):
            self.k=self.k - 1
            

    ################
    # Token Stemmer
    ################
    def stem_token(self, INPUT_TOKEN):
        """
        In stem_token(INPUT_TOKEN), INPUT_TOKEN is a tokenized word.  The major attribute
        of a token is _type and _location.  _type is the the word string and  _location is
        the location of that word in the input text. Detailed explanation about the structure
        please refer to token.py in Edward' Loper's NLTK.

        While calling this function, we also provoke self.b, self.k and self.k0.
        self.k0 is normally 0 as the beginning of a word. Such as if a="Janet", then
        a[k0]="J".  We process the INPUT_TOKEN._type (the word string) by applying
        the stemmer algorithm. 
        """

        # copy the parameters and values into statics

        # pass the word string and location into a new token
        stemmed=Token('dummy')
        stemmed=INPUT_TOKEN
        
        # get the word string from the input token & set all letters into lower case
        # because it would be easier to stem without upper case and lower case letters mixing
        # together.  Otherwise, we would need to add situations like "Able", "aBle" , "A",etc.
        # when we do the stemming.  It would only complicate the structure and doesn't seem to be
        # necessary
        
        self.b=INPUT_TOKEN._type.lower()
        self.k=len(INPUT_TOKEN._type)-1
        self.k0=0
        
        # Another variable for checking
        tail=" "

        if self.k <= self.k0 + 1:
            return stemmed  # --DEPARTURE, as annotated in the .c file--

        
        # In token._type, if a word is followed by a symbol that is not a alphabet letter,
        # such as "connection," the puncutation mark should be left out first while processing
        # "connection".  Otherwise "connection," instead of being suffix stripped into "connect,",
        # would remain as "connection,".
        
        if ((not(isalphabet(self.b[self.k])))==1):
            tail=self.b[self.k]
            self.b=self.b[:self.k]
            self.k=self.k-1

        
        # With this line, strings of length 1 or 2 don't go through the
        # stemming process, although no mention is made of this in the
        # published algorithm. Remove the line to match the published
        # algorithm.

        self.step1ab()
        self.step1c()
        self.step2()
        self.step3()
        self.step4()
        self.step5()

        # get the stemmed word string        
        stemmed._type= self.b[self.k0:self.k+1]
        

        # attach the symobol other than letters back to the stemmed word
        if ((not (tail==" "))==1):
            stemmed._type=stemmed._type+tail

        
        return stemmed


####################
# File Stemmer 
####################
def stem_file(input_file):
    """
    This function takes in a file. Tt tokenizes the words in the file and then calls Stemmer.stem_token
    to stem the tokens.

    """    
    print "Please wait... reading the the input file"
    print "The output of stemmed tokens from input file is as the following: \n"

    # reading in the input file          
    text=open(input_file).read()
    all_tokens=WhitespaceTokenizer().tokenize(text)
    stemmed_toks=[]

    # stemming process
    stemmer = Stemmer()
    for each_token in all_tokens:
        stemmed_toks.append(stemmer.stem_token(each_token))

    for i in range(len(stemmed_toks)):
        print stemmed_toks[i].type(),
        if i % 10 == 0: print
    print
  
####################################
# demo to to demonstrate the example
####################################
def demo(targetfile):
    """
    A demo that would stem on the file specified in ..
    You can just change the specified file's location as you wish. As long as
    you give the right path for the demo to find that file to work on.

    """    
    stem_file(targetfile)


################
# The Testing 
################
if __name__ == '__main__':
    from nltk.corpus import gutenberg
    demo(gutenberg.path('blake-poems.txt'))


    
