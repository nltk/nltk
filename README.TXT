###############################################################
###                 THE NLTK CVS REPOSITORY                 ###
###~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~###
### Copyright (C) 2001 University of Pennsylvania           ###
### Author: Edward Loper <edloper@gradient.cis.upenn.edu>   ###
### URL: <http://nltk.sf.net>                               ###
### For license information, see LICENSE.TXT                ###
###############################################################

Introduction
~~~~~~~~~~~~
    nltk is a Python package that simplifies the construction of
    programs that process natural language; and defines standard
    interfaces between the different components of an NLP system.


Repository Structure
~~~~~~~~~~~~~~~~~~~~

nltk
  |
  +-- src      .............. Python source code.
  |    |
  |    +-- nltk    .......... Source code for the toolkit itself.
  |    |
  |    +-- [demo]  .......... Source code for demo programs
  |
  +-- doc      .............. Documentation
  |    |
  |    +-- technical ........ Technical reports (LaTeX)
  |    |    |
  |    |    +-- proposal
  |    |    |
  |    |    +-- printing
  |    |    |
  |    |    +-- etc.
  |    |
  |    +-- tutorial ......... Tutorial-style documentation (Docbook)
  |    |    |
  |    |    +-- introduction
  |    |    |
  |    |    +-- etc.
  |    |
  |    +-- misc ............. Assorted short-term and meta documentation
  |
  +-- psets    .............. Problem sets and sample exercise sets


Documentation
~~~~~~~~~~~~~
    Documentation is split into four sets:

        - Tutorial documentation: describes how to use the toolkit.
        - Technical reports: describe how the toolkit works, and
          provides the rational behind its design.
        - Reference documentation: provides precise descriptions of
          each Python module, class, and function defined by the
          toolkit. 
        - Miscellaneous documentation: is a place to store working
          documentation (e.g., descriptions of current issues with the 
          toolkit, and intended future additions).

    Tutorial Documentation
    ~~~~~~~~~~~~~~~~~~~~~~
        Each tutorial document is given a short descriptive name
        (typically 5-15 characters, consisting of lower case
        letters).  A tutorial document whose name is <name> is stored
        in doc/tutorial/<name>, and contains at least the following
        files: 

            - <name>.xml .... The tutorial document, written using the 
                              Docbook DTD.
            - abstract.txt .. A one-paragraph plaintext description
                              of the document.  This file is used when
                              generating the description of the
                              document on the webpage.
            - status.txt .... A short (2-3 word) plaintext description 
                              of the current status of the document
                              (e.g., "early draft," "complete," or
                              "not started").  This file is used when
                              generating the description of the
                              document on the webpage.

    Technical Reports
    ~~~~~~~~~~~~~~~~~
        Each technical report is given a short descriptive name
        (typically 5-15 characters, consisting of lower case
        letters).  A technical report whose name is <name> is stored
        in doc/technical/<name>, and contains at least the following
        files: 

            - <name>.tex .... The techical report, written using 
                              LaTeX.
            - abstract.txt .. A one-paragraph plaintext description
                              of the report.  This file is used when
                              generating the description of the
                              report on the webpage.
            - status.txt .... A short (2-3 word) plaintext description 
                              of the current status of the report
                              (e.g., "early draft," "complete," or
                              "not started").  This file is used when
                              generating the description of the
                              report on the webpage.

    Reference Documentation
    ~~~~~~~~~~~~~~~~~~~~~~~
        The reference documentation is generated automatically from
        the Python source code; it is not included in the CVS
        repository.

    Miscellaneous Documentation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        The miscellaneous documentation is maintained in a single
        directory (doc/misc).  It consists primarily of plaintext and
        LaTeX files.


Makefiles
~~~~~~~~~
    The main Makefile can be used to perform the following tasks:

        make documentation: Convert all documentation and problem sets
            to output formats (ps and pdf for technical documentation
            and problem sets; html for tutorial documentation).
        make test: Run unit testing on the toolkit.
        make distributions: Construct distribution files for the
            toolkit. 
        make clean: Remove all temporary files and output files
            generated by make.

    In addition, the Makefiles in the doc, psets, and src directories
    can be used to perform other tasks.


Problem Sets
~~~~~~~~~~~~
    The structure of the problem set directory has not yet been
    decided.  The two options under consideration are:

        - Store each problem set or exercise set in its own directory, 
          along with the corresponding solutions.
        - Store all problem sets, sample exercises, and solutions in a 
          single directory.

    The naming conventions for problem sets have also not yet been
    decided. 

