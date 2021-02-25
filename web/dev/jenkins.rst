NLTK c-i setup
==============

This is an overview of how our `continuous integration`_ setup works. It
includes a quick introduction to the tasks it runs, and the later sections
detail the process of setting up these tasks.

Our continuous integration is currently hosted at `Shining Panda`_, free thanks
to their FLOSS program. The setup is not specific to their solutions, it could
be moved to any `Jenkins`_ instance. The URL of our current instance is
https://jenkins.shiningpanda.com/nltk/

.. _`continuous integration`: http://en.wikipedia.org/wiki/Continuous_integration
.. _`Shining Panda`: http://shiningpanda.com
.. _`Jenkins`: http://jenkins-ci.org


Base tasks
----------

The base tasks of the c-i instance is as follows:

* Check out the NLTK project when VCS changes occur
* Build the project using setup.py
* Run our test suite
* Make packages for all platforms
* Build these web pages

Because the NLTK build environment is highly customized, we only run tests on
one configuration - the lowest version supported. NLTK 2 supports python down
to version 2.5, so all tests are run using a python2.5 virtualenv. The
virtualenv configuration is slightly simplified on ShiningPanda machines by
their having compiled all relevant python versions and making virtualenv use
these versions in their custom virtualenv builders.


VCS setup/integration
---------------------

All operations are done against the `NLTK repos on Github`_. The Jenkins
instance on ShiningPanda has a limit to the build time it can use each day.
Because of this, it only polls the main NLTK repo once a day, using the `Poll
SCM` option in Jenkins. Against the main code repo it uses public access only,
and for pushing to the nltk.github.com repo it uses the key of the user
nltk-webdeploy.

.. _`NLTK repos on Github`: https://github.com/nltk/


The base build
--------------

To build the project, the following tasks are run:

1. Create a VERSION file
  A VERSION file is created using
  ``git describe --tags --match '*.*.*' > nltk/VERSION``.
  This makes the most recent VCS tag available in nltk.__version__ etc.
2. ``python setup.py build``
  This essentially copies the files that are required to run NLTK into build/


The test suite
--------------

The tests require that all dependencies be installed. These have all been
installed beforehand, and to make them run a series of extra environment
variables are initialized. These dependencies will not be detailed until the
last section.

The test suite itself consists of doctests and unittests. Doctests are found in
each module as docstrings, and in all the .doctest files under the test folder in
the nltk repo. We run these tests using pytest_, find code coverage using
`pytest-cov`_ and check for `PEP-8`_ etc. standard violations using `pylint`_.

All these tools are easily installable through pip your favourite OS' software
packaging system. For testing, you can install the requirements with ``pip install -r requirements-test.txt``

The results of these programs are parsed and published by the jenkins instance,
giving us pretty graphs :)

.. _pytest: https://docs.pytest.org/
.. _`pytest-cov`: http://pytest-cov.readthedocs.io/
.. _`PEP-8`: http://www.python.org/dev/peps/pep-0008/
.. _`pylint`: http://www.logilab.org/project/pylint


The builds
----------

The packages are built using ``make dist``. The outputted builds are all placed
`in our jenkins workspace`_ and should be safe to distribute. Builds
specifically for mac are not available. File names are made based on the
``__version__`` string, so they change every build.

.. _`in our jenkins workspace`: http://example.com/


Web page builder
----------------

The web page is built using Sphinx_. It fetches all code documentation directly
from the code's docstrings. After building the page using ``make web`` it
pushes it to the `nltk.github.com repo on github`_. To push it, it needs access
to the repo – because this cannot be done using a deploy key, it has the ssh
key of the ``nltk-webdeploy`` user.

.. _Sphinx: http://sphinx.pocoo.org
.. _`nltk.github.com repo on github`: https://github.com/nltk/nltk.github.com
