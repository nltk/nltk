Installing NLTK
===============

NLTK is a Python package. It supports Python 2.6, 2.7 or 3.2+.

If you don't have Python installed you should install it first.
We recommend using latest Python (3.4.1 at the time of writing).

Below is a description of how to install NLTK with Python 3.4.
There are other ways to install Python and get NLTK working with
it (e.g. one can use Anaconda_, or install NLTK without virtualenv,
or use Python 2.x); please check Wiki_ for other installation methods.

Preparing the Environment
-------------------------

When the environment is ready, NLTK should install the same regardless of
an operating system. How to prepare the environment depends on OS.

Windows 64 bit
~~~~~~~~~~~~~~

TODO: check that it works

#. Download and install latest minor release of Python 3.4 from
   https://www.python.org.

#. Check that the Python is installed correctly: open the terminal and run
   ``python3.4`` - it should open the Python shell. Press Ctrl-D to close the
   Python shell.

#. It is a good practice to use a `virtual environment`_. Create and activate
   it using the following commands::

       pyvenv my-nltk-env
       my-nltk-env/Scripts/activate.bat

#. Install numpy. Some of the NLTK modules can be used without numpy, but
   many of them require numpy; you'll need numpy to follow NLTK book.

   ::

       pip install -f https://nipy.bic.berkeley.edu/scipy_installers numpy

   .. note::

        Installing Numpy can be hard on Windows, especially if a virtual
        environment is used. For 64 bit Windows there are binary wheels_
        available at https://nipy.bic.berkeley.edu/scipy_installers - they
        should work without a build environment.

        If for some reason this doesn't work you may consider using Anaconda_.


OS X
~~~~

#. Download and install latest minor release of Python 3.4 from
   https://www.python.org. Python 3 installed using http://brew.sh/ is
   also fine.

#. Check that the Python is installed correctly: open the terminal and run
   ``python3.4`` - it should open the Python shell. Press Ctrl-D to close the
   Python shell.

#. It is a good practice to use a `virtual environment`_. Create and activate
   it using the following commands::

       pyvenv ./my-nltk-env
       source ./my-nltk-env/bin/activate

#. Install numpy. Some of the NLTK modules can be used without numpy, but
   many of them require numpy; you'll need numpy to follow NLTK book.

   ::

       pip install numpy

   .. note::

        Numpy started to provide binary wheels_ for OS X; this means
        'pip install numpy' should now work fast and without a build
        environment.

Ubuntu
~~~~~~

#. TODO: install Python 3.4 from https://launchpad.net/~fkrull/+archive/ubuntu/deadsnakes
#. TODO: install packages needed to build numpy

#. It is a good practice to use a `virtual environment`_. Create and activate
   it using the following commands::

       pyvenv ./my-nltk-env
       source ./my-nltk-env/bin/activate

#. Install numpy. Some of the NLTK modules can be used without numpy, but
   many of them require numpy; you'll need numpy to follow NLTK book.

   ::

       pip install numpy

   .. note::

        It might take some time to compile numpy.


Installing NLTK
---------------

When the environment is ready, NLTK should install the same regardless of
an operating system.

#. Install NLTK::

       pip install nltk

#. Test installation: run ``python`` then type ``import nltk`` and press
   Enter - it shouldn't raise ImportError.

   Note that NLTK was installed in a virtual environment; if you open a new
   terminal window you should activate the environment again.

#. NLTK provides additional data resources; you'll need them to follow
   the NLTK Book and to use some of the NLTK modules. To get the data
   required for NLTK book run the following command from the command-line::

       python -m nltk.downloader book

   You can also run ``python -m nltk.downloader`` and use the GUI to download
   the data.

.. _virtual environment: https://packaging.python.org/en/latest/tutorial.html#virtual-environments
.. _Anaconda: https://store.continuum.io/cshop/anaconda/
.. _Wiki: https://github.com/nltk/nltk/wiki
.. _wheels: http://pythonwheels.com/
