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

#ifndef CTOKEN_H
#define CTOKEN_H

/*********************************************************************
 *  Location
 *********************************************************************/

/* The struct that is used to encode Location instances. */
typedef struct LocObjectStruct {
    PyObject_HEAD      /* Object head: refcount & type */
    long int start;    /* The start index */
    long int end;      /* The end index */
    PyObject *unit;    /* The unit */
    PyObject *source;  /* The source */
} locationObject;

/* The Location type. */
staticforward PyTypeObject locationType;

/* A macro to test if something's a Location. */
#define is_location(v) ((v)->ob_type == &locationType)

/* Location Constructor & Destructor */
static PyObject *
  location_new(PyTypeObject* type, PyObject *args, PyObject *keywords);
static int
  location_init(locationObject* self, PyObject *args, PyObject *keywords);
static void
  location_dealloc(locationObject* self);

/* Location Methods */
static PyObject *
  location_length(locationObject* self, PyObject *args);
static locationObject *
  location_start_loc(locationObject* self, PyObject *args);
static locationObject *
  location_end_loc(locationObject* self, PyObject *args);
static locationObject *
  location_union(locationObject* self, PyObject *args);
static PyObject *
  location_prec(locationObject* self, PyObject *args);
static PyObject *
  location_succ(locationObject* self, PyObject *args);
static PyObject *
  location_overlaps(locationObject* self, PyObject *args);
static PyObject *
  location_select(locationObject* self, PyObject *args);

/* Location operators */
static PyObject *
  location__repr__(locationObject *self);
static PyObject *
  location__str__(locationObject *self);
static int
  location__len__(locationObject *self);
static int
  location__cmp__(locationObject *self, locationObject *other);
static long
  location__hash__(locationObject *self);
static locationObject *
  location__add__(locationObject *self, locationObject *other);

/*********************************************************************
 *  Type
 *********************************************************************/

/*********************************************************************
 *  Token
 *********************************************************************/

/*********************************************************************
 *  Module Initialization
 *********************************************************************/

/* Module Initialization */
DL_EXPORT(void) init_ctoken(void);
    
#endif /* ifndef CTOKEN_H */
