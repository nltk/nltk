.SUFFIXES: .doctest .errs

TESTS = $(wildcard *.doctest)
#TESTS = chat80.doctest chunk.doctest classify.doctest corpus.doctest data.doctest discourse.doctest drt.doctest featgram.doctest featstruct.doctest grammartestsuites.doctest inference.doctest logic.doctest misc.doctest parse.doctest portuguese_en.doctest relextract.doctest resolution.doctest semantics.doctest stem.doctest tag.doctest tokenize.doctest toolbox.doctest toolbox_language.doctest tree.doctest treetransforms.doctest wordnet.doctest

ERRS := $(TESTS:.doctest=.errs)

.doctest.errs:
	python ./doctest_driver.py $< > $@

all: $(ERRS)

clean:
	rm -f *.errs
