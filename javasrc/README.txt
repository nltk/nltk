NLTK-Java Interface Code

Copyright (C) 2001-2012 NLTK Project
For license information, see LICENSE.TXT

The Java code in this directory is used by NLTK to communicate with
external Java packages, such as Mallet.  In particular, this directory
defines several command-line interfaces that are used by NLTK to
communicate with external Java packages, by spawning them as
subprocesss.  In cases where an external Java package already provides
a command-line interface, teh replacement interface provided here is
either more functional or more stable (or both).  

These command-line interfaces may be called directly by users, but
they are primarily intended for use by NLTK.
