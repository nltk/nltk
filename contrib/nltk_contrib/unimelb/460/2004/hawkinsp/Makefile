#CXXFLAGS=-I/usr/include/python2.3 -Wall -fPIC
CXXFLAGS=-I/local/solaris86/apps/python-2.3/include/python2.3 -Wall -fPIC

all: mfcc.so vecquant 
	chmod a+x extract_mfcc.py vecquant.py recog.py
	(cd java ; $(MAKE))

mfcc.so: mfcc.o SpeechProc.o
	g++ -shared mfcc.o SpeechProc.o -o mfcc.so

vecquant: vecquant.o vec.o
	g++ -o vecquant vecquant.o vec.o

clean:
	rm -f vecquant.o vec.o SpeechProc.o vecquant mfcc.o mfcc.so *.pyc java/*.class

vecquant.o: pspeech.h
vec.o: pspeech.h
