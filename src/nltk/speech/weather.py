# Simple Python application using Festival Text-to-Speech
#
# Author: David Zhang <dlz@students.cs.mu.oz.au>
#	  Steven Bird <sb@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Simple application demonstrating the use of the Festival Text-to-Speech
function in Python through the "tts" extension module. The application
downloads the web page for Melbourne weather forecast, uses a regular
expression to extract the relevant section of the page, then sends the result
to the tts module to be converted to speech.

As the URL and the regular expression are both hard-coded, this application
is very sensitive to changes in the location and layout of the target web
page.
"""

import urllib, re, nltk.speech.tts

URL	= "http://www.bom.gov.au/cgi-bin/wrap_fwo.pl?IDV10450.txt"
REGEXP	= "(Forecast for Melbourne .*)Suburban"

try:
	page = urllib.urlopen(URL).read()
except IOError, e:
	print "Unable to connect to web server."
	sys.exit(1)

x = re.search(REGEXP, page, re.DOTALL)  # DOTALL ensures newlines are included

if x:
	text = x.group(1)
	print text

	tts.initialize()
	tts.say_text(text)

else:
	print "Web page does not have the expected format."
