FROM python:3.5

# USER ubuntu

WORKDIR /usr/src/app

# Copy source files from the host to the container's workdir
COPY . .

# Install NLTK package
RUN pip install .
RUN pip install tox

RUN source tools/travis/pre-install.sh
RUN chmod +x tools/travis/coverage-pylint.sh
RUN chmod +x tools/travis/third-party.sh

# Keep the container running
CMD tail -f /dev/null
# CMD tox -e py35
