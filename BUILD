Building an NLTK-Lite distribution
----------------------------------

Prepare for the build by checking that all code demonstrations work, and that
the tutorial code samples all work (cd nltk/lite/doc/en; make errs)


A. VERSION NUMBER

1. cd nltk/lite
2. Modify nltk_lite/__init__.py with the version number (2 places)
3. Edit doc/definitions.txt with new version number
4. Edit ../doc/webpage/install*.html with new version number
5. Edit ../doc/webpage/index.html with new release announcement
6. Commit all the above changes


B. BUILD

The build requires docutils, pdflatex

1. Check out a clean copy of the CVS tree (or make clean)
2. cd nltk/lite/doc; make all
3. cd nltk/lite; make distributions (see dist/ for the results)


C. ISO IMAGE

1. Check for new versions of Python and Numeric
   (if so, modify top level Makefile and commit; make python)
2. make iso (see dist/ for the iso image)


D. UPLOAD

1. cd nltk/lite/dist/
2. ftp upload.sourceforge.net (anonymous)
3. cd incoming; binary; mput * (wait...)
4. visit https://sourceforge.net/project/admin/editpackages.php?group_id=30982
5. add release: release name is just x.x (no nltk prefix)
6. associate files to release; set types using earlier release as model


E. WEBSITE

1. rsync the docs, code, and webpage (remove .pyc and .pyo files)
2. add a news item
3. post to one or more of the mailing lists, including course mailing lists


F. INSTALLATION

1. download and install new version on all machines
2. contact relevant sysads to install new version
3. copy dist directory to memory stick
4. check out cvs repository to memory stick
