#!/usr/bin/python
googleapi = '/nlptools/googleapi/googleapi.jar'
KEY = "TL8ZdoNQFHK8IIyd7f7oTaqLTJm1VANN" #cs
#KEY = "lST0gVVQFHKcC8YCKIJCd/8m6HcfFBPI"   #ugrad

import sys
import commands

def main():
	if "-c" in sys.argv:
		combine = True
	else:
		combine = False
	if combine:
		terms = sys.stdin.readlines()
		combins = []
		for i in range(0, len(terms)+1):
			for j in range(i+1, len(terms)+1):
				combins.append(terms[i:j])
		combins.sort(lambda x,y: cmp(len(y),len(x)))
		termstrings = ['\n'.join(termlist) for termlist in combins]			
	else:
		termstrings = sys.stdin
	com_line_tp =  'java -cp ' + googleapi + \
		' com.google.soap.search.GoogleAPIDemo ' + KEY + ' search \"%s\"';
	for line in termstrings:
		term = line.rstrip()
		com_line = com_line_tp % term
		print(commands.getoutput(com_line))

if __name__ == "__main__":
	main()
