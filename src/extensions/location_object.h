/* Natural Language Toolkit: C Implementation of Locations (header)
 *
 * Copyright (C) 2003 University of Pennsylvania
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://nltk.sourceforge.net>
 * For license information, see LICENSE.TXT
 *
 * $Id$
 *
 * This class provides a drop-in replacement for Location.  Since
 * Locations are used extensively in NLTK (for Tokens), this C
 * implementation can give a signifigant performance boost.
 */

#ifndef LOCATION_OBJECT_H
#define LOCATION_OBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include <Python.h>

/* The location type object. */
staticforward PyTypeObject locationType;

/* The Location constructor */
extern DL_IMPORT(PyObject*)
create_location(PyObject* self, PyObject *args, PyObject *keywords);

/* A macro to test if something's a Location. */
#define is_location(v) ((v)->ob_type == &locationType)

#endif
