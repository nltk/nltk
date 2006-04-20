Building an NLTK-Lite distribution
----------------------------------

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@ PREPARE
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

A. ERROR CHECKING

  1. Code demos, graphical demonstrations
  2. API docs (cd doc; make api)
  3. Tutorial examples (cd doc/en; make errs)

B. CHANGELOG AND RELEASE ANNOUNCEMENT

  1. Update the ChangeLog ("svn log")
  2. Edit web/index.html with new release announcement
  3. Commit these changes

C. VERSION NUMBER

  1. Modify nltk_lite/__init__.py with the version number (2 places)
  2. Edit doc/definitions.txt with new version number
  3. Edit web/install*.html with new version number
  4. Commit these changes

D. PYTHON AND NUMERIC VERSIONS

  1. Check for new versions of Python and Numeric
  2. Modify top level Makefile and commit
  3. Modify web/install*.html with new URLs and commit
  4. Commit these changes

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@ BUILD
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

The build requires docutils, pdflatex

  1. Check out a clean copy of the subversion repository (or make clean)
  2. make distributions (see dist/ for the results)
  3. make python  (to download all python distros if necessary)
  4. make iso (see dist/ for the iso image)

  (test the distributions?)

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@ RELEASE
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

A. UPLOAD DISTRIBUTIONS

  1. cd nltk/dist/
  2. ftp upload.sourceforge.net (anonymous)
  3. cd incoming; binary; mput * (wait...)
  4. visit https://sourceforge.net/project/admin/editpackages.php?group_id=30982
  5. add release: release name is just x.x (no nltk prefix)
  6. associate files to release; set types using earlier release as model
  7. past in ChangeLog

B. WEBSITE

  1. cd web; make rsync
  2. rsync code and docs (remove .pyc and .pyo files)
  3. post to one or more of the mailing lists, including course mailing lists

C. INSTALLATION

  1. download and install new version on all machines
  2. contact relevant sysads to install new version
  3. copy dist directory to memory stick
  4. check out svn repository to memory stick
