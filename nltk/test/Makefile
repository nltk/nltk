.SUFFIXES: .doctest .errs

TESTS = chunk.doctest classify.doctest corpus.doctest data.doctest drt.doctest featgram.doctest featstruct.doctest grammartestsuites.doctest logic.doctest misc.doctest parse.doctest portuguese_en.doctest prover.doctest relextract.doctest sem-exercise.doctest semantics.doctest stem.doctest tag.doctest tokenize.doctest toolbox.doctest toolbox_language.doctest tree.doctest treetransforms.doctest utilities.doctest wordnet.doctest

ERRS := $(TESTS:.doctest=.errs)

.doctest.errs:
	python ./doctest_driver.py $< > $@ 2>&1

all: $(ERRS)
