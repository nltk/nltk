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
typedef struct {
    PyObject_HEAD      /* Object head: refcount & type */
    long int start;    /* The start index */
    long int end;      /* The end index */
    PyObject *unit;    /* The unit */
    PyObject *source;  /* The source */
} nltkLocation;

/* The Location type. */
static PyTypeObject nltkLocationType;

/* A macro to test if something's a Location. */
#define is_nltkLocation(v) ((v)->ob_type == &nltkLocationType)

/* Location Constructor & Destructor */
static PyObject *
  nltkLocation__new__(PyTypeObject* type, PyObject *args, PyObject *keywords);
static int
  nltkLocation__init__(nltkLocation* self, PyObject *args, PyObject *keywords);
static void
  nltkLocation__del__(nltkLocation* self);

/* Location Methods */
static PyObject *
  nltkLocation_length(nltkLocation* self, PyObject *args);
static nltkLocation *
  nltkLocation_start_loc(nltkLocation* self, PyObject *args);
static nltkLocation *
  nltkLocation_end_loc(nltkLocation* self, PyObject *args);
static nltkLocation *
  nltkLocation_union(nltkLocation* self, PyObject *args);
static PyObject *
  nltkLocation_prec(nltkLocation* self, PyObject *args);
static PyObject *
  nltkLocation_succ(nltkLocation* self, PyObject *args);
static PyObject *
  nltkLocation_overlaps(nltkLocation* self, PyObject *args);
static PyObject *
  nltkLocation_select(nltkLocation* self, PyObject *args);

/* Location operators */
static PyObject *
  nltkLocation__repr__(nltkLocation *self);
static PyObject *
  nltkLocation__str__(nltkLocation *self);
static int
  nltkLocation__len__(nltkLocation *self);
static int
  nltkLocation__cmp__(nltkLocation *self, nltkLocation *other);
static long
  nltkLocation__hash__(nltkLocation *self);
static nltkLocation *
  nltkLocation__add__(nltkLocation *self, nltkLocation *other);

/*********************************************************************
 *  Type
 *********************************************************************/

/* The struct that is used to encode Type instances. */
typedef struct {
    PyObject_HEAD          /* Object head: refcount & type */
    int num_props;         /* num properties defined by this token */
    PyObject **prop_names;  /* names of properties */
    PyObject **prop_values; /* values of properties */
} nltkType;

/* The Type type. */
static PyTypeObject nltkTypeType;

/* A macro to test if something's a Type. */
#define is_nltkType(v) PyType_IsSubtype(&nltkTypeType, (v)->ob_type)

/* Type Constructor & Destructor */
static PyObject*
  nltkType__new__(PyTypeObject* type, PyObject *args, PyObject *keywords);
static int
  nltkType__init__(nltkType *self, PyObject *args, PyObject *keywords);
static void
  nltkType__del__(nltkType *self);

/* Type Methods */
static PyObject*
  nltkType_get(nltkType *self, PyObject *args);
static PyObject*
  nltkType_has(nltkType *self, PyObject *args);
static PyObject*
  nltkType_properties(nltkType *self, PyObject *args);
static nltkType*
  nltkType_extend(nltkType *self, PyObject *args, PyObject *keywords);
static nltkType*
  nltkType_select(nltkType *self, PyObject *args);

/* Type Operators */
static PyObject*
  nltkType__repr__(nltkType *self);
static PyObject*
  nltkType__getattro__(nltkType *self, PyObject *name);
static int
  nltkType__cmp__(nltkType *self, nltkType *other);
static long
  nltkType__hash__(nltkType *self);


/*********************************************************************
 *  Token
 *********************************************************************/
/* Several implementations:
 *    - nltkAbstractToken -- superclass for token implementations.
 *    - nltkArrayToken -- array-based token.
 *    - nltkLen1ArrayToken -- array-based token with len=1. */

typedef struct {
    PyObject_HEAD
} nltkAbstractToken;

/* The array-based implementation of tokens */
typedef struct {
    PyObject_HEAD          /* Object head: refcount & type */
    int num_properties;    /* # properties defined by this token */
    char **names;          /* names of properties */
    PyObject *values;      /* values of properties */
    int start;             /* location's start index */
    int end;               /* location's end index */
    PyObject *unit;        /* location's unit */
    PyObject *source;      /* location's source */
    PyTypeObject *real_type;/* Hmmm */
} nltkArrayToken;

/* The Location types. */
static PyTypeObject nltkAbstractTokenType;
static PyTypeObject nltkArrayTokenType;

/*********************************************************************
 *  Module Initialization
 *********************************************************************/

/* Module Initialization */
DL_EXPORT(void) init_ctoken(void);
    
#endif /* ifndef CTOKEN_H */
