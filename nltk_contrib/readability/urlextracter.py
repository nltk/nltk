#!/usr/bin/python
# -*- coding: utf-8 -*- 
# Sets the encoding to utf-8 to avoid problems with æøå
import urllib
import htmlentitydefs
from sgmllib import *
import re

class URLextracter(SGMLParser):
    
    style = False
    script = False
    hyperlink = False
    
    linklist = []
    
    def __init__(self, url='http://python.org'):
        self.reset()
        try:
            self.sock = urllib.urlopen(url)
            self.feed(self.sock.read())
            self.sock.close()
            self.close()
        except IOError:
            print "Could not connect, or the markup has (too) bad structure"
            raise SGMLParseError
        
    def start_style(self,attr):
        self.style = True
    
    def end_style(self):
        self.style = False
        
    def start_script(self,attr):
        self.script = True
    
    def do_script(self,attr):
        pass
    
    def end_script(self):
        self.script = False
        
    def start_a(self,attr):
        self.hyperlink = True
        href = [v for k, v in attr if k=='href']
        if href:
            self.linklist.extend(href)
    
    def end_a(self):
        self.hyperlink = False
   
    def reset(self):
        self.pieces = []
        self.linklist = []
        SGMLParser.reset(self)
        
    def handle_data(self, text):
        #tags_to_skip = [self.style, self.script, self.hyperlink]
        tags_to_skip = [self.style, self.script]
        if True in tags_to_skip:
            pass
        else: 
            self.pieces.append(text)
    
    def handle_declaration(self,decl):
        pass
    
    def report_unbalanced(self,tag):
        pass
    
    def unknown_starttag(self, tag, attrs):
        pass

    def unknown_endtag(self, tag):         
        pass
    
    def unknown_charref(self,tag):
        pass

        
    def output(self):
        # Clean up text and return it
        content = "" . join(self.pieces)
        content = self._setEncoding(content)
        content = re.sub(r"[^0-9a-zA-ZæøåÆØÅ.?!\n\r]", " ", content)
        content = content.strip()
        #lines = content.replace("\t", " ").replace("\r","\n").splitlines()
        lines = content.splitlines()
        content = ""
        for line in lines:
            temp = line.strip()
            if temp == "" or temp == " ":
                lines.remove(line)
            else:    
                if len(temp.split(" ")) > 2:
                    content += line + "\n"
        return content
        
        
    def _setEncoding(self,text):
        try:
            text = unicode(text, "utf8").encode("utf8")
        except UnicodeError:
            try:
                text = unicode(text, "iso8859_1").encode("utf8")
            except UnicodeError:
                text = unicode(text, "ascii", "replace").encode("utf8")
        return text
    
    def demo(self):
        print 'This class takes an URL, and extracts the text it contains.'
        print 'It also removes special characters and numbers,'
        print 'and sentences must consist of at least'
        print '3 words to not be ignored.'
        
        print '\nFetching text from www.python.org'
        u = URLextracter()
        print "=" * 40
        print u.output()
    demo = classmethod(demo)

def demo():
    URLextracter.demo()

if __name__ == "__main__":
    URLextracter.demo()
