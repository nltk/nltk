Installing NLTK Data
====================

NLTK comes with many corpora, toy grammars, trained models, etc.   A complete list is posted at: http://nltk.org/nltk_data/

To install the data, first install NLTK (see http://nltk.org/install.html), then use NLTK's data downloader as described below.

Apart from individual data packages, you can download the entire collection (using "all"), or just the data required for the examples and exercises in the book (using "book"), or just the corpora and no grammars or trained models (using "all-corpora").

Interactive installer
---------------------

*For central installation on a multi-user machine, do the following from an administrator account.*

Run the Python interpreter and type the commands:

    >>> import nltk
    >>> nltk.download()

A new window should open, showing the NLTK Downloader.  Click on the File menu and select Change Download Directory.  For central installation, set this to ``C:\nltk_data`` (Windows), or ``/usr/share/nltk_data`` (Mac, Unix).  Next, select the packages or collections you want to download.

If you did not install the data to one of the above central locations, you will need to set the ``NLTK_DATA`` environment variable to specify the location of the data.  (On a Windows machine, right click on "My Computer" then select ``Properties > Advanced > Environment Variables > User Variables > New...``)

Test that the data has been installed as follows.  (This assumes you downloaded the Brown Corpus):

    >>> from nltk.corpus import brown
    >>> brown.words()
    ['The', 'Fulton', 'County', 'Grand', 'Jury', 'said', ...]

Installing via a proxy web server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your web connection uses a proxy server, you should specify the proxy address as follows.  In the case of an authenticating proxy, specify a username and password.  If the proxy is set to None then this function will attempt to detect the system proxy.

    >>> nltk.set_proxy('http://proxy.example.com:3128' ('USERNAME', 'PASSWORD'))
    >>> nltk.download() 

Command line installation
-------------------------

The downloader will search for an existing ``nltk_data`` directory to install NLTK data.  If one does not exist it will attempt to create one in a central location (when using an administrator account) or otherwise in the user's filespace.  If necessary, run the download command from an administrator account, or using sudo.  The default system location on Windows is ``C:\nltk_data``; and on Mac and Unix is ``/usr/share/nltk_data``.  You can use the ``-d`` flag to specify a different location (but if you do this, be sure to set the ``NLTK_DATA`` environment variable accordingly).

Python 2.5-2.7: Run the command ``python -m nltk.downloader all``.  To ensure central installation, run the command ``sudo python -m nltk.downloader -d /usr/share/nltk_data all``.

Windows: Use the "Run..." option on the Start menu.  Windows Vista users need to first turn on this option, using ``Start -> Properties -> Customize`` to check the box to activate the "Run..." option. 

Test the installation: Check that the user environment and privileges are set correctly by logging in to a user account,
starting the Python interpreter, and accessing the Brown Corpus (see the previous section).

