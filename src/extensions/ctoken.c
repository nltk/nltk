/* Natural Language Toolkit: C Implementation of nltk.token
 *
 * Copyright (C) 2003 University of Pennsylvania
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://nltk.sourceforge.net>
 * For license information, see LICENSE.TXT
 *
 * $Id$
 *
 */

#include <Python.h>
#include <structmember.h>
#include "ctoken.h"

/* Table of contents:
 *     1. Docstrings & Error Messages
 *     2. Forward Declarations
 *     3. Location Context
 *     4. Location
 *         4.1. Helper Functions
 *         4.2. Constructor & Destructor
 *         4.3. Methods
 *         4.4. Operators
 *         4.5. Type Definition
 *     5. Type
 *         5.1. Helper Functions
 *         5.2. Constructor & Destructor
 *         5.3. Methods
 *         5.4. Operators
 *         5.5. Type Definition
 *     6. Token
 *         6.1. Helper Functions
 *         6.2. Constructor & Destructor
 *         6.3. Methods
 *         6.4. Operators
 *         6.5. Type Definition
 *     7. Module Definition
 *
 * Property names are interned, for speed.
 * Units are interned, too.
 */

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

/* ============================ Token ============================== */
#define TOKEN_DOC "An occurance of a type"
#define TOKEN_ERROR_001 "Bad Token: Token.__init__ was never called."
#define TOKEN_ERROR_002 "Tokens are immutable objects"

/*********************************************************************
 *  FORWARD DECLARATIONS
 *********************************************************************/

static nltkLocation *
nltkLocation__add__(nltkLocation *self, nltkLocation *other);

/*********************************************************************
 *  LOCATION CONTEXT
 *********************************************************************/

/* The cache for location contexts */
static nltkLocationContext *lc_cache[LC_CACHE_SIZE];

/* Return a LocationContext structure that points at the given unit
 * and source.  A small cache allows LocationContexts for common
 * (unit,source) pairs to be reused.
 *
 * The reference count for the unit & source will be incremented by
 * one when a new LocationContext is constructed to point at them.
 *
 * The given unit is case-normalized (to lower case).  Note that this
 * means that the unit pointed to by the location context might not be
 * the same unit that was provided. */
nltkLocationContext *getLocationContext(PyObject *unit, PyObject *source) {
    static int next_cell = -1;
    int result, i;
    
    /* Cache initialization */
    if (next_cell < 0) {
        for (i=0; i<LC_CACHE_SIZE; i++) {
            lc_cache[i] = NULL;
        }
        next_cell = 0;
    }

    /* Downcase the unit. */
    unit = normalizeUnitCase(unit);
    
    /* Intern the unit, so we can do faster compares. */
    if (unit != NULL && unit != Py_None)
        PyString_InternInPlace(&unit);

    /* Search for the given unit/source pair in the cache. 
     * Check cache entries in most-recently-cached order. */
    for (i = (next_cell+LC_CACHE_SIZE-1)%LC_CACHE_SIZE;
                 i != next_cell;
                 i = (i+LC_CACHE_SIZE-1)%LC_CACHE_SIZE)
        if (lc_cache[i] != NULL) {
            if (unit == lc_cache[i]->unit) {
                if (PyObject_Cmp(source, lc_cache[i]->source, &result) == -1)
                    return NULL;
                else if (result == 0) {
                    /* We found a match!  Note that we must decrease
                     * the reference count of the unit string, since
                     * normalizing its case produced a new reference. */
                    Py_DECREF(unit);
                    lc_cache[i]->refcount += 1;
                    return lc_cache[i];
                }
            }
        }

    /* We didn't find a match; so pick a cell to replace, and build a
     * new location context there.  This should be fairly infrequent,
     * so it would be possible to put a smarter algorithm here (e.g.,
     * one that sorts the location contexts by refcount, starting at
     * index 1, and puts the new lc at index 0). */

    /* Reuse empty cells when possible. */
    for (i=0; i<LC_CACHE_SIZE; i++)
        if (lc_cache[i] == NULL) {
            next_cell = i;
            break;
        }

    /* Build the new location context.  We must increment the ref
     * count for source, but not for unit (normalizeUnitCase already
     * generated a new reference). */
    i = next_cell;
    lc_cache[i] = PyMem_Malloc(sizeof(nltkLocationContext));
    lc_cache[i]->refcount = 1;
    lc_cache[i]->unit = unit;
    lc_cache[i]->source = source;
    Py_INCREF(source);

    /* Update the next_cell pointer. */
    next_cell = (next_cell+1)%LC_CACHE_SIZE;

    /* Return the newly cached location context */
    return lc_cache[i];
}

/* If the given string is in lower case, then return it; otherwise,
 * construct a new string that is the downcased version of s.  The
 * returned string is a new reference (not borrowed). */
PyObject *normalizeUnitCase(PyObject *string)
{
    int size = PyString_GET_SIZE(string);
    char *s, *e, *buffer, *s2;
    int normalized;
    
    /* First, check if it's already case-normalized.  If it is, then
       we don't want to create a new string object. */
    s = PyString_AS_STRING(string);
    e = s+size;
    normalized = 1;
    for (; s<e; s++)
        if (isupper(*s)) {
            normalized = 0;
            break;
        }

    /* If it's already normalized, then just return it. */
    if (normalized) {
        Py_INCREF(string);
        return string;
    }
    
    /* Otherwise, downcase it. */
    buffer = PyMem_Malloc((size+1)*sizeof(char));
    if (buffer == NULL) return NULL;
    s2 = buffer;
    buffer[size] = 0;
    s = PyString_AS_STRING(string);
    for (; s<e; s++,s2++)
        (*s2) = tolower(*s);
    string = PyString_FromStringAndSize(buffer, size);
    PyMem_Free(buffer);
    return string;
}

/* Return true iff the units & source of the given location context
 * are equal.  Otherwise, set an appropriate exception and return
 * 0. */
int check_location_contexts_eq(nltkLocationContext *c1,
                            nltkLocationContext *c2) {
    int result = 0;
    
    /* Check that the units match */
    if (PyObject_Cmp(c1->unit, c2->unit, &result) == -1)
        return 0;
    if (result != 0) {
        PyErr_SetString(PyExc_ValueError, LOC_ERROR_003);
        return 0;
    }

    /* Check that the sources match */
    if (PyObject_Cmp(c1->source, c2->source, &result) == -1)
        return 0;
    if (result != 0) {
        PyErr_SetString(PyExc_ValueError, LOC_ERROR_004);
        return 0;
    }

    return 1;
}

/* Deallocate the space associated with the given location context. */
int destroy_location_context(nltkLocationContext *lc) {
    int i;
    
    /* If this lc is in the cache, then remove it. */
    for (i=0; i<LC_CACHE_SIZE; i++)
        if (lc_cache[i] == lc)
            lc_cache[i] = NULL;
    
    /* Free any memory associated with this location context. */
    Py_XDECREF(lc->unit);
    Py_XDECREF(lc->source);
    PyMem_Free(lc);
    return 1;
}

/*********************************************************************
 *  LOCATION
 *********************************************************************/

/* =================== Location Helper Functions =================== */

/* Return a copy of the given location */
nltkLocation *nltkLocation_copy(nltkLocation* original)
{
    nltkLocation *loc;
    
    /* Create the return value object. */
    loc = (nltkLocation*)nltkLocationType.tp_alloc(&nltkLocationType, 0);
    if (loc == NULL) return NULL;

    /* Fill in start & end values. */
    loc->start = original->start;
    loc->end = nltkLocation_END(original);

    /* Fill in unit & source values. */
    locationContext_INCREF(original->context);
    loc->context = original->context;

    return loc;
}

/* ================== Constructor and Destructor =================== */

/* Location.__new__(type) */
/* Create a new Location object, and initialize its members.
 * nltkLocation__new__ will actually return one of two objects,
 * depending on the parameters given: if end is unspecified, or is
 * 1+start, then it will return an nltkLen1Location; otherwise, it
 * will return an nltkLocation.
 *
 * The location attributes are initialized here, to avoid parsing the
 * arguments twice. */
static PyObject*
nltkLocation__new__(PyTypeObject* type, PyObject *args, PyObject *keywords)
{
    nltkLocation *self;
    PyObject *start = NULL;
    PyObject *end = NULL;
    PyObject *unit = NULL;
    PyObject *source = NULL;
    static char *kwlist[] = {"start", "end", "unit", "source", NULL};

    /* Parse the arguments. */
    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O!|O!SO:Location",
                                     kwlist,
                                     &PyInt_Type, &start,
                                     &PyInt_Type, &end,
                                     &unit, &source))
        return NULL;

    /* If end is unspecified, or is start+1, then use a
     * Len1Location. */
    if (end==NULL || ((PyInt_AS_LONG(end)-PyInt_AS_LONG(start))==1))
        type = &nltkLen1LocationType;
    else
        type = &nltkLocationType;

    /* Allocate space for the new object. */
    self = (nltkLocation*)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;

    /* Set the start index. */
    self->start = PyInt_AS_LONG(start);
    
    /* Set the end index, if appropriate. */
    if (type != &nltkLen1LocationType) {
        self->end = PyInt_AS_LONG(end);

        /* Check that end<start */
        if (self->end < self->start) {
            PyErr_SetString(PyExc_ValueError, LOC_ERROR_001);
            return NULL;
        }
    }

    /* Set the unit & source.  Both default to NULL. */
    if (unit == NULL)   { Py_INCREF(Py_None); unit = Py_None;  }
    if (source == NULL) { Py_INCREF(Py_None); source = Py_None; }
    self->context = getLocationContext(unit, source);

    /* Return the new object. */
    return (PyObject *)self;
}
    
/* Location.__del__(self) */
/* Deallocate all space associated with this Location. */
static void
nltkLocation__del__(nltkLocation* self)
{
    locationContext_DECREF(self->context);
    self->ob_type->tp_free((PyObject*)self);
}

/* ======================= Location Methods ======================== */

/* Location.length(self) */
/* Return the length of this location (end-start). */
static PyObject *nltkLocation_length(nltkLocation* self, PyObject *args)
{
    return PyInt_FromLong(nltkLocation_END(self) - self->start);
}

/* Location.start_loc(self) */
/* Return a zero-length location at the start offset */
static nltkLocation *nltkLocation_start_loc(nltkLocation* self, PyObject *args)
{
    /* If we're already zero-length, just return ourself. */
    if (nltkLocation_CheckExact(self) && (self->start == self->end)) {
        Py_INCREF(self);
        return self;
    } else {
        nltkLocation *loc = nltkLocation_copy(self);
        if (loc == NULL) return NULL;
        loc->end = self->start;
        return loc;
    }
}

/* Location.end_loc(self) */
/* Return a zero-length location at the end offset */
static nltkLocation *nltkLocation_end_loc(nltkLocation* self, PyObject *args)
{
    /* If we're already zero-length, just return ourself. */
    if (nltkLocation_CheckExact(self) && (self->start == self->end)) {
        Py_INCREF(self);
        return self;
    } else {
        nltkLocation *loc = nltkLocation_copy(self);
        if (loc == NULL) return NULL;
        loc->start = nltkLocation_END(self);
        return loc;
    }
}

/* Location.union(self, other) */
/* If self and other are contiguous, then return a new location
 * spanning both self and other; otherwise, raise an exception. */
static nltkLocation *nltkLocation_union(nltkLocation* self, PyObject *args)
{
    nltkLocation *other = NULL;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.union", &nltkLocationType, &other))
        return NULL;
    return nltkLocation__add__(self, other);
}

/* Location.prec(self, other) */
/* Return true if self ends before other begins. */
static PyObject *nltkLocation_prec(nltkLocation* self, PyObject *args)
{
    nltkLocation *other = NULL;
    long int s1, s2, e1, e2;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.prec", &nltkLocationType, &other))
        return NULL;
    if (!CHECK_LOCATION_CONTEXTS_EQ(self->context, other->context))
        return NULL;

    s1 = self->start;  e1 = nltkLocation_END(self);
    s2 = other->start; e2 = nltkLocation_END(other);
    return PyInt_FromLong(e2 <= s1 && s2 < e1);
}

/* Location.succ(self, other) */
/* Return true if other ends before self begins. */
static PyObject *nltkLocation_succ(nltkLocation* self, PyObject *args)
{
    nltkLocation *other = NULL;
    long int s1, s2, e1, e2;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.succ", &nltkLocationType, &other))
        return NULL;
    if (!CHECK_LOCATION_CONTEXTS_EQ(self->context, other->context))
        return NULL;

    s1 = self->start;  e1 = nltkLocation_END(self);
    s2 = other->start; e2 = nltkLocation_END(other);
    return PyInt_FromLong(e2 <= s1 && s2 < e1);
}

/* Location.overlaps(self, other) */
/* Return true if self overlaps other. */
static PyObject *nltkLocation_overlaps(nltkLocation* self, PyObject *args)
{
    nltkLocation *other = NULL;
    long int s1, s2, e1, e2;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.overlaps",
                          &nltkLocationType, &other))
        return NULL;
    if (!CHECK_LOCATION_CONTEXTS_EQ(self->context, other->context))
        return NULL;

    s1 = self->start;  e1 = nltkLocation_END(self);
    s2 = other->start; e2 = nltkLocation_END(other);
    return PyInt_FromLong(((s1 <= s2) && (s2 < e1)) ||
                          ((s2 <= s1) && (s1 < e2)) ||
                          ((s1 == s2) && (s2 == e1) && (e1 == e2)));
}

/* Location.select(self, list) */
/* Return list[self.start:self.end] */
static PyObject *nltkLocation_select(nltkLocation* self, PyObject *args)
{
    PyObject *list = NULL;
    
    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.select", &PyList_Type, &list))
        return NULL;

    return PyList_GetSlice(list, self->start, nltkLocation_END(self));
}

/* ====================== Location Operators ======================= */

/* repr(self) */
static PyObject *nltkLocation__repr__(nltkLocation *self)
{
    if (nltkLocation_END(self) == self->start+1) {
        if (self->context == NULL || self->context->unit == Py_None)
            return PyString_FromFormat("@[%ld]", self->start);
        else
            return PyString_FromFormat("@[%ld%s]", self->start,
                                   PyString_AS_STRING(self->context->unit));
    }
    else if (self->context == NULL || self->context->unit == Py_None)
        return PyString_FromFormat("@[%ld:%ld]", self->start,
                                   nltkLocation_END(self));
    else
        return PyString_FromFormat("@[%ld%s:%ld%s]", self->start,
                                   PyString_AS_STRING(self->context->unit),
                                   nltkLocation_END(self),
                                   PyString_AS_STRING(self->context->unit));
}

/* str(self) */
static PyObject *nltkLocation__str__(nltkLocation *self)
{
    if (self->context == NULL || self->context->source == Py_None)
        return nltkLocation__repr__(self);
    else if (nltkLocation_Check(self->context->source))
        return PyString_FromFormat("%s%s",
                   PyString_AS_STRING(nltkLocation__repr__(self)),
                   PyString_AS_STRING(PyObject_Str(self->context->source)));
    else
        return PyString_FromFormat("%s@%s",
                   PyString_AS_STRING(nltkLocation__repr__(self)),
                   PyString_AS_STRING(PyObject_Repr(self->context->source)));
}

/* len(self) */
static int nltkLocation__len__(nltkLocation *self)
{
    return (nltkLocation_END(self) - self->start);
}

/* cmp(self, other) */
static int nltkLocation__cmp__(nltkLocation *self, nltkLocation *other)
{
    /* Check type(other) */
    if (!nltkLocation_Check(other))
        return -1;

    /* Check for unit/source mismatches */
    if (!CHECK_LOCATION_CONTEXTS_EQ(self->context, other->context)) {
        PyErr_Clear(); /* don't raise an exception. */
        return -1;
    }

    /* Compare the start & end indices. */
    if (self->start < other->start)
        return -1;
    else if (self->start > other->start)
        return 1;
    else if (nltkLocation_END(self) < nltkLocation_END(other))
        return -1;
    else if (nltkLocation_END(self) > nltkLocation_END(other))
        return 1;
    else
        return 0;
}

/* hash(self) */
static long nltkLocation__hash__(nltkLocation *self)
{
    /* It's unusual for 2 different locations to share a start offset
       (for a given unit/source); so just hash off the start. */
    return self->start;
}

/* self+other */
/* If self and other are contiguous, then return a new location
 * spanning both self and other; otherwise, raise an exception. */
static nltkLocation *nltkLocation__add__(nltkLocation *self,
                                         nltkLocation *other) {
    /* Check type(other) */
    if (!nltkLocation_Check(other)) {
        PyErr_SetString(PyExc_TypeError, LOC_ERROR_002);
        return NULL;
    }

    if (!CHECK_LOCATION_CONTEXTS_EQ(self->context, other->context))
        return NULL;
    
    if (nltkLocation_END(self) == other->start) {
        nltkLocation *loc = nltkLocation_copy(self);
        loc->end = nltkLocation_END(other);
        return loc;
    }
    else if (nltkLocation_END(other) == self->start) {
        nltkLocation *loc = nltkLocation_copy(other);
        loc->end = nltkLocation_END(self);
        return loc;
    }
    else {
        PyErr_SetString(PyExc_ValueError, LOC_ERROR_005);
        return NULL;
    }
}

static PyObject *nltkLocation__getattro__(nltkLocation *self,
                                          PyObject *name) {
    if (strcmp(PyString_AS_STRING(name), "start") == 0)
        return PyInt_FromLong(self->start);
    if (strcmp(PyString_AS_STRING(name), "end") == 0)
        return PyInt_FromLong(nltkLocation_END(self));
    if (strcmp(PyString_AS_STRING(name), "unit") == 0) {
        if (self->context == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            Py_INCREF(self->context->unit);
            return self->context->unit;
        }
    }
    if (strcmp(PyString_AS_STRING(name), "source") == 0) {
        if (self->context == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            Py_INCREF(self->context->source);
            return self->context->source;
        }
    }

    /* It wasn't a special attribute; Use the generic version of
     * getattr */
    return PyObject_GenericGetAttr((PyObject *)self, name);
}

/* =================== Location Type Definition ==================== */

/* Location attributes.  These are used by PyObject_GenericGetAttr to
 * generate attributes.  However, note that "unit" and "source" are
 * not directly stored in the object; we handle them manually in
 * __getattro__.  So we give a dummy value (-1) for the offset of the
 * value in the object struct.
 */
struct PyMemberDef nltkLocation_members[] = {
    {"start", T_INT, offsetof(nltkLocation, start), RO,
     LOCATION_START_DOC},
    {"end", T_INT, offsetof(nltkLocation, end), RO,
     LOCATION_END_DOC},
    {"unit", T_OBJECT_EX, /*dummy value:*/-1, RO,
     LOCATION_UNIT_DOC},
    {"source", T_OBJECT_EX, /*dummy value:*/-1, RO,
     LOCATION_SOURCE_DOC},
    {NULL, 0, 0, 0, NULL} /* Sentinel */
};

/* Location methods */
static PyMethodDef nltkLocation_methods[] = {
    {"length", (PyCFunction)nltkLocation_length, METH_NOARGS,
     LOCATION_LENGTH_DOC},
    {"start_loc", (PyCFunction)nltkLocation_start_loc, METH_NOARGS,
     LOCATION_START_LOC_DOC},
    {"end_loc", (PyCFunction)nltkLocation_end_loc, METH_NOARGS,
     LOCATION_END_LOC_DOC},
    {"union", (PyCFunction)nltkLocation_union, METH_VARARGS,
     LOCATION_UNION_DOC},
    {"prec", (PyCFunction)nltkLocation_prec, METH_VARARGS,
     LOCATION_PREC_DOC},
    {"succ", (PyCFunction)nltkLocation_succ, METH_VARARGS,
     LOCATION_SUCC_DOC},
    {"overlaps", (PyCFunction)nltkLocation_overlaps, METH_VARARGS,
     LOCATION_OVERLAPS_DOC},
    {"select", (PyCFunction)nltkLocation_select, METH_VARARGS,
     LOCATION_SELECT_DOC},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

/* Location operators. */
/* Use the tp_as_sequence protocol to implement len, concat, etc. */
static PySequenceMethods nltkLocation_as_sequence = {
    (inquiry)nltkLocation__len__,      /* sq_length */
    (binaryfunc)nltkLocation__add__,   /* sq_concat */
};

static PyTypeObject nltkLocationType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /* ob_size */
    "Location",                                /* tp_name */
    sizeof(nltkLocation),                      /* tp_basicsize */
    0,                                         /* tp_itemsize */
    (destructor)nltkLocation__del__,           /* tp_dealloc */
    0,                                         /* tp_print */
    0,                                         /* tp_getattr */
    0,                                         /* tp_setattr */
    (cmpfunc)nltkLocation__cmp__,              /* tp_compare */
    (reprfunc)nltkLocation__repr__,            /* tp_repr */
    0,                                         /* tp_as_number */
    &nltkLocation_as_sequence,                 /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    (hashfunc)nltkLocation__hash__,            /* tp_hash  */
    0,                                         /* tp_call */
    (reprfunc)nltkLocation__str__,             /* tp_str */
    (getattrofunc)nltkLocation__getattro__,    /* tp_getattro */
    0,                                         /* tp_setattro */
    0,                                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                        /* tp_flags */
    LOCATION_DOC,                              /* tp_doc */
    0,		                               /* tp_traverse */
    0,		                               /* tp_clear */
    0,		                               /* tp_richcompare */
    0,		                               /* tp_weaklistoffset */
    0,		                               /* tp_iter */
    0,		                               /* tp_iternext */
    nltkLocation_methods,                      /* tp_methods */
    nltkLocation_members,                      /* tp_members */
    0,                                         /* tp_getset */
    0,                                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    0,                                         /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)nltkLocation__new__,              /* tp_new */
};

/* This is identical to nltkLocationType, except for tp_basicsize and
 * tp_base. */
static PyTypeObject nltkLen1LocationType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /* ob_size */
    "Location",                                /* tp_name */
    sizeof(nltkLen1Location),                  /* tp_basicsize */
    0,                                         /* tp_itemsize */
    (destructor)nltkLocation__del__,           /* tp_dealloc */
    0,                                         /* tp_print */
    0,                                         /* tp_getattr */
    0,                                         /* tp_setattr */
    (cmpfunc)nltkLocation__cmp__,              /* tp_compare */
    (reprfunc)nltkLocation__repr__,            /* tp_repr */
    0,                                         /* tp_as_number */
    &nltkLocation_as_sequence,                 /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    (hashfunc)nltkLocation__hash__,            /* tp_hash  */
    0,                                         /* tp_call */
    (reprfunc)nltkLocation__str__,             /* tp_str */
    (getattrofunc)nltkLocation__getattro__,    /* tp_getattro */
    0,                                         /* tp_setattro */
    0,                                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                        /* tp_flags */
    LOCATION_DOC,                              /* tp_doc */
    0,		                               /* tp_traverse */
    0,		                               /* tp_clear */
    0,		                               /* tp_richcompare */
    0,		                               /* tp_weaklistoffset */
    0,		                               /* tp_iter */
    0,		                               /* tp_iternext */
    nltkLocation_methods,                      /* tp_methods */
    nltkLocation_members,                      /* tp_members */
    0,                                         /* tp_getset */
    &nltkLocationType,                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    0,                                         /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)nltkLocation__new__,              /* tp_new */
};

/*********************************************************************
 *  PROPERTY NAME LISTS
 *********************************************************************/

#define PNL_CACHE_SIZE 20
static PyListObject *pnl_cache[PNL_CACHE_SIZE];

static PyListObject *getPropertyNameListFromDict(PyObject *properties) {
    static int next_cell = -1;
    int i, j;
    int size = PyDict_Size(properties);
    
    /* Cache initialization */
    if (next_cell < 0) {
        for (i=0; i<PNL_CACHE_SIZE; i++) {
            pnl_cache[i] = NULL;
        }
        next_cell = 0;
    }

    /* Search for the given set of properties.
     * Check cache entries in MRU order. */
    for (i = (next_cell+PNL_CACHE_SIZE-1)%PNL_CACHE_SIZE;
                 i != next_cell;
                 i = (i+PNL_CACHE_SIZE-1)%PNL_CACHE_SIZE)
        if (pnl_cache[i] != NULL)
            if (PyList_GET_SIZE(pnl_cache[i]) == size) {
                for (j=0; j<size; j++) {
                    PyObject *pname = PyList_GET_ITEM(pnl_cache[i], j);
                    if (PyDict_GetItem(properties, pname) == NULL)
                        j = size+10; /* Mismatch. */
                }
                if (j == size) {
                    /* Match. */
                    Py_INCREF(pnl_cache[i]);
                    return pnl_cache[i];
                }
            }

    /* It wasn't present in the cache; evict something and add it to
     * the cache. */
    i = next_cell;
    Py_XDECREF(pnl_cache[i]);
    pnl_cache[i] = PyDict_Keys(properties);

    /* Update the next_cell pointer. */
    next_cell = (next_cell+1)%PNL_CACHE_SIZE;

    /* Return the new list. */
    return pnl_cache[i];
}

/*********************************************************************
 *  TYPE
 *********************************************************************/
/* Check immutability?? */

/* ===================== Type Helper Functions ===================== */

#undef DEBUG_SORT_PROPERTY_ARRAY
/* Sort the given array of properties, using the pointers for the
 * property names as keys.  This assumes that the property names have
 * all been intern'ed, so the pointers will uniquely identify property
 * names.
 *
 * Since we expect the property list to be fairly small (5-10
 * elements), I use a fairly simple sorting algorithm (insertion
 * sort).  This algorithm is good for inserting new items to a
 * sorted list, too (e.g., for nltkType_extend).
 */
void sortPropertyArray(PyObject *properties[], int size) {
    int i;             /* The index of the property we're inserting. */
    int j;             /* The index we're checking for insertion. */
    PyObject *cur_key; /* The property that we're currently inserting */
    PyObject *cur_val; /*     (cur_key = name; cur_val = value). */

    /* At the start of each iteration, properties [0:i] are sorted. */
    for (i=1; i<size; i++) {

        /* Short-circuit for already-sorted list items */
        if (properties[i*2-2] <= properties[i*2]) continue;
        
        /* Store property[i] as cur_key and cur_val. */
        cur_key = properties[i*2];
        cur_val = properties[i*2+1];

        /* Move backwards through the sorted sublist, moving
         * properties forwards by one, until we find the proper place
         * to insert the "current" property. */
        for (j=i; (properties[j*2-2] > cur_key) && (j>0); j--) {
            /* Replace entry j with entry j-1 */
            properties[j*2] = properties[j*2-2];
            properties[j*2+1] = properties[j*2-2+1];
        }

        /* Insert the current key at j. */
        properties[j*2] = cur_key;
        properties[j*2+1] = cur_val;
    }

#ifdef DEBUG_SORT_PROPERTY_ARRAY
    for (i=1; i<size; i++)
        if (properties[i*2-2] > properties[i*2]) {
            printf("ERROR: sortPropertyArray() failed!\n");
            exit(-1);
        }
        else if (properties[i*2-2] == properties[i*2]) {
            printf("ERROR: duplicate definitions for a property!\n");
            exit(-1);
        }    
#endif
}

/* ================== Constructor and Destructor =================== */

/* Type.__new__(type) */
/* Create a new Type object, and initialize its properties array.  We
 * need to initialize the property array here (and not in __init__)
 * because we need to know how big to make the new object. */
static PyObject*
nltkType__new__(PyTypeObject* type, PyObject *args, PyObject *keywords)
{
    PyObject *name, *value;
    nltkType *self;
    int size;
    int pos = 0;
    int i;
    
    /* Check that there are no positional arguments. */
    if (PyObject_Length(args) != 0) {
        PyErr_SetString(PyExc_TypeError, TYPE_ERROR_001);
        return NULL;
    }

    /* Special case: no keyword arguments */
    if (keywords == NULL) {
        if ((self = (nltkType*)type->tp_alloc(type, 0)) == NULL)
            return NULL;
        self->ob_size = 0;
        return (PyObject *)self;
    }

    /* Check the number of keyword arguments. */
    size = PyDict_Size(keywords);

    /* Allocate space for the new object. */
    if ((self = (nltkType*)type->tp_alloc(type, size)) == NULL)
        return NULL;
    self->ob_size = size;

    /* Initialize the properties */
    for (i=0; PyDict_Next(keywords, &pos, &name, &value); i++) {
        Py_INCREF(name);
        Py_INCREF(value);
        PyString_InternInPlace(&name);
        nltkType_PROP_NAME(self, i) = name;
        nltkType_PROP_VALUE(self, i) = value;
    }

    /* Return the new object. */
    return (PyObject *)self;
}

/* Type.__del__(self) */
/* Deallocate all space associated with this Type. */
static void
nltkType__del__(nltkType *self)
{
    int i;
    
    /* Delete references to property names & values */
    for (i=0; i<self->ob_size; i++) {
        Py_DECREF(nltkType_PROP_NAME(self, i));
        Py_DECREF(nltkType_PROP_VALUE(self, i));
    }
    
    /* Free self. */
    self->ob_type->tp_free((PyObject*)self);
}

/* ========================= Type Methods ========================== */

/* Type.get(self, property) */
static PyObject *nltkType_get(nltkType *self, PyObject *args)
{
    PyObject *property;
    int i;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "S:Type.get", &property))
        return NULL;
    PyString_InternInPlace(&property);

    /* Look up the value */
    for (i=0; i<self->ob_size; i++)
        if (property == nltkType_PROP_NAME(self, i)) {
            Py_INCREF(nltkType_PROP_VALUE(self, i));
            return nltkType_PROP_VALUE(self, i);
        }

    /* We couldn't find it. */
    PyErr_SetString(PyExc_KeyError, TYPE_ERROR_002);
    return NULL;
}

/* Type.has(self, property) */
static PyObject *nltkType_has(nltkType *self, PyObject *args)
{
    PyObject *property;
    int i;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "S:Type.get", &property))
        return NULL;
    PyString_InternInPlace(&property);

    /* Look up the value */
    for (i=0; i<self->ob_size; i++)
        if (property == nltkType_PROP_NAME(self, i)) {
            Py_INCREF(nltkType_PROP_VALUE(self, i));
            return PyInt_FromLong(1);
        }

    /* We couldn't find it. */
    return PyInt_FromLong(0);
}

/* Type.properties(self) */
static PyObject *nltkType_properties(nltkType *self, PyObject *args)
{
    PyObject *list;
    int i;

    if ((list = PyList_New(self->ob_size)) == NULL) return NULL;

    for (i=0; i<self->ob_size; i++) {
        Py_INCREF(nltkType_PROP_NAME(self, i));
        PyList_SET_ITEM(list, i, nltkType_PROP_NAME(self, i));
    }

    return list;
}

/* Type.extend(self, **properties) */
static nltkType*
nltkType_extend(nltkType *self, PyObject *args, PyObject *keywords)
{
    PyTypeObject *type = self->ob_type;
    nltkType *newobj;
    PyObject *name, *value;
    int size, i, j;
    static char static_dupcheck[256];
    char *dupcheck;
    
    /* Check that there are no positional arguments. */
    if (PyObject_Length(args) != 0) {
        PyErr_SetString(PyExc_TypeError, TYPE_ERROR_003);
        return NULL;
    }

    /* If keywords==null, then just return ourself */
    if (keywords == NULL) {
        Py_INCREF(self);
        return self;
    }

    /* Get space for the duplicate property check.  If there are fewer
     * than 256 properties (the common case), then use the static
     * array; otherwise, we need to dynamically allocate one. */
    if (self->ob_size < 256)
        dupcheck = static_dupcheck;
    else
        dupcheck = PyMem_Malloc((self->ob_size)*sizeof(char));

    /* Calculate the space needed, and scan for duplicates.
     * dupcheck[i] is true iff i is a duplicate property. */
    size = self->ob_size + PyDict_Size(keywords);
    for (i=0; i<self->ob_size; i++) {
        name = nltkType_PROP_NAME(self, i);
        dupcheck[i] = (PyDict_GetItem(keywords, name) != NULL);
        if (dupcheck[i]) size -= 1;
    }

    /* Allocate space for the new object. */
    newobj = (nltkType*)type->tp_alloc(type, size);
    if (newobj == NULL) return NULL;
    newobj->ob_size = size;

    /* Copy the properties from self.  "i" is the index into
     * self->properties, and "j" is the index into
     * outobj->properties. */
    for (i=0,j=0; i<self->ob_size; i++) {
        name = nltkType_PROP_NAME(self, i);
        value = nltkType_PROP_VALUE(self, i);

        /* Don't copy properties that are overridden. */
        if (!dupcheck[i]) {
            Py_INCREF(name);
            Py_INCREF(value);
            PyString_InternInPlace(&name);
            nltkType_PROP_NAME(newobj, j) = name;
            nltkType_PROP_VALUE(newobj, j) = value;
            j++;
        }
    }

    /* Copy the properties from the keyword arguments.  "i" is the
     * positional index used to cycle through the dictionary; "j" is
     * the index into outobj->properties. */
    for (i=0; PyDict_Next(keywords, &i, &name, &value); j++) {
        Py_INCREF(name);
        Py_INCREF(value);
        PyString_InternInPlace(&name);
        nltkType_PROP_NAME(newobj, j) = name;
        nltkType_PROP_VALUE(newobj, j) = value;
    }

    /* Free the duplication check array, if we allocated it. */
    if (self->ob_size >= 256)
        PyMem_Free(dupcheck);

    assert(j==size);

    /* Return the new object. */
    return newobj;
}

/* Type.select(self, *properties) */
static nltkType*
nltkType_select(nltkType *self, PyObject *properties)
{
    PyTypeObject *type = self->ob_type;
    nltkType *newobj;
    int size = PyTuple_GET_SIZE(properties);
    int i, j, n;
    static char static_dupcheck[256];
    char *dupcheck;

    /* If properties==(), then just return ourself */
    if (size == 0) {
        Py_INCREF(self);
        return self;
    }

    /* Get space for the duplicate property check.  If there are fewer
     * than 256 properties (the common case), then use the static
     * array; otherwise, we need to dynamically allocate one. */
    if (self->ob_size < 256)
        dupcheck = static_dupcheck;
    else
        dupcheck = PyMem_Malloc((self->ob_size)*sizeof(char));

    /* Zero-out the duplicate check list */
    bzero(dupcheck, self->ob_size);

    /* Allocate space for the new object. */
    newobj = (nltkType*)type->tp_alloc(type, size);
    newobj->ob_size = size;
    if (newobj == NULL) return NULL;

    /* Fill in newobj's properties.  "n" is the next index to fill-in
     * for newobj; "i" is the next index to read from properties; and
     * "j" is the index we're checking in self.  If properties
     * contains no duplicates, then "i" will be equal to "n". */
    n=0;
    for (i=0; i<size; i++) {
        PyObject *property = PyTuple_GET_ITEM(properties, i);
        PyString_InternInPlace(&property);
        for (j=0; j<self->ob_size; j++) {
            if (property == nltkType_PROP_NAME(self, j)) {
                if (!dupcheck[j]) { /* ignore duplicates. */
                    PyObject *prop_name = nltkType_PROP_NAME(self, j);
                    PyObject *prop_value = nltkType_PROP_VALUE(self, j);
                    Py_INCREF(prop_name);
                    Py_INCREF(prop_value);
                    nltkType_PROP_NAME(newobj, n) = prop_name;
                    nltkType_PROP_VALUE(newobj, n) = prop_value;
                    dupcheck[j] = 1;
                    n++;
                }
                break;
            }
        }
        if (j == self->ob_size) {
            /* We didn't find the property.  We have to undo all the
             * INCREFs that we've done so far. */
            PyErr_SetString(PyExc_KeyError, TYPE_ERROR_004);
            for (i--; i>=0; i--) {
                Py_DECREF(nltkType_PROP_NAME(newobj, i));
                Py_DECREF(nltkType_PROP_VALUE(newobj, i));
            }
            return NULL;
        }
    }

    /* Free the duplication check array, if we allocated it. */
    if (self->ob_size >= 256)
        PyMem_Free(dupcheck);

    /* If there were duplicates, then adjust the size of newobj down.
     * This wastes some space, but otherwise won't hurt anything.  But
     * we don't care too much about the wasted space, because it
     * should be fairly unusual for there to be any duplicates in the
     * given list of properties. */
    if (n<size) newobj->ob_size = n;

    return newobj;
}

/* ======================== Type Operators ========================= */

/* repr(self) */
static PyObject *nltkType__repr__(nltkType *self)
{
    PyObject *s;
    int i;
    int size = self->ob_size;

    /* Construct the initial string. */
    if ((s = PyString_FromString("<")) == NULL) return NULL;

    /* Special check for empty types */
    if (size == 0) {
        PyString_ConcatAndDel(&s, PyString_FromString("Empty Type>"));
        return s;
    }
    
    /* Iterate through properties */
    for (i=0; i<size; i++) {
        PyString_Concat(&s, nltkType_PROP_NAME(self, i));
        PyString_ConcatAndDel(&s, PyString_FromString("="));
        PyString_ConcatAndDel(&s, PyObject_Repr(nltkType_PROP_VALUE(self, i)));
        if (i < (size-1))
            PyString_ConcatAndDel(&s, PyString_FromString(", "));
    }

    PyString_ConcatAndDel(&s, PyString_FromString(">"));
    return s;
}

/* getattr(self, name) */
static PyObject *nltkType__getattro__(nltkType *self, PyObject *name)
{
    int i;

    /* Intern the property name. */
    PyString_InternInPlace(&name);

    /* Look up the name as a property. */
    for (i=0; i<self->ob_size; i++)
        if (name == nltkType_PROP_NAME(self, i)) {
            Py_INCREF(nltkType_PROP_VALUE(self, i));
            return nltkType_PROP_VALUE(self, i);
        }

    /* It wasn't a special attribute; Use the generic version of
     * getattr */
    return PyObject_GenericGetAttr((PyObject *)self, name);
}

static int nltkType__setattro__(PyObject *self, PyObject *name, PyObject *val)
{
    PyErr_SetString(PyExc_AttributeError, TYPE_ERROR_005);
    return -1;
}

/* cmp(self, other) */
static int nltkType__cmp__(nltkType *self, nltkType *other)
{
    int result = 0;
    int i;
    
    /* Check type(other) */
    if (!nltkType_Check(other)) return -1;

    /* If the number of properties differs, then we know they're
     * different. */
    if (self->ob_size != other->ob_size)
        return (self->ob_size<other->ob_size) ? -1 : 1;

    /* Sort the properties in each type.  This will make it easier to
     * compare them.  Note that sortPropertyArray() is fairly fast if
     * the type properties are already sorted. */
    sortPropertyArray(self->properties, self->ob_size);
    sortPropertyArray(other->properties, other->ob_size);

    /* Compare the property names and values. */
    for (i=0; i<self->ob_size; i++) {
        /* Compare the property name. */
        if (nltkType_PROP_NAME(self, i) != nltkType_PROP_NAME(other, i)) {
            return (nltkType_PROP_NAME(self, i)<nltkType_PROP_NAME(other, i)
                    ? -1 : 1);
        }

        /* Compare the property value. */
        if (PyObject_Cmp(nltkType_PROP_VALUE(self, i),
                         nltkType_PROP_VALUE(other, i), &result) == -1)
            return -1; /* Exception exit */
        if (result != 0)
            return result;
    }

    /* All properties were equal; they must be equal. */
    return 0;
}

/* hash(self) */
static long nltkType__hash__(nltkType *self)
{
    /* Hash=0 for empty properties. */
    if (self->ob_size == 0) return 0;

    /* Hash off the first property value (typically "text") */
    return PyObject_Hash(nltkType_PROP_VALUE(self, 0));
}

/* ===================== Type Type Definition ====================== */

/* Type methods */
static PyMethodDef nltkType_methods[] = {
    {"get", (PyCFunction)nltkType_get, METH_VARARGS, ""},
    {"has", (PyCFunction)nltkType_has, METH_VARARGS, ""},
    {"properties", (PyCFunction)nltkType_properties, METH_NOARGS, ""},
    {"extend", (PyCFunction)nltkType_extend, METH_KEYWORDS, ""},
    {"select", (PyCFunction)nltkType_select, METH_VARARGS, ""},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

static PyTypeObject nltkTypeType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /* ob_size */
    "Type",                                    /* tp_name */
    sizeof(nltkType),                          /* tp_basicsize */
    2 * sizeof(PyObject*),                     /* tp_itemsize */
    (destructor)nltkType__del__,               /* tp_dealloc */
    0,                                         /* tp_print */
    0,                                         /* tp_getattr */
    0,                                         /* tp_setattr */
    (cmpfunc)nltkType__cmp__,                  /* tp_compare */
    (reprfunc)nltkType__repr__,                /* tp_repr */
    0,                                         /* tp_as_number */
    0,                                         /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    (hashfunc)nltkType__hash__,                /* tp_hash  */
    0,                                         /* tp_call */
    0,                                         /* tp_str */
    (getattrofunc)nltkType__getattro__,        /* tp_getattro */
    (setattrofunc)nltkType__setattro__,        /* tp_setattro */
    0,                                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /* tp_flags */
    TYPE_DOC,                                  /* tp_doc */
    0,		                               /* tp_traverse */
    0,		                               /* tp_clear */
    0,		                               /* tp_richcompare */
    0,		                               /* tp_weaklistoffset */
    0,		                               /* tp_iter */
    0,		                               /* tp_iternext */
    nltkType_methods,                          /* tp_methods */
    0,                                         /* tp_members */
    0,                                         /* tp_getset */
    0,                                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    0,                                         /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)nltkType__new__,                  /* tp_new */
};

/*********************************************************************
 *  TOKEN: Implementation 1
 *********************************************************************/

/* ================== Constructor and Destructor =================== */

/* Token.__new__(token) */
/* Create a new Token object, and initialize its type to an empty type
 * and its location to None. */
static PyObject*
nltkToken__new__(PyTypeObject* type, PyObject *args, PyObject *keywords)
{
    nltkToken *self;
    
    /* Use this as the default type for tokens.  This lets us avoid
     * several sanity checks later on. */
    static nltkType *default_type = NULL;

    /* Initialize default_type.
     * [XXXX this code is too impl. dependant] */
    if (default_type == NULL) {
        default_type = (nltkType*)nltkTypeType.tp_alloc(&nltkTypeType, 0);
        if (default_type == NULL) return NULL;
        default_type->ob_size = 0;
    }
    
    /* Allocate space for the new object. */
    self = (nltkToken*)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;

    /* Start with no type or location. */
    Py_INCREF(Py_None);
    Py_INCREF(default_type);
    self->loc = Py_None;
    self->type = default_type;

    /* Return the new object. */
    return (PyObject *)self;
}

/* Token.__init__(self, start, end=None, unit=None, source=None) */
/* Initialize the type and location of a Token. */
static int
nltkToken__init__(nltkToken *self, PyObject *args, PyObject *keywords)
{
    PyObject *type = NULL;
    PyObject *loc = NULL;
    static char *kwlist[] = {"type", "loc", NULL};

    /* Parse the arguments. */
    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O|O",
                                     kwlist,
                                     &type, &loc))
        return -1;

    /* Store the type. */
    /* [XXXX Check that it's a Type object] */
    Py_XDECREF(self->type);
    self->type = (nltkType *)type;
    Py_INCREF(self->type);

    /* Store the location. */
    Py_XDECREF(self->loc);
    self->loc = (loc!=NULL) ? loc : Py_None;
    Py_INCREF(self->loc);
    
    return 0;
}

/* Token.__del__(self) */
/* Deallocate all space associated with this Token. */
static void
nltkToken__del__(nltkToken *self)
{
    /* Delete references to loc & type */
    Py_XDECREF(self->loc);
    Py_XDECREF(self->type);

    /* Free self. */
    self->ob_type->tp_free((PyObject*)self);
}

/* ======================== Token Methods ========================== */

/* Token.get(self, property) */
static PyObject *nltkToken_get(nltkToken *self, PyObject *args)
{ return nltkType_get(self->type, args); }

/* Token.has(self, property) */
static PyObject *nltkToken_has(nltkToken *self, PyObject *args)
{ return nltkType_has(self->type, args); }

/* Token.properties(self) */
static PyObject *nltkToken_properties(nltkToken *self, PyObject *args)
{ return nltkType_properties(self->type, args); }

/* Token.extend(self, **properties) */
static nltkToken*
nltkToken_extend(nltkToken *self, PyObject *args, PyObject *keywords)
{
    PyTypeObject *type = self->ob_type;
    nltkToken *newobj;

    /* Create the new object. */
    if ((newobj = (nltkToken*)type->tp_alloc(type, 0)) == NULL)
        return NULL;

    /* Copy the location.  (might be NULL so use XINCREF) */
    Py_XINCREF(self->loc);
    newobj->loc = self->loc;

    /* Extend the type. */
    newobj->type = nltkType_extend(self->type, args, keywords);
    if (newobj->type == NULL) {
        Py_DECREF(newobj);
        return NULL;
    }
    
    /* Return the newly created object. */
    return newobj;
}

/* Token.select(self, *properties) */
static nltkToken*
nltkToken_select(nltkToken *self, PyObject *properties)
{
    PyTypeObject *type = self->ob_type;
    nltkToken *newobj;

    /* Create the new object. */
    if ((newobj = (nltkToken*)type->tp_alloc(type, 0)) == NULL)
        return NULL;

    /* Copy the location.  (might be NULL so use XINCREF) */
    Py_XINCREF(self->loc);
    newobj->loc = self->loc;

    /* Select the type. */
    newobj->type = nltkType_select(self->type, properties);
    if (newobj->type == NULL) {
        Py_DECREF(newobj);
        return NULL;
    }

    /* Return the newly created object. */
    return newobj;
}

/* ======================= Token Operators ========================= */

/* repr(self) */
static PyObject *nltkToken__repr__(nltkToken *self)
{
    PyObject *s;
    
    if ((s = PyObject_Repr((PyObject *)self->type))==NULL)
        return NULL;
    if (self->loc != Py_None)
        PyString_ConcatAndDel(&s, PyObject_Repr((PyObject *)self->loc));
    else
        PyString_ConcatAndDel(&s, PyString_FromString("@[?]"));

    return s;
}

/* cmp(self, other) */
static int nltkToken__cmp__(nltkToken *self, nltkToken *other)
{
    int result = 0;

    /* Check type(other) */
    if (!nltkToken_Check(other)) return -1;

    /* Compare based on location */
    if (PyObject_Cmp(self->loc, other->loc, &result) == -1)
        return -1;
    if (result != 0)
        return result;
    
    /* Compare based on types */
    if (PyObject_Cmp((PyObject*)self->type,
                      (PyObject*)other->type, &result) == -1)
        return -1;
    return result;
}

/* hash(self) */
static long nltkToken__hash__(nltkToken *self) {
    /* Hash based on location, if available.  Otherwise, hash on type. */
    if (self->loc != Py_None)
        return nltkLocation__hash__((nltkLocation *)self->loc);
    else
        return nltkType__hash__(self->type);
}

/* getattr(self, name) */
static PyObject *nltkToken__getattro__(nltkToken *self, PyObject *name)
{
    int i;
    nltkType *typ = self->type;

    /* Intern the property name. */
    PyString_InternInPlace(&name);

    /* Look up the name as a property in our type. */
    for (i=0; i<typ->ob_size; i++)
        if (name == nltkType_PROP_NAME(typ, i)) {
            Py_INCREF(nltkType_PROP_VALUE(typ, i));
            return nltkType_PROP_VALUE(typ, i);
        }

    /* It wasn't a special attribute; Use the generic version of
     * getattr */
    return PyObject_GenericGetAttr((PyObject *)self, name);
}

static int nltkToken__setattro__(PyObject *self, PyObject *name, PyObject *val)
{
    PyErr_SetString(PyExc_AttributeError, TYPE_ERROR_005);
    return -1;
}

/* ==================== Token Type Definition ====================== */

struct PyMemberDef nltkToken_members[] = {
    {"type", T_OBJECT, offsetof(nltkToken, type), RO, ""},
    {"loc", T_OBJECT, offsetof(nltkToken, loc), RO, ""},
    {NULL, 0, 0, 0, NULL} /* Sentinel */
};
    
/* Token methods */
static PyMethodDef nltkToken_methods[] = {
    {"get", (PyCFunction)nltkToken_get, METH_VARARGS, ""},
    {"has", (PyCFunction)nltkToken_has, METH_VARARGS, ""},
    {"properties", (PyCFunction)nltkToken_properties, METH_NOARGS, ""},
    {"extend", (PyCFunction)nltkToken_extend, METH_KEYWORDS, ""},
    {"select", (PyCFunction)nltkToken_select, METH_VARARGS, ""},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

static PyTypeObject nltkTokenType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /* ob_size */
    "Token",                                   /* tp_name */
    sizeof(nltkToken),                         /* tp_basicsize */
    0,                                         /* tp_itemsize */
    (destructor)nltkToken__del__,              /* tp_dealloc */
    0,                                         /* tp_print */
    0,                                         /* tp_getattr */
    0,                                         /* tp_setattr */
    (cmpfunc)nltkToken__cmp__,                 /* tp_compare */
    (reprfunc)nltkToken__repr__,               /* tp_repr */
    0,                                         /* tp_as_number */
    0,                                         /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    (hashfunc)nltkToken__hash__,               /* tp_hash  */
    0,                                         /* tp_call */
    0,                                         /* tp_str */
    (getattrofunc)nltkToken__getattro__,       /* tp_setattro */
    (setattrofunc)nltkToken__setattro__,       /* tp_setattro */
    0,                                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /* tp_flags */
    TOKEN_DOC,                                 /* tp_doc */
    0,		                               /* tp_traverse */
    0,		                               /* tp_clear */
    0,		                               /* tp_richcompare */
    0,		                               /* tp_weaklistoffset */
    0,		                               /* tp_iter */
    0,		                               /* tp_iternext */
    nltkToken_methods,                         /* tp_methods */
    nltkToken_members,                         /* tp_members */
    0,                                         /* tp_getset */
    0,                                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    (initproc)nltkToken__init__,               /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)nltkToken__new__,                 /* tp_new */
};


/*********************************************************************
 *  MODULE DEFINITION
 *********************************************************************/

/* Methods defined by the token module. */
static PyMethodDef _ctoken_methods[] = {
    /* End of list */
    {NULL, NULL, 0, NULL}
};

/* Module initializer */
DL_EXPORT(void) init_ctoken(void) 
{
    PyObject *d, *m;

    /* Finalize type objects */
    if (PyType_Ready(&nltkLocationType) < 0) return;
    if (PyType_Ready(&nltkLen1LocationType) < 0) return;
    if (PyType_Ready(&nltkTypeType) < 0) return;
    if (PyType_Ready(&nltkTokenType) < 0) return;

    /* Initialize the module */
    m = Py_InitModule3("_ctoken", _ctoken_methods, MODULE_DOC);

    /* Add the types to the module dictionary. */
    d = PyModule_GetDict(m);
    PyDict_SetItemString(d, "Location", (PyObject*)&nltkLocationType);
    PyDict_SetItemString(d, "Type", (PyObject*)&nltkTypeType);
    PyDict_SetItemString(d, "Token", (PyObject*)&nltkTokenType);
}
