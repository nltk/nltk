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

/*********************************************************************
 *  LOCATION
 *********************************************************************/

/* =================== Location Helper Functions =================== */

/* If the given string is in lower case, then return it; otherwise,
 * construct a new string that is the downcased version of s.  The
 * returned string is a new reference (not borrowed). */
PyObject *normalizeCase(PyObject *string)
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
    buffer = PyMem_MALLOC(size+1);
    if (buffer == NULL) return NULL;
    s2 = buffer;
    buffer[size] = 0;
    s = PyString_AS_STRING(string);
    for (; s<e; s++,s2++)
        (*s2) = tolower(*s);
    return PyString_FromStringAndSize(buffer, size);
}

/* Return true iff the units & source & type match.  otherwise,
 * set an appropriate exception and return 0. */
int check_units_and_source(locationObject *self, locationObject *other)
{
    int result = 0;
    
    /* Check that the units match */
    if (PyObject_Cmp(self->unit, other->unit, &result) == 1)
        return 0;
    if (result != 0) {
        PyErr_SetString(PyExc_ValueError, LOC_ERROR_003);
        return 0;
    }

    /* Check that the sources match */
    if (PyObject_Cmp(self->source, other->source, &result) == 1)
        return 0;
    if (result != 0) {
        PyErr_SetString(PyExc_ValueError, LOC_ERROR_004);
        return 0;
    }

    return 1;
}

/* Return a copy of the given location */
locationObject *location_copy(locationObject* original)
{
    PyTypeObject *type = original->ob_type;
    locationObject *loc;
    
    /* Create the return value object. */
    loc = (locationObject*)type->tp_alloc(type, 0);
    if (loc == NULL) return NULL;

    /* Fill in values. */
    loc->start = original->start;
    loc->end = original->end;
    loc->unit = original->unit;
    loc->source = original->source;
    Py_INCREF(loc->unit);
    Py_INCREF(loc->source);

    return loc;
}

/* ================== Constructor and Destructor =================== */

/* Location.__new__(type) */
/* Create a new Location object, and initialize its members to default
 * values.  Unit and source are set to None, and start & end are set
 * to zero. */
static PyObject*
location_new(PyTypeObject* type, PyObject *args, PyObject *keywords)
{
    /* Allocate space for the new object. */
    locationObject *self;
    self = (locationObject*)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;
    
    /* Set the start & end to zero. */
    self->start = 0;
    self->end = 0;

    /* Set the unit & source to None. */
    Py_INCREF(Py_None);
    Py_INCREF(Py_None);
    self->unit = Py_None;
    self->source = Py_None;

    /* Return the new object. */
    return (PyObject *)self;
}

/* Location.__init__(self, start, end=None, unit=None, source=None) */
/* Initialize the start, end, unit, and source for the given location.
 * If end is unspecified, then use start+1.  If source or unit are *
 * unspecified, then don't change them.  (Location.__new__ already set
 * them to None. */
static int
location_init(locationObject* self, PyObject *args, PyObject *keywords)
{
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
        return -1;

    /* Set the start index. */
    self->start = PyInt_AsLong(start);
    if (self->start == -1 && PyErr_Occurred()) return -1;

    /* Set the end index. */
    if ((end == NULL) || (end == Py_None)) {
        self->end = self->start + 1;
    } else {
        self->end = PyInt_AsLong(end);
        if (self->end == -1 && PyErr_Occurred()) return -1;

        /* Check that end<start. */
        if (self->end < self->start) {
            PyErr_SetString(PyExc_ValueError, LOC_ERROR_001);
            return -1;
        }
    }

    /* Set the unit. */
    if (unit != NULL) {
        Py_XDECREF(self->unit);
        self->unit = normalizeCase(unit);
    }

    /* Set the source. */
    if (source != NULL) {
        Py_XDECREF(self->source);
        Py_INCREF(source);
        self->source = source;
    }

    return 0;
}

/* Location.__del__(self) */
/* Deallocate all space associated with this Location. */
static void
location_dealloc(locationObject* self)
{
    Py_XDECREF(self->unit);
    Py_XDECREF(self->source);
    self->ob_type->tp_free((PyObject*)self);
}

/* ======================= Location Methods ======================== */

/* Location.length(self) */
/* Return the length of this location (end-start). */
static PyObject *location_length(locationObject* self, PyObject *args)
{
    return PyInt_FromLong(self->end - self->start);
}

/* Location.start_loc(self) */
/* Return a zero-length location at the start offset */
static locationObject *location_start_loc(locationObject* self, PyObject *args)
{
    /* If we're already zero-length, just return ourself. */
    if (self->start == self->end) {
        Py_INCREF(self);
        return self;
    } else {
        locationObject *loc = location_copy(self);
        if (loc == NULL) return NULL;
        loc->end = self->start;
        return loc;
    }
}

/* Location.end_loc(self) */
/* Return a zero-length location at the end offset */
static locationObject *location_end_loc(locationObject* self, PyObject *args)
{
    /* If we're already zero-length, just return ourself. */
    if (self->start == self->end) {
        Py_INCREF(self);
        return self;
    } else {
        locationObject *loc = location_copy(self);
        if (loc == NULL) return NULL;
        loc->start = self->end;
        return loc;
    }
}

/* Location.union(self, other) */
/* If self and other are contiguous, then return a new location
 * spanning both self and other; otherwise, raise an exception. */
static locationObject *location_union(locationObject* self, PyObject *args)
{
    locationObject *other = NULL;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.union", &locationType, &other))
        return NULL;
    return location__add__(self, other);
}

/* Location.prec(self, other) */
/* Return true if self ends before other begins. */
static PyObject *location_prec(locationObject* self, PyObject *args)
{
    locationObject *other = NULL;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.prec", &locationType, &other))
        return NULL;
    if (!check_units_and_source(self, other))
        return NULL;

    return PyInt_FromLong(self->end <= other->start &&
                          self->start < other->end);
}

/* Location.succ(self, other) */
/* Return true if other ends before self begins. */
static PyObject *location_succ(locationObject* self, PyObject *args)
{
    locationObject *other = NULL;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.succ", &locationType, &other))
        return NULL;
    if (!check_units_and_source(self, other))
        return NULL;

    return PyInt_FromLong(self->start >= other->end &&
                          self->end > other->start);
}

/* Location.overlaps(self, other) */
/* Return true if self overlaps other. */
static PyObject *location_overlaps(locationObject* self, PyObject *args)
{
    locationObject *other = NULL;
    long s1, s2, e1, e2;

    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.overlaps", &locationType, &other))
        return NULL;
    if (!check_units_and_source(self, other))
        return NULL;

    s1 = self->start; e1 = self->end;
    s2 = other->start; e2 = other->end;
    return PyInt_FromLong(((s1 <= s2) && (s2 < e1)) ||
                          ((s2 <= s1) && (s1 < e2)));
}

/* Location.select(self, list) */
/* Return list[self.start:self.end] */
static PyObject *location_select(locationObject* self, PyObject *args)
{
    PyObject *list = NULL;
    
    /* Parse the arguments. */
    if (!PyArg_ParseTuple(args, "O!:Location.overlaps", &PyList_Type, &list))
        return NULL;

    return PyList_GetSlice(list, self->start, self->end);
}

/* ====================== Location Operators ======================= */

/* repr(self) */
static PyObject *location__repr__(locationObject *self)
{
    if (self->end == self->start+1) {
        if (self->unit == Py_None)
            return PyString_FromFormat("@[%ld]", self->start);
        else
            return PyString_FromFormat("@[%ld%s]", self->start,
                                       PyString_AS_STRING(self->unit));
    }
    else if (self->unit == Py_None)
        return PyString_FromFormat("@[%ld:%ld]", self->start, self->end);
    else
        return PyString_FromFormat("@[%ld%s:%ld%s]", self->start,
                                   PyString_AS_STRING(self->unit),
                                   self->end, PyString_AS_STRING(self->unit));
}

/* str(self) */
static PyObject *location__str__(locationObject *self)
{
    if (self->source == Py_None)
        return location__repr__(self);
    else if (is_location(self->source))
        return PyString_FromFormat("%s%s",
          PyString_AS_STRING(location__repr__(self)),
          PyString_AS_STRING(location__str__((locationObject*)self->source)));
    else
        return PyString_FromFormat("%s@%s",
          PyString_AS_STRING(location__repr__(self)),
          PyString_AS_STRING(PyObject_Repr(self->source)));
}

/* len(self) */
static int location__len__(locationObject *self)
{
    return (self->end - self->start);
}

/* cmp(self, other) */
static int location__cmp__(locationObject *self, locationObject *other)
{
    /* Check type(other) */
    if (!is_location(other))
        return 0;

    /* Check for unit/source mismatches */
    if (!check_units_and_source(self, other)) {
        PyErr_Clear(); /* don't raise an exception. */
        return -1;
    }

    /* Compare the start & end indices. */
    if (self->start < other->start)
        return -1;
    else if (self->start > other->start)
        return 1;
    else if (self->end < other->end)
        return -1;
    else if (self->end > other->end)
        return 1;
    else
        return 0;
}

/* hash(self) */
static long location__hash__(locationObject *self)
{
    /* It's unusual for 2 different locations to share a start offset
       (for a given unit/source); so just hash off the start. */
    return self->start;
}

/* self+other */
/* If self and other are contiguous, then return a new location
 * spanning both self and other; otherwise, raise an exception. */
static locationObject *location__add__(locationObject *self,
                                       locationObject *other) {
    /* Check type(other) */
    if (!is_location(other)) {
        PyErr_SetString(PyExc_TypeError, LOC_ERROR_002);
        return NULL;
    }

    if (!check_units_and_source(self, other))
        return NULL;
    
    if (self->end == other->start) {
        locationObject *loc = location_copy(self);
        loc->end = other->end;
        return loc;
    }
    else if (other->end == self->start) {
        locationObject *loc = location_copy(other);
        loc->end = self->end;
        return loc;
    }
    else {
        PyErr_SetString(PyExc_ValueError, LOC_ERROR_005);
        return NULL;
    }
}

/* =================== Location Type Definition ==================== */

/* Location attributes */
struct PyMemberDef location_members[] = {
    {"start", T_INT, offsetof(locationObject, start), RO,
     LOCATION_START_DOC},
    {"end", T_INT, offsetof(locationObject, end), RO,
     LOCATION_END_DOC},
    {"unit", T_OBJECT_EX, offsetof(locationObject, unit), RO,
     LOCATION_UNIT_DOC},
    {"source", T_OBJECT_EX, offsetof(locationObject, source), RO,
     LOCATION_SOURCE_DOC},
    {NULL, 0, 0, 0, NULL} /* Sentinel */
};

/* Location methods */
static PyMethodDef location_methods[] = {
    {"length", (PyCFunction)location_length, METH_NOARGS,
     LOCATION_LENGTH_DOC},
    {"start_loc", (PyCFunction)location_start_loc, METH_NOARGS,
     "Return a location corresponding to the start of this location."},
    {"end_loc", (PyCFunction)location_end_loc, METH_NOARGS,
     "Return a location corresponding to the end of this location."},
    {"union", (PyCFunction)location_union, METH_VARARGS,
     "Union."},
    {"prec", (PyCFunction)location_prec, METH_VARARGS,
     "Prec."},
    {"succ", (PyCFunction)location_succ, METH_VARARGS,
     "Succ."},
    {"overlaps", (PyCFunction)location_overlaps, METH_VARARGS,
     "Overlaps."},
    {"select", (PyCFunction)location_select, METH_VARARGS,
     "Select."},
    
    /* End of list */
    {NULL, NULL, 0, NULL}
};

/* Location operators. */
/* Use the tp_as_sequence protocol to implement len, concat, etc. */
static PySequenceMethods location_as_sequence = {
    (inquiry)location__len__,      /* sq_length */
    (binaryfunc)location__add__,   /* sq_concat */
};

static PyTypeObject locationType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /*ob_size*/
    "token.Location",                          /*tp_name*/
    sizeof(locationObject),                    /*tp_basicsize*/
    0,                                         /*tp_itemsize*/
    (destructor)location_dealloc,              /*tp_dealloc*/
    0,                                         /*tp_print*/
    0,                                         /*tp_getattr*/
    0,                                         /*tp_setattr*/
    (cmpfunc)location__cmp__,                  /*tp_compare*/
    (reprfunc)location__repr__,                /*tp_repr*/
    0,                                         /*tp_as_number*/
    &location_as_sequence,                     /*tp_as_sequence*/
    0,                                         /*tp_as_mapping*/
    (hashfunc)location__hash__,                /*tp_hash */
    0,                                         /*tp_call*/
    (reprfunc)location__str__,                 /*tp_str*/
    0,                                         /*tp_getattro*/
    0,                                         /*tp_setattro*/
    0,                                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /*tp_flags*/
    LOCATION_DOC,                              /* tp_doc */
    0,		                               /* tp_traverse */
    0,		                               /* tp_clear */
    0,		                               /* tp_richcompare */
    0,		                               /* tp_weaklistoffset */
    0,		                               /* tp_iter */
    0,		                               /* tp_iternext */
    location_methods,                          /* tp_methods */
    location_members,                          /* tp_members */
    0,                                         /* tp_getset */
    0,                                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    (initproc)location_init,                   /* tp_init */
    0,                                         /* tp_alloc */
    (newfunc)location_new,                     /* tp_new */
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

    /** Finalize type objects */
    if (PyType_Ready(&locationType) < 0) return;

    /* Initialize the module */
    m = Py_InitModule3("_ctoken", _ctoken_methods, MODULE_DOC);

    /* Add the types to the module dictionary. */
    d = PyModule_GetDict(m);
    PyDict_SetItemString(d, "Location", (PyObject*)&locationType);
}
