#
# Author: Rohith Bhaskaran <vrarohith@gmail.com>
#

import os
import tempfile

class StanfordParser:
    def __init__(self,working_dir=None):
        """
        An interface for parsing with the Stanford Parser.

        :param working_dir: Absolute path to the Stanford parser without trailing slash 
                            should be given
        """
        if(working_dir== None):
            self.working_dir='/usr/lib/stanford-parser-*'
        else:
            self.working_dir = working_dir
    
    def parse(self, text):
        """
        Use Stanford parser for dependency parsing a text consisting of many sentences.
        The parser will automatically separate sentences and create typed dependency for each sentence separately. 

        :param text: Input text to parse
        :type sentence: string
        :return: ``Typed dependency relation`` the dependency graph representation of the sentence
        """
        in_file = self.makeFile(text)
        cmd = 'java -mx150m -cp "'+self.working_dir+'/*:" edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat "typedDependencies" edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz $* >'+self.working_dir +'stanford_output.txt'
        os.system(cmd)
        out_file = open(self.working_dir+"stanford_output.txt")
        ret = out_file.read()
        os.remove(self.working_dir+'stanford_output.txt')
        os.remove(in_file)
        return ret

    def makeFile(self,text):
        """
        This method will copy the input text into a temporary file 

        :param text: Input text to parse
        :type sentence: string
        :return: name of temporary file containing the input text.
        """
        input_file = tempfile.NamedTemporaryFile(prefix='stanford_input.txt',
                                                 dir=self.working_dir,
                                                 delete=False)
        input_file.write(text)
        input_file.write('\n')
        return input_file.name    
        
 
        
