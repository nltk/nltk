/* Natural Language Toolkit: C Implementation of nltk.token
 *
 * Copyright (C) 2003 University of Pennsylvania
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://nltk.sourceforge.net>
 * For license information, see LICENSE.TXT
 *
 * $Id$
 *
 * This module provides a drop-in replacement for the Location and
 * Token classes.  Since these classes are used extensively in NLTK
 * (for Tokens), this C implementation can give a signifigant
 * performance boost.
 *
 * Compilation of this extension is handled by NLTK's setup.py script.
 * To test this module, use NLTK's setup.py script to build it:
 *     % python setup.py build
 *
 * This will create a "build" directory, containing the file
 * "build/lib.???/nltk/_ctoken.so", where the name of the "lib.???" 
 * subdirectory depends on your architecture.  Copy this file to
 * "nltk/_ctoken.so", and you should be able to import the module with:
 *     >>> import nltk._ctoken
 */

#include <Python.h>
#include "location_object.h"

/* Methods defined by the token module. */
static PyMethodDef _ctoken_methods[] = {
    /* The Location constructor function. */
    {"Location", (PyCFunction)create_location,
     METH_VARARGS|METH_KEYWORDS,
     "Create a new Location object."},

    /* End of list */
    {NULL, NULL, 0, NULL}
};

/* Module initializer */
DL_EXPORT(void) init_ctoken(void) 
{
    /* type(Location) = <type 'type'> */
    locationType.ob_type = &PyType_Type;

    /* Initialize the module */
    Py_InitModule("_ctoken", _ctoken_methods);
}

