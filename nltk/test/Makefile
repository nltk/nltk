.SUFFIXES: .doctest .errs .html

TESTS = $(wildcard *.doctest)

ERRS := $(TESTS:.doctest=.errs)

HTML = $(TESTS:.doctest=.html)

.doctest.errs:
	python ./runtests.py $< > $@

.doctest.html:
	rst2html.py $< > $@

all: $(ERRS)

html: $(HTML)

install_html:
	cp $(HTML) ../../../nltk.github.com/howto

clean:
	rm -f *.errs
