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

/* How large is the cache for property name lists?  Larger caches
 * increase the chance for shairing property name lists, but make
 * cache lookup slower.  */
#define PNL_CACHE_SIZE 20

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
    PyObject_HEAD         /* Object head: refcount & type */
    PyObject *context;    /* A tuple containing the unit and the source */
    long int start;       /* The start index */
    long int end;         /* The end index */
} nltkLocation;

/* The object struct for the length-1 location object */
typedef struct {
    PyObject_HEAD                 /* Object head: refcount & type */
    PyObject *context; /* The unit and the source */
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

/* Macros to get a location's attributes (work for all implementations) */
#define nltkLocation_START(op) ((op)->start)
#define nltkLocation_END(op) (nltkLen1Location_Check(op) ? \
                                  ((op)->start+1) :\
                                  ((op)->end))
#define nltkLocation_UNIT(op) GET_LC_UNIT(op->context)
#define nltkLocation_SOURCE(op) GET_LC_SOURCE(op->context)

/*********************************************************************
 *  Type
 *********************************************************************/

/* The struct that is used to encode Type instances. */
typedef struct {
    PyObject_VAR_HEAD         /* Object head: refcount & type & size */
    PyObject *prop_names;     /* List of property names */
    PyObject *prop_vals[1];   /* Array of property values */
} nltkType;

/* Use these macros to access nltkType.properties. */
#define nltkType_PROP_NAME(ob, n) \
    PyList_GET_ITEM(((nltkType*)(ob))->prop_names, (n))
#define nltkType_PROP_VALUE(ob, n) (((nltkType*)ob)->prop_vals[n])

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
    PyObject_VAR_HEAD        /* Object head: refcount & type & size */
    PyObject *context;       /* A tuple containing the unit and the source */
    long int start;          /* The start index */
    long int end;            /* The end index */
    PyObject *prop_names;    /* List of property names */
    PyObject *prop_vals[1];  /* Array of property values */
} nltkInlinedToken;

/*********************************************************************
 *  DOCSTRINGS & ERROR MESSAGES
 *********************************************************************/

#define MODULE_DOC "The token module (c implementation)."

/* =========================== Location =========================== */
#define LOCATION_DOC "A span over indices in text."
#define LOCATION_START_DOC "The index at which this Token begins."
#define LOCATION_END_DOC "The index at which this Token ends."
#define LOCATION_UNIT_DOC "The index unit used by this location."
#define LOCATION_SOURCE_DOC "An identifier naming the text over which \
this location is defined."
#define LOCATION_LENGTH_DOC "Location.length(self) -> int\n\
Return the length of this Location."
#define LOCATION_START_LOC_DOC "Location.start_loc(self) -> Location\n\
Return a zero-length location at the start offset of this location."
#define LOCATION_END_LOC_DOC "Location.end_loc(self) -> Location\n\
Return a zero-length location at the end offset of this location."
#define LOCATION_UNION_DOC "Location.union(self, other) -> Location\n\
If self and other are contiguous, then return a new location \n\
spanning both self and other; otherwise, raise an exception."
#define LOCATION_PREC_DOC "Location.prec(self, other) -> boolean\n\
@return: True if self occurs entirely before other.  In particular,\n\
return true iff self.end <= other.start, and self!=other."
#define LOCATION_SUCC_DOC "Location.succ(self, other) -> boolean\n\
@return: True if self occurs entirely after other.  In particular,\n\
return true iff other.end <= self.start, and self!=other."
#define LOCATION_OVERLAPS_DOC "Location.overlaps(self, other) -> boolean\n\
@return: True if self overlaps other.  In particular, return true\n\
iff self.start <= other.start < self.end; or \n\
other.start <= self.start < other.end."
#define LOCATION_SELECT_DOC "Location.select(self, list) -> list\n\
@return The sublist specified by this location.  I.e., return \n\
list[self.start:self.end]"

#define LOC_ERROR_001 "A location's start index must be less than \
or equal to its end index."
#define LOC_ERROR_002 "Locations can only be added to Locations"
#define LOC_ERROR_003 "Locations have incompatible units"
#define LOC_ERROR_004 "Locations have incompatible sources"
#define LOC_ERROR_005 "Locations are not contiguous"

/* ============================= Type ============================== */
#define TYPE_DOC "A unit of language, such as a word or sentence."
#define TYPE_ERROR_001 "The Type constructor only accepts keyword arguments"
#define TYPE_ERROR_002 "Property is not defined for this Type"
#define TYPE_ERROR_003 "Type.extend only accepts keyword arguments"
#define TYPE_ERROR_004 "Type does not define selected property"
#define TYPE_ERROR_005 "Types are immutable objects"
#define TYPE_ERROR_006 "Type.select requires string arguments"

/* ============================ Token ============================== */
#define TOKEN_DOC "An occurance of a type"
#define TOKEN_ERROR_001 "Bad Token: Token.__init__ was never called."
#define TOKEN_ERROR_002 "Tokens are immutable objects"


#endif /* ifndef CTOKEN_H */
