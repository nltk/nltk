.SUFFIXES: .doctest .errs

TESTS = $(wildcard *.doctest)

ERRS := $(TESTS:.doctest=.errs)

.doctest.errs:
	python ./doctest_driver.py $< > $@

all: $(ERRS)

clean:
	rm -f *.errs
