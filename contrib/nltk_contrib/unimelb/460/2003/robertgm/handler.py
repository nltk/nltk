from xml.sax import make_parser
from xml.sax.handler import ContentHandler

#Normalise whitespace - replace arbitrary sequences of whitespace with a single
#space character. We add a space at the end to ensure that sentences are
#separated, except when we would otherwise return an empty string.
def normalise_whitespace(text):
    normalised_text =  ' '.join(text.split())
    return normalised_text!='' and normalised_text+' ' or ''

#XML SAX handler class
class TrainingDocHandler(ContentHandler):
    def __init__(self):
        self.inside_text = 0
        self.inside_summary = 0
        #the summary is a single string
        self.summary = ""
        #the text is a list of strings
        self.text = []

    #respond to the start of an element
    def startElement(self, el, attr):
        if el == "ABSTRACT":            
            self.inside_summary = 1
        if el == "P" and not self.inside_summary:
            #start a new string (=paragraph) inside self.text
            self.text.append("")
            self.inside_text = 1

    #respond to the end of an element
    def endElement(self, el):
        if el == "ABSTRACT":
            self.inside_summary = 0
        if el == "P" and not self.inside_summary:
            self.inside_text = 0

    #process some text
    def characters(self, chars):
        if self.inside_summary:
            #append these chars to the summary
            self.summary += normalise_whitespace(chars).encode('latin-1')
        if self.inside_text:
            #append these chars to the last element (paragraph) of the text
            self.text[len(self.text)-1]+=normalise_whitespace(chars).encode('latin-1')

