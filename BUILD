Building an NLTK-Lite distribution
----------------------------------

Prepare for the build by checking that all code demonstrations work, and that
the tutorial code samples all work (cd nltk/lite/doc/en; make errs)


A. VERSION NUMBER AND RELEASE ANNOUNCEMENT

1. Modify nltk_lite/__init__.py with the version number (2 places)
2. Edit doc/definitions.txt with new version number
3. Edit web/install*.html with new version number
4. Edit web/index.html with new release announcement
5. Commit all the above changes


B. PYTHON AND NUMERIC VERSIONS

1. Check for new versions of Python and Numeric
2. Modify top level Makefile and commit
3. Modify web/install*.html with new URLs and commit
4. make python  (to download)


C. BUILD

The build requires docutils, pdflatex

1. Check out a clean copy of the subversion repository (or make clean)
2. make distributions (see dist/ for the results)
3. make iso (see dist/ for the iso image)


D. UPLOAD

1. cd nltk/dist/
2. ftp upload.sourceforge.net (anonymous)
3. cd incoming; binary; mput * (wait...)
4. visit https://sourceforge.net/project/admin/editpackages.php?group_id=30982
5. add release: release name is just x.x (no nltk prefix)
6. associate files to release; set types using earlier release as model


E. WEBSITE

1. cd web; make rsync
2. rsync code and docs (remove .pyc and .pyo files)
3. post to one or more of the mailing lists, including course mailing lists


F. INSTALLATION

1. download and install new version on all machines
2. contact relevant sysads to install new version
3. copy dist directory to memory stick
4. check out cvs repository to memory stick
