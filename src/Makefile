#
# NLP Toolkit main source Makefile
# Edward Loper
#
# Produce both built and source distributions of the Python code.
#
# Created [05/27/01 09:16 PM]
#

all: distributions

test:
	echo "No tests implemented yet"

clean:
	rm -rf build dist MANIFEST

# Distributions.
# Build all from scratch; and create links for convenient access.
distributions: clean sdist bdist
	(cd dist && ln -s nltk-*.noarch.rpm nltk.rpm)
	(cd dist && ln -s nltk-*.tar.gz nltk.tgz)
	(cd dist && ln -s nltk-*.zip nltk.zip)
	(cd dist && ln -s nltk-*.exe nltk.exe)

# Source distributions
sdist: gztardist zipdist

# Built distributions
bdist: rpmdist windist

# Produce dist/$(NAME)-$(VERSION).tar.gz
gztardist:
	python setup.py sdist --format=gztar

# Produce dist/$(NAME)-$(VERSION).tar.gz
zipdist:
	python setup.py sdist --format=zip

# Produce dist/$(NAME)-$(VERSION)-1.noarch.rpm
# Produce dist/$(NAME)-$(VERSION)-1.src.rpm
rpmdist:
	python setup.py bdist --format=rpm

# Produce dist/$(NAME)-$(VERSION).win32.exe
windist:
	python setup.py bdist --format=wininst
