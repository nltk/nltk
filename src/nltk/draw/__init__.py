# Natural Language Toolkit: graphical representations package
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Methods for graphically displaying the objects created by the Toolkit.
These methods are primarily intended to help students visualize the
objects that they create.  Each drawable object has a X{draw method};
calling this method on the object will create a new window, containing
a graphical representation of the object.  In addition, this window
can be used to print the object's graphical representation to a
postscript file.

Methods in the draw package should not be used directly; instead, call 
the C{draw()} member function on any drawable object.  This will
automatically dispatch to the correct method in the draw package.
"""
