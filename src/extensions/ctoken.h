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
 *  Location Context
 *********************************************************************/

/* This struct is used to pair together a unit and a source.  Since
 * we're often dealing with many tokens that all have the same unit
 * and source, we can save 1 word/location by having each location
 * point to a single nltkLocationContext object.
 *
 * We maintain a cache of the most recently used location contexts,
 * which allows us to reuse them when new locations are defined.  Use
 * getLocationContext to get a new location context for a location;
 * and freeLocationContext to free a location context.
 *
 * nltkLocationContext objects are entirely internal to the ctoken
 * implementation; they are not visible from the python interface. */
typedef struct {
    int refcount;
    PyObject *unit;
    PyObject *source;
} nltkLocationContext;

/* Location Constructor & Destructor */
nltkLocationContext *getLocationContext(PyObject *unit, PyObject *source);
int destroy_location_context(nltkLocationContext *lc);

/* Increase the given location context's reference count by one.
 * It is safe to call locationContext_INCREF(NULL). */
#define locationContext_INCREF(lc) (void)(((lc)==NULL) || ((lc)->refcount++))

/* Decrease the given location context's reference count by one.  If
 * the reference count goes to zero, then free it.  It is safe to call
 * locationContext_DECREF(NULL). */
#define locationContext_DECREF(lc) (void)(((lc)==NULL) || \
                                          (--((lc)->refcount)) || \
                                          destroy_location_context(lc))

/* Equality check (for comparing locations) */
int check_location_contexts_eq(nltkLocationContext *c1,
                               nltkLocationContext *c2);

/* A faster version of check_location_contexts_eq, that first checks if
 * c1==c2.  This should actually be the case most of the time, because
 * the location context cache lets us reuse location context
 * objects. */
#define CHECK_LOCATION_CONTEXTS_EQ(c1, c2) \
      (((c1)==(c2)) || check_location_contexts_eq((c1), (c2)))

/* Helper functions */
PyObject *normalizeUnitCase(PyObject *string);

/*********************************************************************
 *  Location
 *********************************************************************/

/* We define two implementations of the Location type.  The first
 * implementation (struct=nltkLocation, type=nltkLocationType) stores
 * both the start and the end index; and the second implementation
 * (struct=nltkLen1Location, type=nltkLen1LocationType) stores only
 * the start index.  This second implementation is used for the common
 * case of locations with a length of exactly 1 (saving 1
 * word/location of memory).
 *
 * The length-1 location implementation is automatically used by
 * Location.__new__, when appropriate.  nltkLen1LocationType is a
 * subclass of nltkLocation, so isinstance(loc, Location) will work
 * correctly. */

/* The object struct for the arbitrary-length location object */
typedef struct {
    PyObject_HEAD                 /* Object head: refcount & type */
    nltkLocationContext *context; /* The unit and the source */
    long int start;               /* The start index */
    long int end;                 /* The end index */
} nltkLocation;

/* The object struct for the length-1 location object */
typedef struct {
    PyObject_HEAD                 /* Object head: refcount & type */
    nltkLocationContext *context; /* The unit and the source */
    long int start;               /* The start index */
} nltkLen1Location;

/* The Location types. */
static PyTypeObject nltkLocationType;
static PyTypeObject nltkLen1LocationType;

/* A macro to test if something's a Location. */
#define is_nltkLocation(v) ((v)->ob_type == &nltkLocationType)
#define is_nltkLen1Location(v) ((v)->ob_type == &nltkLen1LocationType)
#define nltkLocation_END(ob) (is_nltkLen1Location(ob) ? \
                                  ((ob)->start+1) :\
                                  ((ob)->end))

/* Location Constructor & Destructor */
static PyObject *
  nltkLocation__new__(PyTypeObject* type, PyObject *args, PyObject *keywords);
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
    PyObject_VAR_HEAD        /* Object head: refcount & type & size */
    PyObject *properties[1];  /* alternating list of (value/name) */
} nltkType;

/* Use these macros to access nltkType.properties. */
#define nltkType_PROP_NAME(ob, n) ((ob)->properties[(n)*2])
#define nltkType_PROP_VALUE(ob, n) ((ob)->properties[(n)*2+1])

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

/* The array-based implementation of tokens.  N.b. that this is (for
 * the most part) binary-compatible with nltkType; so we can reuse
 * methods. */
typedef struct {
    PyObject_HEAD            /* Object head: refcount & type */
    int num_props;           /* num properties defined by this token */
    PyObject **properties;   /* alternating list of (value/name) */
    PyObject *loc;           /* Location */
} nltkToken;

/* Use these macros to access nltkToken.properties. */
#define nltkToken_PROP_NAME(ob, n) ((ob)->properties[(n)*2])
#define nltkToken_PROP_VALUE(ob, n) ((ob)->properties[(n)*2+1])

/* The Token type. */
static PyTypeObject nltkTokenType;

/*********************************************************************
 *  Module Initialization
 *********************************************************************/

/* Module Initialization */
DL_EXPORT(void) init_ctoken(void);
    
#endif /* ifndef CTOKEN_H */
