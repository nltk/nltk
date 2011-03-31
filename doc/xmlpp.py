"""
Copyright (c) 2008, Fredrik Ekholdt
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

* Neither the name of None nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

(Minor modifications by Steven Bird)
"""
import sys

def usage(this_file):
    return """SYNOPSIS: pretty print an XML document
USAGE: python %s <filename> or use stdin as input\n""" % this_file

def pprint(indent_level, line):
    if line.strip():
        sys.stdout.write(" " * indent_level +  line + "\n")

def get_next_elem(data):
    start_pos = data.find("<")
    end_pos = data.find(">") + 1
    retval = data[start_pos:end_pos]
    stopper = retval.find("/")
    single = (stopper > -1 and ((retval.find(">") - stopper) < (stopper - retval.find("<"))))

    ignore_excl = retval.find("<!") > -1
    ignore_question =  retval.find("<?") > -1

    if ignore_excl:
        cdata = retval.find("<![CDATA[") > -1
        if cdata:
            end_pos = data.find("]]>")
            if end_pos > -1:
                end_pos = end_pos + len("]]>")

    elif ignore_question:
        end_pos = data.find("?>") + len("?>")
    ignore = ignore_excl or ignore_question
    
    no_indent = ignore or single

    #print retval, end_pos, start_pos, no_indent
    return start_pos, \
           end_pos, \
           stopper > -1, \
           no_indent


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        sys.stderr.write(usage(sys.argv[0]))
        sys.exit(1)
    if len(sys.argv) < 2:
        data = sys.stdin.read()
    else:
        filename = sys.argv[1]
        data = open(filename).read()

    INDENT = 2
    
    indent_level = 0

    start_pos, end_pos, is_stop, no_indent  = get_next_elem(data)
    while ((start_pos > -1 and end_pos > -1)):
        pprint(indent_level, data[:start_pos].strip())
        data = data[start_pos:]
        if is_stop and not no_indent:
            indent_level = indent_level - INDENT
        pprint(indent_level, data[:end_pos - start_pos])
        data = data[end_pos - start_pos:]
        if not is_stop and not no_indent :
            indent_level = indent_level + INDENT

        if not data:
            break
        else:
            start_pos, end_pos, is_stop, no_indent  = get_next_elem(data)
