# Natural Language Toolkit: source Makefile
#
# Copyright (C) 2001-2018 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#	 Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

PACKAGE = nltk
PYTHON = python
VERSION = $(shell $(PYTHON) -c 'import nltk; print(nltk.__version__)' | sed '/^Warning: */d')
NLTK_URL = $(shell $(PYTHON) -c 'import nltk; print(nltk.__url__)' | sed '/^Warning: */d')

MANYLINUX_IMAGE_X86_64=quay.io/pypa/manylinux1_x86_64
MANYLINUX_IMAGE_686=quay.io/pypa/manylinux1_i686

.PHONY: all clean clean_code

all: dist

########################################################################
# TESTING
########################################################################

DOCTEST_DRIVER = nltk/test/runtests.py
DOCTEST_FILES = nltk/test/*.doctest
DOCTEST_CODE_FILES = nltk/*.py nltk/*/*.py

doctest:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_FILES)

doctest_code:
	$(PYTHON) $(DOCTEST_DRIVER) $(DOCTEST_CODE_FILES)

demotest:
	find nltk -name "*.py"\
        -and -not -path *misc* \
        -and -not -name brown_ic.py \
        -exec echo ==== '{}' ==== \; -exec python '{}' \;

########################################################################
# DISTRIBUTIONS
########################################################################

PHONY: sdist dist zipdist windist wheel_manylinux wheel_manylinux64 wheel_manylinux32

dist: zipdist windist

sdist: dist/$(PACKAGE)-$(VERSION).tar.gz

dist/$(PACKAGE)-$(VERSION).tar.gz:
	$(PYTHON) setup.py sdist --formats=gztar

# twine only permits one source distribution
#gztardist: clean_code
#	$(PYTHON) setup.py -q sdist --format=gztar
zipdist: clean_code
	$(PYTHON) setup.py -q sdist --format=zip
windist: clean_code
	$(PYTHON) setup.py -q bdist --format=wininst --plat-name=win32

	wheel_manylinux: wheel_manylinux64 wheel_manylinux32

	wheel_manylinux32 wheel_manylinux64: dist/$(PACKAGE)-$(VERSION).tar.gz
		echo "Building wheels for $(PACKAGE) $(VERSION)"
		mkdir -p wheelhouse_$(subst wheel_,,$@)
		time docker run --rm -t \
			-v $(shell pwd):/io \
			-e CFLAGS="-O3 -g1 -mtune=generic -pipe -fPIC" \
			-e LDFLAGS="$(LDFLAGS) -fPIC" \
			-e WHEELHOUSE=wheelhouse_$(subst wheel_,,$@) \
			$(if $(patsubst %32,,$@),$(MANYLINUX_IMAGE_X86_64),$(MANYLINUX_IMAGE_686)) \
			bash -c '\
				for PYBIN in /opt/python/*/bin; do \
					$$PYBIN/python -V; \
					$$PYBIN/pip install -U pip setuptools; \
					$$PYBIN/pip install Cython six; \
					{ CYTHONIZE_NLTK=true $$PYBIN/pip wheel -w /io/$$WHEELHOUSE /io/$< & } ; \
			    done; wait; \
			    for whl in /io/$$WHEELHOUSE/$(PACKAGE)-$(VERSION)-*-linux_*.whl; do \
			    	auditwheel repair $$whl -w /io/$$WHEELHOUSE; \
				done'


########################################################################
# CLEAN
########################################################################

clean: clean_code
	rm -rf build iso dist api MANIFEST nltk-$(VERSION) nltk.egg-info

clean_code:
	rm -f `find nltk -name '*.pyc'`
	rm -f `find nltk -name '*.pyo'`
	rm -f `find . -name '*~'`
	rm -f MANIFEST # regenerate manifest from MANIFEST.in
