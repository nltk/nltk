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

//
// TO DO:
//   - define Type.__cmp__
//   - override __setattr__ in Type,Token
//   - try maintaining properties in sorted order? (by id)

#ifndef CTOKEN_H
#define CTOKEN_H

/*********************************************************************
 *  Configuration Parameters
 *********************************************************************/

/* How large is the cache for location contexts?  Larger caches
 * increase the chance for sharing (unit,source) pairs, but make cache
 * lookup slower.  */
#define LC_CACHE_SIZE 5

/*********************************************************************
 *  Location Context
 *********************************************************************
 * This struct is used to pair together a unit and a source.  Since
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
 *********************************************************************
 * We define two implementations of the Location type.  The first
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

/* Macros to test if something's a Location.  Note that we don't allow
 * new subtypes of nltkLocation to be defined, so nltkLocation_Check
 * can check directly. */
#define nltkLocation_CheckExact(op) ((op)->ob_type == &nltkLocationType)
#define nltkLen1Location_Check(op) ((op)->ob_type == &nltkLen1LocationType)
#define nltkLocation_Check(op) (nltkLocation_CheckExact(op) || \
                                nltkLen1Location_Check(op))

/* Get the end index of a location (works for both implementations) */
#define nltkLocation_END(op) (nltkLen1Location_Check(op) ? \
                                  ((op)->start+1) :\
                                  ((op)->end))

/*********************************************************************
 *  Type
 *********************************************************************/

/* The struct that is used to encode Type instances. */
typedef struct {
    PyObject_VAR_HEAD         /* Object head: refcount & type & size */
    PyObject *properties[1];  /* alternating list of (value/name) */
} nltkType;

/* Use these macros to access nltkType.properties. */
#define nltkType_PROP_NAME(ob, n) ((ob)->properties[(n)*2])
#define nltkType_PROP_VALUE(ob, n) ((ob)->properties[(n)*2+1])

/* The Type type. */
static PyTypeObject nltkTypeType;

/* A macro to test if something's a Type. */
#define nltkType_Check(v) PyType_IsSubtype(&nltkTypeType, (v)->ob_type)

/*********************************************************************
 *  Token
 *********************************************************************/

/* The struct that is used to encode Token instances. */
typedef struct {
    PyObject_HEAD            /* Object head: refcount & type */
    nltkType *type;          /* The token's type */
    PyObject *loc;           /* The token's location */
} nltkToken;

/* The Token type. */
static PyTypeObject nltkTokenType;

/* A macro to test if something's a Token. */
#define nltkToken_Check(v) PyType_IsSubtype(&nltkTokenType, (v)->ob_type)

/*********************************************************************
 *  InlinedToken
 *********************************************************************
 * This specialized implementation of Token has less space overhead
 * than nltkToken.  However, this smaller size comes at a cost:
 * whenver the token's type or location is accessed, we must construct
 * a new type or location object.
 */

/* The struct that is used to encode InlinedToken instances. */
typedef struct {
    PyObject_VAR_HEAD         /* Object head: refcount & type & size */
    
    PyObject *properties[1];  /* alternating list of (value/name) */

} nltkInlinedToken;


#endif /* ifndef CTOKEN_H */
