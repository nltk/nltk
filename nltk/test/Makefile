.SUFFIXES: .doctest .errs

TESTS = chat80.doctest chunk.doctest classify.doctest corpus.doctest data.doctest discourse.doctest drt.doctest featgram.doctest featstruct.doctest grammartestsuites.doctest inference.doctest logic.doctest misc.doctest parse.doctest portuguese_en.doctest relextract.doctest resolution.doctest semantics.doctest stem.doctest tag.doctest tokenize.doctest toolbox.doctest toolbox_language.doctest tree.doctest treetransforms.doctest gwordnet.doctest

ERRS := $(TESTS:.doctest=.errs)

.doctest.errs:
	python ./doctest_driver.py $< > $@ 2>&1

all: $(ERRS)
