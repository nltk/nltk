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
 *     2. Location
 *         2.1. Helper Functions
 *         2.2. Constructor & Destructor
 *         2.3. Methods
 *         2.4. Operators
 *         2.5. Type Definition
 *     3. Module Definition
 *
 * Property names are interned, for speed.
 * Units should get interned, too.  (But they're not currently)
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

/*********************************************************************
 *  LOCATION CONTEXT
 *********************************************************************/

#define LOCATION_CONTEXT_CACHE_SIZE 5
static nltkLocationContext *lc_cache[LOCATION_CONTEXT_CACHE_SIZE];

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
        for (i=0; i<LOCATION_CONTEXT_CACHE_SIZE; i++) {
            lc_cache[i] = NULL;
        }
        next_cell = 0;
    }

    /* Downcase the unit. */
    unit = normalizeUnitCase(unit);
    
    /* Intern the unit, so we can do faster compares. */
    if (unit != NULL && unit != Py_None)
        PyString_InternInPlace(&unit);

    /* Search for the given unit/source pair in the cache. */
    for (i=0; i<LOCATION_CONTEXT_CACHE_SIZE; i++)
        if (lc_cache[i] != NULL) 
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

    /* We didn't find a match; so pick a cell to replace, and build a
     * new location context there.  This should be fairly infrequent,
     * so it would be possible to put a smarter algorithm here (e.g.,
     * one that sorts the location contexts by refcount, starting at
     * index 1, and puts the new lc at index 0). */

    /* Reuse empty cells when possible. */
    for (i=0; i<LOCATION_CONTEXT_CACHE_SIZE; i++)
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
    next_cell = (next_cell+1)%LOCATION_CONTEXT_CACHE_SIZE;

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
    for (i=0; i<LOCATION_CONTEXT_CACHE_SIZE; i++)
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
    if (!is_nltkLen1Location(self) && (self->start == self->end)) {
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
    if (!is_nltkLen1Location(self) && (self->start == self->end)) {
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
static PyObject *nltkLocation__repr___(nltkLocation *self)
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

static PyObject *nltkLocation__repr__(nltkLocation *self) {
    PyObject *s = nltkLocation__repr___(self);
    if (is_nltkLen1Location(self))
        return PyString_FromFormat("*%s", PyString_AS_STRING(s));
    else
        return s;
}

/* str(self) */
static PyObject *nltkLocation__str__(nltkLocation *self)
{
    if (self->context == NULL || self->context->source == Py_None)
        return nltkLocation__repr__(self);
    else if (is_nltkLocation(self->context->source))
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
    if (!is_nltkLen1Location(other) && !is_nltkLocation(other))
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
    if (!is_nltkLen1Location(other) && !is_nltkLocation(other)) {
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

/* This is used by __getattr__ */
static PyMethodDef nltkLocation_methods[];

static PyObject *nltkLocation__getattr__(nltkLocation *self, char *name) {
    if (strcmp(name, "start") == 0)
        return PyInt_FromLong(self->start);
    if (strcmp(name, "end") == 0)
        return PyInt_FromLong(nltkLocation_END(self));
    if (strcmp(name, "unit") == 0) {
        if (self->context == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            Py_INCREF(self->context->unit);
            return self->context->unit;
        }
    }
    if (strcmp(name, "source") == 0) {
        if (self->context == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            Py_INCREF(self->context->source);
            return self->context->source;
        }
    }

    return PyObject_GenericGetAttr((PyObject *)self,
                                   PyString_FromString(name));
}

/* =================== Location Type Definition ==================== */

/* Location attributes.  These are used by PyObject_GenericGetAttr to
 * generate attributes.  However, note that "unit" and "source" are
 * not directly stored in the object; we handle them manually in
 * __getattr__.  So we give a dummy value (-1) for the offset of the
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
    (getattrfunc)nltkLocation__getattr__,      /* tp_getattr */
    0,                                         /* tp_setattr */
    (cmpfunc)nltkLocation__cmp__,              /* tp_compare */
    (reprfunc)nltkLocation__repr__,            /* tp_repr */
    0,                                         /* tp_as_number */
    &nltkLocation_as_sequence,                 /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    (hashfunc)nltkLocation__hash__,            /* tp_hash  */
    0,                                         /* tp_call */
    (reprfunc)nltkLocation__str__,             /* tp_str */
    0,                                         /* tp_getattro */
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
    (getattrfunc)nltkLocation__getattr__,      /* tp_getattr */
    0,                                         /* tp_setattr */
    (cmpfunc)nltkLocation__cmp__,              /* tp_compare */
    (reprfunc)nltkLocation__repr__,            /* tp_repr */
    0,                                         /* tp_as_number */
    &nltkLocation_as_sequence,                 /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    (hashfunc)nltkLocation__hash__,            /* tp_hash  */
    0,                                         /* tp_call */
    (reprfunc)nltkLocation__str__,             /* tp_str */
    0,                                         /* tp_getattro */
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
 *  TYPE
 *********************************************************************/
/* Check immutability?? */

/* ================== Constructor and Destructor =================== */

/* Type.__new__(type) */
/* Create a new Type object, and initialize its members to default
 * values.  The properties dictionary is set to None. */
static PyObject*
nltkType__new__(PyTypeObject* type, PyObject *args, PyObject *keywords)
{
    /* Allocate space for the new object. */
    nltkType *self = (nltkType*)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;

    /* Start with no properties. */
    self->num_props = 0;
    self->properties = NULL;

    /* Return the new object. */
    return (PyObject *)self;
}

/* Type.__init__(self, start, end=None, unit=None, source=None) */
/* Initialize the properties dictionary for the given Type object. */
static int
nltkType__init__(nltkType *self, PyObject *args, PyObject *keywords)
{
    /* Check that there are no positional arguments. */
    if (PyObject_Length(args) != 0) {
        PyErr_SetString(PyExc_TypeError, TYPE_ERROR_001);
        return -1;
    }

    /* Initialize properties */
    if (keywords == NULL) {
    } else {
        PyObject *name, *value;
        int size, i, pos = 0;

        /* Allocate space for prop_names & prop_values */
        self->num_props = size = PyDict_Size(keywords);
        self->properties = PyMem_Malloc(2*size*sizeof(PyObject *));

        /* Initialize the properties */
        for (i=0; PyDict_Next(keywords, &pos, &name, &value); i++) {
            Py_INCREF(name);
            Py_INCREF(value);
            PyString_InternInPlace(&name);
            nltkType_PROP_NAME(self, i) = name;
            nltkType_PROP_VALUE(self, i) = value;
        }
    }

    return 0;
}

/* Type.__del__(self) */
/* Deallocate all space associated with this Type. */
static void
nltkType__del__(nltkType *self)
{
    int i;
    
    /* Delete references to property names & values */
    for (i=0; i<self->num_props; i++) {
        Py_DECREF(nltkType_PROP_NAME(self, i));
        Py_DECREF(nltkType_PROP_VALUE(self, i));
    }
    
    /* Deallocate space for properties. */
    if (self->properties != NULL) PyMem_Free(self->properties);

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
    for (i=0; i<self->num_props; i++)
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
    for (i=0; i<self->num_props; i++)
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

    if ((list = PyList_New(self->num_props)) == NULL) return NULL;

    for (i=0; i<self->num_props; i++) {
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
    int size, i, j, pos = 0;
    
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
    
    /* Allocate space for the new object. */
    newobj = (nltkType*)type->tp_alloc(type, 0);
    if (newobj == NULL) return NULL;

    /* Allocate space for prop_names & prop_values */
    size = self->num_props + PyDict_Size(keywords);
    newobj->num_props = size;
    newobj->properties = PyMem_Malloc(2*size*sizeof(PyObject *));

    /* Copy the properties from keyword arguments */
    for (i=0; PyDict_Next(keywords, &pos, &name, &value); i++) {
        Py_INCREF(name);
        Py_INCREF(value);
        PyString_InternInPlace(&name);
        nltkType_PROP_NAME(newobj, i) = name;
        nltkType_PROP_VALUE(newobj, i) = value;
    }

    /* Copy the properties from self. */
    for (j=0; j<self->num_props; j++) {
        name = nltkType_PROP_NAME(self, j);
        value = nltkType_PROP_VALUE(self, j);

        /* Don't copy properties that are already defined. */
        if (PyDict_GetItem(keywords, name) == NULL) {
            Py_INCREF(name);
            Py_INCREF(value);
            PyString_InternInPlace(&name);
            nltkType_PROP_NAME(newobj, i) = name;
            nltkType_PROP_VALUE(newobj, i) = value;
            i++;
        }
    }

    /* If any properties were redefined, then i will be smaller than
     * size; if this is the case, then shrink the new Type object down
     * to the appropriate size. */
    if (i<size) {
        newobj->num_props = i;
        newobj->properties = PyMem_Realloc(newobj->properties,
                                           2*i*sizeof(PyObject *));
    }

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
    int n, i, j;
    char *dupcheck;

    /* If properties==(), then just return ourself */
    if (size == 0) {
        Py_INCREF(self);
        return self;
    }

    /* Allocate space for the new object. */
    newobj = (nltkType*)type->tp_alloc(type, 0);
    if (newobj == NULL) return NULL;

    /* Allocate space for prop_names & prop_values.  Assume that
     * properties contains no duplicates (it won't hurt much, it'll
     * just result in a less efficient object). */
    newobj->num_props = size;
    newobj->properties = PyMem_Malloc(2*size*sizeof(PyObject *));

    /* Keep track of duplicates. */
    dupcheck = PyMem_Malloc((self->num_props)*sizeof(char));
    bzero(dupcheck, self->num_props);

    /* Fill in values.  "n" is the next index to fill-in for newobj;
     * "i" is the next index to read from properties; and "j" is the
     * index we're checking in self.  If properties contains no
     * duplicates, then "i" will be equal to "n". */
    n=0;
    for (i=0; i<size; i++) {
        PyObject *property = PyTuple_GET_ITEM(properties, i);
        PyString_InternInPlace(&property);
        for (j=0; j<self->num_props; j++) {
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
        if (j == self->num_props) {
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

    /* Free the duplicate-checking array. */
    PyMem_Free(dupcheck);

    /* If there were duplicates, then shrink the new Type object down
     * to the appropriate size. */
    if (n<size) {
        newobj->num_props = n;
        newobj->properties = PyMem_Realloc(newobj->properties,
                                           2*n*sizeof(PyObject *));
    }

    return newobj;
}

/* ======================== Type Operators ========================= */

/* repr(self) */
static PyObject *nltkType__repr__(nltkType *self)
{
    PyObject *s;
    int i;
    int size = self->num_props;

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

/* This is used by nltkType__getattr__; so declare it. */
static PyMethodDef nltkType_methods[];

/* getattr(self, name) */
static PyObject *nltkType__getattro__(nltkType *self, PyObject *name)
{
    PyObject *val;
    int i;

    /* Intern the property name. */
    PyString_InternInPlace(&name);

    /* Look up the name as a property. */
    for (i=0; i<self->num_props; i++)
        /* Should I bother with hashes here? */
        if (name == nltkType_PROP_NAME(self, i)) {
            Py_INCREF(nltkType_PROP_VALUE(self, i));
            return nltkType_PROP_VALUE(self, i);
        }

    /* Look up the name as a method. */
    val = Py_FindMethod(nltkType_methods, (PyObject*)self,
                        PyString_AS_STRING(name));
    if (val != NULL) return val;

    /* We couldn't find it. */
    PyErr_SetString(PyExc_KeyError, TYPE_ERROR_004);
    return NULL;
}

/* cmp(self, other) */
static int nltkType__cmp__(nltkType *self, nltkType *other)
{
    /*int result = 0; */
    /*int i,j; */
    
    /* Check type(other) */
    if (!is_nltkType(other)) return -1;

    /* Deal with duplicates??? */
    
    return 0;
}

/* hash(self) */
static long nltkType__hash__(nltkType *self)
{
    /* Hash=0 for empty properties. */
    if (self->num_props == 0) return 0;

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
    0,                                         /* tp_itemsize */
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
    0,                                         /* tp_setattro */
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
    (initproc)nltkType__init__,                /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)nltkType__new__,                  /* tp_new */
};

/*********************************************************************
 *  TOKEN
 *********************************************************************/

/* ================== Constructor and Destructor =================== */

/* 1. we ignore type, and pick our own implementation.
 * 2. but, we save type in self->real_type.
 * 3. for getattr, we consult self->real_type???
 */
static PyObject*
nltkToken__new__(PyTypeObject* type, PyObject *args,
                         PyObject *keywords)
{
    /* Allocate space for the new object. */
    nltkType *self = (nltkType*)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;

    /* Start with no properties. */
    self->num_props = 0;
    self->properties = NULL;
    /* Set the start & end to zero. */

    /* Return the new object. */
    return (PyObject *)self;
}

/* Token.__init__(self, type, loc) */
static int
nltkToken__init__(nltkType *self, PyObject *args, PyObject *keywords)
{
    PyObject *type = NULL;
    PyObject *loc = NULL;
    static char *kwlist[] = {"type", "loc", NULL};

    /* Parse the arguments. */
    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O|O",
                                     kwlist,
                                     &type, &loc))
        return -1;

    /* Location of none????? */
    return 0;
}


/* Type.__del__(self) */
/* Deallocate all space associated with this Type. */
static void
nltkToken__del__(PyObject *self)
{
    self->ob_type->tp_free((PyObject*)self);
}

/* getattr(self, name) */
static PyObject *nltkToken__getattro__(nltkToken *self,
                                            PyObject *name)
{
    /*PyObject *x; */
    /* Try returning a property (stub) */
    if (strcmp(PyString_AS_STRING(name), "x") == 0)
        return PyString_FromString("XXX");

    /* Delegate to base class. */
    /*x = self->real_type->tp_getattro((PyObject *)self, name); */
    return NULL;
}

static PyObject *nltkToken__repr__(PyObject *self)
{
    return PyString_FromString("<Token>");
}

/* ==================== Token Type Definition ====================== */

    
static PyTypeObject nltkTokenType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /* ob_size */
    "Token",                                   /* tp_name */
    sizeof(nltkToken),                      /* tp_basicsize */
    0,                                         /* tp_itemsize */
    0,//    (destructor)nltkToken__del__,          /* tp_dealloc */
    0,                                         /* tp_print */
    0,                                         /* tp_getattr */
    0,                                         /* tp_setattr */
    0,//    (cmpfunc)nltkToken__cmp__,              /* tp_compare */
    (reprfunc)nltkToken__repr__,          /* tp_repr */
    0,                                         /* tp_as_number */
    0,//    &nltkToken_as_sequence,                 /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    0,//    (hashfunc)nltkToken__hash__,            /* tp_hash  */
    0,                                         /* tp_call */
    0,//    (reprfunc)nltkToken__str__,             /* tp_str */
    (getattrofunc)nltkToken__getattro__,  /* tp_getattro */
    0,                                         /* tp_setattro */
    0,                                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /* tp_flags */
    0,//    ARRAYTOKEN_DOC,                              /* tp_doc */
    0,		                               /* tp_traverse */
    0,		                               /* tp_clear */
    0,		                               /* tp_richcompare */
    0,		                               /* tp_weaklistoffset */
    0,		                               /* tp_iter */
    0,		                               /* tp_iternext */
    0,//    nltkToken_methods,                      /* tp_methods */
    0,//    nltkToken_members,                      /* tp_members */
    0,                                         /* tp_getset */
    0,                                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    0,//    (initproc)nltkToken__init__,            /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)nltkToken__new__,              /* tp_new */
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
