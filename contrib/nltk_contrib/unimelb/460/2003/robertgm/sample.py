from nltk.tokenizer import *
from features import *
from re import *
from nltk.corpus import *

#we have a list of closed-form words which are not counted in our tf.idf calculations
stop_list = []
sentence_tokenizer = RETokenizer(r'\!|\?|(\.(?!(\d|,)))\s*', negative=1)
word_tokenizer = WSTokenizer()

class TrainingSample:
    def __init__(self, abstract=[], text=[], filename=""):

        #if there is no filename, we have to process the text ourself
        if filename == "":

            #convert the list of paragraphs in to a list of tokenized paragraphs...
            p = 0
            self.text = []
            for p in range(0, len(text)):
                #...where a paragraph is a token, containing a list of tokenized sentences and a location
                self.text.append(Token(sentence_tokenizer.tokenize(text[p]), Location(p)))

            self.extract = []
            sentences = [s.type() for s in sentence_tokenizer.tokenize(abstract)]
            #for each sentence in the abstract            
            for sentence in sentences:
                print 'matching sentence:', sentence
                #record which sentence in the text (if any) matches most closely
                loc = closest_match(sentence, text)
                if loc != None:
                    (p, s) = loc
                    self.extract.append(Token(sentence, Location(s, unit="s", source=Location(p, unit="p"))))

            print 'created extract', self.extract
            print

        #they have given us a filename
        else:
            
            fp = open(filename)

            self.text = []            
            #loop through each paragraph
            text_length = int(fp.readline())
            for p in range(0, text_length):
                #read the paragraph, and drop the trailing \n
                paragraph = fp.readline()
                paragraph = paragraph[0:len(paragraph)-1]
                #add this paragraph in
                self.text.append(Token(sentence_tokenizer.tokenize(paragraph), Location(p)))

            self.extract = []
            #loop through each sentence in the abstract
            abstract_length = int(fp.readline())
            for i in range(0, abstract_length):
                sentence = fp.readline()
                sentence_no = int(fp.readline())
                paragraph_no = int(fp.readline())
                #add in the sentence, and the location of the corresponding sentence in the document
                self.extract.append(Token(sentence[0:len(sentence)-1], Location(sentence_no, unit="s",
                                                                                source=Location(paragraph_no, unit="p"))))
            fp.close()            

    #calculate the given features on this sample
    def train(self, features):
        results = dict()
        for feature in features:
            #calculate the feature on both the document and summary
            results[feature] = (feature.evaluate_document(self.text), feature.evaluate_summary(self.extract, self.text))
        return results

    def write(self, filename):
        fp = open(filename, 'w')
        fp.write(len(self.text).__repr__()+'\n')
        for paragraph in self.text:
            for sentence in paragraph.type():                
                fp.write(sentence.type()+'. ')
            fp.write('\n')
                
        fp.write(len(self.extract).__repr__()+'\n')
        for sentence in self.extract:
            fp.write(sentence.type()+'\n')            
            fp.write(sentence.loc().start().__repr__()+'\n')
            fp.write(sentence.loc().source().start().__repr__()+'\n')
        fp.close()

#Work out the closest match to the given sentence, out of all the sentences in the document
def closest_match(sentence1, document):
    #make a list of the words
    words = [token.type() for token in word_tokenizer.tokenize(sentence1)]
    
    #remove duplicates
    i=0
    while i<len(words):
        word = words[i]
        #if the current word is found later in the list, remove this occurrence (and try again)
        if word in words[i+1:len(words)]:
            words.remove(word)
        #otherwise, move on
        else:
            i+=1

    #remove words which occur in the list of closed-form words
    for word in words:
        if word in stop_list:
            words.remove(word)

    #calculate document frequency
    df = dict()
    #loop through each paragraph
    for paragraph in document:
        #and each sentence in the paragraph; note that we have to tokenize the paragraph into sentences
        for sentence2 in [s.type() for s in sentence_tokenizer.tokenize(paragraph)]:
            #go through each word in our list
            for word in words:
                #if this word occurs in the sentence
                if word in [token.type() for token in word_tokenizer.tokenize(sentence2)]:
                    #add the count to the document frequency
                    if word in df:
                        df[word] += 1
                    else:
                        df[word] = 1

    #calculate scores for each sentence
    score = dict()
    #go through each paragraph
    for paragraph_no in range(0, len(document)):
        current_paragraph = sentence_tokenizer.tokenize(document[paragraph_no])
        #and each sentence
        for sentence_no in range(0, len(current_paragraph)):
            current_sentence = current_paragraph[sentence_no]
            #for each word in the list
            for word in words:
                #if it occurs in this sentence
                if word in [token.type() for token in word_tokenizer.tokenize(current_sentence.type())]:
                    #add to the score for this sentence
                    if ((paragraph_no, sentence_no) in score):
                        score[(paragraph_no, sentence_no)] += 1/float(df[word])
                    else:
                        score[(paragraph_no, sentence_no)] = 1/float(df[word])

    #work out which sentence has the maximum score    
    max_score = 0
    max_sentence_loc = (0, 0)
    for sentence_loc in score:
        if score[sentence_loc] > max_score:
            max_score = score[sentence_loc]
            max_sentence_loc = sentence_loc

    #we need to calculate the maximum possible score, and only succeed if we have a certain fraction of that...
    max_possible_score = sum([1/float(df[word]) for word in df])

    if max_score < 0.75 * max_possible_score: return None
    
    return max_sentence_loc

#create the stop list
def create_stop_list():

    print 'creating stop list...'
    stop_list = []
    #we use the entire Brown corpus
    for entry in brown.items():
        print 'Processing entry:', entry
        for word in brown.tokenize(entry):

            #get the word type
            base = word.type().base().lower()
            #and the associated tag
            tag = word.type().tag()
            #if it is on our list of tags, and not already in the stop list
            if match(r'DT|CC|TO|WDT|WP.*|WRB.*|AT|EX.*|IN|MD.*', tag) and not base in stop_list:
                print 'found word:', base
                #then put it in
                stop_list.append(base)
