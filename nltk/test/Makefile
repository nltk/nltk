.SUFFIXES: .doctest .errs .html

TESTS = $(wildcard *.doctest)

ERRS := $(TESTS:.doctest=.errs)

HTML = $(TESTS:.doctest=.html) # $(IPYNB:.ipynb=.html)

IPYNB = $(wildcard *.ipynb)

.doctest.errs:
	pytest $< > $@

.doctest.html:
	rst2html.py $< > $@

%.html: %.ipynb
	ipython nbconvert $<

all: $(ERRS)

html: $(HTML)

install_html:
	cp $(HTML) ../../../nltk.github.com/howto

clean:
	rm -f *.errs
