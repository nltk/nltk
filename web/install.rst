Installing NLTK
===============

NLTK requires Python versions 3.5, 3.6, 3.7, or 3.8

For Windows users, it is strongly recommended that you go through this guide to install Python 3 successfully https://docs.python-guide.org/starting/install3/win/#install3-windows

Setting up a Python Environment (Mac/Unix/Windows)
--------

Please go through this guide to learn how to manage your virtual environment managers before you install NLTK,  https://docs.python-guide.org/dev/virtualenvs/

Alternatively, you can use the Anaconda distribution installer that comes "batteries included" https://www.anaconda.com/distribution/ 

Mac/Unix
--------

#. Install NLTK: run ``pip install --user -U nltk``
#. Install Numpy (optional): run ``pip install --user -U numpy``
#. Test installation: run ``python`` then type ``import nltk``

For older versions of Python it might be necessary to install setuptools (see http://pypi.python.org/pypi/setuptools) and to install pip (``sudo easy_install pip``).

Windows
-------

These instructions assume that you do not already have Python installed on your machine.

32-bit binary installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Install Python 3.8: http://www.python.org/downloads/ (avoid the 64-bit versions)
#. Install Numpy (optional): https://www.scipy.org/scipylib/download.html
#. Install NLTK: http://pypi.python.org/pypi/nltk
#. Test installation: ``Start>Python38``, then type ``import nltk``

Installing Third-Party Software
-------------------------------

Please see: https://github.com/nltk/nltk/wiki/Installing-Third-Party-Software


Installing NLTK Data
-------------------------------

After installing the NLTK package, please do install the necessary datasets/models for specific functions to work. 

If you're unsure of which datasets/models you'll need, you can install the "popular" subset of NLTK data, on the command line type `python -m nltk.downloader popular`, or in the Python interpreter `import nltk; nltk.download('popular')`

For details, see http://www.nltk.org/data.html
